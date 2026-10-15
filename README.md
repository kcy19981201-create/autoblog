# autoblog

매일 아침 Claude(Max 예약 작업)가 `WRITING_GUIDE.md` 대로 글을 써서 `posts/queue/` 에 올리면,
GitHub Actions(`publish.yml`)가 블로그스팟에 자동 게시하고 `posts/published/` 로 옮깁니다.

- 글 주제·규칙 바꾸기: `WRITING_GUIDE.md` 수정
- 다음에 쓸 키워드 직접 넣기: `keywords.txt` 맨 위에 추가
- 초안으로만 올리기: Settings → Secrets and variables → Actions → Variables 에 `DRAFT_MODE` = `true`

## 블로그 게시 연결 (최초 1회)
1. https://www.blogger.com 에서 블로그 생성
2. https://console.cloud.google.com 에서 프로젝트 생성 → **Blogger API v3** 사용 설정
3. OAuth 동의 화면: 외부, 테스트 사용자에 본인 Gmail 추가 → **게시 상태를 "프로덕션"으로** (테스트 상태면 7일마다 토큰 만료)
4. 사용자 인증 정보 → OAuth 클라이언트 ID → **데스크톱 앱** → JSON 다운로드 → `client_secret.json` 으로 이름 변경
5. 내 PC에서 (client_secret.json 과 같은 폴더):
   ```
   pip install google-auth-oauthlib requests
   python get_token.py
   ```
6. 출력된 4개 값을 이 저장소 Settings → Secrets and variables → Actions → **Secrets** 에 등록:
   `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REFRESH_TOKEN`, `BLOG_ID`
7. Actions 탭 → publish → Run workflow 로 확인

`client_secret.json` 은 절대 저장소에 올리지 마세요 (.gitignore 에 포함됨).
