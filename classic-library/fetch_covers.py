#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_covers.py — 북커버 수집기
books/*.md의 책마다 Open Library(공개 도서 DB)에서 표지를 검색해
assets/covers/<slug>.jpg 로 내려받는다. 이미 받은 책은 건너뛴다.
실패한 책은 조용히 넘어가며, 뷰어가 타이포 표지로 대체한다.
사용: 저장소의 classic-library 폴더에서  python fetch_covers.py
"""
import os, re, glob, json, time, urllib.request, urllib.parse, sys
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = os.path.dirname(os.path.abspath(__file__))
BOOKS = os.path.join(ROOT, "books")
COVERS = os.path.join(ROOT, "assets", "covers")
UA = {"User-Agent": "sage-library-cover-fetcher (personal archive)"}

# 한국어 제목 → 영어 검색어 매핑 (Open Library는 영문 검색이 안정적)
KNOWN = {
    "논어": "Analects Confucius", "손자병법": "Art of War Sun Tzu",
    "군주론": "The Prince Machiavelli", "명상록": "Meditations Marcus Aurelius",
    "국가": "Republic Plato", "니코마코스 윤리학": "Nicomachean Ethics Aristotle",
    "국부론": "Wealth of Nations Adam Smith", "종의 기원": "On the Origin of Species Darwin",
    "월든": "Walden Thoreau", "목민심서": "Admonitions on Governing the People Chong Yagyong",
    "도덕경": "Tao Te Ching Laozi", "맹자": "Mencius", "사기 열전": "Records of the Grand Historian Sima Qian",
    "죄와 벌": "Crime and Punishment Dostoevsky", "햄릿": "Hamlet Shakespeare",
    "돈키호테": "Don Quixote Cervantes", "파우스트": "Faust Goethe", "팡세": "Pensees Pascal",
    "자유론": "On Liberty John Stuart Mill",
    "프로테스탄트 윤리와 자본주의 정신": "Protestant Ethic and the Spirit of Capitalism Weber",
    "대학·중용": "Great Learning Doctrine of the Mean", "장자": "Zhuangzi", "한비자": "Han Feizi",
    "채근담": "Caigentan", "삼국지연의": "Romance of the Three Kingdoms",
    "열하일기": "Jehol Diary Pak Chiwon", "징비록": "Book of Corrections Yu Songnyong",
    "난중일기": "Nanjung Ilgi War Diary Yi Sun-sin", "성학십도": "Ten Diagrams on Sage Learning Yi Hwang",
    "소크라테스의 변명": "Apology Plato", "정치학": "Politics Aristotle", "수사학": "Rhetoric Aristotle",
    "의무론": "De Officiis Cicero", "유토피아": "Utopia Thomas More", "수상록": "Essays Montaigne",
    "방법서설": "Discourse on Method Descartes", "리바이어던": "Leviathan Hobbes",
    "사회계약론": "Social Contract Rousseau", "에밀": "Emile Rousseau",
    "도덕감정론": "Theory of Moral Sentiments Adam Smith",
    "미국의 민주주의": "Democracy in America Tocqueville", "전쟁론": "On War Clausewitz",
    "자조론": "Self-Help Samuel Smiles", "프랭클린 자서전": "Autobiography of Benjamin Franklin",
    "군중심리": "The Crowd Gustave Le Bon", "꿈의 해석": "Interpretation of Dreams Freud",
    "유한계급론": "Theory of the Leisure Class Veblen", "위대한 개츠비": "The Great Gatsby Fitzgerald",
    "변신": "The Metamorphosis Kafka", "데미안": "Demian Hesse",
    "노인과 바다": "The Old Man and the Sea Hemingway", "어린 왕자": "The Little Prince",
    "1984": "1984 George Orwell", "동물농장": "Animal Farm Orwell", "이솝 우화": "Aesop's Fables",
    "그리스 로마 신화": "Bulfinch's Mythology", "플루타르코스 영웅전": "Plutarch's Lives",
    "역사": "Histories Herodotus", "펠로폰네소스 전쟁사": "History of the Peloponnesian War Thucydides",
    "갈리아 전기": "Gallic War Caesar", "일리아스": "Iliad Homer", "오디세이아": "Odyssey Homer",
    "신곡": "Divine Comedy Dante", "캔터베리 이야기": "Canterbury Tales Chaucer",
    "실낙원": "Paradise Lost Milton", "걸리버 여행기": "Gulliver's Travels Swift",
    "캉디드": "Candide Voltaire", "법의 정신": "Spirit of the Laws Montesquieu",
    "순수이성비판": "Critique of Pure Reason Kant", "연방주의자 논집": "Federalist Papers",
    "모비딕": "Moby Dick Melville", "전쟁과 평화": "War and Peace Tolstoy",
    "카라마조프 형제들": "Brothers Karamazov Dostoevsky", "미들마치": "Middlemarch George Eliot",
    "허클베리 핀의 모험": "Adventures of Huckleberry Finn", "선악의 저편": "Beyond Good and Evil Nietzsche",
    "우신예찬": "Praise of Folly Erasmus", "신기관": "Novum Organum Bacon", "에티카": "Ethics Spinoza",
}

def base_title(t):
    return re.split(r"[(（]", t)[0].strip()

def search_cover_id(query):
    url = "https://openlibrary.org/search.json?limit=5&q=" + urllib.parse.quote(query)
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.loads(r.read().decode("utf-8"))
    for doc in data.get("docs", []):
        if doc.get("cover_i"):
            return doc["cover_i"]
    return None

def download_cover(cover_id, dest):
    url = f"https://covers.openlibrary.org/b/id/{cover_id}-L.jpg"
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        blob = r.read()
    if len(blob) < 3000:  # 플레이스홀더/깨진 이미지 컷
        return False
    with open(dest, "wb") as f:
        f.write(blob)
    return True

def main():
    os.makedirs(COVERS, exist_ok=True)
    ok = skip = fail = 0
    for path in sorted(glob.glob(os.path.join(BOOKS, "*.md"))):
        text = open(path, encoding="utf-8").read()
        m_slug = re.search(r"^slug:\s*(.+)$", text, re.M)
        m_title = re.search(r"^title:\s*(.+)$", text, re.M)
        slug = (m_slug.group(1).strip() if m_slug
                else os.path.splitext(os.path.basename(path))[0])
        title = base_title(m_title.group(1).strip()) if m_title else slug
        dest = os.path.join(COVERS, f"{slug}.jpg")
        if os.path.exists(dest):
            skip += 1; continue
        query = KNOWN.get(title, title)
        try:
            cid = search_cover_id(query)
            if cid and download_cover(cid, dest):
                ok += 1; print(f"O {title}")
            else:
                fail += 1; print(f"X {title} (표지 없음 — 타이포 표지 사용)")
        except Exception as e:
            fail += 1; print(f"X {title} ({e})")
        time.sleep(1)  # 공개 API 예의
    print(f"\n완료: 신규 {ok} / 보유 {skip} / 미확보 {fail}")

if __name__ == "__main__":
    main()
