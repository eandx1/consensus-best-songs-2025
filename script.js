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
 * MATH FORMULA WEB COMPONENT
 */
class MathFormula extends HTMLElement {
    connectedCallback() {
        const type = this.getAttribute('type');
        // Using Pico's CSS variable for the current text color
        const color = 'var(--pico-color)';
        
        const formulas = {
            consensus: `
                <svg viewBox="0 0 100 40" style="width: 7em; height: auto;" xmlns="http://www.w3.org/2000/svg" fill="${color}">
                    <text x="0" y="25" font-family="serif" font-style="italic" font-size="16">W(r) =</text>
                    <line x1="52" y1="20" x2="98" y2="20" stroke="${color}" stroke-width="1.5"/>
                    <text x="60" y="14" font-family="serif" font-size="12">1 + K</text>
                    <text x="60" y="34" font-family="serif" font-size="12">r + K</text>
                </svg>`,
            conviction: `
                <svg viewBox="0 0 80 40" style="width: 5.5em; height: auto;" xmlns="http://www.w3.org/2000/svg" fill="${color}">
                    <text x="0" y="25" font-family="serif" font-style="italic" font-size="16">W(r) =</text>
                    <line x1="52" y1="20" x2="78" y2="20" stroke="${color}" stroke-width="1.5"/>
                    <text x="60" y="14" font-family="serif" font-size="12">1</text>
                    <text x="58" y="34" font-family="serif" font-size="12">r<tspan baseline-shift="super" font-size="8">P</tspan></text>
                </svg>`
        };

        this.innerHTML = formulas[type] || '';
        this.style.display = 'inline-flex';
    }
}

customElements.define('math-formula', MathFormula);

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
        
        // Listen Links as nav list items
        const links = [];
        if (song.media?.youtube?.video_id) links.push(`<li><a href="https://www.youtube.com/watch?v=${song.media.youtube.video_id}" target="_blank">YouTube</a></li>`);
        if (song.media?.youtube?.music_id) links.push(`<li><a href="https://music.youtube.com/watch?v=${song.media.youtube.music_id}" target="_blank">YTM</a></li>`);
        if (song.media?.spotify?.id) links.push(`<li><a href="https://open.spotify.com/track/${song.media.spotify.id}" target="_blank">Spotify</a></li>`);
        if (song.media?.bandcamp?.url) links.push(`<li><a href="${song.media.bandcamp.url}" target="_blank">Bandcamp</a></li>`);
        if (song.media?.other?.url) links.push(`<li><a href="${song.media.other.url}" target="_blank">Other</a></li>`);

        return `
            <article class="song-card">
                <div class="grid">
                    <aside>#${song.rank}</aside>
                    
                    <figure>
                        <lite-youtube videoid="${youtubeId}" playlabel="Play ${escapeHtml(song.name)}"></lite-youtube>
                    </figure>
                    
                    <div>
                        <header>
                            <hgroup>
                                <h3>${escapeHtml(song.name)}</h3>
                                <h4>${escapeHtml(song.artist)}</h4>
                            </hgroup>
                            <a href="#" onclick="showStats(${idx}); return false;" aria-label="View ranking details">ⓘ</a>
                        </header>
                        
                        <div data-sources onclick="showReviews(${idx})" title="Click to see reviews">
                            <small>
                                ${song.sourceDetails.map(s => `<span>${escapeHtml(s.full_name || s.name)}#${Math.floor(s.rank)}</span>`).join(' · ')}
                            </small>
                        </div>
                        
                        ${links.length > 0 ? `<nav aria-label="Listen links"><ul>${links.join('')}</ul></nav>` : ''}
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

    document.getElementById('stats-title').textContent = 'Ranking Details';
    
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
        const sourceCfg = STATE.config.sources[sd.name];
        const clusterId = sourceCfg?.cluster;
        const clusterMeta = APP_DATA.config.cluster_metadata?.[clusterId];
        
        // Access the cluster ID (which is the name)
        const clusterEmoji = clusterMeta?.emoji || '';
        const clusterName = clusterId || 'Unknown Category';  // Use cluster ID as the name
        
        // Just use the category name for the tooltip (no descriptor)
        const tooltipText = escapeHtml(clusterName);
        
        // Logic for Shadow Rank display (using the Ghost emoji/tilde approach)
        const displayRank = String(sd.rank).includes('.5') 
            ? `<abbr data-tooltip="Shadow Rank (Calculated from list length)">👻~${Math.ceil(sd.rank)}</abbr>` 
            : sd.rank;

        html += `
            <tr>
                <td>
                    <div style="display: flex; align-items: center; gap: 0.5rem;">
                        <abbr data-tooltip="${tooltipText}" data-placement="right" style="text-decoration: none; cursor: help;">
                            ${clusterEmoji}
                        </abbr>
                        <span>${escapeHtml(sd.full_name || sd.name)}</span>
                    </div>
                </td>
                <td style="font-family: var(--pico-font-family-monospace);">${displayRank}</td>
                <td style="text-align: right;">
                    <kbd style="background: var(--pico-secondary-background); color: var(--pico-secondary-color); font-weight: bold;">
                        +${sd.contribution.toFixed(2)}
                    </kbd>
                </td>
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
    html += '<article>';
    html += '<hgroup>';
    html += '<h4>Ranking Parameters</h4>';
    html += '</hgroup>';

    // Decay Mode
    const isConsensus = ranking.decay_mode === 'consensus';
    html += `
        <label>Decay Mode</label>
        <div class="grid" style="margin-bottom: 2rem;">
            <article class="mode-card ${isConsensus ? 'active' : ''}" onclick="updateSetting('ranking', 'decay_mode', 'consensus')" style="display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; padding: var(--pico-spacing);">
                <header style="width: 100%; border-bottom: none; padding-bottom: 0;">
                    <strong>🤝 Consensus</strong>
                </header>
                
                <div class="formula-container" style="margin: var(--pico-spacing) 0;">
                    <math-formula type="consensus"></math-formula>
                </div>

                <p style="margin-bottom: 0;">
                    <small style="color: var(--pico-muted-color);">
                        Rewards cultural record. Favors songs on more lists.
                    </small>
                </p>
            </article>
            
            <article class="mode-card ${!isConsensus ? 'active' : ''}" onclick="updateSetting('ranking', 'decay_mode', 'conviction')" style="display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; padding: var(--pico-spacing);">
                <header style="width: 100%; border-bottom: none; padding-bottom: 0;">
                    <strong>🔥 Conviction</strong>
                </header>
                
                <div class="formula-container" style="margin: var(--pico-spacing) 0;">
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
    const createSlider = (category, key, label, min, max, step, isPercent = false, isBonus = false, helperText = '') => {
        let currentVal = category === 'ranking' ? ranking[key] : (category === 'source_weight' ? sources[key].weight : sources[key].shadow_rank);
        let defaultVal = category === 'ranking' ? defaults.ranking[key] : (category === 'source_weight' ? defaults.sources[key].weight : defaults.sources[key].shadow_rank);
        
        // Approximate equality check for floating point values (within 0.0001)
        const isModified = Math.abs(currentVal - defaultVal) > 0.0001;
        // Bonus values are stored as multipliers (1.1 = 10% bonus), so subtract 1 and multiply by 100 for display
        let displayVal;
        let minWidth = '3.5rem'; // default for decimals
        
        if (isBonus) {
            displayVal = ((currentVal - 1) * 100).toFixed(1) + '%';
        } else if (isPercent) {
            displayVal = Math.round(currentVal * 100) + '%';
        } else if (key === 'k_value') {
            displayVal = Math.round(currentVal).toString();
            minWidth = '2rem'; // 2 digits
        } else if (key === 'cluster_threshold') {
            displayVal = Math.round(currentVal).toString();
            minWidth = '2.5rem'; // 3 digits
        } else {
            displayVal = parseFloat(currentVal).toFixed(2);
        }
        
        const idBase = `setting-${category}-${key.replace(/[^a-zA-Z0-9]/g, '_')}`;
        const helperId = `helper-text-${key}`;

        return `
            <div style="margin-bottom: var(--pico-spacing);">
                <label id="label-${idBase}" class="${isModified ? 'customized-label' : ''}" style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; margin-bottom: 0;">
                    <span>${label}</span>
                    <kbd id="val-${idBase}" style="font-size: 0.8rem; min-width: ${minWidth}; text-align: center;">${displayVal}</kbd>
                    <input type="range" id="${idBase}" min="${min}" max="${max}" step="${step}" value="${currentVal}" 
                        style="width: 100%; margin-bottom: 0.25rem;"
                        oninput="updateSetting('${category}', '${key}', this.value, '${idBase}', ${isPercent}, ${isBonus})">
                </label>
                ${helperText ? `<p style="color: var(--pico-muted-color); font-size: 0.85em; margin-bottom: 0;">${helperText}</p>` : ''}
            </div>
        `;
    };

    if (isConsensus) {
        const val10 = (1 + ranking.k_value) / (10 + ranking.k_value);
        const val25 = (1 + ranking.k_value) / (25 + ranking.k_value);
        const val50 = (1 + ranking.k_value) / (50 + ranking.k_value);
        const helper = `Rank #10 is worth <strong>${Math.round(val10 * 100)}%</strong> of #1<br>Rank #25 is worth <strong>${Math.round(val25 * 100)}%</strong> of #1<br>Rank #50 is worth <strong>${Math.round(val50 * 100)}%</strong> of #1`;
        html += createSlider('ranking', 'k_value', 'Smoothing Factor (K)', 0, 50, 1, false, false, helper);
    } else {
        const val10 = 1.0 / Math.pow(10, ranking.p_exponent);
        const val25 = 1.0 / Math.pow(25, ranking.p_exponent);
        const val50 = 1.0 / Math.pow(50, ranking.p_exponent);
        const helper = `Rank #10 is worth <strong>${Math.round(val10 * 100)}%</strong> of #1<br>Rank #25 is worth <strong>${Math.round(val25 * 100)}%</strong> of #1<br>Rank #50 is worth <strong>${Math.round(val50 * 100)}%</strong> of #1`;
        html += createSlider('ranking', 'p_exponent', 'Power Law Steepness (P)', 0.0, 1.1, 0.01, false, false, helper);
    }
    
    html += createSlider('ranking', 'consensus_boost', '🤝 Consensus Boost', 0, 0.1, 0.01, true, false, 'Applies a logarithmic bonus based on how many different critics included the song. This acts as a "cultural record" weight, ensuring that a song beloved by 30 critics outpaces a song that hit #1 on only one list.');
    html += createSlider('ranking', 'provocation_boost', '⚡ Provocation Boost', 0, 0.25, 0.01, true, false, 'Rewards "bold" choices. This calculates the standard deviation of a song\'s ranks; songs that critics are divided on (e.g., ranked #1 by some and #80 by others) receive a higher bonus than songs everyone safely ranked in the middle.');
    
    // Collect unique clusters for Cluster Boost description
    const clusters = [...new Set(Object.values(sources).map(src => src.cluster).filter(c => c))].sort();
    const clusterMetadata = APP_DATA.config.cluster_metadata || {};
    const clustersWithEmoji = clusters.map(c => {
        const emoji = clusterMetadata[c]?.emoji || '';
        return emoji ? `${emoji} ${c}` : c;
    });
    const clusterList = clustersWithEmoji.length > 1 
        ? clustersWithEmoji.slice(0, -1).join(', ') + ', and ' + clustersWithEmoji[clustersWithEmoji.length - 1]
        : clustersWithEmoji[0] || '';
    const clusterDesc = `Rewards crossover between different categories of critics by giving a bonus for each additional category reached with a best rank under the Cluster Threshold. The current critic categories are: ${clusterList}.`;
    
    html += createSlider('ranking', 'cluster_boost', '🌍 Cluster Boost', 0, 0.1, 0.01, true, false, clusterDesc);
    
    html += createSlider('ranking', 'cluster_threshold', '🎯 Cluster Threshold', 0, 100, 1, false, false, 'Defines the rank a song must achieve to count for the Cluster Boost.');
    html += createSlider('ranking', 'rank1_bonus', '🥇 Rank 1 Bonus', 1.0, 1.2, 0.005, false, true, 'Provides a heavy point multiplier for the absolute top pick. This rewards the "Obsession" factor, ensuring a critic\'s singular favorite song carries significantly more weight than their #2.');
    html += createSlider('ranking', 'rank2_bonus', '🥈 Rank 2 Bonus', 1.0, 1.2, 0.005, false, true, 'Adds a secondary bonus to the silver medalist. This maintains a distinct gap between the "Elite" top-two picks and the rest of the Top 10.');
    html += createSlider('ranking', 'rank3_bonus', '🥉 Rank 3 Bonus', 1.0, 1.2, 0.005, false, true, 'A slight nudge for the third-place track. This completes the "Podium" effect, giving the top three picks a mathematical edge over the "Standard" ranks.');
    
    html += '</article>';
    
    // 2. Source Weights
    html += '<article>';
    html += '<hgroup>';
    html += '<h4>Source Weights</h4>';
    html += '<p>Fine-tune the individual influence of each publication. These sliders allow you to manually adjust the specific "gravity" a source has within the final consensus.</p>';
    html += '</hgroup>';
    const sortedSources = Object.keys(sources).sort();
    
    // Group sources by cluster
    const sourcesByCluster = {};
    sortedSources.forEach(srcKey => {
        const clusterName = sources[srcKey].cluster || 'Other';
        if (!sourcesByCluster[clusterName]) {
            sourcesByCluster[clusterName] = [];
        }
        sourcesByCluster[clusterName].push(srcKey);
    });
    
    // Sort clusters and display each group
    const sortedClusters = Object.keys(sourcesByCluster).sort();
    sortedClusters.forEach(clusterName => {
        const emoji = clusterMetadata[clusterName]?.emoji || '';
        const descriptor = clusterMetadata[clusterName]?.descriptor || '';
        
        html += '<fieldset>';
        html += `<legend>${emoji} ${clusterName}</legend>`;
        if (descriptor) {
            html += `<p><small style="color: var(--pico-muted-color); display: block; margin-bottom: 1rem;">${descriptor}</small></p>`;
        }
        
        sourcesByCluster[clusterName].forEach(srcKey => {
            html += createSlider('source_weight', srcKey, sources[srcKey].full_name || srcKey, 0.0, 1.5, 0.01);
        });
        html += '</fieldset>';
    });
    html += '</article>';

    // 3. Shadow Ranks
    const unrankedSources = sortedSources.filter(k => sources[k].type === 'unranked');
    if (unrankedSources.length > 0) {
        html += '<article>';
        html += '<hgroup>';
        html += '<h4>Shadow Ranks</h4>';
        html += '<p>Governs how the engine handles unranked review lists. These lists are assigned a "Shadow Rank" based on their total length. This ensures a song appearing on an unranked "Top 10" list correctly receives more weight than one on an unranked "Top 100" list.</p>';
        html += '</hgroup>';
        unrankedSources.forEach(srcKey => {
             const songCount = APP_DATA.config.sources[srcKey].song_count;
             html += createSlider('source_shadow', srcKey, `${sources[srcKey].full_name || srcKey} (${songCount} songs)`, 1.0, 100.0, 0.1);
        });
        html += '</article>';
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
        let displayVal;
        if (isBonus) {
            displayVal = ((numVal - 1) * 100).toFixed(1) + '%';
        } else if (isPercent) {
            displayVal = Math.round(numVal * 100) + '%';
        } else if (key === 'k_value' || key === 'cluster_threshold') {
            displayVal = Math.round(numVal).toString();
        } else {
            displayVal = parseFloat(numVal).toFixed(2);
        }
        document.getElementById(`val-${idBase}`).textContent = displayVal;
        
        const label = document.getElementById(`label-${idBase}`);
        // Approximate equality check for floating point values (within 0.0001)
        if (Math.abs(numVal - defaultVal) > 0.0001) {
            label.classList.add('customized-label');
        } else {
            label.classList.remove('customized-label');
        }
    }

    // Dynamic Helper Text Update for K and P
    if (key === 'k_value' || key === 'p_exponent') {
        const val = parseFloat(value);
        let v10, v25, v50;
        
        if (key === 'k_value') {
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
            helperEl.innerHTML = `Rank #10 is worth <strong>${Math.round(v10 * 100)}%</strong> of #1<br>Rank #25 is worth <strong>${Math.round(v25 * 100)}%</strong> of #1<br>Rank #50 is worth <strong>${Math.round(v50 * 100)}%</strong> of #1`;
        }
    }

    debouncedReRank();
};

