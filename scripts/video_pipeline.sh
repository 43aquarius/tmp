#!/bin/bash
# 单次流水线周期: 收割已完成→提交下一个→返回状态
cd /home/z/my-project/scripts
COLLECT=$(timeout 120 node gen_video_queue.mjs collect 2>&1 | grep -E "已下载|下载[0-9]")
echo "收割: $COLLECT"
DONE=$(ls /home/z/my-project/dalian_video/clips/scene_*.mp4 2>/dev/null | wc -l)
echo "已完成AI视频: $DONE/18"
if [ "$DONE" -lt 18 ]; then
  NEXT=$(python3 -c "
import os
done_files = {int(f.split('_')[1].split('.')[0]) for f in os.listdir('/home/z/my-project/dalian_video/clips') if f.startswith('scene_') and f.endswith('.mp4')}
import json
try:
    tasks = json.load(open('/home/z/my-project/dalian_video/clips/video_tasks.json'))
except: tasks = {}
active = {int(k) for k,v in tasks.items() if v.get('status') not in ('DOWNLOADED','FAILED')}
for i in range(1,19):
    if i not in done_files and i not in active:
        print(i); break
else:
    print(0)
")
  if [ "$NEXT" != "0" ] && [ -n "$NEXT" ]; then
    echo "提交场景 $NEXT..."
    timeout 90 node gen_video_queue.mjs submit $NEXT 2>&1 | grep "场景" | head -1
  else
    echo "所有任务已提交或进行中, 等待处理..."
  fi
fi
