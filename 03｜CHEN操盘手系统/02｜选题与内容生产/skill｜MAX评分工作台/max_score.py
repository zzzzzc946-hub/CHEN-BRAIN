#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MAX 内容评分系统 · codex 运行版
规则依据：《MAX内容评分体系 V2.1》
用法见 AGENTS.md。零第三方依赖，Python 3.8+。
"""
import json, sys, os, argparse, datetime, urllib.request, urllib.error, urllib.parse

BASE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE, "scores_db.json")
CONFIG_PATH = os.path.join(BASE, "config.json")
BRIDGE_ENV_PATH = os.path.abspath(os.path.join(BASE, "..", "6-系统集成", "飞书-Codex桥接", ".env"))

# ---------- 评分体系常量 ----------
DIMS = [
    ("first", "第一印象", 0.15),
    ("real",  "真实感",   0.15),
    ("depth", "文章深度", 0.20),
    ("scene", "场景度",   0.15),
    ("fit",   "MAX贴合度", 0.15),
    ("value", "用户价值", 0.20),
]
HUMAN_PRE_WEIGHT = 0.70
AI_PRE_WEIGHT = 0.30
TYPES = ["流量型", "人设型", "转化型"]
VERDICTS = [  # (下限, 标签, 动作)
    (9.0, "好内容",  "优先拍摄，纳入投放候选，表现好即追投"),
    (8.0, "可以拍",  "正常排期拍摄发布"),
    (6.5, "需要修改", "针对最低分维度修改，提交修改稿重评；二评仍不到8则PASS"),
    (-1,  "PASS",   "不通过。连选题和角度一起重新判断"),
]

def verdict_of(total):
    for mn, label, action in VERDICTS:
        if total >= mn:
            return label, action
    return "PASS", ""

def calc_total(scores):
    return round(sum(scores.get(k, 0) * w for k, _, w in DIMS), 2)

def calc_pre_total(v):
    if v.get("humanTotal") is None:
        return None
    if v.get("aiTotal") is None:
        return v["humanTotal"]
    return round(v["humanTotal"] * HUMAN_PRE_WEIGHT + v["aiTotal"] * AI_PRE_WEIGHT, 2)

def half(v):
    return round(v * 2) / 2

def clamp_score(v):
    return max(0, min(10, half(v)))

def count_hits(text, words):
    return sum(1 for w in words if w in text)

def auto_ai_blind(script):
    """本地盲评引擎：只读取文案，不读取人工分。"""
    text = (script or "").strip()
    redlines = ["泡妞", "拿下", "拿捏", "收割", "猎物", "灌输", "操控",
                "领域流", "环境压强", "叙事灌输", "路径设计"]
    hit_red = [w for w in redlines if w in text]
    if hit_red:
        return {
            "scores": {k: 0 for k, _, _ in DIMS},
            "reasons": {k: f"触红线：{hit_red[0]}" for k, _, _ in DIMS},
            "weakest": f"触红线：出现「{hit_red[0]}」，按体系直接0分退回",
            "uncertain": []
        }

    length = len(text)
    sentence_count = max(1, sum(text.count(p) for p in "。！？!?"))
    avg_sentence = length / sentence_count
    first_part = text[:180]
    questionish = ("？" in first_part or "?" in first_part or
                  count_hits(first_part, ["为什么", "你有没有发现", "真正", "不是", "而是"]) >= 2)
    ai_markers = ["首先", "其次", "再次", "最后", "综上", "总而言之", "你以为", "其实", "本质上", "第一点", "第二点", "第三点"]
    marker_count = count_hits(text, ai_markers)
    colloquial = count_hits(text, ["你看", "我跟你说", "说白了", "说真的", "对吧", "不是说", "你会发现", "我见过"])
    mechanism = count_hits(text, ["因为", "所以", "机制", "信号", "判断", "代价", "原因", "结果", "定价", "价值", "不是", "而是", "真正"])
    scene_words = ["朋友圈", "照片", "配文", "饭局", "客户", "会议", "办公室", "酒店", "机场", "车", "方向盘",
                   "电梯", "餐厅", "聊天", "发消息", "评论区", "镜头", "视频", "穿搭", "酒局", "合同", "公司"]
    action_words = ["发", "问", "回", "删", "换", "拍", "坐", "站", "开口", "转身", "拒绝", "选择", "展示", "看见"]
    scene_hit = count_hits(text, scene_words)
    action_hit = count_hits(text, action_words)
    max_words = ["MAX", "价值感", "展示面", "审美", "主场", "边界", "定价", "段位", "贵", "身份", "结果", "现实验证"]
    max_hit = count_hits(text, max_words)
    low_fit = count_hits(text, ["兄弟们", "哥们儿", "妹子", "女生", "舔狗", "low男", "脱单", "撩"])
    cliche = count_hits(text, ["高级感", "松弛感", "格局", "内核", "框架", "底层逻辑"])

    first = 6
    if questionish:
        first += 1
    if 450 <= length <= 1600:
        first += 1
    elif length < 180:
        first -= 1.5
    if mechanism >= 5 and scene_hit >= 2:
        first += .5
    if marker_count >= 4:
        first -= 1

    real = 7 + min(colloquial, 3) * .4 - max(0, marker_count - 2) * .45
    if avg_sentence > 80:
        real -= .8
    if count_hits(text, ["、"]) > 14:
        real -= .5
    if marker_count >= 5:
        real = min(real, 6)

    depth = 5 + min(mechanism, 8) * .35
    if count_hits(text, ["不是", "而是"]) >= 2:
        depth += .8
    if mechanism < 3:
        depth = min(depth, 3)
    if scene_hit == 0 and mechanism < 5:
        depth = min(depth, 6)

    scene = 4.5 + min(scene_hit, 5) * .7 + min(action_hit, 5) * .25
    if count_hits(text, ["35", "30+", "客户", "老板", "公司", "生意", "高客单"]) >= 1:
        scene += .5
    if scene_hit == 0:
        scene = min(scene, 6)
    if scene_hit > 0 and action_hit == 0:
        scene = min(scene, 6)

    fit = 5.5 + min(max_hit, 5) * .45 - low_fit * .55
    if max_hit >= 2 and low_fit == 0:
        fit += .7
    if max_hit == 0:
        fit = min(fit, 6)
    if cliche >= 4 and scene_hit < 2:
        fit -= .8

    value = 5 + min(mechanism, 6) * .35 + min(scene_hit, 4) * .25
    if depth >= 7:
        value += .7
    if first >= 8:
        value += .3
    if mechanism < 3:
        value = min(value, 5.5)

    scores = {
        "first": clamp_score(first),
        "real": clamp_score(real),
        "depth": clamp_score(depth),
        "scene": clamp_score(scene),
        "fit": clamp_score(fit),
        "value": clamp_score(value),
    }
    if scores["scene"] <= 6:
        scores["depth"] = min(scores["depth"], 7)

    reasons = {
        "first": "开头抓取力、篇幅和机制密度综合判断。",
        "real": "按口语毛边、模板转折和书面化痕迹判断。",
        "depth": "按增量判断、机制解释和是否只是常识复述判断。",
        "scene": "按目标用户场景、具体动作和细节颗粒度判断。",
        "fit": "按MAX判断方式、价值感语境和低龄/通用表达偏移判断。",
        "value": "按用户能否带走刺痛或可复用判断判断。",
    }
    weakest_key, weakest_name, _ = min(DIMS, key=lambda d: scores[d[0]])
    uncertain = []
    if length < 240:
        uncertain.append("文案较短，部分维度置信度偏低")
    if scene_hit == 0:
        uncertain.append("缺少明确场景，场景度与深度可能被高估")
    return {
        "scores": scores,
        "reasons": reasons,
        "weakest": f"{weakest_name}最低：{reasons[weakest_key]}",
        "uncertain": uncertain[:2]
    }

def apply_ai_meta(v, data):
    scores = data["scores"]
    for k, _, _ in DIMS:
        scores[k] = float(scores[k])
    v["ai"] = {k: scores[k] for k, _, _ in DIMS}
    v["aiTotal"] = calc_total(v["ai"])
    v["aiMeta"] = {"reasons": data.get("reasons", {}),
                   "weakest": data.get("weakest", ""),
                   "uncertain": data.get("uncertain", [])}

# ---------- 存储 ----------
def load_db():
    if os.path.exists(DB_PATH):
        with open(DB_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_db(db):
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

def find(db, eid):
    for e in db:
        if e["id"] == eid:
            return e
    sys.exit(f"未找到记录 {eid}，用 list 查看全部ID")

def now():
    return datetime.datetime.now().isoformat(timespec="seconds")

# ---------- 展示 ----------
def parse_scores(raw):
    parts = [p.strip() for p in raw.split(",")]
    if len(parts) != 6:
        sys.exit("需要6个分数，顺序：第一印象,真实感,文章深度,场景度,MAX贴合度,用户价值（例：7,6.5,8,7,7.5,8）")
    vals = []
    for p in parts:
        v = float(p)
        if not (0 <= v <= 10):
            sys.exit(f"分数 {v} 越界（0-10）")
        vals.append(v)
    return {k: vals[i] for i, (k, _, _) in enumerate(DIMS)}

def print_result(entry):
    v = entry["versions"][0]
    pre_total = calc_pre_total(v)
    label, action = verdict_of(pre_total)
    print("=" * 56)
    print(f"《{entry['title']}》 {entry['type']} · 第{v['v']}稿")
    ai_total = f"{v['aiTotal']:.2f}" if v.get("aiTotal") is not None else "—"
    print(f"发布前总评分 {pre_total:.2f}   人工评分 {v['humanTotal']:.2f}   AI评分 {ai_total}")
    print(f"评价：【{label}】 {action}")
    print("-" * 56)
    if v.get("ai"):
        has_human_dims = isinstance(v.get("human"), dict) and all(k in v["human"] for k, _, _ in DIMS)
        if has_human_dims:
            print(f"{'维度':　<6}{'人工':>5}{'AI':>6}{'差值':>6}  AI理由")
        else:
            print(f"{'维度':　<6}{'AI':>6}  AI理由")
        warn_any = False
        for k, name, _ in DIMS:
            a = v["ai"][k]
            reason = (v.get("aiMeta") or {}).get("reasons", {}).get(k, "")
            if has_human_dims:
                h = v["human"][k]
                diff = abs(h - a)
                mark = " ⚠" if diff >= 2 else "  "
                if diff >= 2:
                    warn_any = True
                print(f"{name:　<6}{h:>5.1f}{a:>6.1f}{diff:>5.1f}{mark} {reason}")
            else:
                print(f"{name:　<6}{a:>6.1f}  {reason}")
        human_meta = v.get("humanMeta") or {}
        if human_meta.get("issues"):
            print(f"人工主因：{'、'.join(human_meta['issues'])}")
        if human_meta.get("note"):
            print(f"人工评价：{human_meta['note']}")
        meta = v.get("aiMeta") or {}
        if meta.get("weakest"):
            print(f"AI自认最弱：{meta['weakest']}")
        if meta.get("uncertain"):
            print(f"AI拿不准：{'；'.join(meta['uncertain'])}")
        if warn_any:
            print(">> 存在维度差值≥2：必须记入语感校准库（写明AI高估/低估了什么）")
    else:
        print("（尚未录入AI盲评分，先执行 ai 命令）")
    if pre_total < 8 and v["v"] >= 2:
        print(">> 二评仍不到8分，按体系规则：PASS")
    print("=" * 56)

# ---------- 子命令 ----------
def cmd_new(args):
    db = load_db()
    with open(args.script_file, "r", encoding="utf-8") as f:
        script = f.read().strip()
    if args.type not in TYPES:
        sys.exit(f"内容类型必须是：{' / '.join(TYPES)}")
    eid = datetime.datetime.now().strftime("%y%m%d%H%M%S")
    entry = {
        "id": eid, "createdAt": now(), "title": args.title, "type": args.type,
        "versions": [{"v": 1, "script": script, "changeNote": "",
                      "human": None, "humanTotal": None,
                      "ai": None, "aiTotal": None, "aiMeta": None,
                      "ts": now(), "feishu_record_id": None}],
    }
    db.insert(0, entry)
    save_db(db)
    print(f"已创建记录 id={eid}（第1稿）")
    print("下一步（盲评协议）：先完成AI盲评并写入文件，再向人工要分。")
    print(f"  1. AI按 AGENTS.md 锚点盲评，结果写入 ai_{eid}.json")
    print(f"  2. python max_score.py ai {eid} --file ai_{eid}.json")
    print(f"  3. python max_score.py human {eid} --scores 7,6.5,8,7,7.5,8")

def cmd_ai(args):
    db = load_db()
    entry = find(db, args.id)
    with open(args.file, "r", encoding="utf-8") as f:
        data = json.load(f)
    for k, _, _ in DIMS:
        if k not in data["scores"]:
            sys.exit(f"ai文件缺少维度 {k}")
    v = entry["versions"][0]
    apply_ai_meta(v, data)
    save_db(db)
    print(f"AI盲评已录入（总分 {v['aiTotal']:.2f}，明细暂不展示——等人工分录入后一并对比）")
    if v["human"]:
        print_result(entry)

def cmd_human(args):
    db = load_db()
    entry = find(db, args.id)
    v = entry["versions"][0]
    v["human"] = parse_scores(args.scores)
    v["humanTotal"] = calc_total(v["human"])
    save_db(db)
    print_result(entry)

def cmd_revise(args):
    db = load_db()
    entry = find(db, args.id)
    if not args.note.strip():
        sys.exit("--note（改了什么）是必填项——这是AI理解校准方向的关键")
    with open(args.script_file, "r", encoding="utf-8") as f:
        script = f.read().strip()
    pv = entry["versions"][0]
    entry["versions"].insert(0, {
        "v": pv["v"] + 1, "script": script, "changeNote": args.note.strip(),
        "human": None, "humanTotal": None, "ai": None, "aiTotal": None,
        "aiMeta": None, "ts": now(), "feishu_record_id": None})
    save_db(db)
    print(f"第{pv['v']+1}稿已创建。按盲评协议重新走 ai → human。")
    print(f"修改说明：{args.note.strip()}")

def cmd_list(args):
    db = load_db()
    if not db:
        print("暂无记录")
        return
    print(f"{'ID':<14}{'稿':<3}{'总评':>5}{'AI':>6}  评价     标题")
    for e in db:
        v = e["versions"][0]
        ht = f"{v['humanTotal']:.1f}" if v["humanTotal"] is not None else "—"
        at = f"{v['aiTotal']:.1f}" if v["aiTotal"] is not None else "—"
        pre_total = calc_pre_total(v)
        lbl = verdict_of(pre_total)[0] if pre_total is not None else "未评"
        sync = "✓" if v.get("feishu_record_id") else " "
        pt = f"{pre_total:.1f}" if pre_total is not None else "—"
        print(f"{e['id']:<14}{v['v']:<3}{pt:>5}{at:>6}  {lbl:<5}{sync} {e['title'][:24]}")

def cmd_show(args):
    db = load_db()
    print_result(find(db, args.id))

def cmd_export(args):
    out = os.path.join(BASE, f"max_scores_export_{datetime.date.today()}.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(load_db(), f, ensure_ascii=False, indent=2)
    print(f"已导出：{out}")

# ---------- 飞书同步 ----------
def feishu_config():
    if not os.path.exists(CONFIG_PATH):
        sys.exit("缺少 config.json，参照 config.example.json 创建并填入飞书凭证")
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = json.load(f).get("feishu", {})
    for k in ("app_id", "app_secret", "app_token", "table_id"):
        if not cfg.get(k):
            sys.exit(f"config.json 缺少 feishu.{k}")
    return cfg

def http_json(url, payload=None, token=None, method=None):
    headers = {"Content-Type": "application/json; charset=utf-8"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, headers=headers,
                                 method=method or ("POST" if data else "GET"))
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "ignore")
        sys.exit(f"飞书API错误 HTTP {e.code}: {body[:300]}")
    except urllib.error.URLError as e:
        sys.exit(f"网络错误：{e.reason}")

def http_json_result(url, payload=None, token=None, method=None):
    headers = {"Content-Type": "application/json; charset=utf-8"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, headers=headers,
                                 method=method or ("POST" if data else "GET"))
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "ignore")
        try:
            return e.code, json.loads(body)
        except Exception:
            return e.code, {"code": e.code, "msg": body[:500]}
    except urllib.error.URLError as e:
        return 0, {"code": "NETWORK_ERROR", "msg": str(e.reason)}

def feishu_token(cfg):
    r = http_json("https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
                  {"app_id": cfg["app_id"], "app_secret": cfg["app_secret"]})
    if r.get("code") != 0:
        sys.exit(f"获取tenant_access_token失败：{r}")
    return r["tenant_access_token"]

def read_simple_env(path):
    out = {}
    if not os.path.exists(path):
        return out
    with open(path, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip().strip('"').strip("'")
    return out

def write_config(app_id, app_secret, app_token, table_id):
    data = {"feishu": {
        "app_id": app_id.strip(),
        "app_secret": app_secret.strip(),
        "app_token": app_token.strip(),
        "table_id": table_id.strip(),
    }}
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def feishu_permission_url(app_id):
    q = urllib.parse.quote("bitable:app,base:app:create")
    return f"https://open.feishu.cn/app/{app_id}/auth?q={q}&op_from=openapi&token_type=tenant"

FIELD_SPECS = [
    ("标题", 1, None),
    ("记录ID", 1, None),
    ("内容类型", 3, ["流量型", "人设型", "转化型"]),
    ("稿次", 2, None),
    ("评价", 3, ["好内容", "可以拍", "需要修改", "PASS", "未评"]),
    ("发布前总评分", 2, None),
    ("人工总分", 2, None),
    ("AI总分", 2, None),
    ("人工主因", 1, None),
    ("人工评价", 1, None),
    ("差值告警", 1, None),
    ("修改说明", 1, None),
    ("AI最弱维度", 1, None),
    ("AI拿不准", 1, None),
    ("文案", 1, None),
    ("评分时间", 5, None),
] + [(f"人工-{name}", 2, None) for _, name, _ in DIMS] + [(f"AI-{name}", 2, None) for _, name, _ in DIMS]

def field_payload(name, typ, options=None):
    payload = {"field_name": name, "type": typ}
    if typ == 3 and options:
        payload["property"] = {"options": [{"name": x} for x in options]}
    return payload

def build_fields(entry, v):
    pre_total = calc_pre_total(v)
    label, _ = verdict_of(pre_total) if pre_total is not None else ("未评", "")
    warn = ""
    has_human_dims = isinstance(v.get("human"), dict) and all(k in v["human"] for k, _, _ in DIMS)
    if v.get("ai") and has_human_dims:
        warns = [name for k, name, _ in DIMS if abs(v["human"][k] - v["ai"][k]) >= 2]
        warn = "⚠ " + "、".join(warns) if warns else "无"
    elif v.get("ai") and v.get("humanTotal") is not None:
        diff = abs(v["humanTotal"] - v.get("aiTotal", v["humanTotal"]))
        warn = f"总分差值 {diff:.1f}" if diff >= 1.5 else "无"
    meta = v.get("aiMeta") or {}
    human_meta = v.get("humanMeta") or {}
    fields = {
        "标题": entry["title"],
        "内容类型": entry["type"],
        "稿次": v["v"],
        "评价": label,
        "发布前总评分": pre_total,
        "人工总分": v["humanTotal"],
        "AI总分": v.get("aiTotal"),
        "差值告警": warn,
        "人工主因": "、".join(human_meta.get("issues", [])),
        "人工评价": human_meta.get("note", ""),
        "修改说明": v.get("changeNote", ""),
        "AI最弱维度": meta.get("weakest", ""),
        "AI拿不准": "；".join(meta.get("uncertain", [])),
        "文案": v["script"],
        "评分时间": int(datetime.datetime.fromisoformat(v["ts"]).timestamp() * 1000),
        "记录ID": f"{entry['id']}-v{v['v']}",
    }
    for k, name, _ in DIMS:
        if has_human_dims:
            fields[f"人工-{name}"] = v["human"][k]
        if v.get("ai"):
            fields[f"AI-{name}"] = v["ai"][k]
    return {k: val for k, val in fields.items() if val is not None}

def sync_entry_to_feishu(entry, v):
    if v["humanTotal"] is None:
        raise SystemExit("该稿尚未录入人工分，评完再同步")
    cfg = feishu_config()
    token = feishu_token(cfg)
    base = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{cfg['app_token']}/tables/{cfg['table_id']}/records"
    payload = {"fields": build_fields(entry, v)}
    if v.get("feishu_record_id"):
        r = http_json(f"{base}/{v['feishu_record_id']}", payload, token, method="PUT")
        action = "更新"
    else:
        r = http_json(base, payload, token)
        action = "新建"
    if r.get("code") != 0:
        raise SystemExit(f"同步失败：{r}")
    v["feishu_record_id"] = r["data"]["record"]["record_id"]
    return action, v["feishu_record_id"]

def cmd_sync(args):
    db = load_db()
    entry = find(db, args.id)
    v = entry["versions"][0]
    action, record_id = sync_entry_to_feishu(entry, v)
    save_db(db)
    print(f"已{action}飞书记录：{entry['title']} 第{v['v']}稿 → record_id={record_id}")

def cmd_sync_test(args):
    cfg = feishu_config()
    token = feishu_token(cfg)
    r = http_json(f"https://open.feishu.cn/open-apis/bitable/v1/apps/{cfg['app_token']}/tables/{cfg['table_id']}/fields",
                  token=token)
    if r.get("code") != 0:
        sys.exit(f"读取字段失败：{r}")
    names = [f["field_name"] for f in r["data"]["items"]]
    print(f"连接成功。表内现有字段（{len(names)}个）：{'、'.join(names)}")
    need = (["标题", "内容类型", "稿次", "评价", "发布前总评分", "人工总分", "AI总分", "差值告警",
             "人工主因", "人工评价",
             "修改说明", "AI最弱维度", "AI拿不准", "文案", "评分时间", "记录ID"]
            + [f"人工-{n}" for _, n, _ in DIMS] + [f"AI-{n}" for _, n, _ in DIMS])
    missing = [n for n in need if n not in names]
    if missing:
        print(f"缺少字段（请在表中创建，名称必须完全一致）：{'、'.join(missing)}")
    else:
        print("字段齐全，可以开始 sync。")

def cmd_config_from_bridge(args):
    env = read_simple_env(args.env)
    app_id = env.get("FEISHU_APP_ID", "")
    app_secret = env.get("FEISHU_APP_SECRET", "")
    if not app_id or not app_secret:
        sys.exit(f"未在 {args.env} 找到 FEISHU_APP_ID / FEISHU_APP_SECRET")
    if not args.app_token or not args.table_id:
        sys.exit("需要提供 --app-token 和 --table-id；如果还没有表，先运行 create-bitable（应用需开通 bitable 权限）")
    write_config(app_id, app_secret, args.app_token, args.table_id)
    print(f"已写入 {CONFIG_PATH}（App Secret 未显示）")

def cmd_create_bitable(args):
    env = read_simple_env(args.env)
    app_id = args.app_id or env.get("FEISHU_APP_ID", "")
    app_secret = args.app_secret or env.get("FEISHU_APP_SECRET", "")
    if not app_id or not app_secret:
        sys.exit("缺少 app_id/app_secret。可传 --app-id/--app-secret，或先配置飞书桥接 .env")
    cfg = {"app_id": app_id, "app_secret": app_secret}
    token = feishu_token(cfg)
    status, payload = http_json_result("https://open.feishu.cn/open-apis/bitable/v1/apps",
                                       {"name": args.name}, token)
    if status >= 400 or payload.get("code") != 0:
        msg = json.dumps(payload, ensure_ascii=False, indent=2)
        if payload.get("code") == 99991672:
            print("飞书应用缺少多维表格权限。请开通权限并发布应用后重试：")
            print(feishu_permission_url(app_id))
        sys.exit(f"创建多维表格失败：\n{msg}")
    data = payload.get("data", {})
    app = data.get("app") or data
    app_token = app.get("app_token") or data.get("app_token")
    default_table_id = app.get("default_table_id") or data.get("default_table_id") or app.get("table_id") or data.get("table_id")
    if not app_token:
        sys.exit(f"创建成功但未找到 app_token，返回：{json.dumps(payload, ensure_ascii=False, indent=2)}")

    table_id = default_table_id
    if not table_id:
        status, payload = http_json_result(f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables",
                                           {"table": {"name": args.table_name}}, token)
        if status >= 400 or payload.get("code") != 0:
            sys.exit(f"创建数据表失败：\n{json.dumps(payload, ensure_ascii=False, indent=2)}")
        table = (payload.get("data") or {}).get("table") or payload.get("data") or {}
        table_id = table.get("table_id")

    write_config(app_id, app_secret, app_token, table_id)
    print("已创建飞书多维表格并写入 config.json")
    print(f"app_token={app_token}")
    print(f"table_id={table_id}")
    cmd_init_fields(argparse.Namespace())

def cmd_init_fields(args):
    cfg = feishu_config()
    token = feishu_token(cfg)
    base = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{cfg['app_token']}/tables/{cfg['table_id']}/fields"
    status, payload = http_json_result(base, token=token, method="GET")
    if status >= 400 or payload.get("code") != 0:
        if payload.get("code") == 99991672:
            print("飞书应用缺少多维表格权限。请开通权限并发布应用后重试：")
            print(feishu_permission_url(cfg["app_id"]))
        sys.exit(f"读取字段失败：\n{json.dumps(payload, ensure_ascii=False, indent=2)}")
    items = (payload.get("data") or {}).get("items") or []
    existing = {x.get("field_name") for x in items}
    created, skipped, failed = [], [], []
    for name, typ, options in FIELD_SPECS:
        if name in existing:
            skipped.append(name)
            continue
        status, payload = http_json_result(base, field_payload(name, typ, options), token)
        if status < 400 and payload.get("code") == 0:
            created.append(name)
        else:
            failed.append((name, payload))
    print(f"字段初始化完成：新建 {len(created)} 个，已存在 {len(skipped)} 个，失败 {len(failed)} 个")
    if created:
        print("新建字段：" + "、".join(created))
    if failed:
        print("失败字段：")
        for name, payload in failed:
            print(f"- {name}: {json.dumps(payload, ensure_ascii=False)[:300]}")
        sys.exit(1)

# ---------- 本地工作台服务器 ----------
def _strip_blind(db):
    """盲评保护：人工分未录入的版本，不向前端暴露AI明细"""
    out = json.loads(json.dumps(db))
    for e in out:
        for v in e["versions"]:
            v["aiDone"] = v.get("ai") is not None
            if v.get("human") is None:
                v["ai"] = None
                v["aiTotal"] = None
                v["aiMeta"] = None
    return out

def _ensure_ai_for_scored(db):
    changed = False
    for e in db:
        for v in e.get("versions", []):
            if v.get("human") is not None and v.get("ai") is None:
                apply_ai_meta(v, auto_ai_blind(v.get("script", "")))
                changed = True
    if changed:
        save_db(db)
    return db

def cmd_serve(args):
    import http.server, socketserver
    index_path = os.path.join(BASE, "index.html")

    class H(http.server.BaseHTTPRequestHandler):
        def _json(self, code, obj):
            body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path in ("/", "/index.html"):
                try:
                    with open(index_path, "rb") as f:
                        body = f.read()
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                except FileNotFoundError:
                    self._json(404, {"error": "index.html 不在脚本同目录"})
            elif self.path == "/api/entries":
                self._json(200, _strip_blind(_ensure_ai_for_scored(load_db())))
            else:
                self._json(404, {"error": "not found"})

        def do_POST(self):
            try:
                length = int(self.headers.get("Content-Length", 0))
                data = json.loads(self.rfile.read(length) or b"{}")
            except Exception:
                return self._json(400, {"error": "请求体不是合法JSON"})
            try:
                if self.path == "/api/new":
                    db = load_db()
                    if data.get("type") not in TYPES:
                        return self._json(400, {"error": "内容类型不合法"})
                    if not (data.get("script") or "").strip():
                        return self._json(400, {"error": "文案为空"})
                    eid = datetime.datetime.now().strftime("%y%m%d%H%M%S")
                    db.insert(0, {"id": eid, "createdAt": now(),
                        "title": (data.get("title") or "未命名选题").strip(), "type": data["type"],
                        "versions": [{"v": 1, "script": data["script"].strip(), "changeNote": "",
                                      "human": None, "humanTotal": None, "ai": None, "aiTotal": None,
                                      "aiMeta": None, "ts": now(), "feishu_record_id": None}]})
                    save_db(db)
                    return self._json(200, {"id": eid, "msg": "已创建。请先完成你的人工评分；提交后会立刻揭晓AI对比"})

                if self.path == "/api/human":
                    db = load_db()
                    entry = next((e for e in db if e["id"] == data.get("id")), None)
                    if not entry:
                        return self._json(404, {"error": "记录不存在"})
                    v = entry["versions"][0]
                    if v.get("ai") is None:
                        apply_ai_meta(v, auto_ai_blind(v.get("script", "")))
                    if "total" in data:
                        total = float(data.get("total"))
                        if not (0 <= total <= 10):
                            return self._json(400, {"error": "总分越界"})
                        issues = data.get("issues") or []
                        if len(issues) > 2:
                            return self._json(400, {"error": "主因最多选择2个"})
                        v["human"] = {"overall": total}
                        v["humanTotal"] = round(total, 2)
                        v["humanMeta"] = {
                            "issues": [str(x) for x in issues[:2]],
                            "note": (data.get("note") or "").strip()
                        }
                    else:
                        scores = data.get("scores") or {}
                        for k, _, _ in DIMS:
                            if k not in scores:
                                return self._json(400, {"error": f"缺少维度 {k}"})
                            scores[k] = float(scores[k])
                            if not (0 <= scores[k] <= 10):
                                return self._json(400, {"error": "分数越界"})
                        v["human"] = {k: scores[k] for k, _, _ in DIMS}
                        v["humanTotal"] = calc_total(v["human"])
                        v["humanMeta"] = {
                            "issues": [str(x) for x in (data.get("issues") or [])[:2]],
                            "note": (data.get("note") or "").strip()
                        }
                    sync_status = {"ok": False, "skipped": True, "message": "飞书未配置，结果已保存在本地"}
                    if os.path.exists(CONFIG_PATH):
                        try:
                            action, record_id = sync_entry_to_feishu(entry, v)
                            sync_status = {"ok": True, "skipped": False,
                                           "message": f"已{action}飞书记录",
                                           "record_id": record_id}
                        except SystemExit as e:
                            sync_status = {"ok": False, "skipped": False,
                                           "message": str(e)}
                    save_db(db)
                    return self._json(200, {"entry": _strip_blind([entry])[0],
                                            "sync": sync_status})

                if self.path == "/api/revise":
                    db = load_db()
                    entry = next((e for e in db if e["id"] == data.get("id")), None)
                    if not entry:
                        return self._json(404, {"error": "记录不存在"})
                    if not (data.get("note") or "").strip():
                        return self._json(400, {"error": "「改了什么」是必填项"})
                    if not (data.get("script") or "").strip():
                        return self._json(400, {"error": "修改后全文为空"})
                    pv = entry["versions"][0]
                    entry["versions"].insert(0, {"v": pv["v"] + 1, "script": data["script"].strip(),
                        "changeNote": data["note"].strip(), "human": None, "humanTotal": None,
                        "ai": None, "aiTotal": None, "aiMeta": None, "ts": now(),
                        "feishu_record_id": None})
                    save_db(db)
                    return self._json(200, {"msg": f"第{pv['v']+1}稿已创建。请让codex对新稿执行AI盲评"})

                if self.path == "/api/sync":
                    db = load_db()
                    entry = next((e for e in db if e["id"] == data.get("id")), None)
                    if not entry:
                        return self._json(404, {"error": "记录不存在"})
                    v = entry["versions"][0]
                    if v["humanTotal"] is None:
                        return self._json(400, {"error": "该稿尚未录入人工分"})
                    try:
                        cfg = feishu_config()
                        token = feishu_token(cfg)
                        base_url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{cfg['app_token']}/tables/{cfg['table_id']}/records"
                        payload = {"fields": build_fields(entry, v)}
                        if v.get("feishu_record_id"):
                            r = http_json(f"{base_url}/{v['feishu_record_id']}", payload, token, method="PUT")
                        else:
                            r = http_json(base_url, payload, token)
                        if r.get("code") != 0:
                            return self._json(500, {"error": f"飞书返回错误：{r}"})
                        v["feishu_record_id"] = r["data"]["record"]["record_id"]
                        save_db(db)
                        return self._json(200, {"msg": "已同步飞书", "record_id": v["feishu_record_id"]})
                    except SystemExit as e:
                        return self._json(500, {"error": str(e)})

                return self._json(404, {"error": "not found"})
            except Exception as e:
                return self._json(500, {"error": f"服务端异常：{e}"})

        def log_message(self, *a):
            pass

    class LocalServer(socketserver.ThreadingTCPServer):
        allow_reuse_address = True

    port = args.port
    print(f"MAX评分工作台已启动：http://localhost:{port}")
    print("浏览器打开上述地址即可。Ctrl+C 停止。")
    with LocalServer(("127.0.0.1", port), H) as srv:
        try:
            srv.serve_forever()
        except KeyboardInterrupt:
            print("\n已停止")

# ---------- 入口 ----------
def main():
    p = argparse.ArgumentParser(description="MAX内容评分系统 codex版（规则：评分体系V2.1）")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("new", help="创建新评分记录")
    s.add_argument("--title", required=True)
    s.add_argument("--type", required=True, help="流量型/人设型/转化型")
    s.add_argument("--script-file", required=True, help="文案txt路径")
    s.set_defaults(fn=cmd_new)

    s = sub.add_parser("ai", help="录入AI盲评结果")
    s.add_argument("id")
    s.add_argument("--file", required=True, help="ai评分json路径")
    s.set_defaults(fn=cmd_ai)

    s = sub.add_parser("human", help="录入人工六维分")
    s.add_argument("id")
    s.add_argument("--scores", required=True,
                   help="顺序：第一印象,真实感,文章深度,场景度,MAX贴合度,用户价值")
    s.set_defaults(fn=cmd_human)

    s = sub.add_parser("revise", help="提交修改稿（创建新版本）")
    s.add_argument("id")
    s.add_argument("--note", required=True, help="改了什么（必填）")
    s.add_argument("--script-file", required=True)
    s.set_defaults(fn=cmd_revise)

    s = sub.add_parser("list", help="查看全部记录")
    s.set_defaults(fn=cmd_list)
    s = sub.add_parser("show", help="查看单条结果")
    s.add_argument("id")
    s.set_defaults(fn=cmd_show)
    s = sub.add_parser("export", help="导出全部数据JSON")
    s.set_defaults(fn=cmd_export)
    s = sub.add_parser("sync", help="同步当前稿到飞书")
    s.add_argument("id")
    s.set_defaults(fn=cmd_sync)
    s = sub.add_parser("sync-test", help="测试飞书连接与字段")
    s.set_defaults(fn=cmd_sync_test)
    s = sub.add_parser("config-from-bridge", help="复用飞书桥接.env写入评分系统config.json")
    s.add_argument("--env", default=BRIDGE_ENV_PATH)
    s.add_argument("--app-token", required=True)
    s.add_argument("--table-id", required=True)
    s.set_defaults(fn=cmd_config_from_bridge)
    s = sub.add_parser("create-bitable", help="创建飞书多维表格并初始化字段")
    s.add_argument("--env", default=BRIDGE_ENV_PATH)
    s.add_argument("--app-id", default="")
    s.add_argument("--app-secret", default="")
    s.add_argument("--name", default="MAX内容评分")
    s.add_argument("--table-name", default="评分记录")
    s.set_defaults(fn=cmd_create_bitable)
    s = sub.add_parser("init-fields", help="根据config.json初始化飞书字段")
    s.set_defaults(fn=cmd_init_fields)

    s = sub.add_parser("serve", help="启动本地前端工作台")
    s.add_argument("--port", type=int, default=8765)
    s.set_defaults(fn=cmd_serve)

    args = p.parse_args()
    args.fn(args)

if __name__ == "__main__":
    main()
