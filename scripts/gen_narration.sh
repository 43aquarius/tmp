#!/bin/bash
# 生成《来自海边的信》旁白分镜配音
DIR=/home/z/my-project/dalian_video
TTS_DIR=$DIR/audio
mkdir -p $TTS_DIR

declare -A VOICE_TEXT
VOICE_TEXT[1]="你有多久，没看过海了？"
VOICE_TEXT[2]="那天夜里，一根白色羽毛，悄悄落在我的窗台，变成了一封信。"
VOICE_TEXT[3]="信封上，只写了两个字——大连。"
VOICE_TEXT[4]="出站口的风，是咸的，也是暖的。"
VOICE_TEXT[5]="有一只白色的小海鸥，在等我。"
VOICE_TEXT[6]="它叫浪浪。老人们说，它是这片海养大的精灵，专门替大海，给想家的人送信。"
VOICE_TEXT[7]="一百岁的老电车，还在叮叮当当地跑。载着旧时光，也载着刚回来的我。"
VOICE_TEXT[9]="巷口的焖子，外脆里糯，还是小时候的那个味道。"
VOICE_TEXT[10]="滨海路的风，会把烦恼，吹得很远，很远。"
VOICE_TEXT[11]="小时候，奶奶牵着我喂海鸥。她说，海鸥会记住，每一双喂过它的手。"
VOICE_TEXT[14]="黄昏时，我又打开了那封信，一行字，慢慢浮现——"
VOICE_TEXT[15]="无论走多远，这片海，都记得你。"
VOICE_TEXT[16]="原来，一直记得我的，是这座城市。"
VOICE_TEXT[17]="妈，这个周末，带你来看海吧。"
VOICE_TEXT[18]="大连，一直都在。"

VOICE=${1:-tongtong}
SPEED=${2:-0.95}

for i in $(echo "${!VOICE_TEXT[@]}" | tr ' ' '\n' | sort -n); do
  OUTFILE=$(printf "$TTS_DIR/narr_%02d.wav" $i)
  if [ -f "$OUTFILE" ]; then echo "[$i] 已存在"; continue; fi
  echo "[$i] TTS: ${VOICE_TEXT[$i]}"
  for retry in 1 2 3 4 5; do
    z-ai tts -i "${VOICE_TEXT[$i]}" -o "$OUTFILE" -v $VOICE -s $SPEED 2>&1 | tail -1
    if [ -f "$OUTFILE" ]; then echo "[$i] ✅"; break; fi
    echo "[$i] 失败，等待${retry}0秒重试..."
    sleep $((retry * 10))
  done
  sleep 12
done
echo "=== 旁白生成完毕 ==="
for f in $TTS_DIR/narr_*.wav; do
  d=$(ffprobe -v quiet -show_entries format=duration -of csv=p=0 "$f" 2>/dev/null)
  echo "$f: ${d}s"
done
