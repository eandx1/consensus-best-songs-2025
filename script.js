/**
 * Consensus 2025 - Core Logic
 * Handles: Data fetching, Weighted Ranking, UI Rendering, and State Sync
 */

let songData = null; // Original JSON (Immutable Source)
let userWeights = {}; 
let rankSensitivity = 25;
let consensusBonus = 0.05;
let currentDisplayLimit = 25; // Start with top 25
let rankedSongs = []; // Store the full ranked list

// 1. INITIALIZATION
async function init() {
    try {
        const response = await fetch('./data.json');
        songData = await response.json();
        
        // Load defaults from JSON config
        rankSensitivity = songData.config.ranking.rank_sensitivity;
        consensusBonus = songData.config.ranking.consensus_bonus;
        
        // Store defaults for reset/snap functionality
        defaultRankSensitivity = rankSensitivity;
        defaultConsensusBonus = consensusBonus;
        
        // Map source weights and store defaults
        Object.keys(songData.config.sources).forEach(key => {
            const weight = songData.config.sources[key].weight;
            userWeights[key] = weight;
            defaultWeights[key] = weight;
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
    rankedSongs = calculatedSongs
        .map(song => ({
            ...song,
            normalizedScore: song.rawScore / maxRaw
        }))
        .sort((a, b) => b.normalizedScore - a.normalizedScore)
        .map((song, index) => ({
            ...song,
            currentRank: index + 1
        }));

    renderList();
}

// 3. UI RENDERING
function renderList() {
    const container = document.getElementById('song-list-container');
    container.innerHTML = ''; // Clear loading state

    // Render only up to the current display limit
    const songsToDisplay = rankedSongs.slice(0, currentDisplayLimit);
    
    songsToDisplay.forEach(song => {
        const article = document.createElement('article');
        article.className = 'song-card';
        
        // Determine which YouTube ID to use for embed (prefer video_id, fallback to music_id)
        const embedId = song.media?.youtube?.video_id || song.media?.youtube?.music_id;
        
        // Build player HTML
        let playerHTML = '';
        if (embedId) {
            const escapedSongName = escapeHtml(song.name);
            playerHTML = `<lite-youtube videoid="${embedId}" playlabel="Play ${escapedSongName}"></lite-youtube>`;
        } else {
            // TODO: Fall back to using Spotify or other link for preview
            playerHTML = `<div style="aspect-ratio: 16/9; background: #000; display: flex; align-items: center; justify-content: center; color: var(--pico-muted-color); font-size: 0.8rem;">No preview available</div>`;
        }
        
        // Build Listen links dynamically based on available media
        const listenLinks = [];
        
        // YouTube video link
        if (song.media?.youtube?.video_id) {
            listenLinks.push(`<a href="https://www.youtube.com/watch?v=${song.media.youtube.video_id}" target="_blank">YouTube</a>`);
        }
        
        // YouTube Music link
        if (song.media?.youtube?.music_id) {
            listenLinks.push(`<a href="https://music.youtube.com/watch?v=${song.media.youtube.music_id}" target="_blank">YTM</a>`);
        }
        
        // Spotify link
        if (song.media?.spotify?.id) {
            listenLinks.push(`<a href="https://open.spotify.com/track/${song.media.spotify.id}" target="_blank">Spotify</a>`);
        }
        
        // Bandcamp link
        if (song.media?.bandcamp?.url) {
            listenLinks.push(`<a href="${escapeHtml(song.media.bandcamp.url)}" target="_blank">Bandcamp</a>`);
        }
        
        // Other link
        if (song.media?.other?.url) {
            listenLinks.push(`<a href="${escapeHtml(song.media.other.url)}" target="_blank">Other</a>`);
        }
        
        const listenHTML = listenLinks.length > 0 
            ? `<div class="listen-footer">LISTEN: ${listenLinks.join(' ')}</div>`
            : '';
        
        // Using the 3-column Grid structure from index.html
        article.innerHTML = `
            <button class="stats-trigger" data-song-index="${song.currentRank - 1}">ⓘ</button>
            <div class="card-grid">
                <div class="col-rank">
                    <span class="rank-number">#${song.currentRank}</span>
                </div>
                <div class="col-player">
                    ${playerHTML}
                </div>
                <div class="col-info">
                    <div class="header-group">
                        <h3>${escapeHtml(song.name)}</h3>
                        <h4>${escapeHtml(song.artist)}</h4>
                    </div>
                    <div class="sources-container" data-song-index="${song.currentRank - 1}">
                        ${song.sources.map(src => `<span class="source-item">${escapeHtml(src.name)}#${src.rank}</span>`).join('')}
                    </div>
                    ${listenHTML}
                </div>
            </div>
        `;
        
        // Attach event listeners using proper DOM methods to avoid injection issues
        const statsBtn = article.querySelector('.stats-trigger');
        if (statsBtn) {
            statsBtn.addEventListener('click', () => {
                openStats(song);
            });
        }
        
        const sourcesContainer = article.querySelector('.sources-container');
        if (sourcesContainer) {
            sourcesContainer.addEventListener('click', () => {
                openReview(song);
            });
        }
        
        container.appendChild(article);
    });
    
    // Update Load More button
    updateLoadMoreButton();
}

// Update the Load More button visibility and text
function updateLoadMoreButton() {
    const button = document.getElementById('load-more');
    const totalSongs = rankedSongs.length;
    
    if (currentDisplayLimit >= totalSongs) {
        // All songs are displayed
        button.style.display = 'none';
    } else {
        button.style.display = 'block';
        
        // Determine next limit and update button text
        let nextLimit;
        if (currentDisplayLimit < 100) {
            nextLimit = 100;
        } else if (currentDisplayLimit < 200) {
            nextLimit = 200;
        } else {
            nextLimit = totalSongs;
        }
        
        const remaining = totalSongs - currentDisplayLimit;
        const toShow = Math.min(nextLimit - currentDisplayLimit, remaining);
        
        if (nextLimit === totalSongs) {
            button.textContent = `Show All (${remaining} more)`;
        } else {
            button.textContent = `Show Top ${nextLimit} (${toShow} more)`;
        }
    }
}

// Helper function to escape HTML special characters
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// 4. MODAL & INTERACTION HANDLERS
window.openStats = function(song) {
    document.getElementById('stats-song-title').innerText = song.name;
    document.getElementById('stat-norm').innerText = song.normalizedScore.toFixed(3);
    document.getElementById('stat-count').innerText = song.list_count;
    document.getElementById('stat-mult').innerText = song.multiplier.toFixed(2) + 'x';
    document.getElementById('stat-raw').innerText = song.rawScore.toFixed(3);
    
    // Build source contributions list
    const contributionsList = document.getElementById('contributions-list');
    contributionsList.innerHTML = '';
    
    // Calculate each source's contribution
    const contributions = song.sources.map(src => {
        const weight = userWeights[src.name] || 1.0;
        const contribution = weight / (src.rank + rankSensitivity);
        return {
            name: src.name,
            rank: src.rank,
            contribution: contribution
        };
    });
    
    // Sort by contribution (highest first)
    contributions.sort((a, b) => b.contribution - a.contribution);
    
    // Render each contribution
    contributions.forEach(contrib => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td style="padding: 0.25rem 0.5rem;">${escapeHtml(contrib.name)} #${contrib.rank}</td>
            <td style="padding: 0.25rem 0.5rem; text-align: right; font-family: monospace;">${contrib.contribution.toFixed(4)}</td>
        `;
        contributionsList.appendChild(row);
    });
    
    document.getElementById('stats-modal').showModal();
};

window.openReview = function(song) {
    const container = document.getElementById('review-sources-container');
    container.innerHTML = ''; // Clear previous content
    
    // Display each source with its quote and link
    song.sources.forEach(src => {
        const sourceConfig = songData.config.sources[src.name];
        const sourceUrl = sourceConfig?.url || '#';
        const displayName = sourceConfig?.full_name || src.name;
        const quote = src.quote || 'No snippet available for this review.';
        
        const entry = document.createElement('div');
        entry.className = 'review-source-entry';
        entry.innerHTML = `
            <div class="review-source-name">${escapeHtml(displayName)} #${src.rank}</div>
            <div class="review-quote">"${escapeHtml(quote)}"</div>
            <a href="${escapeHtml(sourceUrl)}" target="_blank" class="review-link">Read Full Review ↗</a>
        `;
        container.appendChild(entry);
    });
    
    document.getElementById('review-modal').showModal();
};

// 5. URL PERSISTENCE (Syncing State)
function saveStateToURL() {
    const params = new URLSearchParams();
    
    // Only add parameters if they differ from defaults
    if (rankSensitivity !== defaultRankSensitivity) {
        params.set('s', rankSensitivity);
    }
    if (consensusBonus !== defaultConsensusBonus) {
        params.set('b', consensusBonus);
    }
    
    // Add source weights that differ from defaults
    Object.entries(userWeights).forEach(([source, weight]) => {
        if (weight !== defaultWeights[source]) {
            // Use a shortened key for URL brevity
            const key = 'w_' + source.replace(/[^a-zA-Z0-9]/g, '_').substring(0, 20);
            params.set(key, weight);
        }
    });
    
    const queryString = params.toString();
    const newURL = queryString ? `${location.pathname}?${queryString}` : location.pathname;
    window.history.replaceState({}, '', newURL);
}

function loadStateFromURL() {
    const params = new URLSearchParams(window.location.search);
    
    // Load rank sensitivity
    if (params.has('s')) {
        rankSensitivity = parseFloat(params.get('s'));
    }
    
    // Load consensus bonus
    if (params.has('b')) {
        consensusBonus = parseFloat(params.get('b'));
    }
    
    // Load source weights
    params.forEach((value, key) => {
        if (key.startsWith('w_')) {
            // Try to match the shortened key back to a source name
            const searchPattern = key.substring(2).toLowerCase();
            const matchedSource = Object.keys(userWeights).find(source => {
                const normalized = source.replace(/[^a-zA-Z0-9]/g, '_').substring(0, 20).toLowerCase();
                return normalized === searchPattern;
            });
            
            if (matchedSource) {
                userWeights[matchedSource] = parseFloat(value);
            }
        }
    });
}

// 6. LOAD MORE HANDLER
document.getElementById('load-more').addEventListener('click', () => {
    // Progress through the display limits: 25 → 100 → 200 → all
    if (currentDisplayLimit < 100) {
        currentDisplayLimit = 100;
    } else if (currentDisplayLimit < 200) {
        currentDisplayLimit = 200;
    } else {
        currentDisplayLimit = rankedSongs.length;
    }
    
    renderList();
});

// 7. CONFIGURATION DIALOG
const configDialog = document.getElementById('config-dialog');
const configBtn = document.getElementById('config-btn');
const closeConfigBtn = document.getElementById('close-config');
const applyConfigBtn = document.getElementById('apply-config');
const resetConfigBtn = document.getElementById('reset-config');

// Store default values for snap-to and reset
let defaultRankSensitivity = 25;
let defaultConsensusBonus = 0.05;
let defaultWeights = {};

// Open configuration dialog
configBtn.addEventListener('click', () => {
    populateConfigDialog();
    configDialog.showModal();
});

// Close configuration dialog
closeConfigBtn.addEventListener('click', () => {
    configDialog.close();
});

// Apply button just closes the dialog (changes are already applied via debounce)
applyConfigBtn.addEventListener('click', () => {
    configDialog.close();
});

// Reset to defaults
resetConfigBtn.addEventListener('click', () => {
    // Reset ranking parameters
    rankSensitivity = defaultRankSensitivity;
    consensusBonus = defaultConsensusBonus;
    
    // Reset source weights
    Object.keys(defaultWeights).forEach(source => {
        userWeights[source] = defaultWeights[source];
    });
    
    // Update UI
    populateConfigDialog();
    
    // Recalculate and update URL
    debouncedUpdate();
});

// Helper function to update label color based on whether value differs from default
function updateLabelHighlight(labelElement, currentValue, defaultValue) {
    if (Math.abs(currentValue - defaultValue) > 0.001) {
        labelElement.style.color = '#f59e0b'; // Amber/orange highlight
    } else {
        labelElement.style.color = ''; // Reset to default
    }
}

// Populate configuration dialog with current values
function populateConfigDialog() {
    // Set ranking parameter values
    const sensitivitySlider = document.getElementById('rank-sensitivity');
    const bonusSlider = document.getElementById('consensus-bonus');
    
    sensitivitySlider.value = rankSensitivity;
    bonusSlider.value = consensusBonus;
    
    document.getElementById('val-sensitivity').textContent = rankSensitivity;
    document.getElementById('val-bonus').textContent = (consensusBonus * 100).toFixed(1);
    
    // Update label highlights for ranking parameters
    const sensitivityLabel = document.querySelector('label[for="rank-sensitivity"]');
    const bonusLabel = document.querySelector('label[for="consensus-bonus"]');
    updateLabelHighlight(sensitivityLabel, rankSensitivity, defaultRankSensitivity);
    updateLabelHighlight(bonusLabel, consensusBonus, defaultConsensusBonus);
    
    // Generate source weight sliders
    const container = document.getElementById('source-weights-container');
    container.innerHTML = '';
    
    Object.keys(songData.config.sources).forEach(sourceName => {
        const weight = userWeights[sourceName];
        const defaultWeight = defaultWeights[sourceName];
        
        const fieldset = document.createElement('fieldset');
        fieldset.style.marginBottom = '1rem';
        
        const label = document.createElement('label');
        label.setAttribute('for', `weight-${sourceName}`);
        label.dataset.source = sourceName; // Add data attribute for easy lookup
        
        // Use full_name if available, otherwise use sourceName
        const displayName = songData.config.sources[sourceName]?.full_name || sourceName;
        
        const sourceLabelSpan = document.createElement('span');
        sourceLabelSpan.textContent = displayName + ': ';
        sourceLabelSpan.style.fontSize = '0.85rem';
        
        const valueSpan = document.createElement('span');
        valueSpan.id = `val-weight-${sourceName}`;
        valueSpan.textContent = weight.toFixed(2);
        valueSpan.style.fontWeight = 'bold';
        
        const slider = document.createElement('input');
        slider.type = 'range';
        slider.id = `weight-${sourceName}`;
        slider.min = '0';
        slider.max = '2';
        slider.step = '0.01';
        slider.value = weight;
        slider.dataset.source = sourceName;
        slider.dataset.default = defaultWeight;
        
        // Add slider with wrapper
        const sliderWrapper = document.createElement('div');
        sliderWrapper.style.position = 'relative';
        
        label.appendChild(sourceLabelSpan);
        label.appendChild(valueSpan);
        sliderWrapper.appendChild(slider);
        label.appendChild(sliderWrapper);
        
        // Update label highlight based on current vs default value
        updateLabelHighlight(label, weight, defaultWeight);
        
        fieldset.appendChild(label);
        container.appendChild(fieldset);
        
        // Add event listener for this slider
        slider.addEventListener('input', handleWeightSliderChange);
    });
    
    // Add listeners for ranking parameter sliders
    sensitivitySlider.removeEventListener('input', handleSensitivityChange);
    bonusSlider.removeEventListener('input', handleBonusChange);
    sensitivitySlider.addEventListener('input', handleSensitivityChange);
    bonusSlider.addEventListener('input', handleBonusChange);
}

// Handle rank sensitivity slider change
function handleSensitivityChange(e) {
    const value = parseFloat(e.target.value);
    const defaultVal = defaultRankSensitivity;
    
    // Snap to default if within threshold
    if (Math.abs(value - defaultVal) < 1) {
        e.target.value = defaultVal;
        rankSensitivity = defaultVal;
    } else {
        rankSensitivity = value;
    }
    
    document.getElementById('val-sensitivity').textContent = rankSensitivity;
    
    // Update label highlight
    const sensitivityLabel = document.querySelector('label[for="rank-sensitivity"]');
    updateLabelHighlight(sensitivityLabel, rankSensitivity, defaultRankSensitivity);
    
    debouncedUpdate();
}

// Handle consensus bonus slider change
function handleBonusChange(e) {
    const value = parseFloat(e.target.value);
    const defaultVal = defaultConsensusBonus;
    
    // Snap to default if within threshold
    if (Math.abs(value - defaultVal) < 0.005) {
        e.target.value = defaultVal;
        consensusBonus = defaultVal;
    } else {
        consensusBonus = value;
    }
    
    document.getElementById('val-bonus').textContent = (consensusBonus * 100).toFixed(1);
    
    // Update label highlight
    const bonusLabel = document.querySelector('label[for="consensus-bonus"]');
    updateLabelHighlight(bonusLabel, consensusBonus, defaultConsensusBonus);
    
    debouncedUpdate();
}

// Handle source weight slider change
function handleWeightSliderChange(e) {
    const sourceName = e.target.dataset.source;
    const value = parseFloat(e.target.value);
    const defaultVal = parseFloat(e.target.dataset.default);
    
    // Snap to default if within threshold
    if (Math.abs(value - defaultVal) < 0.05) {
        e.target.value = defaultVal;
        userWeights[sourceName] = defaultVal;
    } else {
        userWeights[sourceName] = value;
    }
    
    document.getElementById(`val-weight-${sourceName}`).textContent = userWeights[sourceName].toFixed(2);
    
    // Update label highlight
    const label = document.querySelector(`label[for="weight-${sourceName}"]`);
    updateLabelHighlight(label, userWeights[sourceName], parseFloat(e.target.dataset.default));
    
    debouncedUpdate();
}

// Debounced update function (250ms delay)
let updateTimeout = null;
function debouncedUpdate() {
    if (updateTimeout) {
        clearTimeout(updateTimeout);
    }
    
    updateTimeout = setTimeout(() => {
        updateRankings();
        saveStateToURL();
    }, 250);
}

// Kick off
init();