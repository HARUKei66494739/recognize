import os
import json
from websockets.sync.client import connect, ClientConnection
from typing import Callable
import threading
import pythonosc.udp_client as osc
import subprocess

import src.exception as ex
from src.cancellation import CancellationObject

class RecognitionOutputer:
    """
    認識結果を出力する抽象基底クラス
    """
    def output(self, text_ja:str, text_en:str) -> str:
        """
        認識結果を出力
        """
        return text_ja

class PrintOutputer(RecognitionOutputer):
    """
    標準出力に出力する
    """
    pass

class VrChatOutputer(RecognitionOutputer):
    """
    VRC OSCに字幕を出力するための機構
    """
    def __init__(self):
        self.__client = osc.SimpleUDPClient("127.0.0.1", 9000)


    def __del__(self):
        self.__client = None

    def output(self, text_ja:str, text_en:str) -> str:
        if self.__client != None:
            self.__client.send_message("/chatbox/input", [text_ja, True, True])
        return text_ja

class WebSocketOutputer(RecognitionOutputer):
    """
    ウェブソケットに出力する基底クラス
    """
    def __init__(self, uri:str, remote_name:str):
        self.__uri = uri
        self.__remote_name = remote_name
        self.__soc:ClientConnection | None = None
        try:
            self.__con()
        except:
            # コンストラクタなので今回は無視する
            pass

    def __del__(self):
        if not self.__soc is None:
            try:
                self.__soc.close()
            except:
                # どうしようもないし無視する
                pass
        self.__soc = None

    def __con(self) -> None:
        """
        ウェブソケットに接続を試行する
        """
        if not self.__soc is None:
            return

        self.__soc = connect(self.__uri)

    @property
    def _socket(self):
        self.__con()
        return self.__soc


    def output(self, text_ja:str, text_en:str) -> str:
        ...

    def _send(self, text:str) -> str:
        #async def send(text:str):
        #    async with websockets.connect(self.uri) as websocket:
        #        await websocket.send(text)
        #        await websocket.close()
        try:
            self.__con()
        except Exception as e:
            self.__soc = None
            raise WsOutputException(f"リモート[{self.__remote_name}]への接続に失敗しました。{os.linesep}認識結果: {text}", e)

        try:
            if isinstance(self.__soc, ClientConnection):
                self.__soc.send(text)
        except Exception as e:
            self.__soc = None
            raise WsOutputException(f"リモート[{self.__remote_name}]への送信に失敗しました。{os.linesep}認識結果: {text}", e)
        return text
    
    def _recv(self, timeout:float) -> str | None:
        try:
            if isinstance(self.__soc, ClientConnection):
                return str(self.__soc.recv(timeout))
        except Exception as e:
            self.__soc = None
            raise WsOutputException(f"リモート[{self.__remote_name}]からの受信に失敗しました。{os.linesep}", e)
        return None



# ゆかりねっとws仕様
# 0:[認識文字列] => 認識結果の文字列を送信
# 1:close
# 1:[エラーメッセージ]
# 2:network
# 3:aborted
class YukarinetteOutputer(WebSocketOutputer):
    """
    ゆかりねっと外部連携に出力する
    """
    def __init__(self, uri:str):
        super().__init__(uri, "ゆかりねっと")

    def output(self, text_ja:str, text_en:str) -> str:
        return self._send(f"0:{text_ja}")

class YukaconeOutputer(WebSocketOutputer):
    """
    ゆかコネNEO外部連携に出力する
    """
    def __init__(self, uri:str):
        super().__init__(f"{uri}/textonly", "ゆかコネNEO")

    def output(self, text_ja:str, text_en:str) -> str:
        return self._send(text_ja)

    @staticmethod
    def get_port(port:int | None) -> str:
        def get() -> str:
            import winreg
            key:winreg.HKEYType | None = None
            try:
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Software\\YukarinetteConnectorNeo")
                for i in range(winreg.QueryInfoKey(key)[1]):
                    name, val, _ = winreg.EnumValue(key, i)
                    if name == "WebSocket":
                        return str(val)
                raise RuntimeError("ゆかコネが見当たりません")
            finally:
                if not key is None:
                    winreg.CloseKey(key)

        if not port is None:
            return str(port)
        else:
            return get()

class IlluminateSpeechOutputer(WebSocketOutputer):
    def __init__(
            self,
            host:str,
            port:int,
            exe_path:str,
            exe_voice:str,
            exe_client:str,
            exe_launch:bool,
            kana:bool,
            notify_icon:bool,
            debug:bool,
            capture_pause:float,
            cancel:CancellationObject):
        super().__init__( f"ws://{host}:{port}", "Illuminate")
        self.__cancel = cancel
        self.__cooperation_outputers:list[RecognitionOutputer] = []
        self.__thread:threading.Thread|None = None

        args =  [
            exe_path,
             f"--master", f"{os.getpid()}",
             f"--port", f"{port}",
             f"--voice", exe_voice,
             f"--client", exe_client,
             f"--capture_pause", f"{capture_pause}",
        ]
        if notify_icon:
            args.append("--notify_icon")
        if kana:
            args.append("--kana")
        if debug:
            args.append("--debug")
        subprocess.Popen(args)

    def output(self, text_ja:str, text_en:str) -> str:
        return self._send(json.dumps({
            "transcript": text_ja,
            "translate": text_en,
            "finish": True,
        }, ensure_ascii=False))
    
    def set_subtitle_cooperation(self, outputers:list[RecognitionOutputer]):
        for it in outputers:
            self.__cooperation_outputers.append(it)
        self.__thread = threading.Thread(target=self.__thread_proc)
        self.__thread.setDaemon(True)
        self.__thread.start()

    def __thread_proc(self):
        while self.__cancel:
            try:
                soc = self._socket
                if soc != None:
                    o = json.loads(str(soc.recv()))
                    if not o["finish"]:
                        for it in self.__cooperation_outputers:
                            it.output(
                                o["transcript"],
                                o["translate"])
            except:
                pass


class WsOutputException(ex.IlluminateException):
    """
    ウェブソケットでエラーが出た際になげる例外
    """
    pass
