#!/bin/bash
# 批量图生视频：顺序调用gen_video.mjs，带重试
# 用法: bash gen_videos_queue.sh [开始场景] [结束场景]

DIR=/home/z/my-project/dalian_video
SCRIPTS=/home/z/my-project/scripts
START=${1:-1}
END=${2:-18}

declare -A MOTION
MOTION[1]="雨丝缓缓落下，霓虹灯光流动闪烁，女孩撑伞缓步走出，镜头缓慢推近"
MOTION[2]="白色羽毛缓缓飘落，柔光微粒飘散，信封微微发光脉动，窗帘轻轻飘动"
MOTION[3]="晨光缓缓移动变幻，羽毛轻轻颤动，光影在信封上流动，浅景深焦点微移"
MOTION[4]="海鸥精灵歪头眨眼，翅膀轻轻抖动，女孩缓步走近微笑，阳光光斑闪烁"
MOTION[5]="海鸥精灵展翅低飞向前，女孩拖着行李箱奔跑跟随，阳光光斑从画面掠过"
MOTION[6]="海鸥群盘旋飞舞俯冲，女孩抛洒食物，海浪缓缓起伏，风筝轻轻飘动"
MOTION[7]="车厢轻微摇晃，窗外街景缓缓流动后退，阳光光斑在车厢内缓缓移动"
MOTION[8]="云影缓缓流动，鸽子踱步啄食，镜头缓慢横移展现广场建筑"
MOTION[9]="铁板焖子滋滋冒泡冒热气，热气缓缓升腾，芝麻酱缓缓流下，奶奶微笑递盘子"
MOTION[10]="海浪层层拍打礁石，女孩发丝被海风吹起，白云缓缓移动，镜头缓慢右移"
MOTION[11]="暖金光晕缓缓流动，海鸥缓缓盘旋，人物衣角轻轻飘动，柔焦光斑闪烁"
MOTION[12]="水面波光荡漾，游船缓缓划过，建筑倒影轻轻摇晃，夕阳光线流动"
MOTION[13]="大桥灯光缓缓闪烁流动，海面倒影微微荡漾，镜头缓慢推近"
MOTION[14]="夕阳金光在海面缓缓流动，女孩缓缓打开信纸，信纸泛起柔光，发丝轻动"
MOTION[15]="夕阳光斑缓缓移动，羽毛轻轻颤动，光线在信纸上缓缓流动"
MOTION[16]="海鸥精灵轻轻抖动羽毛，女孩侧头微笑，逆光轮廓光晕缓缓流动"
MOTION[17]="朝阳缓缓升起金光渐强，女孩打电话微笑，海鸥精灵振翅，远处海鸥群飞过"
MOTION[18]="海鸥群展翅飞过海面，金光闪烁荡漾，镜头缓缓上升俯瞰大海"

declare -A DUR
for i in $(seq 1 18); do DUR[$i]=5; done
DUR[2]=10; DUR[3]=10; DUR[6]=10; DUR[7]=10; DUR[9]=10; DUR[10]=10; DUR[14]=10; DUR[17]=10; DUR[18]=10

SUCCESS=0
FAIL_LIST=""

for i in $(seq $START $END); do
  FRAME=$(printf "$DIR/frames/scene_%02d.png" $i)
  CLIP=$(printf "$DIR/clips/scene_%02d.mp4" $i)
  if [ ! -f "$FRAME" ]; then echo "[$i] ⚠️ 无分镜图，跳过"; continue; fi
  if [ -f "$CLIP" ]; then echo "[$i] ✅ 已存在，跳过"; SUCCESS=$((SUCCESS+1)); continue; fi

  echo "===== [$(date '+%H:%M:%S')] 场景$i (${DUR[$i]}s): ${MOTION[$i]:0:30}..."
  for retry in 1 2 3 4; do
    timeout 560 node $SCRIPTS/gen_video.mjs "$FRAME" "${MOTION[$i]}" ${DUR[$i]} "$CLIP" 768x1344 2>&1 | tail -2
    if [ -f "$CLIP" ]; then
      echo "[$i] ✅ 完成 ($(stat -c%s $CLIP | numfmt --to=iec))"
      SUCCESS=$((SUCCESS+1))
      break
    fi
    WAIT=$((retry * 60))
    echo "[$i] ❌ 第${retry}次失败，等${WAIT}秒..."
    sleep $WAIT
  done
  if [ ! -f "$CLIP" ]; then FAIL_LIST="$FAIL_LIST $i"; fi
  sleep 20
done

echo ""
echo "========== 汇总: 成功$SUCCESS / 总$((END-START+1)) =========="
if [ -n "$FAIL_LIST" ]; then echo "失败场景:$FAIL_LIST"; fi
ls -la $DIR/clips/scene_*.mp4 2>/dev/null | wc -l
