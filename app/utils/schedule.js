const DAY_NAMES = ['日', '月', '火', '水', '木', '金', '土'];

// 'YYYY-MM-DD' → 'M/D(曜)'
export function formatDate(dateStr) {
  const d = new Date(dateStr + 'T00:00:00');
  return `${d.getMonth() + 1}/${d.getDate()}(${DAY_NAMES[d.getDay()]})`;
}

// theaters[館名][映画] → movieIndex[タイトル]{ movie_id, poster_url, theaters[館名][schedule] }
export function buildMovieIndex(data) {
  const index = {};
  for (const [theaterName, movies] of Object.entries(data.theaters)) {
    for (const movie of movies) {
      if (!index[movie.title]) {
        index[movie.title] = { movie_id: movie.movie_id, poster_url: movie.poster_url || '', theaters: {} };
      } else if (!index[movie.title].poster_url && movie.poster_url) {
        index[movie.title].poster_url = movie.poster_url;
      }
      index[movie.title].theaters[theaterName] = movie.schedule;
    }
  }
  return index;
}

// データ内に存在する日付を昇順で返す
export function getAvailableDates(data) {
  const dates = new Set();
  for (const movies of Object.values(data.theaters)) {
    for (const movie of movies) {
      for (const s of movie.schedule) {
        dates.add(s.date);
      }
    }
  }
  return [...dates].sort();
}

// theaters[館名][映画] → [{title, movie_id, poster_url}, ...]（重複なし・タイトル昇順）
export function buildMovieList(data) {
  const seen = {};
  for (const movies of Object.values(data.theaters)) {
    for (const movie of movies) {
      if (!seen[movie.title] || (!seen[movie.title].poster_url && movie.poster_url)) {
        seen[movie.title] = { title: movie.title, movie_id: movie.movie_id, poster_url: movie.poster_url || '' };
      }
    }
  }
  return Object.values(seen).sort((a, b) => a.title.localeCompare(b.title, 'ja'));
}

// タイトル・日付・劇場でフィルタした映画リストを返す
export function filterMovies(movieIndex, query, selectedDate, selectedTheater = '') {
  return Object.entries(movieIndex)
    .filter(([title]) => query === '' || title.includes(query))
    .map(([title, info]) => {
      const theaters = {};
      const entries = selectedTheater
        ? Object.entries(info.theaters).filter(([name]) => name === selectedTheater)
        : Object.entries(info.theaters);
      for (const [theaterName, schedule] of entries) {
        const filtered = selectedDate
          ? schedule.filter(s => s.date === selectedDate)
          : schedule;
        if (filtered.length > 0) theaters[theaterName] = filtered;
      }
      return { title, movie_id: info.movie_id, poster_url: info.poster_url || '', theaters };
    })
    .filter(({ theaters }) => Object.keys(theaters).length > 0);
}
