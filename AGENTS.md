# Role

You are an expert at frontend web design and implementation.

# Project

A "Consensus Best Songs of 2025" site that displays the best songs of the year collected from many different source lists and reranked to determine the consensus best songs.

Users can adjust source weights and several ranking function parameters to dynamically change the ranks and reorder the list of songs. Customized parameters are updated in the URL for easy sharing.

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

## Inspriation

Think of the Pico CSS website, the IntelliJ Darcula theme, and the Solarized Dark terminal theme for color and font inspiration.

## Header

- Site title: "Consensus Best Songs 2025"
- "Settings" button to open configuration modal
- "About" link that opens an about modal

## Song Card List

The primary focus is a ranked list of song cards showing:

- Song rank number (large, left-aligned on desktop)
- YouTube video player preview (uses `video_id` if available, falls back to `music_id`)
  - Play button customized to white on gray with high transparency
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

By default, the top 25 are shown. Users can progressively load more: top 100, top 200, top 500, then all songs.

## Interactivity

### State Syncing

On Initialization: Check `window.location.search`. If parameters exist, override the defaults from `data.json`.

On Slider Change: Update the `URLSearchParams` object and use `history.replaceState` to update the browser's address bar without reloading the page.

### Overlays/Modals

Four semantic HTML `<dialog>` elements are used, styled with Pico CSS:

1. **Settings Modal**: Title "Settings" - for adjusting ranking parameters and source weights
2. **Ranking Stats Modal**: Title "Ranking: <song name>" - shows detailed scoring breakdown
3. **Reviews Modal**: Title "Reviews" - shows all source reviews with quotes and links
4. **About Modal**: Shows a description of the site and links to the Github Repo

### Settings Modal

Modal header shows "Settings". Contains three sections:

**Ranking Parameters** (appears first):

- Decay Mode, 2 button choice defaulting to "consensus" with the other option being "conviction", default from `data["config"]["ranking"]["decay_mode"]`, url parameter parameter `decay_mode`
- Rank Decay (K), slider, integer range 0-50 in 1 increments, only shown when Decay Mode is "consensus", default from `data["config"]["ranking"]["k_value"]`, url parameter `k_value`
- Power-Law Decay (P), slider, float range 0.0 to 1.1 in 0.01 increments, default from `data["config"]["ranking"]["p_exponent"]`, url parameter `p_exponent`
- Consensus Boost, slider, percentage range from 0% to 10% in 1% increments, default from `data["config"]["ranking"]["consensus_boost"]`, url parameter `consensus_boost`
- Provocation Boost, slider, percentage range from 0% to 25% in 1% increments, default from `data["config"]["ranking"]["provocation_boost"]`, url parameter `provocation_boost`
- Cluster Boost, slider, percentage range from 0% to 10% in 1% increments, default from `data["config"]["ranking"]["cluster_boost"]`, url parameter `cluster_boost`
- Cluster Threshold, slider, integer range 0 to 100 in 1 increments, default from `data["config"]["ranking"]["cluster_threshold"]`, url parameter `cluster_threshold`
- Rank 1 Bonus, slider, percentage range 0% to 20% in 1% increments, default from `data["config"]["ranking"]["rank1_bonus"]`, url parameter `rank1_bonus`
- Rank 2 Bonus, slider, percentage range 0% to 20% in 1% increments, default from `data["config"]["ranking"]["rank2_bonus"]`, url parameter `rank2_bonus`
- Rank 3 Bonus, slider, percentage range 0% to 20% in 1% increments, default from `data["config"]["ranking"]["rank3_bonus"]`, url parameter `rank3_bonus`

When a value differs from default, the label text is highlighted indicate customization.

**Source Weights** (appears second):

- One slider per source: range 0.0-1.5, step 0.01, default from each source's `weight` in `data["config"]["sources"]`
- Display the source's `full_name` if available, otherwise use the source key name
- When a value differs from default, the label text is highlighted indicate customization

**Shadow Ranks** (appears third):
Some sources are unranked lists so use "shadow ranks" instead of real ranks.

If a source has `data["config"]["sources"][source name]["type"]` of `unranked` then its `data["config"]["sources"][source name]["shadow_rank"]` will have its default shadow rank.

For each such source with a shadow rank, provide its name (`full_name` from config if available) and a float slider from 1.0 through 100.0 in 0.1 increments.

The URL parameter should be lowercase source name with spaces or other non-letter characters replaced by underscores.

UI behaviors:

- Values update in real-time (debounced by 250ms)
- Rankings recalculate automatically as user adjusts sliders
- "Defaults" button resets all values
- "Close" button dismisses modal
- Modal has unified scroll (no sub-scrolling sections)

Adjusting parameters triggers debounced ranking recalculation and URL state update.

### Reviews Modal

Modal header shows "Reviews" (no song name to prevent overflow).

Displays all sources for a song in order (preserving source array order from data):

- Each source entry shows:
  - Source name (use `full_name` from config if available, otherwise source key) with rank: "Source Name #Rank"
  - Use the source's `rank` if available. If `uses_shadow_rank` is TRUE, use the source's shadow rank
  - "Read Full Review" link (right-justified) to source URL
- Modal content is scrollable for songs with many sources
- Entries separated by horizontal dividers

### Ranking Stats Modal

Modal header shows "Ranking".

Displays scoring details in order:

1. Normalized Score (the final 0-1 score)
2. Review List Count (number of lists citing the song)
3. Consensus Multiplier (the bonus applied)
4. Provcation Multiplier (the bonus applied)
5. Cluster Multiplier (the bonus applied)
6. Raw Score (base score before normalization)
7. Source Contributions section:
   - Each source listed with rank (or shadow rank) and its calculated contribution
   - Format: "Source Name #Rank: 0.xxxx"
   - Sorted by contribution value (highest first)
   - Scrollable if many sources

# Data Layout

The data JSON is structured as follows:

```
root (object)
├── config (object)
│   ├── ranking (object)
│   │   ├── k_value (integer)
│   │   ├── p_exponent (float)
│   │   ├── cluster_threshold (integer)
│   │   ├── consensus_boost (float)
│   │   ├── provocation_boost (float)
│   │   ├── cluster_boost (float)
│   │   ├── rank1_bonus (float)
│   │   ├── rank2_bonus (float)
│   │   ├── rank3_bonus (float)
│   │   └── decay_mode (string)
│   ├── cluster_metadata (object: map of cluster to cluster_config)
│   │   └── [cluster] (object)
│   │       ├── emoji (string)
│   │       └── descriptor (string)
│   └── sources (object: map of source_name to source_config)
│       └── [source_name] (object)
│           ├── url (string)
│           ├── weight (float)
│           ├── cluster (string)
│           ├── type (string: "ranked" | "unranked")
│           ├── song_count (integer)
│           ├── full_name (string, optional)
│           └── shadow_rank (float, optional: required if type is "unranked")
└── songs (array of song_objects)
    └── [song_object] (object)
        ├── id (string: ISRC or internal ID)
        ├── artist (string)
        ├── name (string: song title)
        ├── sources (array of source_entries)
        │   └── [source_entry] (object)
        │       ├── name (string: must match a key in config.sources)
        │       ├── rank (integer, optional: present if type is "ranked")
        │       ├── uses_shadow_rank (boolean, optional: present if type is "unranked")
        │       └── quote (string, optional)
        ├── list_count (integer: number of sources citing this song)
        ├── archetype (string, optional)
        └── media (object)
            ├── youtube (object)
            │   ├── music_id (string)
            │   └── video_id (string)
            └── spotify (object)
                └── id (string)
```

# Samples

See [sample_data.json](samples/sample_data.json) for the JSON data format and 3 sample songs.

See [song_sample.html](samples/song_sample.html) for inspiration for the UI style for a single song card in the list.

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
- Use white on gray
- Opacity: 0.25 default, 1.0 on hover
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
- Then: "Show Top 500 (300 more)"
- Finally: "Show All (X more)"
- Button hidden when all songs displayed

# Workflow Guidelines

1. **Atomic Changes:** Suggest one feature or one bug fix at a time.
2. **Verification:** After writing code, explain how it interacts with the `data.json` structure.
3. **No Placeholders:** Write complete code blocks; avoid "insert logic here" comments.

# Ranking Function

## 🧠 Core Philosophy: Direct Scoring

This ranking engine uses a **direct scoring** approach where each source citation contributes points based on its rank position and the source's weight multiplier. Unlike normalization-based systems, this allows sources of different sizes to have influence proportional to their configured weight.

Each source is assigned a `weight` which acts as a pure multiplier on their contributions. Sources are also assigned to a `cluster` which is a categorization of the type of source it is.

## 🛠 Ranking Modes

The engine can be toggled between two distinct mathematical philosophies:

### 1. Consensus Mode (Democratic)

Based on a modified **Reciprocal Rank Fusion (RRF)**, this mode identifies the "cultural record"—the hits that achieved the widest agreement across the industry.

- **Formula:** $W(rank) = \frac{1 + K}{rank + K}$ (uses shadow ranks for unranked lists)
- **Smoothing Constant ($K$):** This "damps" the top ranks to allow broad agreement across many lists to outweigh a single outlier #1 ranking. The default is the `k_value` in the ranking config.

### 2. Conviction Mode (Prestige)

Uses a **Power-Law Decay** (Generalized Zipfian distribution) to reward critical obsession and "Song of the Year" statements.

- **Formula:** $W(rank) = \frac{1}{rank^P}$ (uses shadow ranks for unranked lists)
- **Zipf Exponent ($P$):** This creates a steep "winner-take-most" curve where a #1 rank is significantly more valuable than a #10. The default is `p_exponent` in the ranking config.

---

## 📈 Multipliers & Bonuses

The engine applies three specialized multipliers to the raw scores:

1.  **Consensus Boost:** A logarithmic reward based on the total number of lists a song appears on.
    - _Formula:_ $1 + (consensus_booost \times \ln(\text{count}))$
    - `c_mul = 1 + (consensus_boost * np.log(len(ranks)))`
2.  **Provocation Boost:** Rewards "Polarization." Calculated via the standard deviation of ranks, giving a bonus to songs that critics are divided on (e.g., #1 on some lists, #80 on others) over "safe" middle-of-the-road hits.
    - `p_mul = 1 + (provocation_boost * (np.std(ranks) / 100)) if len(ranks) > 1 else 1.0`
3.  **Diversity (Crossover) Boost:** A bonus for every additional unique **Cluster** a song reaches in its top `cluster_threshold`. This identifies "Unicorns"—tracks that appeal to Authority, Tastemakers, and Specialists simultaneously.
    - `cl_mul = (1 + (cluster_boost * (len(top50_clusters_counts) - 1)) if len(top50_clusters_counts) > 0 else 1.0`

# Implementation Plan

## Phase 1: Core Engine & Data Foundation
*   **Feature 1: Ranking Engine Parity & Robustness**
    *   Verify `RankingEngine.compute` handles all edge cases (e.g., empty lists).
    *   Ensure the standard deviation calculation for `Provocation Boost` matches the Python `np.std` (population vs sample).
    *   Expose the `RankingEngine` globally or structure it for easy debugging.

## Phase 2: Structural UI & Layout
*   **Feature 2: Song Card Layout & "Listen" Links**
    *   Implement the responsive 3-column layout (Rank | Video | Info) and dynamic media links.
    *   Update `render()` to generate "Listen" buttons for YouTube, Spotify, Bandcamp, etc.
    *   Format the "Sources" list with middots and proper wrapping.

## Phase 3: Dynamic State & Sharing
*   **Feature 3: Settings Modal (Configuration)**
    *   Implement `renderSettingsUI()` to dynamically generate sliders for Ranking Parameters, Source Weights, and Shadow Ranks.
    *   Attach event listeners to sliders to trigger `debouncedReRank()`.
    *   Implement the "Defaults" button.
*   **Feature 4: URL State Synchronization**
    *   Refine `updateURL()` to write only *changed* values to the query string.
    *   Ensure `syncStateFromURL()` correctly overrides `data.json` defaults on load.

## Phase 4: Detailed Information (Modals)
*   **Feature 5: Reviews Modal**
    *   Implement `showReviews(songIndex)` to display detailed source feedback.
    *   Render the list of sources with ranks, quotes, and links.
*   **Feature 6: Ranking Stats Modal**
    *   Implement `showStats(songIndex)` to show scoring breakdown.
    *   Calculate and display Normalized Score, Multipliers, and individual Source Contributions.
*   **Feature 7: Visual Polish**
    *   Finalize "Dark Mode" aesthetic (IntelliJ/Solarized theme).
    *   Refine `lite-youtube` play button transparency and hover effects.
