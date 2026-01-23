let APP_DATA = null;
let STATE = {
  config: {},
  songs: [],
  displayLimit: 25,
};

const THEME_CONFIG = {
  original: { name: "Original", style: "original", mode: "dark" },
  light1: { name: "Light", style: "light1", mode: "light" },
  studio808: { name: "Studio 808", style: "808", mode: "dark" },
  muthur: { name: "Deep-Space CRT", style: "muthur", mode: "dark" },
  hyperneon: { name: "Hyper-Neon 2026", style: "hyperneon", mode: "dark" },
};

const VALID_THEMES = Object.keys(THEME_CONFIG);
const DEFAULT_THEME = "original";

const urlParams = new URLSearchParams(window.location.search);
const savedTheme =
  urlParams.get("theme") || localStorage.getItem("user-theme") || DEFAULT_THEME;

/**
 * Apply a theme by name. Updates both data-theme (light/dark) and data-style attributes.
 */
function applyTheme(themeName) {
  if (themeName === "original-dark") themeName = "original";
  const theme = THEME_CONFIG[themeName] || THEME_CONFIG[DEFAULT_THEME];
  document.documentElement.setAttribute("data-theme", theme.mode);
  document.documentElement.setAttribute("data-style", theme.style);
  if (STATE.config) {
    STATE.config.theme = themeName;
  }
}

if (VALID_THEMES.includes(savedTheme)) {
  applyTheme(savedTheme); // Sets data-theme and data-style immediately
}

// This initiates the JS-side of the fetch immediately upon script execution.
const APP_DATA_PROMISE = fetch("data.json")
  .then((response) => {
    if (!response.ok) throw new Error("Network response was not ok");
    return response.json();
  })
  .catch((error) => {
    console.error("Critical error loading data.json:", error);
    return null;
  });

// Configuration bounds for validation and UI generation
const CONFIG_BOUNDS = {
  ranking: {
    k_value: { min: 0, max: 50, step: 1 },
    p_exponent: { min: 0.0, max: 1.1, step: 0.01 },
    consensus_boost: { min: 0, max: 0.2, step: 0.01 },
    provocation_boost: { min: 0, max: 0.2, step: 0.01 },
    cluster_boost: { min: 0, max: 0.2, step: 0.01 },
    cluster_threshold: { min: 0, max: 100, step: 1 },
    rank1_bonus: { min: 1.0, max: 1.2, step: 0.005 },
    rank2_bonus: { min: 1.0, max: 1.2, step: 0.005 },
    rank3_bonus: { min: 1.0, max: 1.2, step: 0.005 },
  },
  source_weight: { min: 0.0, max: 1.5, step: 0.01 },
  shadow_rank: { min: 1.0, max: 100.0, step: 0.1 },
};

const VALID_DECAY_MODES = ["consensus", "conviction"];

const UI = {
  songList: document.getElementById("song-list"),
  loadMoreBtn: document.getElementById("load-more"),
  tuneContent: document.getElementById("tune-content"),
  statsContent: document.getElementById("stats-content"),
  reviewsContent: document.getElementById("reviews-content"),
  youtubeContent: document.getElementById("youtube-content"),
  downloadContent: document.getElementById("download-content"),
};

class MathFormula extends HTMLElement {
  connectedCallback() {
    const type = this.getAttribute("type");
    const formulas = {
      consensus: `<svg viewBox="0 0 100 40" style="width: 7em; height: auto;" xmlns="http://www.w3.org/2000/svg" fill="currentColor">
        <text x="0" y="25" font-family="serif" font-style="italic" font-size="16">W(r) =</text>
        <line x1="52" y1="20" x2="98" y2="20" stroke="currentColor" stroke-width="1.5"/>
        <text x="60" y="14" font-family="serif" font-size="12">1 + K</text>
        <text x="60" y="34" font-family="serif" font-size="12">r + K</text>
      </svg>`,
      conviction: `<svg viewBox="0 0 80 40" style="width: 5.5em; height: auto;" xmlns="http://www.w3.org/2000/svg" fill="currentColor">
        <text x="0" y="25" font-family="serif" font-style="italic" font-size="16">W(r) =</text>
        <line x1="52" y1="20" x2="78" y2="20" stroke="currentColor" stroke-width="1.5"/>
        <text x="60" y="14" font-family="serif" font-size="12">1</text>
        <text x="58" y="34" font-family="serif" font-size="12">r<tspan baseline-shift="super" font-size="8">P</tspan></text>
      </svg>`,
    };
    this.innerHTML = formulas[type] || "";
    this.style.display = "inline-flex";
    this.style.color = "var(--pico-color)";
  }
}

customElements.define("math-formula", MathFormula);

function escapeHtml(str) {
  if (!str) return "";
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

function debounce(func, wait) {
  let timeout;
  return (...args) => {
    clearTimeout(timeout);
    timeout = setTimeout(() => func.apply(this, args), wait);
  };
}

/**
 * Clamp a numeric value between min and max bounds.
 * Returns min if value is NaN (handles invalid URL parameters).
 */
function clamp(value, min, max) {
  if (isNaN(value)) return min;
  return Math.max(min, Math.min(max, value));
}

/**
 * Check if any ranking setting differs from defaults.
 * Returns true if ANY parameter is customized.
 */
function isRankingCustomized() {
  if (!APP_DATA || !STATE.config) return false;

  const defaults = APP_DATA.config;
  const current = STATE.config;
  const TOLERANCE = 0.0001;

  const rankingKeys = [
    "decay_mode",
    "k_value",
    "p_exponent",
    "consensus_boost",
    "provocation_boost",
    "cluster_boost",
    "cluster_threshold",
    "rank1_bonus",
    "rank2_bonus",
    "rank3_bonus",
  ];

  for (const key of rankingKeys) {
    if (key === "decay_mode") {
      if (current.ranking[key] !== defaults.ranking[key]) return true;
    } else {
      if (Math.abs(current.ranking[key] - defaults.ranking[key]) > TOLERANCE)
        return true;
    }
  }

  for (const srcKey of Object.keys(current.sources)) {
    const currentSrc = current.sources[srcKey];
    const defaultSrc = defaults.sources[srcKey];

    if (Math.abs(currentSrc.weight - defaultSrc.weight) > TOLERANCE)
      return true;

    if (
      currentSrc.type === "unranked" &&
      Math.abs(currentSrc.shadow_rank - defaultSrc.shadow_rank) > TOLERANCE
    ) {
      return true;
    }
  }

  return false;
}

/**
 * Update the Tune button to show "Tuned" with sliders icon when customized.
 * Also updates the modal title if the modal is open.
 */
function updateTuneButton() {
  const btn = document.getElementById("open-tune");
  if (!btn) return;

  const isCustomized = isRankingCustomized();
  const iconClass = isCustomized ? "tuned-badge-icon" : "tune-icon";
  const label = isCustomized ? "Tuned" : "Tune";

  btn.innerHTML = `<svg class="${iconClass}"><use href="#icon-sliders"></use></svg>${label}`;
  btn.classList.toggle("tuned", isCustomized);

  const modalTitle = document.querySelector("#modal-tune h3");
  const modalTitleText = document.getElementById("tune-modal-title-text");
  if (modalTitle && modalTitleText) {
    modalTitle.classList.toggle("tuned", isCustomized);
    modalTitleText.textContent = isCustomized
      ? "Tuned Ranking"
      : "Tune Ranking";
  }
}

/**
 * RANKING ENGINE
 * Direct scoring with anchor-rank decay functions.
 */
const RankingEngine = {
  getDecayValue(rank, config) {
    // Consensus: (1+K) / (rank+K)
    // Conviction: 1 / (rank^P)
    let val =
      config.decay_mode === "consensus"
        ? (1 + config.k_value) / (rank + config.k_value)
        : 1.0 / Math.pow(rank, config.p_exponent);

    const intRank = Math.floor(rank);
    if (intRank === 1) val *= config.rank1_bonus;
    else if (intRank === 2) val *= config.rank2_bonus;
    else if (intRank === 3) val *= config.rank3_bonus;

    return val;
  },

  compute(songs, config) {
    const rankedSongs = songs.map((song) => {
      let totalScore = 0;
      let ranks = [];
      let clustersSeen = new Set();
      let sourceDetails = [];

      song.sources.forEach((srcEntry) => {
        const srcCfg = config.sources[srcEntry.name];
        if (!srcCfg) return;

        const rank = srcEntry.uses_shadow_rank
          ? srcCfg.shadow_rank
          : srcEntry.rank;
        ranks.push(rank);

        if (rank <= config.ranking.cluster_threshold) {
          clustersSeen.add(srcCfg.cluster);
        }

        const contribution =
          this.getDecayValue(rank, config.ranking) * srcCfg.weight;
        totalScore += contribution;

        sourceDetails.push({
          name: srcEntry.name,
          rank,
          contribution,
          full_name: srcCfg.full_name || srcEntry.name,
        });
      });

      const c_mul =
        ranks.length > 0 && APP_DATA.lnMaxListCount > 0
          ? 1 +
            (config.ranking.consensus_boost * Math.log(ranks.length)) /
              APP_DATA.lnMaxListCount
          : 1.0;

      let p_mul = 1.0;
      if (ranks.length > 1) {
        const mean = ranks.reduce((a, b) => a + b) / ranks.length;
        // Population Standard Deviation (like np.std)
        const stdDev = Math.sqrt(
          ranks.map((x) => Math.pow(x - mean, 2)).reduce((a, b) => a + b) /
            ranks.length,
        );
        p_mul = 1 + config.ranking.provocation_boost * (stdDev / 100);
      }

      const cl_mul =
        clustersSeen.size > 0
          ? 1 + config.ranking.cluster_boost * (clustersSeen.size - 1)
          : 1.0;

      const finalScore = totalScore * c_mul * p_mul * cl_mul;
      const minRank = ranks.length > 0 ? Math.min(...ranks) : Infinity;

      return {
        ...song,
        finalScore,
        sourceDetails: sourceDetails.sort(
          (a, b) => b.contribution - a.contribution,
        ),
        stats: {
          totalScore,
          c_mul,
          p_mul,
          cl_mul,
          listCount: ranks.length,
          minRank,
        },
      };
    });

    const maxScore = Math.max(...rankedSongs.map((s) => s.finalScore)) || 1;
    return rankedSongs
      .map((s) => ({ ...s, normalizedScore: s.finalScore / maxScore }))
      .sort((a, b) => {
        // Tie-breaking order:
        // 1. Normalized score (descending)
        // 2. List count (descending - more sources is better)
        // 3. Min rank (ascending - lower rank is better)
        // 4. Song name (alphabetical)
        // 5. Artist name (alphabetical)
        const scoreA = Math.round(a.normalizedScore * 1e8);
        const scoreB = Math.round(b.normalizedScore * 1e8);
        if (scoreB !== scoreA) return scoreB - scoreA;

        if (b.stats.listCount !== a.stats.listCount) {
          return b.stats.listCount - a.stats.listCount;
        }

        const minRankA = Math.round(a.stats.minRank * 100);
        const minRankB = Math.round(b.stats.minRank * 100);
        if (minRankA !== minRankB) return minRankA - minRankB;

        const nameCompare = a.name
          .toLowerCase()
          .localeCompare(b.name.toLowerCase());
        if (nameCompare !== 0) return nameCompare;

        return a.artist.toLowerCase().localeCompare(b.artist.toLowerCase());
      })
      .map((s, i) => ({ ...s, rank: i + 1 }));
  },
};

// Expose for debugging
window.RankingEngine = RankingEngine;

/**
 * Sync application state from URL parameters.
 * Validates and clamps all values to their defined bounds.
 */
function syncStateFromURL(defaultConfig) {
  const params = new URLSearchParams(window.location.search);
  const config = JSON.parse(JSON.stringify(defaultConfig));

  if (params.has("theme")) {
    const theme = params.get("theme");
    config.theme = VALID_THEMES.includes(theme) ? theme : DEFAULT_THEME;
    applyTheme(config.theme);
  } else {
    config.theme = DEFAULT_THEME;
    applyTheme(DEFAULT_THEME);
  }

  if (params.has("n")) {
    const n = parseInt(params.get("n"));
    if (!isNaN(n) && n > 0) {
      STATE.displayLimit = Math.min(n, 10000);
    }
  }

  const rankingKeys = [
    "decay_mode",
    "k_value",
    "p_exponent",
    "consensus_boost",
    "provocation_boost",
    "cluster_boost",
    "cluster_threshold",
    "rank1_bonus",
    "rank2_bonus",
    "rank3_bonus",
  ];

  rankingKeys.forEach((key) => {
    if (params.has(key)) {
      if (key === "decay_mode") {
        const mode = params.get(key);
        config.ranking[key] = VALID_DECAY_MODES.includes(mode)
          ? mode
          : defaultConfig.ranking.decay_mode;
      } else {
        const value = parseFloat(params.get(key));
        const bounds = CONFIG_BOUNDS.ranking[key];
        config.ranking[key] = clamp(value, bounds.min, bounds.max);
      }
    }
  });

  Object.keys(config.sources).forEach((srcKey) => {
    const urlKey = srcKey.toLowerCase().replace(/[^a-z0-9]/g, "_");

    if (params.has(`w_${urlKey}`)) {
      const value = parseFloat(params.get(`w_${urlKey}`));
      config.sources[srcKey].weight = clamp(
        value,
        CONFIG_BOUNDS.source_weight.min,
        CONFIG_BOUNDS.source_weight.max,
      );
    }

    if (params.has(urlKey) && config.sources[srcKey].type === "unranked") {
      const value = parseFloat(params.get(urlKey));
      config.sources[srcKey].shadow_rank = clamp(
        value,
        CONFIG_BOUNDS.shadow_rank.min,
        CONFIG_BOUNDS.shadow_rank.max,
      );
    }
  });

  return config;
}

/**
 * Update URL with current configuration state.
 * Only writes parameters that differ from defaults.
 */
function updateURL(config) {
  const params = new URLSearchParams();
  const defaults = APP_DATA.config;

  const currentParams = new URLSearchParams(window.location.search);
  if (currentParams.has("tskbd")) {
    params.set("tskbd", "");
  }

  if (STATE.displayLimit !== 25) {
    params.set("n", STATE.displayLimit);
  }

  if (config.theme && config.theme !== DEFAULT_THEME) {
    params.set("theme", config.theme);
  }

  Object.entries(config.ranking).forEach(([k, v]) => {
    if (v !== defaults.ranking[k]) {
      params.set(k, v);
    }
  });

  Object.entries(config.sources).forEach(([srcKey, srcCfg]) => {
    const urlKey = srcKey.toLowerCase().replace(/[^a-z0-9]/g, "_");

    if (srcCfg.weight !== defaults.sources[srcKey].weight) {
      params.set(`w_${urlKey}`, srcCfg.weight.toFixed(2));
    }

    if (
      srcCfg.type === "unranked" &&
      srcCfg.shadow_rank !== defaults.sources[srcKey].shadow_rank
    ) {
      params.set(urlKey, srcCfg.shadow_rank);
    }
  });

  const queryString = params.toString();
  const newUrl = queryString
    ? `${window.location.pathname}?${queryString}`
    : window.location.pathname;
  window.history.replaceState({}, "", newUrl);
}

/**
 * Main render function. Recomputes rankings and updates the song list UI.
 */
function render() {
  STATE.songs = RankingEngine.compute(APP_DATA.songs, STATE.config);
  const visible = STATE.songs.slice(0, STATE.displayLimit);

  UI.songList.innerHTML = visible
    .map((song, idx) => {
      const youtubeId =
        song.media?.youtube?.video_id || song.media?.youtube?.music_id;

      const media = song.media || {};
      const links = [
        media.youtube?.video_id &&
          `<li><a href="https://www.youtube.com/watch?v=${media.youtube.video_id}" target="_blank"><svg><use href="#icon-youtube"></use></svg> YouTube</a></li>`,
        media.youtube?.music_id &&
          `<li><a href="https://music.youtube.com/watch?v=${media.youtube.music_id}" target="_blank"><svg><use href="#icon-ytmusic"></use></svg> YTM</a></li>`,
        media.spotify?.id &&
          `<li><a href="https://open.spotify.com/track/${media.spotify.id}" target="_blank"><svg><use href="#icon-spotify"></use></svg> Spotify</a></li>`,
        media.apple?.url &&
          `<li><a href="${media.apple.url}" target="_blank"><svg><use href="#icon-apple"></use></svg> Apple</a></li>`,
        media.bandcamp?.url &&
          `<li><a href="${media.bandcamp.url}" target="_blank"><svg><use href="#icon-bandcamp"></use></svg> Bandcamp</a></li>`,
        media.other?.url &&
          `<li><a href="${media.other.url}" target="_blank">Other</a></li>`,
      ].filter(Boolean);

      const videoHtml = youtubeId
        ? `<lite-youtube videoid="${youtubeId}" playlabel="Play ${escapeHtml(song.name)}"></lite-youtube>`
        : `<div class="video-placeholder" aria-label="No video available for ${escapeHtml(song.name)}">
             <svg><use href="#icon-disc"></use></svg>
             <span>Video unavailable</span>
           </div>`;

      const sourcesHtml = song.sources
        .map((s) => {
          const srcConfig = STATE.config.sources[s.name];
          if (!srcConfig) return "";

          const usesShadowRank = typeof srcConfig.shadow_rank !== "undefined";
          let displayName = escapeHtml(srcConfig.full_name || s.name);

          if (
            usesShadowRank &&
            s.name !== "NPR Top 25" &&
            s.name !== "NPR Top 125"
          ) {
            displayName = `${displayName} (Top ${srcConfig.song_count || 0})`;
          }

          const rankDisplay = usesShadowRank ? "" : `#${s.rank}`;
          return `<span>${displayName}${rankDisplay}</span>`;
        })
        .filter(Boolean)
        .join(" · ");

      const linksHtml =
        links.length > 0
          ? `<nav aria-label="Listen links"><ul>${links.join("")}</ul></nav>`
          : "";
      const genresHtml = song.genres
        ? `<h5 class="song-genres">${escapeHtml(song.genres)}</h5>`
        : "";

      return `
        <article class="song-card">
          <div class="song-card-layout">
            <aside class="rank-display">#${song.rank}</aside>
            <figure class="video-figure">${videoHtml}</figure>
            <div class="song-info">
              <header>
                <hgroup>
                  <h3>${escapeHtml(song.name)}</h3>
                  <h4>${escapeHtml(song.artist)}</h4>
                  ${genresHtml}
                </hgroup>
                <a href="#" onclick="showStats(${idx}); return false;" aria-label="View ranking details">ⓘ</a>
              </header>
              <div data-sources onclick="showReviews(${idx})" onkeydown="if(event.key === 'Enter') showReviews(${idx})" tabindex="0" aria-label="See reviews for ${escapeHtml(song.name)}" title="Click to see reviews">
                <small>${sourcesHtml}</small>
              </div>
              ${linksHtml}
            </div>
          </div>
        </article>
      `;
    })
    .join("");

  updateLoadMoreButton();
  updateTuneButton();
}

function updateLoadMoreButton() {
  const remaining = STATE.songs.length - STATE.displayLimit;
  if (remaining <= 0) {
    UI.loadMoreBtn.style.display = "none";
  } else {
    UI.loadMoreBtn.style.display = "inline-block";
    let nextStep = 75; // Initial 25 -> 100
    if (STATE.displayLimit === 100) nextStep = 100; // 100 -> 200
    if (STATE.displayLimit === 200) nextStep = 300; // 200 -> 500
    if (STATE.displayLimit >= 500) nextStep = remaining; // 500 -> All

    UI.loadMoreBtn.textContent =
      remaining > nextStep
        ? `Show More (${nextStep})`
        : `Show All (${remaining})`;
  }
}

async function init() {
  APP_DATA = await APP_DATA_PROMISE;
  if (!APP_DATA) return;

  const maxListCount = Math.max(
    ...APP_DATA.songs.map((s) => s.list_count || 0),
  );
  APP_DATA.lnMaxListCount = maxListCount > 1 ? Math.log(maxListCount) : 0;

  STATE.config = syncStateFromURL(APP_DATA.config);
  render();

  const totalSongsEl = document.getElementById("total-songs-count");
  if (totalSongsEl) totalSongsEl.textContent = APP_DATA.songs.length;

  populateSourcesTables();

  UI.loadMoreBtn.onclick = () => {
    if (STATE.displayLimit === 25) STATE.displayLimit = 100;
    else if (STATE.displayLimit === 100) STATE.displayLimit = 200;
    else if (STATE.displayLimit === 200) STATE.displayLimit = 500;
    else STATE.displayLimit = STATE.songs.length;
    updateURL(STATE.config);
    render();
  };

  const openTuneBtn = document.getElementById("open-tune");
  if (openTuneBtn) {
    openTuneBtn.onclick = () => {
      renderSettingsUI();
      document.getElementById("modal-tune").showModal();
      closeHamburgerMenu();
    };
  }

  document.getElementById("reset-defaults").onclick = () => {
    const currentTheme = STATE.config.theme;
    STATE.config = JSON.parse(JSON.stringify(APP_DATA.config));
    STATE.config.theme = currentTheme;
    renderSettingsUI();
    debouncedReRank();
  };

  document.addEventListener("click", (e) => {
    const closeButton = e.target.closest(".close-modal");
    if (closeButton) {
      const dialog = closeButton.closest("dialog");
      if (dialog) dialog.close();
    }
  });

  document.addEventListener("click", (e) => {
    const trigger = e.target.closest(".btt-trigger");
    if (trigger) {
      const modalBody = trigger.closest("article");
      const target = modalBody || window;
      target.scrollTo({ top: 0, behavior: "smooth" });
    }
  });

  const fixedBtt = document.getElementById("fixed-btt");
  window.addEventListener("scroll", () => {
    fixedBtt.classList.toggle("visible", window.scrollY > 800);
  });

  const openAboutMenu = document.getElementById("open-about-menu");
  if (openAboutMenu) {
    openAboutMenu.onclick = () => {
      document.getElementById("modal-about").showModal();
      closeHamburgerMenu();
    };
  }

  const openYouTubeMenu = document.getElementById("open-youtube-menu");
  if (openYouTubeMenu) {
    openYouTubeMenu.onclick = () => {
      renderYouTubeUI();
      document.getElementById("modal-youtube").showModal();
      closeHamburgerMenu();
    };
  }

  const openDownloadMenu = document.getElementById("open-download-menu");
  if (openDownloadMenu) {
    openDownloadMenu.onclick = () => {
      downloadState.downloaded = false;
      renderDownloadUI();
      document.getElementById("modal-download").showModal();
      closeHamburgerMenu();
    };
  }

  const hamburgerBtn = document.getElementById("hamburger-btn");
  const hamburgerMenu = document.getElementById("hamburger-menu");

  if (hamburgerBtn && hamburgerMenu) {
    hamburgerBtn.onclick = (e) => {
      e.stopPropagation();
      const isOpen = !hamburgerMenu.hidden;
      hamburgerMenu.hidden = isOpen;
      hamburgerBtn.setAttribute("aria-expanded", !isOpen);
    };

    document.addEventListener("click", (e) => {
      if (
        !hamburgerMenu.hidden &&
        !hamburgerMenu.contains(e.target) &&
        e.target !== hamburgerBtn
      ) {
        closeHamburgerMenu();
      }
    });

    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && !hamburgerMenu.hidden) {
        closeHamburgerMenu();
        hamburgerBtn.focus();
      }
    });
  }

  renderMenuThemeSelector();
}

function closeHamburgerMenu() {
  const hamburgerMenu = document.getElementById("hamburger-menu");
  const hamburgerBtn = document.getElementById("hamburger-btn");
  if (hamburgerMenu) hamburgerMenu.hidden = true;
  if (hamburgerBtn) hamburgerBtn.setAttribute("aria-expanded", "false");
}

function renderMenuThemeSelector() {
  const select = document.getElementById("menu-theme-select");
  if (!select) return;

  select.innerHTML = Object.entries(THEME_CONFIG)
    .map(
      ([key, config]) =>
        `<option value="${key}" ${STATE.config.theme === key ? "selected" : ""}>${config.name}</option>`,
    )
    .join("");

  select.onchange = (e) => {
    applyTheme(e.target.value);
    updateURL(STATE.config);
  };
}

const debouncedReRank = debounce(() => {
  updateURL(STATE.config);
  render();
}, 250);

function populateSourcesTables() {
  if (!APP_DATA?.config?.sources) return;

  const sources = APP_DATA.config.sources;
  const clusterMetadata = APP_DATA.config.cluster_metadata || {};

  const rankedSources = [];
  const unrankedSources = [];

  Object.entries(sources).forEach(([key, source]) => {
    const clusterMeta = clusterMetadata[source.cluster] || {};
    const sourceData = {
      key,
      name: source.full_name || key,
      url: source.url,
      song_count: source.song_count || 0,
      cluster: source.cluster || "Unknown",
      clusterEmoji: clusterMeta.emoji || "",
    };

    if (source.type === "ranked") {
      rankedSources.push(sourceData);
    } else if (source.type === "unranked") {
      unrankedSources.push(sourceData);
    }
  });

  const sortSources = (a, b) => {
    if (a.cluster !== b.cluster) return a.cluster.localeCompare(b.cluster);
    if (a.name !== b.name) return a.name.localeCompare(b.name);
    return b.song_count - a.song_count;
  };

  rankedSources.sort(sortSources);
  unrankedSources.sort(sortSources);

  function renderSourceRow(source) {
    return `<tr>
      <td>
        <abbr data-tooltip="${escapeHtml(source.cluster)}" data-placement="right" style="text-decoration: none; cursor: help;">${escapeHtml(source.clusterEmoji)}</abbr>
        <a href="${escapeHtml(source.url)}" target="_blank">${escapeHtml(source.name)}</a>
      </td>
      <td>${source.song_count}</td>
    </tr>`;
  }

  const rankedTable = document.getElementById("ranked-sources-table");
  if (rankedTable) {
    const tbody = rankedTable.querySelector("tbody");
    tbody.innerHTML =
      rankedSources.map(renderSourceRow).join("") ||
      '<tr><td colspan="2">No ranked sources found</td></tr>';
  }

  const unrankedTable = document.getElementById("unranked-sources-table");
  if (unrankedTable) {
    const tbody = unrankedTable.querySelector("tbody");
    tbody.innerHTML =
      unrankedSources.map(renderSourceRow).join("") ||
      '<tr><td colspan="2">No unranked sources found</td></tr>';
  }
}

init();

/**
 * Display the Reviews modal for a song.
 * Shows all sources with quotes and links to full reviews.
 */
window.showReviews = (idx) => {
  const song = STATE.songs[idx];
  if (!song) return;

  const html = song.sources
    .map((src) => {
      const srcConfig = STATE.config.sources[src.name];
      const displayName = srcConfig.full_name || src.name;
      const clusterId = srcConfig?.cluster;
      const clusterMeta = APP_DATA.config.cluster_metadata?.[clusterId];
      const clusterEmoji = clusterMeta?.emoji || "";
      const clusterName = clusterId || "Unknown Category";
      const rankVal = src.uses_shadow_rank ? srcConfig.shadow_rank : src.rank;
      const displayRank = src.uses_shadow_rank
        ? `<abbr data-tooltip="Shadow Rank (from Settings since source is unranked)" data-placement="top">👻 ${rankVal.toFixed(1)}</abbr>`
        : `#${rankVal}`;

      return `<article class="review-entry">
      <header style="display: flex; justify-content: space-between; align-items: baseline; gap: 1rem;">
        <hgroup style="flex: 1; margin-bottom: 0;">
          <h4 style="margin-bottom: 0.25rem;">${escapeHtml(displayName)}</h4>
          <h5 class="secondary">${escapeHtml(clusterEmoji)} ${escapeHtml(clusterName)}</h5>
        </hgroup>
        <kbd style="min-width: 3ch; text-align: center; flex-shrink: 0;">${displayRank}</kbd>
      </header>
      ${
        src.quote
          ? `<blockquote style="font-style: italic;">"${escapeHtml(src.quote)}"</blockquote>`
          : '<p style="font-style: italic;">No quote available</p>'
      }
      <footer style="text-align: right;">
        <a href="${escapeHtml(srcConfig.url)}" target="_blank" role="button" class="outline">Read Full Review</a>
      </footer>
    </article>`;
    })
    .join("");

  UI.reviewsContent.innerHTML = html;
  document.getElementById("modal-reviews").showModal();
};

/**
 * Display the Ranking Stats modal for a song.
 * Shows scoring breakdown, multipliers, and source contributions.
 */
window.showStats = (idx) => {
  const song = STATE.songs[idx];
  if (!song) return;

  document.getElementById("stats-title").textContent = "Ranking Details";
  const stats = song.stats;

  const sourceRows = song.sourceDetails
    .map((sd) => {
      const sourceCfg = STATE.config.sources[sd.name];
      const clusterId = sourceCfg?.cluster;
      const clusterMeta = APP_DATA.config.cluster_metadata?.[clusterId];
      const clusterEmoji = clusterMeta?.emoji || "";
      const clusterName = clusterId || "Unknown Category";
      const usesShadowRank =
        sourceCfg && typeof sourceCfg.shadow_rank !== "undefined";
      const displayRank = usesShadowRank
        ? `<small style="color: var(--pico-muted-color);"><abbr data-tooltip="Shadow Rank (from Settings since source is unranked)" data-placement="top">👻 ${sd.rank.toFixed(1)}</abbr></small>`
        : `<small style="color: var(--pico-muted-color);">#${sd.rank}</small>`;

      return `<tr>
      <td>
        <abbr data-tooltip="${escapeHtml(clusterName)}" data-placement="right" style="text-decoration: none; cursor: help;">${clusterEmoji}</abbr> ${escapeHtml(sd.name)} ${displayRank}
      </td>
      <td style="text-align: right;">
        <kbd style="font-weight: bold; min-width: 5ch; display: inline-block;">+${sd.contribution.toFixed(2)}</kbd>
      </td>
    </tr>`;
    })
    .join("");

  UI.statsContent.innerHTML = `
    <section>
      <h5>Scoring</h5>
      <figure>
        <table class="striped">
          <tbody>
            <tr><td>Normalized Score</td><td style="text-align: right;"><kbd style="background: var(--pico-primary-background); color: var(--pico-primary-inverse); font-weight: bold; min-width: 6ch; display: inline-block;">${song.normalizedScore.toFixed(4)}</kbd></td></tr>
            <tr><td>Raw Score</td><td style="text-align: right;"><kbd style="min-width: 6ch; display: inline-block;">${song.finalScore.toFixed(4)}</kbd></td></tr>
            <tr><td>Base Score</td><td style="text-align: right;"><kbd style="min-width: 6ch; display: inline-block;">${stats.totalScore.toFixed(4)}</kbd></td></tr>
            <tr><td>List Count</td><td style="text-align: right;"><kbd style="min-width: 2ch; display: inline-block;">${stats.listCount}</kbd></td></tr>
            <tr><td>Consensus Boost</td><td style="text-align: right;"><kbd style="min-width: 6.5ch; display: inline-block;">${((stats.c_mul - 1) * 100).toFixed(2)}%</kbd></td></tr>
            <tr><td>Provocation Boost</td><td style="text-align: right;"><kbd style="min-width: 6.5ch; display: inline-block;">${((stats.p_mul - 1) * 100).toFixed(2)}%</kbd></td></tr>
            <tr><td>Cluster Boost</td><td style="text-align: right;"><kbd style="min-width: 6.5ch; display: inline-block;">${((stats.cl_mul - 1) * 100).toFixed(2)}%</kbd></td></tr>
          </tbody>
        </table>
      </figure>
    </section>
    <section>
      <h5>Source Contributions</h5>
      <figure>
        <table class="striped">
          <thead><tr><th>Source</th><th style="text-align: right;">Contribution</th></tr></thead>
          <tbody>${sourceRows}</tbody>
        </table>
      </figure>
    </section>`;

  document.getElementById("modal-stats").showModal();
};

function renderYouTubeUI(count = 50, preference = "videos") {
  const modalSubtitle = document.querySelector(
    "#modal-youtube > article > header hgroup p",
  );
  if (modalSubtitle) {
    modalSubtitle.innerHTML = isRankingCustomized()
      ? `Play the top songs on YouTube with your <strong class="tuned-text"><svg class="tuned-badge-icon"><use href="#icon-sliders"></use></svg>tuned</strong> ranking`
      : "Play the top songs as an unnamed playlist on YouTube";
  }

  const songsToExport = STATE.songs.slice(0, count);
  const validSongs = [];
  const missingSongs = [];

  songsToExport.forEach((song) => {
    const id =
      preference === "audio"
        ? song.media?.youtube?.music_id || song.media?.youtube?.video_id
        : song.media?.youtube?.video_id || song.media?.youtube?.music_id;

    if (id) {
      validSongs.push(id);
    } else {
      missingSongs.push(song);
    }
  });

  const url = `https://www.youtube.com/watch_videos?video_ids=${validSongs.join(",")}`;
  const getBtnClass = (isActive) => (isActive ? "" : "outline secondary");

  // HTML Generation
  let html = `
        <fieldset>
            <legend>Media preference</legend>
            <div class="chip-group">
                <button class="${getBtnClass(preference === "videos")}" onclick="renderYouTubeUI(${count}, 'videos')">Music Videos</button>
                <button class="${getBtnClass(preference === "audio")}" onclick="renderYouTubeUI(${count}, 'audio')">Audio Only</button>
            </div>
        </fieldset>

        <fieldset>
            <legend>Songs to include</legend>
            <div class="chip-group">
                <button class="${getBtnClass(count === 10)}" onclick="renderYouTubeUI(10, '${preference}')">Top 10</button>
                <button class="${getBtnClass(count === 25)}" onclick="renderYouTubeUI(25, '${preference}')">Top 25</button>
                <button class="${getBtnClass(count === 50)}" onclick="renderYouTubeUI(50, '${preference}')">Top 50</button>
            </div>
        </fieldset>

        <p>
            Ready to play the top <strong>${validSongs.length}</strong> songs on YouTube
            ${
              missingSongs.length > 0
                ? `
                <br><small style="color: var(--pico-del-color);">⚠️ ${missingSongs.length} ${missingSongs.length === 1 ? "song" : "songs"} missing YouTube IDs will be skipped:</small>
                <ul style="font-size: 0.8em; margin-bottom: 0; color: var(--pico-del-color);">
                    ${missingSongs.map((s) => `<li>${escapeHtml(s.artist)} - ${escapeHtml(s.name)}</li>`).join("")}
                </ul>
            `
                : '<br><small style="color: var(--pico-ins-color);">✓ All requested songs are available</small>'
            }
        </p>
    `;

  if (UI.youtubeContent) {
    UI.youtubeContent.innerHTML = html;
  }

  const modal = document.getElementById("modal-youtube");
  if (modal) {
    const footer = modal.querySelector("footer");
    if (footer) {
      footer.innerHTML = `
        <a href="${url}" role="button" target="_blank" ${validSongs.length === 0 ? "disabled" : ""}>Listen on YouTube</a>
        <button class="secondary close-modal">Close</button>`;
    }
  }
}

window.renderYouTubeUI = renderYouTubeUI;

let downloadState = { downloaded: false };

function renderDownloadUI(count = 100) {
  const modalSubtitle = document.querySelector(
    "#modal-download > article > header hgroup p",
  );
  if (modalSubtitle) {
    modalSubtitle.innerHTML = isRankingCustomized()
      ? `Download the top songs with your <strong class="tuned-text"><svg class="tuned-badge-icon"><use href="#icon-sliders"></use></svg>tuned</strong> ranking as CSV`
      : "Download as CSV and import to the streaming service of your choice";
  }

  const songsToExport = STATE.songs.slice(0, count);
  const songsMissingIsrc = songsToExport.filter(
    (s) => !s.id || s.id.includes(":"),
  );
  const getBtnClass = (isActive) => (isActive ? "" : "outline secondary");
  const totalSongs = STATE.songs.length;

  // HTML Generation
  let html = `
        <fieldset>
            <legend>Songs to include</legend>
            <div class="chip-group">
                <button class="${getBtnClass(count === 25)}" onclick="renderDownloadUI(25)">Top 25</button>
                <button class="${getBtnClass(count === 100)}" onclick="renderDownloadUI(100)">Top 100</button>
                <button class="${getBtnClass(count === 200)}" onclick="renderDownloadUI(200)">Top 200</button>
                <button class="${getBtnClass(count === 500)}" onclick="renderDownloadUI(500)">Top 500</button>
                <button class="${getBtnClass(count === totalSongs)}" onclick="renderDownloadUI(${totalSongs})">All</button>
            </div>
        </fieldset>

        <p>
            Ready to download the top <strong>${songsToExport.length}</strong> songs as CSV file
            ${
              songsMissingIsrc.length > 0
                ? `
                <br><small style="color: var(--pico-del-color);">⚠️ ${songsMissingIsrc.length} ${songsMissingIsrc.length === 1 ? "song" : "songs"} missing ISRC codes (some import services may not find these):</small>
                <ul style="font-size: 0.8em; margin-bottom: 0; color: var(--pico-del-color);">
                    ${songsMissingIsrc.map((s) => `<li>${escapeHtml(s.artist)} - ${escapeHtml(s.name)}</li>`).join("")}
                </ul>
            `
                : '<br><small style="color: var(--pico-ins-color);">✓ All songs have ISRC codes</small>'
            }
        </p>
    `;

  if (UI.downloadContent) {
    UI.downloadContent.innerHTML = html;
  }

  const modal = document.getElementById("modal-download");
  if (modal) {
    const footer = modal.querySelector("footer");
    if (footer) {
      if (downloadState.downloaded) {
        footer.innerHTML = `
          <p style="margin-bottom: var(--pico-spacing);"><strong>Next step:</strong> Import your playlist to a streaming service</p>
          <div class="import-services-wrapper">
            <a href="https://soundiiz.com/transfer-playlist-and-favorites" role="button" class="outline" target="_blank">Import via Soundiiz</a>
            <a href="https://www.tunemymusic.com/transfer" role="button" class="outline" target="_blank">Import via TuneMyMusic</a>
          </div>
          <button onclick="downloadCSV(${count}); return false;">Download Again</button>
          <button class="secondary close-modal">Close</button>`;
      } else {
        footer.innerHTML = `
          <button onclick="downloadCSV(${count}); return false;">Download CSV</button>
          <button class="secondary close-modal">Close</button>`;
      }
    }
  }
}

function escapeCSVField(field) {
  if (field === null || field === undefined) return "";
  const str = String(field);
  if (
    str.includes(",") ||
    str.includes('"') ||
    str.includes("\n") ||
    str.includes("\r")
  ) {
    return '"' + str.replace(/"/g, '""') + '"';
  }
  return str;
}

function downloadCSV(count) {
  const songsToExport = STATE.songs.slice(0, count);
  const headers = [
    "title",
    "artist",
    "isrc",
    "spotify_id",
    "youtube_id",
    "youtube_music_id",
    "apple_music_url",
    "other_url",
  ];

  const rows = songsToExport.map((song) => {
    const isrc = song.id && !song.id.includes(":") ? song.id : "";
    return [
      escapeCSVField(song.name),
      escapeCSVField(song.artist),
      escapeCSVField(isrc),
      escapeCSVField(song.media?.spotify?.id || ""),
      escapeCSVField(song.media?.youtube?.video_id || ""),
      escapeCSVField(song.media?.youtube?.music_id || ""),
      escapeCSVField(song.media?.apple?.url || ""),
      escapeCSVField(song.media?.other?.url || ""),
    ].join(",");
  });

  const csvContent = [headers.join(","), ...rows].join("\n");
  const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.setAttribute("href", url);
  link.setAttribute("download", `consensus-best-songs-2025-top-${count}.csv`);
  link.style.display = "none";
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);

  downloadState.downloaded = true;
  renderDownloadUI(count);
}

window.renderDownloadUI = renderDownloadUI;
window.downloadCSV = downloadCSV;

/**
 * Render the Tune Ranking modal UI.
 * Generates sliders for ranking parameters, source weights, and shadow ranks.
 */
function renderSettingsUI() {
  const { ranking, sources } = STATE.config;
  const defaults = APP_DATA.config;
  updateTuneButton();

  let html = "";
  const isConsensus = ranking.decay_mode === "consensus";

  html += `<article class="tune-inner-article">
    <hgroup><h4>Ranking Parameters</h4></hgroup>
    <label>Decay Mode</label>
    <div class="grid" style="margin-bottom: 2rem;">
      <article class="mode-card ${isConsensus ? "active" : ""}" onclick="updateSetting('ranking', 'decay_mode', 'consensus')">
        <header><strong>🤝 Consensus</strong></header>
        <div class="formula-container"><math-formula type="consensus"></math-formula></div>
        <p style="margin-bottom: 0;"><small style="color: var(--pico-muted-color);">Rewards cultural record. Favors songs on more lists.</small></p>
      </article>
      <article class="mode-card ${!isConsensus ? "active" : ""}" onclick="updateSetting('ranking', 'decay_mode', 'conviction')">
        <header><strong>🔥 Conviction</strong></header>
        <div class="formula-container"><math-formula type="conviction"></math-formula></div>
        <p style="margin-bottom: 0;"><small style="color: var(--pico-muted-color);">Rewards obsession. Top ranks carry massive weight.</small></p>
      </article>
    </div>`;

  const createSlider = (
    category,
    key,
    label,
    isPercent = false,
    isBonus = false,
    helperText = "",
    sublabel = "",
  ) => {
    let bounds;
    if (category === "ranking") bounds = CONFIG_BOUNDS.ranking[key];
    else if (category === "source_weight") bounds = CONFIG_BOUNDS.source_weight;
    else bounds = CONFIG_BOUNDS.shadow_rank;

    const { min, max, step } = bounds;

    let currentVal, defaultVal;
    if (category === "ranking") {
      currentVal = ranking[key];
      defaultVal = defaults.ranking[key];
    } else if (category === "source_weight") {
      currentVal = sources[key].weight;
      defaultVal = defaults.sources[key].weight;
    } else {
      currentVal = sources[key].shadow_rank;
      defaultVal = defaults.sources[key].shadow_rank;
    }

    const isModified = Math.abs(currentVal - defaultVal) > 0.0001;
    let displayVal;
    let minWidth = "3.5rem";

    if (isBonus) {
      displayVal = ((currentVal - 1) * 100).toFixed(1) + "%";
    } else if (isPercent) {
      displayVal = Math.round(currentVal * 100) + "%";
    } else if (key === "k_value") {
      displayVal = Math.round(currentVal).toString();
      minWidth = "2rem";
    } else if (key === "cluster_threshold") {
      displayVal = Math.round(currentVal).toString();
      minWidth = "2.5rem";
    } else {
      displayVal = parseFloat(currentVal).toFixed(2);
    }

    const idBase = `setting-${category}-${key.replace(/[^a-zA-Z0-9]/g, "_")}`;

    return `<div style="margin-bottom: var(--pico-spacing);">
      <label id="label-${idBase}" class="${isModified ? "customized-label" : ""}" style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; margin-bottom: 0;">
        <span>${label}${sublabel ? `<small style="opacity: 0.6; font-size: 0.85em; margin-left: 0.25rem;">${sublabel}</small>` : ""}</span>
        <kbd id="val-${idBase}" style="font-size: 0.8rem; min-width: ${minWidth}; text-align: center;">${displayVal}</kbd>
        <input type="range" id="${idBase}" min="${min}" max="${max}" step="${step}" value="${currentVal}" style="width: 100%; margin-bottom: 0.25rem;" oninput="updateSetting('${category}', '${key}', this.value, '${idBase}', ${isPercent}, ${isBonus})">
      </label>
      ${helperText ? `<p id="helper-text-${key}" style="color: var(--pico-muted-color); font-size: 0.85em; margin-bottom: 0;">${helperText}</p>` : ""}
    </div>`;
  };

  function generateRankHelper(v10, v25, v50) {
    return `Rank #10 is worth <strong>${Math.round(v10 * 100)}%</strong> of #1<br>Rank #25 is worth <strong>${Math.round(v25 * 100)}%</strong> of #1<br>Rank #50 is worth <strong>${Math.round(v50 * 100)}%</strong> of #1`;
  }

  if (isConsensus) {
    const k = ranking.k_value;
    html += createSlider(
      "ranking",
      "k_value",
      "Smoothing Factor (K)",
      false,
      false,
      generateRankHelper(
        (1 + k) / (10 + k),
        (1 + k) / (25 + k),
        (1 + k) / (50 + k),
      ),
    );
  } else {
    const p = ranking.p_exponent;
    html += createSlider(
      "ranking",
      "p_exponent",
      "Power Law Steepness (P)",
      false,
      false,
      generateRankHelper(
        1.0 / Math.pow(10, p),
        1.0 / Math.pow(25, p),
        1.0 / Math.pow(50, p),
      ),
    );
  }

  html += createSlider(
    "ranking",
    "consensus_boost",
    "🤝 Consensus Boost",
    true,
    false,
    'Applies a logarithmic bonus based on how many different critics included the song. The slider percentage is the maximum boost (for the song on the most lists). This acts as a "cultural record" weight, ensuring that a song beloved by many critics outpaces a song that hit #1 on only one list.',
  );
  html += createSlider(
    "ranking",
    "provocation_boost",
    "⚡ Provocation Boost",
    true,
    false,
    'Rewards "bold" choices. This calculates the standard deviation of a song\'s ranks; songs that critics are divided on (e.g., ranked #1 by some and #80 by others) receive a higher bonus than songs everyone safely ranked in the middle.',
  );
  html += createSlider(
    "ranking",
    "cluster_boost",
    "🌍 Cluster Boost",
    true,
    false,
    "Rewards crossover between different categories of critics by giving a bonus for each additional category reached with a best rank under the Cluster Threshold.",
  );
  html += createSlider(
    "ranking",
    "cluster_threshold",
    "🎯 Cluster Threshold",
    false,
    false,
    "Defines the rank a song must achieve to count for the Cluster Boost.",
  );
  html += createSlider(
    "ranking",
    "rank1_bonus",
    "🥇 Rank 1 Bonus",
    false,
    true,
    'Provides a heavy point multiplier for the absolute top pick. This rewards the "Obsession" factor, ensuring a critic\'s singular favorite song carries significantly more weight than their #2.',
  );
  html += createSlider(
    "ranking",
    "rank2_bonus",
    "🥈 Rank 2 Bonus",
    false,
    true,
    'Adds a secondary bonus to the silver medalist. This maintains a distinct gap between the "Elite" top-two picks and the rest of the Top 10.',
  );
  html += createSlider(
    "ranking",
    "rank3_bonus",
    "🥉 Rank 3 Bonus",
    false,
    true,
    'A slight nudge for the third-place track. This completes the "Podium" effect, giving the top three picks a mathematical edge over the "Standard" ranks.',
  );

  html += "</article>";

  const clusterMetadata = APP_DATA.config.cluster_metadata || {};
  const sortedSources = Object.keys(sources).sort();
  const sourcesByCluster = {};

  sortedSources.forEach((srcKey) => {
    const clusterName = sources[srcKey].cluster || "Other";
    if (!sourcesByCluster[clusterName]) sourcesByCluster[clusterName] = [];
    sourcesByCluster[clusterName].push(srcKey);
  });

  html += `<article class="tune-inner-article">
    <hgroup>
      <h4>Source Weights</h4>
      <p>Fine-tune the individual influence of each publication. These sliders allow you to manually adjust the specific "gravity" a source has within the final consensus.</p>
    </hgroup>`;

  Object.keys(sourcesByCluster)
    .sort()
    .forEach((clusterName) => {
      const emoji = clusterMetadata[clusterName]?.emoji || "";
      const descriptor = clusterMetadata[clusterName]?.descriptor || "";

      html += "<fieldset>";
      html += `<legend>${emoji} ${clusterName}</legend>`;
      if (descriptor) {
        html += `<p><small style="color: var(--pico-muted-color); display: block; margin-bottom: 1rem;">${descriptor}</small></p>`;
      }

      sourcesByCluster[clusterName].forEach((srcKey) => {
        html += createSlider("source_weight", srcKey, srcKey);
      });
      html += "</fieldset>";
    });
  html += "</article>";

  const unrankedSources = sortedSources.filter(
    (k) => sources[k].type === "unranked",
  );
  if (unrankedSources.length > 0) {
    html += `<article class="tune-inner-article">
      <hgroup>
        <h4>Shadow Ranks</h4>
        <p>Governs how the engine handles unranked review lists. These lists are assigned a "Shadow Rank" based on their total length. This ensures a song appearing on an unranked "Top 10" list correctly receives more weight than one on an unranked "Top 100" list.</p>
      </hgroup>`;
    unrankedSources.forEach((srcKey) => {
      const songCount = APP_DATA.config.sources[srcKey].song_count;
      html += createSlider(
        "source_shadow",
        srcKey,
        srcKey,
        false,
        false,
        "",
        `(${songCount} songs)`,
      );
    });
    html += "</article>";
  }

  UI.tuneContent.innerHTML = html;
}

window.updateSetting = (category, key, value, idBase, isPercent, isBonus) => {
  if (key === "decay_mode") {
    STATE.config.ranking.decay_mode = value;
    renderSettingsUI();
    debouncedReRank();
    return;
  }

  if (key === "theme") {
    applyTheme(value);
    debouncedReRank();
    return;
  }

  const numVal = parseFloat(value);
  const defaults = APP_DATA.config;
  let defaultVal;

  if (category === "ranking") {
    STATE.config.ranking[key] = numVal;
    defaultVal = defaults.ranking[key];
  } else if (category === "source_weight") {
    STATE.config.sources[key].weight = numVal;
    defaultVal = defaults.sources[key].weight;
  } else if (category === "source_shadow") {
    STATE.config.sources[key].shadow_rank = numVal;
    defaultVal = defaults.sources[key].shadow_rank;
  }

  if (idBase) {
    let displayVal;
    if (isBonus) {
      displayVal = ((numVal - 1) * 100).toFixed(1) + "%";
    } else if (isPercent) {
      displayVal = Math.round(numVal * 100) + "%";
    } else if (key === "k_value" || key === "cluster_threshold") {
      displayVal = Math.round(numVal).toString();
    } else {
      displayVal = parseFloat(numVal).toFixed(2);
    }
    document.getElementById(`val-${idBase}`).textContent = displayVal;

    const label = document.getElementById(`label-${idBase}`);
    label.classList.toggle(
      "customized-label",
      Math.abs(numVal - defaultVal) > 0.0001,
    );
  }

  if (key === "k_value" || key === "p_exponent") {
    const val = parseFloat(value);
    const v10 =
      key === "k_value" ? (1 + val) / (10 + val) : 1.0 / Math.pow(10, val);
    const v25 =
      key === "k_value" ? (1 + val) / (25 + val) : 1.0 / Math.pow(25, val);
    const v50 =
      key === "k_value" ? (1 + val) / (50 + val) : 1.0 / Math.pow(50, val);

    const helperEl = document.getElementById(`helper-text-${key}`);
    if (helperEl) {
      helperEl.innerHTML = `Rank #10 is worth <strong>${Math.round(v10 * 100)}%</strong> of #1<br>Rank #25 is worth <strong>${Math.round(v25 * 100)}%</strong> of #1<br>Rank #50 is worth <strong>${Math.round(v50 * 100)}%</strong> of #1`;
    }
  }

  debouncedReRank();
};

(function initThemeCycler() {
  const themes = Object.keys(THEME_CONFIG);
  let currentIndex = Math.max(
    0,
    themes.indexOf(STATE.config?.theme || "original"),
  );

  document.addEventListener("keydown", (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "t") {
      const params = new URLSearchParams(window.location.search);
      if (!params.has("tskbd")) return;

      event.preventDefault();
      currentIndex = (currentIndex + 1) % themes.length;
      const newTheme = themes[currentIndex];

      applyTheme(newTheme);
      updateURL(STATE.config);

      const menuThemeSelect = document.getElementById("menu-theme-select");
      if (menuThemeSelect) menuThemeSelect.value = newTheme;

      console.log(`Theme switched to: ${newTheme}`);
    }
  });
})();

// Keyboard navigation detection for focus styling
// Tracks actual keyboard usage to only show focus rings when user has pressed Tab
// This fixes iOS Safari treating autofocus as keyboard-like, showing unwanted focus rings
document.addEventListener("keydown", (e) => {
  if (e.key === "Tab") {
    document.body.classList.add("using-keyboard");
  }
});
document.addEventListener("mousedown", () => {
  document.body.classList.remove("using-keyboard");
});
document.addEventListener(
  "touchstart",
  () => {
    document.body.classList.remove("using-keyboard");
  },
  { passive: true },
);
