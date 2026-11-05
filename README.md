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

## Adding a video

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

## Adding a playlist

Add it to `data/playlists/<kind>.js`, matching its `kind`. Copy the grouping
fields (`kind`, `era`, `member`, `unit`, `solo`) from a similar playlist.

A new kind needs a new file plus a `<script src="data/playlists/<kind>.js">`
tag in `index.html`, placed with the other playlist tags. Data scripts must
stay before the main inline script, and the inline `const PLAYLISTS = []`
must come before any playlist file.
