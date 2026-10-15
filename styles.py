"""
Blogger 테마는 <style> 을 무시하고 표 테두리·배경을 지워버리므로,
게시 직전에 본문 태그에 인라인 스타일을 직접 입힌다.
"""
import re

ACCENT = "#2BB58A"
ACCENT_BG = "#F1FAF6"
LINE = "#E3E8EC"

WRAP = ('<div style="overflow-x:auto;-webkit-overflow-scrolling:touch;margin:22px 0;'
        'border-radius:14px;border:1px solid ' + LINE + '">')
TABLE = ('<table style="width:100%;border-collapse:collapse;font-size:15px;line-height:1.5;'
         'min-width:480px;margin:0">')
TH = ('<th style="background:' + ACCENT + ';color:#fff;font-weight:700;padding:11px 12px;'
      'text-align:center;white-space:nowrap;border:none">')


def _td(row_i, col_i):
    bg = ACCENT_BG if row_i % 2 else "#fff"
    weight = "700" if col_i == 0 else "400"
    return (f'<td style="background:{bg};padding:11px 12px;text-align:center;font-weight:{weight};'
            f'border:none;border-top:1px solid {LINE}">')


def _style_table(m):
    t = m.group(0)
    if "data-styled" in t:
        return t
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", t, re.S)
    out, body_i = [], 0
    for r in rows:
        cells = re.findall(r"<(th|td)[^>]*>(.*?)</\1>", r, re.S)
        if cells and all(c[0] == "th" for c in cells):
            out.append("<tr>" + "".join(f"{TH}{c[1]}</th>" for c in cells) + "</tr>")
        else:
            body_i += 1
            out.append("<tr>" + "".join(f"{_td(body_i, j)}{c[1]}</td>" for j, c in enumerate(cells)) + "</tr>")
    return WRAP + TABLE.replace("<table ", '<table data-styled="" ') + "".join(out) + "</table></div>"


def style_html(html: str) -> str:
    html = re.sub(r"<table[^>]*>.*?</table>", _style_table, html, flags=re.S)
    html = re.sub(r"<h2>", f'<h2 style="border-left:6px solid {ACCENT};padding-left:12px;margin-top:40px">', html)
    return html
