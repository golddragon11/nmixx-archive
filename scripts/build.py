"""Build data/bundle.js (the arrays the page code reads) and data/targets.js (for add.html)."""

import json

import nmixx_data as nd
from add_video import targets


def main():
    albums, members, videos, playlists = nd.load()
    arrays = nd.build_legacy(albums, members, videos, playlists)
    (nd.DATA / "bundle.js").write_text(nd.bundle_js(arrays), encoding="utf-8")
    items = [{"id": pid, "label": label} for pid, label in targets(playlists)]
    (nd.DATA / "targets.js").write_text(
        "const TARGETS = " + json.dumps(items, ensure_ascii=False, separators=(",", ":")) + ";\n",
        encoding="utf-8")
    print("data/bundle.js: " + ", ".join(f"{k} {len(v)}" for k, v in arrays.items())
          + f"; data/targets.js: {len(items)}")


if __name__ == "__main__":
    main()
