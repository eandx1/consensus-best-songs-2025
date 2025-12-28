/**
 * APP STATE & CONSTANTS
 */
let APP_DATA = null;
let STATE = {
    config: {}, // Current active configuration (weights, rankings, etc)
    songs: [],  // The final ranked list
    displayLimit: 25
};

const UI = {
    songList: document.getElementById('song-list'),
    loadMoreBtn: document.getElementById('load-more'),
    settingsContent: document.getElementById('settings-content'),
    statsContent: document.getElementById('stats-content'),
    reviewsContent: document.getElementById('reviews-content')
};

/**
 * UTILITIES
 */
const escapeHtml = (str) => {
    if (!str) return '';
    const div = document.createElement('div');
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
 * RANKING ENGINE (Ported from Python)
 * Implements the "Influence Budget" philosophy where every source has a fixed power.
 */
const RankingEngine = {
    getDecayValue(rank, config) {
        let val = 0;
        if (config.decay_mode === 'consensus') {
            // (1+K) / (rank+K)
            val = (1 + config.k_value) / (rank + config.k_value);
        } else {
            // 1 / (rank^P)
            val = 1.0 / Math.pow(rank, config.p_exponent);
        }

        // Apply Top Rank Bonuses
        if (rank === 1) val *= (1 + config.rank1_bonus);
        else if (rank === 2) val *= (1 + config.rank2_bonus);
        else if (rank === 3) val *= (1 + config.rank3_bonus);
        
        return val;
    },

    calculateSourceNormFactors(sources, rankingConfig) {
        const normFactors = {};
        Object.entries(sources).forEach(([name, srcConfig]) => {
            // Lists are treated as if they have at least min_norm_length
            const effLen = Math.max(srcConfig.song_count, rankingConfig.min_norm_length);
            let totalPoints = 0;
            // Handle NPR Top 125 offset: ranks start at 26
            const startR = (name === "NPR Top 125") ? 26 : 1;
            
            for (let r = startR; r <= effLen; r++) {
                totalPoints += this.getDecayValue(r, rankingConfig);
            }
            normFactors[name] = totalPoints;
        });
        return normFactors;
    },

    compute(songs, config) {
        const normFactors = this.calculateSourceNormFactors(config.sources, config.ranking);
        
        const rankedSongs = songs.map(song => {
            let totalNormalizedScore = 0;
            let ranks = [];
            let clustersSeen = new Set();
            let sourceDetails = [];

            song.sources.forEach(srcEntry => {
                const srcCfg = config.sources[srcEntry.name];
                if (!srcCfg) return;

                const rank = srcEntry.uses_shadow_rank ? srcCfg.shadow_rank : srcEntry.rank;
                ranks.push(rank);

                if (rank <= config.ranking.cluster_threshold) {
                    clustersSeen.add(srcCfg.cluster);
                }

                // Contribution = (Decay / Total Source Points) * Weight
                const contribution = (this.getDecayValue(rank, config.ranking) / normFactors[srcEntry.name]) * srcCfg.weight;
                totalNormalizedScore += contribution;
                
                sourceDetails.push({ name: srcEntry.name, rank, contribution, full_name: srcCfg.full_name || srcEntry.name });
            });

            // Multipliers
            const c_mul = 1 + (config.ranking.consensus_boost * Math.log(ranks.length));
            
            let p_mul = 1.0;
            if (ranks.length > 1) {
                const mean = ranks.reduce((a, b) => a + b) / ranks.length;
                const stdDev = Math.sqrt(ranks.map(x => Math.pow(x - mean, 2)).reduce((a, b) => a + b) / ranks.length);
                p_mul = 1 + (config.ranking.provocation_boost * (stdDev / 100));
            }

            const cl_mul = clustersSeen.size > 0 ? 1 + (config.ranking.cluster_boost * (clustersSeen.size - 1)) : 1.0;

            const finalScore = totalNormalizedScore * c_mul * p_mul * cl_mul;

            return {
                ...song,
                finalScore,
                sourceDetails: sourceDetails.sort((a, b) => b.contribution - a.contribution),
                stats: { totalNormalizedScore, c_mul, p_mul, cl_mul, listCount: ranks.length }
            };
        });

        // Normalize final scores to 0.0 - 1.0 range based on the top song
        const maxScore = Math.max(...rankedSongs.map(s => s.finalScore));
        return rankedSongs
            .map(s => ({ ...s, normalizedScore: s.finalScore / maxScore }))
            .sort((a, b) => b.finalScore - a.finalScore);
    }
};

/**
 * STATE SYNCING (URL <-> APP)
 */
function syncStateFromURL(defaultConfig) {
    const params = new URLSearchParams(window.location.search);
    const config = JSON.parse(JSON.stringify(defaultConfig));

    // Ranking Params
    const rankingKeys = ['decay_mode', 'k_value', 'p_exponent', 'consensus_boost', 'provocation_boost', 'cluster_boost', 'cluster_threshold', 'rank1_bonus', 'rank2_bonus', 'rank3_bonus'];
    rankingKeys.forEach(key => {
        if (params.has(key)) {
            config.ranking[key] = (key === 'decay_mode') ? params.get(key) : parseFloat(params.get(key));
        }
    });

    // Source Weights & Shadows
    Object.keys(config.sources).forEach(srcKey => {
        const urlKey = srcKey.toLowerCase().replace(/[^a-z0-9]/g, '_');
        if (params.has(`w_${urlKey}`)) config.sources[srcKey].weight = parseFloat(params.get(`w_${urlKey}`));
        if (params.has(urlKey) && config.sources[srcKey].type === 'unranked') {
            config.sources[srcKey].shadow_rank = parseFloat(params.get(urlKey));
        }
    });

    return config;
}

function updateURL(config) {
    const params = new URLSearchParams();
    Object.entries(config.ranking).forEach(([k, v]) => params.set(k, v));
    Object.entries(config.sources).forEach(([srcKey, srcCfg]) => {
        const urlKey = srcKey.toLowerCase().replace(/[^a-z0-9]/g, '_');
        params.set(`w_${urlKey}`, srcCfg.weight.toFixed(2));
        if (srcCfg.type === 'unranked') params.set(urlKey, srcCfg.shadow_rank);
    });
    window.history.replaceState({}, '', `${window.location.pathname}?${params.toString()}`);
}

/**
 * UI RENDERING
 */
function render() {
    STATE.songs = RankingEngine.compute(APP_DATA.songs, STATE.config);
    const visible = STATE.songs.slice(0, STATE.displayLimit);
    
    UI.songList.innerHTML = visible.map((song, idx) => {
        const youtubeId = song.media?.youtube?.video_id || song.media?.youtube?.music_id;
        return `
            <article class="song-card">
                <div class="grid">
                    <div class="rank-large">${idx + 1}</div>
                    <div class="video-container">
                        <lite-youtube videoid="${youtubeId}"></lite-youtube>
                    </div>
                    <div>
                        <header>
                            <hgroup>
                                <h4>${escapeHtml(song.name)}</h4>
                                <p>${escapeHtml(song.artist)}</p>
                            </hgroup>
                            <a href="#" onclick="showStats(${idx}); return false;" style="float:right">ⓘ</a>
                        </header>
                        <small onclick="showReviews(${idx})" style="cursor:pointer">
                            ${song.sources.map(s => `<span style="white-space: nowrap">${s.name}#${s.rank || '★'}</span>`).join(' · ')}
                        </small>
                    </div>
                </div>
            </article>
        `;
    }).join('');

    updateLoadMoreButton();
}

function updateLoadMoreButton() {
    const remaining = STATE.songs.length - STATE.displayLimit;
    if (remaining <= 0) {
        UI.loadMoreBtn.style.display = 'none';
    } else {
        UI.loadMoreBtn.style.display = 'block';
        let nextStep = 75; // Initial 25 -> 100
        if (STATE.displayLimit === 100) nextStep = 100; // 100 -> 200
        if (STATE.displayLimit === 200) nextStep = 300; // 200 -> 500
        UI.loadMoreBtn.textContent = remaining > nextStep ? `Show More (${nextStep})` : `Show All (${remaining})`;
    }
}

/**
 * INITIALIZATION
 */
async function init() {
    const response = await fetch('data.json');
    APP_DATA = await response.json();
    STATE.config = syncStateFromURL(APP_DATA.config);
    render();
    
    // Listen for "Load More"
    UI.loadMoreBtn.onclick = () => {
        if (STATE.displayLimit === 25) STATE.displayLimit = 100;
        else if (STATE.displayLimit === 100) STATE.displayLimit = 200;
        else if (STATE.displayLimit === 200) STATE.displayLimit = 500;
        else STATE.displayLimit = STATE.songs.length;
        render();
    };

    // Modal triggers
    document.getElementById('open-settings').onclick = () => {
        renderSettingsUI();
        document.getElementById('modal-settings').showModal();
    };
}

const debouncedReRank = debounce(() => {
    updateURL(STATE.config);
    render();
}, 250);

init();
