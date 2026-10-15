"""
posts/queue/ 에 있는 글을 Blogger에 게시하고 posts/published/ 로 옮김.
GitHub Actions에서 실행 (Claude 사용 안 함).

글 파일 형식 (posts/queue/YYYY-MM-DD-slug.html):
---
title: 글 제목
labels: 라벨1, 라벨2
---
<h2>본문 HTML ...</h2>
"""
import os
import re
import sys
import pathlib
import requests

ROOT = pathlib.Path(__file__).parent
QUEUE = ROOT / "posts" / "queue"
DONE = ROOT / "posts" / "published"

CLIENT_ID = os.environ["GOOGLE_CLIENT_ID"]
CLIENT_SECRET = os.environ["GOOGLE_CLIENT_SECRET"]
REFRESH_TOKEN = os.environ["GOOGLE_REFRESH_TOKEN"]
BLOG_ID = os.environ["BLOG_ID"]
DRAFT_MODE = (os.environ.get("DRAFT_MODE") or "false").lower() == "true"


def parse(path: pathlib.Path) -> dict:
    text = path.read_text(encoding="utf-8")
    m = re.match(r"\s*---\s*\n(.*?)\n---\s*\n(.*)", text, re.S)
    if not m:
        raise ValueError("머리말(--- title/labels ---)이 없음")
    meta = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip().lower()] = v.strip()
    if not meta.get("title"):
        raise ValueError("title 없음")
    content = m.group(2).strip()
    if len(re.sub(r"<[^>]+>", "", content)) < 1200:
        raise ValueError("본문이 너무 짧음")
    labels = [l.strip() for l in meta.get("labels", "").split(",") if l.strip()][:5]
    return {"title": meta["title"], "labels": labels, "content": content}


def access_token() -> str:
    r = requests.post(
        "https://oauth2.googleapis.com/token",
        data={"client_id": CLIENT_ID, "client_secret": CLIENT_SECRET,
              "refresh_token": REFRESH_TOKEN, "grant_type": "refresh_token"},
        timeout=60,
    )
    if r.status_code != 200:
        raise RuntimeError(f"구글 토큰 갱신 실패 {r.status_code}: {r.text[:300]}")
    return r.json()["access_token"]


def publish(post: dict, token: str) -> str:
    r = requests.post(
        f"https://www.googleapis.com/blogger/v3/blogs/{BLOG_ID}/posts",
        params={"isDraft": "true" if DRAFT_MODE else "false"},
        headers={"Authorization": f"Bearer {token}"},
        json={"kind": "blogger#post", "title": post["title"],
              "content": post["content"], "labels": post["labels"]},
        timeout=120,
    )
    if r.status_code not in (200, 201):
        raise RuntimeError(f"Blogger 게시 실패 {r.status_code}: {r.text[:300]}")
    return r.json().get("url") or "(초안으로 저장됨)"


def main() -> int:
    files = sorted(QUEUE.glob("*.html"))
    if not files:
        print("게시할 글 없음")
        return 0
    token = access_token()
    failed = 0
    for f in files:
        try:
            url = publish(parse(f), token)
            f.rename(DONE / f.name)
            print(f"[ok] {f.name} → {url}")
        except Exception as e:
            failed += 1
            print(f"[fail] {f.name}: {e}", file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
