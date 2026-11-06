"""Build data/bundle.js (the arrays the page code reads) from data/*.json."""

import nmixx_data as nd


def main():
    arrays = nd.build_legacy(*nd.load())
    (nd.DATA / "bundle.js").write_text(nd.bundle_js(arrays), encoding="utf-8")
    print("data/bundle.js: " + ", ".join(f"{k} {len(v)}" for k, v in arrays.items()))


if __name__ == "__main__":
    main()
