# MAX BRAIN 版本管理说明

当前 Codex 桌面环境不允许在本目录创建标准 `.git` 文件或目录，因此本库使用分离式 Git 目录：

- Git 数据目录：`.gitrepo/`
- 工作目录：MAX BRAIN 根目录
- 快捷命令：`6-系统集成/maxgit`

---

## 常用操作

查看变化：

```bash
6-系统集成/maxgit status --short
```

查看提交历史：

```bash
6-系统集成/maxgit log --oneline --decorate -5
```

创建提交：

```bash
6-系统集成/maxgit add .
6-系统集成/maxgit commit -m "说明这次改了什么"
```

---

## 注意

- `.gitrepo/` 已加入 `.gitignore`，不会被提交进自己。
- `.env`、token 缓存、AI 会话、本地窗口状态不会进入版本管理。
- 因为没有标准 `.git` 目录，直接运行普通 `git status` 不会识别本库；请使用 `6-系统集成/maxgit`。
