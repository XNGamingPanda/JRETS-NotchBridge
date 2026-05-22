"""
JRETS Controller — main.py
JR East Train Simulator 外设控制插件

窗口: 400 × 560 px，固定大小，Always-On-Top
"""

import sys
import os
import json
import time
import pygame
import shutil

from notch import (
    build_notch_names, notch_color, notch_description,
    get_total_notches, axis_to_notch, axis_to_notch_calibrated, apply_deadzone,
    COLOR_BG, COLOR_WHITE, COLOR_GRAY, COLOR_GREEN,
    COLOR_RED, COLOR_ORANGE, COLOR_BLUE,
)
from key_sender import (
    KeyQueue, send_key_raw, send_key_down, send_key_up,
    VK_Q, VK_Z, VK_S, VK_A, VK_M, VK_1, VK_COMMA, VK_SLASH, VK_DOT,
    VK_RETURN, VK_BACK, VK_W, VK_PRIOR, VK_NEXT, VK_END,
)
from focus_checker import FocusChecker

# ──────────────────────────────────────────────────────────────────────
# 窗口尺寸与区域划分
# ──────────────────────────────────────────────────────────────────────
WIN_W, WIN_H = 400, 660
STATUS_H     = 70    # 顶部状态栏高度
MAIN_H       = 260   # 主显示区高度（档位条 + 文字）
CTRL_Y       = STATUS_H + MAIN_H   # 操作区起始 y
CTRL_H       = WIN_H - CTRL_Y      # 操作区高度 ≈ 230px
BAR_W        = 120   # 左侧档位条宽度

# ──────────────────────────────────────────────────────────────────────
# 颜色
# ──────────────────────────────────────────────────────────────────────
COLOR_PANEL   = (45,  45,  52)
COLOR_BORDER  = (70,  70,  80)
COLOR_DIM     = (90,  90, 100)
COLOR_YELLOW  = (255, 210,  50)
COLOR_EB_BG   = (100,  20,  20)
COLOR_HILIGHT = (255, 255, 255)
COLOR_BTN     = (60,  60,  72)
COLOR_BTN_HOV = (80,  80,  95)
COLOR_BTN_ACT = (40, 100,  60)

# ──────────────────────────────────────────────────────────────────────
# Config / vehicles
# ──────────────────────────────────────────────────────────────────────
APP_NAME = "JRETS-NotchBrige"


def get_resource_base():
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


def get_appdata_dir():
    base = os.environ.get("APPDATA")
    if not base:
        base = os.path.expanduser("~")
    return os.path.join(base, APP_NAME)


RESOURCE_BASE = get_resource_base()
APPDATA_DIR   = get_appdata_dir()
CONFIG_PATH   = os.path.join(APPDATA_DIR, "config.json")
VEHICLES_PATH = os.path.join(APPDATA_DIR, "vehicles.json")
LEGACY_CONFIG_PATH   = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
LEGACY_VEHICLES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vehicles.json")
DEFAULT_VEHICLES_PATH = os.path.join(RESOURCE_BASE, "vehicles.json")

DEFAULT_CONFIG = {
    "selected_vehicle": "E233-1000\uff08\u4eac\u6ee8\u4e1c\u5317\u30fb\u6839\u5cb8\u7ebf\uff09",
    "joystick_index": 0,
    "axis_index": 0,
    "axis_invert": False,
    "deadzone": 0.05,
    "key_interval_ms": 100,
    "poll_hz": 30,
    "button_neutral": 3,
    "button_eb": 0,
    "button_resync": 7,
    "axis_mapping_mode": "linear",
    "axis_calibration": {},
    "axis2_index": 1,
    "axis_dual_average": False,
    "axis_eb_enabled": False,
    "axis_eb_threshold": 0.95,
    "game_process_name": "JREAST_TrainSimulator.exe",
    "game_window_title": "JREAST_TrainSimulator",
    "button_horn": -1,
    "button_skip_stop": -1,
    "button_cruise": -1,
    "button_depart_music": -1,
    "button_announce": -1,
    "button_stop_announce": -1,
    "plugin_enabled": False,
}


def ensure_appdata_files():
    os.makedirs(APPDATA_DIR, exist_ok=True)

    if not os.path.exists(VEHICLES_PATH):
        if os.path.exists(LEGACY_VEHICLES_PATH):
            shutil.copy2(LEGACY_VEHICLES_PATH, VEHICLES_PATH)
        elif os.path.exists(DEFAULT_VEHICLES_PATH):
            shutil.copy2(DEFAULT_VEHICLES_PATH, VEHICLES_PATH)

    if not os.path.exists(CONFIG_PATH) and os.path.exists(LEGACY_CONFIG_PATH):
        shutil.copy2(LEGACY_CONFIG_PATH, CONFIG_PATH)


def load_config():
    ensure_appdata_files()
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        cfg = {**DEFAULT_CONFIG, **data}
        cfg.setdefault("button_horn", -1)
        cfg.setdefault("button_skip_stop", -1)
        cfg.setdefault("button_stop_announce", -1)
        cfg.setdefault("axis2_index", 1)
        cfg.setdefault("axis_dual_average", False)
        # 迁移：修正旧版本遗留的错误进程名
        if cfg.get("game_process_name", "").lower() in ("jreasttrainsimulator.exe",):
            cfg["game_process_name"] = "JREAST_TrainSimulator.exe"
        if cfg.get("game_window_title", "").lower() in ("jr east train simulator",):
            cfg["game_window_title"] = "JREAST_TrainSimulator"
        return cfg
    cfg = dict(DEFAULT_CONFIG)
    cfg.update({
        "selected_vehicle": "E233-1000（京滨东北・根岸线）",
        "button_horn": -1,
        "button_skip_stop": -1,
        "button_stop_announce": -1,
    })
    save_config(cfg)
    return cfg


def save_config(cfg):
    os.makedirs(APPDATA_DIR, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def load_vehicles():
    ensure_appdata_files()
    with open(VEHICLES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


# ──────────────────────────────────────────────────────────────────────
# Font
# ──────────────────────────────────────────────────────────────────────
def load_font(size):
    for path in [
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/msyhbd.ttc",
        "C:/Windows/Fonts/simhei.ttf",
        "C:/Windows/Fonts/simsun.ttc",
    ]:
        if os.path.exists(path):
            return pygame.font.Font(path, size)
    return pygame.font.SysFont("Arial", size)


# ──────────────────────────────────────────────────────────────────────
# Drawing helpers
# ──────────────────────────────────────────────────────────────────────
def draw_text(surf, font, text, color, x, y, anchor="topleft"):
    img = font.render(text, True, color)
    rect = img.get_rect()
    if anchor == "topleft":
        rect.topleft = (x, y)
    elif anchor == "topright":
        rect.topright = (x, y)
    elif anchor == "center":
        rect.center = (x, y)
    surf.blit(img, rect)
    return rect.width


def fit_text(font, text, max_width):
    if font.size(text)[0] <= max_width:
        return text
    ellipsis = "..."
    lo, hi = 0, len(text)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        candidate = text[:mid] + ellipsis
        if font.size(candidate)[0] <= max_width:
            lo = mid
        else:
            hi = mid - 1
    return text[:lo] + ellipsis


def draw_tooltip(surf, font, text, x, y):
    pad = 6
    tw, th = font.size(text)
    box_w = tw + pad * 2
    box_h = th + pad * 2
    box_x = min(x, WIN_W - box_w - 8)
    box_y = max(4, y - box_h - 10)
    rect = pygame.Rect(box_x, box_y, box_w, box_h)
    pygame.draw.rect(surf, (28, 28, 34), rect, border_radius=5)
    pygame.draw.rect(surf, COLOR_BORDER, rect, 1, border_radius=5)
    draw_text(surf, font, text, COLOR_WHITE, rect.x + pad, rect.y + pad)


def draw_button(surf, font, text, rect, hover=False, active=False, disabled=False):
    color = COLOR_DIM if disabled else (COLOR_BTN_ACT if active else (COLOR_BTN_HOV if hover else COLOR_BTN))
    pygame.draw.rect(surf, color, rect, border_radius=5)
    border = COLOR_DIM if disabled else (COLOR_GREEN if active else COLOR_BORDER)
    pygame.draw.rect(surf, border, rect, 1, border_radius=5)
    tc = COLOR_DIM if disabled else COLOR_WHITE
    draw_text(surf, font, text, tc, rect.centerx, rect.centery, anchor="center")


def draw_led(surf, x, y, color, r=5):
    pygame.draw.circle(surf, color, (x, y), r)
    pygame.draw.circle(surf, (255, 255, 255, 60), (x, y), r, 1)


def draw_checkbox(surf, font, label, rect, checked, hover=False):
    box = pygame.Rect(rect.x, rect.y + (rect.height - 14) // 2, 14, 14)
    bg = COLOR_BTN_HOV if hover else COLOR_BTN
    pygame.draw.rect(surf, bg, box, border_radius=2)
    pygame.draw.rect(surf, COLOR_BORDER, box, 1, border_radius=2)
    if checked:
        pygame.draw.line(surf, COLOR_GREEN, (box.x+2, box.centery), (box.x+5, box.y+box.h-3), 2)
        pygame.draw.line(surf, COLOR_GREEN, (box.x+5, box.y+box.h-3), (box.x+12, box.y+2), 2)
    draw_text(surf, font, label, COLOR_WHITE, box.right + 5, rect.y + (rect.height - font.get_height()) // 2)


# ──────────────────────────────────────────────────────────────────────
# AxisMonitorPanel — 嵌入主显示区的轴监视子模式
# ──────────────────────────────────────────────────────────────────────
class AxisMonitorPanel:
    def __init__(self):
        self.prev_vals = {}
        self.max_delta_axis = None
        self.selected_axis = 0
        self.selected_axis2 = 1
        self.target = "main"

    def tick(self, js):
        if js is None:
            return
        deltas = {}
        for i in range(js.get_numaxes()):
            cur = js.get_axis(i)
            prev = self.prev_vals.get(i, cur)
            deltas[i] = abs(cur - prev)
            self.prev_vals[i] = cur
        if deltas:
            self.max_delta_axis = max(deltas, key=deltas.get)

    def confirm_selection(self):
        """按 Enter 时将高亮轴设为选中轴，返回轴编号。"""
        if self.max_delta_axis is not None:
            if self.target == "sub":
                self.selected_axis2 = self.max_delta_axis
            else:
                self.selected_axis = self.max_delta_axis
            return self.max_delta_axis
        return None

    def toggle_target(self):
        self.target = "sub" if self.target == "main" else "main"

    def draw(self, surf, fonts, rect, js):
        """在 rect 区域内绘制轴监视内容。"""
        font = fonts["sm"]
        x, y = rect.x + 10, rect.y + 8

        if js is None:
            draw_text(surf, font, "未检测到手柄", COLOR_RED, x, y)
            return

        target_label = "副轴" if self.target == "sub" else "主轴"
        draw_text(surf, font, f"拨动摇杆高亮轴；Tab切换目标；Enter 设为{target_label}", COLOR_YELLOW, x, y)
        y += 22

        row_h = 30
        bar_w = rect.width - 130
        for i in range(js.get_numaxes()):
            val = self.prev_vals.get(i, 0.0)
            is_max = (i == self.max_delta_axis)
            is_main = (i == self.selected_axis)
            is_sub = (i == self.selected_axis2)
            is_sel = is_main or is_sub

            row_rect = pygame.Rect(rect.x + 4, y - 3, rect.width - 8, row_h - 2)
            if is_max:
                pygame.draw.rect(surf, (60, 55, 10), row_rect, border_radius=3)
            elif is_sel:
                pygame.draw.rect(surf, (15, 45, 25), row_rect, border_radius=3)

            markers = []
            if is_main:
                markers.append("主")
            if is_sub:
                markers.append("副")
            label = f"轴{i}" + (f" [{' '.join(markers)}]" if markers else "")
            draw_text(surf, font, label, COLOR_YELLOW if is_max else COLOR_WHITE, x, y + 2)

            bx = x + 48
            by = y + (row_h - 10) // 2
            pygame.draw.rect(surf, COLOR_BORDER, (bx, by, bar_w, 10), border_radius=2)
            mid = bx + bar_w // 2
            fill = int(abs(val) * (bar_w // 2))
            col = COLOR_ORANGE
            if val >= 0:
                pygame.draw.rect(surf, col, (mid, by, fill, 10), border_radius=1)
            else:
                pygame.draw.rect(surf, col, (mid - fill, by, fill, 10), border_radius=1)
            pygame.draw.line(surf, COLOR_GRAY, (mid, by), (mid, by + 10))

            draw_text(surf, font, f"{val:+.3f}", COLOR_WHITE, bx + bar_w + 6, y + 2)
            y += row_h
            if y + row_h > rect.bottom - 4:
                break


# ──────────────────────────────────────────────────────────────────────
# CalibrationPanel — 轴标定（模式 B：分段线性映射）
# ──────────────────────────────────────────────────────────────────────
class CalibrationPanel:
    """
    嵌入主显示区的标定面板。
    - ↑↓ 键选择目标档位
    - Enter：将当前轴值记录为该档位的标定值
    - Del/Backspace：清除该档位的标定值
    - 面板内还有 [切换映射模式] 和 [清除全部] 按钮
    """

    def __init__(self):
        self.cursor = 0          # 当前选中的档位索引
        self.scroll = 0          # 滚动偏移（显示行数有限时）
        self._clickables: list[tuple[str, pygame.Rect]] = []

    def reset_cursor(self, total):
        self.cursor = min(self.cursor, total - 1)
        self.scroll = 0

    # ── 键盘事件 ──────────────────────────────────────────────────────
    def handle_key(self, event, names, calibration: dict, js, axis_index: int) -> str | None:
        """返回 "done" 表示退出标定模式，否则返回 None。"""
        total = len(names)

        if event.key == pygame.K_UP:
            self.cursor = max(0, self.cursor - 1)
        elif event.key == pygame.K_DOWN:
            self.cursor = min(total - 1, self.cursor + 1)

        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            if js is not None:
                val = js.get_axis(axis_index)
                calibration[str(self.cursor)] = round(val, 5)
        elif event.key in (pygame.K_DELETE, pygame.K_BACKSPACE):
            calibration.pop(str(self.cursor), None)
        elif event.key == pygame.K_ESCAPE:
            return "done"
        return None

    # ── 鼠标点击 ──────────────────────────────────────────────────────
    def handle_click(self, pos, names, calibration: dict,
                     js, axis_index: int, cfg: dict, save_fn) -> str | None:
        for cid, rect in self._clickables:
            if rect.collidepoint(pos):
                if cid == "done":
                    return "done"
                elif cid == "clear_all":
                    calibration.clear()
                    save_fn(cfg)
                elif cid == "toggle_mode":
                    if cfg["axis_mapping_mode"] == "segmented":
                        cfg["axis_mapping_mode"] = "linear"
                    else:
                        cfg["axis_mapping_mode"] = "segmented"
                    save_fn(cfg)
                elif cid.startswith("row_"):
                    idx = int(cid[4:])
                    self.cursor = idx
                    # 双击效果：直接设定
                    if js is not None:
                        val = js.get_axis(axis_index)
                        calibration[str(idx)] = round(val, 5)
                        save_fn(cfg)
        return None

    # ── 绘制 ──────────────────────────────────────────────────────────
    def draw(self, surf, fonts, rect, names, calibration: dict,
             js, axis_index: int, cfg: dict):
        self._clickables = []
        fn  = fonts["sm"]
        fmd = fonts["md"]
        x, y = rect.x + 10, rect.y + 8
        w = rect.width - 20

        # 标题行
        draw_text(surf, fmd, "【轴标定】", COLOR_GREEN, x, y)
        mode_label = "当前: 分段映射 ✓" if cfg["axis_mapping_mode"] == "segmented" else "当前: 均匀映射"
        mode_color = COLOR_GREEN if cfg["axis_mapping_mode"] == "segmented" else COLOR_ORANGE
        draw_text(surf, fn, mode_label, mode_color, x + 90, y + 4)
        y += 28

        # 当前轴值实时显示
        if js is not None:
            av = js.get_axis(axis_index)
            draw_text(surf, fn, f"轴 {axis_index} 当前值: {av:+.4f}", COLOR_YELLOW, x, y)
            bx, by2 = x, y + 18
            bar_w = w
            pygame.draw.rect(surf, COLOR_BORDER, (bx, by2, bar_w, 8), border_radius=2)
            mid = bx + bar_w // 2
            fill = int(abs(av) * (bar_w // 2))
            if av >= 0:
                pygame.draw.rect(surf, COLOR_ORANGE, (mid, by2, fill, 8), border_radius=1)
            else:
                pygame.draw.rect(surf, COLOR_ORANGE, (mid - fill, by2, fill, 8), border_radius=1)
            pygame.draw.line(surf, COLOR_GRAY, (mid, by2), (mid, by2 + 8))
        else:
            draw_text(surf, fn, "无手柄", COLOR_RED, x, y)
        y += 32

        # 操作提示
        draw_text(surf, fn, "↑↓选择  Enter记录  Del清除  点击行直接记录", COLOR_DIM, x, y)
        y += 20

        # 档位列表
        total     = len(names)
        row_h     = 22
        max_rows  = (rect.bottom - y - 40) // row_h

        # 自动滚动使 cursor 可见
        if self.cursor < self.scroll:
            self.scroll = self.cursor
        elif self.cursor >= self.scroll + max_rows:
            self.scroll = self.cursor - max_rows + 1

        for i in range(self.scroll, min(self.scroll + max_rows, total)):
            name = names[i]
            key  = str(i)
            cal_val = calibration.get(key)
            is_cur = (i == self.cursor)

            row_rect = pygame.Rect(rect.x + 4, y - 2, rect.width - 8, row_h)
            if is_cur:
                pygame.draw.rect(surf, (40, 70, 40), row_rect, border_radius=3)

            # 颜色块
            nc = notch_color(name)
            pygame.draw.rect(surf, nc, (x, y + 4, 10, 12), border_radius=2)

            # 档位名
            draw_text(surf, fn, name, COLOR_WHITE if is_cur else COLOR_GRAY, x + 16, y + 2)

            # 标定值或状态
            if cal_val is not None:
                draw_text(surf, fn, f"{cal_val:+.4f}", COLOR_GREEN, x + 60, y + 2)
            else:
                draw_text(surf, fn, "未标定", COLOR_DIM, x + 60, y + 2)

            # 选中行箭头
            if is_cur:
                draw_text(surf, fn, "◄ Enter记录", COLOR_YELLOW, x + 130, y + 2)

            self._clickables.append((f"row_{i}", row_rect))
            y += row_h

        # 底部按钮行
        by_btn = rect.bottom - 30
        mode_btn_label = "切换→均匀映射" if cfg["axis_mapping_mode"] == "segmented" else "切换→分段映射"
        b1 = pygame.Rect(rect.x + 4, by_btn, 110, 24)
        b2 = pygame.Rect(rect.x + 120, by_btn, 80, 24)
        b3 = pygame.Rect(rect.x + 206, by_btn, 60, 24)

        hov_mode  = b1.collidepoint(pygame.mouse.get_pos())
        hov_clear = b2.collidepoint(pygame.mouse.get_pos())
        hov_done  = b3.collidepoint(pygame.mouse.get_pos())

        draw_button(surf, fn, mode_btn_label, b1, hover=hov_mode,
                    active=(cfg["axis_mapping_mode"] == "segmented"))
        draw_button(surf, fn, "清除全部", b2, hover=hov_clear)
        draw_button(surf, fn, "完成", b3, hover=hov_done, active=True)

        self._clickables += [("toggle_mode", b1), ("clear_all", b2), ("done", b3)]


# ──────────────────────────────────────────────────────────────────────
# SelectOverlay — 车辆/设备选择覆盖层
# ──────────────────────────────────────────────────────────────────────
class SelectOverlay:
    def __init__(self, title, items):
        self.title   = title
        self.items   = items
        self.cursor  = 0

    def handle_key(self, event):
        if event.key == pygame.K_UP:
            self.cursor = (self.cursor - 1) % len(self.items)
        elif event.key == pygame.K_DOWN:
            self.cursor = (self.cursor + 1) % len(self.items)
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            return "confirm"
        elif event.key == pygame.K_ESCAPE:
            return "cancel"
        return None

    def draw(self, surf, fonts):
        # 半透明遮罩
        overlay = pygame.Surface((WIN_W, WIN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        surf.blit(overlay, (0, 0))

        item_h = 36
        pad    = 20
        list_h = min(len(self.items), 8) * item_h + 60
        box    = pygame.Rect(pad, (WIN_H - list_h) // 2, WIN_W - pad * 2, list_h)

        pygame.draw.rect(surf, COLOR_PANEL, box, border_radius=8)
        pygame.draw.rect(surf, COLOR_BORDER, box, 1, border_radius=8)

        draw_text(surf, fonts["md"], self.title, COLOR_WHITE,
                  box.centerx, box.y + 14, anchor="center")

        y = box.y + 44
        for i, item in enumerate(self.items[:8]):
            row = pygame.Rect(box.x + 8, y, box.width - 16, item_h - 4)
            if i == self.cursor:
                pygame.draw.rect(surf, COLOR_BTN_ACT, row, border_radius=4)
            draw_text(surf, fonts["sm"], item,
                      COLOR_WHITE if i == self.cursor else COLOR_GRAY,
                      row.x + 10, row.y + (item_h - 4 - fonts["sm"].get_height()) // 2)
            y += item_h

        draw_text(surf, fonts["sm"], "↑↓选择  Enter确认  Esc取消",
                  COLOR_DIM, box.centerx, box.bottom - 18, anchor="center")


# ──────────────────────────────────────────────────────────────────────
# App — 主应用
# ──────────────────────────────────────────────────────────────────────
class App:
    def __init__(self):
        # 允许 Pygame 窗口在后台（游戏聚焦时）仍然读取手柄轴值
        # 必须在 pygame.init() 之前设置
        os.environ.setdefault("SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS", "1")

        pygame.init()
        pygame.joystick.init()

        self.cfg      = load_config()
        self.vehicles = load_vehicles()
        self.veh_names = list(self.vehicles.keys())

        self.screen = pygame.display.set_mode((WIN_W, WIN_H))
        pygame.display.set_caption("JRETS Controller")
        self._set_always_on_top()

        self.fonts = {
            "sm": load_font(15),
            "md": load_font(19),
            "lg": load_font(34),
        }

        self.queue   = KeyQueue()
        self.focus   = FocusChecker(
            self.cfg["game_process_name"],
            self.cfg["game_window_title"],
        )
        self.clock   = pygame.time.Clock()

        # 控制状态
        self.current_notch:  int | None = None
        self.eb_active:      bool = False
        self.axis_eb_in_zone:bool = False
        self.game_focused:   bool = True
        self.syncing:        bool = False
        self.horn_held:      bool = False

        # UI 状态
        self.axis_monitor_active: bool = False
        self.axis_panel = AxisMonitorPanel()
        self.calibration_active: bool = False
        self.cal_panel = CalibrationPanel()
        self.overlay: SelectOverlay | None = None
        self.button_learn_target: str | None = None  # "neutral" / "eb" / "resync"
        self.interval_editing: bool = False

        # 鼠标悬停追踪
        self.hover_rect_id: str = ""

        # 可点击区域注册表（每帧重建）
        self._clickables: list[tuple[str, pygame.Rect]] = []

        self.js = self._init_joystick()

    # ── pygame 窗口置顶 ────────────────────────────────────────────────
    def _set_always_on_top(self):
        try:
            import win32gui, win32con
            hwnd = win32gui.FindWindow(None, "JRETS Controller")
            if hwnd:
                win32gui.SetWindowPos(
                    hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0,
                    win32con.SWP_NOMOVE | win32con.SWP_NOSIZE,
                )
        except Exception:
            pass

    # ── 手柄初始化 ─────────────────────────────────────────────────────
    def _init_joystick(self):
        idx = self.cfg["joystick_index"]
        if pygame.joystick.get_count() > idx:
            js = pygame.joystick.Joystick(idx)
            js.init()
            self.axis_panel.selected_axis = self.cfg["axis_index"]
            return js
        return None

    # ── 车辆配置快捷属性 ───────────────────────────────────────────────
    @property
    def vcfg(self):
        name = self.cfg["selected_vehicle"]
        return self.vehicles.get(name, list(self.vehicles.values())[0])

    @property
    def notch_names(self):
        v = self.vcfg
        return build_notch_names(v["power_notches"], v["brake_notches"], v["has_hb"])

    @property
    def control_type(self):
        return self.vcfg.get("control_type", "1-handle")

    @property
    def total_notches(self):
        return get_total_notches(self.vcfg)

    @property
    def n_index(self):
        """N 档在档位列表中的内部索引。"""
        try:
            return self.notch_names.index("N")
        except ValueError:
            return self.vcfg["brake_notches"] + (1 if self.vcfg["has_hb"] else 0)

    def _axis_value(self):
        js = self.js
        cfg = self.cfg
        if not js or js.get_numaxes() <= cfg["axis_index"]:
            return None
        primary = js.get_axis(cfg["axis_index"])
        if not cfg.get("axis_dual_average", False):
            return primary
        axis2 = cfg.get("axis2_index", cfg["axis_index"])
        if js.get_numaxes() <= axis2:
            return primary
        return (primary + js.get_axis(axis2)) / 2.0

    # ── 归位同步 ────────────────────────────────────────────────────────
    def trigger_resync(self):
        self.queue.clear()
        if self.control_type == "2-handle":
            self.queue.push([VK_S] + [VK_DOT] * (self.vcfg["brake_notches"] + 2))
        else:
            total = self.total_notches
            self.queue.push([VK_Q] * (total + 2))
        self.current_notch = 0
        self.syncing       = True
        self.eb_active     = False

    # ── EB 触发 ─────────────────────────────────────────────────────────
    def trigger_eb(self):
        self.queue.push_urgent(VK_SLASH if self.control_type == "2-handle" else VK_1)
        self.eb_active = True
        # EB 后游戏档位已跳至紧急制动，当前追踪值失效，强制重新归位同步
        self.current_notch = None

    # ── N 档直跳 ────────────────────────────────────────────────────────
    def trigger_neutral(self):
        if self.control_type == "2-handle":
            self.queue.clear()
            self.queue.push([VK_M, VK_S])
        else:
            self.queue.push_urgent(VK_S)
        if self.current_notch is not None:
            self.current_notch = self.n_index
        self.eb_active = False

    def _build_transition_keys(self, current: int, target: int) -> list[int]:
        if self.control_type != "2-handle":
            diff = target - current
            return [VK_Z] * diff if diff > 0 else [VK_Q] * abs(diff)

        n = self.n_index
        if current == target:
            return []
        if current == n:
            if target < n:
                return [VK_DOT] * (n - target)
            return [VK_Z] * (target - n)
        if target == n:
            return [VK_M] if current < n else [VK_S]
        if current < n and target < n:
            diff = target - current
            return [VK_COMMA] * diff if diff > 0 else [VK_DOT] * abs(diff)
        if current > n and target > n:
            diff = target - current
            return [VK_Z] * diff if diff > 0 else [VK_A] * abs(diff)
        if current < n and target > n:
            return [VK_M] + [VK_Z] * (target - n)
        return [VK_S] + [VK_DOT] * (n - target)

    # ──────────────────────────────────────────────────────────────────
    # 主循环
    # ──────────────────────────────────────────────────────────────────
    def run(self):
        fps = self.cfg.get("poll_hz", 30)
        running = True
        last_js_count = pygame.joystick.get_count()

        while running:
            # ── 手柄热插拔检测（仅数量变化时重新初始化）──────────
            cur_js_count = pygame.joystick.get_count()
            if cur_js_count != last_js_count:
                last_js_count = cur_js_count
                self.js = self._init_joystick()

            mouse_pos = pygame.mouse.get_pos()

            # ── 事件处理 ───────────────────────────────────────────
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    if self.horn_held:
                        send_key_up(VK_BACK)
                        self.horn_held = False
                    running = False

                elif event.type == pygame.KEYDOWN:
                    if self.overlay:
                        result = self.overlay.handle_key(event)
                        if result == "confirm":
                            self._overlay_confirm()
                        elif result == "cancel":
                            self.overlay = None
                    elif self.button_learn_target:
                        if event.key == pygame.K_ESCAPE:
                            self.button_learn_target = None
                    elif self.calibration_active:
                        names = self.notch_names
                        cal   = self.cfg["axis_calibration"]
                        result = self.cal_panel.handle_key(
                            event, names, cal, self.js, self.cfg["axis_index"]
                        )
                        if result == "done":
                            self.calibration_active = False
                            save_config(self.cfg)
                        else:
                            save_config(self.cfg)  # 每次记录都即时保存
                    elif self.axis_monitor_active:
                        if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                            ax = self.axis_panel.confirm_selection()
                            if ax is not None:
                                if self.axis_panel.target == "sub":
                                    self.cfg["axis2_index"] = ax
                                else:
                                    self.cfg["axis_index"] = ax
                                save_config(self.cfg)
                        elif event.key == pygame.K_TAB:
                            self.axis_panel.toggle_target()
                        elif event.key == pygame.K_ESCAPE:
                            self.axis_monitor_active = False
                    elif self.interval_editing:
                        if event.key == pygame.K_LEFT:
                            self.cfg["key_interval_ms"] = max(20, self.cfg["key_interval_ms"] - 10)
                            save_config(self.cfg)
                        elif event.key == pygame.K_RIGHT:
                            self.cfg["key_interval_ms"] = min(500, self.cfg["key_interval_ms"] + 10)
                            save_config(self.cfg)
                        elif event.key == pygame.K_ESCAPE:
                            self.interval_editing = False
                    else:
                        if event.key == pygame.K_ESCAPE:
                            running = False

                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if not self.overlay:
                        if self.calibration_active:
                            names = self.notch_names
                            cal   = self.cfg["axis_calibration"]
                            result = self.cal_panel.handle_click(
                                event.pos, names, cal,
                                self.js, self.cfg["axis_index"],
                                self.cfg, save_config,
                            )
                            if result == "done":
                                self.calibration_active = False
                                save_config(self.cfg)
                        else:
                            self._handle_click(event.pos)

                # 手柄按钮事件
                elif event.type == pygame.JOYBUTTONDOWN:
                    self._handle_joy_button(event.button)
                elif event.type == pygame.JOYBUTTONUP:
                    self._handle_joy_button_up(event.button)

            # ── 帧逻辑 ─────────────────────────────────────────────
            self._frame_logic()

            # ── 渲染 ───────────────────────────────────────────────
            self._draw(mouse_pos)
            pygame.display.flip()
            self.clock.tick(fps)

        save_config(self.cfg)
        if self.horn_held:
            send_key_up(VK_BACK)
            self.horn_held = False
        pygame.quit()
        sys.exit(0)

    # ──────────────────────────────────────────────────────────────────
    # 帧逻辑（按 Design.md §5）
    # ──────────────────────────────────────────────────────────────────
    def _frame_logic(self):
        # 后台运行时手动 pump，确保手柄轴值始终是最新状态
        pygame.event.pump()

        js  = self.js
        cfg = self.cfg

        # 轴监视面板每帧更新
        if js:
            self.axis_panel.tick(js)

        # syncing 完成检测
        if self.syncing and len(self.queue) == 0:
            self.syncing = False

        # ── 2. EB 检测（最高优先级）──────────────────────────────
        axis_val = self._axis_value()
        axis_for_eb = axis_val if axis_val is not None else 0.0
        eb_thresh = cfg["axis_eb_threshold"]
        eb_normalized = (-axis_for_eb + 1.0) / 2.0 if not cfg["axis_invert"] else (axis_for_eb + 1.0) / 2.0

        if cfg["axis_eb_enabled"] and eb_normalized > eb_thresh:
            if not self.axis_eb_in_zone:
                self.axis_eb_in_zone = True
                self.trigger_eb()
        else:
            if self.axis_eb_in_zone:
                self.axis_eb_in_zone = False
                self.eb_active = False   # 退出 EB 区域，解除 EB 显示

        # ── 4. 焦点检测 ─────────────────────────────────────────
        self.game_focused = self.focus.tick()
        if not self.game_focused:
            self.queue.clear()
            if self.horn_held:
                send_key_up(VK_BACK)
                self.horn_held = False
            return

        # ── EB 优先处理：先发 DOT 键，发完后解除 EB 状态 ────────
        if self.eb_active:
            self.queue.tick(cfg["key_interval_ms"])
            # 按钮触发的 EB（非轴末端）：DOT 发完后解除 eb_active 标志
            if not self.axis_eb_in_zone and len(self.queue) == 0:
                self.eb_active = False
            return

        # ── 5. 轴值 → 目标档位 ──────────────────────────────────
        if axis_val is not None:
            if (cfg["axis_mapping_mode"] == "segmented"
                    and len(cfg.get("axis_calibration", {})) >= 2):
                target = axis_to_notch_calibrated(
                    axis_val,
                    cfg["axis_calibration"],
                    self.total_notches,
                )
            else:
                target = axis_to_notch(axis_val, self.total_notches,
                                       cfg["axis_invert"], cfg["deadzone"])
        else:
            target = None

        # ── 6. 未同步时跳过 ─────────────────────────────────────
        if self.current_notch is None:
            self.queue.tick(cfg["key_interval_ms"])
            return

        # ── 7. 计算差量，填充队列 ────────────────────────────────
        # 注意：不在此处更新 current_notch；由步骤8每发一键更新一步，
        # 确保焦点丢失导致队列被清空时 current_notch 仍与游戏实际档位吻合。
        if target is not None and target != self.current_notch and len(self.queue) == 0:
            self.queue.push(self._build_transition_keys(self.current_notch, target))

        # ── 8. 发送一个按键，同步更新 current_notch ─────────────
        sent = self.queue.tick(cfg["key_interval_ms"])
        if sent and self.current_notch is not None:
            vk = self.queue.last_sent_vk
            total = self.total_notches
            if vk == VK_Z:
                self.current_notch = min(total - 1, self.current_notch + 1)
            elif vk == VK_Q:
                self.current_notch = max(0, self.current_notch - 1)
            elif vk == VK_DOT and self.control_type == "2-handle":
                self.current_notch = max(0, self.current_notch - 1)
            elif vk == VK_COMMA and self.control_type == "2-handle":
                self.current_notch = min(self.n_index, self.current_notch + 1)
            elif vk in (VK_M, VK_S) and self.control_type == "2-handle":
                self.current_notch = self.n_index if self.current_notch != self.n_index else self.current_notch
            elif vk == VK_A and self.control_type == "2-handle":
                self.current_notch = max(self.n_index, self.current_notch - 1)

    # ──────────────────────────────────────────────────────────────────
    # 手柄按钮处理
    # ──────────────────────────────────────────────────────────────────
    def _handle_joy_button(self, btn: int):
        cfg = self.cfg

        # 按钮学习模式
        if self.button_learn_target:
            key_map = {
                "neutral":      "button_neutral",
                "eb":           "button_eb",
                "resync":       "button_resync",
                "horn":         "button_horn",
                "skip_stop":    "button_skip_stop",
                "cruise":       "button_cruise",
                "depart_music": "button_depart_music",
                "announce":     "button_announce",
                "stop_announce": "button_stop_announce",
            }
            cfg_key = key_map.get(self.button_learn_target)
            if cfg_key:
                cfg[cfg_key] = btn
                save_config(cfg)
            self.button_learn_target = None
            return

        # EB 按钮（最高优先级）
        if btn == cfg["button_eb"]:
            self.trigger_eb()
            return

        # N 档按钮
        if btn == cfg["button_neutral"]:
            self.trigger_neutral()
            return

        # 归位同步按钮
        if btn == cfg["button_resync"]:
            self.trigger_resync()
            return

        # ── 扩展功能按键（仅在游戏聚焦时触发）────────────────────
        if not self.game_focused:
            return

        # 定速巡航 → W（hold 50ms 确保游戏轮询捕获到按下状态）
        if cfg["button_cruise"] != -1 and btn == cfg["button_cruise"]:
            send_key_raw(VK_W, hold_ms=50)
            return

        if cfg.get("button_horn", -1) != -1 and btn == cfg["button_horn"]:
            if not self.horn_held:
                send_key_down(VK_BACK)
                self.horn_held = True
            return

        if cfg.get("button_skip_stop", -1) != -1 and btn == cfg["button_skip_stop"]:
            send_key_raw(VK_RETURN, hold_ms=50)
            return

        # 发车音乐 → Page Up（扩展键 + hold 50ms；需插件按键已启用）
        if (cfg.get("plugin_enabled", False)
                and cfg["button_depart_music"] != -1
                and btn == cfg["button_depart_music"]):
            send_key_raw(VK_PRIOR, hold_ms=50)
            return

        # 下一站报站 → Page Down（扩展键 + hold 50ms；需插件按键已启用）
        if (cfg.get("plugin_enabled", False)
                and cfg["button_announce"] != -1
                and btn == cfg["button_announce"]):
            send_key_raw(VK_NEXT, hold_ms=50)
            return

        if (cfg.get("plugin_enabled", False)
                and cfg.get("button_stop_announce", -1) != -1
                and btn == cfg["button_stop_announce"]):
            send_key_raw(VK_END, hold_ms=50)
            return

    def _handle_joy_button_up(self, btn: int):
        cfg = self.cfg
        if cfg.get("button_horn", -1) != -1 and btn == cfg["button_horn"] and self.horn_held:
            send_key_up(VK_BACK)
            self.horn_held = False

    # ──────────────────────────────────────────────────────────────────
    # 鼠标点击处理
    # ──────────────────────────────────────────────────────────────────
    def _handle_click(self, pos):
        for cid, rect in self._clickables:
            if rect.collidepoint(pos):
                self._on_click(cid)
                return

    def _on_click(self, cid: str):
        cfg = self.cfg
        vnames = self.veh_names

        if cid == "btn_vehicle":
            self.overlay = SelectOverlay("选择车辆", vnames)
            self.overlay.cursor = vnames.index(cfg["selected_vehicle"]) if cfg["selected_vehicle"] in vnames else 0

        elif cid == "btn_device":
            devices = [f"[{i}] {pygame.joystick.Joystick(i).get_name()}"
                       for i in range(pygame.joystick.get_count())]
            if not devices:
                devices = ["(无设备)"]
            self.overlay = SelectOverlay("选择设备", devices)
            self.overlay.cursor = cfg["joystick_index"] if cfg["joystick_index"] < len(devices) else 0
            self.overlay._mode = "device"

        elif cid == "btn_resync":
            self.trigger_resync()

        elif cid == "btn_axis_monitor":
            self.axis_monitor_active = not self.axis_monitor_active
            self.calibration_active  = False
            self.axis_panel.selected_axis = cfg["axis_index"]
            self.axis_panel.selected_axis2 = cfg.get("axis2_index", 1)

        elif cid == "btn_calibration":
            self.calibration_active  = not self.calibration_active
            self.axis_monitor_active = False
            if self.calibration_active:
                self.cal_panel.reset_cursor(self.total_notches)

        elif cid == "chk_invert":
            cfg["axis_invert"] = not cfg["axis_invert"]
            save_config(cfg)

        elif cid == "chk_axiseb":
            cfg["axis_eb_enabled"] = not cfg["axis_eb_enabled"]
            save_config(cfg)

        elif cid == "chk_dualavg":
            cfg["axis_dual_average"] = not cfg.get("axis_dual_average", False)
            save_config(cfg)

        elif cid == "btn_neutral_map":
            self.button_learn_target = "neutral"

        elif cid == "btn_eb_map":
            self.button_learn_target = "eb"

        elif cid == "btn_resync_map":
            self.button_learn_target = "resync"

        elif cid == "btn_horn_map":
            self.button_learn_target = "horn"

        elif cid == "btn_skip_stop_map":
            self.button_learn_target = "skip_stop"

        elif cid == "btn_cruise_map":
            self.button_learn_target = "cruise"

        elif cid == "btn_depart_music_map":
            self.button_learn_target = "depart_music"

        elif cid == "btn_announce_map":
            self.button_learn_target = "announce"

        elif cid == "btn_stop_announce_map":
            self.button_learn_target = "stop_announce"

        elif cid == "chk_plugin":
            cfg["plugin_enabled"] = not cfg.get("plugin_enabled", False)
            save_config(cfg)

        elif cid.startswith("clear_"):
            # "clear_neutral" → "button_neutral"，其余同理
            cfg_key = "button_" + cid[len("clear_"):]
            if cfg_key in cfg:
                cfg[cfg_key] = -1
                save_config(cfg)

        elif cid == "btn_interval":
            self.interval_editing = not self.interval_editing

    def _overlay_confirm(self):
        if self.overlay is None:
            return
        mode = getattr(self.overlay, "_mode", "vehicle")
        if mode == "device":
            idx = self.overlay.cursor
            self.cfg["joystick_index"] = idx
            save_config(self.cfg)
            self.js = self._init_joystick()
        else:
            self.cfg["selected_vehicle"] = self.veh_names[self.overlay.cursor]
            save_config(self.cfg)
            # 切换车辆后重置同步状态
            self.current_notch = None
            self.syncing = False
        self.overlay = None

    # ──────────────────────────────────────────────────────────────────
    # 渲染
    # ──────────────────────────────────────────────────────────────────
    def _draw(self, mouse_pos):
        self._clickables = []
        surf = self.screen
        surf.fill(COLOR_BG)

        self._draw_status_bar(surf, mouse_pos)
        self._draw_divider(surf, STATUS_H)

        if self.calibration_active:
            cal_rect = pygame.Rect(0, STATUS_H, WIN_W, MAIN_H)
            self.cal_panel.draw(
                surf, self.fonts, cal_rect,
                self.notch_names, self.cfg["axis_calibration"],
                self.js, self.cfg["axis_index"], self.cfg,
            )
        elif self.axis_monitor_active:
            self._draw_axis_monitor(surf, mouse_pos)
        else:
            self._draw_main_display(surf, mouse_pos)

        self._draw_divider(surf, CTRL_Y)
        self._draw_controls(surf, mouse_pos)

        if self.button_learn_target:
            self._draw_learn_hint(surf)

        if self.interval_editing:
            self._draw_interval_hint(surf)

        if self.overlay:
            self.overlay.draw(surf, self.fonts)

    # ── 分割线 ─────────────────────────────────────────────────────────
    def _draw_divider(self, surf, y):
        pygame.draw.line(surf, COLOR_BORDER, (0, y), (WIN_W, y))

    # ── 顶部状态栏 ─────────────────────────────────────────────────────
    def _draw_status_bar(self, surf, mouse_pos):
        pygame.draw.rect(surf, COLOR_PANEL, (0, 0, WIN_W, STATUS_H))
        fn, fm = self.fonts["sm"], self.fonts["md"]

        vname = self.cfg["selected_vehicle"]
        jsname = self.js.get_name() if self.js else "\u65e0\u8bbe\u5907"

        right_x = WIN_W - 152
        left_w = right_x - 18

        vehicle_full = f"\u8f66\u8f86: {vname}"
        vehicle_shown = fit_text(fm, vehicle_full, left_w)
        draw_text(surf, fm, vehicle_shown, COLOR_WHITE, 12, 8)
        draw_text(surf, fn, fit_text(fn, f"\u8bbe\u5907: {jsname}", left_w), COLOR_GRAY, 12, 30)

        foc_color = COLOR_GREEN if self.game_focused else COLOR_GRAY
        foc_text = "\u25cf \u5df2\u805a\u7126" if self.game_focused else "\u25cf \u672a\u805a\u7126"
        if self.syncing:
            syn_color, syn_text = COLOR_YELLOW, "\u25cf \u540c\u6b65\u4e2d"
        elif self.current_notch is None:
            syn_color, syn_text = COLOR_RED, "\u25cf \u672a\u540c\u6b65"
        else:
            syn_color, syn_text = COLOR_GREEN, "\u25cf \u5df2\u540c\u6b65"

        draw_text(surf, fn, "\u6e38\u620f:", COLOR_DIM, right_x, 10)
        draw_text(surf, fn, foc_text, foc_color, right_x + 38, 10)
        draw_text(surf, fn, "\u540c\u6b65:", COLOR_DIM, right_x, 30)
        draw_text(surf, fn, syn_text, syn_color, right_x + 38, 30)

        if vehicle_shown != vehicle_full:
            hover_rect = pygame.Rect(12, 8, min(left_w, fm.size(vehicle_shown)[0]), fm.get_height())
            if hover_rect.collidepoint(mouse_pos):
                draw_tooltip(surf, fn, vehicle_full, mouse_pos[0] + 10, mouse_pos[1])

    def _draw_main_display(self, surf, mouse_pos):
        names  = self.notch_names
        total  = self.total_notches
        cur    = self.current_notch
        eb     = self.eb_active

        main_rect = pygame.Rect(0, STATUS_H, WIN_W, MAIN_H)

        # EB 状态：背景变红
        if eb:
            pygame.draw.rect(surf, COLOR_EB_BG, main_rect)

        # ── 左侧：竖向档位条 ──────────────────────────────────────
        bar_rect = pygame.Rect(0, STATUS_H, BAR_W, MAIN_H)
        self._draw_notch_bar(surf, bar_rect, names, cur, eb)

        # ── 右侧：文字区 ──────────────────────────────────────────
        text_x  = BAR_W + 14
        text_y  = STATUS_H + 30

        if eb:
            draw_text(surf, self.fonts["lg"], "EB",    COLOR_RED,   text_x, text_y)
            draw_text(surf, self.fonts["md"], "紧急制动", COLOR_RED, text_x, text_y + 44)
        elif cur is None:
            draw_text(surf, self.fonts["md"], "未同步", COLOR_GRAY, text_x, text_y + 20)
            draw_text(surf, self.fonts["sm"], "请先执行归位同步", COLOR_DIM, text_x, text_y + 50)
        else:
            name  = names[cur] if 0 <= cur < len(names) else "?"
            color = notch_color(name)
            desc  = notch_description(name)
            draw_text(surf, self.fonts["lg"], name,  color, text_x, text_y)
            draw_text(surf, self.fonts["md"], desc,  color, text_x, text_y + 44)
            draw_text(surf, self.fonts["sm"], f"{cur} / {total - 1}", COLOR_GRAY, text_x, text_y + 74)

            # 待发队列提示
            if len(self.queue) > 0:
                draw_text(surf, self.fonts["sm"],
                          f"发送中… {len(self.queue)} 键", COLOR_YELLOW, text_x, text_y + 100)

    # ── 竖向档位条 ─────────────────────────────────────────────────────
    def _draw_notch_bar(self, surf, rect, names, cur, eb_active):
        cfg = self.cfg
        total = len(names)
        pad   = 6
        x     = rect.x + pad
        avail_h = rect.height - pad * 2

        # 可选：顶部 EB 小块（轴末端 EB 开启时）
        eb_block_h = 0
        if cfg["axis_eb_enabled"]:
            eb_block_h = 18
            eb_rect = pygame.Rect(x, rect.y + pad, rect.width - pad * 2, eb_block_h - 2)
            pygame.draw.rect(surf, COLOR_RED if eb_active else (80, 30, 30), eb_rect, border_radius=3)
            draw_text(surf, self.fonts["sm"], "EB", COLOR_WHITE if eb_active else COLOR_DIM,
                      eb_rect.centerx, eb_rect.centery, anchor="center")
            avail_h -= eb_block_h

        cell_h = avail_h / total
        y0     = rect.y + pad + eb_block_h

        for i, name in enumerate(names):
            cell_y = int(y0 + i * cell_h)
            cell_rect = pygame.Rect(x, cell_y, rect.width - pad * 2, max(2, int(cell_h) - 1))

            if eb_active:
                color = COLOR_RED
            else:
                color = notch_color(name)

            # 暗底色
            dark = tuple(max(0, c - 100) for c in color)
            pygame.draw.rect(surf, dark, cell_rect, border_radius=2)

            # 当前档高亮
            if cur == i and not eb_active:
                pygame.draw.rect(surf, color, cell_rect, border_radius=2)
                pygame.draw.rect(surf, COLOR_HILIGHT, cell_rect, 2, border_radius=2)
            elif eb_active:
                pygame.draw.rect(surf, color, cell_rect, border_radius=2)

            # 档位名称（格子够大才显示）
            if cell_h >= 16:
                tc = COLOR_WHITE if (cur == i and not eb_active) else COLOR_DIM
                draw_text(surf, self.fonts["sm"], name,
                          tc, cell_rect.centerx, cell_rect.centery, anchor="center")

    # ── 轴监视子模式（占据整个主显示区）──────────────────────────────
    def _draw_axis_monitor(self, surf, mouse_pos):
        rect = pygame.Rect(0, STATUS_H, WIN_W, MAIN_H)
        self.axis_panel.draw(surf, self.fonts, rect, self.js)

        hint = "Esc 退出轴监视"
        draw_text(surf, self.fonts["sm"], hint, COLOR_DIM,
                  WIN_W - 10, STATUS_H + MAIN_H - 18, anchor="topright")

    # ── 按键映射控件辅助（标签 + [值] + [×]）─────────────────────────
    _LEARN_TARGET_MAP = {
        "btn_neutral_map":      "neutral",
        "btn_eb_map":           "eb",
        "btn_resync_map":       "resync",
        "btn_horn_map":         "horn",
        "btn_skip_stop_map":    "skip_stop",
        "btn_cruise_map":       "cruise",
        "btn_depart_music_map": "depart_music",
        "btn_announce_map":     "announce",
        "btn_stop_announce_map": "stop_announce",
    }

    def _draw_btn_map(self, surf, fn, mouse_pos, x, y, btn_h,
                      label, cfg_key, learn_cid, clear_cid, disabled=False,
                      label_w=78, value_w=34, clear_w=20):
        lbl_color = COLOR_DIM if disabled else COLOR_GRAY
        draw_text(surf, fn, label, lbl_color, x, y + 5)

        cfg_val  = self.cfg.get(cfg_key, -1)
        val_str  = "--" if cfg_val == -1 else str(cfg_val)
        is_learn = (self.button_learn_target == self._LEARN_TARGET_MAP.get(learn_cid))
        has_val  = (cfg_val != -1)

        val_x = x + label_w
        val_r = pygame.Rect(val_x, y, value_w, btn_h)
        clr_r = pygame.Rect(val_r.right + 2, y, clear_w, btn_h)

        hov_v = val_r.collidepoint(mouse_pos) and not disabled
        hov_c = clr_r.collidepoint(mouse_pos) and not disabled and has_val

        draw_button(surf, fn, val_str, val_r,
                    hover=hov_v, active=is_learn, disabled=disabled)
        draw_button(surf, fn, "x", clr_r,
                    hover=hov_c, disabled=not has_val)

        self._clickables.append((learn_cid, val_r))
        if has_val:
            self._clickables.append((clear_cid, clr_r))

        return label_w + value_w + 2 + clear_w

    def _draw_controls(self, surf, mouse_pos):
        fn = self.fonts["sm"]
        cfg = self.cfg

        pygame.draw.rect(surf, COLOR_PANEL, (0, CTRL_Y, WIN_W, CTRL_H))

        y = CTRL_Y + 8
        btn_w, btn_h = 110, 26
        gap = 8
        total_row_w = btn_w * 3 + gap * 2
        start_x = (WIN_W - total_row_w) // 2

        for i, (cid, label) in enumerate([
            ("btn_vehicle", "选择车辆"),
            ("btn_device", "选择设备"),
            ("btn_resync", "归位同步"),
        ]):
            r = pygame.Rect(start_x + i * (btn_w + gap), y, btn_w, btn_h)
            hov = r.collidepoint(mouse_pos)
            act = (cid == "btn_resync" and self.syncing)
            draw_button(surf, fn, label, r, hover=hov, active=act)
            self._clickables.append((cid, r))

        y += btn_h + 8

        x = 14
        draw_text(surf, fn, f"主轴: {cfg['axis_index']}", COLOR_GRAY, x, y + 5)
        x += 70

        chk_r = pygame.Rect(x, y, 75, btn_h)
        hov = chk_r.collidepoint(mouse_pos)
        draw_checkbox(surf, fn, "反转", chk_r, cfg["axis_invert"], hover=hov)
        self._clickables.append(("chk_invert", chk_r))
        x += 85

        am_r = pygame.Rect(x, y, 110, btn_h)
        hov = am_r.collidepoint(mouse_pos)
        act = self.axis_monitor_active
        draw_button(surf, fn, "轴监视模式", am_r, hover=hov, active=act)
        self._clickables.append(("btn_axis_monitor", am_r))

        y += btn_h + 8

        x = 14
        avg_r = pygame.Rect(x, y, 105, btn_h)
        hov = avg_r.collidepoint(mouse_pos)
        draw_checkbox(surf, fn, "双轴平均", avg_r, cfg.get("axis_dual_average", False), hover=hov)
        self._clickables.append(("chk_dualavg", avg_r))
        x += 120
        draw_text(surf, fn, f"副轴: {cfg.get('axis2_index', 1)}", COLOR_GRAY, x, y + 5)

        y += btn_h + 8

        col_x = [12, 204]
        row_gap = 4

        rows = [
            [('N档按钮', 'button_neutral', 'btn_neutral_map', 'clear_neutral'),
             ('EB按钮', 'button_eb', 'btn_eb_map', 'clear_eb')],
            [('归位按钮', 'button_resync', 'btn_resync_map', 'clear_resync'),
             ('鸣笛Bksp', 'button_horn', 'btn_horn_map', 'clear_horn')],
            [('跳停Enter', 'button_skip_stop', 'btn_skip_stop_map', 'clear_skip_stop'),
             ('定速(W)', 'button_cruise', 'btn_cruise_map', 'clear_cruise')],
        ]
        for row in rows:
            for cx, item in zip(col_x, row):
                self._draw_btn_map(surf, fn, mouse_pos, cx, y, btn_h, *item, label_w=82)
            y += btn_h + row_gap

        x = 14
        draw_text(surf, fn, "间隔:", COLOR_GRAY, x, y + 5)
        x += 38
        int_r = pygame.Rect(x, y, 58, btn_h)
        hov = int_r.collidepoint(mouse_pos)
        act = self.interval_editing
        draw_button(surf, fn, f"{cfg['key_interval_ms']}ms", int_r, hover=hov, active=act)
        self._clickables.append(("btn_interval", int_r))
        x += 66

        chk_eb_r = pygame.Rect(x, y, 98, btn_h)
        hov = chk_eb_r.collidepoint(mouse_pos)
        draw_checkbox(surf, fn, "轴末端EB", chk_eb_r, cfg["axis_eb_enabled"], hover=hov)
        self._clickables.append(("chk_axiseb", chk_eb_r))
        x += 106

        cal_r = pygame.Rect(x, y, 60, btn_h)
        hov_cal = cal_r.collidepoint(mouse_pos)
        act_cal = self.calibration_active
        draw_button(surf, fn, "标定", cal_r, hover=hov_cal, active=act_cal)
        self._clickables.append(("btn_calibration", cal_r))

        y += btn_h + 4
        pygame.draw.line(surf, COLOR_BORDER, (14, y), (WIN_W - 14, y))
        y += 6

        plugin_on = cfg.get("plugin_enabled", False)
        plugin_r = pygame.Rect(14, y, 108, btn_h)
        hov_plugin = plugin_r.collidepoint(mouse_pos)
        draw_checkbox(surf, fn, "插件按键", plugin_r, plugin_on, hover=hov_plugin)
        self._clickables.append(("chk_plugin", plugin_r))

        y += btn_h + 6
        plugin_rows = [
            [('发车PgUp', 'button_depart_music', 'btn_depart_music_map', 'clear_depart_music'),
             ('报站PgDn', 'button_announce', 'btn_announce_map', 'clear_announce')],
            [('停播End', 'button_stop_announce', 'btn_stop_announce_map', 'clear_stop_announce')],
        ]
        for row in plugin_rows:
            for i, item in enumerate(row):
                self._draw_btn_map(surf, fn, mouse_pos, col_x[i], y, btn_h, *item,
                                   disabled=not plugin_on, label_w=82)
            y += btn_h + row_gap

    def _draw_learn_hint(self, surf):
        target_names = {
            "neutral": "N档按钮",
            "eb": "EB按钮",
            "resync": "归位按钮",
            "horn": "鸣笛",
            "skip_stop": "跳过停车",
            "cruise": "定速巡航",
            "depart_music": "发车音乐",
            "announce": "报站广播",
            "stop_announce": "停止广播",
        }
        name = target_names.get(self.button_learn_target, "?")
        msg = f"请按手柄按钮来绑定「{name}」  Esc 取消"
        s = self.fonts["sm"]
        tw = s.size(msg)[0]
        bx = (WIN_W - tw - 20) // 2
        by = CTRL_Y - 30
        pygame.draw.rect(surf, (50, 50, 20), (bx - 4, by - 4, tw + 28, 26), border_radius=5)
        draw_text(surf, s, msg, COLOR_YELLOW, bx + 4, by + 2)

    def _draw_interval_hint(self, surf):
        msg = "← → 调整发送间隔  |  Esc 完成"
        s   = self.fonts["sm"]
        tw  = s.size(msg)[0]
        bx  = (WIN_W - tw - 20) // 2
        by  = CTRL_Y - 30
        pygame.draw.rect(surf, (20, 40, 55), (bx - 4, by - 4, tw + 28, 26), border_radius=5)
        draw_text(surf, s, msg, COLOR_YELLOW, bx + 4, by + 2)


# ──────────────────────────────────────────────────────────────────────
# 入口
# ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    App().run()
