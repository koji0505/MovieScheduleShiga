let movieIndex = null;

// theaters[館名][映画] → movieIndex[タイトル][館名] に再編成
function buildMovieIndex(data) {
  const index = {};
  for (const [theaterName, movies] of Object.entries(data.theaters)) {
    for (const movie of movies) {
      if (!index[movie.title]) {
        index[movie.title] = { movie_id: movie.movie_id, theaters: {} };
      }
      index[movie.title].theaters[theaterName] = movie.schedule;
    }
  }
  return index;
}

function formatDate(dateStr) {
  const d = new Date(dateStr + "T00:00:00");
  const days = ["日", "月", "火", "水", "木", "金", "土"];
  return `${d.getMonth() + 1}/${d.getDate()}(${days[d.getDay()]})`;
}

function render(query) {
  const results = document.getElementById("results");
  if (!movieIndex) return;

  const q = query.trim();
  const entries = Object.entries(movieIndex).filter(([title]) =>
    q === "" || title.includes(q)
  );

  if (entries.length === 0) {
    results.innerHTML = '<p class="no-results">該当する映画が見つかりません</p>';
    return;
  }

  results.innerHTML = entries
    .map(([title, info]) => {
      const theatersHtml = Object.entries(info.theaters)
        .map(([theaterName, schedule]) => {
          const scheduleHtml = schedule
            .map(
              (s) => `
              <div class="schedule-row">
                <span class="schedule-date">${formatDate(s.date)}</span>
                <span class="schedule-times">${s.times.join("\u2002")}</span>
              </div>`
            )
            .join("");
          return `
            <div class="theater-block">
              <div class="theater-name">${theaterName}</div>
              ${scheduleHtml}
            </div>`;
        })
        .join("");

      return `
        <div class="movie-card">
          <h2 class="movie-title">${title}</h2>
          ${theatersHtml}
        </div>`;
    })
    .join("");
}

async function loadData() {
  const resp = await fetch("data/schedules.json");
  const data = await resp.json();
  movieIndex = buildMovieIndex(data);

  if (data.updated_at) {
    const dt = new Date(data.updated_at);
    document.getElementById("updatedAt").textContent =
      `更新: ${dt.toLocaleString("ja-JP")}`;
  }

  render("");
}

document.getElementById("searchInput").addEventListener("input", (e) => {
  render(e.target.value);
});

loadData().catch(() => {
  document.getElementById("results").innerHTML =
    '<p class="error">データの読み込みに失敗しました</p>';
});
