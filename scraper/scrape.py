import requests
from bs4 import BeautifulSoup
import json
import re
import os
import shutil
import unicodedata
from datetime import datetime, timedelta

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

# 直接スクレイピング対象の3館
AEON_THEATERS = {
    "イオンシネマ近江八幡": "oumihachiman",
    "イオンシネマ草津":     "kusatsu",
}
UNITED_THEATER_NAME = "ユナイテッド・シネマ大津"
AEON_BASE_URL = "https://theater.aeoncinema.com/theaters/{slug}/?date={date}"
UNITED_BASE_URL = "https://www.unitedcinemas.jp/otsu/daily.php?date={date}"
DIRECT_SCRAPE_DAYS = 10


def normalize_title(title: str) -> str:
    """タイトルを比較用に正規化（NFKC: 半角カナ→全角カナ等）"""
    return unicodedata.normalize("NFKC", title).strip()


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


def _parse_aeon_page(soup: BeautifulSoup, iso_date: str, movies_by_title: dict) -> bool:
    """イオンシネマの1日分HTMLをパース。映画があればTrueを返す。"""
    movie_divs = soup.find_all("div", class_="p-schedule__movie")
    if not movie_divs:
        return False

    for div in movie_divs:
        poster_link = div.find("a", class_="p-schedule__poster")
        poster_url = ""
        movie_url_id = ""
        if poster_link:
            href = poster_link.get("href", "")
            m = re.search(r"/movie/([^/]+)/", href)
            if m:
                movie_url_id = m.group(1)
            img = poster_link.find("img")
            if img:
                poster_url = img.get("src", "")

        for info_div in div.find_all("div", class_="p-schedule__information"):
            h2 = info_div.find("h2")
            if not h2:
                continue
            title = h2.get_text(strip=True)

            times = []
            for ticket in info_div.find_all("div", class_="p-schedule__ticket"):
                time_div = ticket.find("div", class_="p-schedule__time")
                if time_div:
                    span = time_div.find("span")
                    if span:
                        times.append(span.get_text(strip=True))
            if not times:
                continue

            movie_id = f"aeon_{movie_url_id}" if movie_url_id else ""
            if title not in movies_by_title:
                movies_by_title[title] = {
                    "title": title,
                    "movie_id": movie_id,
                    "original_poster_url": poster_url,
                    "schedule": {},
                }
            sched = movies_by_title[title]["schedule"]
            if iso_date not in sched:
                sched[iso_date] = times
            else:
                sched[iso_date] = sorted(set(sched[iso_date]) | set(times))
    return True


def scrape_aeon(theater_name: str, slug: str, today: datetime) -> list:
    """イオンシネマの直接スクレイピング（Playwright使用、最大DIRECT_SCRAPE_DAYS日分）"""
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

    movies_by_title: dict = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        pw_page = browser.new_page()

        for delta in range(DIRECT_SCRAPE_DAYS):
            date = today + timedelta(days=delta)
            date_str = date.strftime("%Y%m%d")
            iso_date = date.strftime("%Y-%m-%d")
            url = AEON_BASE_URL.format(slug=slug, date=date_str)

            try:
                pw_page.goto(url, timeout=30000)
                pw_page.wait_for_selector(".p-schedule__movie", timeout=10000)
            except PWTimeout:
                print(f"  Aeon {theater_name} {date_str}: no movies, stopping")
                break
            except Exception as e:
                print(f"  Aeon {theater_name} {date_str}: Error {e}")
                break

            soup = BeautifulSoup(pw_page.content(), "html.parser")
            if not _parse_aeon_page(soup, iso_date, movies_by_title):
                print(f"  Aeon {theater_name} {date_str}: no movies (empty), stopping")
                break

        browser.close()

    result = []
    for movie in movies_by_title.values():
        schedule_list = [{"date": d, "times": t} for d, t in sorted(movie["schedule"].items())]
        if schedule_list:
            result.append({
                "title": movie["title"],
                "movie_id": movie["movie_id"],
                "original_poster_url": movie["original_poster_url"],
                "schedule": schedule_list,
            })
    return result


def scrape_united(today: datetime) -> list:
    """ユナイテッドシネマ大津の直接スクレイピング（最大DIRECT_SCRAPE_DAYS日分）"""
    movies_by_title: dict = {}

    for delta in range(DIRECT_SCRAPE_DAYS):
        date = today + timedelta(days=delta)
        date_str = date.strftime("%Y-%m-%d")
        iso_date = date_str
        url = UNITED_BASE_URL.format(date=date_str)

        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            resp.raise_for_status()
        except requests.RequestException as e:
            print(f"  United {date_str}: Error {e}")
            break

        # resp.content を使い BeautifulSoup に文字コード検出を任せる（Shift-JIS対応）
        soup = BeautifulSoup(resp.content, "html.parser")
        daily_list = soup.find("ul", id="dailyList")
        if not daily_list:
            print(f"  United {date_str}: no dailyList, stopping")
            break

        movie_items = daily_list.find_all("li", recursive=False)
        if not movie_items:
            print(f"  United {date_str}: no movies, stopping")
            break

        for li in movie_items:
            title_span = li.find("span", class_="movieTitle")
            if not title_span:
                continue
            title_a = title_span.find("a")
            if not title_a:
                continue
            title = title_a.get_text(strip=True)

            film_id = ""
            m = re.search(r"film=(\d+)", title_a.get("href", ""))
            if m:
                film_id = f"uc_{m.group(1)}"

            times = [t.get_text(strip=True) for t in li.find_all("li", class_="startTime")]
            if not times:
                continue

            if title not in movies_by_title:
                movies_by_title[title] = {
                    "title": title,
                    "movie_id": film_id,
                    "original_poster_url": "",
                    "schedule": {},
                }
            sched = movies_by_title[title]["schedule"]
            if iso_date not in sched:
                sched[iso_date] = times
            else:
                sched[iso_date] = sorted(set(sched[iso_date]) | set(times))

    result = []
    for movie in movies_by_title.values():
        schedule_list = [{"date": d, "times": t} for d, t in sorted(movie["schedule"].items())]
        if schedule_list:
            result.append({
                "title": movie["title"],
                "movie_id": movie["movie_id"],
                "original_poster_url": movie["original_poster_url"],
                "schedule": schedule_list,
            })
    return result


def merge_direct_schedules(mw_movies: list, direct_movies: list) -> list:
    """直接スクレイピングのデータをMW取得データにマージ（MW未掲載分のみ補完）"""
    mw_by_norm = {normalize_title(m["title"]): m for m in mw_movies}

    for direct in direct_movies:
        norm = normalize_title(direct["title"])
        if norm not in mw_by_norm:
            # MW にない映画: そのまま追加
            mw_movies.append(direct)
        else:
            # MW にある映画: 不足している日付のみ追加
            mw_movie = mw_by_norm[norm]
            mw_dates = {s["date"] for s in mw_movie["schedule"]}
            for sched in direct["schedule"]:
                if sched["date"] not in mw_dates:
                    mw_movie["schedule"].append(sched)
            mw_movie["schedule"].sort(key=lambda s: s["date"])

    return mw_movies


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

    # 3館を直接スクレイピングし、MW未掲載分をマージ
    print("\n直接スクレイピング（補完用）...")
    for name, slug in AEON_THEATERS.items():
        print(f"Scraping {name} (direct) ...")
        direct = scrape_aeon(name, slug, today)
        print(f"  -> {len(direct)} 件取得")
        result["theaters"][name] = merge_direct_schedules(result["theaters"][name], direct)
        print(f"  -> マージ後 {len(result['theaters'][name])} 件")

    print(f"Scraping {UNITED_THEATER_NAME} (direct) ...")
    direct = scrape_united(today)
    print(f"  -> {len(direct)} 件取得")
    result["theaters"][UNITED_THEATER_NAME] = merge_direct_schedules(
        result["theaters"][UNITED_THEATER_NAME], direct
    )
    print(f"  -> マージ後 {len(result['theaters'][UNITED_THEATER_NAME])} 件")

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
