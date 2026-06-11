#!/bin/zsh
cd "$(dirname "$0")"
echo "正在测试飞书-Codex连接..."
echo "目录：$(pwd)"
echo ""
python3 feishu_codex.py auth-test
echo ""
echo "如果上面看到 OK，说明连接成功。"
echo "如果失败，把这整个窗口里的报错复制给 Codex。"
echo ""
echo "按回车关闭窗口。"
read
