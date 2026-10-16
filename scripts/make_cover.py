#!/usr/bin/env python3
"""封面图合成: 底图+标题文字+署名 → 最终9:16封面"""
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

DIR = '/home/z/my-project/dalian_video'
BASE = f'{DIR}/output/cover_base.png'
OUT = f'{DIR}/output/cover_final.jpg'

W, H = 1080, 1920
img = Image.open(BASE).convert('RGB')
# 裁剪适配 1080x1920
ar = W / H
w, h = img.size
if w / h > ar:
    nw = int(h * ar)
    img = img.crop(((w - nw) // 2, 0, (w + nw) // 2, h))
else:
    nh = int(w / ar)
    img = img.crop((0, 0, w, nh))
img = img.resize((W, H), Image.LANCZOS)

# 轻微增强
img = ImageEnhance.Color(img).enhance(1.08)
img = ImageEnhance.Contrast(img).enhance(1.05)

# 顶部柔和暗化渐变（提高文字可读性）
overlay = Image.new('L', (W, H), 0)
od = ImageDraw.Draw(overlay)
for y in range(0, 700):
    v = int(80 * (1 - y / 700))
    od.line([(0, y), (W, y)], fill=v)
dark = Image.new('RGB', (W, H), (20, 30, 50))
img = Image.composite(Image.blend(img, dark, 0.5), img, overlay.point(lambda p: p))

d = ImageDraw.Draw(img)

# 字体
f_title = ImageFont.truetype('/usr/share/fonts/truetype/lxgw-wenkai/LXGWWenKai-Regular.ttf', 118)
f_sub = ImageFont.truetype('/usr/share/fonts/truetype/lxgw-wenkai/LXGWWenKai-Regular.ttf', 56)
f_tag = ImageFont.truetype('/usr/share/fonts/truetype/noto-serif-sc/NotoSerifSC-Regular.ttf', 40)

def draw_text_shadow(base_draw, pos, text, font, fill=(255, 255, 255), shadow=(15, 25, 40), offset=4, blur_alpha=120):
    """带柔和阴影的文字"""
    x, y = pos
    # 阴影层
    shadow_img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow_img)
    sd.text((x + offset, y + offset), text, font=font, fill=shadow + (blur_alpha,))
    shadow_img = shadow_img.filter(ImageFilter.GaussianBlur(6))
    base_draw._image.paste(shadow_img, (0, 0), shadow_img)
    # 主文字
    base_draw.text((x, y), text, font=font, fill=fill)

# 主标题（竖排感设计：横排大字）
title = '来自海边的信'
bbox = d.textbbox((0, 0), title, font=f_title)
tw = bbox[2] - bbox[0]
draw_text_shadow(d, ((W - tw) // 2, 150), title, f_title)

# 副标题
sub = '大连 · 浪浪的回家之旅'
bbox = d.textbbox((0, 0), sub, font=f_sub)
sw = bbox[2] - bbox[0]
draw_text_shadow(d, ((W - sw) // 2, 330), sub, f_sub, fill=(255, 240, 210))

# 底部标签
tag = '2026 动感地带 AI+ 高校创智计划'
bbox = d.textbbox((0, 0), tag, font=f_tag)
tw2 = bbox[2] - bbox[0]
# 底部半透明条
bar = Image.new('RGBA', (W, H), (0, 0, 0, 0))
bd = ImageDraw.Draw(bar)
bd.rectangle([(0, H - 130), (W, H)], fill=(15, 25, 45, 110))
img.paste(bar, (0, 0), bar)
d = ImageDraw.Draw(img)
d.text(((W - tw2) // 2, H - 105), tag, font=f_tag, fill=(225, 235, 245))

img.save(OUT, 'JPEG', quality=92)
import os
print(f'✅ 封面完成: {OUT} ({os.path.getsize(OUT)//1024}KB)')
