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
- Mobile-first
- State Management: Treat `data.json` as an immutable source of truth. All rankings must be calculated as a "derived view" by applying default or user-defined weights to the source data
- URL Persistence: Use the native URLSearchParams API to synchronize configuration state (weights and ranking parameters) to the URL query string. The application must be "deep-linkable," meaning if a user shares a URL, another user opening it should see the exact same custom ranking.
- Performance: The ranking algorithm should be efficient enough to run on input events (sliders) without blocking the UI thread
- Constraints: No build steps (no Webpack/Vite), no frameworks (no React/Vue)
- Design Style: Clean, semantic, and responsive using Pico CSS defaults
- Ensure font and colors can be easily switched to different themes

# Project Structure

## File Layout

- `index.html` - Single HTML file with all CSS inline (no separate .css files)
- `script.js` - Single JS file with all application logic (no bundling/build)
- `data.json` - Song data and configuration (immutable source of truth)
- `python/` - Testing infrastructure (Playwright + pytest)
- `samples/` - Reference data and UI samples

## index.html Structure (~1980 lines)

- `<style>` block: All CSS (themes defined via `[data-style="themename"]`)
- Five themes: `original`, `light1`, `studio808`, `muthur`, `hyperneon`
- SVG sprite: Icon symbols (`#icon-spotify`, `#icon-youtube`, `#icon-sliders`, etc.)
- Header: Nav with title, Tune button, hamburger menu
- Main: `#song-list` container, load more button
- Dialogs: Six modals (`modal-tune`, `modal-stats`, `modal-reviews`, `modal-youtube`, `modal-download`, `modal-about`)
- External: Pico CSS (CDN), lite-youtube (CDN), Google Fonts (Sora + theme fonts)

## script.js Structure (~1470 lines)

- `CONFIG_BOUNDS` - Validation ranges for all slider parameters
- `THEME_CONFIG` - Theme definitions (name, style, mode)
- `STATE` - Mutable application state (config, songs, displayLimit)
- `APP_DATA` - Immutable data loaded from data.json
- `UI` - Cached DOM element references
- `RankingEngine` - Core ranking computation (exposed on `window` for debugging)
- `syncStateFromURL()` / `updateURL()` - URL state persistence
- `render()` - Main render function, recomputes rankings and updates DOM
- `init()` - Entry point, loads data, sets up event listeners
- `showReviews()` / `showStats()` - Modal content renderers
- `renderSettingsUI()` - Tune modal slider generation
- `renderYouTubeUI()` / `renderDownloadUI()` / `downloadCSV()` - Playlist export features
- `isRankingCustomized()` - Detects if settings differ from defaults

# UI Design

"Dark mode" style website with clean, responsive UI for both desktop and mobile.

## Inspiration

Think of the Pico CSS website, the IntelliJ Darcula theme, and the Solarized Dark terminal theme for color and font inspiration.

## Header

- Site title: "Consensus Best Songs 2025"
- "Tune" button to open ranking configuration modal
  - Shows sliders icon with "Tune" text by default
  - Changes to "Tuned" with highlighted styling when any ranking parameter differs from defaults (indicates customized ranking)
- Hamburger menu (☰) containing:
  - "Listen on YouTube" - opens YouTube playlist modal
  - "Download playlist" - opens CSV download modal
  - "About" - opens about modal
  - Theme selector dropdown

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
  - "Apple" link (if `apple.url` exists)
  - "Bandcamp" link (if `bandcamp.url` exists)
  - "Other" link (if `other.url` exists)
- Info (ⓘ) icon in top right that opens Ranking Stats modal

By default, the top 25 are shown. Users can progressively load more: top 100, top 200, top 500, then all songs.

## Interactivity

### State Syncing

On Initialization: Check `window.location.search`. If parameters exist, override the defaults from `data.json`.

On Slider Change: Update the `URLSearchParams` object and use `history.replaceState` to update the browser's address bar without reloading the page.

### Overlays/Modals

Six semantic HTML `<dialog>` elements are used, styled with Pico CSS:

1. **Tune Ranking Modal**: Title "Tune Ranking" - for adjusting ranking parameters and source weights
2. **Ranking Stats Modal**: Title "Ranking Details" - shows detailed scoring breakdown for a song
3. **Reviews Modal**: Title "Reviews" - shows all source reviews with quotes and links
4. **YouTube Modal**: Title "Listen on YouTube" - generates YouTube playlist from top songs
5. **Download Modal**: Title "Download playlist" - exports songs as CSV for streaming service import
6. **About Modal**: Title "About" - shows site description, methodology explanation, and mode comparison table

### Tune Ranking Modal

Modal header shows a sliders icon followed by "Tune Ranking". The icon is always visible but uses a muted color by default. When settings are customized (differ from defaults), the icon and title text change to the primary color, and the title changes to "Tuned Ranking" to indicate active customization. Contains four sections:

**Ranking Parameters** (appears first):

- Decay Mode, 2 button choice defaulting to "consensus" with the other option being "conviction", default from `data["config"]["ranking"]["decay_mode"]`, url parameter `decay_mode`
- Smoothing Factor (K), slider, integer range 0-50 in 1 increments, only shown when Decay Mode is "consensus", default from `data["config"]["ranking"]["k_value"]`, url parameter `k_value`
- Power Law Steepness (P), slider, float range 0.0 to 1.1 in 0.01 increments, only shown when Decay Mode is "conviction", default from `data["config"]["ranking"]["p_exponent"]`, url parameter `p_exponent`
- Consensus Boost, slider, percentage range from 0% to 20% in 1% increments, default from `data["config"]["ranking"]["consensus_boost"]`, url parameter `consensus_boost`
- Provocation Boost, slider, percentage range from 0% to 20% in 1% increments, default from `data["config"]["ranking"]["provocation_boost"]`, url parameter `provocation_boost`
- Cluster Boost, slider, percentage range from 0% to 20% in 1% increments, default from `data["config"]["ranking"]["cluster_boost"]`, url parameter `cluster_boost`
- Cluster Threshold, slider, integer range 0 to 100 in 1 increments, default from `data["config"]["ranking"]["cluster_threshold"]`, url parameter `cluster_threshold`
- Rank 1 Bonus, slider, percentage range 0% to 20% in 0.5% increments, stored as multiplier (1.0-1.2), default from `data["config"]["ranking"]["rank1_bonus"]`, url parameter `rank1_bonus`
- Rank 2 Bonus, slider, percentage range 0% to 20% in 0.5% increments, stored as multiplier (1.0-1.2), default from `data["config"]["ranking"]["rank2_bonus"]`, url parameter `rank2_bonus`
- Rank 3 Bonus, slider, percentage range 0% to 20% in 0.5% increments, stored as multiplier (1.0-1.2), default from `data["config"]["ranking"]["rank3_bonus"]`, url parameter `rank3_bonus`

When a value differs from default, the label text is highlighted to indicate customization.

**Source Weights** (appears second):

- One slider per source: range 0.0-1.5, step 0.01, default from each source's `weight` in `data["config"]["sources"]`
- Display the source key name as the slider label
- When a value differs from default, the label text is highlighted to indicate customization

**Shadow Ranks** (appears third):
Some sources are unranked lists so use "shadow ranks" instead of real ranks.

If a source has `data["config"]["sources"][source name]["type"]` of `unranked` then its `data["config"]["sources"][source name]["shadow_rank"]` will have its default shadow rank.

For each such source with a shadow rank, display the source key name and a float slider from 1.0 through 100.0 in 0.1 increments.

The URL parameter should be lowercase source name with spaces or other non-letter characters replaced by underscores.

**Song Filters** (appears fourth):
Control which songs appear in the ranking based on their source data.

- Shows counter: "Including N of M songs"
- Minimum Source Count, slider, integer range 1-10 in 1 increments, default 1, url parameter `min_sources`. Only include songs that appear on at least this many lists.
- Rank Cutoff, slider, integer range 0-100 in 1 increments, default 0 (meaning no cutoff), url parameter `rank_cutoff`. Ignore contributions from ranks worse than this cutoff. When set to 0, displays "Any".

**Filter Independence:** The two filters operate independently:
- `min_sources` checks the *original* number of lists a song appears on (not affected by rank_cutoff)
- `rank_cutoff` filters which source contributions count toward a song's score
- Songs with 0 qualifying contributions after rank_cutoff filtering are excluded (they would have no score)

Example: A song on 5 lists with only 1 rank ≤ cutoff will pass `min_sources=3` (because it appears on 5 lists) and remain visible (because it has 1 qualifying contribution).

When filters exclude all songs, an empty state is shown with a button to adjust filters.

UI behaviors:

- Values update in real-time (debounced by 250ms)
- Rankings recalculate automatically as user adjusts sliders
- "Reset" button resets all values to defaults
- "Back to top" button scrolls modal content to top
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

Modal header shows "Ranking Details".

Displays scoring details in order:

1. Normalized Score (the final 0-1 score)
2. Raw Score (score after multipliers applied)
3. Base Score (sum of source contributions before multipliers)
4. List Count (number of lists citing the song)
5. Consensus Boost (the multiplier applied)
6. Provocation Boost (the multiplier applied)
7. Cluster Boost (the multiplier applied)
8. Source Contributions section:
   - Each source listed with rank (or shadow rank) and its calculated contribution
   - Format: "Source Name #Rank: 0.xxxx"
   - Sorted by contribution value (highest first)
   - Scrollable if many sources

### YouTube Modal

Modal header shows "Listen on YouTube" with subtitle "Play the top songs as an unnamed playlist on YouTube". When ranking settings are customized, the subtitle changes to mention "your tuned ranking" with sliders icon.

Allows users to generate a YouTube playlist URL from the current ranking:

**Media preference** (fieldset with pill-shaped chip buttons):
- "Music Videos" (default) - prefers `video_id` over `music_id`
- "Audio Only" - prefers `music_id` over `video_id`

**Songs to include** (fieldset with pill-shaped chip buttons):
- Top 10, Top 25, Top 50 (default is 50)

**Status display:**
- Shows count of valid songs ready to play
- Filter limitation note when filters reduce available songs below requested count
- Warning message listing specific songs missing YouTube IDs (if any)
- Success message if all requested songs are available

**Footer:**
- "Listen on YouTube" button opens YouTube with playlist URL
- "Close" button dismisses modal

### Download Modal

Modal header shows "Download playlist" with subtitle "Download as CSV and import to the streaming service of your choice". When ranking settings are customized, the subtitle changes to mention "your tuned ranking" with sliders icon.

Allows users to export the current ranking as a CSV file:

**Songs to include** (fieldset with pill-shaped chip buttons):
- Top 25, Top 100 (default), Top 200, Top 500, All

**Status display:**
- Shows count of songs ready to download
- Filter limitation note when filters reduce available songs below requested count (including when "All" is selected with active filters)
- Warning message listing specific songs missing ISRC codes (if any)
- Success message if all songs have ISRC codes

**Footer (before download):**
- "Download CSV" button triggers file download
- "Close" button dismisses modal

**Footer (after download):**
- "Next step" message with streaming service import links
- Links to Soundiiz and TuneMyMusic import services
- "Download Again" button for re-downloading
- "Close" button dismisses modal

**CSV Format:**
Columns: `title`, `artist`, `isrc`, `spotify_id`, `youtube_id`, `youtube_music_id`, `apple_music_url`, `other_url`

### About Modal

Modal header shows "About".

Contains three main sections:

**Behind the project:**

- Personal statement about the site
- Dynamic display of total song count from `data.json` using `<kbd>` element
- Links to GitHub repository and LinkedIn

**How it works:**

- Explanation of the aggregation methodology
- Bullet list of customization options (source weights, decay functions, boosts)

**Sources:**

- Two tables showing all sources with song counts
- Ranked sources table (sources with explicit rankings)
- Unranked sources table (sources using shadow ranks)

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
│   │   ├── decay_mode (string)
│   │   ├── min_sources (integer)
│   │   └── rank_cutoff (integer)
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
        ├── genres (string, optional)
        └── media (object)
            ├── apple (object, optional)
            │   └── url (string)
            ├── youtube (object, optional)
            │   ├── music_id (string, optional)
            │   └── video_id (string, optional)
            ├── spotify (object, optional)
            │   └── id (string, optional)
            ├── bandcamp (object, optional)
            │   └── url (string)
            └── other (object, optional)
                └── url (string)
```

# Samples

See [sample_data.json](samples/sample_data.json) for the JSON data format and sample songs.

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
- Apple link if `apple.url` exists
- Bandcamp link if `bandcamp.url` exists
- Other link if `other.url` exists

## Video Player Customization

The `lite-youtube` play button is customized via `::part(playButton)`:

- Size: 68x48px (standard YouTube button size)
- Grayscale filter with transparent background
- Opacity: 0.15 default on touch devices
- On hover-capable devices: opacity 0 by default, 1.0 on hover

## Tuned Badge Indicator

The "Tuned" badge appears throughout the UI when ranking settings differ from defaults:

- **Detection**: Compares current URL parameters against default values from `data.json`
- **Tune button**: Adds `.tuned` class, changes text to "Tuned" with sliders icon
- **Modal subtitles**: Tune, YouTube, and Download modals show "tuned" indicator with sliders icon
- **Styling**: Uses `.tuned-text` class with theme-aware highlight color (primary color in dark mode)
- **Icon**: Uses `#icon-sliders` SVG symbol via `<use>` element
- **Reset behavior**: Clicking "Reset" in Tune modal clears all customizations and removes tuned state

## About Modal Styling

The `.about-methodology-box` class is used to style the mode description cards:

- Background: Uses Pico's card background color
- Padding: Standard Pico spacing
- Border radius: Pico's default border radius
- Border: 1px solid muted border color
- Applied to the Consensus and Conviction mode description boxes

## Security

Always use `escapeHtml()` helper function when inserting user-generated or data-driven content into HTML to prevent XSS attacks.

## Responsive Design

- Mobile: Stacked column layout with flexbox
- Desktop (768px+): Row flexbox layout with fixed widths (rank: 4rem, video: 320px, info: flex-grow)
- Large screens (1200px+): Video column expands to 360px
- Sources list wraps with `white-space: nowrap` on individual items

## Progressive Loading

- Initial: 25 songs
- Button shows: "Show More (75)" to load up to 100
- Then: "Show More (100)" to load up to 200
- Then: "Show More (300)" to load up to 500
- Finally: "Show All (N)" where N is remaining count
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

1.  **Consensus Boost:** A logarithmic reward based on the total number of lists a song appears on, normalized so that the slider percentage represents the maximum possible boost.
    - _Formula:_ $1 + \frac{consensus\_boost \times \ln(\text{count})}{\ln(\text{max\_count})}$
    - `c_mul = 1 + (consensus_boost * np.log(len(ranks)) / ln_max_list_count)`
2.  **Provocation Boost:** Rewards "Polarization." Calculated via the standard deviation of ranks, giving a bonus to songs that critics are divided on (e.g., #1 on some lists, #80 on others) over "safe" middle-of-the-road hits.
    - `p_mul = 1 + (provocation_boost * (np.std(ranks) / 100)) if len(ranks) > 1 else 1.0`
3.  **Diversity (Crossover) Boost:** A bonus for every additional unique **Cluster** a song reaches within the configurable `cluster_threshold` rank. This identifies "Unicorns"—tracks that appeal to Authority, Tastemakers, and Specialists simultaneously.
    - `cl_mul = clustersSeen.size > 0 ? 1 + cluster_boost * (clustersSeen.size - 1) : 1.0`

---

## ⚙️ Default Configuration Rationale

The default values in `data.json.config.ranking` were chosen through empirical testing to produce rankings that balance multiple objectives:

### Decay Mode Parameters

| Parameter | Default | Rationale |
|-----------|---------|-----------|
| `decay_mode` | `"consensus"` | Consensus mode (RRF) is the default because it produces more stable rankings that favor songs with broad critical agreement. Conviction mode is available for users who want to emphasize critics' #1 picks. |
| `k_value` | `20` | The smoothing constant K=20 was chosen because it creates a balanced decay curve: #10 is worth ~66% of #1, #25 is worth ~47%, #50 is worth ~30%. This prevents a single #1 pick from dominating while still rewarding higher ranks. K=0 would give 100% weight to #1, K=50 would flatten differences too much. |
| `p_exponent` | `0.55` | The power law exponent P=0.55 creates a moderately steep curve in Conviction mode: #10 is worth ~28% of #1, #25 is worth ~15%, #50 is worth ~9%. This preserves the "winner-take-most" philosophy without completely ignoring lower ranks. P=1.0 would be too extreme (1/rank), P=0.3 would be too flat. |

### Boost Parameters

| Parameter | Default | Rationale |
|-----------|---------|-----------|
| `consensus_boost` | `0.03` (3%) | A modest 3% maximum boost for appearing on many lists. Higher values would over-reward songs with broad but shallow support. Set to reward songs on 10+ lists without overwhelming the base ranking. |
| `provocation_boost` | `0.0` (0%) | Disabled by default because "polarizing" songs (high rank variance) don't necessarily indicate quality. Users can enable this to surface controversial picks. |
| `cluster_boost` | `0.03` (3%) | A 3% boost per additional cluster rewards crossover appeal. A song appearing in Authority, Tastemaker, and Specialist clusters gets 6% boost total. This identifies "unicorns" that resonate across the music industry. |
| `cluster_threshold` | `25` | Only ranks 1-25 count toward cluster diversity. This ensures a song must have meaningful support in a cluster (not just a #99 placement) to receive the crossover bonus. |

### Podium Bonuses

| Parameter | Default | Rationale |
|-----------|---------|-----------|
| `rank1_bonus` | `1.10` (10%) | A significant 10% multiplier for #1 picks. This rewards critics' absolute favorite songs, recognizing that a #1 ranking represents a strong curatorial statement. |
| `rank2_bonus` | `1.075` (7.5%) | A 7.5% multiplier for #2 picks maintains a clear hierarchy while acknowledging the difficulty of the #1 choice. The 2.5% gap from #1 is meaningful but not overwhelming. |
| `rank3_bonus` | `1.025` (2.5%) | A modest 2.5% multiplier for #3 picks completes the "podium effect" while ensuring the bonus curve doesn't extend too far down the list. |

### Design Principles

1. **Conservative Defaults**: All boosts are modest (0-10%) to preserve the core ranking signal from the decay functions.

2. **Transparency**: Every parameter is exposed in the Tune modal, so users can see exactly how rankings are calculated and adjust them to their preferences.

3. **Balance Over Optimization**: The defaults prioritize producing intuitively reasonable rankings over maximizing any single metric. A song that appears on many lists with solid (not spectacular) ranks should compete with a song that has fewer, higher ranks.

4. **Reproducibility**: All parameters are persisted in the URL, making every ranking configuration shareable and reproducible.

# Testing

We use [Playwright](https://playwright.dev/python/) with `pytest` for end-to-end testing of the application. This ensures that the UI renders correctly, the ranking logic behaves as expected, and user interactions (like adjusting sliders) properly update the URL state.

## Setup

The testing infrastructure is located in the `python/` directory.

- **Infrastructure**: `python/tests/conftest.py`
  - Starts a local static file server for the project root.
  - Intercepts requests to `data.json` and mocks them with deterministic data from `python/tests/testdata/test_data.json`.
  - This ensures tests run in isolation without modifying production data.

## Running Tests

```bash
cd python
uv sync        # Install dependencies (first time)
uv run pytest  # Run tests (visual regression tests auto-skipped)
```

Visual regression tests are automatically skipped when running locally because font rendering differs between macOS and Linux. CI runs all tests including visual regression in a Docker container.

To run specific tests:

```bash
uv run pytest tests/test_ranking_logic.py
```

## Visual Regression Tests

Visual regression tests compare screenshots pixel-by-pixel against baselines. To run them locally or update baselines, use Docker:

```bash
# From project root, run ALL tests including visual regression (matches CI environment)
python/scripts/test-docker.sh

# Update visual baselines after intentional UI changes
python/scripts/test-docker.sh tests/test_theme_visual.py --update-snapshots
```

Note: The script is located at `python/scripts/test-docker.sh` (not in the project root).

The Docker script uses Microsoft's official Playwright container (`mcr.microsoft.com/playwright:v1.57.0-noble`), the same image used in CI.

## Test Scope

The test suite covers:

- **Core Loading**: Verifies page title, initial song list, and data loading.
- **Song Rendering**: Checks correct display of song details, ranks, and dynamic media links (YouTube, Spotify, Bandcamp, etc.).
- **Ranking Logic**: Validates that URL parameters drive the configuration and that UI interactions (sliders) update the URL.
- **Modals**: Verifies correct rendering and behavior of:
  - Tune Ranking Modal (Ranking Params, Source Weights, Shadow Ranks)
  - Reviews Modal (Quotes, Source lists, Ghost emojis for shadow ranks)
  - Ranking Stats Modal (Score breakdown tables)
  - About Modal (Dynamic content)
- **Playlist Features**: Tests for YouTube and Download modals:
  - YouTube modal count selection and preference toggles
  - YouTube playlist URL generation with correct video IDs
  - Download modal count selection
  - CSV export with proper headers and data
  - Warning messages for missing YouTube IDs or ISRC codes
- **Theme Switching**: Verifies theme selector in hamburger menu works correctly
- **Visual Regression**: Screenshot comparisons for theme styling (requires Docker):
  - Song card rendering across themes
  - Modal styling (Tune, Reviews, Stats)
  - Font rendering and visual consistency
- **Tuned Badge**: Validates tuned state indicators:
  - Tune button state transitions (default vs tuned)
  - Modal subtitle visibility and content based on customization
  - Reset behavior clearing tuned state
  - Slider and mode changes triggering tuned state
