"""
posts/queue/ 에 있는 글을 Blogger에 게시하고 posts/published/ 로 옮김.
GitHub Actions에서 실행 (Claude 사용 안 함).

글 파일 형식 (posts/queue/YYYY-MM-DD-slug.html):
---
title: 글 제목
labels: 라벨1, 라벨2
update: true        (선택: 이미 게시된 글을 같은 제목으로 찾아 내용 교체)
---
<p>본문 HTML ...</p>

게시 후 머리말에 post_id, url 이 기록된다. post_id 가 있는 파일을 다시 queue 에 넣으면 그 글을 수정한다.
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
BLOG_ID = os.environ["BLOG_ID"].strip()
DRAFT_MODE = (os.environ.get("DRAFT_MODE") or "false").lower() == "true"
API = f"https://www.googleapis.com/blogger/v3/blogs/{BLOG_ID}/posts"


def split(text: str):
    m = re.match(r"\s*---\s*\n(.*?)\n---\s*\n(.*)", text, re.S)
    if not m:
        raise ValueError("머리말(--- title/labels ---)이 없음")
    meta = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip().lower()] = v.strip()
    return meta, m.group(2).strip()


def parse(path: pathlib.Path) -> dict:
    meta, content = split(path.read_text(encoding="utf-8"))
    if not meta.get("title"):
        raise ValueError("title 없음")
    if len(re.sub(r"<[^>]+>", "", content)) < 1200:
        raise ValueError("본문이 너무 짧음")
    labels = [l.strip() for l in meta.get("labels", "").split(",") if l.strip()][:5]
    return {"title": meta["title"].replace("[퀀트]", "").strip(), "labels": labels, "content": content,
            "post_id": meta.get("post_id"), "update": meta.get("update", "").lower() == "true"}


def access_token() -> str:
    r = requests.post(
        "https://oauth2.googleapis.com/token",
        data={"client_id": CLIENT_ID.strip(), "client_secret": CLIENT_SECRET.strip(),
              "refresh_token": REFRESH_TOKEN.strip(), "grant_type": "refresh_token"},
        timeout=60,
    )
    if r.status_code != 200:
        raise RuntimeError(f"구글 토큰 갱신 실패 {r.status_code}: {r.text[:300]}")
    return r.json()["access_token"]


def find_by_title(title: str, h: dict):
    r = requests.get(f"{API}/search", params={"q": title, "fetchBodies": "false"}, headers=h, timeout=60)
    for it in r.json().get("items", []) if r.status_code == 200 else []:
        if it.get("title", "").strip() == title:
            return it["id"]
    return None


def publish(post: dict, token: str):
    h = {"Authorization": f"Bearer {token}"}
    body = {"kind": "blogger#post", "title": post["title"], "content": post["content"], "labels": post["labels"]}
    pid = post["post_id"] or (find_by_title(post["title"], h) if post["update"] else None)
    if pid:
        r = requests.patch(f"{API}/{pid}", headers=h, json=body, timeout=120)
    else:
        r = requests.post(API, params={"isDraft": "true" if DRAFT_MODE else "false"}, headers=h, json=body, timeout=120)
    if r.status_code not in (200, 201):
        raise RuntimeError(f"Blogger {'수정' if pid else '게시'} 실패 {r.status_code}: {r.text[:300]}")
    j = r.json()
    return j.get("id"), j.get("url") or "(초안으로 저장됨)", bool(pid)


def record(path: pathlib.Path, post_id: str, url: str):
    meta, content = split(path.read_text(encoding="utf-8"))
    meta.pop("update", None)
    meta["post_id"], meta["url"] = post_id, url
    head = "\n".join(f"{k}: {v}" for k, v in meta.items())
    path.write_text(f"---\n{head}\n---\n{content}\n", encoding="utf-8")


def main() -> int:
    files = sorted(QUEUE.glob("*.html"))
    if not files:
        print("게시할 글 없음")
        return 0
    token = access_token()
    failed = 0
    for f in files:
        try:
            pid, url, updated = publish(parse(f), token)
            record(f, pid, url)
            f.rename(DONE / f.name)
            cards = f.with_name(f.name[:-5] + ".cards.json")
            if cards.exists():
                cards.rename(DONE / cards.name)
            print(f"[{'updated' if updated else 'ok'}] {f.name} → {url}")
        except Exception as e:
            failed += 1
            print(f"[fail] {f.name}: {e}", file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
