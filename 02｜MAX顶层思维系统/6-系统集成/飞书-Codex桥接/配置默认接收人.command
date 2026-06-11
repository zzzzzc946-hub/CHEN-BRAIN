#!/bin/zsh
cd "$(dirname "$0")"
echo "配置默认飞书接收人"
echo ""
echo "常用类型："
echo "1) email   - 用飞书绑定邮箱发送给个人，最适合新手先测试"
echo "2) open_id - 飞书用户 open_id"
echo "3) user_id - 飞书用户 user_id"
echo "4) chat_id - 飞书群 chat_id"
echo ""
read "rtype?请输入接收人类型，直接回车默认 email: "
rtype=${rtype:-email}
read "rid?请输入接收人 ID / 邮箱 / 群 chat_id: "
if [ -z "$rid" ]; then
  echo "没有输入接收人，已取消。"
  echo "按回车关闭窗口。"
  read
  exit 1
fi
python3 - "$rtype" "$rid" <<'PY'
from pathlib import Path
import sys
rtype, rid = sys.argv[1], sys.argv[2]
p = Path('.env')
if not p.exists():
    raise SystemExit('没有找到 .env，请先完成飞书连接配置。')
lines = p.read_text(encoding='utf-8').splitlines()
updates = {
    'FEISHU_RECEIVE_ID_TYPE': rtype,
    'FEISHU_RECEIVE_ID': rid,
}
seen = set()
out = []
for line in lines:
    if '=' in line and not line.lstrip().startswith('#'):
        key = line.split('=', 1)[0].strip()
        if key in updates:
            out.append(f'{key}={updates[key]}')
            seen.add(key)
        else:
            out.append(line)
    else:
        out.append(line)
for key, value in updates.items():
    if key not in seen:
        out.append(f'{key}={value}')
p.write_text('\n'.join(out) + '\n', encoding='utf-8')
print('已写入默认接收人配置。')
print(f'FEISHU_RECEIVE_ID_TYPE={rtype}')
print('FEISHU_RECEIVE_ID=已保存')
PY
echo ""
echo "下一步：双击 发送测试消息.command"
echo "按回车关闭窗口。"
read
