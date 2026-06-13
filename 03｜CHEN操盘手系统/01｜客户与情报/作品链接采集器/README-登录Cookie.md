# 登录 Cookie 增强说明

部分抖音链接公开页面不返回标题、图片或视频直链，`yt-dlp` 会提示需要 fresh cookies。解决方法有两种：

## 方式一：cookies.txt

1. 在浏览器安装能导出 Netscape cookies.txt 的扩展。
2. 登录抖音网页版。
3. 导出当前站点 cookies。
4. 保存为本目录下的 `cookies.txt`。
5. 重新运行采集或转写命令。

本目录的 `.gitignore` 已经忽略 `cookies.txt`，不要提交或发送给别人。

## 方式二：从浏览器读取

在 `config.json` 里设置：

```json
"yt_dlp": {
  "enabled": true,
  "cookies_file": "/Users/chen.zip/Desktop/CHEN BRAIN/03｜CHEN操盘手系统/01｜客户与情报/作品链接采集器/cookies.txt",
  "cookies_from_browser": "chrome"
}
```

可尝试值：`chrome`、`edge`、`safari`。macOS 上浏览器 Cookie 读取可能需要钥匙串/浏览器权限；失败时用方式一更稳。
