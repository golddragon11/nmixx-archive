"""Add videos or new playlists from GitHub issue forms, or regenerate those forms.

Usage:
  ISSUE_BODY=... python3 scripts/add_video.py add
  python3 scripts/add_video.py sync-form

Each line of the links field is `link | extra | extra | ...`; extras are recognised
by shape: a date, an image or YouTube link (thumbnail), or anything else (title).
See docs/DATA_REDESIGN.md for the data format.
"""

import datetime
import hashlib
import html
import json
import os
import re
import subprocess
import sys
import unicodedata
import urllib.parse
import urllib.request
import uuid

import nmixx_data as nd
from validate import validate

KST = datetime.timezone(datetime.timedelta(hours=9))
TEMPLATES = nd.ROOT / ".github" / "ISSUE_TEMPLATE"
UA = {"User-Agent": "Mozilla/5.0 (compatible; nmixx-archive)"}

KIND_LABELS = {
    "live": ("라이브", "Live"), "tv": ("방송", "TV"), "guest": ("웹예능 출연", "Web show"),
    "mv": ("MV·퍼포먼스", "MV"), "nmixxetc": ("MIXX 스페셜", "Special"),
    "original": ("NMIXX Original", "Original"), "shorts": ("쇼츠", "Shorts"),
    "stage": ("음악방송", "Music show"), "stagex": ("무대 비하인드", "Stage behind"),
    "tour": ("투어·콘서트", "Tour"), "univx": ("대학 축제 비하인드", "Festival behind"),
    nd.SERIES: ("쇼츠 시리즈", "Shorts series"),
}
STANDALONE = "tiktok-standalone"
NEW_PLAYLIST_KINDS = {  # kind -> (id prefix, default channel; None = first video's)
    "guest": ("g", None), "tv": ("tv", None), "original": ("orig", "NMIXX"),
    "live": ("live", "NMIXX"), "tour": ("tour", "NMIXX"),
}
IMPLIED_CHANNEL = {"shorts": "NMIXX", "mv": "NMIXX", "nmixxetc": "NMIXX"}
SOURCE_NAMES = {"youtube": "YouTube", "tiktok": "TikTok", "wavve": "Wavve", "tving": "TVING",
                "netflix": "Netflix"}
NO_RESPONSE = ("_No response_", "None")


def bi(ko, en):
    return f"{ko} / {en}"


F_TARGET = bi("재생목록", "Playlist")
F_LINKS = bi("링크", "Links")
F_DATE = bi("날짜 (선택)", "Date (optional)")
F_TITLE = bi("제목 (선택)", "Title (optional)")
F_CHANNEL = bi("채널 (선택)", "Channel (optional)")
F_MEMBER = bi("멤버 (선택)", "Member (optional)")
F_ERA = bi("활동 시기 (선택)", "Era (optional)")
F_OPTIONS = bi("옵션", "Options")
F_KIND = bi("종류", "Kind")
F_NEW_TITLE = bi("제목", "Title")
F_DESC = bi("설명 (선택)", "Description (optional)")
VERTICAL = bi("세로 영상 (쇼츠)", "Vertical video (Shorts)")
NONE_OPTION = bi("없음", "None")
AUTO_OPTION = bi("자동 (날짜 기준)", "Automatic (by date)")

YOUTUBE_ID = re.compile(
    r"(?:youtu\.be/|[?&]v=|/shorts/|/live/|/embed/)([A-Za-z0-9_-]{11})(?![A-Za-z0-9_-])")
TIKTOK_ID = re.compile(r"tiktok\.com/.*?/video/(\d+)")
WAVVE_ID = re.compile(r"wavve\.com/.*?contentid=([A-Za-z0-9_.]+)")
TVING_ID = re.compile(r"tving\.com/(?:player|contents)/(E\d+)")
NETFLIX_ID = re.compile(r"netflix\.com/(?:[a-z]{2}(?:-[a-z]{2})?/)?(title|watch)/(\d+)")
DATE = re.compile(r"(\d{4})\s*[-./]\s*(\d{1,2})\s*[-./]\s*(\d{1,2})\.?")


class InputError(Exception):
    def __init__(self, ko, en):
        super().__init__(f"{ko}\n{en}")


# ---------- forms ----------

def option_label(p):
    ko, en = KIND_LABELS.get(p["kind"], (p["kind"], p["kind"]))
    era = f" · {p['era']}" if p.get("era") else ""
    return f"[{ko} · {en}] {p['title']}{era} ({p['id']})"


def targets(playlists):
    """Everything a video can be added to: [(id, label)]."""
    return [(p["id"], option_label(p)) for p in playlists] + [(STANDALONE, standalone_label())]


def normalize(text):
    return re.sub(r"[\s\W_]+", "", unicodedata.normalize("NFKC", text).lower())


def find_target(query, playlists):
    """Resolve the playlist field: a full label, an id, or words from the title/era."""
    query = query.strip()
    if m := re.search(r"\(([^()]+)\)\s*$", query):
        query = m.group(1)
    options = targets(playlists)
    exact = [t for t in options if t[0].lower() == query.lower()]
    if exact:
        return exact[0][0]
    words = [normalize(w) for w in query.split() if normalize(w)]
    hits = [t for t in options if words and all(w in normalize(t[1]) for w in words)]
    if len(hits) == 1:
        return hits[0][0]
    if not hits:
        raise InputError(f"재생목록을 찾을 수 없습니다: `{query}` — 검색 페이지에서 찾아 보세요.",
                         f"No playlist matches `{query}` — try the search page.")
    shown = "\n".join(f"- `{pid}` — {label}" for pid, label in hits[:15])
    more = f"\n- … {len(hits) - 15}개 더 / {len(hits) - 15} more" if len(hits) > 15 else ""
    raise InputError(f"`{query}` 에 맞는 재생목록이 {len(hits)}개입니다. 재생목록 칸에 아래 id 중 하나를 넣어 주세요:",
                     f"{len(hits)} playlists match `{query}`. Put one of these ids in the playlist field:\n{shown}{more}")


def search_page_url():
    repo = os.environ.get("GITHUB_REPOSITORY")
    if not repo:
        try:
            url = subprocess.run(["git", "remote", "get-url", "origin"], cwd=nd.ROOT,
                                 capture_output=True, text=True).stdout.strip()
            repo = re.search(r"github\.com[:/](.+?)(?:\.git)?$", url).group(1)
        except (OSError, AttributeError):
            return ""
    owner, name = repo.split("/", 1)
    return f"https://{owner.lower()}.github.io/{name}/add.html"


def standalone_label():
    return f"[틱톡 · TikTok] 시리즈 없는 틱톡 · TikTok without a series ({STANDALONE})"


def field(ftype, fid, label, ko=None, en=None, required=False, options=None, placeholder=None,
          default=None):
    q = lambda s: json.dumps(s, ensure_ascii=False)
    out = [f"  - type: {ftype}", f"    id: {fid}", "    attributes:", f"      label: {q(label)}"]
    if ko:
        out.append(f"      description: {q(ko + '  ' + chr(10) + en)}")
    if placeholder:
        out.append(f"      placeholder: {q(placeholder)}")
    if options is not None:
        out.append("      options:")
        out += [f"        - {q(o)}" for o in options]
    if default is not None:
        out.append(f"      default: {default}")
    if required:
        out += ["    validations:", "      required: true"]
    return out


def header(name, about, title, intro_ko, intro_en):
    q = lambda s: json.dumps(s, ensure_ascii=False)
    return ["# Generated by scripts/add_video.py sync-form — edit the script, not this file.",
            f"name: {q(name)}", f"description: {q(about)}", f"title: {q(title)}", "body:",
            "  - type: markdown", "    attributes:",
            f"      value: {q(intro_ko + chr(10) + chr(10) + intro_en)}"]


LINKS_KO = ("한 줄에 영상 하나. 링크 뒤에 `|` 로 날짜·제목·썸네일을 붙일 수 있습니다. "
            "유튜브는 제목이 자동이고, 틱톡·웨이브·티빙·넷플릭스는 제목이 필요합니다. "
            "웨이브·넷플릭스는 썸네일(이미지 주소나 유튜브 링크)도 필요합니다.")
LINKS_EN = ("One video per line. After the link you can add `|` date, title, thumbnail. "
            "YouTube titles are automatic; TikTok, Wavve, TVING and Netflix need a title. "
            "Wavve and Netflix also need a thumbnail (an image URL or a YouTube link).")
LINKS_EXAMPLE = ("https://youtu.be/abc123def45\n"
                 "https://www.wavve.com/player/vod?contentid=… | 2026-11-04 | 988회 · 특집 | https://image.wavve.com/….jpg")


def sync_form(data=None):
    albums, members, videos, playlists = data or nd.load()
    search = search_page_url()
    search_ko = f" 목록에서 찾기: {search}" if search else ""
    search_en = f" Search the list: {search}" if search else ""
    member_opts = [NONE_OPTION] + [f"{ko} ({code})" for code, ko in members.items() if code != "NMIXX"]
    era_opts = [AUTO_OPTION] + [a["name"] for a in reversed(albums)] + [nd.PRE_DEBUT]

    video = header(
        "새 영상 추가 / Add videos",
        "재생목록에 영상을 추가합니다 / Add videos to a playlist (YouTube, TikTok, Wavve, TVING, Netflix)",
        "[새 영상] ",
        "재생목록을 고르고 링크를 붙여 넣은 뒤 제출하세요. 제출하면 자동으로 사이트에 반영됩니다.",
        "Pick a playlist, paste the links and submit. The site updates automatically.")
    video += field("input", "playlist", F_TARGET,
                   "재생목록 id나 이름 일부를 입력하세요 (예: 월간, radio star, shorts strange muse)." + search_ko,
                   "Type the playlist id or part of its name (e.g. 월간, radio star, shorts strange muse)." + search_en,
                   required=True)
    video += field("textarea", "links", F_LINKS, LINKS_KO, LINKS_EN, required=True, placeholder=LINKS_EXAMPLE)
    video += field("input", "date", F_DATE, "링크 뒤에 날짜가 없는 영상에 쓰입니다. 비워 두면 오늘(한국 시간). 예: 2026-11-05",
                   "Used for links without their own date. Blank = today (Korea time). e.g. 2026-11-05")
    video += field("input", "title", F_TITLE, "영상이 1개일 때만 적용됩니다.", "Only used when there is one video.")
    video += field("input", "channel", F_CHANNEL, "비워 두면 유튜브 채널 이름을 씁니다.", "Blank = the YouTube channel name.")
    video += field("dropdown", "member", F_MEMBER, "멤버 솔로 영상이면 선택하세요. 모든 링크에 적용됩니다.",
                   "Pick a member for solo videos. Applies to every link.", options=member_opts, default=0)
    video += field("dropdown", "era", F_ERA, "시리즈 없는 틱톡에만 쓰입니다. 발매 전 티저는 다음 앨범을 고르세요.",
                   "Only for TikToks without a series. For pre-release teasers pick the upcoming album.",
                   options=era_opts, default=0)
    video += ["  - type: checkboxes", "    id: options", "    attributes:",
              f"      label: {json.dumps(F_OPTIONS, ensure_ascii=False)}", "      options:",
              f"        - label: {json.dumps(VERTICAL, ensure_ascii=False)}"]

    kinds = [f"{KIND_LABELS[k][0]} · {KIND_LABELS[k][1]} ({k})" for k in NEW_PLAYLIST_KINDS]
    playlist = header(
        "새 재생목록 추가 / New playlist",
        "새 재생목록을 만들고 영상을 넣습니다 / Create a playlist with its first videos",
        "[새 재생목록] ",
        "이미 있는 재생목록에 넣을 때는 '새 영상 추가'를 쓰세요. 영상이 1개 이상 있어야 사이트에 보입니다.",
        "To add to an existing playlist use 'Add videos'. A playlist needs at least one video to show.")
    playlist += field("dropdown", "kind", F_KIND, required=True, options=kinds)
    playlist += field("input", "title", F_NEW_TITLE, "사이트에 보일 재생목록 이름", "Playlist name shown on the site",
                      required=True)
    playlist += field("input", "channel", F_CHANNEL,
                      "비워 두면 라이브·NMIXX Original·투어는 NMIXX, 웹예능·방송은 첫 영상의 유튜브 채널.",
                      "Blank = NMIXX for live, original and tour; the first video's YouTube channel otherwise.")
    playlist += field("textarea", "desc", F_DESC, "재생목록 소개 문구", "Short description of the playlist")
    playlist += field("textarea", "links", F_LINKS, LINKS_KO, LINKS_EN, required=True, placeholder=LINKS_EXAMPLE)
    playlist += field("input", "date", F_DATE, "링크 뒤에 날짜가 없는 영상에 쓰입니다. 비워 두면 오늘(한국 시간).",
                      "Used for links without their own date. Blank = today (Korea time).")

    TEMPLATES.mkdir(parents=True, exist_ok=True)
    (TEMPLATES / "add-video.yml").write_text("\n".join(video) + "\n", encoding="utf-8")
    (TEMPLATES / "add-playlist.yml").write_text("\n".join(playlist) + "\n", encoding="utf-8")
    print("issue forms written")


# ---------- parsing ----------

def parse_issue(body):
    sections, cur = {}, None
    for line in body.replace("\r\n", "\n").split("\n"):
        m = re.match(r"^### (.+?)\s*$", line)
        if m:
            cur = m.group(1)
            sections[cur] = []
        elif cur:
            sections[cur].append(line)
    out = {}
    for k, v in sections.items():
        text = "\n".join(v).strip()
        out[k] = "" if text in NO_RESPONSE else text
    return out


def parse_date(text):
    m = DATE.fullmatch(text.strip())
    if not m:
        raise InputError(f"날짜 형식을 알 수 없습니다: `{text}` (예: 2026-11-05)",
                         f"Unrecognised date: `{text}` (e.g. 2026-11-05)")
    try:
        return datetime.date(*map(int, m.groups())).isoformat()
    except ValueError:
        raise InputError(f"존재하지 않는 날짜입니다: `{text}`", f"That date does not exist: `{text}`")


def today():
    return datetime.datetime.now(KST).date().isoformat()


def identify(url):
    """Return (source, video id, canonical url) for a supported link."""
    if m := YOUTUBE_ID.search(url):
        return "youtube", m.group(1), None
    if re.match(r"^[A-Za-z0-9_-]{11}$", url):
        return "youtube", url, None
    if "vt.tiktok.com" in url or "vm.tiktok.com" in url:
        url = resolve_redirect(url)
    if m := TIKTOK_ID.search(url):
        return "tiktok", m.group(1), None
    if m := WAVVE_ID.search(url):
        cid = m.group(1)
        return "wavve", "wv-" + re.sub(r"\.\d+$", "", cid), \
            f"https://www.wavve.com/player/stream/vod?contentid={cid}"
    if m := TVING_ID.search(url):
        return "tving", "tv-" + m.group(1), f"https://www.tving.com/player/{m.group(1)}"
    if m := NETFLIX_ID.search(url):
        return "netflix", "nf-" + m.group(2), f"https://www.netflix.com/{m.group(1)}/{m.group(2)}"
    raise InputError(f"지원하지 않는 링크입니다: `{url}` (유튜브·틱톡·웨이브·티빙·넷플릭스만 가능)",
                     f"Unsupported link: `{url}` (YouTube, TikTok, Wavve, TVING and Netflix only)")


def parse_links(text, fallback_date):
    """Return [{source, id, url, date, title, thumb, short}] in the order given."""
    out = []
    for line in filter(None, (l.strip() for l in text.split("\n"))):
        parts = [p.strip() for p in line.split("|")]
        head = parts[0].split()
        link, extras = head[0], [" ".join(head[1:])] + parts[1:]
        source, vid, url = identify(link)
        item = {"source": source, "id": vid, "url": url, "date": fallback_date, "title": "",
                "thumb": "", "short": "/shorts/" in link}
        for extra in filter(None, extras):
            if DATE.fullmatch(extra):
                item["date"] = parse_date(extra)
            elif re.match(r"^https?://", extra):
                yt = YOUTUBE_ID.search(extra)
                item["thumb"] = f"https://i.ytimg.com/vi/{yt.group(1)}/mqdefault.jpg" if yt else extra
            else:
                item["title"] = extra
        out.append(item)
    if not out:
        raise InputError("링크를 1개 이상 넣어 주세요.", "Please add at least one link.")
    ids = [i["id"] for i in out]
    if len(set(ids)) != len(ids):
        raise InputError("같은 영상이 두 번 들어 있습니다.", "The same video is listed twice.")
    return out


# ---------- fetching ----------

def fetch(url, timeout=20):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def resolve_redirect(url):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20) as r:
            return r.geturl()
    except Exception:
        return url


def youtube_info(vid):
    url = "https://www.youtube.com/oembed?format=json&url=" + urllib.parse.quote(
        f"https://www.youtube.com/watch?v={vid}", safe="")
    try:
        d = json.loads(fetch(url))
        return d.get("title", ""), d.get("author_name", "")
    except Exception as e:
        raise InputError(f"유튜브에서 영상 정보를 가져오지 못했습니다: `{vid}` ({e}). 비공개·삭제된 영상인지 확인해 주세요.",
                         f"Could not read video info from YouTube: `{vid}` ({e}). Is it private or deleted?")


def tving_thumb(episode):
    try:
        page = fetch(f"https://www.tving.com/contents/{episode}")
    except Exception:
        return ""
    m = re.search(r'"episode_image":\[\{"url":"([^"]+)"', page)
    return "https://image.tving.com" + html.unescape(m.group(1)).replace("\\u002F", "/") if m else ""


# ---------- building records ----------

def era_for(date, albums):
    for a in reversed(albums):
        if a["date"] <= date:
            return a["name"]
    return nd.PRE_DEBUT


def new_video(item, *, title_override, channel_override, playlist_channel, member, vertical):
    source = item["source"]
    v = {"source": source, "title": item["title"] or title_override, "date": item["date"]}
    name = SOURCE_NAMES[source]
    if source == "youtube":
        yt_title, yt_channel = youtube_info(item["id"])
        v["title"] = v["title"] or yt_title
        ch = channel_override or yt_channel
        if ch and ch != playlist_channel:
            v["channel"] = ch
    elif not v["title"]:
        raise InputError(f"{name} 영상은 제목이 필요합니다: `{item['id']}` (링크 뒤에 `| 제목` 을 붙여 주세요)",
                         f"{name} videos need a title: `{item['id']}` (add `| title` after the link)")
    if source in nd.SOURCE_LABELS:
        v["url"] = item["url"]
        thumb = item["thumb"] or (tving_thumb(item["id"][3:]) if source == "tving" else "")
        if not thumb:
            raise InputError(f"{name} 영상은 썸네일이 필요합니다: `{item['id']}` (이미지 주소나 유튜브 링크를 `|` 뒤에)",
                             f"{name} videos need a thumbnail: `{item['id']}` (an image URL or YouTube link after `|`)")
        v["thumb"] = thumb
        if channel_override:
            v["channel"] = channel_override
    if vertical or item["short"]:
        v["vertical"] = True
    if member:
        v["members"] = [member]
    return v


def insert_by_date(ids, vid, date, videos):
    pos = max((n + 1 for n, i in enumerate(ids) if videos[i]["date"] <= date), default=0)
    ids.insert(pos, vid)


# ---------- commands ----------

def add_videos(form, data):
    albums, members, videos, playlists = data
    if not form.get(F_TARGET, "").strip():
        raise InputError("재생목록을 입력해 주세요.", "Please enter a playlist.")
    target = find_target(form[F_TARGET], playlists)
    playlist = next((p for p in playlists if p["id"] == target), None)

    items = parse_links(form.get(F_LINKS, ""), parse_date(form[F_DATE]) if form.get(F_DATE) else today())
    title_override = form.get(F_TITLE, "")
    if title_override and len(items) > 1:
        raise InputError("영상이 여러 개일 때는 제목 칸을 비우고 링크 뒤에 `| 제목` 을 쓰세요.",
                         "With several videos leave the title field blank and add `| title` after each link.")
    member_m = re.search(r"\(([A-Z]+)\)", form.get(F_MEMBER, ""))
    member = member_m.group(1) if member_m else None
    vertical = f"- [x] {VERTICAL}".lower() in form.get(F_OPTIONS, "").lower()
    era_choice = form.get(F_ERA, "")

    kind = playlist["kind"] if playlist else STANDALONE
    allowed = {nd.SERIES: {"youtube", "tiktok"}, STANDALONE: {"tiktok"}}.get(kind, {"youtube", *nd.SOURCE_LABELS})
    channel = (playlist or {}).get("channel") or IMPLIED_CHANNEL.get(kind, "")
    added = []
    for item in items:
        if item["source"] not in allowed:
            raise InputError(
                f"{SOURCE_NAMES[item['source']]} 영상은 이 재생목록에 넣을 수 없습니다: `{item['id']}`",
                f"{SOURCE_NAMES[item['source']]} videos cannot go into this playlist: `{item['id']}`")
        vid = item["id"]
        if kind == STANDALONE:
            if "era" in videos.get(vid, {}):
                raise InputError(f"이미 등록된 틱톡입니다: `{vid}`", f"This TikTok is already listed: `{vid}`")
        elif vid in playlist["videos"]:
            raise InputError(f"이미 이 재생목록에 있는 영상입니다: `{vid}`", f"Already in this playlist: `{vid}`")
        if vid not in videos:
            videos[vid] = new_video(item, title_override=title_override,
                                    channel_override=form.get(F_CHANNEL, ""), playlist_channel=channel,
                                    member=member, vertical=vertical)
        if kind == STANDALONE:
            era = era_choice if era_choice and era_choice != AUTO_OPTION else era_for(videos[vid]["date"], albums)
            videos[vid]["era"] = era
        else:
            insert_by_date(playlist["videos"], vid, videos[vid]["date"], videos)
        added.append(vid)

    where = standalone_label() if kind == STANDALONE else option_label(playlist)
    summary = [f"✅ **{where}** 에 {len(added)}개 추가했습니다. / Added {len(added)}.", ""]
    summary += [video_line(vid, videos[vid]) for vid in added]
    return f"새 영상 {len(added)}개 추가 ({today()})", "\n".join(summary)


def make_playlist_id(prefix, title, first_video, taken):
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:40].strip("-")
    digest = hashlib.sha1(f"{prefix}|{title}|{first_video}".encode()).hexdigest()[:6]
    pid = f"{prefix}-{slug}-{digest}" if slug else f"{prefix}-{digest}"
    if pid in taken:
        raise InputError(f"재생목록 id가 겹칩니다: `{pid}`. 제목을 조금 바꿔 주세요.",
                         f"Playlist id already exists: `{pid}`. Please change the title slightly.")
    return pid


def add_playlist(form, data):
    albums, members, videos, playlists = data
    m = re.search(r"\(([a-z]+)\)\s*$", form.get(F_KIND, ""))
    if not m or m.group(1) not in NEW_PLAYLIST_KINDS:
        raise InputError("재생목록 종류를 선택해 주세요.", "Please choose a playlist kind.")
    kind = m.group(1)
    prefix, default_channel = NEW_PLAYLIST_KINDS[kind]
    title = form.get(F_NEW_TITLE, "").strip()
    if not title:
        raise InputError("재생목록 제목을 입력해 주세요.", "Please enter a playlist title.")
    same = next((p for p in playlists if p["kind"] == kind and p["title"] == title), None)
    if same:
        raise InputError(f"같은 이름의 재생목록이 이미 있습니다: `{same['id']}`. 영상을 넣으려면 '새 영상 추가'를 쓰세요.",
                         f"A playlist with this name exists: `{same['id']}`. Use 'Add videos' to add to it.")
    items = parse_links(form.get(F_LINKS, ""), parse_date(form[F_DATE]) if form.get(F_DATE) else today())
    for item in items:
        if item["source"] == "tiktok":
            raise InputError("틱톡은 이 종류의 재생목록에 넣을 수 없습니다.", "TikToks cannot go into this kind of playlist.")

    channel = form.get(F_CHANNEL, "").strip() or default_channel
    if not channel:
        first = items[0]
        channel = youtube_info(first["id"])[1] if first["source"] == "youtube" else SOURCE_NAMES[first["source"]]
    pid = make_playlist_id(prefix, title, items[0]["id"], {p["id"] for p in playlists})
    p = {"id": pid, "kind": kind, "title": title, "channel": channel}
    if form.get(F_DESC, "").strip():
        p["desc"] = form[F_DESC].strip()
    p["videos"] = []
    for item in items:
        if item["id"] not in videos:
            videos[item["id"]] = new_video(item, title_override="", channel_override="",
                                           playlist_channel=channel, member=None, vertical=False)
        insert_by_date(p["videos"], item["id"], videos[item["id"]]["date"], videos)
    last_same_kind = max((n for n, q in enumerate(playlists) if q["kind"] == kind), default=len(playlists) - 1)
    playlists.insert(last_same_kind + 1, p)

    summary = [f"✅ 새 재생목록 **{option_label(p)}** 을 만들고 영상 {len(items)}개를 넣었습니다. / "
               f"Created with {len(items)} videos.", ""]
    summary += [video_line(i, videos[i]) for i in p["videos"]]
    summary += ["", "'새 영상 추가' 양식의 목록에도 추가했습니다. / Added to the 'Add videos' form."]
    return f"새 재생목록 추가: {title} (영상 {len(items)}개)", "\n".join(summary)


def video_line(vid, v):
    link = v.get("url") or (f"https://www.tiktok.com/video/{vid}" if v["source"] == "tiktok"
                            else f"https://youtu.be/{vid}")
    extras = [v["date"], v["title"], v.get("channel"), "세로" if v.get("vertical") else None,
              ",".join(v.get("members", [])) or None, v.get("era")]
    return "- " + " · ".join(filter(None, extras)) + f" — {link}"


def add():
    form = parse_issue(os.environ["ISSUE_BODY"])
    data = nd.load()
    handler = add_playlist if F_KIND in form else add_videos
    message, summary = handler(form, data)
    errors = validate(*data, check_files=False)
    if errors:
        raise RuntimeError("validation failed:\n" + "\n".join(errors))
    nd.save(*data)
    errors = validate(*nd.load())
    if errors:
        raise RuntimeError("validation failed after saving:\n" + "\n".join(errors))
    write_outputs(commit_message=message, summary=summary)


def write_outputs(**kv):
    eof = f"EOF_{uuid.uuid4().hex}"
    text = "".join(f"{k}<<{eof}\n{v}\n{eof}\n" for k, v in kv.items())
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a", encoding="utf-8") as f:
            f.write(text)
    else:
        print(text)


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "sync-form":
        return sync_form()
    if cmd != "add":
        sys.exit(__doc__)
    try:
        add()
    except InputError as e:
        write_outputs(error=f"❌ {e}\n\n이슈 내용을 수정하면 자동으로 다시 시도합니다. / "
                            "Edit the issue to try again automatically.")
        sys.exit(1)


if __name__ == "__main__":
    main()
