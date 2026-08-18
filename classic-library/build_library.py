#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_library.py (v3 · 고요서가) — sage library 서가 뷰어 생성기
Claude Design 시안 '고요서가'의 디자인 언어를 이식한 버전.
books/*.md 카드를 읽어 library.html + index.html 생성.
assets/covers/<slug>.jpg 가 있으면 실물 표지, 없으면 분야색 표지.
사용: classic-library 폴더에서  python build_library.py
"""
import os, re, glob, html, json, hashlib, datetime, sys
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = os.path.dirname(os.path.abspath(__file__))
BOOKS_DIR = os.path.join(ROOT, "books")
HUES = [25, 70, 150, 210, 290, 340, 50, 185, 110, 260]

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
    lines, out, i = md.splitlines(), [], 0
    in_ul = in_ol = in_bq = False
    def close():
        nonlocal in_ul, in_ol, in_bq
        if in_ul: out.append("</ul>"); in_ul = False
        if in_ol: out.append("</ol>"); in_ol = False
        if in_bq: out.append("</blockquote>"); in_bq = False
    def inline(s):
        s = html.escape(s)
        s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
        s = re.sub(r"(?<!\*)\*([^*]+?)\*(?!\*)", r"<em>\1</em>", s)
        return s
    while i < len(lines):
        ln = lines[i]
        if re.match(r"^\s*$", ln): close(); i += 1; continue
        h = re.match(r"^(#{1,4})\s+(.*)", ln)
        if h: close(); lv = min(len(h.group(1)) + 1, 5); out.append(f"<h{lv}>{inline(h.group(2))}</h{lv}>"); i += 1; continue
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
    m = re.search(r"\*\*한 줄 (?:정의|정수):?\*\*\s*(.+)", body)
    return m.group(1).strip() if m else ""

def load_books():
    books = []
    for path in sorted(glob.glob(os.path.join(BOOKS_DIR, "*.md"))):
        if os.path.basename(path).startswith("_"): continue
        with open(path, encoding="utf-8") as f: text = f.read()
        meta, body = parse_frontmatter(text)
        cat = str(meta.get("category", "기타"))
        main_cat = cat.split("·")[0]
        slug = str(meta.get("slug", os.path.splitext(os.path.basename(path))[0]))
        hue = HUES[int(hashlib.md5(main_cat.encode()).hexdigest(), 16) % len(HUES)]
        has_cover = os.path.exists(os.path.join(ROOT, "assets", "covers", f"{slug}.jpg"))
        books.append({
            "title": str(meta.get("title", "")).split("(")[0].strip() or slug,
            "full_title": str(meta.get("title", "")),
            "author": str(meta.get("author", "")),
            "era": str(meta.get("era", "")),
            "category": cat, "main_cat": main_cat, "hue": hue,
            "tags": meta.get("tags", []) if isinstance(meta.get("tags"), list) else [],
            "reliability": str(meta.get("reliability", "미상")),
            "cover": f"assets/covers/{slug}.jpg" if has_cover else "",
            "one": one_liner(body),
            "html": md_to_html(body),
        })
    return books

def render(books):
    cats = sorted({b["main_cat"] for b in books},
                  key=lambda c: -sum(1 for b in books if b["main_cat"] == c))
    n = len(books)
    covers_n = sum(1 for b in books if b["cover"])
    feat_i = int(hashlib.md5(datetime.date.today().isoformat().encode()).hexdigest(), 16) % n if n else 0
    data = json.dumps(books, ensure_ascii=False).replace("</", "<\\/")
    return """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>고요서가 — sage library</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Nanum+Myeongjo:wght@400;700;800&family=Noto+Serif+KR:wght@400;500;600&display=swap" rel="stylesheet">
<style>
html{scroll-behavior:smooth}
*{margin:0;padding:0;box-sizing:border-box}
::-webkit-scrollbar{height:8px;width:10px}
::-webkit-scrollbar-thumb{background:oklch(80% .02 70);border-radius:4px}
body{font-family:'Noto Serif KR',serif;background:oklch(97% .014 75);color:oklch(20% .02 50);min-height:100vh}
a{color:inherit;text-decoration:none}
header{position:sticky;top:0;z-index:50;display:flex;align-items:center;justify-content:space-between;gap:20px;flex-wrap:wrap;padding:18px 48px;background:oklch(97% .014 75 / .92);backdrop-filter:blur(8px);border-bottom:1px solid oklch(20% .02 50 / .08)}
.brand{font-family:'Nanum Myeongjo',serif;font-size:25px;font-weight:800;letter-spacing:.5px}
nav{display:flex;gap:22px;font-size:14.5px;color:oklch(45% .02 50);flex-wrap:wrap}
nav a:hover{color:oklch(20% .02 50)}
.searchpill{display:flex;align-items:center;gap:10px;background:oklch(92% .02 75);border-radius:999px;padding:10px 18px;width:clamp(180px,24vw,300px)}
.searchpill input{border:none;background:transparent;outline:none;font-family:inherit;font-size:14px;color:oklch(20% .02 50);width:100%}
.hero{margin:38px 48px 60px;padding:52px;background:oklch(94% .02 75);border-radius:20px;box-shadow:0 20px 50px oklch(20% .02 50 / .08);display:flex;align-items:center;gap:56px;flex-wrap:wrap}
.bookcover{position:relative;border-radius:3px 10px 10px 3px;overflow:hidden;flex-shrink:0}
.bookcover img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}
.bookcover .spine{position:absolute;left:0;top:0;bottom:0;z-index:2}
.bookcover .gen{position:absolute;left:0;right:0;bottom:0;padding:14px;display:flex;flex-direction:column;gap:6px;z-index:1}
.bookcover .gen .rule{width:22px;height:1px;background:oklch(96% .01 75 / .3)}
.bookcover .gen .t{font-family:'Nanum Myeongjo',serif;font-weight:600;color:oklch(97% .01 75);line-height:1.35;word-break:keep-all}
.bookcover .gen .a{color:oklch(97% .01 75 / .7)}
.hero .bookcover{width:280px;height:420px;box-shadow:0 30px 60px oklch(20% .02 50 / .28), 0 8px 16px oklch(20% .02 50 / .15)}
.hero .bookcover .spine{width:7px}
.hero .bookcover .gen .t{font-size:22px}.hero .bookcover .gen .a{font-size:13px}
.hero .txt{flex:1;min-width:260px}
.hero .eyebrow{font-size:12px;letter-spacing:.32em;color:oklch(50% .06 60);text-transform:uppercase}
.hero h1{font-family:'Nanum Myeongjo',serif;font-weight:800;font-size:clamp(28px,3.6vw,44px);margin:12px 0 8px;line-height:1.25;word-break:keep-all}
.hero .who{font-size:15px;color:oklch(45% .02 50)}
.hero .one{margin-top:16px;font-size:15.5px;line-height:1.85;color:oklch(30% .02 50);max-width:58ch;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}
.hero button{margin-top:22px;font-family:inherit;font-size:14.5px;background:oklch(24% .03 50);color:oklch(97% .01 75);border:none;border-radius:999px;padding:12px 26px;cursor:pointer}
.hero button:hover{background:oklch(34% .06 40)}
.stats{padding:0 48px 8px;font-size:13px;color:oklch(45% .02 50);letter-spacing:.08em}
.shelfsec{margin:0 0 58px;scroll-margin-top:100px}
.shelfhead{display:flex;align-items:baseline;justify-content:space-between;padding:0 48px 16px}
.shelfhead h2{font-family:'Nanum Myeongjo',serif;font-size:25px;font-weight:700}
.shelfhead .cnt{font-size:13.5px;color:oklch(45% .02 50)}
.shelfwrap{position:relative;padding:0 48px 30px}
.row{display:flex;gap:26px;overflow-x:auto;padding:10px 0 24px;align-items:flex-end}
.slot{flex-shrink:0;background:none;border:none;cursor:pointer;font-family:inherit;padding:0}
.slot .bookcover{width:148px;height:222px;box-shadow:0 10px 16px oklch(20% .02 50 / .28);transition:transform .25s ease, box-shadow .25s ease}
.slot .bookcover .spine{width:5px}
.slot .bookcover .gen .t{font-size:14px}.slot .bookcover .gen .a{font-size:10.5px}
.slot:hover .bookcover,.slot:focus-visible .bookcover{transform:translateY(-10px);box-shadow:0 26px 32px oklch(20% .02 50 / .32)}
.slot:focus-visible{outline:2px solid oklch(50% .1 60);outline-offset:4px;border-radius:8px}
.shelfbar{position:absolute;left:48px;right:48px;bottom:14px;height:14px;border-radius:2px;background:linear-gradient(oklch(84% .03 70), oklch(76% .035 65));box-shadow:0 10px 18px oklch(20% .02 50 / .22)}
.empty{padding:40px 48px 80px;color:oklch(45% .02 50)}
dialog{width:min(780px,94vw);max-height:88vh;background:oklch(97% .014 75);color:oklch(20% .02 50);border:none;border-radius:14px;padding:0;box-shadow:0 40px 80px oklch(20% .02 50 / .4)}
dialog::backdrop{background:oklch(20% .02 50 / .55);backdrop-filter:blur(3px)}
.dwrap{display:flex;gap:38px;padding:46px;flex-wrap:wrap}
.dwrap .bookcover{width:210px;height:315px;box-shadow:0 24px 40px oklch(20% .02 50 / .3)}
.dwrap .bookcover .spine{width:6px}
.dwrap .bookcover .gen .t{font-size:17px}.dwrap .bookcover .gen .a{font-size:11.5px}
.dtxt{flex:1;min-width:260px;display:flex;flex-direction:column;gap:13px}
.chips{display:flex;gap:8px;flex-wrap:wrap}
.chip{font-size:12px;padding:4px 12px;border-radius:999px}
.dtxt h2{font-family:'Nanum Myeongjo',serif;font-size:29px;font-weight:800;line-height:1.3;word-break:keep-all}
.dtxt .who{font-size:15px;color:oklch(45% .02 50)}
.hr{height:1px;background:oklch(20% .02 50 / .1);margin:4px 0}
.done{font-size:15.5px;line-height:1.8;color:oklch(28% .02 50)}
.dbody{font-size:15px;line-height:1.85;color:oklch(34% .02 50)}
.dbody h2,.dbody h3{font-family:'Nanum Myeongjo',serif;margin:22px 0 9px;font-size:18px;color:oklch(22% .02 50);border-bottom:1px solid oklch(20% .02 50 / .1);padding-bottom:6px}
.dbody h4,.dbody h5{margin:15px 0 7px;color:oklch(24% .02 50)}
.dbody p{margin:9px 0}.dbody ul,.dbody ol{margin:9px 0 9px 20px}.dbody li{margin:6px 0}
.dbody blockquote{border-left:3px solid oklch(60% .08 70);padding-left:13px;color:oklch(45% .02 50);margin:11px 0}
.dbody em{color:oklch(45% .09 60)}
.dclose{position:absolute;top:16px;right:20px;border:none;background:transparent;font-size:23px;cursor:pointer;color:oklch(45% .02 50);font-family:serif}
.dclose:hover{color:oklch(20% .02 50)}
footer{padding:40px 48px 60px;font-size:12.5px;color:oklch(55% .02 50);letter-spacing:.08em}
@media (prefers-reduced-motion:reduce){*{transition:none!important}}
@media (max-width:680px){header,.stats,.shelfhead,.empty,footer{padding-left:20px;padding-right:20px}
 .hero{margin:24px 20px 44px;padding:30px 22px;gap:28px;flex-direction:column-reverse;text-align:center}
 .hero .one{-webkit-line-clamp:4}.hero .bookcover{width:190px;height:285px}
 .shelfwrap{padding:0 20px 30px}.shelfbar{left:20px;right:20px}
 .dwrap{padding:26px 20px;gap:22px}.dwrap .bookcover{margin:0 auto}}
</style>
</head>
<body>
<header>
  <a class="brand" href="#top">고요서가</a>
  <nav id="nav"></nav>
  <div class="searchpill">
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="oklch(45% 0.02 50)" stroke-width="2.4"><circle cx="10.5" cy="10.5" r="7"/><line x1="16" y1="16" x2="21" y2="21"/></svg>
    <input id="q" type="search" placeholder="책 제목, 저자, 태그 검색">
  </div>
</header>
<div id="top"></div>

<section class="hero" id="hero"></section>
<div class="stats">서가의 책 __N__권 · 실물 표지 __C__권 · 매주 자동으로 자랍니다</div>
<div id="shelves"></div>
<footer>고요서가 — sage library · 스스로 자라는 개인 인사이트 서가</footer>

<dialog id="dlg"><button class="dclose" onclick="dlg.close()" aria-label="닫기">×</button><div class="dwrap" id="dwrap"></div></dialog>
<script>
const BOOKS=__DATA__;
const CATS=__CATS__;
const FEAT=__FEAT__;
let q="";
const catId=c=>"cat-"+encodeURIComponent(c).replace(/%/g,"");
function coverHTML(b){
  const spine=`<div class="spine" style="background:oklch(22% .05 ${b.hue})"></div>`;
  if(b.cover) return `<div class="bookcover">${spine}<img src="${b.cover}" alt="" loading="lazy"></div>`;
  return `<div class="bookcover" style="background:linear-gradient(160deg, oklch(40% .07 ${b.hue}), oklch(25% .06 ${b.hue}))">${spine}
    <div class="gen"><div class="rule"></div><div class="t">${b.title}</div><div class="a">${b.author}</div></div></div>`;
}
document.getElementById("nav").innerHTML=CATS.map(c=>`<a href="#${catId(c)}">${c}</a>`).join("");
document.getElementById("q").addEventListener("input",e=>{q=e.target.value.trim().toLowerCase();draw()});
function match(b){const hay=(b.title+b.author+b.category+(b.tags||[]).join(" ")).toLowerCase();return !q||hay.includes(q)}
function draw(){
  const shelves=document.getElementById("shelves");
  const list=BOOKS.filter(match);
  shelves.innerHTML="";
  if(!list.length){shelves.innerHTML='<div class="empty">이 검색어에 맞는 책이 서가에 없습니다.</div>';return}
  const groups={};
  list.forEach(b=>{(groups[b.main_cat]=groups[b.main_cat]||[]).push(b)});
  CATS.filter(c=>groups[c]).forEach(c=>{
    const sec=document.createElement("section");sec.className="shelfsec";sec.id=catId(c);
    sec.innerHTML=`<div class="shelfhead"><h2>${c}</h2><span class="cnt">${groups[c].length}권</span></div>`;
    const wrap=document.createElement("div");wrap.className="shelfwrap";
    const row=document.createElement("div");row.className="row";
    groups[c].forEach(b=>{
      const el=document.createElement("button");el.className="slot";el.title=b.title+" · "+b.author;
      el.innerHTML=coverHTML(b);
      el.onclick=()=>open(b);row.appendChild(el);
    });
    wrap.appendChild(row);
    wrap.insertAdjacentHTML("beforeend",'<div class="shelfbar"></div>');
    sec.appendChild(wrap);shelves.appendChild(sec);
  });
}
function open(b){
  document.getElementById("dwrap").innerHTML=coverHTML(b)+`
    <div class="dtxt">
      <div class="chips">
        <span class="chip" style="background:oklch(90% .05 ${b.hue});color:oklch(35% .09 ${b.hue})">${b.category}</span>
        <span class="chip" style="background:oklch(92% .02 75);color:oklch(40% .02 50)">${b.reliability}</span>
      </div>
      <h2>${b.full_title||b.title}</h2>
      <div class="who">${b.author} 지음 · ${b.era}</div>
      <div class="hr"></div>
      <p class="done">${b.one}</p>
      <div class="dbody">${b.html}</div>
    </div>`;
  dlg.showModal();dlg.scrollTop=0;
}
(function(){const f=BOOKS[FEAT];if(!f)return;
 document.getElementById("hero").innerHTML=coverHTML(f)+`
   <div class="txt"><div class="eyebrow">오늘의 책</div>
   <h1>${f.title}</h1><div class="who">${f.author} 지음 · ${f.category}</div>
   <div class="one">${f.one}</div><button id="fopen">이 책의 카드 열기</button></div>`;
 document.getElementById("fopen").onclick=()=>open(f);
})();
draw();
</script>
</body>
</html>""".replace("__DATA__", data).replace("__CATS__", json.dumps(cats, ensure_ascii=False)).replace("__N__", str(n)).replace("__C__", str(covers_n)).replace("__FEAT__", str(feat_i))

if __name__ == "__main__":
    books = load_books()
    out = render(books)
    for name in ("library.html", "index.html"):
        with open(os.path.join(ROOT, name), "w", encoding="utf-8") as f:
            f.write(out)
    print(f"library.html + index.html 생성 완료 — {len(books)}권 (실물 표지 {sum(1 for b in books if b['cover'])}권)")
