#!/bin/zsh
cd "$(dirname "$0")"
python3 content_link_collector.py desktop-app --host 127.0.0.1 --port 51216 --open
