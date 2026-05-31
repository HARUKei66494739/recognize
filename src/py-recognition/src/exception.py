

class IlluminateException(Exception):
    """
    例外基底クラス
    """
    def __init__(self, message:str, inner:Exception|None = None):
        super().__init__(message)
        self.__message = message
        self.__inner = inner

    def __str__(self) -> str:
        return f"{type(self)}:{self.message}"

    @property
    def message(self) -> str:
        """
        例外メッセージ
        """
        return self.__message

    @property
    def inner(self) -> Exception | None:
        """
        内部例外がある場合内部例外
        """
        return self.__inner

class TmpError__(Exception):
    """
    ブロック抜けるための仮置き例外
    """
    pass


class ProgramError(Exception):
    """
    この例外はプログラムバグなので投げられても処理しないこと
    """
    pass
