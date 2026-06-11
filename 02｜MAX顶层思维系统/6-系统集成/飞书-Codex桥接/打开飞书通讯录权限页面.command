#!/bin/zsh
cd "$(dirname "$0")"
echo "正在打开飞书应用权限页面..."
echo "需要开通权限：contact:user.id:readonly"
echo "权限用途：通过手机号/邮箱查询用户 open_id 或 user_id，用于给你发送飞书消息。"
open "https://open.feishu.cn/app/cli_aaa3c5a0c1389bcf/auth?q=contact:user.id:readonly&op_from=openapi&token_type=tenant"
echo ""
echo "打开后请申请/开通 contact:user.id:readonly 权限。"
echo "如果页面要求发布新版本，请创建版本并发布/启用应用。"
echo "完成后回来双击：通过手机号查询飞书用户ID.command"
echo ""
echo "按回车关闭窗口。"
read
