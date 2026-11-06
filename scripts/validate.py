"""Check data/ for consistency. Exit code 1 and a list of problems if anything is wrong."""

import datetime
import json
import sys

import nmixx_data as nd

SOURCES = {"youtube", "tiktok", "fans", *nd.SOURCE_LABELS}
PLAYLIST_KINDS = {"live", "tv", "guest", "mv", "nmixxetc", "original", "shorts",
                  "stage", "stagex", "tour", "univx", nd.SERIES}
SERIES_SOURCES = {"youtube", "tiktok"}
PLAYLIST_SOURCES = {"youtube", *nd.SOURCE_LABELS}


def valid_date(s):
    try:
        return datetime.date.fromisoformat(s).isoformat() == s
    except (TypeError, ValueError):
        return False


def validate(albums, members, videos, playlists, check_files=True):
    """check_files=False skips the on-disk file checks (for data not saved yet)."""
    errors = []
    err = errors.append

    names = [a["name"] for a in albums]
    eras = set(names) | {nd.PRE_DEBUT}
    dates = [a["date"] for a in albums]
    if dates != sorted(dates):
        err("albums.json must be oldest first")
    for a in albums:
        if not valid_date(a.get("date")):
            err(f"album {a.get('name')}: bad date {a.get('date')!r}")

    ids = [p["id"] for p in playlists]
    if len(set(ids)) != len(ids):
        err("order.json lists a playlist twice")
    if check_files:
        for missing in sorted({p.stem for p in nd.PLAYLIST_DIR.glob("*/*.json")} - set(ids)):
            err(f"playlist file {missing} is not in order.json")

    used = set()
    for p in playlists:
        where = f"playlist {p['id']}"
        if p.get("kind") not in PLAYLIST_KINDS:
            err(f"{where}: unknown kind {p.get('kind')!r}")
        if check_files and not nd.playlist_path(p).exists():
            err(f"{where}: file must be data/playlists/{p.get('kind')}/{p['id']}.json")
        if not p.get("title"):
            err(f"{where}: missing title")
        if "era" in p and p["era"] not in eras:
            err(f"{where}: unknown era {p['era']!r}")
        for code in p.get("members", []):
            if code not in members:
                err(f"{where}: unknown member {code!r}")
        if not p.get("videos"):
            err(f"{where}: has no videos")
        if len(set(p.get("videos", []))) != len(p.get("videos", [])):
            err(f"{where}: lists a video twice")
        allowed = SERIES_SOURCES if p.get("kind") == nd.SERIES else PLAYLIST_SOURCES
        for vid in p.get("videos", []):
            used.add(vid)
            if vid not in videos:
                err(f"{where}: video {vid} does not exist")
            elif videos[vid].get("source") not in allowed:
                err(f"{where}: {videos[vid].get('source')} video {vid} cannot be in this playlist")

    for vid, v in videos.items():
        where = f"video {vid}"
        source = v.get("source")
        if source not in SOURCES:
            err(f"{where}: unknown source {source!r}")
            continue
        if not v.get("title"):
            err(f"{where}: missing title")
        if not valid_date(v.get("date")):
            err(f"{where}: bad date {v.get('date')!r}")
        for code in v.get("members", []):
            if code not in members:
                err(f"{where}: unknown member {code!r}")
        if source in nd.SOURCE_LABELS and not (v.get("url") and v.get("thumb")):
            err(f"{where}: {source} videos need url and thumb")
        if source == "fans" and not (v.get("tier") and v.get("thumb")):
            err(f"{where}: fan lives need tier and thumb")
        if "era" in v and (source != "tiktok" or v["era"] not in eras):
            err(f"{where}: era {v['era']!r} is only allowed on TikToks and must be a known album")
        standalone = source == "fans" or (source == "tiktok" and "era" in v)
        if vid not in used and not standalone:
            err(f"{where}: not in any playlist")

    if not errors:
        try:
            nd.build_legacy(albums, members, videos, playlists)
        except (KeyError, ValueError) as e:
            err(f"build failed: {e!r}")
    return errors


def main():
    try:
        data = nd.load()
    except (OSError, KeyError, json.JSONDecodeError) as e:
        sys.exit(f"could not load data/: {e!r}")
    errors = validate(*data)
    for e in errors:
        print(e)
    if errors:
        sys.exit(1)
    albums, _, videos, playlists = data
    print(f"data/ ok: {len(albums)} albums, {len(playlists)} playlists, {len(videos)} videos")


if __name__ == "__main__":
    main()
