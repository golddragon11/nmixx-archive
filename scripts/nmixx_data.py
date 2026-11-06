"""Shared helpers for the data/ format described in docs/DATA_REDESIGN.md."""

import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
PLAYLIST_DIR = DATA / "playlists"
VIDEO_DIR = DATA / "videos"

SOURCE_LABELS = {"wavve": "웨이브", "tving": "티빙", "netflix": "넷플릭스"}
SERIES = "series"
FANS = "fans"
PRE_DEBUT = "데뷔 전"
DROPPED_PLAYLIST_FIELDS = ("featured", "single")


def site_text(lang):
    """Kind labels and the live-diary title from index.html's translations, e.g. site_text("en")."""
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    start = re.search(rf"^          {lang}: \{{$", html, re.M)
    if not start:
        raise ValueError(f"no '{lang}' translations in index.html")
    rest = html[start.end():]
    end = re.search(r"^          [a-z]+: \{$", rest, re.M)
    block = rest[:end.start()] if end else rest
    labels = {}
    for key, text in re.findall(r'^\s+(kind_\w+|stab_univ): "([^"]*)",?$', block, re.M):
        labels.setdefault(key, text)
    diary = re.search(r"diaryTitle: \(e\) =>\s*`(.*?)\$\{e\}`", block)
    if not diary or not labels:
        raise ValueError(f"could not read the '{lang}' labels from index.html")
    return labels, diary.group(1).strip()


def fans_id(tier):
    """Same id the page generates for a fan-live playlist: 'NSWER 4th' -> 'fans-nswer-4th'."""
    return "fans-" + re.sub(r"\W+", "-", (tier or "etc").lower())


def fans_title(tier):
    """Korean title the page shows (it translates it itself); used for search in add.html."""
    return "팬즈 라이브 · " + re.sub(r"^NSWER (\d+)(st|nd|rd|th)$", r"NSWER \1기", tier)


def era_slug(era):
    """'A Midsummer NMIXX's Dream' -> 'a-midsummer-nmixxs-dream'; '데뷔 전' -> 'pre-debut'."""
    if era == PRE_DEBUT:
        return "pre-debut"
    ascii_name = unicodedata.normalize("NFKD", era).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", ascii_name.lower().replace("'", "")).strip("-")


# ---------- reading and writing ----------

def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_video_file(path, videos):
    """One video per line keeps diffs and searches readable."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"  {json.dumps(k, ensure_ascii=False)}: {json.dumps(v, ensure_ascii=False)}"
             for k, v in videos.items()]
    path.write_text("{\n" + ",\n".join(lines) + "\n}\n", encoding="utf-8")


def playlist_path(playlist):
    return PLAYLIST_DIR / playlist["kind"] / f"{playlist['id']}.json"


def load():
    """Return (albums, members, videos, playlists) with playlists in page order."""
    videos = {}
    for path in sorted(VIDEO_DIR.glob("*.json")):
        videos.update(read_json(path))
    files = {p.stem: p for p in PLAYLIST_DIR.glob("*/*.json")}
    playlists = [read_json(files[pid]) for pid in read_json(PLAYLIST_DIR / "order.json")]
    return read_json(DATA / "albums.json"), read_json(DATA / "members.json"), videos, playlists


def save(albums, members, videos, playlists):
    """Write the whole data set, removing files that no longer belong to it."""
    write_json(DATA / "albums.json", albums)
    write_json(DATA / "members.json", members)
    by_year = {}
    for vid, v in videos.items():
        by_year.setdefault(v["date"][:4], {})[vid] = v
    for old in VIDEO_DIR.glob("*.json"):
        if old.stem not in by_year:
            old.unlink()
    for year, items in by_year.items():
        write_video_file(VIDEO_DIR / f"{year}.json", items)
    keep = {playlist_path(p) for p in playlists}
    for old in PLAYLIST_DIR.glob("*/*.json"):
        if old not in keep:
            old.unlink()
    for p in playlists:
        write_json(playlist_path(p), p)
    write_json(PLAYLIST_DIR / "order.json", [p["id"] for p in playlists])


# ---------- building the arrays the page code expects ----------

def legacy_episode(vid, v, in_series):
    ep = {"id": vid, "title": v["title"], "date": v["date"]}
    if in_series:
        if v["source"] == "tiktok":
            ep["tt"] = 1
        if len(v.get("members", [])) == 1:
            ep["m"] = v["members"][0]
        return ep
    if v["source"] not in ("youtube", *SOURCE_LABELS):
        raise ValueError(f"{vid}: {v['source']} videos cannot be in a playlist")
    if "channel" in v:
        ep["ch"] = v["channel"]
    if v.get("vertical"):
        ep["v"] = 1
    if v.get("embeddable") is False:
        ep["x"] = 1
    if v["source"] in SOURCE_LABELS:
        ep.update(link=v["url"], img=v["thumb"], via=SOURCE_LABELS[v["source"]])
    return ep


def member_names(codes, members):
    return "·".join(members[c] for c in codes)


def build_legacy(albums, members, videos, playlists):
    """Return the five arrays (ALBUMS, PLAYLISTS, FAN_LIVES, TIKTOKS, TIKTOK_SERIES)."""
    out_playlists, series, fan_lives, tiktoks = [], [], [], []
    for p in playlists:
        if p["kind"] == FANS:
            # stored oldest first like other playlists; the page's list is newest first
            fan_lives += [[vid, videos[vid], p["tier"]] for vid in reversed(p["videos"])]
            continue
        if p["kind"] == SERIES:
            s = {"id": p["id"], "tag": p["tag"], "title": p["title"],
                 "member": member_names(p.get("members", []), members)}
            for flag in ("unit", "chal", "solo"):
                if p.get(flag):
                    s[flag] = 1
            s["eps"] = [legacy_episode(i, videos[i], True) for i in p["videos"]]
            series.append(s)
            continue
        q = {"id": p["id"], "kind": p["kind"]}
        for new, old in (("cover", "coverFirst"), ("diary", "diary")):
            if p.get(new):
                q[old] = 1
        for new, old in (("title", "title"), ("channel", "channel"), ("desc", "desc"),
                         ("era", "era"), ("show", "prog"), ("format", "ftype")):
            if new in p:
                q[old] = p[new]
        # TikToks stored in a Shorts playlist are the page's standalone TikToks; it merges them back in
        tiktoks += [[i, videos[i], p["era"]] for i in p["videos"] if videos[i]["source"] == "tiktok"]
        q["eps"] = [legacy_episode(i, videos[i], False) for i in p["videos"] if videos[i]["source"] != "tiktok"]
        out_playlists.append(q)

    tiktoks = sorted(tiktoks, key=lambda x: x[1]["date"])
    fans = sorted(fan_lives, key=lambda x: x[1]["date"], reverse=True)
    return {
        "ALBUMS": [{"name": a["name"], "date": a["date"]} for a in reversed(albums)],  # page wants newest first
        "PLAYLISTS": out_playlists,
        "FAN_LIVES": [{"id": vid, "title": v["title"], "date": v["date"],
                       "member": member_names(v.get("members", []), members),
                       "only": tier, "thumb": v["thumb"]} for vid, v, tier in fans],
        "TIKTOKS": [{"id": vid, "title": v["title"], "date": v["date"], "era": era}
                    for vid, v, era in tiktoks],
        "TIKTOK_SERIES": series,
    }


def bundle_js(arrays):
    dump = lambda x: json.dumps(x, ensure_ascii=False, separators=(",", ":"))
    return "".join(f"const {name} = {dump(value)};\n" for name, value in arrays.items())
