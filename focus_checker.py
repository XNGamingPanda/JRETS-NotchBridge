"""
focus_checker.py — 检测游戏窗口是否处于前台聚焦状态

依赖 pywin32 + psutil；若未安装则降级为始终聚焦（is_focused 恒为 True）。
"""

try:
    import win32gui
    import win32process
    import psutil
    _HAS_WIN32 = True
except ImportError:
    _HAS_WIN32 = False


class FocusChecker:
    def __init__(self, process_name: str, window_title: str = ""):
        """
        :param process_name: 目标进程名，如 "JREAST_TrainSimulator.exe"（精确匹配）
        :param window_title: 备选：窗口标题精确匹配（不做子串匹配，防止误命中资源管理器等）
        """
        self.process_name  = process_name.lower()
        self.window_title  = window_title.lower()
        self.is_focused    = True   # 默认聚焦（无 pywin32 时保持 True）
        self._degraded     = not _HAS_WIN32

    # ------------------------------------------------------------------
    def tick(self) -> bool:
        """每帧调用一次，更新并返回 is_focused。"""
        if self._degraded:
            self.is_focused = True
            return True

        focused = False
        try:
            hwnd = win32gui.GetForegroundWindow()
            if hwnd:
                focused = self._check_by_process(hwnd) or self._check_by_title(hwnd)
        except Exception:
            focused = False

        self.is_focused = focused
        return focused

    # ------------------------------------------------------------------
    def _check_by_process(self, hwnd: int) -> bool:
        """通过 hwnd → PID → 进程名 判断是否为目标进程。"""
        if not self.process_name:
            return False
        try:
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            proc_name = psutil.Process(pid).name().lower()
            return proc_name == self.process_name
        except Exception:
            return False

    def _check_by_title(self, hwnd: int) -> bool:
        """备选：窗口标题精确匹配（==），防止误命中含有相同字符串的其他窗口。"""
        if not self.window_title:
            return False
        try:
            title = win32gui.GetWindowText(hwnd).lower()
            return title == self.window_title
        except Exception:
            return False

    # ------------------------------------------------------------------
    @property
    def degraded(self) -> bool:
        """True 表示 pywin32 不可用，焦点检测已降级。"""
        return self._degraded
