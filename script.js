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
 * Direct scoring with anchor-rank decay functions.
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

        // Apply Top Rank Bonuses (for integer ranks only)
        const intRank = Math.floor(rank);
        if (intRank === 1) val *= (1 + config.rank1_bonus);
        else if (intRank === 2) val *= (1 + config.rank2_bonus);
        else if (intRank === 3) val *= (1 + config.rank3_bonus);
        
        return val;
    },

    compute(songs, config) {
        const rankedSongs = songs.map(song => {
            let totalScore = 0;
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

                // Direct Scoring: Decay * Weight (no normalization)
                const contribution = this.getDecayValue(rank, config.ranking) * srcCfg.weight;
                totalScore += contribution;
                
                sourceDetails.push({ name: srcEntry.name, rank, contribution, full_name: srcCfg.full_name || srcEntry.name });
            });

            // Multipliers
            const c_mul = ranks.length > 0 ? 1 + (config.ranking.consensus_boost * Math.log(ranks.length)) : 1.0;
            
            let p_mul = 1.0;
            if (ranks.length > 1) {
                const mean = ranks.reduce((a, b) => a + b) / ranks.length;
                // Population Standard Deviation (like np.std)
                const stdDev = Math.sqrt(ranks.map(x => Math.pow(x - mean, 2)).reduce((a, b) => a + b) / ranks.length);
                p_mul = 1 + (config.ranking.provocation_boost * (stdDev / 100));
            }

            const cl_mul = clustersSeen.size > 0 ? 1 + (config.ranking.cluster_boost * (clustersSeen.size - 1)) : 1.0;

            const finalScore = totalScore * c_mul * p_mul * cl_mul;

            return {
                ...song,
                finalScore,
                sourceDetails: sourceDetails.sort((a, b) => b.contribution - a.contribution),
                stats: { totalScore, c_mul, p_mul, cl_mul, listCount: ranks.length }
            };
        });

        // Normalize final scores to 0.0 - 1.0 range based on the top song
        const maxScore = Math.max(...rankedSongs.map(s => s.finalScore)) || 1; // Prevent div by zero
        return rankedSongs
            .map(s => ({ ...s, normalizedScore: s.finalScore / maxScore }))
            .sort((a, b) => b.finalScore - a.finalScore)
            .map((s, i) => ({ ...s, rank: i + 1 }));
    }
};

// Expose for debugging
window.RankingEngine = RankingEngine;

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
    const defaults = APP_DATA.config;

    // Ranking Params
    Object.entries(config.ranking).forEach(([k, v]) => {
        if (v !== defaults.ranking[k]) {
            params.set(k, v);
        }
    });

    // Sources
    Object.entries(config.sources).forEach(([srcKey, srcCfg]) => {
        const urlKey = srcKey.toLowerCase().replace(/[^a-z0-9]/g, '_');
        
        // Weight
        if (srcCfg.weight !== defaults.sources[srcKey].weight) {
            params.set(`w_${urlKey}`, srcCfg.weight.toFixed(2));
        }

        // Shadow Rank
        if (srcCfg.type === 'unranked' && srcCfg.shadow_rank !== defaults.sources[srcKey].shadow_rank) {
            params.set(urlKey, srcCfg.shadow_rank);
        }
    });

    const queryString = params.toString();
    const newUrl = queryString ? `${window.location.pathname}?${queryString}` : window.location.pathname;
    window.history.replaceState({}, '', newUrl);
}

/**
 * UI RENDERING
 */
function render() {
    STATE.songs = RankingEngine.compute(APP_DATA.songs, STATE.config);
    const visible = STATE.songs.slice(0, STATE.displayLimit);
    
    UI.songList.innerHTML = visible.map((song, idx) => {
        const youtubeId = song.media?.youtube?.video_id || song.media?.youtube?.music_id;
        
        // Listen Links
        const links = [];
        if (song.media?.youtube?.video_id) links.push(`<a href="https://www.youtube.com/watch?v=${song.media.youtube.video_id}" target="_blank">YouTube</a>`);
        if (song.media?.youtube?.music_id) links.push(`<a href="https://music.youtube.com/watch?v=${song.media.youtube.music_id}" target="_blank">YTM</a>`);
        if (song.media?.spotify?.id) links.push(`<a href="https://open.spotify.com/track/${song.media.spotify.id}" target="_blank">Spotify</a>`);
        if (song.media?.bandcamp?.url) links.push(`<a href="${song.media.bandcamp.url}" target="_blank">Bandcamp</a>`);
        if (song.media?.other?.url) links.push(`<a href="${song.media.other.url}" target="_blank">Other</a>`);

        const listenHTML = links.length > 0 ? `<div class="listen-links" style="margin-top: 0.5rem;"><small><strong>LISTEN:</strong> ${links.join(' ')}</small></div>` : '';

        return `
            <article class="song-card" style="position: relative;">
                <div class="song-card-grid">
                    <div class="rank-large">#${song.rank}</div>
                    <div class="video-container">
                        <lite-youtube videoid="${youtubeId}"></lite-youtube>
                    </div>
                    <div>
                        <header style="margin-bottom: 0;">
                            <hgroup style="margin-bottom: 0.5rem;">
                                <h3 style="margin-bottom: 0.25rem;">${escapeHtml(song.name)}</h3>
                                <h4 style="color: var(--pico-muted-color); font-weight: normal;">${escapeHtml(song.artist)}</h4>
                            </hgroup>
                        </header>
                        
                        <div class="sources-list" onclick="showReviews(${idx})" style="cursor:pointer" title="Click to see reviews">
                            <small>
                                ${song.sourceDetails.map(s => `<span class="source-tag">${s.full_name || s.name}#${s.rank || '★'}</span>`).join(' · ')}
                            </small>
                        </div>

                        ${listenHTML}
                        
                        <div style="position: absolute; top: 1rem; right: 1rem;">
                            <a href="#" onclick="showStats(${idx}); return false;" class="secondary" style="text-decoration: none; font-size: 1.2rem;">ⓘ</a>
                        </div>
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
        UI.loadMoreBtn.style.display = 'inline-block';
        let nextStep = 75; // Initial 25 -> 100
        if (STATE.displayLimit === 100) nextStep = 100; // 100 -> 200
        if (STATE.displayLimit === 200) nextStep = 300; // 200 -> 500
        if (STATE.displayLimit >= 500) nextStep = remaining; // 500 -> All

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

    document.getElementById('reset-defaults').onclick = () => {
        STATE.config = JSON.parse(JSON.stringify(APP_DATA.config));
        renderSettingsUI();
        debouncedReRank();
    };

    // Close modal triggers
    document.querySelectorAll('.close-modal').forEach(btn => {
        btn.onclick = function() {
            this.closest('dialog').close();
        };
    });

    // About modal
    document.getElementById('open-about').onclick = () => {
        document.getElementById('modal-about').showModal();
    };
}

const debouncedReRank = debounce(() => {
    updateURL(STATE.config);
    render();
}, 250);

init();
// Reviews Modal
window.showReviews = (idx) => {
    const song = STATE.songs[idx];
    if (!song) return;

    let html = '<div style="display: flex; flex-direction: column; gap: 1rem;">';
    
    song.sources.forEach(src => {
        const srcConfig = STATE.config.sources[src.name];
        const displayName = srcConfig.full_name || src.name;
        // Use configured shadow rank if applicable, otherwise source rank
        const rankVal = src.uses_shadow_rank ? srcConfig.shadow_rank : src.rank;
        const rankDisplay = `#${rankVal}`;
        
        html += `
            <article style="padding: 1rem; margin: 0; background-color: var(--pico-card-background-color);">
                <header style="margin-bottom: 0.5rem; display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <strong>${displayName}</strong> 
                        <span style="color: var(--pico-muted-color); margin-left: 0.5rem;">${rankDisplay}</span>
                    </div>
                    <a href="${srcConfig.url}" target="_blank" role="button" class="outline contrast" style="font-size: 0.8rem; padding: 0.25rem 0.5rem;">Read Review</a>
                </header>
                ${src.quote ? `<blockquote style="margin: 0.5rem 0 0 0;">"${escapeHtml(src.quote)}"</blockquote>` : ''}
            </article>
        `;
    });
    
    html += '</div>';
    
    UI.reviewsContent.innerHTML = html;
    document.getElementById('modal-reviews').showModal();
};

// Ranking Stats Modal
window.showStats = (idx) => {
    const song = STATE.songs[idx];
    if (!song) return;

    document.getElementById('stats-title').textContent = `Ranking: ${song.name}`;
    
    const stats = song.stats;
    
    let html = `
        <div>
            <div>
                <h5>Scoring</h5>
                <table class="striped">
                    <tbody>
                        <tr><td>Normalized Score</td><td><strong>${song.normalizedScore.toFixed(4)}</strong></td></tr>
                        <tr><td>Raw Score</td><td>${song.finalScore.toFixed(4)}</td></tr>
                        <tr><td>Base Score</td><td>${stats.totalScore.toFixed(4)}</td></tr>
                        <tr><td>List Count</td><td>${stats.listCount}</td></tr>
                        <tr><td>Consensus Boost</td><td>x${stats.c_mul.toFixed(3)}</td></tr>
                        <tr><td>Provocation Boost</td><td>x${stats.p_mul.toFixed(3)}</td></tr>
                        <tr><td>Cluster Boost</td><td>x${stats.cl_mul.toFixed(3)}</td></tr>
                    </tbody>
                </table>
            </div>
        </div>
        
        <hr>
        <h5>Source Contributions</h5>
        <div style="overflow-x: auto;">
            <table class="striped">
                <thead>
                    <tr>
                        <th>Source</th>
                        <th>Rank</th>
                        <th>Contribution</th>
                    </tr>
                </thead>
                <tbody>
    `;
    
    // sourceDetails is already sorted by contribution in RankingEngine
    song.sourceDetails.forEach(sd => {
        html += `
            <tr>
                <td>${sd.full_name || sd.name}</td>
                <td>${sd.rank}</td>
                <td>${sd.contribution.toFixed(4)}</td>
            </tr>
        `;
    });
    
    html += `
                </tbody>
            </table>
        </div>
    `;

    UI.statsContent.innerHTML = html;
    document.getElementById('modal-stats').showModal();
};

/**
 * SETTINGS UI
 */
function renderSettingsUI() {
    const { ranking, sources } = STATE.config;
    const defaults = APP_DATA.config;

    let html = '';

    // 1. Ranking Parameters
    html += '<h4>Ranking Parameters</h4>';

    // Decay Mode
    const isConsensus = ranking.decay_mode === 'consensus';
    html += `
        <fieldset>
            <legend>Decay Mode</legend>
            <div class="grid" style="grid-template-columns: 1fr 1fr; gap: 1rem;">
                <label>
                    <input type="radio" name="decay_mode" value="consensus" ${isConsensus ? 'checked' : ''} onchange="updateSetting('ranking', 'decay_mode', 'consensus')">
                    Consensus
                </label>
                <label>
                    <input type="radio" name="decay_mode" value="conviction" ${!isConsensus ? 'checked' : ''} onchange="updateSetting('ranking', 'decay_mode', 'conviction')">
                    Conviction
                </label>
            </div>
        </fieldset>
    `;

    // Sliders Helper
    const createSlider = (category, key, label, min, max, step, isPercent = false, isBonus = false) => {
        let currentVal = category === 'ranking' ? ranking[key] : (category === 'source_weight' ? sources[key].weight : sources[key].shadow_rank);
        let defaultVal = category === 'ranking' ? defaults.ranking[key] : (category === 'source_weight' ? defaults.sources[key].weight : defaults.sources[key].shadow_rank);
        
        const isModified = currentVal !== defaultVal;
        // Bonus values are stored as multipliers (1.1 = 10% bonus), so subtract 1 and multiply by 100 for display
        const displayVal = isBonus ? Math.round((currentVal - 1) * 100) + '%' : (isPercent ? Math.round(currentVal * 100) + '%' : currentVal);
        const idBase = `setting-${category}-${key.replace(/[^a-zA-Z0-9]/g, '_')}`;

        return `
            <div style="margin-bottom: 1rem;">
                <label id="label-${idBase}" class="${isModified ? 'customized-label' : ''}" style="display:flex; justify-content:space-between;">
                    <span>${label}</span>
                    <strong id="val-${idBase}">${displayVal}</strong>
                </label>
                <input type="range" id="${idBase}" min="${min}" max="${max}" step="${step}" value="${currentVal}" 
                    oninput="updateSetting('${category}', '${key}', this.value, '${idBase}', ${isPercent}, ${isBonus})">
            </div>
        `;
    };

    html += '<div style="display: flex; flex-direction: column; gap: 0;">';
    
    if (isConsensus) {
        html += createSlider('ranking', 'k_value', 'Rank Decay (K)', 0, 50, 1);
    } else {
        html += createSlider('ranking', 'p_exponent', 'Power-Law Decay (P)', 0.0, 1.1, 0.01);
    }
    
    html += createSlider('ranking', 'consensus_boost', 'Consensus Boost', 0, 0.1, 0.01, true);
    html += createSlider('ranking', 'provocation_boost', 'Provocation Boost', 0, 0.25, 0.01, true);
    html += createSlider('ranking', 'cluster_boost', 'Cluster Boost', 0, 0.1, 0.01, true);
    
    html += createSlider('ranking', 'cluster_threshold', 'Cluster Threshold', 0, 100, 1);
    html += createSlider('ranking', 'rank1_bonus', 'Rank 1 Bonus', 1.0, 1.2, 0.01, false, true);
    html += createSlider('ranking', 'rank2_bonus', 'Rank 2 Bonus', 1.0, 1.2, 0.01, false, true);
    html += createSlider('ranking', 'rank3_bonus', 'Rank 3 Bonus', 1.0, 1.2, 0.01, false, true);
    
    html += '</div>'; // End Stack
    
    // 2. Source Weights
    html += '<hr><h4>Source Weights</h4>';
    const sortedSources = Object.keys(sources).sort();
    
    html += '<div style="display: flex; flex-direction: column; gap: 0;">';
    sortedSources.forEach(srcKey => {
        html += createSlider('source_weight', srcKey, sources[srcKey].full_name || srcKey, 0.0, 1.5, 0.01);
    });
    html += '</div>';

    // 3. Shadow Ranks
    const unrankedSources = sortedSources.filter(k => sources[k].type === 'unranked');
    if (unrankedSources.length > 0) {
        html += '<hr><h4>Shadow Ranks</h4>';
        html += '<div style="display: flex; flex-direction: column; gap: 0;">';
        unrankedSources.forEach(srcKey => {
             const songCount = APP_DATA.config.sources[srcKey].song_count;
             html += createSlider('source_shadow', srcKey, `${sources[srcKey].full_name || srcKey} (${songCount} songs)`, 1.0, 100.0, 0.1);
        });
        html += '</div>';
    }

    UI.settingsContent.innerHTML = html;
}

window.updateSetting = (category, key, value, idBase, isPercent, isBonus) => {
    // If switching mode, full re-render
    if (key === 'decay_mode') {
        STATE.config.ranking.decay_mode = value;
        renderSettingsUI();
        debouncedReRank();
        return;
    }

    let numVal = parseFloat(value);
    const defaults = APP_DATA.config;
    let defaultVal;

    if (category === 'ranking') {
        STATE.config.ranking[key] = numVal;
        defaultVal = defaults.ranking[key];
    } else if (category === 'source_weight') {
        STATE.config.sources[key].weight = numVal;
        defaultVal = defaults.sources[key].weight;
    } else if (category === 'source_shadow') {
        STATE.config.sources[key].shadow_rank = numVal;
        defaultVal = defaults.sources[key].shadow_rank;
    }

    // Update Label UI
    if (idBase) {
        const displayVal = isBonus ? Math.round((numVal - 1) * 100) + '%' : (isPercent ? Math.round(numVal * 100) + '%' : numVal);
        document.getElementById(`val-${idBase}`).textContent = displayVal;
        
        const label = document.getElementById(`label-${idBase}`);
        if (numVal !== defaultVal) label.classList.add('customized-label');
        else label.classList.remove('customized-label');
    }

    debouncedReRank();
};

