#!/usr/bin/env python3
"""
《来自海边的信》主合成管线
- AI视频片段优先，缺失的分镜用Ken Burns动态图补齐
- 旁白精准对位 + BGM + ASS字幕 + 光效文字浮现
- 输出1080x1920竖屏成片
"""
import json, os, subprocess, sys

DIR = '/home/z/my-project/dalian_video'
FRAMES = f'{DIR}/frames'
CLIPS = f'{DIR}/clips'
AUDIO = f'{DIR}/audio'
OUT = f'{DIR}/output'
os.makedirs(OUT, exist_ok=True)

FONTS = {
    'hei': '/usr/share/fonts/truetype/noto-serif-sc/NotoSerifSC-Regular.ttf',
    'wenkai': '/usr/share/fonts/truetype/lxgw-wenkai/LXGWWenKai-Regular.ttf',
}
for k, v in FONTS.items():
    if not os.path.exists(v):
        print(f'⚠️ 字体缺失: {v}')

# ============ 时间线定义 ============
# dur: 该镜头时长; narr: 旁白文件; narr_at: 旁白在镜头内的起始偏移; text: 浮现文字
TIMELINE = [
    dict(scene=1,  dur=5.5,  narr='narr_01.wav', narr_at=1.2, sub='你有多久，没看过海了？', motion='zoom_in'),
    dict(scene=2,  dur=10.0, narr='narr_02.wav', narr_at=2.0, sub='一根白色羽毛，悄悄落在我的窗台', motion='zoom_out'),
    dict(scene=3,  dur=8.0,  narr='narr_03.wav', narr_at=1.5, sub='信封上只写了两个字', text=('大连', 55, 0.62, 0.40, 'wenkai', 1.5), motion='pan_right'),
    dict(scene=4,  dur=7.0,  narr='narr_04.wav', narr_at=1.0, sub='出站口的风，是咸的，也是暖的', motion='zoom_in'),
    dict(scene=5,  dur=7.0,  narr='narr_05.wav', narr_at=0.8, sub='有一只白色的小海鸥，在等我', motion='pan_left'),
    dict(scene=6,  dur=11.0, narr='narr_06.wav', narr_at=0.8, sub='它叫浪浪，这片海养大的精灵', motion='zoom_out'),
    dict(scene=7,  dur=11.0, narr='narr_07.wav', narr_at=0.6, sub='一百岁的老电车，叮叮当当', motion='pan_right'),
    dict(scene=8,  dur=7.0,  narr=None,           sub=None, motion='pan_left'),
    dict(scene=9,  dur=9.5,  narr='narr_09.wav', narr_at=1.0, sub='巷口的焖子，还是那个味道', motion='zoom_in'),
    dict(scene=10, dur=9.5,  narr='narr_10.wav', narr_at=1.0, sub='滨海路的风，把烦恼吹得很远', motion='pan_right'),
    dict(scene=11, dur=9.5,  narr='narr_11.wav', narr_at=0.5, sub='海鸥会记住每一双喂过它的手', motion='zoom_out'),
    dict(scene=12, dur=7.0,  narr=None,           sub=None, motion='pan_left'),
    dict(scene=13, dur=7.0,  narr=None,           sub=None, motion='zoom_in'),
    dict(scene=14, dur=10.0, narr='narr_14.wav', narr_at=1.5, sub='我又打开了那封信', motion='zoom_in'),
    dict(scene=15, dur=7.0,  narr='narr_15.wav', narr_at=0.8, sub='无论走多远', text=('无论走多远\n这片海，都记得你', 46, 0.50, 0.45, 'wenkai', 2.0), motion='zoom_out'),
    dict(scene=16, dur=7.0,  narr='narr_16.wav', narr_at=1.0, sub='一直记得我的，是这座城市', motion='zoom_in'),
    dict(scene=17, dur=9.0,  narr='narr_17.wav', narr_at=1.5, sub='妈，这个周末，带你来看海吧', motion='pan_right'),
    dict(scene=18, dur=13.0, narr='narr_18.wav', narr_at=1.0, sub='大连，一直都在', text=('来自海边的信', 72, 0.50, 0.42, 'wenkai', 2.5), motion='zoom_out'),
]

XFADE = 0.8  # 转场时长

def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr[-1500:])
        raise RuntimeError(f'命令失败: {" ".join(cmd[:8])}...')
    return r

def probe_dur(f):
    r = subprocess.run(['ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
                        '-of', 'csv=p=0', f], capture_output=True, text=True)
    return float(r.stdout.strip())

# ============ 第1步: 准备各镜头片段 ============
def make_kb_clip(scene, dur, motion):
    """Ken Burns片段: 由gen_kb.py预生成, 此处校验时长后直接使用"""
    out = f'{CLIPS}/kb_{scene:02d}.mp4'
    if not os.path.exists(out):
        raise RuntimeError(f'缺少Ken Burns片段: {out}, 请先运行 gen_kb.py {scene}')
    return out
    # 768x1344 → 1080x1920: 先放大到能覆盖平移范围的尺寸
    W, H = 1080, 1920
    # Ken Burns参数: 缩放范围+位移
    if motion == 'zoom_in':
        z0, z1 = 1.0, 1.18
        x0, y0, x1, y1 = 0, 0, 0, 0
    elif motion == 'zoom_out':
        z0, z1 = 1.18, 1.0
        x0, y0, x1, y1 = 0, 0, 0, 0
    elif motion == 'pan_right':
        z0 = z1 = 1.12
        x0, x1 = -60, 60; y0 = y1 = 0
    elif motion == 'pan_left':
        z0 = z1 = 1.12
        x0, x1 = 60, -60; y0 = y1 = 0
    else:
        z0 = z1 = 1.05
        x0, x1, y0, y1 = 0, 0, 0, 0

    # zoompan: 输入先scale放大保证画质, zoompan输出1080x1920
    # zoompan公式: s=1080x1920, zoom从z0到z1线性, x/y随时间线性
    nframes = int(dur * 30)
    zf = f"zoompan=z='if(lte(on,1),{z0},{z0}+({z1}-{z0})*on/{nframes})'"
    xf = f"x='iw/2-(iw/zoom/2)+({x0}+({x1}-{x0})*on/{nframes})'"
    yf = f"y='ih/2-(ih/zoom/2)+({y0}+({y1}-{y0})*on/{nframes})'"

    vf = (f"scale=1296:2268:flags=lanczos,"
          f"{zf}:x={xf}:y={yf}:d=1:s=1080x1920:fps=30,"
          f"format=yuv420p")
    cmd = ['ffmpeg', '-y', '-loop', '1', '-i', frame,
           '-t', str(dur), '-vf', vf, '-r', '30',
           '-c:v', 'libx264', '-preset', 'medium', '-crf', '18',
           '-pix_fmt', 'yuv420p', out]
    run(cmd)
    return out

def get_scene_clip(item):
    """优先AI视频(精确匹配目标时长), 否则Ken Burns"""
    scene, dur = item['scene'], item['dur']
    ai = f'{CLIPS}/scene_{scene:02d}.mp4'
    if os.path.exists(ai):
        nat = probe_dur(ai)
        out = f'{CLIPS}/use_{scene:02d}.mp4'
        if os.path.exists(out) and abs(probe_dur(out) - dur) < 0.3:
            return out
        if nat >= dur * 0.75:  # AI片段够长才用
            if abs(nat - dur) < 0.3:
                vf = 'scale=1080:1920:flags=lanczos,format=yuv420p'
                t_arg = str(dur + 0.2)
            elif nat < dur:
                factor = nat / dur
                vf = f'setpts={1/factor:.5f}*PTS,scale=1080:1920:flags=lanczos,format=yuv420p'
                t_arg = str(dur + 0.1)
            else:
                vf = 'scale=1080:1920:flags=lanczos,format=yuv420p'
                t_arg = str(dur)
            run(['ffmpeg', '-y', '-i', ai, '-vf', vf, '-t', t_arg, '-r', '30',
                 '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18', '-an', out])
            actual = probe_dur(out)
            if abs(actual - dur) < 0.5:
                return out
            print(f'  ⚠️ 场景{scene} AI片时长异常({actual:.1f}s vs {dur}s), 回退KB')
    return make_kb_clip(scene, dur, item.get('motion', 'zoom_in'))

# ============ 第2步: 转场拼接 ============
def concat_with_xfade(clips):
    """chain xfade拼接所有片段, 返回总时长"""
    n = len(clips)
    if n == 1:
        return clips[0], probe_dur(clips[0])
    inputs = []
    for c in clips:
        inputs += ['-i', c]
    # 逐级xfade
    fc_parts = []
    prev = '[0:v]'
    cumulative = probe_dur(clips[0])
    for i in range(1, n):
        offset = cumulative - XFADE
        label = f'[v{i}]' if i < n - 1 else '[vout]'
        fc_parts.append(f'{prev}[{i}:v]xfade=transition=fade:duration={XFADE}:offset={offset:.3f}{label}')
        prev = label
        cumulative = offset + probe_dur(clips[i])
    fc = ';'.join(fc_parts)
    out = f'{OUT}/visual_base.mp4'
    run(['ffmpeg', '-y', *inputs, '-filter_complex', fc, '-map', '[vout]',
         '-r', '30', '-c:v', 'libx264', '-preset', 'medium', '-crf', '17',
         '-pix_fmt', 'yuv420p', out])
    return out, cumulative

# ============ 第3步: 音轨合成 ============
def build_audio(total_dur):
    """旁白按镜头起始时间排布 + BGM铺底"""
    # 计算各镜头在成片中的实际起始时间(xfade偏移)
    starts = []
    t = 0.0
    # 偏移逻辑与拼接一致
    t = 0.0
    for idx, item in enumerate(TIMELINE):
        starts.append(t)
        t = t + item['dur'] - XFADE if idx < len(TIMELINE) - 1 else t + item['dur']
    print(f'总时长: {t:.1f}s (目标≥120s)')

    narr_inputs = []
    narr_parts = []
    adelay_parts = []
    idx = 0
    for i, item in enumerate(TIMELINE):
        if item['narr']:
            narr_file = f'{AUDIO}/{item["narr"]}'
            if not os.path.exists(narr_file):
                print(f'⚠️ 缺旁白 {narr_file}')
                continue
            narr_inputs += ['-i', narr_file]
            start_at = starts[i] + item['narr_at']
            adelay_parts.append(f'[{idx}:a]adelay={int(start_at*1000)}|{int(start_at*1000)}[n{idx}]')
            narr_parts.append(f'[n{idx}]')
            idx += 1
    # BGM
    bgm_dur = probe_dur(f'{AUDIO}/bgm.wav')
    inputs = narr_inputs + ['-i', f'{AUDIO}/bgm.wav']
    bgm_idx = idx
    # BGM截到成片时长, 若不够则循环
    if bgm_dur < t:
        loop = f'aloop=loop={int(t/bgm_dur)+1}:size={int(bgm_dur*44100)}'
    else:
        loop = 'anull'
    bgm_part = f'[{bgm_idx}:a]{loop},atrim=0:{t:.2f},volume=0.55[bgm]'
    # 混音
    if narr_parts:
        mix_in = ''.join(narr_parts) + '[bgm]'
        fc = ';'.join(adelay_parts + [bgm_part]) + f';{mix_in}amix=inputs={len(narr_parts)+1}:duration=longest:normalize=0,alimiter=limit=0.9[aout]'
    else:
        fc = f'{bgm_part};[bgm]volume=0.6[aout]'
    out = f'{OUT}/audio_mix.wav'
    run(['ffmpeg', '-y', *inputs, '-filter_complex', fc, '-map', '[aout]',
         '-c:a', 'pcm_s16le', '-ar', '44100', out])
    return out, t

# ============ 主流程 ============
if __name__ == '__main__':
    print('===== 第1步: 准备镜头 =====')
    clips = []
    for item in TIMELINE:
        c = get_scene_clip(item)
        tag = 'AI' if f'scene_{item["scene"]:02d}' in c and 'kb' not in c and 'use' in c else 'KB'
        clips.append(c)
        print(f'  场景{item["scene"]:02d}: {os.path.basename(c)} ({tag})')
    print('===== 第2步: 转场拼接 =====')
    visual, vlen = concat_with_xfade(clips)
    print(f'  视觉轨: {vlen:.1f}s')
    print('===== 第3步: 音轨 =====')
    audio, alen = build_audio(vlen)
    print(f'  音轨: {alen:.1f}s')
    print('完成基础三步, 字幕与文字层由 subtitle+text 脚本处理')
