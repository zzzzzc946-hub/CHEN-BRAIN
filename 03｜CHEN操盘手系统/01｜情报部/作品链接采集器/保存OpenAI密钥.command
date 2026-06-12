#!/bin/zsh
cd "$(dirname "$0")"
echo "请输入 OpenAI API key。输入时不会显示在屏幕上："
read -s OPENAI_API_KEY_VALUE
echo
if [[ -z "$OPENAI_API_KEY_VALUE" ]]; then
  echo "未输入，已取消。"
  read -k 1 "?按任意键关闭窗口。"
  exit 1
fi
export OPENAI_API_KEY_VALUE
python3 -c 'from pathlib import Path
import os
path = Path(".env")
key = os.environ["OPENAI_API_KEY_VALUE"].strip()
lines = []
if path.exists():
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if not line.startswith("OPENAI_API_KEY=")]
lines.append("OPENAI_API_KEY=" + key)
path.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("已保存 OPENAI_API_KEY 到 .env")'
unset OPENAI_API_KEY_VALUE
echo
read -k 1 "?按任意键关闭窗口。"
