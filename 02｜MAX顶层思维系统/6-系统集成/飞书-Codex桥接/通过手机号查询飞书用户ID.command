#!/bin/zsh
cd "$(dirname "$0")"
echo "通过手机号查询飞书用户 ID"
echo ""
echo "请输入你的飞书绑定手机号。"
echo "中国大陆手机号可以直接输入 11 位数字；脚本会自动补 +86。"
read "mobile?手机号: "
if [ -z "$mobile" ]; then
  echo "没有输入手机号，已取消。"
  read
  exit 1
fi

# 去掉空格、横杠
mobile=$(echo "$mobile" | tr -d ' -')
# 如果是大陆 11 位手机号，自动加 +86
if [[ "$mobile" =~ '^[0-9]{11}$' ]]; then
  mobile="+86$mobile"
fi

echo ""
echo "正在查询 open_id..."
python3 feishu_codex.py api POST /open-apis/contact/v3/users/batch_get_id \
  --query user_id_type=open_id \
  --body-json "{\"mobiles\":[\"$mobile\"]}"

echo ""
echo "正在查询 user_id..."
python3 feishu_codex.py api POST /open-apis/contact/v3/users/batch_get_id \
  --query user_id_type=user_id \
  --body-json "{\"mobiles\":[\"$mobile\"]}"

echo ""
echo "如果返回 code=0，并且 data.user_list 里有 open_id 或 user_id，就复制那个值。"
echo "如果返回权限错误，请去飞书开放平台给应用开通通讯录/通过手机号或邮箱获取用户ID相关权限，并发布应用。"
echo ""
echo "拿到 open_id 后，双击 配置默认接收人.command："
echo "接收人类型填 open_id"
echo "接收人 ID 填 ou_xxxxx 那串值"
echo ""
echo "按回车关闭窗口。"
read
