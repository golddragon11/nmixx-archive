# NMIXX Archive

Static site served by GitHub Pages straight from this repo (no build step).

- `index.html` — page layout, styles and app code
- `data/` — all albums, playlists and videos

```
data/
  albums.js          ALBUMS         album names and release dates (used for eras)
  fan-lives.js       FAN_LIVES      fan-platform lives (member, thumb)
  tiktoks.js         TIKTOKS        standalone TikTok shorts (era)
  tiktok-series.js   TIKTOK_SERIES  TikTok series, each with an eps list
  playlists/<kind>.js               YouTube playlists of that kind, each with an eps list
                                    (live, tv, guest, mv, nmixxetc, original,
                                     shorts, stage, stagex, tour, univx)
```

## 영상 추가하기 (추천)

코드를 직접 고칠 필요 없이 GitHub 웹사이트에서 추가할 수 있습니다. 휴대폰에서도 됩니다.

1. 저장소의 **Issues → New issue → 새 영상 추가** 를 누릅니다.
2. **재생목록** 을 고르고 **유튜브 링크** 를 붙여 넣습니다. 여러 개면 한 줄에 하나씩.
3. 날짜, 제목, 채널은 비워 두면 자동으로 채워집니다. (날짜는 오늘, 제목·채널은 유튜브에서)
4. **Submit new issue** 를 누르면 1~2분 뒤 봇이 영상을 추가하고 이슈에 결과를 남긴 뒤 이슈를 닫습니다.
   사이트에는 몇 분 안에 반영됩니다.
5. 문제가 있으면 봇이 이유를 댓글로 남깁니다. 이슈 내용을 수정하면 자동으로 다시 시도합니다.

저장소 주인과 협업자(Collaborator)가 올린 이슈만 처리됩니다.

## Adding a video by hand

1. Open the playlist file for its kind (e.g. `data/playlists/live.js`) and find
   the playlist by searching for its `title` or `id` (e.g. `id: "monthly-haewon"`).
2. Append the video to the end of that playlist's `eps` list. Lists are kept
   oldest → newest.

```js
eps: [
  // ...existing videos
  {
    id: "CjV2LNNcWRc",   // YouTube video id (the part after watch?v=)
    title: "...",
    date: "2026-11-05",  // YYYY-MM-DD
    ch: "NMIXX",         // channel name
  },
],
```

### Optional fields

| Field | Meaning |
|---|---|
| `v: 1` | Vertical video (Shorts) |
| `m: "HAEWON"` | Member tag; drives the member chips on solo playlists (`HAEWON`, `LILY`, `SULLYOON`, `BAE`, `JIWOO`, `KYUJIN`) |
| `tt: 1` | TikTok video; `id` is the TikTok video id |
| `x: 1` | Embedding is blocked; the video opens on YouTube instead |
| `link`, `img`, `via` | Non-YouTube video: page URL, thumbnail URL, platform name (e.g. `"웨이브"`) |

## How the issue form works

- `.github/ISSUE_TEMPLATE/add-video.yml` — the form. Generated: its playlist
  list is rebuilt by `.github/workflows/sync-form.yml` whenever playlist files
  change on `main` (or run `python3 scripts/add_video.py sync-form`).
- `.github/workflows/add-video.yml` — runs `scripts/add_video.py add` on new or
  edited issues from the owner/collaborators, then commits, comments and closes.
- `scripts/add_video.py add` fetches the title and channel from YouTube's public
  oEmbed endpoint (no API key), inserts entries in date order, runs Prettier,
  and checks with Node that the data still loads and only the intended
  playlist changed.

One-time setup on a new repo/fork: **Settings → General → Features → Issues**
on, and **Actions → enable workflows**.

## Adding a playlist

Add it to `data/playlists/<kind>.js`, matching its `kind`. Copy the grouping
fields (`kind`, `era`, `member`, `unit`, `solo`) from a similar playlist.

A new kind needs a new file plus a `<script src="data/playlists/<kind>.js">`
tag in `index.html`, placed with the other playlist tags. Data scripts must
stay before the main inline script, and the inline `const PLAYLISTS = []`
must come before any playlist file.
