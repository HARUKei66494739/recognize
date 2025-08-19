import io
import os
import re
import datetime
import time
import threading
import obswebsocket
import obswebsocket.exceptions
import websocket._exceptions

from src.output import RecognitionOutputer
from src import Logger

class SubtitleOutputer(RecognitionOutputer):
    def __init__(self, truncate_sec:float, logger:Logger):
        self.__prv_time = 0
        self.__truncate_sec = truncate_sec
        self._logger = logger
        #t = threading.Thread(target = self.__scheduler)
        t = threading.Timer(0.1, self.__scheduler)
        t.setDaemon(True)
        t.start()

    def __scheduler(self) -> None:
        cur = time.time()
        if (0 < self.__truncate_sec) and self.__truncate_sec < (cur - self.__prv_time):
            self.output("", "")
        t = threading.Timer(0.1, self.__scheduler)
        t.setDaemon(True)
        t.start()

    def output(self, text_ja:str, text_en:str) -> str:
        self.__prv_time = time.time()
        return text_ja


class NopSubtitleOutputer(SubtitleOutputer):
    """
    何もしない字幕連携
    """
    def __init__(self, logger:Logger) -> None:
        super().__init__(0, logger)

class FileSubtitleOutputer(SubtitleOutputer):
    """
    ファイル出力による字幕連携
    """

    def __init__(self, root:str, truncate_sec:float, logger:Logger) -> None:
        super().__init__(truncate_sec, logger)
        self.__io_ja = open(
            f"{root}{os.sep}subtitle-ja_JP.txt",
            "w",
            encoding="UTF-8",
            newline="")
        self.__io_en = open(
            f"{root}{os.sep}subtitle-en_US.txt",
            "w",
            encoding="UTF-8",
            newline="")

    def output(self, text_ja:str, text_en:str) -> str:
        self.__io_ja.seek(0)
        self.__io_en.seek(0)
        self.__io_ja.truncate(0)
        self.__io_en.truncate(0)
        self.__io_ja.write(text_ja)
        self.__io_en.write(text_en)
        self.__io_ja.flush()
        self.__io_en.flush()
        return super().output(text_ja, text_en)



class ObsV5SubtitleOutputer(SubtitleOutputer):
    """
    OBS Web Socket API v5による字幕連携
    """
    def __init__(
            self, 
            host:str,
            port:int,
            password:str,
            target_text_ja:str | None,
            target_text_en:str | None,
            truncate_sec:float,
            logger:Logger) -> None:
        super().__init__(truncate_sec, logger)

        self.__host = host
        self.__port = port
        self.__password = password
        self.__target_text_ja = target_text_ja
        self.__target_text_en = target_text_en
        self.__try_connect(
            self.__host,
            self.__port,
            self.__password)

    def output(self, text_ja:str, text_en:str) -> str:
        if self.__obs is None:
            self.__try_connect(
                self.__host,
                self.__port,
                self.__password)

        if self.__obs is not None:
            try:
                if self.__target_text_ja is not None:
                    self.__obs.call(obswebsocket.requests.SetInputSettings(
                        inputName = self.__target_text_ja,
                        inputSettings = {
                            "text": text_ja,
                        }
                    ))
                if self.__target_text_en is not None:
                    self.__obs.call(obswebsocket.requests.SetInputSettings(
                        inputName = self.__target_text_en,
                        inputSettings = {
                            "text": text_en,
                        }
                    ))
            except websocket._exceptions.WebSocketConnectionClosedException:
                self.__obs = None
                self._logger.error("OBSとの接続が閉じられました")
        return super().output(text_ja, text_en)

    def __try_connect(self, host, port, password) -> bool:
        try:
            self.__obs = obswebsocket.obsws(host, port, password)
            self.__obs.connect()
            return True
        except obswebsocket.exceptions.ConnectionFailure:
            self.__obs = None
            self._logger.error("OBSとの接続に失敗しました")
            return False