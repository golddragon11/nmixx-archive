# NMIXX Archive

Static site published to GitHub Pages by a GitHub Actions build.

- `index.html` — page layout, styles and app code
- `data/` — albums, playlists and videos as JSON (format: [docs/DATA_REDESIGN.md](docs/DATA_REDESIGN.md))
- `add.html` — fill-in page for adding videos or playlists; opens a ready-to-create GitHub issue
- `scripts/` — build, validation, issue-form and upstream-import tools

## 영상 추가하기 / Adding videos

코드를 직접 고칠 필요 없이 GitHub 웹사이트에서 추가할 수 있습니다. 휴대폰에서도 됩니다.
No code editing needed — everything happens on github.com, also from a phone.

1. **사이트의 `/add.html`** 을 엽니다 (추천). 재생목록 검색, 링크 입력, 옵션을 모두 그 페이지에서 하고,
   링크마다 문제가 없는지 바로 보여 줍니다. **GitHub 이슈 만들기** 를 누르면 내용이 채워진 이슈가 열리니 **Create** 만 누르세요.
   Open **`/add.html`** on the site (recommended): search the playlist, paste links and set options there; each
   link is checked as you type. **Create issue** opens a filled-in GitHub issue — just press **Create**.
   (GitHub의 **Issues → New issue → 새 영상 추가** 양식을 직접 써도 됩니다. The GitHub form works too.)
2. **재생목록**: id나 이름 일부로 검색합니다 (예: `radio star`, `shorts strange muse`).
   **Playlist**: search by id or part of the name.
3. **링크**: 한 줄에 영상 하나, `링크 | 제목 | 날짜 | 썸네일` 형식으로 출처마다 필요한 칸만 씁니다.
   **Links**: one video per line as `link | title | date | thumbnail`, writing only what each source needs.

   ```
   https://youtu.be/abc123def45
   https://www.tiktok.com/@nmixx_official/video/7704213048080207122 | 𝑵𝑬𝑶𝑵 🐶〃🐱
   https://www.tving.com/player/E004548958 | 415회 · 엔믹스 릴리 | 2026-05-02
   https://www.wavve.com/player/stream/vod?contentid=M_EP202610297364.1 | 988회 · 특집 | 2026-11-04 | https://image.wavve.com/….jpg
   ```

   | 출처 / Source | 쓰는 법 / Write | 자동 / Automatic | 넣을 수 있는 곳 / Allowed in |
   |---|---|---|---|
   | YouTube | `링크` | 제목, 날짜 (유튜브 게시일, 한국 시간), 채널 / title, date (publish date, Korea time), channel | 재생목록, 쇼츠 시리즈 / playlists, Shorts series |
   | TikTok | `링크 \| 제목` | 날짜 (영상 id에서) / date (from the id) | 쇼츠 시리즈, 시리즈 없는 틱톡 / Shorts series, TikTok without a series |
   | TVING | `링크 \| 제목 \| 날짜` | 썸네일 / thumbnail | 재생목록 / playlists |
   | Wavve, Netflix | `링크 \| 제목 \| 날짜 \| 썸네일` | — | 재생목록 / playlists |
   | FANS | `링크 \| 제목 \| 날짜 \| 썸네일` + 멤버 / member | — | 팬즈 라이브 기수 / FANS tier playlists |

   썸네일은 이미지 주소 (웨이브·팬즈는 이미지 우클릭 → '이미지 주소 복사') 나 유튜브 링크 (그 영상의 썸네일). 칸 순서가 바뀌어도 알아서 구분합니다.
   **모든 링크에 같은 날짜** 칸은 날짜가 없는 줄 모두에 그 날짜를 씁니다 (자동 날짜보다 우선). 보통은 비워 둡니다.
   A thumbnail is an image URL (on Wavve or FANS: right-click the image → "Copy image address") or a YouTube link (its thumbnail is used); parts are recognised in any order.
   **Same date for all links** applies to every line without its own date (overriding automatic dates); usually left blank.

   **멤버**: 멤버 솔로 시리즈(`tt-solo`)와 팬즈 라이브에 넣을 때만 나타나며 꼭 골라야 합니다. 여러 멤버가 나오는 영상은
   해당 유닛 시리즈(예: `tt-unit-lily-haewon`)에 넣으면 됩니다.
   **Member** only appears for the member-solo series (`tt-solo`) and FANS lives, where it is required. Videos with several
   members go into the matching unit series (e.g. `tt-unit-lily-haewon`).
   `add.html` 은 한국어와 영어로 볼 수 있습니다 (사이트와 같은 언어 설정). `add.html` is available in Korean and English.
4. 제출하면 1~2분 뒤 봇이 추가하고 결과를 댓글로 남긴 뒤 이슈를 닫습니다. 사이트에는 몇 분 안에 반영됩니다.
   After submitting, a bot adds the videos within a minute or two, comments and closes the issue; the site updates a few minutes later.
5. 문제가 있으면 봇이 이유를 댓글로 남깁니다. 이슈를 수정하면 자동으로 다시 시도합니다.
   If something is wrong the bot explains why; editing the issue retries automatically.

## 새 재생목록 만들기 / New playlists

`add.html` 의 **새 재생목록** 탭, 또는 **Issues → New issue → 새 재생목록 추가 / New playlist**: 종류 (웹예능 출연, 방송, NMIXX Original,
라이브, 투어·콘서트), 제목, 첫 영상 링크를 넣습니다. Pick a kind (web show, TV, NMIXX Original, live,
tour), a title and the first links. 앨범 활동별 재생목록 (음악방송·MV·쇼츠·MIXX 스페셜) 은 이 양식으로
만들 수 없습니다. Album-era playlists (music shows, MV, Shorts, specials) cannot be created this way.
새 팬즈 멤버십 기수는 종류 '팬즈 라이브', 제목에 기수 (예: `NSWER 5th`), 멤버를 고르면 됩니다.
A new FANS membership tier: kind "FANS live", the tier as the title (e.g. `NSWER 5th`), and a member.

저장소 주인과 협업자가 올린 이슈만 처리됩니다. Only issues from the owner and collaborators are processed.

## Development

```sh
python3 scripts/validate.py                 # check data/
python3 scripts/build.py                    # write data/bundle.js and data/add-form.js (gitignored)
python3 -m http.server                      # preview at http://localhost:8000
python3 scripts/add_video.py sync-form      # regenerate the issue forms
```

Editing by hand: add a video record to `data/videos/<year>.json` (keyed by its id) and its id
to the playlist's `videos` list in `data/playlists/<kind>/<id>.json`; a new playlist also needs
its id in `data/playlists/order.json`. Then run `validate.py`. Field reference:
[docs/DATA_REDESIGN.md](docs/DATA_REDESIGN.md).

### Workflows

| Workflow | Runs on | Does |
|---|---|---|
| `pages.yml` | push to `main`, or started by `add-video.yml` | validate, build, deploy to Pages |
| `add-video.yml` | issues from the forms | `scripts/add_video.py add`, commit, deploy, comment, close |
| `sync-form.yml` | changes to albums, members or the form script | regenerate `.github/ISSUE_TEMPLATE/` |

One-time setup on a new repo or fork: **Settings → General → Features → Issues** on,
**Settings → Pages → Source: GitHub Actions** (before the first push — a branch-based publish that is
already queued can finish after ours and replace it; re-run 사이트 배포 if that happens), and enable
workflows in the **Actions** tab.

### Syncing from upstream

The original site publishes a single generated `index.html`. To take its data:

```sh
git fetch upstream
git show upstream/main:index.html > /tmp/upstream.html
NODE_CMD=node python3 scripts/import_legacy.py --html /tmp/upstream.html   # needs Node
git diff --stat data/                                                       # review, then commit
```

The importer replaces `data/` with upstream's data (renaming era playlist ids to album names) and
refuses to write anything unless converting back reproduces upstream exactly. Changes to
upstream's page code have to be copied into `index.html` by hand.
