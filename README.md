# 태권도장 홈페이지 템플릿

도장 하나당 **`config.js` 파일 하나만** 고치면 홈페이지가 완성됩니다.
`index.html` 은 자동으로 만들어지므로 직접 수정하지 마세요.

---

## 새 도장 세팅 순서 (약 15분)

### 1. 저장소 복사

이 저장소 오른쪽 위 **Use this template → Create a new repository** 를 누릅니다.

- 소유자(Owner): **그 도장의 GitHub 계정**
- 저장소 이름: `homepage`
- 공개 범위: **Public** (Cloudflare 연결에 필요)

> 원본 저장소는 반드시 **Private** 으로 두세요.

### 2. `config.js` 채우기

저장소에서 `config.js` 를 열고 연필 아이콘을 눌러 수정합니다.

필수로 바꿔야 하는 항목:

| 항목 | 설명 |
|---|---|
| `theme` | 색상 (아래 목록 참고) |
| `dojang` | 도장명, 주소, 전화번호, 좌표, 도메인 |
| `hours` | 운영 시간 |
| `sections` | 안 하는 서비스는 `false` |
| `faq` | **가장 중요** — 아래 설명 참고 |
| `blog.blogId` | 네이버 블로그 아이디 (없으면 `""`) |

**좌표 찾는 법** — 네이버지도에서 도장 주소 검색 → 지도 위 마우스 우클릭 → 좌표 복사

### 3. 사진 넣기

`images/` 폴더에 아래 이름으로 올립니다. 없으면 그 자리는 자동으로 비워집니다.

```
hero.jpg          첫 화면 배경   (1920x1080 권장)
master.jpg        관장 사진     (세로 3:4)
program1~6.jpg    교육과정 사진  (가로 4:3)
facility1~6.jpg   시설 사진     (가로 4:3)
og.jpg            카톡 공유 이미지 (1200x630, 300KB 이하)
```

### 4. Actions 권한 켜기

**Settings → Actions → General → Workflow permissions**
→ **Read and write permissions** 선택 → Save

이걸 안 하면 홈페이지가 자동 생성되지 않습니다.

### 5. 첫 빌드 실행

**Actions 탭 → 홈페이지 자동 갱신 → Run workflow**

1분쯤 뒤 `index.html` 이 만들어집니다.

### 6. Cloudflare Pages 연결

1. [dash.cloudflare.com](https://dash.cloudflare.com) → **Workers & Pages → Create → Pages**
2. **Connect to Git** → 방금 만든 저장소 선택
3. 빌드 설정은 **모두 비워두기** (이미 완성된 HTML 이라 빌드 불필요)
4. Deploy
5. **Custom domains** 에서 도장 도메인 연결

---

## 색상 프리셋

**진한 계열** — 신뢰감, 전통

`navy` `forest` `charcoal` `indigo` `burgundy` `teal`

**밝은 계열** — 친근함, 유치부

`sky` `sand` `mint` `lilac`

직접 지정하려면:

```js
theme: { dark:"#0A1628", accent:"#D92B3A", gold:"#E8A020", tint:"#F5F7FA" }
```

---

## FAQ 작성이 가장 중요합니다

검색 노출과 AI 답변에서 **가장 큰 효과를 내는 항목**입니다.

❌ 나쁜 예
```
Q: 수련 시간은 어떻게 되나요?
A: 상담 시 안내해 드립니다.
```

✅ 좋은 예
```
Q: 수련 시간은 어떻게 되나요?
A: 1부 2:00~2:50, 2부 3:00~3:50, 3부 4:30~5:20으로 운영합니다.
```

**숫자와 고유명사를 반드시 넣으세요.** 학부모가 검색창에 치는 말 그대로 질문을 쓰고,
답변에는 구체적인 시간·나이·지역명을 적습니다.

---

## 블로그 자동 연동

네이버 블로그에 글을 올리면 **하루 한 번 자동으로** 홈페이지 공지·갤러리에 반영됩니다.
관리자 페이지도, 별도 로그인도 필요 없습니다.

- 제목에 `공지` `안내` `모집` `심사` 등이 들어가면 → **공지사항**
- 나머지 → **갤러리** (대표 사진 자동 추출)

분류 기준은 `config.js` 의 `noticeKeywords` 에서 바꿀 수 있습니다.

**오래된 글 처리**

| 상황 | 동작 |
|---|---|
| 6개월 초과 | 날짜만 숨김 (사진·제목은 표시) |
| 24개월 초과 | 공지·갤러리 섹션 전체 숨김 |
| 블로그 미사용 | 두 섹션 자동 숨김 |

기준은 `hideDateAfterMonths`, `hideSectionAfterMonths` 로 조정합니다.

> 도장에는 **"분기에 한 번은 블로그에 사진을 올려주세요"** 라고 안내하세요.
> 홈페이지가 살아 있어 보이는지 여부가 상담 전환율을 크게 좌우합니다.

---

## 수정이 필요할 때

`config.js` 를 고치고 저장(커밋)하면 **1~2분 뒤 홈페이지에 자동 반영**됩니다.
별도 명령이나 업로드 과정이 없습니다.

---

## 내 컴퓨터에서 미리 보기 (선택)

```bash
python3 scripts/sync_blog.py    # 블로그 가져오기
python3 scripts/build.py        # 홈페이지 생성
```

필요한 것: Node.js, Python 3, `pip install Pillow`

---

## 폴더 구조

```
├── config.js              ← 여기만 수정
├── index.html             ← 자동 생성 (수정 금지)
├── sitemap.xml            ← 자동 생성
├── robots.txt             ← 자동 생성
├── images/                ← 사진
│   └── blog/              ← 블로그 사진 (자동)
└── scripts/
    ├── template.html      ← 디자인 틀
    ├── build.py           ← 홈페이지 생성기
    ├── sync_blog.py       ← 블로그 수집기
    └── blog_data.json     ← 자동 생성
```

---

## 자주 생기는 문제

**홈페이지가 안 바뀝니다**
→ Actions 탭에서 실행 결과를 확인하세요. 빨간 X 가 있으면 클릭해서 오류를 봅니다.

**Actions 가 실패합니다 (permission denied)**
→ 4번 단계(Workflow permissions)를 하지 않은 경우입니다.

**`config.js 에 문법 오류가 있습니다`**
→ 따옴표나 쉼표가 빠졌습니다. 오류 메시지에 줄 번호가 나옵니다.

**갤러리 사진이 안 나옵니다**
→ 블로그 글에 사진이 있는지, `blogId` 가 맞는지 확인하세요.
   블로그가 비공개면 RSS를 읽을 수 없습니다.
