"""
최초 1회만 내 PC에서 실행: 구글 로그인 → refresh token 과 블로그 ID 출력
사용법:
    pip install google-auth-oauthlib requests
    python get_token.py        (같은 폴더에 client_secret.json 필요)
"""
import json
import requests
from google_auth_oauthlib.flow import InstalledAppFlow

flow = InstalledAppFlow.from_client_secrets_file(
    "client_secret.json", scopes=["https://www.googleapis.com/auth/blogger"]
)
creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")

with open("client_secret.json", encoding="utf-8") as f:
    info = json.load(f)
    info = info.get("installed") or info.get("web")

blogs = requests.get(
    "https://www.googleapis.com/blogger/v3/users/self/blogs",
    headers={"Authorization": f"Bearer {creds.token}"},
    timeout=60,
).json().get("items", [])

print("\n===== GitHub Secrets 에 아래 값을 등록하세요 =====")
print("GOOGLE_CLIENT_ID     =", info["client_id"])
print("GOOGLE_CLIENT_SECRET =", info["client_secret"])
print("GOOGLE_REFRESH_TOKEN =", creds.refresh_token)
print("\n블로그 목록 (쓸 블로그의 id 를 BLOG_ID 로 등록):")
for b in blogs:
    print(f"  BLOG_ID = {b['id']}   ({b['name']} - {b['url']})")
if not blogs:
    print("  블로그가 없습니다. blogger.com 에서 먼저 블로그를 만드세요.")
