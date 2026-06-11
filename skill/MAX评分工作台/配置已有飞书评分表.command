#!/bin/zsh
cd "$(dirname "$0")"
echo "配置已有飞书评分表"
echo
read "APP_ID?请输入飞书 App ID（cli_...）："
read -s "APP_SECRET?请输入飞书 App Secret："
echo
read "APP_TOKEN?请输入多维表格 app_token（base/ 后那串，常见 bas...）："
read "TABLE_ID?请输入数据表 table_id（tbl...）："
cat > config.json <<EOF
{
  "feishu": {
    "app_id": "$APP_ID",
    "app_secret": "$APP_SECRET",
    "app_token": "$APP_TOKEN",
    "table_id": "$TABLE_ID"
  }
}
EOF
echo
echo "已写入 config.json。现在初始化字段..."
python3 max_score.py init-fields
echo
echo "完成后建议运行一次：python3 max_score.py sync-test"
read -n 1 -s "?按任意键关闭窗口..."
