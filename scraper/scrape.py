import requests
from bs4 import BeautifulSoup
import json
import re
import os
import shutil
import unicodedata
from datetime import datetime, timedelta, timezone

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
ALEX_THEATER_NAME  = "水口アレックスシネマ"
AEON_API_URL      = "https://theater.aeoncinema.com/schedule/v2/data/{slug}/schedule.json"
AEON_POSTER_URL   = "https://www.aeoncinema.com/movie_images/{movie_id}/poster400x560.jpg"
UNITED_BASE_URL   = "https://www.unitedcinemas.jp/otsu/daily.php?date={date}"
ALEX_SCHEDULE_URL = "https://schedule.alex-cinemas.com/schedule/data/schedule.json"
ALEX_MOVIE_URL    = "https://schedule.alex-cinemas.com/schedule/data/{movie_id}/001/{date}.json"
DIRECT_SCRAPE_DAYS = 10


VARIANT_RE = re.compile(
    r'(?:'
    r'^\s*[\[［【][^\]］】]*(?:吹替|字幕)[^\]］】]*[\]］】]\s*'  # 先頭: [吹替] [字幕] 等
    r'|[\s　]*[（(][^）)]*(?:吹替|字幕)[^）)]*[）)]\s*$'          # 末尾: （吹替）（字幕）等
    r')'
)

def normalize_title(title: str) -> str:
    """タイトルを比較用に正規化（NFKC: 半角カナ→全角カナ等）"""
    return unicodedata.normalize("NFKC", title).strip()


def base_title(title: str) -> str:
    """吹替・字幕などのバリアントサフィックスを除き、スペースを正規化した基本タイトルを返す"""
    t = unicodedata.normalize("NFKC", title)
    t = VARIANT_RE.sub("", t)
    # 全角・半角スペースをすべて除去して比較
    t = re.sub(r'[\s　]+', '', t)
    return t.strip()


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


def scrape_aeon(theater_name: str, slug: str, today: datetime) -> list:
    """イオンシネマの直接スクレイピング（JSON API使用）"""
    JST = timezone(timedelta(hours=9))
    url = AEON_API_URL.format(slug=slug)
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"  Aeon {theater_name}: API error {e}")
        return []

    # 今日から DIRECT_SCRAPE_DAYS 日分の日付セット（YYYYMMDD形式）
    target_dates = {(today + timedelta(days=d)).strftime("%Y%m%d") for d in range(DIRECT_SCRAPE_DAYS)}

    movies_by_title: dict = {}
    for date_key, sessions_by_movie in data.items():
        if date_key not in target_dates:
            continue
        iso_date = f"{date_key[:4]}-{date_key[4:6]}-{date_key[6:]}"

        for sessions in sessions_by_movie.values():
            if not sessions:
                continue
            first = sessions[0]
            title = first.get("name", {}).get("ja", "")
            if not title:
                continue

            # ポスター用 MovieID
            movie_num_id = next(
                (p["value"] for p in first.get("additionalProperty", []) if p.get("name") == "MovieID"),
                ""
            )

            # 上映開始時刻: UTC → JST
            times = []
            for s in sessions:
                start_utc = s.get("startDate", "")
                if start_utc:
                    dt = datetime.fromisoformat(start_utc.replace("Z", "+00:00")).astimezone(JST)
                    times.append(dt.strftime("%H:%M"))
            if not times:
                continue

            movie_id = f"aeon_{movie_num_id}" if movie_num_id else ""
            poster_url = AEON_POSTER_URL.format(movie_id=movie_num_id) if movie_num_id else ""

            if title not in movies_by_title:
                movies_by_title[title] = {
                    "title": title,
                    "movie_id": movie_id,
                    "original_poster_url": poster_url,
                    "schedule": {},
                }
            sched = movies_by_title[title]["schedule"]
            if iso_date not in sched:
                sched[iso_date] = sorted(times)
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


def _parse_united_html(soup: BeautifulSoup, iso_date: str, movies_by_title: dict) -> bool:
    """ユナイテッドシネマの1日分HTMLをパース。映画があればTrueを返す。"""
    daily_list = soup.find("ul", id="dailyList")
    if not daily_list:
        return False
    movie_items = daily_list.find_all("li", recursive=False)
    if not movie_items:
        return False

    found = False
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

        found = True
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
    return found


def scrape_united(today: datetime) -> list:
    """ユナイテッドシネマ大津の直接スクレイピング（Playwright使用、最大DIRECT_SCRAPE_DAYS日分）"""
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

    movies_by_title: dict = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        pw_page = browser.new_page()

        for delta in range(DIRECT_SCRAPE_DAYS):
            date = today + timedelta(days=delta)
            date_str = date.strftime("%Y-%m-%d")
            iso_date = date_str
            url = UNITED_BASE_URL.format(date=date_str)

            try:
                pw_page.goto(url, timeout=30000)
                pw_page.wait_for_selector("#dailyList li", timeout=15000)
            except Exception as e:
                print(f"  United {date_str}: no movies or error: {e}")
                break

            soup = BeautifulSoup(pw_page.content(), "html.parser")
            if not _parse_united_html(soup, iso_date, movies_by_title):
                print(f"  United {date_str}: no movies, stopping")
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


def scrape_alex(theater_name: str, today: datetime) -> list:
    """アレックスシネマのスクレイピング（JSON API使用）"""
    target_dates = {(today + timedelta(days=d)).strftime("%Y%m%d") for d in range(DIRECT_SCRAPE_DAYS)}

    try:
        resp = requests.get(ALEX_SCHEDULE_URL, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        schedule_data = resp.json()
    except Exception as e:
        print(f"  Alex {theater_name}: schedule.json error {e}")
        return []

    result = []
    for movie_id, theaters in schedule_data.items():
        if "001" not in theaters:
            continue
        dates_in_range = {d: times for d, times in theaters["001"].items() if d in target_dates}
        if not dates_in_range:
            continue

        # タイトルを最初の日付の詳細JSONから取得
        first_date = sorted(dates_in_range.keys())[0]
        try:
            r = requests.get(ALEX_MOVIE_URL.format(movie_id=movie_id, date=first_date), headers=HEADERS, timeout=10)
            r.raise_for_status()
            detail = r.json()
        except Exception as e:
            print(f"  Alex movie {movie_id}: detail error {e}")
            continue

        title = ""
        for screens in detail.values():
            for screen_data in screens.values():
                title = screen_data.get("name", {}).get("ja", "")
                if title:
                    break
            if title:
                break
        if not title:
            continue

        schedule = []
        for date_str, times_dict in sorted(dates_in_range.items()):
            iso_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
            times = sorted(f"{t[:2]}:{t[2:]}" for t in times_dict.keys())
            if times:
                schedule.append({"date": iso_date, "times": times})

        if schedule:
            result.append({
                "title": title,
                "movie_id": f"alex_{movie_id}",
                "original_poster_url": "",
                "schedule": schedule,
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
    # base_title -> (movie_id, url) も収集（吹替/字幕バリアント間でポスター共有用）
    poster_map: dict = {}        # movie_id -> url
    base_to_movie: dict = {}     # base_title -> movie_id（ポスターあり）
    movie_to_base: dict = {}     # movie_id -> base_title

    for movies in theaters.values():
        for movie in movies:
            movie_id = movie.get("movie_id")
            url = movie.get("original_poster_url", "")
            title = movie.get("title", "")
            if not movie_id:
                continue
            bt = base_title(title)
            movie_to_base[movie_id] = bt
            if url and movie_id not in poster_map:
                poster_map[movie_id] = url
                if bt and bt not in base_to_movie:
                    base_to_movie[bt] = movie_id

    # ポスターURLがない映画を同じ base_title の別バリアントで補完
    for movies in theaters.values():
        for movie in movies:
            movie_id = movie.get("movie_id")
            if not movie_id or movie_id in poster_map:
                continue
            bt = movie_to_base.get(movie_id, "")
            if bt and bt in base_to_movie:
                poster_map[movie_id] = poster_map[base_to_movie[bt]]

    # ダウンロード（同じURLは1回だけ取得して共有）
    url_to_local: dict = {}  # url -> local URL
    saved = {}
    for movie_id, url in poster_map.items():
        if url in url_to_local:
            saved[movie_id] = url_to_local[url]
            continue
        try:
            resp = requests.get(url, headers=HEADERS, timeout=10)
            resp.raise_for_status()
            path = os.path.join(poster_dir, f"{movie_id}.jpg")
            with open(path, "wb") as f:
                f.write(resp.content)
            local_url = f"{POSTER_BASE_URL}{movie_id}.jpg"
            saved[movie_id] = local_url
            url_to_local[url] = local_url
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

    print(f"Scraping {ALEX_THEATER_NAME} (direct) ...")
    direct = scrape_alex(ALEX_THEATER_NAME, today)
    print(f"  -> {len(direct)} 件取得")
    result["theaters"][ALEX_THEATER_NAME] = merge_direct_schedules(
        result["theaters"][ALEX_THEATER_NAME], direct
    )
    print(f"  -> マージ後 {len(result['theaters'][ALEX_THEATER_NAME])} 件")

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
