let movieData = null;
let movieIndex = null;
let selectedDate = '';
let selectedTheater = '';

function buildMovieIndex(data) {
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

function buildMovieList(data) {
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

function getAvailableDates(data) {
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

function formatDate(dateStr) {
  const d = new Date(dateStr + 'T00:00:00');
  const days = ['日', '月', '火', '水', '木', '金', '土'];
  return `${d.getMonth() + 1}/${d.getDate()}(${days[d.getDay()]})`;
}

function showHome() {
  document.getElementById('homeView').hidden = false;
  document.getElementById('searchView').hidden = true;
}

function showSearch(title = '') {
  document.getElementById('homeView').hidden = true;
  document.getElementById('searchView').hidden = false;
  const input = document.getElementById('searchInput');
  input.value = title;
  render(title);
}

function renderHome() {
  if (!movieData) return;
  const movies = buildMovieList(movieData);
  const grid = document.getElementById('homeGrid');
  if (movies.length === 0) {
    grid.innerHTML = '<p class="no-results">上映中の映画がありません</p>';
    return;
  }
  grid.innerHTML = movies.map(movie => {
    const safeTitle = movie.title.replace(/\\/g, '\\\\').replace(/'/g, "\\'");
    const posterHtml = movie.poster_url
      ? `<img class="poster" src="${movie.poster_url}" alt="${movie.title}" loading="lazy">`
      : `<div class="poster-placeholder"></div>`;
    return `
      <div class="home-card" onclick="showSearch('${safeTitle}')">
        ${posterHtml}
        <div class="home-card-body">
          <div class="home-card-title">${movie.title}</div>
          <a class="detail-link" href="https://moviewalker.jp/mv${movie.movie_id}/" target="_blank" rel="noopener" onclick="event.stopPropagation()">詳細</a>
        </div>
      </div>`;
  }).join('');
}

function renderTheaterFilter(data) {
  const theaterNames = Object.keys(data.theaters);
  const sel = document.getElementById('theaterSelect');
  sel.innerHTML = '<option value="">すべての劇場</option>' +
    theaterNames.map(t => `<option value="${t}">${t}</option>`).join('');
  sel.addEventListener('change', () => {
    selectedTheater = sel.value;
    render(document.getElementById('searchInput').value);
  });
}

function renderDateFilter(dates) {
  const container = document.getElementById('dateFilter');
  container.innerHTML = ['', ...dates]
    .map(date => {
      const label = date === '' ? 'すべて' : formatDate(date);
      const active = date === selectedDate ? ' active' : '';
      return `<button class="date-btn${active}" data-date="${date}">${label}</button>`;
    })
    .join('');
  container.querySelectorAll('.date-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      selectedDate = btn.dataset.date;
      container.querySelectorAll('.date-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      render(document.getElementById('searchInput').value);
    });
  });
}

function render(query) {
  const results = document.getElementById('results');
  if (!movieIndex) return;
  const q = query.trim();

  const entries = Object.entries(movieIndex)
    .filter(([title]) => q === '' || title.includes(q))
    .map(([title, info]) => {
      const theaters = {};
      const theaterEntries = selectedTheater
        ? Object.entries(info.theaters).filter(([name]) => name === selectedTheater)
        : Object.entries(info.theaters);
      for (const [theaterName, schedule] of theaterEntries) {
        const filtered = selectedDate
          ? schedule.filter(s => s.date === selectedDate)
          : schedule;
        if (filtered.length > 0) theaters[theaterName] = filtered;
      }
      return { title, poster_url: info.poster_url || '', theaters };
    })
    .filter(({ theaters }) => Object.keys(theaters).length > 0);

  if (entries.length === 0) {
    results.innerHTML = '<p class="no-results">該当する映画が見つかりません</p>';
    return;
  }

  results.innerHTML = entries
    .map(({ title, poster_url, theaters }) => {
      const posterHtml = poster_url
        ? `<img class="card-poster" src="${poster_url}" alt="${title}" loading="lazy">`
        : `<div class="card-poster-placeholder"></div>`;
      const theatersHtml = Object.entries(theaters)
        .map(([theaterName, schedule]) => {
          const scheduleHtml = schedule
            .map(s => `
              <div class="schedule-row">
                <span class="schedule-date">${formatDate(s.date)}</span>
                <span class="schedule-times">${s.times.join('\u2002')}</span>
              </div>`)
            .join('');
          return `
            <div class="theater-block">
              <div class="theater-name">${theaterName}</div>
              ${scheduleHtml}
            </div>`;
        })
        .join('');

      return `
        <div class="movie-card">
          ${posterHtml}
          <div class="movie-card-body">
            <h2 class="movie-title">${title}</h2>
            ${theatersHtml}
          </div>
        </div>`;
    })
    .join('');
}

async function loadData() {
  const resp = await fetch('data/schedules.json');
  const data = await resp.json();
  movieData = data;
  movieIndex = buildMovieIndex(data);

  if (data.updated_at) {
    const formatted = new Date(data.updated_at).toLocaleString('ja-JP');
    document.getElementById('homeUpdatedAt').textContent = `更新: ${formatted}`;
    document.getElementById('updatedAt').textContent = `更新: ${formatted}`;
  }

  renderTheaterFilter(data);
  renderDateFilter(getAvailableDates(data));
  renderHome();
  render('');
}

document.getElementById('searchInput').addEventListener('input', e => {
  render(e.target.value);
});

loadData().catch(() => {
  document.getElementById('homeGrid').innerHTML = '<p class="error">データの読み込みに失敗しました</p>';
  document.getElementById('results').innerHTML = '<p class="error">データの読み込みに失敗しました</p>';
});
