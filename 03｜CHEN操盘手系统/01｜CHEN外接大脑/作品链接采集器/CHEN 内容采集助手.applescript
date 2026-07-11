set collectorDir to "/Users/chen.zip/Desktop/CHEN BRAIN/03｜CHEN操盘手系统/01｜CHEN外接大脑/作品链接采集器"
set appUrl to "http://127.0.0.1:51216/"
set healthUrl to appUrl & "api/health"

set shellCmd to "if /usr/bin/curl -fsS " & quoted form of healthUrl & " >/dev/null 2>&1; then " & ¬
  "/usr/bin/open " & quoted form of appUrl & "; " & ¬
  "else cd " & quoted form of collectorDir & " && " & ¬
  "(/usr/bin/nohup /usr/bin/python3 content_link_collector.py desktop-app --host 127.0.0.1 --port 51216 > /tmp/chen-content-collector-app.log 2>&1 &); " & ¬
  "/bin/sleep 1; /usr/bin/open " & quoted form of appUrl & "; fi"

do shell script shellCmd
