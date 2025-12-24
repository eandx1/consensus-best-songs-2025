# Role

You are an expert at frontend web design and implementation.

# Project

A "Consensus Best Songs of 2025" site that displays the best songs of the year collected from many different source lists and reranked to determine the consensus best songs.

Users can adjust source weights and two ranking function parameters to dynamically change the ranks and reorder the list of songs. Customized parameters are updated in the URL for easy sharing.

# Technical Design

- Static site hosted on Github Pages
- Plain semantic HTML5
- Vanilla JavaScript (ES6+)
- Pico CSS
- Video Embeds: Use the `lite-youtube` web component when YouTube or YouTube Music IDs exist. Include it via CDN in the `<head>: <script type="module" src="https://cdn.jsdelivr.net/npm/@justinribeiro/lite-youtube@1.5.0/lite-youtube.js"></script>`
- Data: All data is from a local `data.json` file
- State Management: Treat `data.json` as an immutable source of truth. All rankings must be calculated as a "derived view" by applying default or user-defined weights to the source data
- URL Persistence: Use the native URLSearchParams API to synchronize configuration state (weights and ranking parameters) to the URL query string. The application must be "deep-linkable," meaning if a user shares a URL, another user opening it should see the exact same custom ranking.
- Performance: The ranking algorithm should be efficient enough to run on input events (sliders) without blocking the UI thread
- Constraints: No build steps (no Webpack/Vite), no frameworks (no React/Vue)
- Design Style: Clean, semantic, and responsive using Pico CSS defaults
- Ensure font and colors can be easily switched to different themes

# UI Design

"Dark mode" style website with clean, responsive UI for both desktop and mobile.

## Top

- Include the site title "Consensus Best Songs of 2025"
- Include a "Configuration" button (could use a gear icon)
- Include an "About" link last that links to the README.md in this repo

## Song Card List

The primary focus is a ranked list of song cards showing:

- Song title
- Artist list
- List of source review sites citing it and their ranks in Site#Rank format with links
- One or more of Spotify, YouTube, Bandcamp, or Other link
- Song thumbnail facade and link to play song (when data available)
- Optional: Archetype badge
- A faint info icon in the top right that opens up a modal with stats about the ranking 

By default, the top 25 are shown, but the user can expand to the top 100, top 200, and then all.

## Interactivity

### State Syncing

On Initialization: Check `window.location.search`. If parameters exist, override the defaults from `data.json`.

On Slider Change: Update the `URLSearchParams` object and use `history.replaceState` to update the browser's address bar without reloading the page.

### Overlays

Overlays: Use semantic HTML `<dialog>` elements for the Configuration and Source Quote overlays. Leverage Pico CSS's built-in styles for modals.

### Configuration

Clicking the configuration button in the header should open an overlay that lets the user adjust the following with horizontal sliders. Actual values should be shown at least in tool-tip like overlays when moved. The default should be marked with a small vertical line and have snap-to functionality.

- Ranking parameters
  - Rank sensitivity in the weighted rank decay function. Default is in `data["config"]["ranking"]["rank_sensitivity"]`. Its range is 0 to 50.
  - Consensus boost, which is a percentage from 0% to 10%. Default is in `data["config"]["ranking"]["consensus_boost"]`
- Source weights
  - These are weights from 0.0 to 2.0 per source. Defaults are in `"weight"` in `data["config"]["sources"]`

Adjusting these parameters recomputes the score for each song. The song list is then automatically re-ranked by descending score and the UI is updated. Implementation of the ranking recalculation should be debounced (e.g., 250ms) to ensure the UI remains fluid while the user is actively sliding a range input.

### Source review quotes

Each source for a song also has a quote from the review. Clicking on an "info" icon near the source list should open an overlay showing the sources, their ranks, and a quote for each with a link to the full review.

# Data Layout

The data JSON is structured as follows:

```
root
├── config
│   ├── ranking
│   │   ├── rank_sensitivity: number (int)        // Decay for score calculation
│   │   └── consensus_bonus: number (float)       // Multiplier for multi-list presence
│   └── sources
│       └── [SITE_NAME]                          // e.g., "Billboard (Staff Picks)"
│           ├── url: string (url)
│           ├── full_name: string (optional)
│           └── weight: number (float)           // Default rank decay weight
└── songs (array)
    └── [object]
        ├── id: string (ISRC or internal ID)
        ├── artist: string
        ├── name: string
        ├── sources (array)
        │   └── [SITE]
        │       ├── name: string                   // Must match a key in config.sources
        │       ├── rank: number (int/float)
        │       └── quote: string (optional)       // Snippet from the review
        ├── list_count: number (int)               // Total number of lists citing the song
        ├── media
        │   ├── youtube (optional)
        │   │   ├── music_id: string (optional)
        │   │   └── video_id: string (optional)
        │   ├── spotify (optional)
        │   │   └── id: string
        │   ├── bandcamp (optional)
        │   │    └── url: string (url)
        │   └── other (optional)
        │       └── url: string (url)
        └── archetype (optional): string         // e.g., "Critical Darling 🧠"
```

# Samples

See [sample_data.json](samples/sample_data.json) for the JSON data format and 3 sample songs.

See [song_sample.html](samples/song_sample.html) for inspiration for the UI style for a single song card in the list.

# Workflow Guidelines

1. **Atomic Changes:** Suggest one feature or one bug fix at a time.
2. **Verification:** After writing code, explain how it interacts with the `data.json` structure.
3. **No Placeholders:** Write complete code blocks; avoid "insert logic here" comments.

# Ranking Function

The ranking function is based on two parts: 1) A weighted rank decay 2) A consensus boost multiplier.

```
base_score = sum over sources for the song of (source weight / (source rank + rank_sensitivity))

consensus_multiplier = `1 + (consensus_bonus * ln(list_count))`

raw_score = base_score * consensus_multiplier

The raw_scores are then normalizer to [0.0, 1.0] by dividing over the maximum raw_score across all songs in the data.
```
