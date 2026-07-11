import Cocoa
import WebKit

final class AppDelegate: NSObject, NSApplicationDelegate, WKNavigationDelegate {
    private var window: NSWindow!
    private var webView: WKWebView!
    private let appURL = URL(string: "http://127.0.0.1:51216/")!
    private let healthURL = URL(string: "http://127.0.0.1:51216/api/health")!
    private let collectorDir = "/Users/chen.zip/Desktop/CHEN BRAIN/03｜CHEN操盘手系统/01｜CHEN外接大脑/作品链接采集器"

    func applicationDidFinishLaunching(_ notification: Notification) {
        buildMenu()
        startServerIfNeeded()
        buildWindow()
        loadWhenReady()
    }

    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool {
        true
    }

    private func buildWindow() {
        let config = WKWebViewConfiguration()
        webView = WKWebView(frame: .zero, configuration: config)
        webView.navigationDelegate = self

        window = NSWindow(
            contentRect: NSRect(x: 0, y: 0, width: 1280, height: 840),
            styleMask: [.titled, .closable, .miniaturizable, .resizable],
            backing: .buffered,
            defer: false
        )
        window.center()
        window.title = "CHEN 内容采集助手"
        window.contentView = webView
        window.titlebarAppearsTransparent = false
        window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
    }

    private func buildMenu() {
        let mainMenu = NSMenu()

        let appMenuItem = NSMenuItem()
        mainMenu.addItem(appMenuItem)
        let appMenu = NSMenu(title: "CHEN 内容采集助手")
        appMenu.addItem(NSMenuItem(title: "退出 CHEN 内容采集助手", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q"))
        appMenuItem.submenu = appMenu

        let editMenuItem = NSMenuItem()
        mainMenu.addItem(editMenuItem)
        let editMenu = NSMenu(title: "编辑")
        editMenu.addItem(NSMenuItem(title: "剪切", action: #selector(NSText.cut(_:)), keyEquivalent: "x"))
        editMenu.addItem(NSMenuItem(title: "拷贝", action: #selector(NSText.copy(_:)), keyEquivalent: "c"))
        editMenu.addItem(NSMenuItem(title: "粘贴", action: #selector(NSText.paste(_:)), keyEquivalent: "v"))
        editMenu.addItem(NSMenuItem.separator())
        editMenu.addItem(NSMenuItem(title: "全选", action: #selector(NSText.selectAll(_:)), keyEquivalent: "a"))
        editMenuItem.submenu = editMenu

        NSApp.mainMenu = mainMenu
    }

    private func loadWhenReady(attempt: Int = 0) {
        if serverIsHealthy() {
            webView.load(URLRequest(url: appURL))
            return
        }
        if attempt >= 60 {
            showError("本地服务没有启动成功。请检查 /tmp/chen-content-collector-app.log")
            return
        }
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.4) {
            self.loadWhenReady(attempt: attempt + 1)
        }
    }

    private func serverIsHealthy() -> Bool {
        let semaphore = DispatchSemaphore(value: 0)
        var ok = false
        URLSession.shared.dataTask(with: healthURL) { _, response, _ in
            if let http = response as? HTTPURLResponse, http.statusCode == 200 {
                ok = true
            }
            semaphore.signal()
        }.resume()
        _ = semaphore.wait(timeout: .now() + 0.8)
        return ok
    }

    private func startServerIfNeeded() {
        if serverIsHealthy() {
            return
        }
        stopUnhealthyServerOnPort()
        let process = Process()
        process.launchPath = "/bin/zsh"
        process.arguments = [
            "-lc",
            "cd \(shellQuote(collectorDir)) && /usr/bin/nohup /usr/bin/python3 content_link_collector.py desktop-app --host 127.0.0.1 --port 51216 > /tmp/chen-content-collector-app.log 2>&1 &"
        ]
        try? process.run()
    }

    private func stopUnhealthyServerOnPort() {
        let process = Process()
        process.launchPath = "/bin/zsh"
        process.arguments = [
            "-lc",
            "pids=$(/usr/sbin/lsof -tiTCP:51216 -sTCP:LISTEN 2>/dev/null); if [ -n \"$pids\" ]; then /bin/kill $pids 2>/dev/null; /bin/sleep 0.4; fi"
        ]
        try? process.run()
        process.waitUntilExit()
    }

    private func showError(_ message: String) {
        let html = """
        <html><body style='font-family:-apple-system;padding:32px;background:#081120;color:#eef5ff'>
        <h2>CHEN 内容采集助手启动失败</h2>
        <p>\(message)</p>
        </body></html>
        """
        webView.loadHTMLString(html, baseURL: nil)
    }

    private func shellQuote(_ text: String) -> String {
        "'" + text.replacingOccurrences(of: "'", with: "'\\''") + "'"
    }
}

let app = NSApplication.shared
let delegate = AppDelegate()
app.delegate = delegate
app.setActivationPolicy(.regular)
app.run()
