"""
posts/queue/*.html 중 짝이 되는 *.cards.json 이 있는 글의 카드 이미지를 그려서
images/<글이름>/ 에 저장하고, 본문의 <!--card:이름--> 자리에 이미지 태그를 넣는다.
cover 카드는 자리 표시가 없으면 본문 맨 위에 넣는다.
"""
import json
import os
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from render import render  # noqa: E402

ROOT = pathlib.Path(__file__).parent.parent
QUEUE = ROOT / "posts" / "queue"
REPO = os.environ.get("GITHUB_REPOSITORY", "kcy19981201-create/autoblog")
BRANCH = os.environ.get("GITHUB_REF_NAME", "main")


def img_tag(url, alt):
    return (f'<div style="text-align:center;margin:28px 0">'
            f'<img src="{url}" alt="{alt}" style="width:100%;max-width:640px;border-radius:18px" /></div>')


def main():
    for spec_path in sorted(QUEUE.glob("*.cards.json")):
        stem = spec_path.name[: -len(".cards.json")]
        post = QUEUE / f"{stem}.html"
        if not post.exists():
            print(f"[skip] {spec_path.name}: 짝이 되는 html 없음")
            continue
        text = post.read_text(encoding="utf-8")
        if "data-cards-built" in text:
            continue
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
        out = ROOT / "images" / stem
        render(spec, out)

        m = re.match(r"(\s*---\s*\n.*?\n---\s*\n)(.*)", text, re.S)
        head, body = m.group(1), m.group(2)
        title = re.search(r"title:\s*(.*)", head).group(1).strip()
        for c in spec["cards"]:
            url = f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/images/{stem}/{c['name']}.png"
            tag = img_tag(url, f"{title} - {c.get('tag', c['name'])}")
            ph = f"<!--card:{c['name']}-->"
            if ph in body:
                body = body.replace(ph, tag)
            elif c["type"] == "cover":
                body = tag + "\n" + body
        body = re.sub(r"<!--card:[^>]*-->", "", body)
        post.write_text(head + '<span data-cards-built=""></span>\n' + body, encoding="utf-8")
        print(f"[cards] {stem}: {len(spec['cards'])}장")


if __name__ == "__main__":
    main()
