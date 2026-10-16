#!/usr/bin/env python3
"""PIL高速Ken Burns分镜生成器: 渲染帧序列→ffmpeg编码"""
import os, sys, subprocess
from PIL import Image, ImageFilter, ImageEnhance

DIR = '/home/z/my-project/dalian_video'
FRAMES = f'{DIR}/frames'
CLIPS = f'{DIR}/clips'
TMP = f'{DIR}/kb_tmp'
os.makedirs(TMP, exist_ok=True)
W, H, FPS = 1080, 1920, 30

MOTIONS = {
    1: ('zoom_in', 1.10), 2: ('zoom_out', 1.10), 3: ('pan_right', 1.10),
    4: ('zoom_in', 1.12), 5: ('pan_left', 1.10), 6: ('zoom_out', 1.12),
    7: ('pan_right', 1.10), 8: ('pan_left', 1.10), 9: ('zoom_in', 1.12),
    10: ('pan_right', 1.12), 11: ('zoom_out', 1.08), 12: ('pan_left', 1.10),
    13: ('zoom_in', 1.12), 14: ('zoom_in', 1.10), 15: ('zoom_out', 1.08),
    16: ('zoom_in', 1.10), 17: ('pan_right', 1.10), 18: ('zoom_out', 1.15),
}

DURS = {1:5.5, 2:10, 3:8, 4:7, 5:7, 6:11, 7:11, 8:7, 9:9.5, 10:9.5,
        11:9.5, 12:7, 13:7, 14:10, 15:7, 16:7, 17:9, 18:13}

def ease(t):
    """缓动: 平滑入出"""
    return t * t * (3 - 2 * t)

def render_kb(scene):
    dur = DURS[scene]
    motion, zoom_amt = MOTIONS[scene]
    n = int(dur * FPS)
    img = Image.open(f'{FRAMES}/scene_{scene:02d}.png').convert('RGB')
    # 预放大到安全尺寸(留出平移和缩放余量)
    base_w = int(W * 1.25)
    base_h = int(H * 1.25)
    big = img.resize((base_w, base_h), Image.LANCZOS)

    scene_tmp = f'{TMP}/s{scene:02d}'
    os.makedirs(scene_tmp, exist_ok=True)

    for f in range(n):
        t = ease(f / max(1, n - 1))  # 0→1 缓动
        if motion == 'zoom_in':
            z = 1.0 + (zoom_amt - 1.0) * t
            cx, cy = 0.5, 0.5
        elif motion == 'zoom_out':
            z = zoom_amt - (zoom_amt - 1.0) * t
            cx, cy = 0.5, 0.5
        elif motion == 'pan_right':
            z = 1.0
            cx = 0.45 + 0.1 * t
            cy = 0.5
        elif motion == 'pan_left':
            z = 1.0
            cx = 0.55 - 0.1 * t
            cy = 0.5
        else:
            z, cx, cy = 1.05, 0.5, 0.5

        # 当前缩放的窗口尺寸
        win_w = int(base_w / z)
        win_h = int(base_h / z)
        # 中心点
        px = int(base_w * cx)
        py = int(base_h * cy)
        # 计算crop窗口
        left = max(0, min(base_w - win_w, px - win_w // 2))
        top = max(0, min(base_h - win_h, py - win_h // 2))
        crop = big.crop((left, top, left + win_w, top + win_h))
        if crop.size != (W, H):
            # 保持宽高比裁剪到1080x1920
            ar = W / H
            cw, ch = crop.size
            if cw / ch > ar:
                nw = int(ch * ar)
                x0 = (cw - nw) // 2
                crop = crop.crop((x0, 0, x0 + nw, ch))
            else:
                nh = int(cw / ar)
                y0 = (ch - nh) // 2
                crop = crop.crop((0, y0, cw, y0 + nh))
            frame = crop.resize((W, H), Image.BILINEAR)
        else:
            frame = crop
        frame.save(f'{scene_tmp}/f{f:05d}.jpg', quality=92)

    # ffmpeg编码帧序列
    out = f'{CLIPS}/kb_{scene:02d}.mp4'
    cmd = ['ffmpeg', '-y', '-framerate', str(FPS), '-i', f'{scene_tmp}/f%05d.jpg',
           '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18',
           '-pix_fmt', 'yuv420p', '-movflags', '+faststart', out]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr[-500:])
        raise RuntimeError(f'场景{scene}编码失败')
    # 清理帧
    for f in os.listdir(scene_tmp):
        os.remove(f'{scene_tmp}/{f}')
    os.rmdir(scene_tmp)
    return out

if __name__ == '__main__':
    scenes = [int(x) for x in sys.argv[1:]] if len(sys.argv) > 1 else list(range(1, 19))
    for s in scenes:
        out = f'{CLIPS}/kb_{s:02d}.mp4'
        if os.path.exists(out) and os.path.getsize(out) > 100000:
            print(f'场景{s:02d} 已存在')
            continue
        print(f'场景{s:02d}: 渲染{DURS[s]}s × {FPS}fps ...', flush=True)
        render_kb(s)
        print(f'场景{s:02d} ✅ {os.path.getsize(out)//1024}KB', flush=True)
    print('全部完成')
