import requests
from bs4 import BeautifulSoup
import json
import re
import os
import shutil
from datetime import datetime

THEATERS = {
    "ユナイテッド・シネマ大津": "th524",
    "イオンシネマ草津":         "th249",
    "イオンシネマ近江八幡":     "th393",
    "水口アレックスシネマ":     "th525",
    "彦根ビバシティシネマ":     "th138",
}

BASE_URL = "https://press.moviewalker.jp/{}/schedule/"
POSTER_BASE_URL = "https://koji0505.github.io/MovieScheduleShiga/data/posters/"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


def parse_date_str(date_str: str, today: datetime) -> str:
    """'2/24' のような文字列を 'YYYY-MM-DD' に変換する"""
    m = re.match(r"(\d{1,2})/(\d{1,2})", date_str.strip())
    if not m:
        return ""
    month, day = int(m.group(1)), int(m.group(2))
    year = today.year
    # 月が現在より小さければ翌年
    if month < today.month:
        year += 1
    return f"{year}-{month:02d}-{day:02d}"


def scrape_theater(theater_name: str, theater_id: str, today: datetime) -> list:
    url = BASE_URL.format(theater_id)
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"  Error: {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    movies = []

    for article in soup.find_all("article"):
        h2 = article.find("h2")
        if not h2:
            continue
        title = h2.get_text(strip=True)

        # 映画ID取得
        link = article.find("a", href=re.compile(r"^/mv\d+/$"))
        movie_id = ""
        if link:
            m = re.search(r"/mv(\d+)/", link["href"])
            if m:
                movie_id = m.group(1)

        # ポスター画像URL取得（元URL）
        img_tag = article.find("img")
        original_poster_url = img_tag["src"] if img_tag and img_tag.get("src") else ""

        # スケジュール取得
        schedule = []
        time_table = article.find("div", class_="bl_screen_timeTable")
        if not time_table:
            continue

        for li in time_table.find_all("li"):
            date_div = li.find("div", class_=re.compile(r"\bdate\b"))
            if not date_div:
                continue

            # 最初のテキストノードが日付 ("2/24")
            raw_date = next(date_div.strings, "").strip()
            date_str = parse_date_str(raw_date, today)
            if not date_str:
                continue

            times = [
                a.get_text(strip=True)
                for a in li.find_all("a", class_="startTime")
            ]
            if times:
                schedule.append({"date": date_str, "times": times})

        if schedule:
            movies.append({
                "title": title,
                "movie_id": movie_id,
                "original_poster_url": original_poster_url,
                "schedule": schedule,
            })

    return movies


def download_posters(theaters: dict, poster_dir: str) -> dict:
    """ポスターをダウンロードして保存し、movie_id -> ローカルURLのマップを返す"""
    # 毎回ディレクトリを削除して再作成
    if os.path.exists(poster_dir):
        shutil.rmtree(poster_dir)
    os.makedirs(poster_dir)

    # 全館から movie_id -> original_poster_url を収集（重複排除）
    poster_map = {}
    for movies in theaters.values():
        for movie in movies:
            movie_id = movie.get("movie_id")
            url = movie.get("original_poster_url", "")
            if movie_id and url and movie_id not in poster_map:
                poster_map[movie_id] = url

    # ダウンロード
    saved = {}
    for movie_id, url in poster_map.items():
        try:
            resp = requests.get(url, headers=HEADERS, timeout=10)
            resp.raise_for_status()
            path = os.path.join(poster_dir, f"{movie_id}.jpg")
            with open(path, "wb") as f:
                f.write(resp.content)
            saved[movie_id] = f"{POSTER_BASE_URL}{movie_id}.jpg"
            print(f"  Poster saved: {movie_id}.jpg")
        except Exception as e:
            print(f"  Poster failed ({movie_id}): {e}")

    return saved


def main():
    today = datetime.now()
    result = {
        "updated_at": today.strftime("%Y-%m-%dT%H:%M:%S"),
        "theaters": {},
    }

    for name, tid in THEATERS.items():
        print(f"Scraping {name} ...")
        movies = scrape_theater(name, tid, today)
        result["theaters"][name] = movies
        print(f"  -> {len(movies)} 件")

    # ポスターをダウンロード
    poster_dir = os.path.join(
        os.path.dirname(__file__), "..", "docs", "data", "posters"
    )
    print("\nDownloading posters ...")
    saved_posters = download_posters(result["theaters"], poster_dir)
    print(f"  -> {len(saved_posters)} 件保存")

    # poster_url をGitHub PagesのURLに書き換え、一時フィールドを削除
    for movies in result["theaters"].values():
        for movie in movies:
            movie_id = movie.pop("movie_id", "")
            movie.pop("original_poster_url", "")
            movie["movie_id"] = movie_id
            movie["poster_url"] = saved_posters.get(movie_id, "")

    out_path = os.path.join(
        os.path.dirname(__file__), "..", "docs", "data", "schedules.json"
    )
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n保存完了: {out_path}")


if __name__ == "__main__":
    main()
