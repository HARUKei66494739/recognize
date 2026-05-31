import json
import time
import audioop
import collections
import queue
import threading
import http.server
import socket
import ipaddress
import sounddevice
import math
import numpy as np
from websockets.sync.server import serve
from typing import Any, Callable, Deque, NamedTuple

from src import Logger, rms2db
import src.interface as inf
import src.recognition as recognition
import src.filter as filter
import src.val as val
import src.exception as exception
from src.cancellation import CancellationObject

class ListenEnergy(NamedTuple):
    value:float
    max:float
    min:float

class _Indicator:
    def __init__(self) -> None:
        import datetime
        pass
        self.__now = 0
        self.__db_str = ""
        self.__UPDATE_SEC = 0.33

    def update(self, str, dB, color_foreground:str, color_background:str, print:Any) -> None:
        import time
        def __round(number, ndigits=0) -> float:
            """
            四捨五入
            """
            p = 10 ** ndigits
            return (number * p * 2 + 1) // 2 / p
        MAX = 71
        now = time.time()
        if self.__UPDATE_SEC < (now - self.__now):
            self.__now = now
            if 80 < dB:
                self.__db_str = "8+.0dB"
            else:
                self.__db_str = f"{__round(dB, 1):.1f}dB"

        dB = min(dB, 80)
        len = int(dB / 80 * MAX)
        a = "".join(map(lambda _: " ", range(len)))
        b = "".join(map(lambda _: " ", range(MAX - len)))
        #print("\033[1G", end="", flush=True)
        print(f"{str}{self.__db_str}|{color_foreground}{a}{color_background}{b}{val.Console.Reset.value}\r", end="")


class ListenResultParam(NamedTuple):
    '''listenのコールバックパラメータ'''
    pcm:bytes
    '''PCMバイナリデータ'''
    energy:ListenEnergy | None
    '''pcmのRMS値(src.mic.AudioDataのみに格納)'''

class Device(NamedTuple):
    device_no:int
    hostapi:str
    name:str

    def __str__(self) -> str:
        return f"{self.device_no} : {self.name}"

class Microphone:
    def __init__(self) -> None:
        pass

    @property
    def device_name(self) -> str:
        ...

    @property
    def energy_threshold(self) -> float:
        ...

    @property
    def start_insert_sec(self) -> float:
        ...

    @property
    def end_insert_sec(self) -> float:
        ...

    @property
    def record_min_sec(self) -> float:
        ...

    @property
    def sample_rate(self) -> int:
        ...

    @property
    def sample_width(self) -> int:
        ...

    @property
    def chunk_size(self) -> int:
        ...

    @staticmethod
    def query_devices() -> list[Device]:
        r:list[Device] = []
        for hostapi in sounddevice.query_hostapis():
            if hostapi["name"].lower() == "mme": #type: ignore
                for device_numbar in hostapi["devices"]: #type: ignore
                    device = sounddevice.query_devices(device=device_numbar)
                    if 0 < device["max_input_channels"]: #type: ignore
                        r.append(Device(device_numbar, hostapi["name"], device["name"])) #type: ignore
        return r

    def listen(
        self,
        onrecord:Callable[[int, str|ListenResultParam], None],
        cancel:CancellationObject,
        opt_enable_energy_threshold:bool = True,
        opt_enable_indicator:bool|None = None):
        ...

class Indexable:
    def __init__(self):
        self.__index = 0

    @property
    def index(self):
        return self.__index

    def update_index(self) -> int:
        self.__index += 1
        return self.__index

class DeviceMicrophone(Microphone):
    __BAR_COLOR_NONE = val.Console.background_index(240)
    __BAR_COLOR_ENAGY_OK = val.Console.background_index(35)
    __BAR_COLOR_VAD_OK = val.Console.background_index(39)
    __BAR_COLOR_BACKGROUND = val.Console.background_index(234)

    def __init__(
            self,
            energy_threshold:float,
            mp_recog_conf:recognition.RecognizeMicrophoneConfig,
            filter_vad:inf.VoiceActivityDetectorFilter,
            filter_highPass:filter.HighPassFilter | None,
            phase2_sec:float | None,
            record_min_sec:float,
            push_talk:list[str],
            device:int|None,
            logger:Logger) -> None:
        self.__energy_threshold = energy_threshold
        self.__recog_conf = mp_recog_conf
        self.__filter_vad = filter_vad
        self.__filter_highPass = filter_highPass
        self.__device = device
        self.__vad_sec = 0.5
        if phase2_sec == None:
            self.__vad_phase2_sec = filter_vad.mic_pause_duration
        else:
            self.__vad_phase2_sec = phase2_sec
        self.__record_min_sec = record_min_sec
        self.__sample_rate = val.MIC_SAMPLE_RATE
        self.__sample_width = val.MIC_SAMPLE_WIDTH
        self.__chunk_size = 1024
        self.__logger = logger
        self.__indicator = _Indicator()
        self.__push_talk = push_talk

        d = sounddevice.query_devices(
            device=device) if not device is None else sounddevice.query_devices(
                device=sounddevice.default.device[0],
                kind="input")
        if d is None:
            self.__device_name = "-不明なデバイス-"
        else:
            self.__device_name = d["name"] #type: ignore

    @property
    def device_name(self) -> str: return self.__device_name

    @property
    def energy_threshold(self) -> float: return self.__energy_threshold

    @property
    def start_insert_sec(self) -> float: return self.__recog_conf.head_insert_duration

    @property
    def end_insert_sec(self) -> float: return self.__recog_conf.tail_insert_duration

    @property
    def record_min_sec(self) -> float: return self.__record_min_sec

    @property
    def sample_rate(self) -> int: return self.__sample_rate
    @property
    def sample_width(self) -> int: return self.__sample_width
    @property
    def chunk_size(self) -> int: return self.__chunk_size

    def listen(
        self,
        onrecord:Callable[[int, str|ListenResultParam], None],
        cancel:CancellationObject,
        opt_enable_energy_threshold:bool = True,
        opt_enable_indicator:bool|None = None):

        if 0 < len(self.__push_talk):
            self.__listen_push_to(
                onrecord,
                cancel,
                opt_enable_energy_threshold,
                opt_enable_indicator)
        else:
            self.__listen(
                onrecord,
                cancel,
                opt_enable_energy_threshold,
                opt_enable_indicator)

    def __listen(
        self,
        onrecord:Callable[[int, str|ListenResultParam], None],
        cancel:CancellationObject,
        opt_enable_energy_threshold:bool = True,
        opt_enable_indicator:bool|None = None):
        index = 0

        if opt_enable_energy_threshold:
            energy_threshold = self.energy_threshold
        else:
            energy_threshold = 0
        if not opt_enable_indicator is None and opt_enable_indicator:
            _print = print
        else:
            _print = self.__logger.notice

        with sounddevice.RawInputStream(
            samplerate=self.__sample_rate,
            blocksize=self.__chunk_size,
            channels=1,
            dtype="int16",
            device=self.__device) as stream:

            dB = 0.0
            vad_list_len = math.ceil(self.sample_rate * self.__vad_sec / self.__chunk_size)
            vad_phase2_len = max(1, math.ceil(self.sample_rate * self.__vad_phase2_sec / self.__chunk_size))
            while cancel.alive:
                frames = collections.deque()
                is_overflowed = False

                # chunk_sizeが小さい場合VADが認識しないのでvad_secバッファをためてVADにかける
                #print("Phase.0")
                #ph2_frames = collections.deque()
                for _ in range(vad_list_len):
                    self.__indicate(dB, _print)

                    _buffer, overflowed = stream.read(self.__chunk_size)
                    if(overflowed):
                        self.__logger.error("overflowed")
                        is_overflowed = True
                        break
                    buffer = self.filter(bytes(_buffer)) # type: ignore
                    en = audioop.rms(buffer, val.MIC_SAMPLE_WIDTH)
                    dB = rms2db(en)
                    frames.append((buffer, en))

                # 開始音検索位置
                #print("Phase.1")
                if is_overflowed:
                    continue
                while True:
                    self.__indicate(dB, _print)

                    b = b"".join(map(lambda x:x[0], frames))
                    energy = audioop.rms(b, val.MIC_SAMPLE_WIDTH)
                    if energy_threshold < energy and self.__filter_vad.check(b):
                        break
                    else:
                        frames.popleft()

                    _buffer, overflowed = stream.read(self.__chunk_size)
                    if(overflowed):
                        self.__logger.error("overflowed")
                        break
                    buffer = self.filter(bytes(_buffer)) # type: ignore
                    en = audioop.rms(buffer, val.MIC_SAMPLE_WIDTH)
                    dB = rms2db(en)
                    frames.append((buffer, en))

                # 声が含まれなくなるまでVADにかける
                #print("Phase.2")
                if is_overflowed:
                    continue
                while True:
                    #temp = []
                    #for _ in range(vad_phase2_len):
                    #    _buffer, overflowed = stream.read(self.__chunk_size)
                    #    if(overflowed):
                    #        self.__logger.error("overflowed")
                    #        break
                    #    buffer = self.filter(bytes(_buffer)) # type: ignore
                    #    temp.append(buffer)
                    #    db = rms2db(audioop.rms(buffer, val.MIC_SAMPLE_WIDTH))
                    #    self.__indicate_pahse2(db, _print)

                    _buffer, overflowed = stream.read(self.__chunk_size)
                    if(overflowed):
                        self.__logger.error("overflowed")
                        break
                    buffer = self.filter(bytes(_buffer)) # type: ignore
                    db = rms2db(audioop.rms(buffer, val.MIC_SAMPLE_WIDTH))
                    self.__indicate_pahse2(db, _print)

                    frames.append((_buffer, audioop.rms(buffer, val.MIC_SAMPLE_WIDTH)))
                    if len(frames) < vad_phase2_len:
                        continue
                    b = b"".join(map(lambda x: x[0], frames))
                    if not self.__filter_vad.check(b[-(vad_phase2_len * self.__chunk_size * 2):]):
                       break
                if is_overflowed:
                    continue
                print("\033[1G\033[0K", end="", flush=True)

                # 先頭末尾無音追加処理
                head = b""
                tail = b""
                if 0 < self.__recog_conf.head_insert_duration:
                    mx = math.ceil(self.__sample_rate * self.__recog_conf.head_insert_duration)
                    head = b"".join(map(lambda _: b"00", range(mx)))
                if 0 < self.__recog_conf.tail_insert_duration:
                    mx = math.ceil(self.__sample_rate * self.__recog_conf.tail_insert_duration)
                    tail = b"".join(map(lambda _: b"00", range(mx)))
                frame_data = head + b"".join(map(lambda x: x[0], frames)) + tail
                index += 1
                onrecord(index, ListenResultParam(
                    frame_data,
                    ListenEnergy(
                        sum(map(lambda x: x[1], frames)) / len(frames),
                        max(map(lambda x: x[1], frames)),
                        min(map(lambda x: x[1], frames)))))

    def __listen_push_to(
        self,
        onrecord:Callable[[int, str|ListenResultParam], None],
        cancel:CancellationObject,
        opt_enable_energy_threshold:bool = True,
        opt_enable_indicator:bool|None = None):
        index = 0

        if opt_enable_energy_threshold:
            energy_threshold = self.energy_threshold
        else:
            energy_threshold = 0
        if not opt_enable_indicator is None and opt_enable_indicator:
            _print = print
        else:
            _print = self.__logger.notice

        with sounddevice.RawInputStream(
            samplerate=self.__sample_rate,
            blocksize=self.__chunk_size,
            channels=1,
            dtype="int16",
            device=self.__device) as stream:
            while cancel.alive:
                dB = 0.0
                is_overflowed = False
                frames = collections.deque()

                self.__indicate(dB, _print)
                while self.__is_input():
                    _buffer, overflowed = stream.read(self.__chunk_size)
                    if(overflowed):
                        self.__logger.error("overflowed")
                        is_overflowed = True
                        break
                    buffer = self.filter(bytes(_buffer)) # type: ignore
                    en = audioop.rms(buffer, val.MIC_SAMPLE_WIDTH)
                    dB = rms2db(en)
                    frames.append((buffer, en))
                    self.__indicate_pahse2(dB, _print)

                if is_overflowed:
                    continue

                if len(frames):
                    print("\033[1G\033[0K", end="", flush=True)

                    # 先頭末尾無音追加処理
                    frame_data = b"".join(map(lambda x: x[0], frames))
                    index += 1
                    onrecord(index, ListenResultParam(
                        frame_data,
                        ListenEnergy(
                            sum(map(lambda x: x[1], frames)) / len(frames),
                            max(map(lambda x: x[1], frames)),
                            min(map(lambda x: x[1], frames)))))


    def listen_ambient(self, record_sec:float) -> ListenEnergy:
        with sounddevice.RawInputStream(
            samplerate=self.__sample_rate,
            blocksize=self.__chunk_size,
            channels=1,
            dtype="int16",
            device=self.__device) as stream:

            c = []
            loop = math.ceil(self.__sample_rate * record_sec / self.__chunk_size)
            for _ in range(loop):
                _buffer, overflowed = stream.read(self.__chunk_size)
                buffer = bytes(_buffer) #type: ignore
                en = audioop.rms(buffer, val.MIC_SAMPLE_WIDTH)
                c.append(en)
                self.__indicate(rms2db(en), print)

            return ListenEnergy(
                sum(map(lambda x: x, c)) / len(c),
                max(map(lambda x: x, c)),
                min(map(lambda x: x, c)))

    def filter(self, buffer:bytes) -> bytes:
        if self.__filter_highPass is None:
            return buffer
        else:
            fft = np.fft.fft(np.frombuffer(buffer, np.int16).flatten())
            self.__filter_highPass.filter(fft)
            return np.real(np.fft.ifft(fft)).astype(np.uint16, order="C").tobytes()

    def __is_input(self) -> bool:
        for it in self.__push_talk:
            type, pm = it.split(":")
            if type.upper() == "KEYBOARD":
                import ctypes
                v1, _ = pm.split(",")
                r = (ctypes.windll.user32.GetAsyncKeyState(val.VK[v1.upper()]) >> 8) != 0
                if r:
                    return True
            elif (type.upper() == "VR") or (type.upper() == "QUEST") or (type.upper() == "INDEX"):
                import src.vr as vr

                action_name, role_name, v3, _ = pm.split(",")
                role = None
                if role_name.upper() == "LEFT":
                    role = vr.TARACK_ROLE_LEFT
                elif role_name.upper() == "RIGHT":
                    role = vr.TARACK_ROLE_RIGHT

                controller_type = None
                target = None
                #knuckles
                if type.upper() == "INDEX":
                    controller_type = "knuckles"
                    if v3.upper() == "TRIGGER":
                        target = vr.BUTTON_INDEX_TRIGGER
                    elif v3.upper() == "STICK":
                        target = vr.BUTTON_INDEX_STICK
                    elif v3.upper() == "A":
                        target = vr.BUTTON_INDEX_A
                    elif v3.upper() == "B":
                        target = vr.BUTTON_INDEX_B

                if type.upper() == "QUEST":
                    controller_type = "oculus_touch"
                    if v3.upper() == "STICK":
                        target = vr.BUTTON_QUEST_STICK
                    elif v3.upper() == "GRIP":
                        target = vr.BUTTON_QUEST_GRIP
                    elif v3.upper() == "TRIGGER":
                        target = vr.BUTTON_QUEST_TRIGGER
                    elif v3.upper() == "A":
                        target = vr.BUTTON_QUEST_A
                    elif v3.upper() == "B":
                        target = vr.BUTTON_QUEST_B
                    elif v3.upper() == "X":
                        intargetddex = vr.BUTTON_QUEST_X
                    elif v3.upper() == "Y":
                        index = vr.BUTTON_QUEST_Y
                elif type.upper() == "VR":
                    target = int(v3)

                if role == None:
                    continue
                if target == None:
                    continue

                if action_name.upper() == "TOUCH":
                    if vr.is_touch(
                        index = target,
                        role = role,
                        target_device = controller_type):
                        return True
                elif action_name.upper() == "PRESS":
                    if vr.is_touch(
                        index = target,
                        role = role,
                        target_device = controller_type):
                        return True
        return False


    def __indicate(self, dB, print:Any):
        if rms2db(self.energy_threshold) < dB:
            color = DeviceMicrophone.__BAR_COLOR_ENAGY_OK
        else:
            color = DeviceMicrophone.__BAR_COLOR_NONE
        self.__print_dB("！", dB, color, print)

    def __indicate_pahse2(self, dB, print:Any):
        self.__print_dB("＃", dB, DeviceMicrophone.__BAR_COLOR_VAD_OK, print)

    def __print_dB(self, str, dB, color:str, print:Any):
        self.__indicator.update(str, dB, color, DeviceMicrophone.__BAR_COLOR_BACKGROUND, print)



class RecognizeHandler(http.server.BaseHTTPRequestHandler):
    _responseHtml:str = ""

    @staticmethod
    def initHtml(html:str):
        if RecognizeHandler._responseHtml != "":
            raise exception.ProgramError()
        
        RecognizeHandler._responseHtml = html

    def do_GET(self):
        print(self.path)
        if(self.path != "/"):
            self.send_response(404)
            self.send_header("Content-type","text/html")
            self.end_headers()
            self.wfile.write(bytes("404", "utf8"))
            return

        self.send_response(200)
        self.send_header("Content-type","text/html")
        self.end_headers()
        self.wfile.write(bytes(RecognizeHandler._responseHtml, "utf8"))

class ChromeMicrophone(Microphone, Indexable):
    def __init__(
        self,
        bind_ip:str|None,
        http_port:int|None,
        ws_port:int|None,
        is_locally:bool,
        _:CancellationObject,
        logger:Logger) -> None:
        global _responseHtml

        Microphone.__init__(self)
        Indexable.__init__(self)
        def _ip() -> str:
            if bind_ip == None:
                return val.get_localhost_address()
            if bind_ip == "":
                return val.get_localhost_address()
            return bind_ip
        
        def _http_port() -> int:
            if http_port == None:
                return val.HTTP_PORT
            if http_port == 0:
                return val.HTTP_PORT
            return http_port

        def _ws_port() -> int:
            if ws_port == None:
                return _http_port() + 1
            if ws_port == 0:
                return _http_port() + 1
            return ws_port

        def _url(scheme:str, host:str, port:int) -> str:
            if host == val.get_localhost_address():
                return f"{scheme}://localhost:{port}/"
            return f"{scheme}://{host}:{port}/"
            
        self.__http_ip = _ip()
        self.__http_port = _http_port()
        self.__ws_port = _ws_port()
        self.__logger = logger
        self.__http_uri = _url("http", self.__http_ip, self.__http_port)
    
        with open(val.get_recognize_html(), "r", encoding="utf-8") as f:
            html = f.read()
            html = html.replace("$$WS_PORT$$", f"{self.__ws_port}")
            html = html.replace("$$LOCALLY$$", "true")
            RecognizeHandler.initHtml(html)

    @property
    def device_name(self) -> str:
        return "Chrome"

    @property
    def energy_threshold(self) -> float:
        return 0

    @property
    def start_insert_sec(self) -> float:
        return 0

    @property
    def end_insert_sec(self) -> float:
        return 0


    @property
    def record_min_sec(self) -> float:
        return 0


    @property
    def sample_rate(self) -> int:
        return 0


    @property
    def sample_width(self) -> int:
        return 0


    @property
    def chunk_size(self) -> int:
        return 0

    def listen(
        self,
        onrecord:Callable[[int, str|ListenResultParam], None],
        cancel:CancellationObject,
        opt_enable_energy_threshold:bool = True,
        opt_enable_indicator:bool|None = None):

        def __ws_thread_proc():
            def __echo(websocket):
                # クライアントからのメッセージを受信（ブロックします）
                for message in websocket:
                    #print(f"受信: {message}")
                    smsg = str(message)
                    if smsg == "ping":
                        continue

                    o = json.loads(smsg)
                    if o["finish"]:
                        onrecord(self.update_index(), o["transcript"])
            with serve(__echo, "localhost", self.__ws_port) as server:
                server.serve_forever()

        self.__ws_thread = threading.Thread(target=__ws_thread_proc)
        self.__ws_thread.daemon = True
        self.__ws_thread.start()

        ip = ipaddress.ip_address(self.__http_ip)
        if ip.version == 4:
            http.server.HTTPServer.address_family = socket.AddressFamily.AF_INET
        if ip.version == 6:
            http.server.HTTPServer.address_family = socket.AddressFamily.AF_INET6

        with http.server.HTTPServer((self.__http_ip, self.__http_port), RecognizeHandler) as server:
            self.__logger.print(f"Chromeを起動し{self.__http_uri}にアクセスしてください")
            server.serve_forever()
            while cancel.alive:
                time.sleep(0.01)