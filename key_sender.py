import ctypes
import ctypes.wintypes
import time

# Virtual key codes
VK_Q = 0x51
VK_K = 0x4B
VK_L = 0x4C
VK_Z = 0x5A
VK_S = 0x53
VK_A = 0x41
VK_M = 0x4D
VK_1 = 0x31
VK_COMMA = 0xBC
VK_SLASH = 0xBF
VK_RETURN = 0x0D
VK_BACK = 0x08
VK_W = 0x57
VK_DOT = 0xBE
VK_PRIOR = 0x21
VK_NEXT = 0x22
VK_END = 0x23

MAPVK_VK_TO_VSC = 0
INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_EXTENDEDKEY = 0x0001

_EXTENDED_VK = frozenset({
    0x21,  # VK_PRIOR
    0x22,  # VK_NEXT
    0x23,  # VK_END
    0x24,  # VK_HOME
    0x25,  # VK_LEFT
    0x26,  # VK_UP
    0x27,  # VK_RIGHT
    0x28,  # VK_DOWN
    0x2D,  # VK_INSERT
    0x2E,  # VK_DELETE
    0x6F,  # VK_DIVIDE
    0x5B,  # VK_LWIN
    0x5C,  # VK_RWIN
    0x5D,  # VK_APPS
})

PUL = ctypes.POINTER(ctypes.c_ulong)


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", ctypes.c_long),
        ("dy", ctypes.c_long),
        ("mouseData", ctypes.c_ulong),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", PUL),
    ]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", ctypes.c_ushort),
        ("wScan", ctypes.c_ushort),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", PUL),
    ]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", ctypes.c_ulong),
        ("wParamL", ctypes.c_short),
        ("wParamH", ctypes.c_ushort),
    ]


class _INPUT_UNION(ctypes.Union):
    _fields_ = [
        ("mi", MOUSEINPUT),
        ("ki", KEYBDINPUT),
        ("hi", HARDWAREINPUT),
    ]


class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", ctypes.c_ulong),
        ("_input", _INPUT_UNION),
    ]


assert ctypes.sizeof(INPUT) == 40, (
    f"INPUT struct size = {ctypes.sizeof(INPUT)}, expected 40. "
    "SendInput will reject all inputs on this platform."
)


def send_key_raw(vk_code: int, hold_ms: int = 0) -> bool:
    """Send a single key down/up pair via SendInput."""
    is_ext = vk_code in _EXTENDED_VK
    base_flags = KEYEVENTF_EXTENDEDKEY if is_ext else 0
    scan = ctypes.windll.user32.MapVirtualKeyW(vk_code, MAPVK_VK_TO_VSC)
    extra = ctypes.c_ulong(0)

    def _make(flags: int) -> INPUT:
        return INPUT(
            type=INPUT_KEYBOARD,
            _input=_INPUT_UNION(ki=KEYBDINPUT(
                wVk=vk_code,
                wScan=scan,
                dwFlags=flags,
                time=0,
                dwExtraInfo=ctypes.pointer(extra),
            )),
        )

    down = _make(base_flags)
    up = _make(base_flags | KEYEVENTF_KEYUP)

    sent = ctypes.windll.user32.SendInput(1, ctypes.byref(down), ctypes.sizeof(INPUT))
    if hold_ms > 0:
        time.sleep(hold_ms / 1000.0)
    ctypes.windll.user32.SendInput(1, ctypes.byref(up), ctypes.sizeof(INPUT))
    return sent > 0


def send_key_down(vk_code: int) -> bool:
    is_ext = vk_code in _EXTENDED_VK
    base_flags = KEYEVENTF_EXTENDEDKEY if is_ext else 0
    scan = ctypes.windll.user32.MapVirtualKeyW(vk_code, MAPVK_VK_TO_VSC)
    extra = ctypes.c_ulong(0)
    down = INPUT(
        type=INPUT_KEYBOARD,
        _input=_INPUT_UNION(ki=KEYBDINPUT(
            wVk=vk_code,
            wScan=scan,
            dwFlags=base_flags,
            time=0,
            dwExtraInfo=ctypes.pointer(extra),
        )),
    )
    sent = ctypes.windll.user32.SendInput(1, ctypes.byref(down), ctypes.sizeof(INPUT))
    return sent > 0


def send_key_up(vk_code: int) -> bool:
    is_ext = vk_code in _EXTENDED_VK
    base_flags = KEYEVENTF_EXTENDEDKEY if is_ext else 0
    scan = ctypes.windll.user32.MapVirtualKeyW(vk_code, MAPVK_VK_TO_VSC)
    extra = ctypes.c_ulong(0)
    up = INPUT(
        type=INPUT_KEYBOARD,
        _input=_INPUT_UNION(ki=KEYBDINPUT(
            wVk=vk_code,
            wScan=scan,
            dwFlags=base_flags | KEYEVENTF_KEYUP,
            time=0,
            dwExtraInfo=ctypes.pointer(extra),
        )),
    )
    sent = ctypes.windll.user32.SendInput(1, ctypes.byref(up), ctypes.sizeof(INPUT))
    return sent > 0


class KeyQueue:
    def __init__(self):
        self.pending: list[int] = []
        self.last_send_time: float = 0.0
        self.last_sent_vk: int | None = None

    def push(self, vk_list: list[int]) -> None:
        self.pending.extend(vk_list)

    def push_urgent(self, vk_code: int) -> None:
        self.pending.clear()
        self.pending.insert(0, vk_code)

    def clear(self) -> None:
        self.pending.clear()

    def tick(self, interval_ms: float) -> bool:
        now = time.monotonic()
        if self.pending and (now - self.last_send_time) * 1000 >= interval_ms:
            vk = self.pending.pop(0)
            send_key_raw(vk)
            self.last_sent_vk = vk
            self.last_send_time = now
            return True
        return False

    def __len__(self) -> int:
        return len(self.pending)
