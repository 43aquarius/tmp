#!/usr/bin/env python3
"""
《来自海边的信》v3 合成管线 — 咪咕绘影平台AI视频为主 (13平台+5智谱)
- 12个平台图生视频(480P/720P) + 6个智谱片段混合
- 氛围镜头变速放缓(1.15-1.5x)提升电影感并保证总时长≥120s
- 旁白静音修剪 + 时序求解器(无重叠) + BGM + ASS字幕 + 文字浮现
- S18尾帧定格4s作为标题卡
用法: python3 assemble_v3.py [trim|prep|xfade|audio|final|all]
"""
import os, subprocess, sys, json

DIR = '/home/z/my-project/dalian_video'
MIGU = f'{DIR}/migu_clips'
CLIPS = f'{DIR}/clips'
AUDIO = f'{DIR}/audio'
OUT = f'{DIR}/output'
TRIM = f'{AUDIO}/trim'
os.makedirs(OUT, exist_ok=True)
os.makedirs(TRIM, exist_ok=True)

XFADE = 0.7
FINAL = f'{DIR}/来自海边的信_成片.mp4'

# ============ 时间线 v3 ============
# src: migu=平台 / zhipu=智谱
# speed: 放慢倍数(>1更慢); dur: 目标时长(秒)
TIMELINE = [
    dict(scene=1,  src='migu',  speed=1.25, narr='narr_01.wav', narr_at=1.0, sub='你有多久，没看过海了？'),
    dict(scene=2,  src='migu',  speed=1.35, narr='narr_02.wav', narr_at=0.5, sub='一根白色羽毛，悄悄落在我的窗台'),
    dict(scene=3,  src='zhipu', speed=1.0,  narr='narr_03.wav', narr_at=1.0, sub='信封上，只写了两个字'),
    dict(scene=4,  src='migu',  speed=1.25, narr='narr_04.wav', narr_at=0.8, sub='出站口的风，是咸的，也是暖的'),
    dict(scene=5,  src='migu',  speed=1.25, narr='narr_05.wav', narr_at=0.8, sub='有一只白色的小海鸥，在等我'),
    dict(scene=6,  src='migu',  speed=1.5,  narr='narr_06.wav', narr_at=0.3, sub='它叫浪浪，这片海养大的精灵'),
    dict(scene=7,  src='zhipu', speed=1.0,  narr='narr_07.wav', narr_at=0.6, sub='一百岁的老电车，还在叮叮当当地跑'),
    dict(scene=8,  src='zhipu', speed=1.0,  narr=None,           sub=None),
    dict(scene=9,  src='migu',  speed=1.25, narr='narr_09.wav', narr_at=1.0, sub='巷口的焖子，还是小时候的味道'),
    dict(scene=10, src='zhipu', speed=1.0,  narr='narr_10.wav', narr_at=1.0, sub='滨海路的风，把烦恼吹得很远'),
    dict(scene=11, src='migu',  speed=1.25, narr='narr_11.wav', narr_at=0.5, sub='海鸥会记住，每一双喂过它的手'),
    dict(scene=12, src='zhipu', speed=1.0,  narr=None,           sub=None),
    dict(scene=13, src='zhipu', speed=1.0,  narr=None,           sub=None),
    dict(scene=14, src='migu',  speed=1.15, narr='narr_14.wav', narr_at=1.5, sub='黄昏时，我又打开了那封信'),
    dict(scene=15, src='migu',  speed=1.35, narr='narr_15.wav', narr_at=0.8, sub=None),
    dict(scene=16, src='migu',  speed=1.25, narr='narr_16.wav', narr_at=1.0, sub='原来，一直记得我的，是这座城市'),
    dict(scene=17, src='migu',  speed=1.25, narr='narr_17.wav', narr_at=1.0, sub='妈，这个周末，带你来看海吧'),
    dict(scene=18, src='migu',  speed=1.15, narr='narr_18.wav', narr_at=1.0, sub=None, end_hold=4.0),
]
END_HOLD = 4.0  # S18定格

def run(cmd, tag=''):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr[-1200:])
        raise RuntimeError(f'命令失败{(":" + tag) if tag else ""}')
    return r

def probe_dur(f):
    r = subprocess.run(['ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
                        '-of', 'csv=p=0', f], capture_output=True, text=True)
    return float(r.stdout.strip())

def src_clip(item):
    d = MIGU if item['src'] == 'migu' else CLIPS
    return f"{d}/scene_{item['scene']:02d}.mp4"

def use_clip(scene):
    return f'{OUT}/usev3_{scene:02d}.mp4'

# ============ 第0步: 旁白静音修剪 ============
def trim_narrs():
    for item in TIMELINE:
        n = item['narr']
        if not n: continue
        src = f'{AUDIO}/{n}'
        dst = f'{TRIM}/{n}'
        if os.path.exists(dst):
            continue
        run(['ffmpeg', '-y', '-i', src, '-af',
             'silenceremove=start_periods=1:start_threshold=-42dB:start_silence=0.15,'
             'areverse,silenceremove=start_periods=1:start_threshold=-42dB:start_silence=0.2,areverse',
             '-c:a', 'pcm_s16le', '-ar', '44100', dst], n)
    durs = {}
    for item in TIMELINE:
        if item['narr']:
            durs[item['scene']] = probe_dur(f"{TRIM}/{item['narr']}")
    print('✅ 旁白修剪完成:', {k: round(v, 1) for k, v in durs.items()})
    return durs

# ============ 第1步: 镜头规范化 ============
def prep_clips():
    for item in TIMELINE:
        scene = item['scene']
        out = use_clip(scene)
        src = src_clip(item)
        nat = probe_dur(src)
        factor = item['speed']
        target = nat * factor + (END_HOLD if item.get('end_hold') else 0)
        if os.path.exists(out) and abs(probe_dur(out) - target) < 0.35:
            print(f'  场景{scene:02d}: 已存在 {probe_dur(out):.1f}s, 跳过')
            continue
        vf = (f"setpts={factor:.4f}*PTS,"
              f"scale=1080:1920:force_original_aspect_ratio=increase:flags=lanczos,"
              f"crop=1080:1920,format=yuv420p")
        if item.get('end_hold'):
            vf += f",tpad=stop_mode=clone:stop_duration={END_HOLD}"
        cmd = ['ffmpeg', '-y', '-i', src, '-vf', vf, '-t', f'{target:.3f}',
               '-r', '30', '-an', '-c:v', 'libx264', '-preset', 'veryfast',
               '-crf', '17', '-pix_fmt', 'yuv420p', out]
        run(cmd, f'scene{scene}')
        print(f'  场景{scene:02d}: {item["src"]}×{factor} → {probe_dur(out):.2f}s (原始{nat:.2f}s)')

# ============ 第2步: 转场拼接(分组防OOM) ============
def scene_durs():
    durs = []
    for item in TIMELINE:
        nat = probe_dur(src_clip(item))
        durs.append(nat * item['speed'] + (END_HOLD if item.get('end_hold') else 0))
    return durs

def xfade_chain(clips, out, durs):
    n = len(clips)
    if n == 1:
        run(['ffmpeg', '-y', '-i', clips[0], '-r', '30', '-c:v', 'libx264',
             '-preset', 'medium', '-crf', '17', '-pix_fmt', 'yuv420p', '-an', out])
        return out
    inputs = []
    for c in clips: inputs += ['-i', c]
    fc_parts, prev = [], '[0:v]'
    cumulative = durs[0]
    for i in range(1, n):
        offset = cumulative - XFADE
        label = f'[v{i}]' if i < n - 1 else '[vout]'
        fc_parts.append(f'{prev}[{i}:v]xfade=transition=fade:duration={XFADE}:offset={offset:.3f}{label}')
        prev = label
        cumulative = offset + durs[i]
    run(['ffmpeg', '-y', *inputs, '-filter_complex', ';'.join(fc_parts), '-map', '[vout]',
         '-r', '30', '-c:v', 'libx264', '-preset', 'medium', '-crf', '17',
         '-pix_fmt', 'yuv420p', '-an', out])
    return out

def build_visual():
    clips = [use_clip(it['scene']) for it in TIMELINE]
    durs = scene_durs()
    print(f'镜头时长: {[round(d,1) for d in durs]}')
    print(f'原始总和: {sum(durs):.1f}s, 转场后: {sum(durs) - XFADE*(len(durs)-1):.1f}s')
    groups = [(clips[0:6], durs[0:6]), (clips[6:12], durs[6:12]), (clips[12:18], durs[12:18])]
    parts = []
    for gi, (g, gd) in enumerate(groups):
        gf = f'{OUT}/v3_group{gi}.mp4'
        exp = sum(gd) - XFADE * (len(gd) - 1)
        if os.path.exists(gf) and abs(probe_dur(gf) - exp) < 0.4:
            parts.append(gf); print(f'  组{gi}: 已存在 {probe_dur(gf):.1f}s')
            continue
        xfade_chain(g, gf, gd)
        parts.append(gf)
        print(f'  组{gi}: {probe_dur(gf):.1f}s')
    out = f'{OUT}/v3_visual.mp4'
    gdurs = [probe_dur(p) for p in parts]
    if os.path.exists(out) and abs(probe_dur(out) - (sum(gdurs) - XFADE * 2)) < 0.5:
        print(f'  视觉轨已存在 {probe_dur(out):.1f}s')
        return out
    xfade_chain(parts, out, gdurs)
    print(f'  视觉轨完成: {probe_dur(out):.1f}s')
    return out

# ============ 第3步: 时序求解 + 音轨 ============
def compute_starts():
    durs = scene_durs()
    starts, t = [], 0.0
    for i, d in enumerate(durs):
        starts.append(t)
        t = t + d - XFADE if i < len(durs) - 1 else t + d
    return starts, t

def build_audio():
    starts, total = compute_starts()
    narr_durs = {}
    for item in TIMELINE:
        if item['narr']:
            narr_durs[item['scene']] = probe_dur(f"{TRIM}/{item['narr']}")
    # 时序求解: 旁白不重叠, 允许溢出到下一镜头
    placement = []
    prev_end = 0.0
    for i, item in enumerate(TIMELINE):
        if not item['narr']: continue
        desired = starts[i] + item['narr_at']
        actual = max(desired, prev_end + 0.35)
        dur = narr_durs[item['scene']]
        placement.append((i, item, actual, dur))
        prev_end = actual + dur
        if actual > desired + 0.5:
            print(f'  ⚠️ 场景{item["scene"]}旁白后移{actual-desired:.1f}s(避免重叠)')
    # 校验旁白不超出成片
    last_end = placement[-1][2] + placement[-1][3]
    if last_end > total - 1.0:
        print(f'  ⚠️ 最后旁白结束{last_end:.1f}s接近成片尾{total:.1f}s')
    json.dump({'starts': starts, 'total': total,
               'narr': {str(p[0]): [p[2], p[3]] for p in placement}},
              open(f'{OUT}/v3_timing.json', 'w'), ensure_ascii=False, indent=1)
    # ffmpeg混音
    inputs, adelay_parts, narr_parts, idx = [], [], [], 0
    for i, item, actual, dur in placement:
        inputs += ['-i', f"{TRIM}/{item['narr']}"]
        ms = int(actual * 1000)
        adelay_parts.append(f'[{idx}:a]adelay={ms}|{ms}[n{idx}]')
        narr_parts.append(f'[n{idx}]')
        idx += 1
    inputs += ['-i', f'{AUDIO}/bgm.wav']
    bgm_idx = idx
    fc_parts = adelay_parts + [
        f'[{bgm_idx}:a]atrim=0:{total:.2f},volume=0.5,'
        f'afade=t=out:st={total-3.5:.2f}:d=3.5[bgm]']
    mix_in = ''.join(narr_parts) + '[bgm]'
    fc = ';'.join(fc_parts) + f';{mix_in}amix=inputs={len(narr_parts)+1}:duration=longest:normalize=0,alimiter=limit=0.9[aout]'
    out = f'{OUT}/v3_audio.wav'
    run(['ffmpeg', '-y', *inputs, '-filter_complex', fc, '-map', '[aout]',
         '-c:a', 'pcm_s16le', '-ar', '44100', out], 'audio')
    print(f'✅ 音轨: {probe_dur(out):.1f}s, 旁白{len(placement)}段, 总长{total:.1f}s')
    return out

# ============ 第4步: 字幕 + 最终合成 ============
def ass_time(t):
    h = int(t // 3600); m = int((t % 3600) // 60); s = t % 60
    return f'{h}:{m:02d}:{s:05.2f}'

def final_render():
    timing = json.load(open(f'{OUT}/v3_timing.json'))
    starts, total = timing['starts'], timing['total']
    narr_map = timing['narr']
    events = []
    # 旁白字幕
    for i, item in enumerate(TIMELINE):
        if not item['sub'] or str(i) not in narr_map: continue
        nstart, ndur = narr_map[str(i)]
        events.append((nstart - 0.25, nstart + ndur + 0.85, 'Narr', item['sub']))
    # 文字浮现
    s3 = starts[2]
    events.append((s3 + 3.0, s3 + 7.4, 'Letter', '大{\fs58}连'))
    s15 = starts[14]
    events.append((s15 + 1.2, s15 + 5.8, 'Letter', '无论走多远\\N{\fs46}这片海，都记得你'))
    s18 = starts[17]
    hold_start = s18 + 11.65 - 0.8
    events.append((hold_start, total - 0.5, 'Title', '来自海边的信'))
    events.append((hold_start + 1.5, total - 0.5, 'TitleSub', '大 连 · 一 直 都 在'))
    events.append((0.8, 4.5, 'TitleSub', 'AI内容赛道 · 家乡文旅与国潮创新'))
    ASS_FILE = f'{OUT}/v3_subtitles.ass'
    header = '''[Script Info]
Title: 来自海边的信
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Narr,Noto Serif SC,46,&H00FFFFFF,&H000000FF,&H00000000,&H96000000,0,0,0,0,100,100,1,0,1,2.2,1.6,2,60,60,120,1
Style: Letter,LXGW WenKai,62,&H00F8E8C8,&H000000FF,&H00281810,&H96000000,0,0,0,0,100,100,2,0,1,0,2.5,3,5,60,60,1
Style: Title,LXGW WenKai,88,&H00FFFFFF,&H000000FF,&H00000000,&H96000000,0,0,0,0,100,100,4,0,1,0,3,2,5,60,60,1
Style: TitleSub,LXGW WenKai,40,&H90FFFFFF,&H000000FF,&H00000000,&H96000000,0,0,0,0,100,100,6,0,1,0,0,0,8,60,60,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''
    lines = [header]
    for start, end, style, text in sorted(events, key=lambda e: e[0]):
        fade_dur = 900 if style == 'Narr' else (1800 if 'Letter' in style or style == 'Title' else 1200)
        fade = f'{{\\fad({fade_dur},700)}}'
        pos = {'Narr': (540, 1780), 'Letter': (540, 760), 'Title': (540, 880), 'TitleSub': (540, 1020)}[style]
        fade += f'{{\\pos({pos[0]},{pos[1]})}}'
        lines.append(f'Dialogue: 0,{ass_time(start)},{ass_time(end)},{style},,0,0,0,,{fade}{text}\n')
    with open(ASS_FILE, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    print(f'✅ 字幕: {len(events)}事件')
    VISUAL, AUDIOF = f'{OUT}/v3_visual.mp4', f'{OUT}/v3_audio.wav'
    cmd = ['ffmpeg', '-y', '-i', VISUAL, '-i', AUDIOF, '-filter_complex',
           f'[0:v]ass={ASS_FILE},fade=t=in:st=0:d=1.2,fade=t=out:st={total-2.2:.1f}:d=2.2,format=yuv420p[v];'
           f'[1:a]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo[a]',
           '-map', '[v]', '-map', '[a]',
           '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18',
           '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', '-r', '30',
           FINAL]
    run(cmd, 'final')
    print(f'🎉 v3成片: {FINAL} ({os.path.getsize(FINAL)/1048576:.1f}MB, {total:.1f}s)')

if __name__ == '__main__':
    phase = sys.argv[1] if len(sys.argv) > 1 else 'all'
    if phase in ('trim', 'all'): trim_narrs()
    if phase in ('prep', 'all'): prep_clips()
    if phase in ('xfade', 'all'): build_visual()
    if phase in ('audio', 'all'): build_audio()
    if phase in ('final', 'all'): final_render()
