#!/bin/zsh
cd "$(dirname "$0")"
echo "通过邮箱查询飞书用户 ID"
echo ""
echo "请输入你的飞书账号绑定邮箱。"
read "email?邮箱: "
if [ -z "$email" ]; then
  echo "没有输入邮箱，已取消。"
  read
  exit 1
fi

echo ""
echo "正在查询 open_id..."
python3 feishu_codex.py api POST /open-apis/contact/v3/users/batch_get_id \
  --query user_id_type=open_id \
  --body-json "{\"emails\":[\"$email\"]}"

echo ""
echo "正在查询 user_id..."
python3 feishu_codex.py api POST /open-apis/contact/v3/users/batch_get_id \
  --query user_id_type=user_id \
  --body-json "{\"emails\":[\"$email\"]}"

echo ""
echo "如果返回 code=0，并且 data.user_list 里有 open_id 或 user_id，就复制那个值。"
echo "如果返回权限错误，请去飞书开放平台给应用开通通讯录/通过邮箱获取用户ID相关权限，并发布应用。"
echo ""
echo "按回车关闭窗口。"
read
