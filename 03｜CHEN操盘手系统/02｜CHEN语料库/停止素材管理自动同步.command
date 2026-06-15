#!/bin/zsh
set -e

DIR="${0:A:h}"
PID_FILE="$DIR/.素材管理自动同步.pid"

if [[ ! -f "$PID_FILE" ]]; then
  echo "素材管理自动同步未运行。"
  exit 0
fi

PID="$(cat "$PID_FILE")"
if [[ -n "$PID" ]] && kill -0 "$PID" 2>/dev/null; then
  kill "$PID"
  echo "素材管理自动同步已停止：$PID"
else
  echo "素材管理自动同步进程不存在，清理 PID 文件。"
fi

rm -f "$PID_FILE"
