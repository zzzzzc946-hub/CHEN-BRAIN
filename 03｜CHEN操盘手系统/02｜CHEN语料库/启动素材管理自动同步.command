#!/bin/zsh
set -e

DIR="${0:A:h}"
PID_FILE="$DIR/.素材管理自动同步.pid"
LOG_FILE="$DIR/.素材管理自动同步.log"
WATCHER="$DIR/00｜监听素材管理自动同步.py"

if [[ -f "$PID_FILE" ]]; then
  PID="$(cat "$PID_FILE")"
  if [[ -n "$PID" ]] && kill -0 "$PID" 2>/dev/null; then
    echo "素材管理自动同步已在运行：$PID"
    exit 0
  fi
fi

nohup /usr/bin/python3 "$WATCHER" >> "$LOG_FILE" 2>&1 &
echo $! > "$PID_FILE"
echo "素材管理自动同步已启动：$!"
