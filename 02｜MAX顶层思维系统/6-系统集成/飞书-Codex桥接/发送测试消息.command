#!/bin/zsh
cd "$(dirname "$0")"
echo "正在向默认接收人发送飞书测试消息..."
echo ""
python3 feishu_codex.py send-text --text "飞书-Codex桥已打通：MAX 的外接系统上线。"
echo ""
echo "如果上面返回 code=0 或 payload 里没有错误，说明发送成功。"
echo "如果报权限错误：请去飞书开放平台给应用开启消息发送权限，并发布/启用应用。"
echo "如果报 receive_id 错误：请重新双击 配置默认接收人.command。"
echo ""
echo "按回车关闭窗口。"
read
