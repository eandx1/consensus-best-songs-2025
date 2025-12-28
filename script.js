/**
 * APP STATE & CONFIGURATION
 */
let APP_DATA = null;
let CURRENT_CONFIG = {};
let DISPLAY_LIMIT = 25;

const UI = {
    songList: document.getElementById('song-list'),
    loadMoreBtn: document.getElementById('load-more'),
    settingsContent: document.getElementById('settings-content')
};

/**
 * UTILS
 */
const escapeHtml = (str) => {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
};

/**
 * RANKING ENGINE
 */
const RankingEngine = {
    getDecayValue(rank, mode, config) {
        let val = 0;
        if (mode === 'consensus') {
            val = (1 + config.k_value) / (rank + config.k_value);
        } else {
            val = 1.0 / Math.pow(rank, config.p_exponent);
        }

        // Apply Top Rank Bonuses
        if (rank === 1) val *= config.rank1_bonus;
        else if (rank === 2) val *= config.rank2_bonus;
        else if (rank === 3) val *= config.rank3_bonus;
        
        return val;
    },

    calculateSourceNormFactors(sources, config) {
        const normFactors = {};
        Object.entries(sources).forEach(([name, srcConfig]) => {
            const effLen = Math.max(srcConfig.song_count, config.min_norm_length);
            let totalPoints = 0;
            // Handle specific NPR offset logic if needed from Python
            const startR = (name === "NPR Top 125") ? 26 : 1;
            
            for (let r = startR; r <= effLen; r++) {
                totalPoints += this.getDecayValue(r, config.decay_mode, config);
            }
            normFactors[name] = totalPoints;
        });
        return normFactors;
    },

    compute(songs, config, sources) {
        const normFactors = this.calculateSourceNormFactors(sources, config);
        
        const rankedSongs = songs.map(song => {
            let totalNormalizedScore = 0;
            let ranks = [];
            let clustersSeen = new Set();

            song.sources.forEach(srcEntry => {
                const srcName = srcEntry.name;
                const srcCfg = sources[srcName];
                if (!srcCfg) return;

                const rank = srcEntry.uses_shadow_rank ? srcCfg.shadow_rank : srcEntry.rank;
                ranks.push(rank);

                if (rank <= config.cluster_threshold) {
                    clustersSeen.add(srcCfg.cluster);
                }

                const normPts = this.getDecayValue(rank, config.decay_mode, config) / normFactors[srcName];
                totalNormalizedScore += (normPts * srcCfg.weight);
            });

            // Multipliers
            const c_mul = 1 + (config.consensus_boost * Math.log(ranks.length));
            
            // Standard Deviation for Provocation
            let p_mul = 1.0;
            if (ranks.length > 1) {
                const mean = ranks.reduce((a, b) => a + b) / ranks.length;
                const stdDev = Math.sqrt(ranks.map(x => Math.pow(x - mean, 2)).reduce((a, b) => a + b) / ranks.length);
                p_mul = 1 + (config.provocation_boost * (stdDev / 100));
            }

            const cl_mul = clustersSeen.size > 0 ? 1 + (config.cluster_boost * (clustersSeen.size - 1)) : 1.0;

            const finalScore = totalNormalizedScore * c_mul * p_mul * cl_mul;

            return {
                ...song,
                finalScore,
                stats: { totalNormalizedScore, c_mul, p_mul, cl_mul, listCount: ranks.length }
            };
        });

        return rankedSongs.sort((a, b) => b.finalScore - a.finalScore);
    }
};

/**
 * CORE APP LOGIC
 */
async function init() {
    const response = await fetch('data.json');
    APP_DATA = await response.json();
    
    // Initialize config with defaults, then override with URL params
    CURRENT_CONFIG = JSON.parse(JSON.stringify(APP_DATA.config));
    syncStateFromURL();
    
    render();
    setupEventListeners();
}

function render() {
    const results = RankingEngine.compute(APP_DATA.songs, CURRENT_CONFIG.ranking, CURRENT_CONFIG.sources);
    const visible = results.slice(0, DISPLAY_LIMIT);
    
    UI.songList.innerHTML = visible.map((song, idx) => `
        <article class="song-card">
            <div class="grid">
                <div class="rank-large">${idx + 1}</div>
                <div>
                    <lite-youtube videoid="${song.media.youtube.video_id || song.media.youtube.music_id}"></lite-youtube>
                </div>
                <div>
                    <h4>${escapeHtml(song.name)}</h4>
                    <p>${escapeHtml(song.artist)}</p>
                    <small>${song.sources.map(s => `${s.name}#${s.rank || '★'}`).join(' · ')}</small>
                </div>
            </div>
        </article>
    `).join('');
}

function syncStateFromURL() {
    const params = new URLSearchParams(window.location.search);
    // Logic to loop through params and update CURRENT_CONFIG
}

function setupEventListeners() {
    // Dialog handling
    document.querySelectorAll('[id^="open-"]').forEach(btn => {
        btn.onclick = () => document.getElementById(`modal-${btn.id.split('-')[1]}`).showModal();
    });
    
    document.querySelectorAll('.close-modal').forEach(btn => {
        btn.onclick = (e) => e.target.closest('dialog').close();
    });

    UI.loadMoreBtn.onclick = () => {
        DISPLAY_LIMIT += 75; // Simplification of the 25 -> 100 -> 200 logic
        render();
    };
}

init();