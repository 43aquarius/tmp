#!/bin/bash
# 视频生成队列：对每个分镜图生视频，带持久重试
# 成功的片段存到 clips/scene_XX.mp4，失败记录到 failed.txt
# 用法: nohup bash gen_videos.sh > gen_videos.log 2>&1 &

DIR=/home/z/my-project/dalian_video
FRAMES=$DIR/frames
CLIPS=$DIR/clips
mkdir -p $CLIPS
FAILED=$CLIPS/failed.txt
touch $FAILED

# 每镜的运镜指令（图生视频动画描述）
declare -A MOTION
MOTION[1]="雨丝缓缓落下，霓虹灯光流动闪烁，女孩撑伞缓步走出，镜头缓慢推近"
MOTION[2]="白色羽毛缓缓飘落，柔光微粒飘散，信封微微发光脉动，窗帘轻拂"
MOTION[3]="晨光缓缓移动，羽毛轻轻滚动，浅景深焦点微移，光影流转"
MOTION[4]="海鸥精灵歪头眨眼，翅膀轻轻抖动，女孩走近，阳光光斑闪烁流动"
MOTION[5]="海鸥精灵展翅低飞前行，女孩奔跑跟随，阳光光斑从画面掠过"
MOTION[6]="海鸥群盘旋飞舞俯冲，女孩抛洒食物，海浪缓缓起伏，风筝飘动"
MOTION[7]="车厢轻微摇晃，窗外街景流动后退，阳光光斑在车厢内缓缓移动"
MOTION[8]="云影缓缓流动，鸽子踱步啄食，镜头缓慢横移展现广场建筑"
MOTION[9]="铁板焖子滋滋冒油，热气升腾，芝麻酱缓缓流下，奶奶递盘子微笑"
MOTION[10]="海浪层层拍打礁石，女孩发丝被海风吹起，云缓缓移动，镜头缓慢右移"
MOTION[11]="暖金光晕缓缓流动，海鸥盘旋，小女孩和奶奶衣角轻动，柔焦光斑闪烁"
MOTION[12]="水面波光荡漾，贡多拉缓缓划过，倒影轻轻摇晃，夕阳光线流动"
MOTION[13]="大桥灯光缓缓闪烁流动，海面倒影微微荡漾，镜头缓慢推近"
MOTION[14]="夕阳金光在海面流动，女孩缓缓打开信纸，信纸泛起柔光，发丝轻动"
MOTION[15]="夕阳光斑缓缓移动，羽毛轻轻颤动，光线在信纸上流动，浅景深焦点微移"
MOTION[16]="海鸥精灵轻轻抖动羽毛落在肩头，女孩侧头微笑，逆光轮廓光晕流动"
MOTION[17]="朝阳缓缓升起金光渐强，女孩打电话微笑，海鸥精灵振翅，远处海鸥群飞过"
MOTION[18]="海鸥群展翅飞过海面，金光闪烁，翅膀剪影流动，镜头缓缓上升俯瞰"

# 5秒或10秒
declare -A DUR
for i in $(seq 1 18); do DUR[$i]=5; done
DUR[2]=10; DUR[3]=10; DUR[6]=10; DUR[7]=10; DUR[9]=10; DUR[10]=10; DUR[14]=10; DUR[17]=10; DUR[18]=10

MAX_SCENE=${1:-18}

while true; do
  APIDOWN=false
  for i in $(seq 1 $MAX_SCENE); do
    FRAME=$(printf "$FRAMES/scene_%02d.png" $i)
    CLIP=$(printf "$CLIPS/scene_%02d.mp4" $i)
    if [ ! -f "$FRAME" ]; then continue; fi
    if [ -f "$CLIP" ]; then continue; fi
    if grep -q "^$i$" $FAILED; then continue; fi

    echo "[$(date '+%H:%M:%S')] 尝试场景$i (时长${DUR[$i]}s)..."
    RESULT=$(timeout 400 z-ai video -i "$FRAME" -p "${MOTION[$i]}" -d ${DUR[$i]} --poll --poll-interval 10 --max-polls 30 -o "$CLIPS/scene_${i}_result.json" 2>&1 | tail -3)

    if [ -f "$CLIPS/scene_${i}_result.json" ]; then
      # 从json中提取视频URL并下载
      VIDEO_URL=$(python3 -c "
import json
try:
    with open('$CLIPS/scene_${i}_result.json') as f:
        d = json.load(f)
    # 尝试多种可能的字段路径
    def find_url(obj):
        if isinstance(obj, str) and obj.startswith('http') and ('.mp4' in obj or 'video' in obj):
            return obj
        if isinstance(obj, dict):
            for v in obj.values():
                r = find_url(v)
                if r: return r
        if isinstance(obj, list):
            for v in obj:
                r = find_url(v)
                if r: return r
        return None
    print(find_url(d) or '')
except Exception as e:
    print('')
" 2>/dev/null)
      if [ -n "$VIDEO_URL" ]; then
        echo "场景$i 视频URL获取成功，下载中..."
        curl -sL "$VIDEO_URL" -o "$CLIP" --max-time 120
        if [ -f "$CLIP" ] && [ $(stat -c%s "$CLIP" 2>/dev/null || echo 0) -gt 100000 ]; then
          echo "场景$i ✅ 下载完成 $(stat -c%s $CLIP) bytes"
          continue
        else
          rm -f "$CLIP"
        fi
      fi
    fi
    echo "场景$i 本轮失败: $RESULT" | head -2
    if echo "$RESULT" | grep -q "429"; then
      APIDOWN=true
      echo "[$(date '+%H:%M:%S')] API限流，休息5分钟..."
      break
    fi
  done

  # 检查是否全部完成
  DONE_COUNT=$(ls $CLIPS/scene_*.mp4 2>/dev/null | wc -l)
  echo "[$(date '+%H:%M:%S')] 已完成 $DONE_COUNT/$MAX_SCENE 个视频片段"
  if [ "$DONE_COUNT" -ge "$MAX_SCENE" ]; then
    echo "🎉 全部完成！"
    break
  fi

  # 限流则长休息，否则短休息继续下一轮
  if [ "$APIDOWN" = true ]; then
    sleep 300
  else
    sleep 60
  fi
done
