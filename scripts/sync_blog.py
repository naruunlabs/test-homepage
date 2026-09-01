#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sync_blog.py — 네이버 블로그 RSS를 읽어 scripts/blog_data.json 을 만듭니다.

대표 이미지는 저장소 안(images/blog/)에 내려받습니다.
네이버 이미지 서버는 외부 사이트에서 직접 불러오면 차단하기 때문입니다.

이 스크립트는 데이터만 만들고, HTML 생성은 build.py 가 담당합니다.
"""

import hashlib
import html
import io
import json
import os
import re
import subprocess
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(ROOT, "config.js")
OUT_PATH = os.path.join(ROOT, "scripts", "blog_data.json")
IMAGE_DIR = os.path.join(ROOT, "images", "blog")
IMAGE_WEB = "images/blog"

KST = timezone(timedelta(hours=9))
MAX_W, QUALITY = 900, 82

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"),
    "Accept-Language": "ko-KR,ko;q=0.9",
}
IMG_HEADERS = dict(HEADERS, Referer="https://blog.naver.com/")

IMG_RE = re.compile(r"""<img[^>]+src=["']([^"']+)["']""", re.I)
SKIP_IMG = ("ssl.pstatic.net/static", "blogpfthumb", "sticker", "emoticon", "ssl.pstatic.net/dthumb")


def log(m):
    print(f"[sync_blog] {m}", flush=True)


def load_config():
    out = subprocess.run(
        ["node", "-e", f"const c=require({json.dumps(CONFIG_PATH)});process.stdout.write(JSON.stringify(c));"],
        capture_output=True, text=True, timeout=20)
    if out.returncode != 0:
        print("config.js 오류:\n" + out.stderr, file=sys.stderr)
        sys.exit(1)
    return json.loads(out.stdout)


def fetch(url, headers=None, timeout=25):
    req = urllib.request.Request(url, headers=headers or HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def strip_tags(raw):
    if not raw:
        return ""
    t = re.sub(r"<(script|style).*?</\1>", " ", raw, flags=re.S | re.I)
    t = re.sub(r"<br\s*/?>|</p>", " ", t, flags=re.I)
    t = re.sub(r"<[^>]+>", " ", t)
    t = html.unescape(t)
    t = re.sub(r"[\u200b\ufeff]", "", t)
    return re.sub(r"\s+", " ", t).strip()


def summarize(raw, limit=110):
    t = strip_tags(raw)
    return t if len(t) <= limit else t[:limit].rstrip() + "…"


def parse_date(v):
    if not v:
        return None
    try:
        d = parsedate_to_datetime(v)
        return (d.replace(tzinfo=timezone.utc) if d.tzinfo is None else d).astimezone(KST)
    except Exception:
        pass
    for f in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            d = datetime.strptime(v.strip(), f)
            return (d.replace(tzinfo=KST) if d.tzinfo is None else d).astimezone(KST)
        except Exception:
            continue
    return None


def load_feed(blog_id):
    last = None
    for url in (f"https://rss.blog.naver.com/{blog_id}.xml",
                f"https://blog.rss.naver.com/{blog_id}.xml"):
        try:
            log(f"RSS 요청: {url}")
            return ET.fromstring(fetch(url))
        except Exception as exc:
            last = exc
            log(f"실패: {exc}")
    raise SystemExit(f"RSS를 읽지 못했습니다: {last}")


def parse_items(root):
    items = []
    for node in root.iter("item"):
        def txt(tag):
            el = node.find(tag)
            return (el.text or "").strip() if el is not None and el.text else ""

        title, link = html.unescape(txt("title")), txt("link")
        if not title or not link:
            continue
        link = link.replace("m.blog.naver.com", "blog.naver.com").replace("http://", "https://")

        body = txt("description")
        for ch in node:
            if ch.tag.endswith("encoded") and ch.text and len(ch.text) > len(body):
                body = ch.text

        items.append({
            "title": title, "url": link, "body": body,
            "categories": [c.text.strip() for c in node.findall("category") if c.text],
            "date": parse_date(txt("pubDate") or txt("date")),
        })
    log(f"글 {len(items)}건 수집")
    return items


def pick_image(body):
    if not body:
        return ""
    for src in IMG_RE.findall(html.unescape(body)):
        src = src.strip()
        if not src.startswith("http") or any(b in src for b in SKIP_IMG):
            continue
        src = re.sub(r"\?type=w?\d+", "?type=w966", src)
        if "?type=" not in src and "postfiles" in src:
            src += "?type=w966"
        return src
    return ""


def save_image(url, prefix):
    if not url:
        return "", 0, 0
    os.makedirs(IMAGE_DIR, exist_ok=True)
    name = f"{prefix}-{hashlib.sha1(url.encode()).hexdigest()[:12]}.jpg"
    disk, web = os.path.join(IMAGE_DIR, name), f"{IMAGE_WEB}/{name}"

    if os.path.exists(disk):
        try:
            from PIL import Image
            with Image.open(disk) as im:
                return web, im.width, im.height
        except Exception:
            return web, 0, 0
    try:
        raw = fetch(url, headers=IMG_HEADERS, timeout=30)
    except Exception as exc:
        log(f"이미지 실패({exc}): {url[:70]}")
        return "", 0, 0
    try:
        from PIL import Image
        with Image.open(io.BytesIO(raw)) as im:
            im = im.convert("RGB")
            if im.width > MAX_W:
                im = im.resize((MAX_W, round(im.height * MAX_W / im.width)), Image.LANCZOS)
            im.save(disk, "JPEG", quality=QUALITY, optimize=True)
            log(f"이미지 저장: {name} ({im.width}x{im.height})")
            return web, im.width, im.height
    except Exception as exc:
        log(f"이미지 변환 실패({exc}) — 원본 저장")
        with open(disk, "wb") as fp:
            fp.write(raw)
        return web, 0, 0


def prune(used):
    if not os.path.isdir(IMAGE_DIR):
        return
    n = 0
    for f in os.listdir(IMAGE_DIR):
        if f.endswith(".jpg") and f not in used:
            try:
                os.remove(os.path.join(IMAGE_DIR, f)); n += 1
            except OSError:
                pass
    if n:
        log(f"미사용 이미지 {n}건 정리")


def main():
    cfg = load_config()
    bcfg = cfg.get("blog", {})
    blog_id = bcfg.get("blogId", "").strip()

    if not blog_id:
        log("blogId 가 비어 있습니다 — 빈 데이터로 저장합니다.")
        with open(OUT_PATH, "w", encoding="utf-8") as fp:
            json.dump({"notices": [], "gallery": []}, fp, ensure_ascii=False, indent=2)
        return 0

    items = parse_items(load_feed(blog_id))
    if not items:
        log("가져온 글이 없습니다.")
        return 0

    kws = bcfg.get("noticeKeywords", ["공지", "안내"])
    notices, gallery = [], []
    for it in items:
        it["summary"] = summarize(it["body"])
        it["img_url"] = pick_image(it["body"])
        hay = it["title"] + " " + " ".join(it["categories"])
        (notices if any(k in hay for k in kws) else gallery).append(it)

    notices = notices[: bcfg.get("noticeCount", 5)]
    gallery = [g for g in gallery if g["img_url"]][: bcfg.get("galleryCount", 9)]
    log(f"분류 결과 — 공지 {len(notices)}건, 갤러리 {len(gallery)}건")

    used = set()
    for g in gallery:
        stamp = g["date"].strftime("%Y%m%d") if g["date"] else "nodate"
        path, w, h = save_image(g["img_url"], f"blog-{stamp}")
        g["image"], g["w"], g["h"] = path, w, h
        if path:
            used.add(os.path.basename(path))
    prune(used)

    def clean(lst):
        return [{"title": i["title"], "url": i["url"], "summary": i["summary"],
                 "date": i["date"].isoformat() if i["date"] else "",
                 "image": i.get("image", ""), "w": i.get("w", 0), "h": i.get("h", 0)}
                for i in lst]

    with open(OUT_PATH, "w", encoding="utf-8") as fp:
        json.dump({"notices": clean(notices), "gallery": clean(gallery),
                   "syncedAt": datetime.now(KST).isoformat()},
                  fp, ensure_ascii=False, indent=2)
    log("blog_data.json 저장 완료")
    return 0


if __name__ == "__main__":
    sys.exit(main())
