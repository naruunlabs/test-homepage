#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build.py — config.js 를 읽어 완전한 정적 index.html 을 생성합니다.

브라우저 자바스크립트로 내용을 그리지 않고, 이 스크립트가 HTML 파일 자체에
글자를 박아 넣습니다. 그래서 네이버·구글 크롤러와 AI 답변엔진이
내용을 그대로 읽을 수 있습니다.

사용법:  python3 scripts/build.py
"""

import html
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(ROOT, "config.js")
TEMPLATE_PATH = os.path.join(ROOT, "scripts", "template.html")
OUTPUT_PATH = os.path.join(ROOT, "index.html")
BLOG_DATA = os.path.join(ROOT, "scripts", "blog_data.json")

KST = timezone(timedelta(hours=9))

# ── 색상 프리셋 ──────────────────────────────────────────
THEMES = {
    "navy":     {"dark": "#0A1628", "accent": "#D92B3A", "gold": "#E8A020", "tint": "#F5F7FA"},
    "forest":   {"dark": "#10241C", "accent": "#1F7A4D", "gold": "#D9A441", "tint": "#F1F7F3"},
    "charcoal": {"dark": "#1C1C1E", "accent": "#C35528", "gold": "#F0B429", "tint": "#F6F5F4"},
    "indigo":   {"dark": "#1A1633", "accent": "#6D4AC7", "gold": "#E0A83B", "tint": "#F4F2FA"},
    "burgundy": {"dark": "#241017", "accent": "#A32236", "gold": "#C9A227", "tint": "#FAF3F4"},
    "teal":     {"dark": "#0C2028", "accent": "#198192", "gold": "#E3A62F", "tint": "#EFF6F8"},
    "sky":      {"dark": "#4879B1", "accent": "#D93C23", "gold": "#F2B93B", "tint": "#EDF4FC"},
    "sand":     {"dark": "#946F4F", "accent": "#C55423", "gold": "#E5B84B", "tint": "#FBF4EB"},
    "mint":     {"dark": "#358278", "accent": "#D23F64", "gold": "#F2C14E", "tint": "#EAF7F4"},
    "lilac":    {"dark": "#8A65B3", "accent": "#CF3D86", "gold": "#EFC05B", "tint": "#F3EFFB"},
}

DAY_EN = {"weekday": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
          "saturday": ["Saturday"], "sunday": ["Sunday"]}


def log(m):
    print(f"[build] {m}", flush=True)


def die(m):
    print(f"\n❌ {m}\n", file=sys.stderr)
    sys.exit(1)


# ── config.js 읽기 ──────────────────────────────────────
def load_config():
    if not os.path.exists(CONFIG_PATH):
        die("config.js 파일이 없습니다.")
    try:
        out = subprocess.run(
            ["node", "-e",
             f"const c=require({json.dumps(CONFIG_PATH)});process.stdout.write(JSON.stringify(c));"],
            capture_output=True, text=True, timeout=20)
    except FileNotFoundError:
        die("node(Node.js)가 필요합니다. GitHub Actions 에서는 자동으로 설치됩니다.")
    if out.returncode != 0:
        die("config.js 에 문법 오류가 있습니다.\n\n" + out.stderr.strip())
    return json.loads(out.stdout)


# ── 유틸 ────────────────────────────────────────────────
def e(v):
    """HTML 이스케이프"""
    return html.escape(str(v if v is not None else ""), quote=True)


def nl2br(v):
    return e(v).replace("\n", "<br>")


def img_exists(rel):
    return bool(rel) and os.path.exists(os.path.join(ROOT, rel))


def tel_href(p):
    return "tel:" + re.sub(r"[^0-9+]", "", str(p or ""))


def resolve_theme(t):
    if isinstance(t, dict):
        base = dict(THEMES["navy"]); base.update(t); return base
    if t in THEMES:
        return THEMES[t]
    log(f"⚠ 알 수 없는 테마 '{t}' — navy 로 대체합니다.")
    return THEMES["navy"]


def shade(hex_color, pct):
    n = hex_color.lstrip("#")
    r, g, b = (int(n[i:i+2], 16) for i in (0, 2, 4))
    f = 1 + pct / 100
    return "#%02X%02X%02X" % tuple(max(0, min(255, round(v * f))) for v in (r, g, b))


# ── 블로그 데이터 ────────────────────────────────────────
def load_blog():
    if not os.path.exists(BLOG_DATA):
        return {"notices": [], "gallery": []}
    try:
        with open(BLOG_DATA, encoding="utf-8") as fp:
            return json.load(fp)
    except Exception as exc:
        log(f"⚠ 블로그 데이터를 읽지 못했습니다: {exc}")
        return {"notices": [], "gallery": []}


def months_since(iso):
    if not iso:
        return 999
    try:
        d = datetime.fromisoformat(iso)
        if d.tzinfo is None:
            d = d.replace(tzinfo=KST)
        delta = datetime.now(KST) - d.astimezone(KST)
        return delta.days / 30.4
    except Exception:
        return 999


def date_visible(cfg, iso):
    mode = cfg["blog"].get("showDate", "auto")
    if mode is True:
        return True
    if mode is False:
        return False
    return months_since(iso) <= cfg["blog"].get("hideDateAfterMonths", 6)


def fmt_date(iso):
    try:
        return datetime.fromisoformat(iso).strftime("%Y.%m.%d")
    except Exception:
        return ""


# ── 섹션 렌더링 ─────────────────────────────────────────
def r_strengths(cfg):
    items = cfg.get("strengths", [])
    if not items:
        return ""
    cards = "\n".join(
        f'''        <article class="s-card">
          <h3>{e(s.get("title"))}</h3>
          <p>{e(s.get("desc"))}</p>
        </article>''' for s in items)
    return f'''    <section id="about" class="sec sec-tint">
      <div class="inner">
        <span class="eyebrow">Our standard</span>
        <h2 class="sec-title">아이의 하루를 생각하는 기준</h2>
        <p class="sec-lead">태권도 수련의 본질은 지키고, 아이가 도장에 머무는 시간 전체를 안전하게 운영합니다.</p>
        <div class="s-grid">
{cards}
        </div>
      </div>
    </section>'''


def r_programs(cfg):
    items = cfg.get("programs", [])
    if not items:
        return ""
    cards = []
    for i, p in enumerate(items, 1):
        rel = f"images/program{i}.jpg"
        pic = (f'<img src="{rel}" alt="{e(cfg["dojang"]["name"])} {e(p.get("title"))}" '
               f'loading="lazy" decoding="async">') if img_exists(rel) else ""
        cards.append(f'''        <article class="p-card">
          <div class="p-thumb">{pic}</div>
          <div class="p-body">
            <span class="p-tag">{e(p.get("tag"))}</span>
            <h3>{e(p.get("title"))}</h3>
            <p>{e(p.get("desc"))}</p>
          </div>
        </article>''')
    d = cfg["dojang"]
    return f'''    <section id="programs" class="sec">
      <div class="inner">
        <span class="eyebrow">Programs</span>
        <h2 class="sec-title">{e(d["region"])} 연령별 태권도 교육과정</h2>
        <p class="sec-lead">유치부부터 초등부, 중고등부까지 아이의 나이와 수준에 맞춰 단계적으로 지도합니다.</p>
        <div class="p-grid">
{chr(10).join(cards)}
        </div>
      </div>
    </section>'''


def r_master(cfg):
    m = cfg.get("master", {})
    if not m.get("name"):
        return ""
    badges = "".join(f'<span class="badge">{e(b)}</span>' for b in m.get("badges", []))
    photo = (f'<div class="m-photo"><img src="{e(m["photo"])}" alt="{e(m.get("name"))} 관장" '
             f'loading="lazy" decoding="async"></div>') if img_exists(m.get("photo")) else ""
    # 직함에 도장명이 없으면 자동으로 앞에 붙입니다 (도장명을 두 번 적는 실수 방지)
    role = m.get("title") or "관장"
    dname = cfg["dojang"]["name"]
    if dname not in role:
        role = f"{dname} {role}"
    return f'''    <section id="master" class="sec sec-tint">
      <div class="inner m-wrap">
        {photo}
        <div class="m-text">
          <span class="eyebrow">관장 소개</span>
          <h2 class="sec-title">아이를 이해하는 전문 지도</h2>
          <p class="m-name">{e(m.get("name"))} <span>{e(role)}</span></p>
          <p class="m-desc">{nl2br(m.get("desc"))}</p>
          <div class="badges">{badges}</div>
        </div>
      </div>
    </section>'''


def r_facility(cfg):
    f = cfg.get("facility", {})
    items = f.get("items", [])
    pics = [f"images/facility{i}.jpg" for i in range(1, 7)]
    pics = [p for p in pics if img_exists(p)]
    grid = "".join(
        f'<figure class="f-pic"><img src="{p}" alt="{e(cfg["dojang"]["name"])} 시설 사진" '
        f'loading="lazy" decoding="async"></figure>' for p in pics)
    chips = "".join(f'<span class="chip">{e(i)}</span>' for i in items)
    if not (grid or chips):
        return ""
    return f'''    <section id="facility" class="sec">
      <div class="inner">
        <span class="eyebrow">Training space</span>
        <h2 class="sec-title">수련에 집중할 수 있는 안전한 공간</h2>
        <div class="chips">{chips}</div>
        <div class="f-grid">{grid}</div>
      </div>
    </section>'''


def r_care(cfg):
    c = cfg.get("care", {})
    steps = "\n".join(
        f'''          <li><strong>{e(s.get("label"))}</strong><span>{e(s.get("desc"))}</span></li>'''
        for s in c.get("steps", []))
    return f'''    <section id="care" class="sec sec-dark">
      <div class="inner">
        <h2 class="sec-title">{nl2br(c.get("title"))}</h2>
        <p class="sec-lead">{nl2br(c.get("desc"))}</p>
        <ol class="care-steps">
{steps}
        </ol>
      </div>
    </section>'''


def r_van(cfg):
    v = cfg.get("van", {})
    areas = v.get("areas", [])
    if not areas:
        return ""
    chips = "".join(f'<span class="chip">{e(a)}</span>' for a in areas)
    note = f'<p class="sec-note">{e(v.get("note"))}</p>' if v.get("note") else ""
    return f'''    <section id="van" class="sec sec-tint">
      <div class="inner">
        <span class="eyebrow">차량 운행</span>
        <h2 class="sec-title">{e(cfg["dojang"]["region"])} 지역 차량 운행 안내</h2>
        <p class="sec-lead">학교와 주요 아파트를 중심으로 안전한 등하원을 돕습니다.</p>
        <div class="chips">{chips}</div>
        {note}
      </div>
    </section>'''


def r_notice(cfg, blog):
    items = blog.get("notices", [])[: cfg["blog"].get("noticeCount", 5)]
    if not items:
        return ""
    rows = []
    for n in items:
        dt = (f'<time datetime="{e(n.get("date", "")[:10])}">{fmt_date(n.get("date"))}</time>'
              if date_visible(cfg, n.get("date")) else "")
        rows.append(f'''          <li><a href="{e(n.get("url"))}" target="_blank" rel="noopener">
            <span class="n-title">{e(n.get("title"))}</span>
            <span class="n-desc">{e(n.get("summary"))}</span>{dt}
          </a></li>''')
    return f'''    <section id="notice" class="sec">
      <div class="inner">
        <span class="eyebrow">Notice</span>
        <h2 class="sec-title">도장 소식</h2>
        <ul class="n-list">
{chr(10).join(rows)}
        </ul>
      </div>
    </section>'''


def r_gallery(cfg, blog):
    items = [g for g in blog.get("gallery", []) if g.get("image")]
    items = items[: cfg["blog"].get("galleryCount", 9)]
    if not items:
        return ""
    cards = []
    for g in items:
        dt = (f'<span class="g-date">{fmt_date(g.get("date"))}</span>'
              if date_visible(cfg, g.get("date")) else "")
        dim = ""
        if g.get("w") and g.get("h"):
            dim = f' width="{g["w"]}" height="{g["h"]}"'
        cards.append(f'''          <figure class="g-card"><a href="{e(g.get("url"))}" target="_blank" rel="noopener">
            <img src="{e(g.get("image"))}" alt="{e(cfg["dojang"]["name"])} {e(g.get("title"))}"{dim} loading="lazy" decoding="async">
            <figcaption><span class="g-title">{e(g.get("title"))}</span>{dt}</figcaption>
          </a></figure>''')
    blog_url = f'https://blog.naver.com/{cfg["blog"]["blogId"]}'
    return f'''    <section id="gallery" class="sec sec-tint">
      <div class="inner">
        <span class="eyebrow">Gallery</span>
        <h2 class="sec-title">수련 갤러리</h2>
        <div class="g-grid">
{chr(10).join(cards)}
        </div>
        <a class="btn btn-line" href="{e(blog_url)}" target="_blank" rel="noopener">네이버 블로그에서 더 보기</a>
      </div>
    </section>'''


def r_faq(cfg):
    items = cfg.get("faq", [])
    if not items:
        return ""
    rows = "\n".join(f'''          <details class="faq-item">
            <summary>{e(f.get("q"))}</summary>
            <div class="faq-a">{nl2br(f.get("a"))}</div>
          </details>''' for f in items)
    return f'''    <section id="faq" class="sec">
      <div class="inner">
        <span class="eyebrow">Information</span>
        <h2 class="sec-title">자주 묻는 질문</h2>
        <div class="faq-list">
{rows}
        </div>
      </div>
    </section>'''


def r_location(cfg):
    d = cfg["dojang"]
    addr = d["address"]
    q = addr.replace(" ", "+")
    return f'''    <section id="location" class="sec sec-tint">
      <div class="inner">
        <span class="eyebrow">Location</span>
        <h2 class="sec-title">오시는 길</h2>
        <p class="loc-name">{e(d["name"])}</p>
        <p class="loc-addr">{e(addr)}</p>
        <div class="loc-btns">
          <a class="btn btn-line" href="https://map.naver.com/v5/search/{q}" target="_blank" rel="noopener">네이버지도</a>
          <a class="btn btn-line" href="https://map.kakao.com/link/search/{q}" target="_blank" rel="noopener">카카오맵</a>
          <a class="btn btn-line" href="https://www.google.com/maps/search/{q}" target="_blank" rel="noopener">구글지도</a>
        </div>
      </div>
    </section>'''


# ── JSON-LD (config 에서 자동 생성 → 값이 항상 일치) ──────
def r_jsonld(cfg, blog):
    d, h = cfg["dojang"], cfg["hours"]
    site = d["domain"].rstrip("/")

    opening = []
    for key, days in DAY_EN.items():
        slot = h.get(key, {})
        if slot.get("open") and slot.get("close"):
            opening.append({"@type": "OpeningHoursSpecification", "dayOfWeek": days,
                            "opens": slot["open"], "closes": slot["close"]})

    org = {
        "@type": ["SportsActivityLocation", "LocalBusiness", "Organization"],
        "@id": f"{site}/#organization",
        "name": d["name"], "url": f"{site}/", "sport": "태권도",
        "telephone": d["phone"] or d["phone2"],
        "address": {"@type": "PostalAddress", "streetAddress": d["address"],
                    "addressLocality": d["regionFull"], "addressCountry": "KR",
                    "postalCode": d.get("postalCode", "")},
        "geo": {"@type": "GeoCoordinates", "latitude": d["lat"], "longitude": d["lng"]},
        "areaServed": [{"@type": "AdministrativeArea", "name": d["regionFull"]}],
        "audience": [{"@type": "PeopleAudience", "audienceType": p.get("title")}
                     for p in cfg.get("programs", [])],
        "currenciesAccepted": "KRW", "paymentAccepted": "현금, 카드",
    }
    if opening:
        org["openingHoursSpecification"] = opening
    if d.get("phone2") and d.get("phone"):
        org["contactPoint"] = [{"@type": "ContactPoint", "telephone": d["phone2"],
                                "contactType": "상담"}]
    if cfg["blog"].get("blogId"):
        org["sameAs"] = [f'https://blog.naver.com/{cfg["blog"]["blogId"]}']

    graph = [
        {"@type": "WebSite", "@id": f"{site}/#website", "url": f"{site}/",
         "name": d["name"], "inLanguage": "ko-KR",
         "publisher": {"@id": f"{site}/#organization"}},
        org,
    ]
    if cfg.get("faq"):
        graph.append({
            "@type": "FAQPage", "@id": f"{site}/#faq", "inLanguage": "ko-KR",
            "mainEntity": [{"@type": "Question", "name": f["q"],
                            "acceptedAnswer": {"@type": "Answer", "text": f["a"]}}
                           for f in cfg["faq"]],
        })
    posts = (blog.get("notices", []) + blog.get("gallery", []))[:10]
    if posts:
        graph.append({
            "@type": "Blog", "@id": f"{site}/#blog", "name": f'{d["name"]} 소식',
            "blogPost": [{k: v for k, v in {
                "@type": "BlogPosting", "headline": p.get("title"), "url": p.get("url"),
                "datePublished": p.get("date"), "description": p.get("summary"),
                "image": (site + "/" + p["image"]) if p.get("image") else None,
            }.items() if v} for p in posts],
        })

    payload = {"@context": "https://schema.org", "@graph": graph}
    return ('<script type="application/ld+json">\n'
            + json.dumps(payload, ensure_ascii=False, indent=2) + '\n  </script>')


# ── 메타 / 네비게이션 ────────────────────────────────────
def r_meta(cfg):
    d, s = cfg["dojang"], cfg["seo"]
    site = d["domain"].rstrip("/")
    title = s.get("title") or f'{d["region"]} 태권도장 | 유치부·초등부 | {d["name"]}'
    desc = s.get("description") or (
        f'{d["region"]} {d["name"]}. 유치부·초등부 태권도 전문'
        + (', 방과 후 돌봄' if cfg["sections"].get("care") else "")
        + (', 차량운행' if cfg["sections"].get("van") else "")
        + ', 무료 체험수업 상담 가능합니다.')
    og = f'{site}/{s.get("ogImage")}' if img_exists(s.get("ogImage")) else ""

    tags = [
        f'<title>{e(title)}</title>',
        f'<meta name="description" content="{e(desc)}">',
        f'<link rel="canonical" href="{site}/">',
        f'<meta name="robots" content="index, follow, max-image-preview:large, max-snippet:-1">',
        f'<meta property="og:type" content="website">',
        f'<meta property="og:site_name" content="{e(d["name"])}">',
        f'<meta property="og:title" content="{e(title)}">',
        f'<meta property="og:description" content="{e(desc)}">',
        f'<meta property="og:url" content="{site}/">',
        f'<meta property="og:locale" content="ko_KR">',
        f'<meta name="twitter:card" content="summary_large_image">',
        f'<meta name="geo.region" content="KR">',
        f'<meta name="geo.placename" content="{e(d["regionFull"])}">',
        f'<meta name="geo.position" content="{d["lat"]};{d["lng"]}">',
        f'<meta name="ICBM" content="{d["lat"]}, {d["lng"]}">',
    ]
    if og:
        tags += [f'<meta property="og:image" content="{og}">',
                 f'<meta property="og:image:width" content="1200">',
                 f'<meta property="og:image:height" content="630">',
                 f'<meta name="twitter:image" content="{og}">']
    if s.get("googleVerification"):
        tags.append(f'<meta name="google-site-verification" content="{e(s["googleVerification"])}">')
    if s.get("naverVerification"):
        tags.append(f'<meta name="naver-site-verification" content="{e(s["naverVerification"])}">')
    return "\n  ".join(tags)


NAV_LABELS = [("about", "도장소개"), ("programs", "교육과정"), ("master", "관장소개"),
              ("facility", "시설안내"), ("van", "차량운행"), ("care", "돌봄"),
              ("notice", "공지사항"), ("gallery", "갤러리"), ("faq", "자주묻는질문"),
              ("location", "오시는길")]


def r_nav(cfg, present):
    return "\n".join(
        f'        <a href="#{k}">{e(label)}</a>'
        for k, label in NAV_LABELS
        if cfg["sections"].get(k) and k in present)


# ── 메인 ────────────────────────────────────────────────
def validate(cfg):
    """흔한 설정 실수를 미리 잡아냅니다."""
    warn, err = [], []
    d = cfg.get("dojang", {})

    for key, label in [("name", "도장 이름"), ("address", "주소"), ("region", "지역명")]:
        if not str(d.get(key, "")).strip():
            err.append(f"dojang.{key} ({label})이 비어 있습니다.")

    if not (d.get("phone") or d.get("phone2")):
        err.append("전화번호가 하나도 없습니다. dojang.phone 을 채워주세요.")

    dom = str(d.get("domain", ""))
    if not dom.startswith("http"):
        err.append("dojang.domain 은 https:// 로 시작해야 합니다.")
    if dom.endswith("/"):
        warn.append("dojang.domain 끝의 / 는 빼는 것이 좋습니다.")

    try:
        lat, lng = float(d.get("lat", 0)), float(d.get("lng", 0))
        if not (33 <= lat <= 39 and 124 <= lng <= 132):
            warn.append(f"좌표({lat}, {lng})가 한국 범위를 벗어납니다. 위도/경도가 바뀌지 않았는지 확인하세요.")
    except (TypeError, ValueError):
        err.append("dojang.lat / dojang.lng 는 숫자여야 합니다.")

    vague = ("상담 시 안내", "문의 바랍니다", "전화 문의", "상담을 통해")
    weak = [f["q"] for f in cfg.get("faq", [])
            if any(v in str(f.get("a", "")) for v in vague) and not re.search(r"\d", str(f.get("a", "")))]
    for q in weak:
        warn.append(f'FAQ "{q}" 의 답변에 구체적인 내용이 없습니다. 숫자나 지역명을 넣으면 검색 노출에 크게 유리합니다.')

    if len(cfg.get("faq", [])) < 3:
        warn.append("FAQ가 3개 미만입니다. 5개 이상 권장합니다.")

    for w in warn:
        log(f"⚠ {w}")
    if err:
        die("설정 오류\n\n  - " + "\n  - ".join(err))
    return cfg


def main():
    cfg = validate(load_config())
    blog = load_blog()
    log(f'도장: {cfg["dojang"]["name"]}')

    # 블로그가 너무 오래되었으면 섹션을 자동으로 숨김
    cutoff = cfg["blog"].get("hideSectionAfterMonths", 24)
    newest = min([months_since(p.get("date"))
                  for p in blog.get("notices", []) + blog.get("gallery", [])] or [999])
    if not cfg["blog"].get("blogId"):
        cfg["sections"]["notice"] = cfg["sections"]["gallery"] = False
        log("블로그 미사용 — 공지·갤러리 섹션 숨김")
    elif newest > cutoff:
        cfg["sections"]["notice"] = cfg["sections"]["gallery"] = False
        log(f"블로그 최신 글이 {newest:.0f}개월 전 — 공지·갤러리 섹션 숨김")

    renderers = {
        "strengths": lambda: r_strengths(cfg), "programs": lambda: r_programs(cfg),
        "master": lambda: r_master(cfg), "facility": lambda: r_facility(cfg),
        "van": lambda: r_van(cfg), "care": lambda: r_care(cfg),
        "notice": lambda: r_notice(cfg, blog), "gallery": lambda: r_gallery(cfg, blog),
        "faq": lambda: r_faq(cfg), "location": lambda: r_location(cfg),
    }
    order = ["strengths", "programs", "master", "facility", "care", "van",
             "notice", "gallery", "faq", "location"]

    body, present = [], set()
    for key in order:
        if not cfg["sections"].get(key):
            continue
        chunk = renderers[key]()
        if chunk.strip():
            body.append(chunk)
            present.add("about" if key == "strengths" else key)
    if cfg["sections"].get("strengths"):
        present.add("about")

    log(f"표시 섹션 {len(body)}개")

    if not os.path.exists(TEMPLATE_PATH):
        die("scripts/template.html 이 없습니다.")
    with open(TEMPLATE_PATH, encoding="utf-8") as fp:
        tpl = fp.read()

    d, h = cfg["dojang"], cfg["hours"]
    theme = resolve_theme(cfg.get("theme"))

    hours_txt = []
    if h["weekday"]["open"]:
        hours_txt.append(f'평일 {h["weekday"]["open"]}~{h["weekday"]["close"]}')
    if h["saturday"]["open"]:
        hours_txt.append(f'토 {h["saturday"]["open"]}~{h["saturday"]["close"]}')
    if h.get("closedNote"):
        hours_txt.append(h["closedNote"])

    hero_bg = ""
    if img_exists(cfg["hero"].get("bgImage")):
        hero_bg = f'style="background-image:url(\'{e(cfg["hero"]["bgImage"])}\')"'

    kakao = (f'<a class="btn btn-line" href="{e(d["kakaoUrl"])}" target="_blank" rel="noopener">카카오톡 문의</a>'
             if d.get("kakaoUrl") else "")

    repl = {
        "{{META}}": r_meta(cfg),
        "{{JSONLD}}": r_jsonld(cfg, blog),
        "{{THEME_DARK}}": theme["dark"],
        "{{THEME_DARK2}}": shade(theme["dark"], -20),
        "{{THEME_ACCENT}}": theme["accent"],
        "{{THEME_GOLD}}": theme["gold"],
        "{{THEME_TINT}}": theme["tint"],
        "{{NAV}}": r_nav(cfg, present),
        "{{SHORT_NAME}}": e(d["shortName"]),
        "{{NAME}}": e(d["name"]),
        "{{HERO_BG}}": hero_bg,
        "{{HERO_BADGE}}": e(cfg["hero"]["badge"]),
        "{{HERO_T1}}": e(cfg["hero"]["title1"]),
        "{{HERO_T2}}": e(cfg["hero"]["title2"]),
        "{{HERO_SUB}}": nl2br(cfg["hero"]["subtitle"]),
        "{{CTA1}}": e(cfg["hero"]["ctaPrimary"]),
        "{{CTA2}}": e(cfg["hero"]["ctaSecondary"]),
        "{{PHONE}}": e(d["phone"] or d["phone2"]),
        "{{TEL_HREF}}": tel_href(d["phone"] or d["phone2"]),
        "{{PHONE2_BLOCK}}": (f' · 상담전화 {e(d["phone2"])}' if d.get("phone2") else ""),
        "{{KAKAO_BTN}}": kakao,
        "{{ADDRESS}}": e(d["address"]),
        "{{HOURS}}": e(" / ".join(hours_txt)),
        "{{YEAR}}": str(datetime.now(KST).year),
        "{{SECTIONS}}": "\n\n".join(body),
    }
    out = tpl
    for k, v in repl.items():
        out = out.replace(k, v)

    left = re.findall(r"\{\{[A-Z_0-9]+\}\}", out)
    if left:
        die(f"치환되지 않은 자리표시자가 있습니다: {sorted(set(left))}")

    with open(OUTPUT_PATH, "w", encoding="utf-8") as fp:
        fp.write(out)
    log(f"index.html 생성 완료 ({len(out):,} bytes)")

    # sitemap / robots 도 함께 갱신
    site = d["domain"].rstrip("/")
    today = datetime.now(KST).strftime("%Y-%m-%d")
    with open(os.path.join(ROOT, "sitemap.xml"), "w", encoding="utf-8") as fp:
        fp.write(f'''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>{site}/</loc>
    <lastmod>{today}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>1.0</priority>
  </url>
</urlset>
''')
    with open(os.path.join(ROOT, "robots.txt"), "w", encoding="utf-8") as fp:
        fp.write(f"User-agent: *\nAllow: /\n\nSitemap: {site}/sitemap.xml\n")
    log("sitemap.xml / robots.txt 갱신 완료")
    return 0


if __name__ == "__main__":
    sys.exit(main())
