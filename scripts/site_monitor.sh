#!/bin/bash
# 绘影站点恢复监控: 每5分钟检查主入口JS是否恢复200
URL="https://aistatic.migudm.cn/ai-delivery-platform/assets/index-BPBHra9j.js"
LOG=/home/z/my-project/dalian_video/site_monitor.log
echo "$(date '+%m-%d %H:%M:%S') 监控启动" >> "$LOG"
while true; do
  code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 20 "$URL")
  if [ "$code" = "200" ]; then
    echo "$(date '+%m-%d %H:%M:%S') ✅ 站点已恢复(entry JS=200)" >> "$LOG"
    break
  fi
  echo "$(date '+%m-%d %H:%M:%S') entry JS=$code" >> "$LOG"
  sleep 300
done
