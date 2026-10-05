import sys
from datetime import datetime

# try:
#     from PyQt6.QtCore import QObject, pyqtSignal
# except ImportError:
#     try:
#         from PyQt5.QtCore import QObject, pyqtSignal
#     except ImportError:
#         QObject = object

#         def pyqtSignal(*args):
#             return None


class BaseLogger:
    def _format_msg(self, level: str, msg: str) -> str:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        padded_level = f"{level.upper():<7}"
        return f"[{timestamp}] [{padded_level}] {msg}"

    def i(self, msg: str): raise NotImplementedError
    def d(self, msg: str): raise NotImplementedError
    def w(self, msg: str): raise NotImplementedError
    def e(self, msg: str): raise NotImplementedError


class ConsoleLogger(BaseLogger):
    COLORS = {
        "INFO": "\033[32m",     # green
        "DEBUG": "\033[36m",    # cyan
        "WARNING": "\033[33m",  # yello
        "ERROR": "\033[31m",    # red
    }
    RESET = "\033[0m"

    def _print(self, level: str, msg: str, is_error: bool = False):
        base_str = self._format_msg(level, msg)
        color = self.COLORS.get(level.upper(), "")
        colored_str = f"{color}{base_str}{self.RESET}"

        if is_error:
            print(colored_str, file=sys.stderr)
        else:
            print(colored_str)

    def i(self, msg: str): self._print("INFO", msg)
    def d(self, msg: str): self._print("DEBUG", msg)
    def w(self, msg: str): self._print("WARNING", msg)
    def e(self, msg: str): self._print("ERROR", msg, is_error=True)


# class PyQtLogger(QObject, BaseLogger):
#     log_signal = pyqtSignal(str, str)  # Truyền (level, chuỗi đã format)

#     def __init__(self, parent=None):
#         if QObject is not object:
#             super().__init__(parent)
#         else:
#             super().__init__()

#     def _emit(self, level: str, msg: str):
#         formatted = self._format_msg(level, msg)
#         if hasattr(self.log_signal, 'emit'):
#             self.log_signal.emit(level.upper(), formatted)
#         else:
#             print(formatted)

#     def i(self, msg: str): self._emit("INFO", msg)
#     def d(self, msg: str): self._emit("DEBUG", msg)
#     def w(self, msg: str): self._emit("WARNING", msg)
#     def e(self, msg: str): self._emit("ERROR", msg)


logger: BaseLogger = ConsoleLogger()


def set_logger(new_logger: BaseLogger):
    global logger
    logger = new_logger
