#!/usr/bin/env python3
"""
《来自海边的信》BGM合成器 - 治愈系钢琴曲
结构（对应18镜叙事）:
  0:00-0:20  引子(冷清稀疏) 异乡雨夜
  0:20-0:35  转折(希望浮现) 收到信
  0:35-1:10  主题A(温暖流动) 重游大连
  1:10-1:25  间奏(宁静) 童年闪回
  1:25-1:50  主题A'(情感递进) 信的秘密
  1:50-2:25  尾声(明亮释然) 日出与归家
采样率: 44100Hz 立体声
"""
import numpy as np
from scipy.io import wavfile
import random

SR = 44100
random.seed(42)

def note_freq(midi):
    return 440.0 * (2 ** ((midi - 69) / 12))

def piano_note(freq, duration, velocity=0.7, brightness=1.0):
    """合成钢琴音色: 多谐波+指数衰减+轻微失谐"""
    n = int(SR * duration)
    t = np.linspace(0, duration, n, endpoint=False)
    # 谐波分量
    wave = np.zeros(n)
    harmonics = [(1, 1.0), (2, 0.45 * brightness), (3, 0.22 * brightness),
                 (4, 0.12 * brightness), (5, 0.06 * brightness), (6, 0.03)]
    for h, amp in harmonics:
        # 轻微失谐增加温暖感
        detune = 1 + random.uniform(-0.0004, 0.0004)
        wave += amp * np.sin(2 * np.pi * freq * h * detune * t)
    # 双弦感: 轻微延迟的第二层
    offset = int(SR * 0.003)
    layer2 = np.zeros(n)
    m = max(0, offset)
    layer2[m:] = 0.3 * np.sin(2 * np.pi * freq * 1.001 * t)[m:n - m + m] if n > m else layer2
    wave = wave + 0.25 * layer2
    # 起音攻击(钢琴特点: 快速起音)
    attack = int(SR * 0.004)
    env = np.ones(n)
    env[:attack] = np.linspace(0, 1, attack)
    # 双段衰减: 快速初始衰减+长尾
    decay = np.exp(-t * 1.8) * 0.6 + np.exp(-t * 0.5) * 0.4
    env = env * decay
    # 释音: 结尾淡出避免爆音
    release = int(SR * 0.05)
    if n > release:
        env[-release:] *= np.linspace(1, 0, release)
    return wave * env * velocity

def pad_chord(freqs, duration, velocity=0.25):
    """合成温暖弦乐垫: 缓慢起音的正弦叠加+微颤"""
    n = int(SR * duration)
    t = np.linspace(0, duration, n, endpoint=False)
    wave = np.zeros(n)
    for f in freqs:
        vib = 1 + 0.002 * np.sin(2 * np.pi * 4.5 * t + random.uniform(0, 6))
        wave += np.sin(2 * np.pi * f * vib * t) + 0.4 * np.sin(2 * np.pi * f * 2.001 * t) * 0.1
    # 缓慢起音和释音
    attack = int(SR * min(1.5, duration * 0.4))
    release = int(SR * min(2.0, duration * 0.35))
    env = np.ones(n)
    env[:attack] = np.linspace(0, 1, attack) ** 2
    env[-release:] *= np.linspace(1, 0, release) ** 1.5
    return wave * env * velocity / len(freqs)

def add_track(master, track, start_sec, pan=0.0, gain=1.0):
    """把音轨叠加到主时间线, track可为单声道(1D)或立体声(2D), pan: -1左到1右"""
    start = int(start_sec * SR)
    if start >= len(master):
        return
    if track.ndim == 1:
        # 单声道 → 按pan分配到两声道
        l_gain = np.sqrt(0.5 * (1 - pan))
        r_gain = np.sqrt(0.5 * (1 + pan))
        end = min(len(master), start + len(track))
        seg = (track * gain)[:end - start]
        master[start:end, 0] += seg * l_gain
        master[start:end, 1] += seg * r_gain
    else:
        # 立体声 → 直接叠加(pan作用于平衡)
        end = min(len(master), start + len(track))
        seg = (track * gain)[:end - start]
        l_gain = np.sqrt(2.0 * (1 - max(0, pan)))
        r_gain = np.sqrt(2.0 * (1 + min(0, pan)))
        master[start:end, 0] += seg[:, 0] * l_gain
        master[start:end, 1] += seg[:, 1] * r_gain

def simple_reverb(audio, decay=0.35, delays_ms=[83, 127, 173, 211, 293]):
    """简易多抽头混响"""
    out = audio.copy()
    for d_ms in delays_ms:
        delay = int(SR * d_ms / 1000)
        shifted = np.zeros_like(audio)
        shifted[delay:] = audio[:-delay] * (decay ** (d_ms / 100))
        out += shifted
    return out * 0.7

# ========== 主时间线 ==========
TOTAL = 148  # 秒
master = np.zeros((int(SR * TOTAL), 2))

# ---- 和弦进行定义 (C大调系, 温暖治愈) ----
# 乐器音域: 右手旋律 C5-A5, 左手伴奏 C3-A3
G = lambda name: name  # 可读性

# 段落1: 引子 0-20s (C大调 → Am, 冷清)
intro_melody = [
    (4, 0.0, 2.0, 0.45),   # E5
    (2, 3.0, 2.0, 0.40),   # D5  
    (0, 6.0, 3.0, 0.42),   # C5
    (4, 10.0, 2.0, 0.38),  # E5
    (3, 13.5, 1.5, 0.35),  # D#5(Eb)
    (2, 15.5, 3.0, 0.40),  # D5
]
intro_bass = [
    (24, 0.0, 4.0, 0.5),   # C3
    (21, 4.0, 4.0, 0.5),   # A2
    (24, 8.0, 4.0, 0.5),   # C3
    (19, 12.0, 4.0, 0.5),  # G2
    (21, 16.0, 4.0, 0.5),  # A2
]

# 段落2: 转折 20-35s (F → G → C, 希望浮现)
trans_melody = [
    (5, 20.0, 1.8, 0.5),   # F5
    (7, 22.0, 1.8, 0.5),   # G5
    (9, 24.0, 2.5, 0.55),  # A5
    (7, 27.0, 1.5, 0.45),
    (4, 29.0, 2.0, 0.5),   # E5
    (0, 32.0, 2.8, 0.52),  # C5
]
trans_bass = [
    (17, 20.0, 4.0, 0.5),  # F2
    (19, 24.0, 4.0, 0.5),  # G2
    (24, 28.0, 4.0, 0.5),  # C3
    (16, 32.0, 3.0, 0.5),  # E2
]

# 段落3: 主题A 35-70s (C-Am-F-G 循环, 温暖流动) 主旋律是海的感觉
themeA = [
    # 第1句 (C - Am)
    (4, 35.0, 1.2, 0.6), (7, 36.4, 1.2, 0.6), (9, 37.8, 1.4, 0.65), (12, 39.4, 1.8, 0.62),
    (9, 41.4, 1.2, 0.55), (7, 42.8, 1.2, 0.5), (4, 44.2, 2.2, 0.55),
    # 第2句 (F - G)
    (5, 47.0, 1.2, 0.6), (9, 48.4, 1.2, 0.6), (12, 49.8, 1.4, 0.65), (14, 51.4, 1.8, 0.6),
    (12, 53.4, 1.2, 0.55), (11, 54.8, 1.2, 0.5), (7, 56.2, 2.4, 0.55),
    # 第3句 变化
    (9, 59.5, 1.5, 0.6), (12, 61.2, 1.5, 0.62), (16, 62.9, 2.0, 0.65),
    (14, 65.2, 1.5, 0.55), (12, 66.9, 1.5, 0.5), (9, 68.6, 1.5, 0.5),
]
themeA_bass = [
    (36, 35.0, 3.8, 0.55), (33, 38.8, 3.8, 0.55),   # C2-E2琶音
    (29, 42.6, 3.8, 0.55), (31, 46.4, 3.8, 0.55),   # F2-G2
    (36, 50.2, 3.8, 0.55), (33, 54.0, 3.8, 0.55),
    (29, 57.8, 3.8, 0.55), (31, 61.6, 3.8, 0.55),
    (36, 65.4, 3.8, 0.55), (28, 69.2, 3.0, 0.5),
]
# 主题A琶音伴奏(轻柔波浪感)
arp_sectionA = (35.0, 35.0)  # 35-70s

# 段落4: 间奏 70-85s (宁静 Am-F 悬浮感)
bridge_melody = [
    (9, 70.5, 3.0, 0.5), (12, 74.0, 3.0, 0.48), (9, 77.5, 2.5, 0.45), (7, 80.5, 3.5, 0.42),
]
bridge_bass = [
    (21, 70.0, 6.5, 0.45), (17, 76.5, 6.5, 0.45), (19, 83.0, 2.0, 0.4),
]

# 段落5: 主题A' 85-115s (情感递进, 高八度+更饱满)
themeB = [
    (16, 85.0, 1.1, 0.62), (19, 86.3, 1.1, 0.62), (21, 87.6, 1.3, 0.66), (24, 89.1, 1.7, 0.64),
    (21, 91.0, 1.1, 0.58), (19, 92.3, 1.1, 0.52), (16, 93.6, 2.2, 0.56),
    (17, 96.5, 1.1, 0.6), (21, 97.8, 1.1, 0.6), (24, 99.1, 1.3, 0.65), (26, 100.7, 1.7, 0.62),
    (24, 102.6, 1.1, 0.55), (23, 103.9, 1.1, 0.5), (19, 105.2, 2.3, 0.55),
    (21, 108.0, 1.4, 0.6), (24, 109.7, 1.4, 0.6), (28, 111.4, 2.2, 0.62),
    (26, 113.8, 1.5, 0.5), (24, 115.5, 1.5, 0.45), (21, 117.2, 2.0, 0.45),
]
themeB_bass = [
    (36, 85.0, 3.8, 0.55), (33, 88.8, 3.8, 0.55),
    (29, 92.6, 3.8, 0.55), (31, 96.4, 3.8, 0.55),
    (36, 100.2, 3.8, 0.55), (33, 104.0, 3.8, 0.55),
    (29, 107.8, 3.8, 0.55), (31, 111.6, 3.8, 0.55),
    (36, 115.4, 3.5, 0.5),
]

# 段落6: 尾声 120-148s (C-G-Am-F → C 明亮释然)
ending_melody = [
    (12, 120.0, 1.5, 0.55), (16, 121.7, 1.5, 0.55), (19, 123.4, 2.2, 0.6),
    (17, 125.8, 1.5, 0.5), (16, 127.5, 1.5, 0.45), (12, 129.2, 2.5, 0.5),
    (14, 132.0, 1.5, 0.5), (12, 133.7, 1.5, 0.45), (9, 135.4, 2.6, 0.48),
    (7, 138.2, 2.0, 0.42), (4, 140.5, 2.5, 0.4), (0, 143.2, 4.5, 0.38),
]
ending_bass = [
    (24, 120.0, 3.8, 0.5), (19, 123.8, 3.8, 0.5),
    (21, 127.6, 3.8, 0.5), (17, 131.4, 3.8, 0.5),
    (24, 135.2, 3.8, 0.5), (19, 139.0, 3.8, 0.45),
    (24, 143.0, 5.0, 0.4),
]

# ---- 渲染函数 ----
def midi_offset(base_midi, offset):
    return note_freq(base_midi + offset)

# C大调基准: 音阶 0=C,2=D,4=E,5=F,7=G,9=A,11=B 相对C5(72)
BASE = 72  # C5

def render_notes(master, notes, base_midi=72, pan=0.15, gain=1.0, brightness=1.0):
    for offset, start, dur, vel in notes:
        freq = note_freq(base_midi + offset)
        track = piano_note(freq, dur + 1.5, vel * 0.35 * gain, brightness)  # 加余音
        add_track(master, track, start, pan=pan)

def render_notes_bass(master, notes, base_midi=48, pan=-0.2, gain=1.0):
    for offset, start, dur, vel in notes:
        freq = note_freq(base_midi + (offset - 24))
        track = piano_note(freq, dur + 2.0, vel * 0.5 * gain, 0.7)
        add_track(master, track, start, pan=pan)

# 和弦垫
def render_pads(master, start, dur, chord_midis, velocity=0.16, pan=0.0):
    freqs = [note_freq(m) for m in chord_midis]
    track = pad_chord(freqs, dur, velocity)
    add_track(master, track, start, pan=pan)

# ========== 分段落渲染 ==========
# 段落1: 引子 (清冷, 少垫)
render_notes(master, intro_melody, 72, 0.2, 0.8, 0.6)
render_notes_bass(master, intro_bass, 48, -0.3, 0.7)
render_pads(master, 0, 20, [48, 55, 60, 64], 0.10)   # C小三和弦感 Am add

# 段落2: 转折 (渐暖)
render_notes(master, trans_melody, 72, 0.15, 0.95)
render_notes_bass(master, trans_bass, 48, -0.25)
render_pads(master, 20, 15, [53, 60, 65, 69], 0.13)  # F大调垫
render_pads(master, 24, 11, [55, 62, 67, 71], 0.12)  # G

# 段落3: 主题A (温暖流动+琶音)
render_notes(master, themeA, 72, 0.18, 1.0)
render_notes_bass(master, themeA_bass, 48, -0.25)
render_pads(master, 35, 16, [48, 55, 64, 67], 0.15)  # C
render_pads(master, 43, 14, [45, 52, 57, 64], 0.14)  # Am
render_pads(master, 51, 16, [41, 48, 57, 60], 0.15)  # F
render_pads(master, 59, 15, [43, 50, 55, 62], 0.14)  # G
# 琶音波浪 (35-70s)
arp_notes = []
t = 35.0
arp_pattern = [0, 4, 7, 12, 16, 12, 7, 4]  # C大调琶音
chord_roots = [48, 45, 41, 43, 48, 45, 41, 43]
ci = 0
while t < 69:
    root = chord_roots[ci % len(chord_roots)]
    for step in [0, 4, 7]:
        arp_notes.append((root + step - 72 + 24, t, 0.55, 0.16))
        t += 0.55
    ci += 1
render_notes(master, arp_notes, 60, 0.35, 0.55, 0.85)

# 段落4: 间奏 (宁静)
render_notes(master, bridge_melody, 72, 0.25, 0.7, 0.75)
render_notes_bass(master, bridge_bass, 48, -0.3)
render_pads(master, 70, 15, [45, 52, 60, 64], 0.12)  # Am

# 段落5: 主题A' (高八度, 情感递进)
render_notes(master, themeB, 72, 0.1, 1.05)
render_notes_bass(master, themeB_bass, 48, -0.25)
render_pads(master, 85, 16, [48, 55, 64, 67], 0.16)
render_pads(master, 93, 14, [45, 52, 57, 64], 0.15)
render_pads(master, 101, 16, [41, 48, 57, 60], 0.16)
render_pads(master, 109, 15, [43, 50, 55, 62], 0.15)
# 更密的琶音
arp2 = []
t = 85.0
ci = 0
while t < 118:
    root = chord_roots[ci % len(chord_roots)]
    for step in [0, 4, 7, 12]:
        arp2.append((root + step - 72 + 24, t, 0.4, 0.15))
        t += 0.4
    ci += 1
render_notes(master, arp2, 60, 0.4, 0.5, 0.9)

# 段落6: 尾声 (明亮)
render_notes(master, ending_melody, 72, 0.15, 1.0)
render_notes_bass(master, ending_bass, 48, -0.25)
render_pads(master, 120, 13, [48, 55, 64, 67], 0.15)
render_pads(master, 127, 13, [45, 52, 57, 64], 0.14)
render_pads(master, 133, 13, [41, 48, 57, 60], 0.15)
render_pads(master, 139, 9, [36, 48, 55, 64], 0.14)  # C收束

# ========== 海浪氛围层 (贯穿, 模拟海边) ==========
def wave_texture(start, dur, intensity=0.06, period=7.0):
    n = int(SR * dur)
    t = np.linspace(0, dur, n, endpoint=False)
    # 海浪: 低通滤波的噪声 + 缓慢振幅包络(浪涌)
    noise = np.random.randn(n)
    # 简单低通: 累积平均
    kernel = np.ones(2200) / 2200
    filtered = np.convolve(noise, kernel, mode='same')
    # 浪涌包络
    surge = 0.5 + 0.5 * np.sin(2 * np.pi * t / period)
    surge = surge ** 2
    env = np.linspace(0, 1, min(n, int(SR * 2)))  # 淡入
    if n > len(env):
        full_env = np.ones(n)
        full_env[:len(env)] = env
        fade = int(SR * 3)
        full_env[-fade:] *= np.linspace(1, 0, fade)
    else:
        full_env = env
    wave = filtered * surge * full_env * intensity
    stereo = np.column_stack([wave * 0.9, wave * 1.1])  # 微立体差
    add_track(master, stereo, start, 0, 1.0)

# 海浪只在海洋相关段落(35-70, 85-120, 133-148)
wave_texture(35, 35, 0.05)
wave_texture(85, 35, 0.05)
wave_texture(133, 15, 0.04)

# ========== 后期处理 ==========
# 软限幅
peak = np.abs(master).max()
if peak > 0.85:
    master = master / peak * 0.85
# 混响
master = simple_reverb(master, decay=0.30)
# 总淡入淡出
fade_in = int(SR * 0.5)
master[:fade_in] *= np.linspace(0, 1, fade_in)[:, None]
fade_out = int(SR * 4)
master[-fade_out:] *= np.linspace(1, 0, fade_out)[:, None] ** 1.5
# 归一化到 -1dB
master = master / np.abs(master).max() * 0.89

# 输出
out = (master * 32767).astype(np.int16)
wavfile.write('/home/z/my-project/dalian_video/audio/bgm.wav', SR, out)
print(f"✅ BGM已生成: 148秒, 44.1kHz立体声")
print(f"峰值: {np.abs(master).max():.3f}")
