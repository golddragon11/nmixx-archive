"""Shared helpers for the data/ format described in docs/DATA_REDESIGN.md."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
PLAYLIST_DIR = DATA / "playlists"
VIDEO_DIR = DATA / "videos"

SOURCE_LABELS = {"wavve": "웨이브", "tving": "티빙", "netflix": "넷플릭스"}
SERIES = "series"
PRE_DEBUT = "데뷔 전"
DROPPED_PLAYLIST_FIELDS = ("featured", "single")


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
    out_playlists, series = [], []
    for p in playlists:
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
        q["eps"] = [legacy_episode(i, videos[i], False) for i in p["videos"]]
        out_playlists.append(q)

    tiktoks = sorted(([vid, v] for vid, v in videos.items() if v["source"] == "tiktok" and "era" in v),
                     key=lambda x: x[1]["date"])
    fans = sorted(([vid, v] for vid, v in videos.items() if v["source"] == "fans"),
                  key=lambda x: x[1]["date"], reverse=True)
    return {
        "ALBUMS": [{"name": a["name"], "date": a["date"]} for a in albums],
        "PLAYLISTS": out_playlists,
        "FAN_LIVES": [{"id": vid, "title": v["title"], "date": v["date"],
                       "member": member_names(v.get("members", []), members),
                       "only": v["tier"], "thumb": v["thumb"]} for vid, v in fans],
        "TIKTOKS": [{"id": vid, "title": v["title"], "date": v["date"], "era": v["era"]}
                    for vid, v in tiktoks],
        "TIKTOK_SERIES": series,
    }


def bundle_js(arrays):
    dump = lambda x: json.dumps(x, ensure_ascii=False, separators=(",", ":"))
    return "".join(f"const {name} = {dump(value)};\n" for name, value in arrays.items())
