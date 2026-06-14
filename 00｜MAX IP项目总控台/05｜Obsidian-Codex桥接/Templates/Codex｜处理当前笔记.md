<%*
const active = app.workspace.getActiveFile();
if (!active) {
  new Notice("没有打开的当前笔记");
  return;
}

const task = await tp.system.prompt("给 Codex 的任务", "请基于当前笔记处理：");
if (!task || !task.trim()) {
  new Notice("已取消");
  return;
}

const vaultPath = app.vault.adapter.getBasePath();
const scriptPath = `${vaultPath}/00｜MAX IP项目总控台/05｜Obsidian-Codex桥接/Scripts/obsidian_codex_bridge.py`;
const { execFileSync } = require("child_process");

new Notice("Codex 正在处理当前笔记...");

try {
  const output = execFileSync(
    "/usr/bin/python3",
    [scriptPath, "--active-file", active.path, "--task", task],
    {
      cwd: vaultPath,
      timeout: 900000,
      maxBuffer: 1024 * 1024 * 20
    }
  ).toString();
  new Notice(output.trim() || "Codex 已完成");
  await app.workspace.getActiveViewOfType(MarkdownView)?.leaf.rebuildView();
} catch (error) {
  const message = String(error.stderr || error.message || error).slice(-1200);
  new Notice("Codex 执行失败，详见控制台");
  console.error(message);
}
%>
