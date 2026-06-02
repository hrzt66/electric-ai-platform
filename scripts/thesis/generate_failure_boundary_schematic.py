#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
SRC_LEFT = ROOT / "model/image/136_0_1000.png"
SRC_RIGHT = ROOT / "model/image/135_0_1000.png"
OUT = ROOT / "docs/image/paper-ready/31_post_training_validation_showcase_grid.png"

INK = "#1f2937"
MUTED = "#667085"
LINE = "#d9e2ec"
BG = "#ffffff"


def font(size: int, bold: bool = False):
    candidates = [
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        "/System/Library/Fonts/STHeiti Medium.ttc" if bold else "/System/Library/Fonts/STHeiti Light.ttc",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    ]
    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            try:
                return ImageFont.truetype(str(path), size=size)
            except OSError:
                continue
    return ImageFont.load_default()


def main() -> None:
    left = Image.open(SRC_LEFT).convert("RGB")
    right = Image.open(SRC_RIGHT).convert("RGB")

    target_h = 640
    left_w = int(left.width * target_h / left.height)
    right_w = int(right.width * target_h / right.height)
    left = left.resize((left_w, target_h), Image.Resampling.LANCZOS)
    right = right.resize((right_w, target_h), Image.Resampling.LANCZOS)

    panel_w = max(left_w, right_w)
    panel_h = target_h
    canvas_w = panel_w * 2 + 180
    canvas_h = panel_h + 220
    canvas = Image.new("RGB", (canvas_w, canvas_h), BG)
    draw = ImageDraw.Draw(canvas)

    title_f = font(36, bold=True)
    sub_f = font(20)
    panel_f = font(26, bold=True)
    note_f = font(18)

    draw.text((46, 32), "训练后验证样例拼图", fill=INK, font=title_f)
    draw.text((46, 78), "展示训练完成后验证阶段筛选出的高质量生成结果，并对比不同模型在风机场景中的表现。", fill=MUTED, font=sub_f)

    left_x, top_y = 46, 138
    right_x = left_x + panel_w + 40
    for x in (left_x, right_x):
        draw.rounded_rectangle((x - 10, top_y - 10, x + panel_w + 10, top_y + panel_h + 10), radius=18, fill="#fbfcfe", outline=LINE, width=2)

    draw.text((left_x, 106), "样例 A  sd15-electric-specialized", fill=INK, font=panel_f)
    draw.text((right_x, 106), "样例 B  sd15-electric", fill=INK, font=panel_f)

    canvas.paste(left, (left_x + (panel_w - left_w) // 2, top_y))
    canvas.paste(right, (right_x + (panel_w - right_w) // 2, top_y))

    draw.text((46, canvas_h - 40), "图注建议：训练后验证阶段筛选出的高分样例在主体结构、场景清晰度与整体观感方面表现较好，可作为不同模型优化效果展示。", fill=MUTED, font=note_f)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(OUT, quality=95)
    print(OUT)


if __name__ == "__main__":
    main()
