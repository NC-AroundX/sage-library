#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_library.py — sage library 웹 뷰어 생성기
books/*.md 카드를 읽어 library.html 한 파일을 만든다. (의존성 없음, 표준 라이브러리만)
사용: 프로젝트 폴더에서  python build_library.py
"""
import os, re, glob, html, json, hashlib

ROOT = os.path.dirname(os.path.abspath(__file__))
BOOKS_DIR = os.path.join(ROOT, "books")
OUT = os.path.join(ROOT, "library.html")

EASTERN_KEYS = ["동양", "한국"]  # 세로쓰기 표지 적용 분야

PALETTES = [  # 분야 해시 → 표지 색 (배경, 잉크, 액센트)
    ("#1E3A32", "#EFE7D6", "#B8905A"),
    ("#3A2A24", "#EFE7D6", "#C99A5B"),
    ("#252C3F", "#EAE6DA", "#A8B48C"),
    ("#4A2E33", "#F0E8D8", "#C3A15F"),
    ("#2E3A2A", "#EDE5D2", "#B78B4F"),
    ("#33313F", "#EBE7DE", "#AD9660"),
    ("#41352A", "#F0EADB", "#BC9A62"),
]

def parse_frontmatter(text):
    meta, body = {}, text
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.S)
    if m:
        body = text[m.end():]
        for line in m.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                v = v.strip()
                if v.startswith("[") and v.endswith("]"):
                    v = [x.strip() for x in v[1:-1].split(",") if x.strip()]
                meta[k.strip()] = v
    return meta, body

def md_to_html(md):
    lines = md.splitlines()
    out, i, in_ul, in_ol, in_bq = [], 0, False, False, False
    def close():
        nonlocal in_ul, in_ol, in_bq
        if in_ul: out.append("</ul>"); in_ul = False
        if in_ol: out.append("</ol>"); in_ol = False
        if in_bq: out.append("</blockquote>"); in_bq = False
    def inline(s):
        s = html.escape(s)
        s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
        s = re.sub(r"(?<!\*)\*([^*]+?)\*(?!\*)", r"<em>\1</em>", s)
        s = re.sub(r"`([^`]+?)`", r"<code>\1</code>", s)
        return s
    while i < len(lines):
        ln = lines[i]
        if re.match(r"^\s*$", ln): close(); i += 1; continue
        h = re.match(r"^(#{1,4})\s+(.*)", ln)
        if h: close(); lv = min(len(h.group(1)) + 1, 5); out.append(f"<h{lv}>{inline(h.group(2))}</h{lv}>"); i += 1; continue
        if re.match(r"^---+\s*$", ln): close(); out.append("<hr>"); i += 1; continue
        if ln.startswith(">"):
            if not in_bq: close(); out.append("<blockquote>"); in_bq = True
            out.append(f"<p>{inline(ln.lstrip('> '))}</p>"); i += 1; continue
        m_ol = re.match(r"^\s*\d+\.\s+(.*)", ln)
        m_ul = re.match(r"^\s*[-*]\s+(.*)", ln)
        if m_ol:
            if not in_ol: close(); out.append("<ol>"); in_ol = True
            out.append(f"<li>{inline(m_ol.group(1))}</li>"); i += 1; continue
        if m_ul:
            if not in_ul: close(); out.append("<ul>"); in_ul = True
            out.append(f"<li>{inline(m_ul.group(1))}</li>"); i += 1; continue
        if ln.strip().startswith("|"):
            close(); rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                if not re.match(r"^\s*\|[\s:|-]+\|\s*$", lines[i]):
                    rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            if rows:
                out.append("<table><thead><tr>" + "".join(f"<th>{inline(c)}</th>" for c in rows[0]) + "</tr></thead><tbody>")
                for r in rows[1:]:
                    out.append("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>")
                out.append("</tbody></table>")
            continue
        close(); out.append(f"<p>{inline(ln)}</p>"); i += 1
    close()
    return "\n".join(out)

def one_liner(body):
    m = re.search(r"\*\*한 줄 정의:?\*\*\s*(.+)", body)
    return m.group(1).strip() if m else ""

def load_books():
    books = []
    for path in sorted(glob.glob(os.path.join(BOOKS_DIR, "*.md"))):
        if os.path.basename(path).startswith("_"): continue
        with open(path, encoding="utf-8") as f: text = f.read()
        meta, body = parse_frontmatter(text)
        cat = str(meta.get("category", "기타"))
        idx = int(hashlib.md5(cat.split("·")[0].encode()).hexdigest(), 16) % len(PALETTES)
        bg, ink, acc = PALETTES[idx]
        books.append({
            "title": str(meta.get("title", os.path.basename(path))).split("(")[0].strip(),
            "full_title": str(meta.get("title", "")),
            "author": str(meta.get("author", "")),
            "era": str(meta.get("era", "")),
            "category": cat,
            "tags": meta.get("tags", []) if isinstance(meta.get("tags"), list) else [],
            "reliability": str(meta.get("reliability", "미상")),
            "vertical": any(k in cat for k in EASTERN_KEYS),
            "bg": bg, "ink": ink, "acc": acc,
            "one": one_liner(body),
            "html": md_to_html(body),
        })
    return books

def render(books):
    cats = sorted({b["category"].split("·")[0] for b in books})
    data = json.dumps(books, ensure_ascii=False).replace("</", "<\\/")
    n = len(books)
    return """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>sage library — 서가</title>
<link href="https://fonts.googleapis.com/css2?family=Noto+Serif+KR:wght@400;600;900&family=Gowun+Batang&display=swap" rel="stylesheet">
<style>
:root{--night:#101815;--night2:#16211C;--paper:#EFE7D6;--paper-dim:#C9BFA8;--brass:#B8905A;--oxblood:#8A4636;--line:rgba(239,231,214,.14)}
*{margin:0;padding:0;box-sizing:border-box}
body{background:var(--night);color:var(--paper);font-family:'Gowun Batang','Noto Serif KR',serif;-webkit-font-smoothing:antialiased}
a{color:var(--brass)}
header{padding:56px 6vw 28px;border-bottom:1px solid var(--line)}
.eyebrow{font-size:12px;letter-spacing:.35em;color:var(--brass);text-transform:uppercase}
h1{font-family:'Noto Serif KR',serif;font-weight:900;font-size:clamp(30px,4.5vw,52px);margin:10px 0 6px}
.sub{color:var(--paper-dim);font-size:15px}
.toolbar{display:flex;flex-wrap:wrap;gap:10px;align-items:center;padding:18px 6vw;border-bottom:1px solid var(--line);position:sticky;top:0;background:rgba(16,24,21,.92);backdrop-filter:blur(8px);z-index:5}
.chip{border:1px solid var(--line);background:none;color:var(--paper-dim);padding:7px 14px;border-radius:999px;font-family:inherit;font-size:13px;cursor:pointer;transition:.2s}
.chip:hover{border-color:var(--brass);color:var(--paper)}
.chip.on{background:var(--brass);border-color:var(--brass);color:#171310;font-weight:700}
#q{margin-left:auto;background:var(--night2);border:1px solid var(--line);color:var(--paper);padding:9px 14px;border-radius:8px;font-family:inherit;font-size:14px;min-width:200px}
#q:focus{outline:2px solid var(--brass);outline-offset:1px}
.shelf{display:grid;grid-template-columns:repeat(auto-fill,minmax(168px,1fr));gap:34px 26px;padding:40px 6vw 80px}
.slot{display:flex;flex-direction:column;gap:10px;cursor:pointer;background:none;border:none;text-align:left;font-family:inherit;color:var(--paper)}
.cover{aspect-ratio:2/3;border-radius:3px 8px 8px 3px;position:relative;padding:16px 14px;display:flex;box-shadow:0 12px 24px rgba(0,0,0,.45), inset 4px 0 0 rgba(0,0,0,.25), inset 6px 0 0 rgba(255,255,255,.06);transition:transform .25s, box-shadow .25s;overflow:hidden}
.slot:hover .cover,.slot:focus-visible .cover{transform:translateY(-8px) rotate(-1deg);box-shadow:0 22px 34px rgba(0,0,0,.55), inset 4px 0 0 rgba(0,0,0,.25)}
.slot:focus-visible{outline:2px solid var(--brass);outline-offset:4px;border-radius:8px}
.cover .frame{position:absolute;inset:8px;border:1px solid;opacity:.5;border-radius:2px 5px 5px 2px;pointer-events:none}
.cover .t{font-family:'Noto Serif KR',serif;font-weight:900;font-size:clamp(16px,1.6vw,21px);line-height:1.35;word-break:keep-all}
.cover .a{position:absolute;bottom:14px;left:14px;right:14px;font-size:11.5px;letter-spacing:.08em;opacity:.85}
.cover.v{justify-content:flex-end}
.cover.v .t{writing-mode:vertical-rl;text-orientation:upright;letter-spacing:.28em;margin:6px 4px 0 0}
.cover.v .a{writing-mode:vertical-rl;left:16px;right:auto;top:16px;bottom:auto;letter-spacing:.2em}
.cover .seal{position:absolute;width:22px;height:22px;border-radius:4px;background:var(--oxblood);bottom:14px;right:14px;display:flex;align-items:center;justify-content:center;font-size:10px;color:#EFE7D6;font-weight:700}
.meta .bt{font-weight:700;font-size:14.5px}
.meta .bs{color:var(--paper-dim);font-size:12.5px;margin-top:3px}
.badge{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:6px;vertical-align:1px}
.b-원전기반{background:#8FAE6B}.b-요약검증{background:#C99A5B}.b-미검증,.b-미상{background:#777}
.count{padding:0 6vw;margin-top:26px;color:var(--paper-dim);font-size:13px;letter-spacing:.15em}
dialog{width:min(760px,92vw);max-height:86vh;background:var(--paper);color:#241F17;border:none;border-radius:10px;padding:0}
dialog::backdrop{background:rgba(8,12,10,.72);backdrop-filter:blur(3px)}
.dhead{padding:30px 38px 20px;border-bottom:1px solid rgba(36,31,23,.15);position:sticky;top:0;background:var(--paper)}
.dhead .cat{font-size:12px;letter-spacing:.3em;color:var(--oxblood)}
.dhead h2{font-family:'Noto Serif KR',serif;font-weight:900;font-size:26px;margin:6px 0 4px}
.dhead .who{color:#6B6353;font-size:14px}
.dbody{padding:26px 38px 44px;overflow-y:auto;font-size:15.5px;line-height:1.85}
.dbody h3{font-family:'Noto Serif KR',serif;margin:26px 0 10px;font-size:19px;border-bottom:1px solid rgba(36,31,23,.15);padding-bottom:6px}
.dbody h4,.dbody h5{margin:18px 0 8px}
.dbody p{margin:10px 0}.dbody ul,.dbody ol{margin:10px 0 10px 22px}.dbody li{margin:7px 0}
.dbody blockquote{border-left:3px solid var(--brass);padding-left:14px;color:#5C5443;margin:12px 0}
.dbody em{color:#6E5A33}
.close{position:absolute;top:22px;right:24px;background:none;border:1px solid rgba(36,31,23,.3);border-radius:999px;width:34px;height:34px;font-size:16px;cursor:pointer;font-family:inherit}
.empty{padding:60px 6vw;color:var(--paper-dim)}
@media (prefers-reduced-motion:reduce){*{transition:none!important}}
@media (max-width:560px){.shelf{grid-template-columns:repeat(auto-fill,minmax(130px,1fr));gap:24px 16px}.dhead,.dbody{padding-left:22px;padding-right:22px}}
</style>
</head>
<body>
<header>
  <div class="eyebrow">Sage Library</div>
  <h1>인사이트 서가</h1>
  <div class="sub">책 __N__권 · 카드를 누르면 개요와 인사이트가 열립니다 · <span class="badge b-원전기반"></span>원전기반 <span class="badge b-요약검증"></span>요약검증</div>
</header>
<div class="toolbar" id="chips"><input id="q" type="search" placeholder="제목·저자·태그 검색"></div>
<div class="count" id="count"></div>
<div class="shelf" id="shelf"></div>
<dialog id="dlg"><button class="close" onclick="dlg.close()" aria-label="닫기">✕</button><div class="dhead"><div class="cat" id="dcat"></div><h2 id="dtitle"></h2><div class="who" id="dwho"></div></div><div class="dbody" id="dbody"></div></dialog>
<script>
const BOOKS=__DATA__;
const CATS=__CATS__;
let cat="전체", q="";
const chips=document.getElementById("chips"), shelf=document.getElementById("shelf");
["전체",...CATS].forEach(c=>{const b=document.createElement("button");b.className="chip"+(c==="전체"?" on":"");b.textContent=c;b.onclick=()=>{cat=c;document.querySelectorAll(".chip").forEach(x=>x.classList.toggle("on",x===b));draw()};chips.insertBefore(b,document.getElementById("q"))});
document.getElementById("q").addEventListener("input",e=>{q=e.target.value.trim().toLowerCase();draw()});
function match(b){const inCat=cat==="전체"||b.category.startsWith(cat);const hay=(b.title+b.author+b.category+(b.tags||[]).join(" ")).toLowerCase();return inCat&&(!q||hay.includes(q))}
function draw(){
  const list=BOOKS.filter(match);
  document.getElementById("count").textContent=list.length+" / "+BOOKS.length+"권";
  shelf.innerHTML="";
  if(!list.length){shelf.innerHTML='<div class="empty">이 조건에 맞는 책이 아직 서가에 없습니다. 검색어를 지우거나 다른 분야를 눌러보세요.</div>';return}
  list.forEach((b,i)=>{
    const el=document.createElement("button");el.className="slot";
    el.innerHTML=`<div class="cover ${b.vertical?"v":""}" style="background:${b.bg};color:${b.ink}">
      <div class="frame" style="border-color:${b.acc}"></div>
      <div class="t">${b.title}</div><div class="a">${b.author}</div>
      ${b.vertical?`<div class="seal">${b.title[0]||""}</div>`:""}
    </div>
    <div class="meta"><div class="bt"><span class="badge b-${b.reliability}"></span>${b.title}</div><div class="bs">${b.author} · ${b.category}</div></div>`;
    el.onclick=()=>open(b);
    shelf.appendChild(el);
  });
}
function open(b){
  document.getElementById("dcat").textContent=b.category+" · "+b.era+" · "+b.reliability;
  document.getElementById("dtitle").textContent=b.full_title||b.title;
  document.getElementById("dwho").textContent=b.author;
  document.getElementById("dbody").innerHTML=b.html;
  document.getElementById("dbody").scrollTop=0;
  dlg.showModal();
}
draw();
</script>
</body>
</html>""".replace("__DATA__", data).replace("__CATS__", json.dumps(cats, ensure_ascii=False)).replace("__N__", str(n))

if __name__ == "__main__":
    books = load_books()
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(render(books))
    print(f"library.html 생성 완료 — {len(books)}권 수록")
