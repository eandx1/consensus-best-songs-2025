/**
 * Consensus 2025 - Core Logic
 * Handles: Data fetching, Weighted Ranking, UI Rendering, and State Sync
 */

let songData = null; // Original JSON (Immutable Source)
let userWeights = {}; 
let rankSensitivity = 25;
let consensusBonus = 0.05;

// 1. INITIALIZATION
async function init() {
    try {
        const response = await fetch('./data.json');
        songData = await response.json();
        
        // Load defaults from JSON config
        rankSensitivity = songData.config.ranking.rank_sensitivity;
        consensusBonus = songData.config.ranking.consensus_bonus;
        
        // Map source weights
        Object.keys(songData.config.sources).forEach(key => {
            userWeights[key] = songData.config.sources[key].weight;
        });

        // Sync with URL if parameters exist
        loadStateFromURL();
        
        // Initial Render
        updateRankings();
    } catch (err) {
        console.error("Failed to load consensus data:", err);
    }
}

// 2. RANKING ENGINE
function updateRankings() {
    // A. Calculate Raw Scores for all songs
    const calculatedSongs = songData.songs.map(song => {
        // Weighted Rank Decay: sum(weight / (rank + sensitivity))
        const baseScore = song.sources.reduce((acc, src) => {
            const weight = userWeights[src.name] || 1.0;
            return acc + (weight / (src.rank + rankSensitivity));
        }, 0);

        // Consensus Multiplier: 1 + (bonus * ln(count))
        const multiplier = 1 + (consensusBonus * Math.log(song.list_count));
        const rawScore = baseScore * multiplier;

        return { ...song, rawScore, multiplier, baseScore };
    });

    // B. Find Max Raw Score for Normalization
    const maxRaw = Math.max(...calculatedSongs.map(s => s.rawScore));

    // C. Normalize, Sort, and Assign Rank
    const rankedList = calculatedSongs
        .map(song => ({
            ...song,
            normalizedScore: song.rawScore / maxRaw
        }))
        .sort((a, b) => b.normalizedScore - a.normalizedScore)
        .map((song, index) => ({
            ...song,
            currentRank: index + 1
        }));

    renderList(rankedList);
}

// 3. UI RENDERING
function renderList(songs) {
    const container = document.getElementById('song-list-container');
    container.innerHTML = ''; // Clear loading state

    songs.slice(0, 100).forEach(song => {
        const article = document.createElement('article');
        article.className = 'song-card';
        
        // Using the 3-column Grid structure from index.html
        article.innerHTML = `
            <button class="stats-trigger" onclick="openStats('${song.name.replace(/'/g, "\\'")}', ${song.normalizedScore}, ${song.rawScore}, ${song.multiplier}, ${song.list_count})">ⓘ</button>
            <div class="card-grid">
                <div class="col-rank">
                    <span class="rank-number">#${song.currentRank}</span>
                </div>
                <div class="col-player">
                    <lite-youtube videoid="${song.media.youtube.video_id}" playlabel="Play ${song.name}"></lite-youtube>
                </div>
                <div class="col-info">
                    <div class="header-group">
                        <h3>${song.name}</h3>
                        <h4>${song.artist}</h4>
                    </div>
                    ${song.archetype ? `<div class="archetype-badge">${song.archetype}</div>` : ''}
                    <div class="sources-list">
                        ${song.sources.map(src => `
                            <button class="source-pill" onclick="openReview('${src.name}', '${src.quote || ''}', '${songData.config.sources[src.name].url}')">
                                ${src.name} #${src.rank}
                            </button>
                        `).join('')}
                    </div>
                    <div class="listen-footer">
                        LISTEN: 
                        <a href="https://open.spotify.com/track/${song.media.spotify.id}" target="_blank">Spotify</a>
                        <a href="https://music.youtube.com/watch?v=${song.media.youtube.music_id}" target="_blank">YT Music</a>
                        ${song.media.bandcamp ? `<a href="${song.media.bandcamp.url}" target="_blank">Bandcamp</a>` : ''}
                    </div>
                </div>
            </div>
        `;
        container.appendChild(article);
    });
}

// 4. MODAL & INTERACTION HANDLERS
window.openStats = function(title, norm, raw, mult, count) {
    document.getElementById('stats-song-title').innerText = title;
    document.getElementById('stat-norm').innerText = norm.toFixed(3);
    document.getElementById('stat-raw').innerText = raw.toFixed(3);
    document.getElementById('stat-mult').innerText = mult.toFixed(2) + 'x';
    document.getElementById('stat-count').innerText = count;
    document.getElementById('stats-modal').showModal();
};

window.openReview = function(name, quote, url) {
    document.getElementById('review-source-name').innerText = name;
    document.getElementById('review-quote').innerText = quote || "No snippet available for this review.";
    document.getElementById('review-link').href = url;
    document.getElementById('review-modal').showModal();
};

// 5. URL PERSISTENCE (Syncing State)
function saveStateToURL() {
    const params = new URLSearchParams();
    params.set('s', rankSensitivity);
    params.set('b', consensusBonus);
    Object.entries(userWeights).forEach(([site, weight]) => {
        if (weight !== 1.0) params.set(site, weight);
    });
    window.history.replaceState({}, '', `${location.pathname}?${params}`);
}

function loadStateFromURL() {
    const params = new URLSearchParams(window.location.search);
    if (params.has('s')) rankSensitivity = parseFloat(params.get('s'));
    if (params.has('b')) consensusBonus = parseFloat(params.get('b'));
    // Additional logic for site weights here...
}

// Kick off
init();