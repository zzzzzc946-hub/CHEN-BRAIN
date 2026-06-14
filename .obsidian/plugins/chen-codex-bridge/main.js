const { Plugin, Modal, Notice, MarkdownView } = require("obsidian");
const { execFile } = require("child_process");
const path = require("path");

class CodexPromptModal extends Modal {
  constructor(app, plugin) {
    super(app);
    this.plugin = plugin;
  }

  onOpen() {
    const { contentEl } = this;
    contentEl.empty();
    contentEl.addClass("chen-codex-modal");

    contentEl.createEl("h2", { text: "Codex｜处理当前笔记" });

    const activeFile = this.app.workspace.getActiveFile();
    if (!activeFile) {
      contentEl.createEl("p", { text: "当前没有打开的 Markdown 笔记。" });
      return;
    }

    contentEl.createEl("p", {
      text: `当前笔记：${activeFile.path}`,
      cls: "chen-codex-current-file"
    });

    const textarea = contentEl.createEl("textarea", {
      cls: "chen-codex-textarea",
      attr: {
        placeholder: "输入你要 Codex 做的事，比如：总结当前笔记、提炼选题、整理成表格、按 MAX 规则判断这段内容。"
      }
    });

    const buttonRow = contentEl.createDiv({ cls: "chen-codex-button-row" });
    const runButton = buttonRow.createEl("button", {
      text: "发送给 Codex",
      cls: "mod-cta"
    });
    const cancelButton = buttonRow.createEl("button", { text: "取消" });

    textarea.focus();

    cancelButton.addEventListener("click", () => this.close());
    runButton.addEventListener("click", async () => {
      const task = textarea.value.trim();
      if (!task) {
        new Notice("先输入给 Codex 的任务。");
        return;
      }
      runButton.disabled = true;
      cancelButton.disabled = true;
      runButton.setText("Codex 处理中...");
      try {
        await this.plugin.runCodexOnActiveFile(activeFile, task);
        new Notice("Codex 已完成，并写回当前笔记。");
        this.close();
      } catch (error) {
        console.error(error);
        new Notice(`Codex 执行失败：${String(error.message || error).slice(0, 500)}`);
        runButton.disabled = false;
        cancelButton.disabled = false;
        runButton.setText("发送给 Codex");
      }
    });
  }

  onClose() {
    this.contentEl.empty();
  }
}

module.exports = class ChenCodexBridgePlugin extends Plugin {
  async onload() {
    this.addRibbonIcon("bot", "Codex｜处理当前笔记", () => {
      new CodexPromptModal(this.app, this).open();
    });

    this.addCommand({
      id: "chen-codex-process-current-note",
      name: "Codex｜处理当前笔记",
      callback: () => {
        new CodexPromptModal(this.app, this).open();
      }
    });
  }

  getVaultPath() {
    const adapter = this.app.vault.adapter;
    if (!adapter || typeof adapter.getBasePath !== "function") {
      throw new Error("只能在 Obsidian 桌面端使用 Codex Bridge。");
    }
    return adapter.getBasePath();
  }

  runCodexOnActiveFile(activeFile, task) {
    return new Promise((resolve, reject) => {
      const vaultPath = this.getVaultPath();
      const scriptPath = path.join(
        vaultPath,
        "00｜MAX IP项目总控台",
        "05｜Obsidian-Codex桥接",
        "Scripts",
        "obsidian_codex_bridge.py"
      );

      execFile(
        "/usr/bin/python3",
        [scriptPath, "--active-file", activeFile.path, "--task", task],
        {
          cwd: vaultPath,
          timeout: 900000,
          maxBuffer: 1024 * 1024 * 20
        },
        async (error, stdout, stderr) => {
          if (error) {
            reject(new Error((stderr || stdout || error.message || "").slice(-4000)));
            return;
          }
          const view = this.app.workspace.getActiveViewOfType(MarkdownView);
          if (view && view.file && view.file.path === activeFile.path) {
            await view.leaf.rebuildView();
          }
          resolve(stdout);
        }
      );
    });
  }
};
