const { ItemView, MarkdownView, Notice, Plugin } = require("obsidian");
const { spawn } = require("child_process");
const fs = require("fs");
const path = require("path");

const VIEW_TYPE_CHEN_AI_CHAT = "chen-ai-chat-view";
const CODEX_BIN = "/Users/chen.zip/.local/bin/codex";

function compact(text, limit = 120000) {
  if (!text || text.length <= limit) return text || "";
  const half = Math.floor(limit / 2);
  return `${text.slice(0, half)}

<!-- 中间内容过长，已由 CHEN AI 面板压缩 -->

${text.slice(-half)}`;
}

function escapeHtml(text) {
  return String(text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

class ChenAiChatView extends ItemView {
  constructor(leaf, plugin) {
    super(leaf);
    this.plugin = plugin;
    this.messagesEl = null;
    this.inputEl = null;
    this.includeNoteEl = null;
    this.sendButton = null;
    this.clearButton = null;
    this.isRunning = false;
  }

  getViewType() {
    return VIEW_TYPE_CHEN_AI_CHAT;
  }

  getDisplayText() {
    return "CHEN AI";
  }

  getIcon() {
    return "bot";
  }

  async onOpen() {
    this.render();
  }

  render() {
    const container = this.containerEl.children[1];
    container.empty();
    container.addClass("chen-ai-chat-view");

    const header = container.createDiv({ cls: "chen-ai-chat-header" });
    header.createEl("h2", { text: "CHEN AI" });
    header.createEl("p", {
      text: "直接在 Obsidian 里和 Codex 对话。默认遵守 CHEN BRAIN 仓库规则。",
      cls: "chen-ai-chat-subtitle"
    });

    this.messagesEl = container.createDiv({ cls: "chen-ai-chat-messages" });
    this.renderMessages();

    const controls = container.createDiv({ cls: "chen-ai-chat-controls" });
    const noteLabel = controls.createEl("label", { cls: "chen-ai-chat-check" });
    this.includeNoteEl = noteLabel.createEl("input", { type: "checkbox" });
    this.includeNoteEl.checked = true;
    noteLabel.createSpan({ text: "带上当前笔记" });

    this.clearButton = controls.createEl("button", { text: "清空对话" });
    this.clearButton.addEventListener("click", async () => {
      await this.plugin.clearMessages();
      this.renderMessages();
    });

    const inputRow = container.createDiv({ cls: "chen-ai-chat-input-row" });
    this.inputEl = inputRow.createEl("textarea", {
      cls: "chen-ai-chat-input",
      attr: {
        placeholder: "直接输入：总结当前笔记 / 按 MAX 判断这段内容 / 生成选题 / 修改某个文件..."
      }
    });

    this.sendButton = inputRow.createEl("button", {
      text: "发送",
      cls: "mod-cta chen-ai-chat-send"
    });
    this.sendButton.addEventListener("click", () => this.sendMessage());
    this.inputEl.addEventListener("keydown", (event) => {
      if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
        event.preventDefault();
        this.sendMessage();
      }
    });

    this.inputEl.focus();
  }

  renderMessages() {
    if (!this.messagesEl) return;
    this.messagesEl.empty();

    const messages = this.plugin.messages;
    if (!messages.length) {
      const empty = this.messagesEl.createDiv({ cls: "chen-ai-chat-empty" });
      empty.setText("还没有对话。你可以直接问 Codex，也可以让它基于当前笔记处理。");
      return;
    }

    for (const message of messages) {
      const item = this.messagesEl.createDiv({
        cls: `chen-ai-chat-message chen-ai-chat-message-${message.role}`
      });
      item.createDiv({
        text: message.role === "user" ? "CHEN" : "Codex",
        cls: "chen-ai-chat-role"
      });
      const body = item.createDiv({ cls: "chen-ai-chat-body" });
      body.innerHTML = `<pre>${escapeHtml(message.content)}</pre>`;
    }
    this.messagesEl.scrollTop = this.messagesEl.scrollHeight;
  }

  async sendMessage() {
    if (this.isRunning) return;
    const text = this.inputEl.value.trim();
    if (!text) {
      new Notice("先输入你要和 Codex 说的话。");
      return;
    }

    this.inputEl.value = "";
    this.setRunning(true);

    await this.plugin.addMessage({ role: "user", content: text });
    this.renderMessages();

    try {
      const reply = await this.plugin.runCodexChat({
        userMessage: text,
        includeCurrentNote: this.includeNoteEl.checked
      });
      await this.plugin.addMessage({ role: "assistant", content: reply || "Codex 没有返回内容。" });
    } catch (error) {
      console.error(error);
      await this.plugin.addMessage({
        role: "assistant",
        content: `执行失败：${String(error.message || error).slice(0, 4000)}`
      });
    } finally {
      this.setRunning(false);
      this.renderMessages();
      this.inputEl.focus();
    }
  }

  setRunning(isRunning) {
    this.isRunning = isRunning;
    this.inputEl.disabled = isRunning;
    this.sendButton.disabled = isRunning;
    this.clearButton.disabled = isRunning;
    this.sendButton.setText(isRunning ? "Codex 处理中..." : "发送");
  }
}

module.exports = class ChenCodexBridgePlugin extends Plugin {
  async onload() {
    const data = await this.loadData();
    this.messages = Array.isArray(data?.messages) ? data.messages : [];
    this.lastMarkdownFile = null;

    this.registerView(
      VIEW_TYPE_CHEN_AI_CHAT,
      (leaf) => new ChenAiChatView(leaf, this)
    );

    this.registerEvent(
      this.app.workspace.on("file-open", (file) => {
        if (file && file.extension === "md") this.lastMarkdownFile = file;
      })
    );

    this.addRibbonIcon("bot", "CHEN AI｜和 Codex 对话", () => {
      this.activateChatView();
    });

    this.addCommand({
      id: "open-chen-ai-chat",
      name: "打开 CHEN AI 对话",
      callback: () => this.activateChatView()
    });

    this.addCommand({
      id: "chen-codex-process-current-note",
      name: "Codex｜处理当前笔记",
      callback: () => this.activateChatView()
    });
  }

  onunload() {
    this.app.workspace.detachLeavesOfType(VIEW_TYPE_CHEN_AI_CHAT);
  }

  async activateChatView() {
    const existing = this.app.workspace.getLeavesOfType(VIEW_TYPE_CHEN_AI_CHAT)[0];
    if (existing) {
      this.app.workspace.revealLeaf(existing);
      return;
    }
    const leaf = this.app.workspace.getRightLeaf(false);
    await leaf.setViewState({ type: VIEW_TYPE_CHEN_AI_CHAT, active: true });
    this.app.workspace.revealLeaf(leaf);
  }

  getVaultPath() {
    const adapter = this.app.vault.adapter;
    if (!adapter || typeof adapter.getBasePath !== "function") {
      throw new Error("只能在 Obsidian 桌面端使用 CHEN AI。");
    }
    return adapter.getBasePath();
  }

  getContextFile() {
    const activeView = this.app.workspace.getActiveViewOfType(MarkdownView);
    if (activeView?.file) return activeView.file;
    const activeFile = this.app.workspace.getActiveFile();
    if (activeFile?.extension === "md") return activeFile;
    return this.lastMarkdownFile;
  }

  async addMessage(message) {
    this.messages.push({
      role: message.role,
      content: message.content,
      createdAt: new Date().toISOString()
    });
    if (this.messages.length > 30) {
      this.messages = this.messages.slice(-30);
    }
    await this.saveData({ messages: this.messages });
  }

  async clearMessages() {
    this.messages = [];
    await this.saveData({ messages: this.messages });
  }

  async readCurrentNote(includeCurrentNote) {
    if (!includeCurrentNote) return { file: null, content: "" };
    const file = this.getContextFile();
    if (!file) return { file: null, content: "" };
    const content = await this.app.vault.read(file);
    return { file, content };
  }

  buildPrompt(userMessage, currentNote) {
    const history = this.messages
      .slice(-12)
      .map((message) => `${message.role === "user" ? "CHEN" : "Codex"}：\n${message.content}`)
      .join("\n\n---\n\n");

    const noteBlock = currentNote.file
      ? `当前 Obsidian 笔记：${currentNote.file.path}

当前笔记全文：
\`\`\`markdown
${compact(currentNote.content)}
\`\`\``
      : "当前没有附带 Obsidian 笔记。";

    return `你是运行在 CHEN BRAIN Obsidian 仓库内的 Codex。

硬规则：
- 本仓库是 Obsidian Markdown 知识库，不是普通代码项目。
- 不主动扩系统。
- 不修改 02｜MAX顶层思维系统 中的 MAX 原始源文档，除非 CHEN 明确要求。
- 不主动 commit / push。
- 如果只是对话，直接回答。
- 如果 CHEN 明确要求改文件，可以在仓库内局部修改，并在回答中说明变更。
- 回答使用中文，简洁、直接、可执行。

${noteBlock}

最近对话：
${history || "暂无。"}

CHEN 最新输入：
${userMessage}`;
  }

  runCodexChat({ userMessage, includeCurrentNote }) {
    return new Promise(async (resolve, reject) => {
      try {
        const vaultPath = this.getVaultPath();
        const currentNote = await this.readCurrentNote(includeCurrentNote);
        const prompt = this.buildPrompt(userMessage, currentNote);
        const resultsDir = path.join(
          vaultPath,
          "00｜MAX IP项目总控台",
          "05｜Obsidian-Codex桥接",
          "Results"
        );
        fs.mkdirSync(resultsDir, { recursive: true });
        const outputFile = path.join(resultsDir, `${Date.now()}｜CHEN-AI对话.md`);

        const child = spawn(
          CODEX_BIN,
          [
            "-a",
            "never",
            "exec",
            "-C",
            vaultPath,
            "--sandbox",
            "workspace-write",
            "--output-last-message",
            outputFile,
            "-"
          ],
          {
            cwd: vaultPath,
            stdio: ["pipe", "pipe", "pipe"]
          }
        );

        let stdout = "";
        let stderr = "";
        const timer = setTimeout(() => {
          child.kill("SIGTERM");
          reject(new Error("Codex 执行超时。"));
        }, 900000);

        child.stdout.on("data", (chunk) => {
          stdout += chunk.toString();
          if (stdout.length > 1024 * 1024 * 20) stdout = stdout.slice(-1024 * 1024 * 20);
        });
        child.stderr.on("data", (chunk) => {
          stderr += chunk.toString();
          if (stderr.length > 1024 * 1024 * 20) stderr = stderr.slice(-1024 * 1024 * 20);
        });
        child.on("error", (error) => {
          clearTimeout(timer);
          reject(error);
        });
        child.on("close", (code) => {
          clearTimeout(timer);
          if (code !== 0) {
            reject(new Error((stderr || stdout || `Codex 退出码：${code}`).slice(-4000)));
            return;
          }
          try {
            if (fs.existsSync(outputFile)) {
              resolve(fs.readFileSync(outputFile, "utf8").trim());
              return;
            }
            resolve((stdout || "").trim());
          } catch (error) {
            reject(error);
          }
        });
        child.stdin.write(prompt);
        child.stdin.end();
      } catch (error) {
        reject(error);
      }
    });
  }
};
