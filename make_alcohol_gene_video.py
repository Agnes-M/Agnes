#!/usr/bin/env python3
import asyncio
import math
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import edge_tts
from PIL import Image, ImageDraw, ImageFilter, ImageFont


WIDTH = 1280
HEIGHT = 720
FPS = 20
SCENE_SECONDS = 4
TOTAL_SCENES = 6
FRAMES_PER_SCENE = FPS * SCENE_SECONDS
ARTIFACT_DIR = Path("/opt/cursor/artifacts")
OUTPUT_VIDEO = ARTIFACT_DIR / "alcohol_gene_3d_realistic_cn_voice_bgm.mp4"
OUTPUT_POSTER = ARTIFACT_DIR / "alcohol_gene_3d_realistic_poster.png"
FONT_PATH = "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"
VOICE_NAME = "zh-CN-XiaoxiaoNeural"
VOICE_RATE = "+18%"

BG_TOP = (9, 22, 52)
BG_BOTTOM = (28, 88, 149)
ACCENT = (66, 192, 255)
ACCENT_2 = (120, 246, 224)
WARM = (255, 110, 120)
PANEL = (241, 247, 255)
TEXT = (245, 250, 255)
SUBTEXT = (196, 221, 244)
DARK = (7, 18, 39)


SCENES = [
    {
        "title": "酒精反应差异",
        "subtitle": "为什么同样喝一杯，有人面不改色，有人很快脸红头晕？",
    },
    {
        "title": "酒精代谢通路",
        "subtitle": "乙醇先转化为有毒乙醛，再由 ALDH2 进一步分解为较无害的乙酸。",
    },
    {
        "title": "三种基因型",
        "subtitle": "正常型、杂合突变、纯合突变，对乙醛的处理能力差异明显。",
    },
    {
        "title": "检测流程",
        "subtitle": "咨询、采样、检测、报告，通常 5 到 7 个工作日获得结果。",
    },
    {
        "title": "临床意义",
        "subtitle": "知道代谢类型，不只是敢不敢喝酒，更关系到长期健康风险管理。",
    },
    {
        "title": "行动建议",
        "subtitle": "了解自己的基因，让健康选择更有依据。一次检测，长期参考。",
    },
]

NARRATION_LINES = [
    "很多人都有这样的经历，同样喝一杯酒，反应却完全不同。",
    "酒精进入体内后，先由 ADH 转化为乙醛，再由 ALDH2 继续分解。",
    "根据 ALDH2 基因检测结果，可分为正常型、杂合突变和纯合突变三类。",
    "检测流程通常包括咨询、采样、实验检测与报告解读，五到七个工作日可出结果。",
    "了解代谢类型，不只是能不能喝酒，更关系到长期健康风险管理。",
    "了解自己的基因，让健康选择更有依据。一次检测，长期参考。",
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


def make_gradient():
    base = Image.new("RGB", (WIDTH, HEIGHT))
    px = base.load()
    for y in range(HEIGHT):
        vertical = y / HEIGHT
        row = blend(BG_TOP, BG_BOTTOM, vertical)
        for x in range(WIDTH):
            radial = min(1.0, math.dist((x, y), (WIDTH * 0.75, HEIGHT * 0.25)) / 1000)
            glow = blend((48, 146, 255), row, radial)
            px[x, y] = glow
    return base


BASE_BG = make_gradient().convert("RGBA")
VIGNETTE = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
_vdraw = ImageDraw.Draw(VIGNETTE)
_vdraw.rectangle((0, 0, WIDTH, HEIGHT), fill=(0, 0, 0, 28))
VIGNETTE = VIGNETTE.filter(ImageFilter.GaussianBlur(24))


def make_texture_overlay():
    layer = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    px = layer.load()
    for y in range(HEIGHT):
        for x in range(WIDTH):
            val = ((x * 31 + y * 17 + (x // 9) * 13) % 100) / 100.0
            alpha = int(10 + val * 16)
            px[x, y] = (220, 230, 245, alpha)
    return layer.filter(ImageFilter.GaussianBlur(0.6))


TEXTURE_OVERLAY = make_texture_overlay()


def add_glow(canvas, center, radius, color, alpha):
    layer = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    x, y = center
    d.ellipse((x - radius, y - radius, x + radius, y + radius), fill=color + (alpha,))
    layer = layer.filter(ImageFilter.GaussianBlur(radius / 3))
    canvas.alpha_composite(layer)


def draw_rounded_panel(draw, box, fill, outline=None, radius=28):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=2 if outline else 1)


def draw_title(draw, scene_no, title):
    draw.text((72, 48), f"酒精代谢基因科普样片  |  场景 {scene_no}", font=LABEL_FONT, fill=SUBTEXT)
    draw.text((72, 86), title, font=TITLE_FONT, fill=TEXT)


def wrap_text(text, max_width, font):
    words = list(text)
    lines = []
    current = ""
    dummy = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    for ch in words:
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


def draw_subtitle(draw, text):
    lines = wrap_text(text, WIDTH - 220, SUBTITLE_FONT)
    line_height = 38
    box_h = 46 + line_height * len(lines)
    y0 = HEIGHT - box_h - 40
    draw.rounded_rectangle((64, y0, WIDTH - 64, HEIGHT - 40), radius=26, fill=(5, 15, 32, 190))
    for idx, line in enumerate(lines):
        draw.text((96, y0 + 20 + idx * line_height), line, font=SUBTITLE_FONT, fill=TEXT)


def add_realistic_grade(canvas, scene_idx: int, progress: float):
    # Subtle scene-dependent color grading and specular bloom.
    tint_palette = [(16, 40, 78), (10, 50, 72), (26, 46, 62), (18, 54, 78), (26, 42, 70), (20, 60, 84)]
    tint = tint_palette[scene_idx % len(tint_palette)]
    grade = Image.new("RGBA", (WIDTH, HEIGHT), tint + (20,))
    canvas.alpha_composite(grade)
    canvas.alpha_composite(TEXTURE_OVERLAY)

    bloom = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    bdraw = ImageDraw.Draw(bloom)
    cx = int(lerp(WIDTH * 0.2, WIDTH * 0.85, (progress + scene_idx * 0.11) % 1))
    cy = int(HEIGHT * 0.22)
    bdraw.ellipse((cx - 180, cy - 90, cx + 180, cy + 90), fill=(255, 255, 255, 24))
    bloom = bloom.filter(ImageFilter.GaussianBlur(22))
    canvas.alpha_composite(bloom)


def draw_shadowed_circle(canvas, xy, r, fill):
    layer = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    x, y = xy
    d.ellipse((x - r, y - r + 10, x + r, y + r + 10), fill=(0, 0, 0, 70))
    layer = layer.filter(ImageFilter.GaussianBlur(12))
    canvas.alpha_composite(layer)
    d = ImageDraw.Draw(canvas)
    d.ellipse((x - r, y - r, x + r, y + r), fill=fill)


def scene_one(canvas, draw, t):
    add_glow(canvas, (380, 320), 220, WARM, 80)
    add_glow(canvas, (920, 260), 260, ACCENT, 80)
    table_y = 520
    draw.ellipse((100, table_y - 55, 1180, table_y + 55), fill=(15, 35, 65, 220))
    clink = math.sin(t * math.pi) * 22
    for offset, sign in [(-80, -1), (80, 1)]:
        cx = 470 + offset + sign * clink
        top = 292 - sign * clink * 0.2
        bowl = [(cx - 46, top), (cx + 46, top + 10), (cx + 32, top + 104), (cx - 32, top + 104)]
        draw.polygon(bowl, fill=(240, 247, 255, 130))
        draw.rectangle((cx - 5, top + 104, cx + 5, top + 210), fill=(220, 236, 252, 180))
        draw.ellipse((cx - 38, top + 42, cx + 38, top + 106), fill=(145, 20, 45, 220))
        draw.ellipse((cx - 24, top + 206, cx + 24, top + 222), fill=(220, 236, 252, 200))
    calm_x = 910
    flush_x = 1080
    for x, is_flush in [(calm_x, False), (flush_x, True)]:
        draw_shadowed_circle(canvas, (x, 340), 68, (247, 218, 198, 255))
        draw.rounded_rectangle((x - 52, 405, x + 52, 535), radius=34, fill=(234, 241, 255, 255))
        eye_y = 332
        draw.ellipse((x - 24, eye_y, x - 8, eye_y + 12), fill=DARK)
        draw.ellipse((x + 8, eye_y, x + 24, eye_y + 12), fill=DARK)
        draw.arc((x - 18, 354, x + 18, 376), 0, 180, fill=DARK, width=3)
        if is_flush:
            pulse = int(70 + 50 * math.sin(t * math.pi * 4))
            draw.ellipse((x - 44, 356, x - 16, 384), fill=(255, 120, 132, pulse))
            draw.ellipse((x + 16, 356, x + 44, 384), fill=(255, 120, 132, pulse))
            draw.arc((x + 66, 288, x + 102, 324), 40, 260, fill=TEXT, width=4)


def scene_two(canvas, draw, t):
    add_glow(canvas, (380, 360), 240, ACCENT_2, 90)
    add_glow(canvas, (980, 320), 200, WARM, 70)
    body = [(320, 180), (380, 160), (440, 180), (474, 250), (452, 390), (430, 540), (330, 540), (308, 390), (286, 250)]
    draw.polygon(body, fill=(225, 239, 255, 60), outline=(210, 235, 255, 180))
    draw.ellipse((324, 118, 436, 232), fill=(230, 242, 255, 70), outline=(210, 235, 255, 180), width=3)
    draw.rounded_rectangle((318, 272, 425, 360), radius=34, fill=(170, 78, 72, 220))
    path_points = [(250, 198), (280, 260), (305, 330), (330, 302), (365, 316)]
    for i, p in enumerate(path_points[: max(2, int(2 + t * (len(path_points) - 1)))]):
        r = 14 if i % 2 == 0 else 10
        draw.ellipse((p[0] - r, p[1] - r, p[0] + r, p[1] + r), fill=(109, 232, 255, 220))
    draw.text((210, 150), "酒精进入体内", font=LABEL_FONT, fill=TEXT)
    panel = (600, 190, 1180, 495)
    draw_rounded_panel(draw, panel, (235, 246, 255, 225), outline=(170, 215, 255))
    x1, x2, x3 = 690, 890, 1090
    y = 320
    for x, color, label in [(x1, (78, 180, 255), "乙醇"), (x2, (255, 122, 94), "乙醛"), (x3, (118, 232, 182), "乙酸")]:
        draw.ellipse((x - 50, y - 50, x + 50, y + 50), fill=color)
        draw.text((x - 30, y + 76), label, font=LABEL_FONT, fill=DARK)
    draw.line((x1 + 58, y, x2 - 58, y), fill=(64, 120, 180), width=8)
    draw.line((x2 + 58, y, x3 - 58, y), fill=(64, 120, 180), width=8)
    arrow = int(lerp(x1 + 58, x2 - 58, ease((t * 1.8) % 1)))
    draw.ellipse((arrow - 12, y - 12, arrow + 12, y + 12), fill=WARM)
    draw.text((730, 230), "ADH", font=BIG_FONT, fill=(26, 92, 154))
    draw.text((928, 230), "ALDH2", font=BIG_FONT, fill=(26, 92, 154))
    if t > 0.58:
        warn_alpha = int(lerp(0, 210, ease((t - 0.58) / 0.42)))
        draw.rounded_rectangle((782, 380, 1000, 444), radius=18, fill=(255, 110, 120, warn_alpha))
        draw.text((822, 396), "乙醛蓄积风险", font=LABEL_FONT, fill=TEXT)


def draw_dna(draw, center, scale, color):
    cx, cy = center
    points_left = []
    points_right = []
    for i in range(16):
        y = cy - 90 * scale + i * 12 * scale
        x_offset = math.sin(i / 2) * 20 * scale
        points_left.append((cx - 20 * scale + x_offset, y))
        points_right.append((cx + 20 * scale - x_offset, y))
    draw.line(points_left, fill=color, width=max(2, int(5 * scale)))
    draw.line(points_right, fill=color, width=max(2, int(5 * scale)))
    for left, right in zip(points_left[::2], points_right[::2]):
        draw.line((left, right), fill=(255, 255, 255), width=max(1, int(2 * scale)))


def scene_three(canvas, draw, t):
    add_glow(canvas, (230, 300), 200, ACCENT, 60)
    add_glow(canvas, (1040, 280), 220, WARM, 70)
    cards = [
        (190, "正常型", "风险较低", (73, 208, 154)),
        (520, "杂合突变", "中等风险", (255, 196, 84)),
        (850, "纯合突变", "高风险", (255, 110, 120)),
    ]
    for idx, (x, title, risk, color) in enumerate(cards):
        rise = (1 - ease(min(1.0, max(0.0, t * 1.5 - idx * 0.18)))) * 80
        box = (x, 180 + rise, x + 240, 510 + rise)
        draw_rounded_panel(draw, box, (244, 249, 255, 225), outline=color)
        draw.rounded_rectangle((x + 22, 205 + rise, x + 218, 252 + rise), radius=20, fill=color)
        draw.text((x + 52, 214 + rise), title, font=LABEL_FONT, fill=DARK)
        draw_dna(draw, (x + 120, 340 + rise), 1.1, color)
        bars = [0.9, 0.55, 0.12][idx]
        draw.text((x + 58, 415 + rise), "乙醛代谢能力", font=SMALL_FONT, fill=(45, 70, 100))
        draw.rounded_rectangle((x + 52, 446 + rise, x + 188, 468 + rise), radius=10, fill=(208, 223, 238))
        draw.rounded_rectangle((x + 52, 446 + rise, x + 52 + 136 * bars, 468 + rise), radius=10, fill=color)
        draw.text((x + 84, 484 + rise), risk, font=LABEL_FONT, fill=DARK)


def draw_person(draw, x, y, coat=False):
    skin = (247, 218, 198)
    draw.ellipse((x - 20, y - 60, x + 20, y - 20), fill=skin)
    fill = (240, 246, 255) if coat else (129, 204, 255)
    draw.rounded_rectangle((x - 26, y - 20, x + 26, y + 46), radius=18, fill=fill)


def scene_four(canvas, draw, t):
    labels = ["咨询", "采样", "检测", "报告"]
    xs = [220, 460, 740, 1020]
    draw.line((220, 500, 1020, 500), fill=(184, 213, 240), width=8)
    active_x = lerp(xs[0], xs[-1], ease(t))
    draw.line((220, 500, active_x, 500), fill=ACCENT_2, width=8)
    for idx, (label, x) in enumerate(zip(labels, xs)):
        completed = t >= idx / 3 if idx < 3 else t > 0.88
        color = (90, 226, 196) if completed else (224, 235, 246)
        draw.ellipse((x - 34, 466, x + 34, 534), fill=color, outline=(255, 255, 255), width=3)
        draw.text((x - 24, 548), label, font=LABEL_FONT, fill=TEXT)
    stages = [
        ("挂号咨询", 120, 180),
        ("样本采集", 400, 180),
        ("实验检测", 680, 180),
        ("报告解读", 960, 180),
    ]
    for idx, (title, x, y) in enumerate(stages):
        shift = (1 - ease(min(1.0, max(0.0, t * 1.4 - idx * 0.2)))) * 40
        draw_rounded_panel(draw, (x, y + shift, x + 210, y + 170 + shift), (240, 247, 255, 220), outline=(160, 214, 255))
        if idx == 0:
            draw.rectangle((x + 32, y + 60 + shift, x + 82, y + 110 + shift), fill=(106, 180, 255))
            draw.rectangle((x + 90, y + 46 + shift, x + 165, y + 124 + shift), fill=(223, 236, 249))
            draw_person(draw, x + 160, y + 136 + shift)
        elif idx == 1:
            draw_person(draw, x + 76, y + 128 + shift)
            draw_person(draw, x + 148, y + 128 + shift, coat=True)
            draw.line((x + 142, y + 92 + shift, x + 92, y + 76 + shift), fill=WARM, width=5)
        elif idx == 2:
            draw.rounded_rectangle((x + 42, y + 52 + shift, x + 168, y + 120 + shift), radius=18, fill=(71, 129, 201))
            for lx in range(56, 160, 26):
                draw.line((x + lx, y + 60 + shift, x + lx, y + 112 + shift), fill=(190, 230, 255), width=3)
        else:
            draw_person(draw, x + 64, y + 126 + shift, coat=True)
            draw_person(draw, x + 146, y + 126 + shift)
            draw.rectangle((x + 88, y + 54 + shift, x + 156, y + 108 + shift), fill=(255, 255, 255))
        draw.text((x + 52, y + 128 + shift), title, font=LABEL_FONT, fill=DARK)
    draw.text((520, 610), "通常 5-7 个工作日出报告", font=LABEL_FONT, fill=SUBTEXT)


def scene_five(canvas, draw, t):
    add_glow(canvas, (640, 310), 260, ACCENT, 85)
    draw_person(draw, 640, 360, coat=True)
    draw.rounded_rectangle((590, 328, 690, 468), radius=30, fill=(255, 255, 255))
    draw.line((640, 360, 640, 438), fill=(84, 162, 255), width=6)
    draw.line((610, 382, 670, 382), fill=(84, 162, 255), width=6)
    icons = [
        ((360, 238), "肿瘤风险"),
        ((920, 238), "手术评估"),
        ((360, 390), "药物参考"),
        ((920, 390), "家族筛查"),
    ]
    for idx, ((x, y), label) in enumerate(icons):
        pulse = 1 + 0.08 * math.sin(t * math.pi * 4 + idx)
        r = int(66 * pulse)
        draw.ellipse((x - r, y - r, x + r, y + r), fill=(241, 247, 255, 220), outline=(157, 214, 255), width=4)
        if idx == 0:
            draw.arc((x - 24, y - 34, x + 24, y + 24), 200, 340, fill=WARM, width=6)
            draw.line((x, y + 6, x, y + 30), fill=WARM, width=6)
        elif idx == 1:
            draw.rectangle((x - 16, y - 24, x + 18, y + 26), outline=ACCENT, width=5)
            draw.line((x + 18, y - 24, x + 36, y - 42), fill=ACCENT, width=5)
        elif idx == 2:
            draw.rounded_rectangle((x - 24, y - 14, x + 24, y + 14), radius=14, fill=(84, 162, 255))
            draw.line((x - 8, y - 14, x - 8, y + 14), fill=TEXT, width=4)
        else:
            draw.line((x, y - 24, x, y + 22), fill=ACCENT_2, width=6)
            draw.line((x - 18, y - 2, x + 18, y - 2), fill=ACCENT_2, width=6)
        text_w = draw.textlength(label, font=LABEL_FONT)
        label_y = y - 116 if idx < 2 else y + 100
        draw.rounded_rectangle((x - text_w / 2 - 12, label_y - 8, x + text_w / 2 + 12, label_y + 30), radius=14, fill=(8, 20, 42, 120))
        draw.text((x - text_w / 2, label_y), label, font=LABEL_FONT, fill=TEXT)


def scene_six(canvas, draw, t):
    add_glow(canvas, (1020, 230), 200, ACCENT, 70)
    add_glow(canvas, (300, 250), 180, ACCENT_2, 70)
    draw.rectangle((136, 280, 430, 525), fill=(232, 242, 255))
    for i in range(5):
        bx = 176 + i * 46
        draw.rectangle((bx, 320, bx + 24, 350), fill=(75, 137, 212))
        draw.rectangle((bx, 374, bx + 24, 404), fill=(75, 137, 212))
        draw.rectangle((bx, 428, bx + 24, 458), fill=(75, 137, 212))
    draw.rectangle((232, 446, 334, 525), fill=(75, 137, 212))
    draw_dna(draw, (520, 330), 1.8, ACCENT_2)
    alpha = int(lerp(0, 255, ease(t)))
    draw.rounded_rectangle((660, 180, 1150, 520), radius=34, fill=(239, 247, 255, alpha))
    draw.text((712, 230), "了解自己的酒精代谢基因", font=BIG_FONT, fill=DARK)
    draw.text((712, 284), "让健康选择有据可依", font=TITLE_FONT, fill=(23, 72, 123))
    draw.text((712, 360), "XX医院 · 基因检测门诊", font=LABEL_FONT, fill=(37, 92, 152))
    draw.text((712, 404), "预约咨询：400-800-1234", font=LABEL_FONT, fill=(37, 92, 152))
    draw.rectangle((972, 336, 1082, 446), fill=(220, 232, 246), outline=(72, 132, 200), width=4)
    for i in range(6):
        draw.line((984, 348 + i * 16, 1070, 348 + i * 16), fill=(100, 136, 180), width=3)
        if i < 5:
            draw.line((984 + i * 16, 348, 984 + i * 16, 434), fill=(100, 136, 180), width=3)
    disclaimer = "本视频仅供健康科普，具体诊疗请遵医嘱"
    draw.text((704, 478), disclaimer, font=SMALL_FONT, fill=(74, 104, 138))


SCENE_DRAWERS = [scene_one, scene_two, scene_three, scene_four, scene_five, scene_six]


def render_frame(scene_idx: int, frame_idx: int):
    progress = frame_idx / FRAMES_PER_SCENE
    canvas = BASE_BG.copy()
    draw = ImageDraw.Draw(canvas, "RGBA")
    draw_title(draw, scene_idx + 1, SCENES[scene_idx]["title"])
    SCENE_DRAWERS[scene_idx](canvas, draw, progress)
    add_realistic_grade(canvas, scene_idx, progress)
    draw_subtitle(draw, SCENES[scene_idx]["subtitle"])
    canvas.alpha_composite(VIGNETTE)
    fade = 1.0
    if progress < 0.12:
        fade = progress / 0.12
    elif progress > 0.88:
        fade = (1.0 - progress) / 0.12
    if fade < 1.0:
        overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, int((1 - fade) * 255)))
        canvas.alpha_composite(overlay)
    return canvas.convert("RGB")


def encode_video(frame_dir: Path, silent_video: Path):
    cmd = [
        "ffmpeg",
        "-y",
        "-framerate",
        str(FPS),
        "-i",
        str(frame_dir / "frame_%04d.png"),
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(silent_video),
    ]
    subprocess.run(cmd, check=True)


async def synthesize_voice(text: str, output_path: Path):
    communicate = edge_tts.Communicate(text=text, voice=VOICE_NAME, rate=VOICE_RATE)
    await communicate.save(str(output_path))


def generate_bgm(duration_sec: float, output_path: Path):
    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        f"sine=frequency=196:duration={duration_sec}:sample_rate=44100",
        "-f",
        "lavfi",
        "-i",
        f"sine=frequency=294:duration={duration_sec}:sample_rate=44100",
        "-f",
        "lavfi",
        "-i",
        f"sine=frequency=392:duration={duration_sec}:sample_rate=44100",
        "-filter_complex",
        "[0:a]volume=0.05[a0];[1:a]volume=0.035[a1];[2:a]volume=0.025[a2];"
        "[a0][a1][a2]amix=inputs=3,lowpass=f=1800,afade=t=in:st=0:d=1.5,afade=t=out:st="
        f"{max(0.0, duration_sec - 2.0)}:d=2.0",
        str(output_path),
    ]
    subprocess.run(cmd, check=True)


def mux_audio_video(silent_video: Path, voice_audio: Path, bgm_audio: Path):
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(silent_video),
        "-i",
        str(voice_audio),
        "-i",
        str(bgm_audio),
        "-filter_complex",
        "[1:a]volume=1.15[voice];[2:a]volume=0.55[bgm];"
        "[bgm][voice]amix=inputs=2:duration=first:dropout_transition=2[aout]",
        "-map",
        "0:v:0",
        "-map",
        "[aout]",
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-shortest",
        str(OUTPUT_VIDEO),
    ]
    subprocess.run(cmd, check=True)


def main():
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    temp_root = Path(tempfile.mkdtemp(prefix="alcohol_gene_video_"))
    try:
        frame_dir = temp_root / "frames"
        silent_video = temp_root / "silent_video.mp4"
        voice_audio = temp_root / "voice_cn.mp3"
        bgm_audio = temp_root / "bgm.wav"
        frame_dir.mkdir(parents=True, exist_ok=True)
        for scene_idx in range(TOTAL_SCENES):
            print(f"Rendering scene {scene_idx + 1}/{TOTAL_SCENES}...", flush=True)
            for frame_idx in range(FRAMES_PER_SCENE):
                image = render_frame(scene_idx, frame_idx)
                absolute_idx = scene_idx * FRAMES_PER_SCENE + frame_idx
                out = frame_dir / f"frame_{absolute_idx:04d}.png"
                image.save(out, quality=95)
        shutil.copy(frame_dir / f"frame_{(TOTAL_SCENES * FRAMES_PER_SCENE) - 1:04d}.png", OUTPUT_POSTER)
        encode_video(frame_dir, silent_video)
        narration = " ".join(NARRATION_LINES)
        asyncio.run(synthesize_voice(narration, voice_audio))
        total_duration = TOTAL_SCENES * SCENE_SECONDS
        generate_bgm(total_duration, bgm_audio)
        mux_audio_video(silent_video, voice_audio, bgm_audio)
        print(f"Video written to {OUTPUT_VIDEO}")
        print(f"Poster written to {OUTPUT_POSTER}")
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


if __name__ == "__main__":
    main()
