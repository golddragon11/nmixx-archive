# Data structure redesign

Status: approved 2026-11-06. Phases 1–3 in progress; phase 4 deferred.

## Why

The data mirrors the arrays an external page generator wrote into `index.html`:

- Five differently shaped lists (`ALBUMS`, `PLAYLISTS`, `FAN_LIVES`, `TIKTOKS`,
  `TIKTOK_SERIES`). The page converts fan lives and TikToks into playlists at load
  time (`index.html`, the block before `nmixx-shows-order`).
- Magic flags: `tt: 1` (TikTok), `v: 1` (vertical), `x: 1` (embedding blocked),
  `lock: 1` (members only); non-YouTube videos are recognised by `link`/`img`/`via`.
- 849 videos are stored twice (Shorts playlist + TikTok series, or TikTok series +
  standalone TikTok). Titles and dates never disagree; only list-specific flags do.
- Data lives in page code: hero slide ids (`se()`), title/description overrides
  (`he`), 12 playlist descriptions translated into 5 languages (`descs`), and
  guest→TV playlist merge rules.
- Data is JavaScript, so tools edit it as text and need Node + Prettier to check it.

## Decisions

| Question | Decision |
|---|---|
| Store each video once? | Yes — videos keyed by id, playlists list video ids |
| Publishing | Pages deploys from a GitHub Actions build; the bundle is not committed |
| Page code changes (phase 4) | Later. Phases 1–3 leave the page code untouched |
| Upstream tracking | Continues; an importer converts upstream's `index.html` |
| Video ids | Unchanged (links use them; browser storage does not) |
| Issue forms | Labels and descriptions in Korean and English |

## Format

```
data/
  albums.json                     [{ "name": "Strange Muse", "date": "2026-10-19" }, …]  newest first
  members.json                    { "HAEWON": "해원", "LILY": "릴리", …, "NMIXX": "NMIXX" }
  videos/<year>.json              { "<video id>": { video }, … }  by year of `date`
  playlists/order.json            [ "<playlist id>", … ]  page order
  playlists/<kind>/<id>.json      { playlist }
```

### Video

```json
"ufuhu3hhOtA": { "source": "youtube", "title": "…", "date": "2026-11-05",
                 "vertical": true, "members": ["SULLYOON", "JIWOO", "KYUJIN"] }
"wv-M_EP202610297364": { "source": "wavve", "title": "988회 · …", "date": "2026-11-04",
                 "url": "https://www.wavve.com/…", "thumb": "https://image.wavve.com/…" }
"7704213048080207122": { "source": "tiktok", "title": "…", "date": "2026-11-04",
                 "era": "Strange Muse" }
```

| Field | Meaning | Legacy |
|---|---|---|
| `source` | `youtube`, `tiktok`, `wavve`, `tving`, `netflix`, `fans` | `tt`, `via`, list membership |
| `title`, `date` | Required. Date is `YYYY-MM-DD` | same |
| `channel` | Channel label shown for this video; absent = the playlist's | `ch` |
| `vertical` | Vertical video | `v` (playlists only) |
| `embeddable: false` | Opens on YouTube instead of playing inline | `x` |
| `members` | Member codes from `members.json` | `m`, `member` |
| `url`, `thumb` | Watch page and thumbnail for non-YouTube sources | `link`, `img`/`thumb` |
| `era` | TikTok: also listed as a standalone Short in that era | `TIKTOKS[].era` |
| `tier` | Fan lives: membership tier (`NSWER 4th`, …) | `only` |

### Playlist

```json
{ "id": "monthly-haewon", "kind": "live", "title": "월간 5️⃣☀️1️⃣", "channel": "NMIXX",
  "desc": "…", "cover": "first", "videos": ["6BhdWyfL3Y0", "s7uxBKF84MI", …] }
```

Fields: `id`, `kind`, `title`, `channel`, `desc`, `era` (album name or `데뷔 전`),
`show` (legacy `prog`), `format` (legacy `ftype`), `cover: "first"` (legacy
`coverFirst`), `diary`, and for TikTok series (`kind: "series"`) `tag`, `members`,
`unit`, `chal`, `solo`. `videos` keeps the stored order (the page sorts by date;
stored order breaks ties). Dropped because no code reads them: `featured`, `single`.

Fan lives and standalone TikToks are videos, not playlists — the page builds their
playlists itself (by `tier`, and by `era`).

## Build

`scripts/build.py` turns `data/` into `data/bundle.js` containing the five legacy
arrays, so the page code is unchanged. Per-list rules:

| Legacy list | Built from | Video fields emitted |
|---|---|---|
| `ALBUMS` | `albums.json` | `name`, `date` |
| `PLAYLISTS` | playlists except `series`, in `order.json` order | `id title date` + `ch` + `v` + `x` + `link img via` |
| `TIKTOK_SERIES` | `series` playlists | `id title date` + `tt` (TikTok) + `m` (single member) |
| `TIKTOKS` | TikTok videos with `era`, oldest first | `id title date era` |
| `FAN_LIVES` | `fans` videos, newest first | `id title date member only thumb` |

Local preview: `python3 scripts/build.py && python3 -m http.server`.
`.github/workflows/pages.yml` builds and deploys on every push to `main`
(Settings → Pages → Source: GitHub Actions).

## Validation

`scripts/validate.py` (plain Python) runs on every push and inside the form Action:
unique ids; every playlist video exists; every video is in a playlist or is a
standalone TikTok/fan live; valid dates; known `era`, `members`, `kind`, `source`;
required fields per source (`thumb` for Wavve/Netflix, `url` for non-YouTube).

## Tools

- **Issue forms** (Korean + English): one "add video" form for every source — each
  link line may add `| date | title | thumbnail`; the playlist dropdown includes
  TikTok series and "standalone TikTok". One "new playlist" form. Edits are plain
  JSON; no Node or Prettier.
- **`scripts/import_legacy.py`**: converts legacy arrays (from upstream's
  `index.html` or the old `data/*.js`) into the new format; used for the migration
  and for upstream syncs (shows and applies differences).

## Verification

1. Round trip: `import → build` must reproduce today's five arrays exactly
   (JSON-equal, apart from the dropped `featured`/`single`).
2. Screenshot + DOM comparison of every tab, desktop and mobile, old vs new.
3. All issue-form scenarios re-run against the new format.

## Phases

1. Importer + builder; exact round trip.
2. Page loads `bundle.js`; Pages-via-Actions workflow; render check; remove old `data/*.js`.
3. Validator; issue forms and Action rewritten; upstream sync via importer.
   **Push phases 1–3 together** — the live forms edit the old files until phase 3 lands.
4. (Later) Page reads the new format directly; move hero ids, `he` overrides,
   `descs` translations and merge rules out of the minified code into data.
