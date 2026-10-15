"""
카드뉴스 이미지 렌더러 (1080x1080 PNG)
사용: python cards/render.py spec.json out_dir/
spec.json = {"theme": "mint", "cards": [{"name": "cover", "type": "cover", ...}, ...]}

공통: name(파일명), type, tag(상단 알약), title (줄바꿈 \n 가능, **굵게** 는 형광펜)
- cover   : subtitle, emoji, chips[2~3]  (썸네일)
- points  : emoji, points[{t, d}] 3~4개 (t=한 줄 요점, d=짧은 설명)
- compare : headers[2~3], rows[[...]] 3~5행, tip (아래 팁 박스)
- bars    : items[{label, value, display}] 2~4개, takeaway (결론 박스), note (작은 주석)
- qa      : items[{q, a}] 2~3개
- check   : emoji, items[4~6] (체크리스트), tip
theme: mint | peach | lavender | sky | lemon
"""
import html
import json
import sys
import pathlib
from playwright.sync_api import sync_playwright

THEMES = {
    "mint":     ("#E7F7F1", "#2BB58A", "#14543F"),
    "peach":    ("#FFEFE6", "#FF8A5B", "#7A3418"),
    "lavender": ("#F1ECFF", "#8B6CF0", "#3B2A7A"),
    "sky":      ("#E8F3FF", "#3D8BFD", "#16386B"),
    "lemon":    ("#FFF8DC", "#E0A800", "#6B5000"),
}
BRAND = "quantlib-diary.blogspot.com"

BASE_CSS = """
*{margin:0;padding:0;box-sizing:border-box}
body{width:1080px;height:1080px;background:var(--bg);font-family:'Noto Sans CJK KR','Noto Color Emoji',sans-serif;color:var(--ink);
     display:flex;align-items:center;justify-content:center;overflow:hidden;position:relative;word-break:keep-all}
.blob{position:absolute;border-radius:50%;background:var(--accent);opacity:.12}
.dots{position:absolute;top:70px;right:80px;width:160px;height:100px;opacity:.35;
      background-image:radial-gradient(var(--accent) 3px,transparent 3.5px);background-size:22px 22px}
.card{position:relative;width:960px;height:960px;background:#fff;border-radius:56px;padding:60px 70px 96px;
      box-shadow:0 24px 60px rgba(0,0,0,.08);display:flex;flex-direction:column}
.top{display:flex;align-items:center;gap:16px}
.tag{background:var(--accent);color:#fff;font-weight:700;font-size:28px;padding:9px 24px;border-radius:999px}
.page{font-size:26px;color:#B0B7C0;font-weight:700}
.brand{position:absolute;bottom:30px;left:0;right:0;text-align:center;font-size:22px;color:#B0B7C0;font-weight:500}
h1{font-weight:900;letter-spacing:-1.5px;line-height:1.25}
.hl{background:linear-gradient(transparent 60%, var(--hl) 60%)}
.box{background:var(--bg);border-radius:28px;padding:26px 32px;font-size:32px;line-height:1.45;font-weight:600;
     display:flex;gap:18px;align-items:flex-start}
.box .ic{font-size:40px;line-height:1.1}
.muted{color:#6B7280}
"""


def esc(s):
    s = html.escape(str(s))
    parts = s.split("**")
    s = "".join(f'<span class="hl">{p}</span>' if i % 2 else p for i, p in enumerate(parts))
    return s.replace("\n", "<br>")


PRO_CSS = """
body{background:#E9ECF1}
.blob,.dots,.emoji{display:none}
.card{border-radius:10px;box-shadow:0 2px 0 rgba(15,27,45,.06);padding-top:56px}
.card:before{content:"";position:absolute;left:0;top:0;right:0;height:10px;background:var(--accent);border-radius:10px 10px 0 0}
h1{font-family:'Noto Serif CJK KR',serif;font-weight:900;letter-spacing:-1px}
.hl{background:none;border-bottom:5px solid var(--accent)}
.tag{border-radius:4px;background:none;color:var(--accent);border:2px solid var(--accent);font-size:24px;letter-spacing:1px;padding:6px 16px}
.page{font-family:'Noto Sans Mono CJK KR',monospace}
.brand{font-family:'Noto Sans Mono CJK KR',monospace;letter-spacing:1px;text-align:right;right:70px;left:auto}
.box{border-radius:6px;background:#F3F5F8;border-left:6px solid var(--accent)}
.box .ic{display:none}
.row{border-radius:6px;background:#F7F8FA;border-left:6px solid var(--accent)}
.num,.ck{border-radius:4px;font-family:'Noto Sans Mono CJK KR',monospace}
.it{border-bottom:2px solid #E6E9EE}
th{border-radius:0 !important;background:#fff !important;color:var(--ink) !important;border-top:4px solid var(--ink);border-bottom:2px solid var(--ink)}
td{border-radius:0 !important;background:#fff !important;border-bottom:1px solid #D9DEE5}
.q{border-radius:4px;background:none;color:var(--accent);padding:0 0 0 20px;border-left:6px solid var(--accent)}
.a{align-self:stretch;max-width:100%;border-radius:4px;background:#F7F8FA;margin-left:26px}
.chip{border-radius:4px;border-width:2px;font-size:24px;font-family:'Noto Sans Mono CJK KR',monospace}
/* cover */
.pro-cover body{background:#0F1B2D}
.cov{background:#0F1B2D !important;color:#fff}
.cov h1{color:#fff}.cov .sub{color:#AEB8C6 !important}
.cov .hl{border-bottom-color:#7FA7D9}
.cov .tag{color:#9FC0E8;border-color:#9FC0E8}
.cov .chip{color:#C9D6E6;border-color:#4A6283}
.cov .chips{flex-direction:row;flex-wrap:wrap;gap:12px}.cov .formula+.bottom{margin-top:0}
.cov .brand{color:#6F8099}
.cov:before{background:#7FA7D9}
.formula{font-family:'Noto Serif CJK KR',serif;font-style:italic;font-size:44px;color:#7FA7D9;
         border-top:1px solid #33465F;padding-top:26px;margin-top:auto;margin-bottom:26px}
"""

THEMES["navy"] = ("#E9ECF1", "#1F4E8C", "#0F1B2D")


def page(theme, body, css="", s=None):
    s = s or {}
    pro = s.get("style") == "pro"
    if pro:
        theme = theme if theme in ("navy",) else "navy"
    bg, accent, ink = THEMES.get(theme, THEMES["mint"])
    extra = PRO_CSS if pro else ""
    cls = "card cov" if (pro and s.get("type") == "cover") else "card"
    if pro and s.get("type") == "cover" and s.get("formula"):
        body = body.replace('<div class="bottom">', f'<div class="formula">{s.get("formula", "")}</div><div class="bottom">')
    return f"""<html><head><meta charset="utf-8"><style>
:root{{--bg:{bg};--accent:{accent};--ink:{ink};--hl:{accent}55}}{BASE_CSS}{css}{extra}</style></head>
<body><div class="blob" style="width:420px;height:420px;top:-130px;left:-150px"></div>
<div class="blob" style="width:320px;height:320px;bottom:-100px;right:-70px"></div>
<div class="{cls}"><div class="dots"></div>{body}<div class="brand">{BRAND}</div></div></body></html>"""


def top(s, default, idx):
    pg = f'<span class="page">{idx}</span>' if idx else ""
    return f'<div class="top"><div class="tag">{esc(s.get("tag", default))}</div>{pg}</div>'


def cover(s, idx):
    css = """h1{font-size:92px;margin-top:50px}.sub{font-size:38px;margin-top:30px;line-height:1.5}
.bottom{margin-top:auto;display:flex;align-items:flex-end;justify-content:space-between}
.chips{display:flex;flex-direction:column;gap:14px}
.chip{align-self:flex-start;border:3px solid var(--accent);color:var(--accent);font-weight:800;font-size:30px;padding:8px 22px;border-radius:999px}
.emoji{font-size:230px;line-height:1}"""
    chips = "".join(f'<div class="chip"># {esc(c)}</div>' for c in s.get("chips", [])[:3])
    raw = s["title"].replace("**", "")
    longest = max(len(l) for l in raw.split("\n"))
    lines = raw.count("\n") + 1 + sum(len(l) > 9 for l in raw.split("\n"))
    if lines >= 4 or longest > 11:
        css += "h1{font-size:72px}.emoji{font-size:180px}"
    if lines >= 5:
        css += "h1{font-size:62px}.chip{font-size:26px}"
    body = f"""{top(s, '재테크 사전', '')}<h1>{esc(s['title'])}</h1><div class="sub muted">{esc(s.get('subtitle', ''))}</div>
<div class="bottom"><div class="chips">{chips}</div><div class="emoji">{s.get('emoji', '💰')}</div></div>"""
    return page(s.get("theme"), body, css, s)


def points(s, idx):
    css = """h1{font-size:60px;margin:34px 0 34px}.emoji{position:absolute;top:56px;right:72px;font-size:100px}
.list{display:flex;flex-direction:column;gap:20px;flex:1;justify-content:center}
.row{display:flex;gap:26px;background:var(--bg);border-radius:28px;padding:24px 28px;align-items:center}
.num{flex:none;width:64px;height:64px;border-radius:20px;background:var(--accent);color:#fff;font-size:34px;font-weight:900;
     display:flex;align-items:center;justify-content:center}
.t{font-size:36px;font-weight:800;line-height:1.3}.d{font-size:27px;margin-top:6px;line-height:1.4}"""
    rows = "".join(
        f'<div class="row"><div class="num">{i + 1}</div><div><div class="t">{esc(p["t"] if isinstance(p, dict) else p)}</div>'
        f'<div class="d muted">{esc(p.get("d", "") if isinstance(p, dict) else "")}</div></div></div>'
        for i, p in enumerate(s["points"][:4]))
    body = f"""{top(s, '핵심 정리', idx)}<div class="emoji">{s.get('emoji', '✅')}</div>
<h1>{esc(s['title'])}</h1><div class="list">{rows}</div>"""
    return page(s.get("theme"), body, css, s)


def compare(s, idx):
    n = len(s["headers"])
    css = f"""h1{{font-size:58px;margin:30px 0 18px}}
table{{width:100%;border-collapse:separate;border-spacing:0 12px}}
th{{font-size:30px;color:#fff;background:var(--accent);padding:16px 14px;text-align:center}}
th:first-child{{border-radius:20px 0 0 20px}}th:last-child{{border-radius:0 20px 20px 0}}
td{{font-size:{32 if n <= 2 else 28}px;padding:16px 14px;background:var(--bg);text-align:center;line-height:1.35;font-weight:500}}
td:first-child{{font-weight:800;border-radius:20px 0 0 20px}}td:last-child{{border-radius:0 20px 20px 0}}
.box{{margin-top:auto}}"""
    head = "".join(f"<th>{esc(h)}</th>" for h in s["headers"])
    rows = "".join("<tr>" + "".join(f"<td>{esc(c)}</td>" for c in r) + "</tr>" for r in s["rows"][:5])
    tip = f'<div class="box"><div class="ic">💡</div><div>{esc(s["tip"])}</div></div>' if s.get("tip") else ""
    body = f"""{top(s, '한눈에 비교', idx)}<h1>{esc(s['title'])}</h1><table><tr>{head}</tr>{rows}</table>{tip}"""
    return page(s.get("theme"), body, css, s)


def bars(s, idx):
    items = s["items"][:4]
    mx = max(float(i["value"]) for i in items) or 1
    css = """h1{font-size:58px;margin:34px 0 40px}
.b{margin-bottom:30px}.lab{display:flex;justify-content:space-between;font-size:32px;font-weight:700;margin-bottom:12px}
.track{height:52px;background:var(--bg);border-radius:18px;overflow:hidden}
.fill{height:100%;background:var(--accent);border-radius:18px}
.box{margin-top:auto}.note{font-size:24px;color:#9AA3AE;margin-top:16px}"""
    rows = "".join(
        f'<div class="b"><div class="lab"><span>{esc(i["label"])}</span><span>{esc(i.get("display", i["value"]))}</span></div>'
        f'<div class="track"><div class="fill" style="width:{max(3, float(i["value"]) / mx * 100):.1f}%"></div></div></div>'
        for i in items)
    take = f'<div class="box"><div class="ic">👉</div><div>{esc(s["takeaway"])}</div></div>' if s.get("takeaway") else ""
    note = f'<div class="note">{esc(s["note"])}</div>' if s.get("note") else ""
    body = f"""{top(s, '숫자로 보기', idx)}<h1>{esc(s['title'])}</h1>{rows}{take}{note}"""
    return page(s.get("theme"), body, css, s)


def qa(s, idx):
    css = """h1{font-size:58px;margin:34px 0 30px}
.list{display:flex;flex-direction:column;gap:18px;flex:1;justify-content:center}
.q{align-self:flex-start;background:var(--accent);color:#fff;font-size:32px;font-weight:800;padding:18px 28px;
   border-radius:30px 30px 30px 8px;line-height:1.35}
.a{align-self:flex-end;max-width:88%;background:var(--bg);font-size:29px;font-weight:500;padding:20px 28px;
   border-radius:30px 30px 8px 30px;line-height:1.45;margin-top:12px}"""
    rows = "".join(f'<div style="display:flex;flex-direction:column"><div class="q">Q. {esc(i["q"])}</div>'
                   f'<div class="a">{esc(i["a"])}</div></div>' for i in s["items"][:3])
    body = f"""{top(s, '자주 묻는 질문', idx)}<h1>{esc(s['title'])}</h1><div class="list">{rows}</div>"""
    return page(s.get("theme"), body, css, s)


def check(s, idx):
    css = """h1{font-size:60px;margin:34px 0 30px}.emoji{position:absolute;top:56px;right:72px;font-size:100px}
.list{display:flex;flex-direction:column;gap:16px}
.it{display:flex;gap:22px;align-items:center;font-size:33px;font-weight:600;padding:16px 8px;border-bottom:3px dashed var(--bg)}
.ck{flex:none;width:52px;height:52px;border-radius:16px;background:var(--accent);color:#fff;font-size:34px;font-weight:900;
    display:flex;align-items:center;justify-content:center}.box{margin-top:auto}"""
    rows = "".join(f'<div class="it"><div class="ck">✓</div><div>{esc(i)}</div></div>' for i in s["items"][:6])
    tip = f'<div class="box"><div class="ic">💡</div><div>{esc(s["tip"])}</div></div>' if s.get("tip") else ""
    body = f"""{top(s, '체크리스트', idx)}<div class="emoji">{s.get('emoji', '📝')}</div>
<h1>{esc(s['title'])}</h1><div class="list">{rows}</div>{tip}"""
    return page(s.get("theme"), body, css, s)


TEMPLATES = {"cover": cover, "points": points, "compare": compare, "bars": bars, "qa": qa, "check": check}


def render(spec, out_dir):
    out = pathlib.Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    theme = spec.get("theme", "mint")
    cards = spec["cards"]
    total = len(cards) - sum(1 for c in cards if c["type"] == "cover")
    files, n = [], 0
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1080, "height": 1080})
        for c in cards:
            c.setdefault("theme", theme)
            if spec.get("style"):
                c.setdefault("style", spec["style"])
            idx = ""
            if c["type"] != "cover":
                n += 1
                idx = f"{n}/{total}"
            pg.set_content(TEMPLATES[c["type"]](c, idx))
            pg.wait_for_timeout(150)
            f = out / f'{c["name"]}.png'
            pg.screenshot(path=str(f))
            files.append(f)
        b.close()
    return files


if __name__ == "__main__":
    for f in render(json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")), sys.argv[2]):
        print("rendered", f)
