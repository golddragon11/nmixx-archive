"""Convert the legacy data arrays into the data/ format and check the round trip.

Usage:
  python3 scripts/import_legacy.py --html path/to/upstream/index.html
  python3 scripts/import_legacy.py --js data/albums.js data/playlists/live.js ...

The result is written to data/ (replacing it); review it with `git diff data/`.
Env: NODE_CMD (default "node").
"""

import argparse
import json
import os
import re
import shlex
import subprocess
import sys

import nmixx_data as nd

KO_TO_CODE = {"해원": "HAEWON", "릴리": "LILY", "설윤": "SULLYOON", "배이": "BAE",
              "지우": "JIWOO", "규진": "KYUJIN", "NMIXX": "NMIXX"}
VIA_TO_SOURCE = {label: source for source, label in nd.SOURCE_LABELS.items()}
NAMES = ("ALBUMS", "PLAYLISTS", "FAN_LIVES", "TIKTOKS", "TIKTOK_SERIES")

# Classify the anonymous arrays of a minified page by shape.
CLASSIFY = """
const kinds = {
  ALBUMS: (a) => a.every((x) => "name" in x && "date" in x && !("id" in x)),
  PLAYLISTS: (a) => a.every((x) => "kind" in x && Array.isArray(x.eps)),
  FAN_LIVES: (a) => a.every((x) => "only" in x),
  TIKTOKS: (a) => a.every((x) => "era" in x && !("eps" in x) && "id" in x),
  TIKTOK_SERIES: (a) => a.every((x) => "tag" in x && Array.isArray(x.eps)),
};
const out = {};
for (const [name, test] of Object.entries(kinds)) {
  const hits = Object.keys(globalThis.__vars).filter((k) => {
    const v = globalThis.__vars[k];
    return Array.isArray(v) && v.length && test(v);
  });
  if (hits.length !== 1) throw new Error(name + ": found " + hits.length + " candidate arrays");
  out[name] = globalThis.__vars[hits[0]];
}
process.stdout.write(JSON.stringify(out));
"""


def run_node(js):
    node = shlex.split(os.environ.get("NODE_CMD", "node"))
    r = subprocess.run(node + ["-"], input=js, capture_output=True, text=True, encoding="utf-8")
    if r.returncode:
        sys.exit("node failed:\n" + r.stderr[-3000:])
    return json.loads(r.stdout)


def read_from_html(path):
    html = open(path, encoding="utf-8").read()
    m = re.search(r"const (\w+)=\[\{name:", html)
    end = re.search(r",\w+=\w+=>document\.querySelector\(\w+\)", html[m.start():]) if m else None
    if not m or not end:
        sys.exit("could not find the data block in " + path)
    block = html[m.start() + len("const "):m.start() + end.start()]
    js = ("const vm = require('vm'); const ctx = {}; vm.createContext(ctx);"
          f"vm.runInContext({json.dumps('var ' + block + ';')}, ctx);"
          "globalThis.__vars = ctx;" + CLASSIFY)
    return run_node(js)


def read_from_js(paths):
    body = "const PLAYLISTS = [];\n" + "\n".join(open(p, encoding="utf-8").read() for p in paths)
    return run_node(body + "\nprocess.stdout.write(JSON.stringify({" + ",".join(NAMES) + "}));")


def stable_id(playlist):
    """Upstream numbers era playlists from the newest album (shorts-era00); use the album name."""
    if "era" not in playlist:
        return playlist["id"]
    return re.sub(r"era\d+", nd.era_slug(playlist["era"]), playlist["id"])


def codes(member_string):
    return [KO_TO_CODE[n] for n in member_string.split("·")] if member_string else []


def convert(legacy):
    videos = {}

    def put(vid, fields):
        v = videos.setdefault(vid, {})
        for k, val in fields.items():
            if k in v and v[k] != val:
                raise ValueError(f"video {vid}: conflicting {k}: {v[k]!r} vs {val!r}")
            v[k] = val

    for f in legacy["FAN_LIVES"]:
        check_fields(f, {"id", "title", "date", "member", "only", "thumb"}, "fan live")
        put(f["id"], {"source": "fans", "title": f["title"], "date": f["date"],
                      "members": codes(f["member"]), "tier": f["only"], "thumb": f["thumb"]})
    for t in legacy["TIKTOKS"]:
        check_fields(t, {"id", "title", "date", "era"}, "tiktok")
        put(t["id"], {"source": "tiktok", "title": t["title"], "date": t["date"], "era": t["era"]})

    playlists = []
    for p in legacy["PLAYLISTS"]:
        check_fields(p, {"id", "kind", "title", "channel", "desc", "era", "prog", "ftype",
                         "coverFirst", "diary", "eps", *nd.DROPPED_PLAYLIST_FIELDS}, "playlist")
        q = {"id": stable_id(p), "kind": p["kind"]}
        for old, new in (("title", "title"), ("channel", "channel"), ("desc", "desc"),
                         ("era", "era"), ("prog", "show"), ("ftype", "format")):
            if old in p:
                q[new] = p[old]
        if p.get("coverFirst"):
            q["cover"] = "first"
        if p.get("diary"):
            q["diary"] = True
        for e in p["eps"]:
            check_fields(e, {"id", "title", "date", "ch", "v", "x", "link", "img", "via"}, "episode")
            source = VIA_TO_SOURCE[e["via"]] if "via" in e else "youtube"
            fields = {"source": source, "title": e["title"], "date": e["date"]}
            if "ch" in e:
                fields["channel"] = e["ch"]
            if e.get("v"):
                fields["vertical"] = True
            if e.get("x"):
                fields["embeddable"] = False
            if "link" in e:
                fields.update(url=e["link"], thumb=e["img"])
            put(e["id"], fields)
        q["videos"] = [e["id"] for e in p["eps"]]
        playlists.append(q)

    for s in legacy["TIKTOK_SERIES"]:
        check_fields(s, {"id", "tag", "title", "member", "unit", "chal", "solo", "eps"}, "series")
        q = {"id": s["id"], "kind": nd.SERIES, "tag": s["tag"], "title": s["title"],
             "members": codes(s["member"])}
        for flag in ("unit", "chal", "solo"):
            if s.get(flag):
                q[flag] = True
        for e in s["eps"]:
            check_fields(e, {"id", "title", "date", "tt", "m"}, "series episode")
            fields = {"source": "tiktok" if e.get("tt") else "youtube",
                      "title": e["title"], "date": e["date"]}
            if "m" in e:
                fields["members"] = [e["m"]]
            put(e["id"], fields)
        q["videos"] = [e["id"] for e in s["eps"]]
        playlists.append(q)

    albums = [{"name": a["name"], "date": a["date"]} for a in reversed(legacy["ALBUMS"])]  # oldest first
    ids = [p["id"] for p in playlists]
    if len(set(ids)) != len(ids):
        raise ValueError("playlist ids collide after renaming era ids")
    members = {code: ko for ko, code in KO_TO_CODE.items()}
    return albums, members, videos, playlists


def check_fields(item, allowed, what):
    extra = set(item) - allowed
    if extra:
        raise ValueError(f"{what} {item.get('id', item.get('name'))}: unknown fields {sorted(extra)}")


def comparable(legacy):
    out = json.loads(json.dumps({k: legacy[k] for k in NAMES}))
    for p in out["PLAYLISTS"]:
        p["id"] = stable_id(p)
        for f in nd.DROPPED_PLAYLIST_FIELDS:
            p.pop(f, None)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--html")
    src.add_argument("--js", nargs="+")
    args = ap.parse_args()

    legacy = read_from_html(args.html) if args.html else read_from_js(args.js)
    data = convert(legacy)
    rebuilt = nd.build_legacy(*data)
    if comparable(rebuilt) != comparable(legacy):
        for name in NAMES:
            if comparable(rebuilt)[name] != comparable(legacy)[name]:
                print(f"round trip differs in {name}", file=sys.stderr)
        sys.exit(1)
    nd.save(*data)
    albums, members, videos, playlists = data
    print(f"imported {len(albums)} albums, {len(playlists)} playlists, {len(videos)} videos; round trip exact")


if __name__ == "__main__":
    main()
