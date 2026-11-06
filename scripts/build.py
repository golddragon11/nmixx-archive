"""Build data/bundle.js (the arrays the page code reads) and data/add-form.js (for add.html)."""

import json

import nmixx_data as nd
from add_video import form_spec


def main():
    data = nd.load()
    arrays = nd.build_legacy(*data)
    (nd.DATA / "bundle.js").write_text(nd.bundle_js(arrays), encoding="utf-8")
    spec = form_spec(data)
    (nd.DATA / "add-form.js").write_text(
        "const ADD_FORM = " + json.dumps(spec, ensure_ascii=False, separators=(",", ":")) + ";\n",
        encoding="utf-8")
    print("data/bundle.js: " + ", ".join(f"{k} {len(v)}" for k, v in arrays.items())
          + f"; data/add-form.js: {len(spec['targets'])} targets")


if __name__ == "__main__":
    main()
