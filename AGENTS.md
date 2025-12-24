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
- Video Embeds: Use the `lite-youtube` web component (v1+) when YouTube or YouTube Music IDs exist. Include it via CDN in the `<head>`: `<script type="module" src="https://cdn.jsdelivr.net/npm/@justinribeiro/lite-youtube@1/lite-youtube.js"></script>`. Version 1+ is required for `::part(playButton)` styling support.
- Data: All data is from a local `data.json` file
- State Management: Treat `data.json` as an immutable source of truth. All rankings must be calculated as a "derived view" by applying default or user-defined weights to the source data
- URL Persistence: Use the native URLSearchParams API to synchronize configuration state (weights and ranking parameters) to the URL query string. The application must be "deep-linkable," meaning if a user shares a URL, another user opening it should see the exact same custom ranking.
- Performance: The ranking algorithm should be efficient enough to run on input events (sliders) without blocking the UI thread
- Constraints: No build steps (no Webpack/Vite), no frameworks (no React/Vue)
- Design Style: Clean, semantic, and responsive using Pico CSS defaults
- Ensure font and colors can be easily switched to different themes

# UI Design

"Dark mode" style website with clean, responsive UI for both desktop and mobile.

## Header

- Site title: "Consensus Best Songs 2025"
- "Settings" button to open configuration modal
- "About" link that opens GitHub repository in new tab (https://github.com/eandx1/consensus-best-songs-2025)

## Song Card List

The primary focus is a ranked list of song cards showing:

- Song rank number (large, left-aligned on desktop)
- YouTube video player preview (uses `video_id` if available, falls back to `music_id`)
  - Play button customized to be smaller (68x48px) and positioned in lower right corner via `::part(playButton)` styling
- Song title and artist
- Sources list: Single clickable line showing all sources in "SourceName#Rank" format, separated by middot (·)
  - Sources wrap but each "SourceName#Rank" stays together (no line breaks within)
  - Clicking opens Reviews modal with all sources, quotes, and review links
- "LISTEN:" links dynamically generated based on available media:
  - "YouTube" link (if `video_id` exists)
  - "YTM" link (if `music_id` exists) - both can appear if both IDs present
  - "Spotify" link (if `spotify.id` exists)
  - "Bandcamp" link (if `bandcamp.url` exists)
  - "Other" link (if `other.url` exists)
- Info (ⓘ) icon in top right that opens Ranking Stats modal

**Note**: Archetype badges have been removed from the current implementation.

By default, the top 25 are shown. Users can progressively load more: top 100, top 200, then all songs.

## Interactivity

### State Syncing

On Initialization: Check `window.location.search`. If parameters exist, override the defaults from `data.json`.

On Slider Change: Update the `URLSearchParams` object and use `history.replaceState` to update the browser's address bar without reloading the page.

### Overlays/Modals

Three semantic HTML `<dialog>` elements are used, styled with Pico CSS:

1. **Settings Modal**: Title "Settings" - for adjusting ranking parameters and source weights
2. **Ranking Stats Modal**: Title "Ranking: <song name>" - shows detailed scoring breakdown
3. **Reviews Modal**: Title "Reviews" - shows all source reviews with quotes and links

### Settings Modal

Modal header shows "Settings". Contains two sections:

**Ranking Parameters** (appears first):
- Rank Sensitivity slider: range 0-50, step 1, default from `data["config"]["ranking"]["rank_sensitivity"]`
- Consensus Boost slider: range 0%-10%, step 0.1%, default from `data["config"]["ranking"]["consensus_boost"]`

**Source Weights** (appears second):
- One slider per source: range 0.0-2.0, step 0.01, default from each source's `weight` in `data["config"]["sources"]`
- Display the source's `full_name` if available, otherwise use the source key name
- When a value differs from default, the label text is highlighted in amber (#f59e0b) to indicate customization

UI behaviors:
- Values update in real-time (debounced by 250ms)
- Rankings recalculate automatically as user adjusts sliders
- Snap-to-default functionality when slider value is within threshold of default
- "Defaults" button resets all values
- "Close" button dismisses modal
- Modal has unified scroll (no sub-scrolling sections)

Adjusting parameters triggers debounced ranking recalculation and URL state update.

### Reviews Modal

Modal header shows "Reviews" (no song name to prevent overflow).

Displays all sources for a song in order (preserving source array order from data):
- Each source entry shows:
  - Source name (use `full_name` from config if available, otherwise source key) with rank: "Source Name #Rank"
  - Quote in italic, wrapped in double quotes
  - "Read Full Review ↗" link (right-justified) to source URL
- Modal content is scrollable for songs with many sources
- Entries separated by horizontal dividers

### Ranking Stats Modal

Modal header shows "Ranking: <song name>".

Displays scoring details in order:
1. Normalized Score (the final 0-1 score)
2. Review List Count (number of lists citing the song)
3. Consensus Multiplier (the bonus applied)
4. Raw Score (base score before normalization)
5. Source Contributions section:
   - Each source listed with rank and its calculated contribution
   - Format: "Source Name #Rank: 0.xxxx"
   - Sorted by contribution value (highest first)
   - Scrollable if many sources

Footer shows the formula: "Score = Raw Score × Consensus Multiplier"

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

# Implementation Details

## YouTube Embed Priority

For the main video player embed, prefer `video_id` over `music_id`:
```javascript
const embedId = song.media?.youtube?.video_id || song.media?.youtube?.music_id;
```

## Listen Links Logic

Generate links dynamically based on available media:
- YouTube link if `video_id` exists → `https://www.youtube.com/watch?v={video_id}`
- YTM link if `music_id` exists → `https://music.youtube.com/watch?v={music_id}`
- Both can appear if both IDs are present
- Spotify link if `spotify.id` exists
- Bandcamp link if `bandcamp.url` exists  
- Other link if `other.url` exists

## Video Player Customization

The `lite-youtube` play button is customized via `::part(playButton)`:
- Size: 68x48px (standard YouTube button size)
- Position: lower right corner (bottom: 12px, right: 12px)
- Opacity: 0.9 default, 1.0 on hover
- Slight scale-up on hover for feedback

## Security

Always use `escapeHtml()` helper function when inserting user-generated or data-driven content into HTML to prevent XSS attacks.

## Responsive Design

- Desktop: Uses CSS Grid with 3 columns (rank, video, info)
- Video column uses `minmax(200px, 320px)` for responsive scaling
- Mobile: Stacked layout with flexbox
- Sources list wraps with `white-space: nowrap` on individual items

## Progressive Loading

- Initial: 25 songs
- Button shows: "Show Top 100 (75 more)"
- Then: "Show Top 200 (100 more)"
- Finally: "Show All (X more)"
- Button hidden when all songs displayed

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
