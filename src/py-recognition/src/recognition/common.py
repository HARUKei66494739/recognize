import src.exception as ex

class RecognizeMicrophoneConfig:
    def __init__(self, head_insert_duration:float, tail_insert_duration:float) -> None:
        self.__head_insert_duration = head_insert_duration
        self.__tail_insert_duration = tail_insert_duration

    @property
    def head_insert_duration(self) -> float:
        return self.__head_insert_duration

    @property
    def tail_insert_duration(self) -> float:
        return self.__tail_insert_duration


class DefaultMicrophoneConfig(RecognizeMicrophoneConfig):
    __DEFAULT_HEAD_DULATION = 0.
    __DEFAULT_TAIL_DULATION = 0.

    def __init__(self, head_insert_duration:float | None = None, tail_insert_duration:float | None = None) -> None:
        super().__init__(
            head_insert_duration if not head_insert_duration is None else DefaultMicrophoneConfig.__DEFAULT_HEAD_DULATION,
            tail_insert_duration if not tail_insert_duration is None else DefaultMicrophoneConfig.__DEFAULT_TAIL_DULATION)


class TranscribeException(ex.IlluminateException):
    """
    認識に失敗した際なげる例外
    """
    pass

#class TranslateException(ex.IlluminateException):
#    """
#    認識に失敗した際なげる例外
#    """
#    pass