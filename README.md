# NMIXX Archive

Static site published to GitHub Pages by a GitHub Actions build.

- `index.html` — page layout, styles and app code
- `data/` — albums, playlists and videos as JSON (format: [docs/DATA_REDESIGN.md](docs/DATA_REDESIGN.md))
- `add.html` — playlist search that opens the "add videos" form
- `scripts/` — build, validation, issue-form and upstream-import tools

## 영상 추가하기 / Adding videos

코드를 직접 고칠 필요 없이 GitHub 웹사이트에서 추가할 수 있습니다. 휴대폰에서도 됩니다.
No code editing needed — everything happens on github.com, also from a phone.

1. **사이트의 `/add.html`** 에서 재생목록을 검색해 고르거나, **Issues → New issue → 새 영상 추가** 를 누릅니다.
   Open **`/add.html`** on the site and pick a playlist, or go to **Issues → New issue → Add videos**.
2. **재생목록** 칸에 id나 이름 일부를 적습니다 (예: `radio star`, `shorts strange muse`).
   Type the playlist id or part of its name in **Playlist**.
3. **링크** 칸에 한 줄에 하나씩 붙여 넣습니다. 링크 뒤에 `|` 로 날짜·제목·썸네일을 붙일 수 있습니다.
   Paste one link per line; after a link you can add `|` date, title, thumbnail.

   ```
   https://youtu.be/abc123def45
   https://youtu.be/abc123def46 2024-05-01
   https://www.tiktok.com/@nmixx_official/video/7704213048080207122 | 2026-11-04 | 𝑵𝑬𝑶𝑵 🐶〃🐱
   https://www.wavve.com/player/stream/vod?contentid=M_EP202610297364.1 | 2026-11-04 | 988회 · 특집 | https://image.wavve.com/….jpg
   ```

   | 출처 / Source | 제목 / Title | 썸네일 / Thumbnail | 넣을 수 있는 곳 / Allowed in |
   |---|---|---|---|
   | YouTube | 자동 / automatic | 자동 / automatic | 재생목록, 쇼츠 시리즈 / playlists, Shorts series |
   | TikTok | 필요 / required | — | 쇼츠 시리즈, 시리즈 없는 틱톡 / Shorts series, TikTok without a series |
   | TVING | 필요 / required | 비우면 자동 / automatic if blank | 재생목록 / playlists |
   | Wavve, Netflix | 필요 / required | 필요 (이미지나 유튜브 링크) / required (image or YouTube link) | 재생목록 / playlists |

4. 제출하면 1~2분 뒤 봇이 추가하고 결과를 댓글로 남긴 뒤 이슈를 닫습니다. 사이트에는 몇 분 안에 반영됩니다.
   After submitting, a bot adds the videos within a minute or two, comments and closes the issue; the site updates a few minutes later.
5. 문제가 있으면 봇이 이유를 댓글로 남깁니다. 이슈를 수정하면 자동으로 다시 시도합니다.
   If something is wrong the bot explains why; editing the issue retries automatically.

## 새 재생목록 만들기 / New playlists

**Issues → New issue → 새 재생목록 추가 / New playlist**: 종류 (웹예능 출연, 방송, NMIXX Original,
라이브, 투어·콘서트), 제목, 첫 영상 링크를 넣습니다. Pick a kind (web show, TV, NMIXX Original, live,
tour), a title and the first links. 앨범 활동별 재생목록 (음악방송·MV·쇼츠·MIXX 스페셜) 은 이 양식으로
만들 수 없습니다. Album-era playlists (music shows, MV, Shorts, specials) cannot be created this way.

저장소 주인과 협업자가 올린 이슈만 처리됩니다. Only issues from the owner and collaborators are processed.

## Development

```sh
python3 scripts/validate.py                 # check data/
python3 scripts/build.py                    # write data/bundle.js and data/targets.js (gitignored)
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
**Settings → Pages → Source: GitHub Actions**, and enable workflows in the **Actions** tab.

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
