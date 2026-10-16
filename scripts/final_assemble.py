#!/usr/bin/env python3
"""最终合成: 视觉轨+音轨+ASS字幕+文字浮现+淡入淡出 → 成片"""
import os, subprocess

DIR = '/home/z/my-project/dalian_video'
OUT = f'{DIR}/output'
VISUAL = f'{OUT}/visual_base.mp4'
AUDIO = f'{OUT}/audio_mix.wav'
ASS_FILE = f'{OUT}/subtitles.ass'
FINAL = f'{DIR}/来自海边的信_成片.mp4'

XFADE = 0.8
# 时间线(与assemble.py一致)
TIMELINE = [
    dict(scene=1,  dur=5.5,  narr_at=1.2, sub='你有多久，没看过海了？'),
    dict(scene=2,  dur=10.0, narr_at=2.0, sub='一根白色羽毛，悄悄落在我的窗台'),
    dict(scene=3,  dur=8.0,  narr_at=1.5, sub='信封上，只写了两个字'),
    dict(scene=4,  dur=7.0,  narr_at=1.0, sub='出站口的风，是咸的，也是暖的'),
    dict(scene=5,  dur=7.0,  narr_at=0.8, sub='有一只白色的小海鸥，在等我'),
    dict(scene=6,  dur=11.0, narr_at=0.8, sub='它叫浪浪，这片海养大的精灵'),
    dict(scene=7,  dur=11.0, narr_at=0.6, sub='一百岁的老电车，还在叮叮当当地跑'),
    dict(scene=8,  dur=7.0,  narr_at=None, sub=None),
    dict(scene=9,  dur=9.5,  narr_at=1.0, sub='巷口的焖子，还是小时候的味道'),
    dict(scene=10, dur=9.5,  narr_at=1.0, sub='滨海路的风，把烦恼吹得很远'),
    dict(scene=11, dur=9.5,  narr_at=0.5, sub='海鸥会记住，每一双喂过它的手'),
    dict(scene=12, dur=7.0,  narr_at=None, sub=None),
    dict(scene=13, dur=7.0,  narr_at=None, sub=None),
    dict(scene=14, dur=10.0, narr_at=1.5, sub='黄昏时，我又打开了那封信'),
    dict(scene=15, dur=7.0,  narr_at=0.8, sub=None),  # 信件文字单独浮现
    dict(scene=16, dur=7.0,  narr_at=1.0, sub='原来，一直记得我的，是这座城市'),
    dict(scene=17, dur=9.0,  narr_at=1.5, sub='妈，这个周末，带你来看海吧'),
    dict(scene=18, dur=13.0, narr_at=1.0, sub=None),  # 标题卡
]
# 旁白音频时长
NARR_DUR = {1: 2.11, 2: 6.66, 3: 3.67, 4: 3.97, 5: 3.42, 6: 9.57, 7: 9.99,
            9: 5.14, 10: 5.23, 11: 8.51, 14: 6.49, 15: 4.97, 16: 3.76, 17: 3.71, 18: 1.57}

def ass_time(t):
    h = int(t // 3600); m = int((t % 3600) // 60); s = t % 60
    return f'{h}:{m:02d}:{s:05.2f}'

# 计算场景起始时间
starts = []
t = 0.0
for i, item in enumerate(TIMELINE):
    starts.append(t)
    t = t + item['dur'] - XFADE if i < len(TIMELINE) - 1 else t + item['dur']
TOTAL = t
print(f'成片总长: {TOTAL:.1f}s')

events = []

# ---- 旁白字幕(底部, 优雅衬线) ----
for i, item in enumerate(TIMELINE):
    if not item['sub'] or not item['narr_at']:
        continue
    start = starts[i] + item['narr_at'] - 0.25
    dur = NARR_DUR.get(item['scene'], 3.0)
    end = start + dur + 0.85
    text = item['sub'].replace('，', '，')
    events.append((start, end, 'Narr', text))

# ---- 文字浮现层 ----
# 场景3: 信封上的"大连" (钢笔字感觉)
s3 = starts[2]
events.append((s3 + 3.2, s3 + 7.6, 'Letter', '大{\fs58}连'))
# 场景15: 信件内容浮现
s15 = starts[14]
events.append((s15 + 1.3, s15 + 6.5, 'Letter', '无论走多远\\N{\fs46}这片海，都记得你'))
# 场景18: 标题卡
s18 = starts[17]
events.append((s18 + 3.0, s18 + 12.0, 'Title', '来自海边的信'))
events.append((s18 + 4.5, s18 + 12.0, 'TitleSub', '大 连 · 一 直 都 在'))
# 片头小字
events.append((0.8, 4.5, 'TitleSub', 'AI内容赛道 · 家乡文旅与国潮创新'))

ASS_HEADER = '''[Script Info]
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

lines = [ASS_HEADER]
for start, end, style, text in sorted(events, key=lambda e: e[0]):
    fade_dur = 900 if style == 'Narr' else (1800 if 'Letter' in style or style == 'Title' else 1200)
    fade = f'{{\\fad({fade_dur},700)}}'
    if style == 'Narr':
        fade += '{\\pos(540,1780)}'
    elif style == 'Letter':
        # 信件文字位置偏中上
        fade += '{\\pos(540,760)}'
    elif style == 'Title':
        fade += '{\\pos(540,880)}'
    elif style == 'TitleSub':
        fade += '{\\pos(540,1020)}'
    lines.append(f'Dialogue: 0,{ass_time(start)},{ass_time(end)},{style},,0,0,0,,{fade}{text}\n')

with open(ASS_FILE, 'w', encoding='utf-8') as f:
    f.writelines(lines)
print(f'✅ ASS字幕: {len(events)}个事件 → {ASS_FILE}')

# ---- 最终合成 ----
cmd = [
    'ffmpeg', '-y',
    '-i', VISUAL,
    '-i', AUDIO,
    '-filter_complex',
    f'[0:v]ass={ASS_FILE},'
    f'fade=t=in:st=0:d=1.2,'
    f'fade=t=out:st={TOTAL-2.2:.1f}:d=2.2,'
    f'format=yuv420p[v];'
    f'[1:a]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo[a]',
    '-map', '[v]', '-map', '[a]',
    '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18',
    '-c:a', 'aac', '-b:a', '192k',
    '-movflags', '+faststart',
    '-r', '30',
    FINAL,
]
print('渲染最终成片...')
r = subprocess.run(cmd, capture_output=True, text=True)
if r.returncode != 0:
    print(r.stderr[-2000:])
    raise RuntimeError('最终合成失败')
sz = os.path.getsize(FINAL) / 1048576
print(f'🎉 成片完成: {FINAL} ({sz:.1f}MB)')
