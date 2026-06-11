#!/bin/zsh
cd "$(dirname "$0")"
echo "导入飞书 Docx 文档到 Obsidian"
echo ""
echo "请粘贴飞书文档的 document_id。"
echo "提示：通常在文档链接 /docx/ 后面那一串。"
read "docid?document_id: "
if [ -z "$docid" ]; then
  echo "没有输入 document_id，已取消。"
  read
  exit 1
fi
read "title?保存成什么标题，直接回车则使用 document_id: "
if [ -z "$title" ]; then
  python3 feishu_codex.py pull-docx-to-vault --document-id "$docid" --out-dir ../../2-日常MAX语料
else
  python3 feishu_codex.py pull-docx-to-vault --document-id "$docid" --title "$title" --out-dir ../../2-日常MAX语料
fi
echo ""
echo "完成后请到 Obsidian 的 2-日常MAX语料/ 查看。"
echo "如果报权限错误：请给飞书应用开启云文档读取权限，并确保应用能访问该文档。"
echo ""
echo "按回车关闭窗口。"
read
