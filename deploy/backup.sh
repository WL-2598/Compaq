#!/bin/sh
# 每日备份：为所有实例创建快照，保留最近 7 份（由容器 cron 调用）
set -eu
export COMPAQ_HOME="${COMPAQ_HOME:-/data/compaq}"
cd /app

echo "[backup] $(date -u +%FT%TZ) 开始"
for dir in "$COMPAQ_HOME/instances"/*/; do
  [ -d "$dir" ] || continue
  name=$(basename "$dir")
  python -m compaq backup "$name" || echo "[backup] $name 失败（继续）"
done

# 滚动保留：每个实例只留最近 7 份
for dir in "$COMPAQ_HOME/instances"/*/backups; do
  [ -d "$dir" ] || continue
  ls -1t "$dir"/*.tar.gz 2>/dev/null | tail -n +8 | while read -r old; do
    rm -f "$old"
    echo "[backup] 清理 $old"
  done
done
echo "[backup] 完成"
