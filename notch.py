COLOR_BLUE   = (100, 149, 237)
COLOR_ORANGE = (255, 165,  60)
COLOR_GREEN  = ( 80, 200, 120)
COLOR_RED    = (220,  60,  60)
COLOR_GRAY   = (140, 140, 140)
COLOR_WHITE  = (255, 255, 255)
COLOR_BG     = ( 30,  30,  35)


def build_notch_names(power, brake, has_hb):
    names = []
    for i in range(brake, 0, -1):
        names.append(f"B{i}")
    if has_hb:
        names.append("HB")
    names.append("N")
    for i in range(1, power + 1):
        names.append(f"P{i}")
    return names


def notch_color(name):
    if name.startswith("B"):
        return COLOR_ORANGE
    if name.startswith("H"):
        return COLOR_ORANGE
    if name == "HB":
        return COLOR_ORANGE
    if name == "N":
        return COLOR_GREEN
    if name.startswith("P"):
        return COLOR_BLUE
    if name == "EB":
        return COLOR_RED
    return COLOR_GRAY


def get_total_notches(cfg):
    return cfg["brake_notches"] + (1 if cfg["has_hb"] else 0) + 1 + cfg["power_notches"]


def notch_description(name):
    if name.startswith("H"):
        n = name[1:]
        return f"Hold Brake {n}"
    if name == "N":
        return "空档"
    if name == "HB":
        return "保持制动"
    if name == "EB":
        return "紧急制动"
    if name.startswith("B"):
        n = name[1:]
        return f"制动 {n} 档"
    if name.startswith("P"):
        n = name[1:]
        return f"动力 {n} 档"
    return name


def apply_deadzone(val, deadzone):
    if abs(val) < deadzone:
        return 0.0
    return val


def axis_to_notch(axis_val, total_notches, invert, deadzone):
    val = apply_deadzone(axis_val, deadzone)
    if invert:
        normalized = (val + 1.0) / 2.0
    else:
        normalized = (-val + 1.0) / 2.0
    normalized = max(0.0, min(1.0, normalized))
    return round(normalized * (total_notches - 1))


def axis_to_notch_calibrated(axis_val, calibration: dict, total_notches: int) -> int:
    """
    分段线性插值映射（模式 B）。

    calibration: {str(notch_index): float(axis_value), ...}
      例：{"0": 0.92, "8": 0.01, "13": -0.88}
      键为档位内部索引（字符串），值为对应的轴原始值。

    至少需要 2 个标定点才能插值；否则回退到均匀线性映射。
    标定之外的范围夹紧到最近端点，不做外推。
    """
    if not calibration or len(calibration) < 2:
        # 标定点不足，回退均匀映射
        return axis_to_notch(axis_val, total_notches, False, 0.0)

    # 按轴值升序排列标定点 [(axis_val, notch_idx), ...]
    points = sorted(
        [(float(v), int(k)) for k, v in calibration.items()],
        key=lambda p: p[0],
    )

    # 超出范围：夹紧到端点
    if axis_val <= points[0][0]:
        return max(0, min(total_notches - 1, points[0][1]))
    if axis_val >= points[-1][0]:
        return max(0, min(total_notches - 1, points[-1][1]))

    # 在两个相邻标定点之间线性插值
    for i in range(len(points) - 1):
        av0, n0 = points[i]
        av1, n1 = points[i + 1]
        if av0 <= axis_val <= av1:
            if av1 == av0:
                return n0
            t = (axis_val - av0) / (av1 - av0)
            result = n0 + t * (n1 - n0)
            return max(0, min(total_notches - 1, round(result)))

    return points[-1][1]
