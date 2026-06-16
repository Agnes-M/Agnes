#!/usr/bin/env python3
import asyncio
import math
import shutil
import subprocess
import tempfile
from pathlib import Path

import edge_tts
from PIL import Image, ImageDraw, ImageFilter, ImageFont


WIDTH = 1280
HEIGHT = 720
FPS = 20
SCENE_PAD_SECONDS = 0.4
MIN_SEGMENT_SECONDS = 2.5
ARTIFACT_DIR = Path("/opt/cursor/artifacts")
OUTPUT_VIDEO = ARTIFACT_DIR / "alcohol_gene_3d_realistic_cn_voice_bgm.mp4"
OUTPUT_POSTER = ARTIFACT_DIR / "alcohol_gene_3d_realistic_poster.png"
FONT_PATH = "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"
VOICE_NAME = "zh-CN-XiaoxiaoNeural"
VOICE_RATE = "+12%"

BG_TOP = (9, 22, 52)
BG_BOTTOM = (28, 88, 149)
ACCENT = (66, 192, 255)
ACCENT_2 = (120, 246, 224)
WARM = (255, 110, 120)
TEXT = (245, 250, 255)
SUBTEXT = (196, 221, 244)
DARK = (7, 18, 39)

SCENE_TITLES = {
    1: "开场引入",
    2: "酒精代谢通路",
    3: "三种基因型",
    4: "医院检测流程",
    5: "临床意义与获益",
    6: "结尾行动引导",
}

# 完全按 PDF 脚本拆分的旁白分段；每段独立配音并与画面同步。
SEGMENTS = [
    # 场景一 · 开场引入（约 15 秒）
    {"scene": 1, "phase": 0, "overlay": "为什么同样喝一杯，有人面不改色，有人却醉倒？", "narration": "为什么同样喝一杯，有人面不改色，有人却醉倒？"},
    {"scene": 1, "phase": 1, "overlay": "脸红 · 心跳加速 · 不适反应", "narration": "在中国，超过三分之一的人在饮酒后会脸红、心跳加速甚至不适反应。"},
    {"scene": 1, "phase": 2, "overlay": "秘密：你的基因", "narration": "这背后，隐藏着一个你可能从未关注过的秘密——你的基因。"},
    # 场景二 · 酒精代谢通路（约 35 秒）
    {"scene": 2, "phase": 0, "overlay": "酒精 → 胃肠道吸收 → 肝脏", "narration": "酒精进入身体后，由肝脏中的两种酶来处理。"},
    {"scene": 2, "phase": 1, "overlay": "乙醇 —(ADH)→ 乙醛（有毒）", "narration": "第一步，ADH 将乙醇转化为乙醛，乙醛是一种有毒物质，会引起脸红、恶心等症状。"},
    {"scene": 2, "phase": 2, "overlay": "乙醛 —(ALDH2)→ 乙酸（无害）", "narration": "第二步，ALDH2 酶再将乙醛分解为无害的乙酸。"},
    {"scene": 2, "phase": 3, "overlay": "ALDH2 基因突变 → 乙醛蓄积", "narration": "问题在于，ALDH2 基因存在突变。如果你携带突变型，乙醛就会在体内积聚，让你对酒精格外敏感。"},
    # 场景三 · 基因分型解读（约 25 秒）
    {"scene": 3, "phase": 0, "overlay": "ALDH2 基因检测 · 三种类型", "narration": "根据 ALDH2 基因检测，每个人可分为三种类型。"},
    {"scene": 3, "phase": 1, "overlay": "正常型（*1/*1）· 代谢顺畅", "narration": "正常型可以相对正常饮酒；"},
    {"scene": 3, "phase": 2, "overlay": "杂合突变（*1/*2）· 中等风险", "narration": "杂合突变携带者酶活性下降，风险升高；"},
    {"scene": 3, "phase": 3, "overlay": "纯合突变（*2/*2）· 高风险", "narration": "而纯合突变者几乎失去代谢乙醛的能力，与食道癌、胃癌等风险显著相关。"},
    # 场景四 · 检测流程（约 25 秒）
    {"scene": 4, "phase": 0, "overlay": "流程简单 · 无创", "narration": "在我们医院，酒精代谢基因检测流程简单、无创。"},
    {"scene": 4, "phase": 1, "overlay": "咨询 → 采样 → 检测 → 报告", "narration": "您只需挂号、采集少量样本，五到七个工作日后，即可获得一份详细的基因报告。"},
    {"scene": 4, "phase": 2, "overlay": "专业医生解读 · 个性化建议", "narration": "专业医生将为您解读结果，并制定个性化的饮酒风险管理建议。"},
    # 场景五 · 临床意义（约 10 秒）
    {"scene": 5, "phase": 0, "overlay": "代谢类型 = 健康管理", "narration": "知道自己的代谢类型，不仅仅是为了敢不敢喝酒，更是对自己健康的负责。"},
    {"scene": 5, "phase": 1, "overlay": "食道癌风险可增加 50 倍以上", "narration": "研究表明，ALDH2 突变携带者长期饮酒后，食道癌风险可增加五十倍以上。"},
    {"scene": 5, "phase": 2, "overlay": "早知道 · 早预防", "narration": "早知道，早预防。"},
    # 场景六 · 结尾号召（约 10 秒）
    {"scene": 6, "phase": 0, "overlay": "一次检测 · 终身参考", "narration": "了解自己的基因，让健康选择有据可依。扫描二维码或拨打电话，预约 XX 医院基因检测门诊，一次检测，终身参考。"},
    {"scene": 6, "phase": 1, "overlay": "健康科普免责声明", "narration": "本视频仅供健康科普，具体诊疗请遵医嘱。"},
]


def ease(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return 3 * t * t - 2 * t * t * t


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def blend(c1, c2, t: float):
    return tuple(int(lerp(a, b, t)) for a, b in zip(c1, c2))


def load_font(size: int):
    return ImageFont.truetype(FONT_PATH, size=size)


TITLE_FONT = load_font(36)
SUBTITLE_FONT = load_font(22)
LABEL_FONT = load_font(20)
SMALL_FONT = load_font(16)
BIG_FONT = load_font(28)
HOOK_FONT = load_font(32)


def make_gradient():
    base = Image.new("RGB", (WIDTH, HEIGHT))
    px = base.load()
    for y in range(HEIGHT):
        vertical = y / HEIGHT
        row = blend(BG_TOP, BG_BOTTOM, vertical)
        for x in range(WIDTH):
            radial = min(1.0, math.dist((x, y), (WIDTH * 0.75, HEIGHT * 0.25)) / 1000)
            px[x, y] = blend((48, 146, 255), row, radial)
    return base


BASE_BG = make_gradient().convert("RGBA")
VIGNETTE = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
_vdraw = ImageDraw.Draw(VIGNETTE)
_vdraw.rectangle((0, 0, WIDTH, HEIGHT), fill=(0, 0, 0, 28))
VIGNETTE = VIGNETTE.filter(ImageFilter.GaussianBlur(24))

TEXTURE_OVERLAY = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
_tpx = TEXTURE_OVERLAY.load()
for _y in range(HEIGHT):
    for _x in range(WIDTH):
        val = ((_x * 31 + _y * 17 + (_x // 9) * 13) % 100) / 100.0
        _tpx[_x, _y] = (220, 230, 245, int(10 + val * 16))
TEXTURE_OVERLAY = TEXTURE_OVERLAY.filter(ImageFilter.GaussianBlur(0.6))


def add_glow(canvas, center, radius, color, alpha):
    layer = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    x, y = center
    d.ellipse((x - radius, y - radius, x + radius, y + radius), fill=color + (alpha,))
    layer = layer.filter(ImageFilter.GaussianBlur(radius / 3))
    canvas.alpha_composite(layer)


def draw_rounded_panel(draw, box, fill, outline=None, radius=28):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=2 if outline else 1)


def wrap_text(text, max_width, font):
    lines, current = [], ""
    dummy = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    for ch in text:
        trial = current + ch
        if dummy.textlength(trial, font=font) <= max_width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = ch
    if current:
        lines.append(current)
    return lines


def draw_header(draw, scene_no: int, overlay: str):
    draw.text((72, 48), f"酒精代谢基因检测科普  |  场景 {scene_no} · {SCENE_TITLES[scene_no]}", font=LABEL_FONT, fill=SUBTEXT)
    draw.text((72, 86), overlay, font=TITLE_FONT, fill=TEXT)


def draw_subtitle(draw, text: str):
    lines = wrap_text(text, WIDTH - 220, SUBTITLE_FONT)
    line_height = 38
    box_h = 46 + line_height * len(lines)
    y0 = HEIGHT - box_h - 40
    draw.rounded_rectangle((64, y0, WIDTH - 64, HEIGHT - 40), radius=26, fill=(5, 15, 32, 200))
    for idx, line in enumerate(lines):
        draw.text((96, y0 + 20 + idx * line_height), line, font=SUBTITLE_FONT, fill=TEXT)


def draw_center_hook(draw, text: str, y: int = 168):
    lines = wrap_text(text, WIDTH - 280, HOOK_FONT)
    for idx, line in enumerate(lines):
        tw = draw.textlength(line, font=HOOK_FONT)
        draw.rounded_rectangle((WIDTH / 2 - tw / 2 - 24, y + idx * 46 - 8, WIDTH / 2 + tw / 2 + 24, y + idx * 46 + 40), radius=18, fill=(8, 20, 42, 150))
        draw.text((WIDTH / 2 - tw / 2, y + idx * 46), line, font=HOOK_FONT, fill=TEXT)


def add_realistic_grade(canvas, scene_idx: int, progress: float):
    tint_palette = [(16, 40, 78), (10, 50, 72), (26, 46, 62), (18, 54, 78), (26, 42, 70), (20, 60, 84)]
    canvas.alpha_composite(Image.new("RGBA", (WIDTH, HEIGHT), tint_palette[scene_idx] + (22,)))
    canvas.alpha_composite(TEXTURE_OVERLAY)
    bloom = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    bdraw = ImageDraw.Draw(bloom)
    cx = int(lerp(WIDTH * 0.2, WIDTH * 0.85, (progress + scene_idx * 0.11) % 1))
    bdraw.ellipse((cx - 180, 130, cx + 180, 220), fill=(255, 255, 255, 26))
    canvas.alpha_composite(bloom.filter(ImageFilter.GaussianBlur(22)))


def draw_shadowed_circle(canvas, xy, r, fill):
    layer = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    x, y = xy
    d.ellipse((x - r, y - r + 10, x + r, y + r + 10), fill=(0, 0, 0, 70))
    canvas.alpha_composite(layer.filter(ImageFilter.GaussianBlur(12)))
    ImageDraw.Draw(canvas).ellipse((x - r, y - r, x + r, y + r), fill=fill)


def draw_person(draw, x, y, coat=False, flush=False):
    skin = (247, 218, 198)
    draw.ellipse((x - 20, y - 60, x + 20, y - 20), fill=skin)
    fill = (240, 246, 255) if coat else (129, 204, 255)
    draw.rounded_rectangle((x - 26, y - 20, x + 26, y + 46), radius=18, fill=fill)
    draw.ellipse((x - 16, y - 52, x - 4, y - 40), fill=DARK)
    draw.ellipse((x + 4, y - 52, x + 16, y - 40), fill=DARK)
    if flush:
        draw.ellipse((x - 38, y - 38, x - 10, y - 10), fill=(255, 120, 132, 180))
        draw.ellipse((x + 10, y - 38, x + 38, y - 10), fill=(255, 120, 132, 180))


def draw_dna(draw, center, scale, color):
    cx, cy = center
    pl, pr = [], []
    for i in range(16):
        y = cy - 90 * scale + i * 12 * scale
        xo = math.sin(i / 2) * 20 * scale
        pl.append((cx - 20 * scale + xo, y))
        pr.append((cx + 20 * scale - xo, y))
    draw.line(pl, fill=color, width=max(2, int(5 * scale)))
    draw.line(pr, fill=color, width=max(2, int(5 * scale)))
    for l, r in zip(pl[::2], pr[::2]):
        draw.line((l, r), fill=(255, 255, 255), width=max(1, int(2 * scale)))


def scene_one(canvas, draw, t, phase):
    add_glow(canvas, (420, 300), 220, WARM, 80)
    table_y = 500
    draw.ellipse((120, table_y - 45, 1160, table_y + 45), fill=(15, 35, 65, 220))
    clink = math.sin(t * math.pi) * 18 if phase == 0 else 0
    for offset, sign in [(-70, -1), (70, 1)]:
        cx = 500 + offset + sign * clink
        top = 300 - sign * clink * 0.15
        draw.polygon([(cx - 40, top), (cx + 40, top + 8), (cx + 28, top + 92), (cx - 28, top + 92)], fill=(240, 247, 255, 140))
        draw.rectangle((cx - 4, top + 92, cx + 4, top + 180), fill=(220, 236, 252, 180))
        draw.ellipse((cx - 34, top + 38, cx + 34, top + 94), fill=(145, 20, 45, 220))
    if phase == 0:
        draw_person(draw, 920, 340, flush=False)
        draw_person(draw, 1060, 340, flush=True)
    elif phase == 1:
        draw_person(draw, 980, 330, flush=True)
        pulse = int(120 + 80 * math.sin(t * math.pi * 6))
        draw.ellipse((900, 250, 940, 290), fill=(255, 90, 110, pulse))
        draw.text((948, 258), "心跳加速", font=LABEL_FONT, fill=WARM)
        for i in range(3):
            draw.arc((880 + i * 36, 360, 920 + i * 36, 400), 200, 340, fill=WARM, width=4)
    else:
        draw_dna(draw, (640, 340), 2.2, ACCENT_2)
        draw.text((560, 470), "你的基因", font=BIG_FONT, fill=TEXT)


def scene_two(canvas, draw, t, phase):
    add_glow(canvas, (360, 340), 220, ACCENT_2, 80)
    body = [(300, 190), (360, 170), (420, 190), (450, 260), (430, 420), (330, 420), (310, 260)]
    draw.polygon(body, fill=(225, 239, 255, 55), outline=(210, 235, 255, 160))
    draw.ellipse((304, 130, 416, 242), fill=(230, 242, 255, 65), outline=(210, 235, 255, 160), width=2)
    draw.rounded_rectangle((298, 270, 405, 350), radius=30, fill=(170, 78, 72, 210))
    if phase == 0:
        pts = [(220, 210), (250, 270), (280, 310), (310, 300)]
        for i, p in enumerate(pts[: max(2, int(2 + t * (len(pts) - 1)))]):
            draw.ellipse((p[0] - 12, p[1] - 12, p[0] + 12, p[1] + 12), fill=(109, 232, 255, 220))
        draw.text((180, 160), "胃肠道吸收", font=LABEL_FONT, fill=TEXT)
        draw.text((330, 360), "肝脏", font=BIG_FONT, fill=TEXT)
    panel = (560, 180, 1180, 500)
    draw_rounded_panel(draw, panel, (235, 246, 255, 225), outline=(170, 215, 255))
    x1, x2, x3 = 660, 860, 1060
    y = 310
    molecules = [(x1, (78, 180, 255), "乙醇"), (x2, (255, 122, 94), "乙醛"), (x3, (118, 232, 182), "乙酸")]
    if phase >= 1:
        draw.ellipse((x1 - 48, y - 48, x1 + 48, y + 48), fill=molecules[0][1])
        draw.text((x1 - 28, y + 64), "乙醇", font=LABEL_FONT, fill=DARK)
    if phase >= 1:
        prog = ease(t) if phase == 1 else 1.0
        ax = int(lerp(x1 + 52, x2 - 52, prog))
        draw.line((x1 + 52, y, ax, y), fill=(64, 120, 180), width=8)
        draw.text((700, 220), "ADH / ADH1B", font=LABEL_FONT, fill=(26, 92, 154))
        if phase == 1:
            draw.ellipse((ax - 10, y - 10, ax + 10, y + 10), fill=WARM)
    if phase >= 1:
        draw.ellipse((x2 - 48, y - 48, x2 + 48, y + 48), fill=molecules[1][1])
        draw.text((x2 - 28, y + 64), "乙醛（有毒）", font=LABEL_FONT, fill=DARK)
    if phase >= 2:
        prog = ease(t) if phase == 2 else 1.0
        bx = int(lerp(x2 + 52, x3 - 52, prog))
        draw.line((x2 + 52, y, bx, y), fill=(64, 120, 180), width=8)
        draw.text((900, 220), "ALDH2", font=LABEL_FONT, fill=(26, 92, 154))
    if phase >= 2:
        draw.ellipse((x3 - 48, y - 48, x3 + 48, y + 48), fill=molecules[2][1])
        draw.text((x3 - 28, y + 64), "乙酸（无害）", font=LABEL_FONT, fill=DARK)
    if phase == 3:
        draw.line((x2 - 60, y - 60, x2 + 60, y + 60), fill=WARM, width=6)
        draw.line((x2 + 60, y - 60, x2 - 60, y + 60), fill=WARM, width=6)
        for i in range(6):
            ang = t * math.pi * 2 + i
            px = x2 + int(math.cos(ang) * (40 + i * 8))
            py = y + int(math.sin(ang) * (30 + i * 6))
            draw.ellipse((px - 8, py - 8, px + 8, py + 8), fill=(255, 110, 120, 200))
        draw.text((760, 400), "乙醛在体内积聚", font=LABEL_FONT, fill=WARM)


def scene_three(canvas, draw, t, phase):
    cards = [
        (140, "正常型", "*1/*1", "ALDH2 活性正常，代谢顺畅，风险低", (73, 208, 154), 0.92),
        (470, "杂合突变", "*1/*2", "酶活性下降，乙醛蓄积，中等风险", (255, 196, 84), 0.55),
        (800, "纯合突变", "*2/*2", "几乎无酶活性，高风险", (255, 110, 120), 0.12),
    ]
    highlight = {0: 0, 1: 0, 2: 0, 3: 2}[phase] if phase > 0 else -1
    for idx, (x, title, genotype, desc, color, bars) in enumerate(cards):
        active = phase == 0 or idx == highlight
        alpha = 255 if active else 120
        rise = 0 if active else 30
        box = (x, 170 + rise, x + 250, 520 + rise)
        draw_rounded_panel(draw, box, (244, 249, 255, alpha), outline=color if active else (180, 190, 200))
        draw.rounded_rectangle((x + 20, 195 + rise, x + 230, 245 + rise), radius=18, fill=color + (alpha,))
        draw.text((x + 36, 204 + rise), title, font=LABEL_FONT, fill=DARK if active else (100, 110, 120))
        draw.text((x + 36, 236 + rise), genotype, font=SMALL_FONT, fill=DARK if active else (120, 120, 120))
        if active:
            draw_dna(draw, (x + 125, 340 + rise), 1.0, color)
            draw.rounded_rectangle((x + 40, 420 + rise, x + 210, 442 + rise), radius=10, fill=(208, 223, 238))
            draw.rounded_rectangle((x + 40, 420 + rise, x + 40 + 170 * bars, 442 + rise), radius=10, fill=color)
            for li, line in enumerate(wrap_text(desc, 200, SMALL_FONT)):
                draw.text((x + 40, 452 + rise + li * 22), line, font=SMALL_FONT, fill=DARK)


def scene_four(canvas, draw, t, phase):
    steps = ["挂号咨询", "医生问诊", "样本采集", "实验检测", "报告解读"]
    xs = [140, 320, 500, 680, 860]
    if phase >= 1:
        draw.line((140, 500, 1040, 500), fill=(184, 213, 240), width=8)
        active_i = min(len(steps) - 1, int(t * len(steps) * (1.2 if phase == 1 else 1.5)))
        active_x = xs[active_i]
        draw.line((140, 500, active_x, 500), fill=ACCENT_2, width=8)
        for i, (label, x) in enumerate(zip(["咨询", "采样", "检测", "报告"], [200, 500, 740, 980])):
            done = i <= active_i // 1.2
            col = (90, 226, 196) if done else (224, 235, 246)
            draw.ellipse((x - 30, 470, x + 30, 530), fill=col, outline=(255, 255, 255), width=2)
            draw.text((x - 22, 540), label, font=LABEL_FONT, fill=TEXT)
    for idx, (title, x) in enumerate(zip(steps, xs)):
        show = phase == 0 or (phase == 1 and idx <= int(t * 5)) or (phase == 2 and idx >= 3)
        if not show:
            continue
        y = 180 if idx < 3 else 300
        draw_rounded_panel(draw, (x, y, x + 170, y + 120), (240, 247, 255, 220), outline=(160, 214, 255))
        if idx == 0:
            draw.rectangle((x + 24, y + 36, x + 64, y + 76), fill=(106, 180, 255))
            draw_person(draw, x + 120, y + 90)
        elif idx == 1:
            draw_person(draw, x + 60, y + 90, coat=True)
            draw_person(draw, x + 110, y + 90)
        elif idx == 2:
            draw.line((x + 70, y + 40, x + 40, y + 24), fill=WARM, width=4)
            draw_person(draw, x + 85, y + 90)
        elif idx == 3:
            draw.rounded_rectangle((x + 30, y + 30, x + 140, y + 80), radius=14, fill=(71, 129, 201))
        else:
            draw_person(draw, x + 55, y + 90, coat=True)
            draw.rectangle((x + 90, y + 30, x + 140, y + 70), fill=(255, 255, 255))
        draw.text((x + 24, y + 92), title, font=SMALL_FONT, fill=DARK)
    if phase >= 1:
        draw.text((470, 600), "5–7 个工作日出报告", font=LABEL_FONT, fill=SUBTEXT)


def scene_five(canvas, draw, t, phase):
    add_glow(canvas, (640, 300), 240, ACCENT, 80)
    if phase < 2:
        draw_person(draw, 640, 350, coat=True)
    icons = [
        ((300, 230), "消化道肿瘤\n风险预警"),
        ((980, 230), "手术前酒精\n耐受评估"),
        ((300, 420), "药物相互\n作用参考"),
        ((980, 420), "家族遗传\n风险筛查"),
    ]
    for idx, ((x, y), label) in enumerate(icons):
        show = phase == 0 or (phase == 1 and idx <= int(t * 4))
        if not show:
            continue
        r = 62
        draw.ellipse((x - r, y - r, x + r, y + r), fill=(241, 247, 255, 220), outline=(157, 214, 255), width=3)
        for li, line in enumerate(label.split("\n")):
            tw = draw.textlength(line, font=SMALL_FONT)
            draw.text((x - tw / 2, y - 10 + li * 20), line, font=SMALL_FONT, fill=DARK)
    if phase == 1:
        draw.rounded_rectangle((360, 160, 920, 230), radius=20, fill=(255, 110, 120, 210))
        draw.text((400, 182), "食道癌风险可增加 50 倍以上", font=BIG_FONT, fill=TEXT)
    if phase == 2:
        draw.text((500, 300), "早知道，早预防", font=TITLE_FONT, fill=ACCENT_2)


def scene_six(canvas, draw, t, phase):
    add_glow(canvas, (300, 260), 180, ACCENT_2, 70)
    draw.rectangle((120, 270, 400, 510), fill=(232, 242, 255))
    draw_dna(draw, (500, 320), 1.6, ACCENT_2)
    alpha = int(lerp(0, 255, ease(t)))
    draw.rounded_rectangle((620, 170, 1160, 530), radius=34, fill=(239, 247, 255, alpha))
    draw.text((672, 210), "XX 医院 · 基因检测门诊", font=BIG_FONT, fill=DARK)
    draw.text((672, 262), "让健康选择有据可依", font=TITLE_FONT, fill=(23, 72, 123))
    draw.text((672, 320), "预约咨询：400-800-1234", font=LABEL_FONT, fill=(37, 92, 152))
    draw.rectangle((940, 290, 1050, 400), fill=(220, 232, 246), outline=(72, 132, 200), width=4)
    for i in range(6):
        draw.line((952, 302 + i * 16, 1038, 302 + i * 16), fill=(100, 136, 180), width=3)
    if phase == 1:
        draw.text((672, 420), "本视频仅供健康科普，具体诊疗请遵医嘱", font=LABEL_FONT, fill=(74, 104, 138))


SCENE_DRAWERS = [scene_one, scene_two, scene_three, scene_four, scene_five, scene_six]


def render_frame(segment: dict, frame_idx: int, frames_per_segment: int):
    progress = frame_idx / max(1, frames_per_segment - 1) if frames_per_segment > 1 else 1.0
    scene_idx = segment["scene"] - 1
    canvas = BASE_BG.copy()
    draw = ImageDraw.Draw(canvas, "RGBA")
    draw_header(draw, segment["scene"], segment["overlay"])
    SCENE_DRAWERS[scene_idx](canvas, draw, progress, segment["phase"])
    add_realistic_grade(canvas, scene_idx, progress)
    draw_subtitle(draw, segment["narration"])
    canvas.alpha_composite(VIGNETTE)
    fade = 1.0
    if progress < 0.1:
        fade = progress / 0.1
    elif progress > 0.9:
        fade = (1.0 - progress) / 0.1
    if fade < 1.0:
        canvas.alpha_composite(Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, int((1 - fade) * 255))))
    return canvas.convert("RGB")


def encode_video(frame_dir: Path, silent_video: Path, frame_count: int):
    cmd = [
        "ffmpeg", "-y", "-framerate", str(FPS),
        "-i", str(frame_dir / "frame_%05d.png"),
        "-frames:v", str(frame_count),
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        str(silent_video),
    ]
    subprocess.run(cmd, check=True)


def probe_duration(path: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True, check=True,
    )
    return float(result.stdout.strip())


async def synthesize_segment_voices(temp_root: Path) -> list[dict]:
    timings = []
    for idx, segment in enumerate(SEGMENTS):
        audio_path = temp_root / f"voice_seg_{idx + 1:02d}.mp3"
        await edge_tts.Communicate(
            text=segment["narration"], voice=VOICE_NAME, rate=VOICE_RATE
        ).save(str(audio_path))
        voice_duration = probe_duration(audio_path)
        seg_seconds = max(MIN_SEGMENT_SECONDS, voice_duration + SCENE_PAD_SECONDS)
        timings.append({
            "segment": segment,
            "path": audio_path,
            "voice_duration": voice_duration,
            "seg_seconds": seg_seconds,
            "frames": max(1, int(round(seg_seconds * FPS))),
        })
        print(f"Segment {idx + 1:02d} [场景{segment['scene']}]: {voice_duration:.2f}s -> {seg_seconds:.2f}s", flush=True)
    return timings


def concat_voice_tracks(timings: list[dict], output_path: Path):
    inputs, chains = [], []
    for idx, item in enumerate(timings):
        inputs.extend(["-i", str(item["path"])])
        pad = max(0.0, item["seg_seconds"] - item["voice_duration"])
        chains.append(f"[{idx}:a]apad=pad_dur={pad:.3f}[a{idx}]")
    concat_inputs = "".join(f"[a{idx}]" for idx in range(len(timings)))
    filter_graph = ";".join(chains) + f";{concat_inputs}concat=n={len(timings)}:v=0:a=1[aout]"
    subprocess.run(["ffmpeg", "-y", *inputs, "-filter_complex", filter_graph, "-map", "[aout]", str(output_path)], check=True)


def generate_bgm(duration_sec: float, output_path: Path):
    subprocess.run([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"sine=frequency=196:duration={duration_sec}:sample_rate=44100",
        "-f", "lavfi", "-i", f"sine=frequency=294:duration={duration_sec}:sample_rate=44100",
        "-f", "lavfi", "-i", f"sine=frequency=392:duration={duration_sec}:sample_rate=44100",
        "-filter_complex",
        "[0:a]volume=0.04[a0];[1:a]volume=0.03[a1];[2:a]volume=0.02[a2];"
        f"[a0][a1][a2]amix=inputs=3,lowpass=f=1600,afade=t=in:st=0:d=2,afade=t=out:st={max(0.0, duration_sec - 2.5)}:d=2.5",
        str(output_path),
    ], check=True)


def mux_audio_video(silent_video: Path, voice_audio: Path, bgm_audio: Path):
    subprocess.run([
        "ffmpeg", "-y",
        "-i", str(silent_video), "-i", str(voice_audio), "-i", str(bgm_audio),
        "-filter_complex",
        "[1:a]volume=1.2[voice];[2:a]volume=0.45[bgm];[bgm][voice]amix=inputs=2:duration=first:dropout_transition=2[aout]",
        "-map", "0:v:0", "-map", "[aout]", "-c:v", "copy", "-c:a", "aac",
        str(OUTPUT_VIDEO),
    ], check=True)


def main():
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    temp_root = Path(tempfile.mkdtemp(prefix="alcohol_gene_video_"))
    try:
        frame_dir = temp_root / "frames"
        silent_video = temp_root / "silent_video.mp4"
        voice_audio = temp_root / "voice_cn.mp3"
        bgm_audio = temp_root / "bgm.wav"
        frame_dir.mkdir(parents=True, exist_ok=True)
        timings = asyncio.run(synthesize_segment_voices(temp_root))
        total_frames = 0
        for idx, timing in enumerate(timings):
            frames = timing["frames"]
            seg = timing["segment"]
            print(f"Rendering segment {idx + 1}/{len(timings)} scene {seg['scene']} phase {seg['phase']}...", flush=True)
            for frame_idx in range(frames):
                image = render_frame(seg, frame_idx, frames)
                image.save(frame_dir / f"frame_{total_frames:05d}.png", quality=95)
                total_frames += 1
        shutil.copy(frame_dir / f"frame_{total_frames - 1:05d}.png", OUTPUT_POSTER)
        encode_video(frame_dir, silent_video, total_frames)
        concat_voice_tracks(timings, voice_audio)
        generate_bgm(probe_duration(silent_video), bgm_audio)
        mux_audio_video(silent_video, voice_audio, bgm_audio)
        duration = probe_duration(OUTPUT_VIDEO)
        print(f"Video written to {OUTPUT_VIDEO} ({duration:.1f}s, {len(SEGMENTS)} segments)")
        print(f"Poster written to {OUTPUT_POSTER}")
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


if __name__ == "__main__":
    main()
