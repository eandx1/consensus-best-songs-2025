/**
 * APP STATE & CONSTANTS
 */

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

// Valid values for non-numeric parameters
const VALID_DECAY_MODES = ["consensus", "conviction"];
const DEFAULT_DECAY_MODE = "consensus"; // Safety fallback if data.json is invalid

const THEME_CONFIG = {
  original: { name: "Original", style: "original", mode: "dark" },
  light1: { name: "Light", style: "light1", mode: "light" },
  studio808: { name: "Studio 808", style: "808", mode: "dark" },
};

const VALID_THEMES = Object.keys(THEME_CONFIG);
const DEFAULT_THEME = "original";

let APP_DATA = null;
let STATE = {
  config: {}, // Current active configuration (weights, rankings, etc)
  songs: [], // The final ranked list
  displayLimit: 25,
};

const UI = {
  songList: document.getElementById("song-list"),
  loadMoreBtn: document.getElementById("load-more"),
  settingsContent: document.getElementById("settings-content"),
  statsContent: document.getElementById("stats-content"),
  reviewsContent: document.getElementById("reviews-content"),
  exportContent: document.getElementById("export-content"),
};

/**
 * MATH FORMULA WEB COMPONENT
 */
class MathFormula extends HTMLElement {
  connectedCallback() {
    const type = this.getAttribute("type");

    const formulas = {
      consensus: `
                <svg viewBox="0 0 100 40" style="width: 7em; height: auto;" xmlns="http://www.w3.org/2000/svg" fill="currentColor">
                    <text x="0" y="25" font-family="serif" font-style="italic" font-size="16">W(r) =</text>
                    <line x1="52" y1="20" x2="98" y2="20" stroke="currentColor" stroke-width="1.5"/>
                    <text x="60" y="14" font-family="serif" font-size="12">1 + K</text>
                    <text x="60" y="34" font-family="serif" font-size="12">r + K</text>
                </svg>`,
      conviction: `
                <svg viewBox="0 0 80 40" style="width: 5.5em; height: auto;" xmlns="http://www.w3.org/2000/svg" fill="currentColor">
                    <text x="0" y="25" font-family="serif" font-style="italic" font-size="16">W(r) =</text>
                    <line x1="52" y1="20" x2="78" y2="20" stroke="currentColor" stroke-width="1.5"/>
                    <text x="60" y="14" font-family="serif" font-size="12">1</text>
                    <text x="58" y="34" font-family="serif" font-size="12">r<tspan baseline-shift="super" font-size="8">P</tspan></text>
                </svg>`,
    };

    this.innerHTML = formulas[type] || "";
    this.style.display = "inline-flex";
    this.style.color = "var(--pico-color)"; // Force link to Pico's text color variable
  }
}

customElements.define("math-formula", MathFormula);

/**
 * UTILITIES
 */
const escapeHtml = (str) => {
  if (!str) return "";
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
};

const debounce = (func, wait) => {
  let timeout;
  return (...args) => {
    clearTimeout(timeout);
    timeout = setTimeout(() => func.apply(this, args), wait);
  };
};

/**
 * Clamp a numeric value between min and max bounds
 * Returns min if value is NaN (handles invalid URL parameters)
 */
const clamp = (value, min, max) => {
  // If value is NaN, return min as a safe default
  if (isNaN(value)) {
    return min;
  }
  return Math.max(min, Math.min(max, value));
};

/**
 * RANKING ENGINE (Ported from Python)
 * Direct scoring with anchor-rank decay functions.
 */
const RankingEngine = {
  getDecayValue(rank, config) {
    let val = 0;
    if (config.decay_mode === "consensus") {
      // (1+K) / (rank+K)
      val = (1 + config.k_value) / (rank + config.k_value);
    } else {
      // 1 / (rank^P)
      val = 1.0 / Math.pow(rank, config.p_exponent);
    }

    // Apply Top Rank Bonuses (for integer ranks only)
    const intRank = Math.floor(rank);
    if (intRank === 1) val *= 1 + config.rank1_bonus;
    else if (intRank === 2) val *= 1 + config.rank2_bonus;
    else if (intRank === 3) val *= 1 + config.rank3_bonus;

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

        // Direct Scoring: Decay * Weight (no normalization)
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

      // Multipliers
      const c_mul =
        ranks.length > 0
          ? 1 + config.ranking.consensus_boost * Math.log(ranks.length)
          : 1.0;

      let p_mul = 1.0;
      if (ranks.length > 1) {
        const mean = ranks.reduce((a, b) => a + b) / ranks.length;
        // Population Standard Deviation (like np.std)
        const stdDev = Math.sqrt(
          ranks.map((x) => Math.pow(x - mean, 2)).reduce((a, b) => a + b) /
            ranks.length
        );
        p_mul = 1 + config.ranking.provocation_boost * (stdDev / 100);
      }

      const cl_mul =
        clustersSeen.size > 0
          ? 1 + config.ranking.cluster_boost * (clustersSeen.size - 1)
          : 1.0;

      const finalScore = totalScore * c_mul * p_mul * cl_mul;

      return {
        ...song,
        finalScore,
        sourceDetails: sourceDetails.sort(
          (a, b) => b.contribution - a.contribution
        ),
        stats: { totalScore, c_mul, p_mul, cl_mul, listCount: ranks.length },
      };
    });

    // Normalize final scores to 0.0 - 1.0 range based on the top song
    const maxScore = Math.max(...rankedSongs.map((s) => s.finalScore)) || 1; // Prevent div by zero
    return rankedSongs
      .map((s) => ({ ...s, normalizedScore: s.finalScore / maxScore }))
      .sort((a, b) => b.finalScore - a.finalScore)
      .map((s, i) => ({ ...s, rank: i + 1 }));
  },
};

// Expose for debugging
window.RankingEngine = RankingEngine;

/**
 * THEME MANAGEMENT
 */
function applyTheme(themeName) {
  const html = document.documentElement;
  // Handle legacy theme name if present
  if (themeName === "original-dark") themeName = "original";

  const theme = THEME_CONFIG[themeName] || THEME_CONFIG[DEFAULT_THEME];

  html.setAttribute("data-theme", theme.mode);
  html.setAttribute("data-style", theme.style);

  if (STATE.config) STATE.config.theme = themeName;
}

/**
 * STATE SYNCING (URL <-> APP)
 */
function syncStateFromURL(defaultConfig) {
  const params = new URLSearchParams(window.location.search);
  const config = JSON.parse(JSON.stringify(defaultConfig));

  // Theme - validate against allowed themes
  if (params.has("theme")) {
    const theme = params.get("theme");
    config.theme = VALID_THEMES.includes(theme) ? theme : DEFAULT_THEME;
    applyTheme(config.theme);
  } else {
    config.theme = DEFAULT_THEME;
    applyTheme(DEFAULT_THEME);
  }

  // Display Limit (n parameter)
  if (params.has("n")) {
    const n = parseInt(params.get("n"));
    // Validate: must be a positive integer, clamp to reasonable range
    if (!isNaN(n) && n > 0) {
      STATE.displayLimit = Math.min(n, 10000); // Cap at 10000 for safety
    }
  }

  // Ranking Params
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
        // Validate decay mode against allowed values, fall back to data.json default
        const mode = params.get(key);
        config.ranking[key] = VALID_DECAY_MODES.includes(mode)
          ? mode
          : defaultConfig.ranking.decay_mode;
      } else {
        // Parse and clamp numeric values
        const value = parseFloat(params.get(key));
        const bounds = CONFIG_BOUNDS.ranking[key];
        config.ranking[key] = clamp(value, bounds.min, bounds.max);
      }
    }
  });

  // Source Weights & Shadows
  Object.keys(config.sources).forEach((srcKey) => {
    const urlKey = srcKey.toLowerCase().replace(/[^a-z0-9]/g, "_");

    // Weight
    if (params.has(`w_${urlKey}`)) {
      const value = parseFloat(params.get(`w_${urlKey}`));
      config.sources[srcKey].weight = clamp(
        value,
        CONFIG_BOUNDS.source_weight.min,
        CONFIG_BOUNDS.source_weight.max
      );
    }

    // Shadow Rank
    if (params.has(urlKey) && config.sources[srcKey].type === "unranked") {
      const value = parseFloat(params.get(urlKey));
      config.sources[srcKey].shadow_rank = clamp(
        value,
        CONFIG_BOUNDS.shadow_rank.min,
        CONFIG_BOUNDS.shadow_rank.max
      );
    }
  });

  return config;
}

function updateURL(config) {
  const params = new URLSearchParams();
  const defaults = APP_DATA.config;

  // Preserve existing tskbd parameter if present
  const currentParams = new URLSearchParams(window.location.search);
  if (currentParams.has("tskbd")) {
    params.set("tskbd", "");
  }

  // Display Limit (n parameter) - only include if not default (25)
  if (STATE.displayLimit !== 25) {
    params.set("n", STATE.displayLimit);
  }

  // Theme
  if (config.theme && config.theme !== DEFAULT_THEME) {
    params.set("theme", config.theme);
  }

  // Ranking Params
  Object.entries(config.ranking).forEach(([k, v]) => {
    if (v !== defaults.ranking[k]) {
      params.set(k, v);
    }
  });

  // Sources
  Object.entries(config.sources).forEach(([srcKey, srcCfg]) => {
    const urlKey = srcKey.toLowerCase().replace(/[^a-z0-9]/g, "_");

    // Weight
    if (srcCfg.weight !== defaults.sources[srcKey].weight) {
      params.set(`w_${urlKey}`, srcCfg.weight.toFixed(2));
    }

    // Shadow Rank
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
 * UI RENDERING
 */
function render() {
  STATE.songs = RankingEngine.compute(APP_DATA.songs, STATE.config);
  const visible = STATE.songs.slice(0, STATE.displayLimit);

  UI.songList.innerHTML = visible
    .map((song, idx) => {
      const youtubeId =
        song.media?.youtube?.video_id || song.media?.youtube?.music_id;

      // Listen Links as nav list items
      const links = [];
      if (song.media?.youtube?.video_id)
        links.push(
          `<li><a href="https://www.youtube.com/watch?v=${song.media.youtube.video_id}" target="_blank">YouTube</a></li>`
        );
      if (song.media?.youtube?.music_id)
        links.push(
          `<li><a href="https://music.youtube.com/watch?v=${song.media.youtube.music_id}" target="_blank">YTM</a></li>`
        );
      if (song.media?.spotify?.id)
        links.push(
          `<li><a href="https://open.spotify.com/track/${song.media.spotify.id}" target="_blank">Spotify</a></li>`
        );
      if (song.media?.apple?.url)
        links.push(
          `<li><a href="${song.media.apple.url}" target="_blank">Apple</a></li>`
        );
      if (song.media?.bandcamp?.url)
        links.push(
          `<li><a href="${song.media.bandcamp.url}" target="_blank">Bandcamp</a></li>`
        );
      if (song.media?.other?.url)
        links.push(
          `<li><a href="${song.media.other.url}" target="_blank">Other</a></li>`
        );

      return `
            <article class="song-card">
                <div class="song-card-layout">
                    <aside class="rank-display">#${song.rank}</aside>
                    
                    <figure class="video-figure">
                        <lite-youtube videoid="${youtubeId}" playlabel="Play ${escapeHtml(
        song.name
      )}"></lite-youtube>
                    </figure>
                    
                    <div class="song-info">
                        <header>
                            <hgroup>
                                <h3>${escapeHtml(song.name)}</h3>
                                <h4>${escapeHtml(song.artist)}</h4>
                                ${
                                  song.genres
                                    ? `<h5 class="song-genres">${escapeHtml(
                                        song.genres
                                      )}</h5>`
                                    : ""
                                }
                            </hgroup>
                            <a href="#" onclick="showStats(${idx}); return false;" aria-label="View ranking details">ⓘ</a>
                        </header>
                        
                        <div data-sources onclick="showReviews(${idx})" onkeydown="if(event.key === 'Enter') showReviews(${idx})" tabindex="0" aria-label="See reviews for ${escapeHtml(
        song.name
      )}" title="Click to see reviews">
                            <small>
                                ${song.sources
                                  .map((s) => {
                                    // Check if source uses shadow rank by looking at config
                                    const srcConfig =
                                      STATE.config.sources[s.name];
                                    if (!srcConfig) return "";

                                    const usesShadowRank =
                                      srcConfig &&
                                      typeof srcConfig.shadow_rank !==
                                        "undefined";

                                    // Build the display name
                                    let displayName = escapeHtml(
                                      srcConfig.full_name || s.name
                                    );

                                    // For shadow rank sources (except NPR lists), show "(Top N)"
                                    if (
                                      usesShadowRank &&
                                      s.name !== "NPR Top 25" &&
                                      s.name !== "NPR Top 125"
                                    ) {
                                      const songCount =
                                        srcConfig.song_count || 0;
                                      displayName = `${displayName} (Top ${songCount})`;
                                    }

                                    // Only show rank for sources with actual ranks, not shadow ranks
                                    const rankDisplay = usesShadowRank
                                      ? ""
                                      : `#${Math.floor(s.rank)}`;

                                    return `<span>${displayName}${rankDisplay}</span>`;
                                  })
                                  .filter(Boolean)
                                  .join(" · ")}
                            </small>
                        </div>
                        
                        ${
                          links.length > 0
                            ? `<nav aria-label="Listen links"><ul>${links.join(
                                ""
                              )}</ul></nav>`
                            : ""
                        }
                    </div>
                </div>
            </article>
        `;
    })
    .join("");

  updateLoadMoreButton();
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

/**
 * INITIALIZATION
 */
async function init() {
  const response = await fetch("data.json");
  APP_DATA = await response.json();
  STATE.config = syncStateFromURL(APP_DATA.config);
  render();

  // Update song count in About modal
  const totalSongsEl = document.getElementById("total-songs-count");
  if (totalSongsEl) {
    totalSongsEl.textContent = APP_DATA.songs.length;
  }

  // Populate sources tables in About modal
  populateSourcesTables();

  // Listen for "Load More"
  UI.loadMoreBtn.onclick = () => {
    if (STATE.displayLimit === 25) STATE.displayLimit = 100;
    else if (STATE.displayLimit === 100) STATE.displayLimit = 200;
    else if (STATE.displayLimit === 200) STATE.displayLimit = 500;
    else STATE.displayLimit = STATE.songs.length;
    updateURL(STATE.config); // Persist display limit to URL
    render();
  };

  // Modal triggers
  document.getElementById("open-settings").onclick = () => {
    renderSettingsUI();
    document.getElementById("modal-settings").showModal();
  };

  document.getElementById("reset-defaults").onclick = () => {
    const currentTheme = STATE.config.theme; // Preserve current theme
    STATE.config = JSON.parse(JSON.stringify(APP_DATA.config));
    STATE.config.theme = currentTheme; // Restore preserved theme
    renderSettingsUI();
    debouncedReRank();
  };

  // Close modal triggers
  document.querySelectorAll(".close-modal").forEach((btn) => {
    btn.onclick = function () {
      this.closest("dialog").close();
    };
  });

  // Back to top button handler
  document.addEventListener("click", (e) => {
    // Check if the clicked element or its parent has the 'btt-trigger' class
    const trigger = e.target.closest(".btt-trigger");
    if (trigger) {
      // Find the closest parent <article> (the scrollable part of the modal)
      const modalBody = trigger.closest("article");

      if (modalBody) {
        // Perform the scroll to the top of the modal
        modalBody.scrollTo({
          top: 0,
          behavior: "smooth",
        });
      } else {
        // If not in a modal, scroll to top of the page
        window.scrollTo({
          top: 0,
          behavior: "smooth",
        });
      }
    }
  });

  // About modal
  document.getElementById("open-about").onclick = () => {
    document.getElementById("modal-about").showModal();
  };

  // Export modal - only if feature flag is enabled
  const params = new URLSearchParams(window.location.search);
  const exportEnabled = params.has("unlisted_youtube_export");

  const exportLink = document.getElementById("open-export");
  if (exportEnabled && exportLink) {
    exportLink.style.display = ""; // Show the link by removing inline style
    exportLink.onclick = () => {
      renderExportUI();
      document.getElementById("modal-export").showModal();
    };
  }
}

const debouncedReRank = debounce(() => {
  updateURL(STATE.config);
  render();
}, 250);

/**
 * POPULATE SOURCES TABLES
 * Generates tables showing all ranked and unranked sources
 */
function populateSourcesTables() {
  if (!APP_DATA || !APP_DATA.config || !APP_DATA.config.sources) return;

  const sources = APP_DATA.config.sources;
  const clusterMetadata = APP_DATA.config.cluster_metadata || {};

  // Separate sources by type
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
      clusterDescriptor: clusterMeta.descriptor || "",
    };

    if (source.type === "ranked") {
      rankedSources.push(sourceData);
    } else if (source.type === "unranked") {
      unrankedSources.push(sourceData);
    }
  });

  // Sort by cluster name, then source name, then song_count
  const sortSources = (a, b) => {
    // First by cluster name
    if (a.cluster !== b.cluster) {
      return a.cluster.localeCompare(b.cluster);
    }
    // Then by source name
    if (a.name !== b.name) {
      return a.name.localeCompare(b.name);
    }
    // Finally by song count (descending)
    return b.song_count - a.song_count;
  };

  rankedSources.sort(sortSources);
  unrankedSources.sort(sortSources);

  // Populate ranked sources table
  const rankedTable = document.getElementById("ranked-sources-table");
  if (rankedTable) {
    const tbody = rankedTable.querySelector("tbody");
    const rows = rankedSources
      .map((source) => {
        const tooltipText = source.cluster;
        return `
            <tr>
                <td>
                    <abbr data-tooltip="${escapeHtml(
                      tooltipText
                    )}" data-placement="right" style="text-decoration: none; cursor: help;">${escapeHtml(
          source.clusterEmoji
        )}</abbr> <a href="${escapeHtml(
          source.url
        )}" target="_blank">${escapeHtml(source.name)}</a>
                </td>
                <td>${source.song_count}</td>
            </tr>
        `;
      })
      .join("");
    tbody.innerHTML =
      rows || '<tr><td colspan="2">No ranked sources found</td></tr>';
  }

  // Populate unranked sources table
  const unrankedTable = document.getElementById("unranked-sources-table");
  if (unrankedTable) {
    const tbody = unrankedTable.querySelector("tbody");
    const rows = unrankedSources
      .map((source) => {
        const tooltipText = source.cluster;
        return `
            <tr>
                <td>
                    <abbr data-tooltip="${escapeHtml(
                      tooltipText
                    )}" data-placement="right" style="text-decoration: none; cursor: help;">${escapeHtml(
          source.clusterEmoji
        )}</abbr> <a href="${escapeHtml(
          source.url
        )}" target="_blank">${escapeHtml(source.name)}</a>
                </td>
                <td>${source.song_count}</td>
            </tr>
        `;
      })
      .join("");
    tbody.innerHTML =
      rows || '<tr><td colspan="2">No unranked sources found</td></tr>';
  }
}

init();
// Reviews Modal
window.showReviews = (idx) => {
  const song = STATE.songs[idx];
  if (!song) return;

  let html = "";

  song.sources.forEach((src) => {
    const srcConfig = STATE.config.sources[src.name];
    const displayName = srcConfig.full_name || src.name;

    // Get cluster info
    const clusterId = srcConfig?.cluster;
    const clusterMeta = APP_DATA.config.cluster_metadata?.[clusterId];
    const clusterEmoji = clusterMeta?.emoji || "";
    const clusterName = clusterId || "Unknown Category";
    const clusterDesc = clusterMeta?.descriptor || "";

    // Use configured shadow rank if applicable, otherwise source rank
    const rankVal = src.uses_shadow_rank ? srcConfig.shadow_rank : src.rank;

    // Display rank with shadow rank notation if applicable (full decimal value with ghost emoji)
    const displayRank = src.uses_shadow_rank
      ? `<abbr data-tooltip="Shadow Rank (from Settings since source is unranked)" data-placement="left">👻 ${rankVal.toFixed(
          1
        )}</abbr>`
      : `#${rankVal}`;

    html += `
            <article class="review-entry">
                <header style="display: flex; justify-content: space-between; align-items: baseline; gap: 1rem;">
                    <hgroup style="flex: 1; margin-bottom: 0;">
                        <h4 style="margin-bottom: 0.25rem;">${escapeHtml(
                          displayName
                        )}</h4>
                        <h5 class="secondary">${escapeHtml(
                          clusterEmoji
                        )} ${escapeHtml(clusterName)}</h5>
                    </hgroup>
                    <kbd style="min-width: 3ch; text-align: center; flex-shrink: 0;">${displayRank}</kbd>
                </header>
                ${
                  src.quote
                    ? `<blockquote style="font-style: italic;">"${escapeHtml(
                        src.quote
                      )}"</blockquote>`
                    : '<p style="font-style: italic;">No quote available</p>'
                }
                <footer style="text-align: right;">
                    <a href="${escapeHtml(
                      srcConfig.url
                    )}" target="_blank" role="button" class="outline">Read Full Review</a>
                </footer>
            </article>
        `;
  });

  UI.reviewsContent.innerHTML = html;
  document.getElementById("modal-reviews").showModal();
};

// Ranking Stats Modal
window.showStats = (idx) => {
  const song = STATE.songs[idx];
  if (!song) return;

  document.getElementById("stats-title").textContent = "Ranking Details";

  const stats = song.stats;

  let html = `
        <section>
            <h5>Scoring</h5>
            <figure>
                <table class="striped">
                    <tbody>
                        <tr>
                            <td>Normalized Score</td>
                            <td style="text-align: right;">
                                <kbd style="background: var(--pico-primary-background); color: var(--pico-primary-inverse); font-weight: bold; min-width: 6ch; display: inline-block;">
                                    ${song.normalizedScore.toFixed(4)}
                                </kbd>
                            </td>
                        </tr>
                        <tr>
                            <td>Raw Score</td>
                            <td style="text-align: right;">
                                <kbd style="min-width: 6ch; display: inline-block;">
                                    ${song.finalScore.toFixed(4)}
                                </kbd>
                            </td>
                        </tr>
                        <tr>
                            <td>Base Score</td>
                            <td style="text-align: right;">
                                <kbd style="min-width: 6ch; display: inline-block;">
                                    ${stats.totalScore.toFixed(4)}
                                </kbd>
                            </td>
                        </tr>
                        <tr>
                            <td>List Count</td>
                            <td style="text-align: right;">
                                <kbd style="min-width: 2ch; display: inline-block;">
                                    ${stats.listCount}
                                </kbd>
                            </td>
                        </tr>
                        <tr>
                            <td>Consensus Boost</td>
                            <td style="text-align: right;">
                                <kbd style="min-width: 6.5ch; display: inline-block;">
                                    ${((stats.c_mul - 1) * 100).toFixed(2)}%
                                </kbd>
                            </td>
                        </tr>
                        <tr>
                            <td>Provocation Boost</td>
                            <td style="text-align: right;">
                                <kbd style="min-width: 6.5ch; display: inline-block;">
                                    ${((stats.p_mul - 1) * 100).toFixed(2)}%
                                </kbd>
                            </td>
                        </tr>
                        <tr>
                            <td>Cluster Boost</td>
                            <td style="text-align: right;">
                                <kbd style="min-width: 6.5ch; display: inline-block;">
                                    ${((stats.cl_mul - 1) * 100).toFixed(2)}%
                                </kbd>
                            </td>
                        </tr>
                    </tbody>
                </table>
            </figure>
        </section>
        
        <section>
            <h5>Source Contributions</h5>
            <figure>
                <table class="striped">
                    <thead>
                        <tr>
                            <th>Source</th>
                            <th style="text-align: right;">Contribution</th>
                        </tr>
                    </thead>
                    <tbody>
    `;

  // sourceDetails is already sorted by contribution in RankingEngine
  song.sourceDetails.forEach((sd) => {
    const sourceCfg = STATE.config.sources[sd.name];
    const clusterId = sourceCfg?.cluster;
    const clusterMeta = APP_DATA.config.cluster_metadata?.[clusterId];

    // Access the cluster ID (which is the name)
    const clusterEmoji = clusterMeta?.emoji || "";
    const clusterName = clusterId || "Unknown Category"; // Use cluster ID as the name

    // Just use the category name for the tooltip (no descriptor)
    const tooltipText = escapeHtml(clusterName);

    // Check if source uses shadow rank
    const usesShadowRank =
      sourceCfg && typeof sourceCfg.shadow_rank !== "undefined";

    // Use the main source name (the key name)
    const displayName = sd.name;

    // Logic for Shadow Rank display (ghost emoji with space and full decimal value)
    const displayRank = usesShadowRank
      ? `<small style="color: var(--pico-muted-color);"><abbr data-tooltip="Shadow Rank (from Settings since source is unranked)" data-placement="top">👻 ${sd.rank.toFixed(
          1
        )}</abbr></small>`
      : `<small style="color: var(--pico-muted-color);">#${sd.rank}</small>`;

    html += `
            <tr>
                <td>
                    <abbr data-tooltip="${tooltipText}" data-placement="right" style="text-decoration: none; cursor: help;">${clusterEmoji}</abbr> ${escapeHtml(
      displayName
    )} ${displayRank}
                </td>
                <td style="text-align: right;">
                    <kbd style="font-weight: bold; min-width: 5ch; display: inline-block;">
                        +${sd.contribution.toFixed(2)}
                    </kbd>
                </td>
            </tr>
        `;
  });

  html += `
                    </tbody>
                </table>
            </figure>
        </section>
    `;

  UI.statsContent.innerHTML = html;
  document.getElementById("modal-stats").showModal();
};

/**
 * EXPORT UI
 */
function renderExportUI(limit = 25, preference = "videos") {
  const songsToExport = STATE.songs.slice(0, limit);
  const validSongs = [];
  const missingSongs = [];

  songsToExport.forEach((song) => {
    // Priority logic:
    // Videos preference: video_id > music_id (prefer official music videos)
    // Songs preference: music_id > video_id (prefer album audio)
    let id = null;
    if (preference === "songs") {
      id = song.media?.youtube?.music_id || song.media?.youtube?.video_id;
    } else {
      id = song.media?.youtube?.video_id || song.media?.youtube?.music_id;
    }

    if (id) {
      validSongs.push(id);
    } else {
      missingSongs.push(song);
    }
  });

  const url = `https://www.youtube.com/watch_videos?video_ids=${validSongs.join(
    ","
  )}`;

  // Helper to generate button classes
  const getBtnClass = (isActive) => (isActive ? "" : "outline secondary");

  const preferenceName = preference === "songs" ? "songs" : "videos";

  // HTML Generation
  let html = `
        <label>Preference</label>
        <div class="grid" style="margin-bottom: var(--pico-spacing);">
            <button class="${getBtnClass(
              preference === "videos"
            )}" onclick="renderExportUI(${limit}, 'videos')">
                Videos
            </button>
            <button class="${getBtnClass(
              preference === "songs"
            )}" onclick="renderExportUI(${limit}, 'songs')">
                Songs
            </button>
        </div>

        <label>Range</label>
        <div class="grid" style="margin-bottom: var(--pico-spacing);">
            <button class="${getBtnClass(
              limit === 10
            )}" onclick="renderExportUI(10, '${preference}')">Top 10</button>
            <button class="${getBtnClass(
              limit === 25
            )}" onclick="renderExportUI(25, '${preference}')">Top 25</button>
            <button class="${getBtnClass(
              limit === 50
            )}" onclick="renderExportUI(50, '${preference}')">Top 50</button>
        </div>

        <article style="background-color: var(--pico-card-background-color); margin-bottom: var(--pico-spacing);">
            <header><strong>Summary</strong></header>
            <p style="margin-bottom: ${
              missingSongs.length > 0 ? "0.5rem" : "0"
            }">
                Ready to export <strong>${
                  validSongs.length
                }</strong> ${preferenceName} to a new YouTube playlist.
            </p>
            ${
              missingSongs.length > 0
                ? `
                <div style="color: var(--pico-del-color); border-top: 1px solid var(--pico-muted-border-color); padding-top: 0.5rem; margin-top: 0.5rem;">
                    <small>⚠️ ${missingSongs.length} ${
                    missingSongs.length === 1 ? "song" : "songs"
                  } missing IDs will be skipped:</small>
                    <ul style="font-size: 0.8em; margin-bottom: 0;">
                        ${missingSongs
                          .map(
                            (s) =>
                              `<li>#${s.rank} ${escapeHtml(
                                s.artist
                              )} - ${escapeHtml(s.name)}</li>`
                          )
                          .join("")}
                    </ul>
                </div>
            `
                : '<small style="color: var(--pico-ins-color);">✓ All requested songs are available.</small>'
            }
        </article>
        
        <p><small>Note: You will be redirected to YouTube where you can name and save your playlist.</small></p>
    `;

  // Inject into content
  if (UI.exportContent) {
    UI.exportContent.innerHTML = html;
  }

  // Update Footer
  const modal = document.getElementById("modal-export");
  if (modal) {
    const footer = modal.querySelector("footer");
    if (footer) {
      footer.innerHTML = `
                <button class="secondary outline btt-trigger">Back to top</button>
                <a href="${url}" role="button" target="_blank" ${
        validSongs.length === 0 ? "disabled" : ""
      }>Create Playlist</a>
                <button class="secondary" onclick="document.getElementById('modal-export').close()">Close</button>
            `;
    }
  }
}

// Expose to window
window.renderExportUI = renderExportUI;

/**
 * SETTINGS UI
 */
function renderSettingsUI() {
  const { ranking, sources } = STATE.config;
  const defaults = APP_DATA.config;

  let html = "";

  // 1. Ranking Parameters
  html += "<article>";
  html += "<hgroup>";
  html += "<h4>Ranking Parameters</h4>";
  html += "</hgroup>";

  // Decay Mode
  const isConsensus = ranking.decay_mode === "consensus";
  html += `
        <label>Decay Mode</label>
        <div class="grid" style="margin-bottom: 2rem;">
            <article class="mode-card ${
              isConsensus ? "active" : ""
            }" onclick="updateSetting('ranking', 'decay_mode', 'consensus')">
                <header>
                    <strong>🤝 Consensus</strong>
                </header>
                
                <div class="formula-container">
                    <math-formula type="consensus"></math-formula>
                </div>

                <p style="margin-bottom: 0;">
                    <small style="color: var(--pico-muted-color);">
                        Rewards cultural record. Favors songs on more lists.
                    </small>
                </p>
            </article>
            
            <article class="mode-card ${
              !isConsensus ? "active" : ""
            }" onclick="updateSetting('ranking', 'decay_mode', 'conviction')">
                <header>
                    <strong>🔥 Conviction</strong>
                </header>
                
                <div class="formula-container">
                    <math-formula type="conviction"></math-formula>
                </div>

                <p style="margin-bottom: 0;">
                    <small style="color: var(--pico-muted-color);">
                        Rewards obsession. Top ranks carry massive weight.
                    </small>
                </p>
            </article>
        </div>
    `;

  // Sliders Helper
  const createSlider = (
    category,
    key,
    label,
    isPercent = false,
    isBonus = false,
    helperText = "",
    sublabel = ""
  ) => {
    // Get bounds from CONFIG_BOUNDS
    let bounds;
    if (category === "ranking") {
      bounds = CONFIG_BOUNDS.ranking[key];
    } else if (category === "source_weight") {
      bounds = CONFIG_BOUNDS.source_weight;
    } else if (category === "source_shadow") {
      bounds = CONFIG_BOUNDS.shadow_rank;
    }

    const { min, max, step } = bounds;

    let currentVal =
      category === "ranking"
        ? ranking[key]
        : category === "source_weight"
        ? sources[key].weight
        : sources[key].shadow_rank;
    let defaultVal =
      category === "ranking"
        ? defaults.ranking[key]
        : category === "source_weight"
        ? defaults.sources[key].weight
        : defaults.sources[key].shadow_rank;

    // Approximate equality check for floating point values (within 0.0001)
    const isModified = Math.abs(currentVal - defaultVal) > 0.0001;
    // Bonus values are stored as multipliers (1.1 = 10% bonus), so subtract 1 and multiply by 100 for display
    let displayVal;
    let minWidth = "3.5rem"; // default for decimals

    if (isBonus) {
      displayVal = ((currentVal - 1) * 100).toFixed(1) + "%";
    } else if (isPercent) {
      displayVal = Math.round(currentVal * 100) + "%";
    } else if (key === "k_value") {
      displayVal = Math.round(currentVal).toString();
      minWidth = "2rem"; // 2 digits
    } else if (key === "cluster_threshold") {
      displayVal = Math.round(currentVal).toString();
      minWidth = "2.5rem"; // 3 digits
    } else {
      displayVal = parseFloat(currentVal).toFixed(2);
    }

    const idBase = `setting-${category}-${key.replace(/[^a-zA-Z0-9]/g, "_")}`;
    const helperId = `helper-text-${key}`;

    return `
            <div style="margin-bottom: var(--pico-spacing);">
                <label id="label-${idBase}" class="${
      isModified ? "customized-label" : ""
    }" style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; margin-bottom: 0;">
                <span>
                    ${label} 
                    ${
                      sublabel
                        ? `<small style="opacity: 0.6; font-size: 0.85em; margin-left: 0.25rem;">${sublabel}</small>`
                        : ""
                    }
                </span>
                    <kbd id="val-${idBase}" style="font-size: 0.8rem; min-width: ${minWidth}; text-align: center;">${displayVal}</kbd>
                    <input type="range" id="${idBase}" min="${min}" max="${max}" step="${step}" value="${currentVal}" 
                        style="width: 100%; margin-bottom: 0.25rem;"
                        oninput="updateSetting('${category}', '${key}', this.value, '${idBase}', ${isPercent}, ${isBonus})">
                </label>
                ${
                  helperText
                    ? `<p id="${helperId}" style="color: var(--pico-muted-color); font-size: 0.85em; margin-bottom: 0;">${helperText}</p>`
                    : ""
                }
            </div>
        `;
  };

  if (isConsensus) {
    const val10 = (1 + ranking.k_value) / (10 + ranking.k_value);
    const val25 = (1 + ranking.k_value) / (25 + ranking.k_value);
    const val50 = (1 + ranking.k_value) / (50 + ranking.k_value);
    const helper = `Rank #10 is worth <strong>${Math.round(
      val10 * 100
    )}%</strong> of #1<br>Rank #25 is worth <strong>${Math.round(
      val25 * 100
    )}%</strong> of #1<br>Rank #50 is worth <strong>${Math.round(
      val50 * 100
    )}%</strong> of #1`;
    html += createSlider(
      "ranking",
      "k_value",
      "Smoothing Factor (K)",
      false,
      false,
      helper
    );
  } else {
    const val10 = 1.0 / Math.pow(10, ranking.p_exponent);
    const val25 = 1.0 / Math.pow(25, ranking.p_exponent);
    const val50 = 1.0 / Math.pow(50, ranking.p_exponent);
    const helper = `Rank #10 is worth <strong>${Math.round(
      val10 * 100
    )}%</strong> of #1<br>Rank #25 is worth <strong>${Math.round(
      val25 * 100
    )}%</strong> of #1<br>Rank #50 is worth <strong>${Math.round(
      val50 * 100
    )}%</strong> of #1`;
    html += createSlider(
      "ranking",
      "p_exponent",
      "Power Law Steepness (P)",
      false,
      false,
      helper
    );
  }

  html += createSlider(
    "ranking",
    "consensus_boost",
    "🤝 Consensus Boost",
    true,
    false,
    'Applies a logarithmic bonus based on how many different critics included the song. This acts as a "cultural record" weight, ensuring that a song beloved by 30 critics outpaces a song that hit #1 on only one list.'
  );
  html += createSlider(
    "ranking",
    "provocation_boost",
    "⚡ Provocation Boost",
    true,
    false,
    'Rewards "bold" choices. This calculates the standard deviation of a song\'s ranks; songs that critics are divided on (e.g., ranked #1 by some and #80 by others) receive a higher bonus than songs everyone safely ranked in the middle.'
  );

  const clusterMetadata = APP_DATA.config.cluster_metadata || {};
  const clusterDesc =
    "Rewards crossover between different categories of critics by giving a bonus for each additional category reached with a best rank under the Cluster Threshold.";

  html += createSlider(
    "ranking",
    "cluster_boost",
    "🌍 Cluster Boost",
    true,
    false,
    clusterDesc
  );

  html += createSlider(
    "ranking",
    "cluster_threshold",
    "🎯 Cluster Threshold",
    false,
    false,
    "Defines the rank a song must achieve to count for the Cluster Boost."
  );
  html += createSlider(
    "ranking",
    "rank1_bonus",
    "🥇 Rank 1 Bonus",
    false,
    true,
    'Provides a heavy point multiplier for the absolute top pick. This rewards the "Obsession" factor, ensuring a critic\'s singular favorite song carries significantly more weight than their #2.'
  );
  html += createSlider(
    "ranking",
    "rank2_bonus",
    "🥈 Rank 2 Bonus",
    false,
    true,
    'Adds a secondary bonus to the silver medalist. This maintains a distinct gap between the "Elite" top-two picks and the rest of the Top 10.'
  );
  html += createSlider(
    "ranking",
    "rank3_bonus",
    "🥉 Rank 3 Bonus",
    false,
    true,
    'A slight nudge for the third-place track. This completes the "Podium" effect, giving the top three picks a mathematical edge over the "Standard" ranks.'
  );

  html += "</article>";

  // 2. Source Weights
  html += "<article>";
  html += "<hgroup>";
  html += "<h4>Source Weights</h4>";
  html +=
    '<p>Fine-tune the individual influence of each publication. These sliders allow you to manually adjust the specific "gravity" a source has within the final consensus.</p>';
  html += "</hgroup>";
  const sortedSources = Object.keys(sources).sort();

  // Group sources by cluster
  const sourcesByCluster = {};
  sortedSources.forEach((srcKey) => {
    const clusterName = sources[srcKey].cluster || "Other";
    if (!sourcesByCluster[clusterName]) {
      sourcesByCluster[clusterName] = [];
    }
    sourcesByCluster[clusterName].push(srcKey);
  });

  // Sort clusters and display each group
  const sortedClusters = Object.keys(sourcesByCluster).sort();
  sortedClusters.forEach((clusterName) => {
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

  // 3. Shadow Ranks
  const unrankedSources = sortedSources.filter(
    (k) => sources[k].type === "unranked"
  );
  if (unrankedSources.length > 0) {
    html += "<article>";
    html += "<hgroup>";
    html += "<h4>Shadow Ranks</h4>";
    html +=
      '<p>Governs how the engine handles unranked review lists. These lists are assigned a "Shadow Rank" based on their total length. This ensures a song appearing on an unranked "Top 10" list correctly receives more weight than one on an unranked "Top 100" list.</p>';
    html += "</hgroup>";
    unrankedSources.forEach((srcKey) => {
      const songCount = APP_DATA.config.sources[srcKey].song_count;
      html += createSlider(
        "source_shadow",
        srcKey,
        srcKey,
        false,
        false,
        "",
        (sublabel = `(${songCount} songs)`)
      );
    });
    html += "</article>";
  }

  // 4. Interface Settings
  html += "<article>";
  html += "<hgroup>";
  html += "<h4>Interface</h4>";
  html += "</hgroup>";

  // Theme Selector
  html += `
        <label>Theme</label>
        <select onchange="updateSetting('theme', 'theme', this.value)" style="margin-bottom: 2rem;">
            ${Object.entries(THEME_CONFIG)
              .map(
                ([key, config]) =>
                  `<option value="${key}" ${
                    STATE.config.theme === key ? "selected" : ""
                  }>${config.name}</option>`
              )
              .join("")}
        </select>
    `;
  html += "</article>";

  UI.settingsContent.innerHTML = html;
}

window.updateSetting = (category, key, value, idBase, isPercent, isBonus) => {
  // If switching mode, full re-render
  if (key === "decay_mode") {
    STATE.config.ranking.decay_mode = value;
    renderSettingsUI();
    debouncedReRank();
    return;
  }

  if (key === "theme") {
    applyTheme(value);
    debouncedReRank(); // To update URL
    return;
  }

  let numVal = parseFloat(value);
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

  // Update Label UI
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
    // Approximate equality check for floating point values (within 0.0001)
    if (Math.abs(numVal - defaultVal) > 0.0001) {
      label.classList.add("customized-label");
    } else {
      label.classList.remove("customized-label");
    }
  }

  // Dynamic Helper Text Update for K and P
  if (key === "k_value" || key === "p_exponent") {
    const val = parseFloat(value);
    let v10, v25, v50;

    if (key === "k_value") {
      v10 = (1 + val) / (10 + val);
      v25 = (1 + val) / (25 + val);
      v50 = (1 + val) / (50 + val);
    } else {
      v10 = 1.0 / Math.pow(10, val);
      v25 = 1.0 / Math.pow(25, val);
      v50 = 1.0 / Math.pow(50, val);
    }

    const helperEl = document.getElementById(`helper-text-${key}`);
    if (helperEl) {
      helperEl.innerHTML = `Rank #10 is worth <strong>${Math.round(
        v10 * 100
      )}%</strong> of #1<br>Rank #25 is worth <strong>${Math.round(
        v25 * 100
      )}%</strong> of #1<br>Rank #50 is worth <strong>${Math.round(
        v50 * 100
      )}%</strong> of #1`;
    }
  }

  debouncedReRank();
};

/**
 * CTRL+T THEME CYCLER
 * Cycles through available themes
 */
(function () {
  const themes = Object.keys(THEME_CONFIG);
  let currentIndex = 0;

  // Initialize index based on current theme
  const initTheme = STATE.config?.theme || "original";
  currentIndex = themes.indexOf(initTheme);
  if (currentIndex === -1) currentIndex = 0;

  document.addEventListener("keydown", (event) => {
    // Check for Ctrl+T (or Cmd+T on Mac)
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "t") {
      // Only allow theme switching if tskbd URL parameter is present
      const params = new URLSearchParams(window.location.search);
      if (!params.has("tskbd")) {
        return; // Exit early if flag is not present
      }

      event.preventDefault(); // Stop browser from opening a new tab

      // Advance to next theme
      currentIndex = (currentIndex + 1) % themes.length;
      const newTheme = themes[currentIndex];

      // Apply the theme
      // Don't modify STATE.config.theme directly here, let updateSetting or applyTheme handle it if needed
      // But updateSetting expects a category/key structure or 'theme' special case
      // Let's use applyTheme and then update URL

      applyTheme(newTheme);
      updateURL(STATE.config); // STATE.config.theme is updated inside applyTheme

      // Update the theme dropdown if settings modal is open
      const settingsContent = document.getElementById("settings-content");
      if (settingsContent) {
        const selects = settingsContent.querySelectorAll("select");
        const themeSelect = selects[selects.length - 1]; // Last select is the theme dropdown
        if (themeSelect) {
          themeSelect.value = newTheme;
        }
      }

      // Log to console
      console.log(`🎨 Theme switched to: ${newTheme}`);
    }
  });
})();
