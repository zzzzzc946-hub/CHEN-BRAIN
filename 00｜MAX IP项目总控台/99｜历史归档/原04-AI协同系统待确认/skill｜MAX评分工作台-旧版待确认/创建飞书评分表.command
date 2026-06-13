#!/bin/zsh
cd "$(dirname "$0")"
echo "创建飞书 MAX 内容评分多维表格"
echo
echo "前提：飞书自建应用已开通 bitable:app 或 base:app:create 权限，并已发布/启用。"
echo
read "APP_ID?请输入飞书 App ID（cli_...）："
read -s "APP_SECRET?请输入飞书 App Secret："
echo
python3 max_score.py create-bitable --app-id "$APP_ID" --app-secret "$APP_SECRET"
echo
echo "如果提示权限不足，请按输出链接开通权限，发布应用后重新运行本脚本。"
read -n 1 -s "?按任意键关闭窗口..."
