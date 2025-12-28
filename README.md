# Consensus Best Songs 2025

**The Cultural Record:** A data-driven consensus of 2025's musical landscape.

This project acts as a "meta-critic," aggregating hundreds of year-end "Best of" lists from the music press into a single, transparent ranking. It identifies the songs that defined the year, whether through sheer ubiquity (Consensus) or intense critical obsession (Conviction).

🔗 **Live Site:** [https://eandx1.github.io/consensus-best-songs-2025/](https://eandx1.github.io/consensus-best-songs-2025/)

## 🏗️ Project Structure

The project is built as a lightweight, static web application with no build steps or complex frameworks.

*   **`index.html`**: The main entry point containing the semantic HTML structure and Pico CSS integration.
*   **`script.js`**: Handles data loading, the ranking engine logic, state management, and DOM rendering.
*   **`data.json`**: The single source of truth containing:
    *   Configuration (ranking parameters, boosters, cluster metadata).
    *   Source definitions (weights, URLs, categories).
    *   Song data (artists, titles, media IDs, and source citations).
*   **`ranking_engine.py`**: A Python prototype used to validate the math before porting the logic to JavaScript.

## 🛠️ Technical Choices

*   **Vanilla JavaScript (ES6+)**: Chosen for performance and simplicity. The entire application runs in the browser.
*   **Pico CSS**: A minimal, semantic-first CSS framework that provides a clean "dark mode" aesthetic without the overhead of heavy UI libraries.
*   **No Build Step**: The app is "view-source" friendly. What you see is what you run.
*   **URL State Sync**: All ranking parameters (decay rates, boosters, weights) are synchronized to the URL query string, making specific ranking configurations shareable (deep-linking).
*   **Lite YouTube**: Uses the `lite-youtube` web component for lightning-fast loading of video embeds.

## 🧮 Ranking Decisions

The core engine allows users to toggle between two mathematical philosophies:

1.  **🤝 Consensus Mode (Modified Reciprocal Rank)**:
    *   Identifies the "Cultural Record"—songs appearing on the highest volume of lists.
    *   Formula: `Score = (1 + K) / (Rank + K)`
    *   Smooths out outliers to favor broad agreement.

2.  **🔥 Conviction Mode (Power-Law Decay)**:
    *   Rewards critical obsession. A #1 rank carries exponentially more weight than a #5 or #10.
    *   Formula: `Score = 1 / (Rank ^ P)`
    *   Identifying "Song of the Year" contenders that critics are passionate about.

### Boosters
To capture the nuance of critical reception, the engine applies three specific multipliers:
*   **⚡ Provocation**: Bonus for high standard deviation (polarizing tracks).
*   **🌍 Crossover**: Bonus for appearing in multiple distinct critical clusters.
*   **📈 Consensus**: Logarithmic bonus based on raw list count.

### Shadow Ranks 👻
Not all lists are ranked. For unranked lists (e.g., "NPR's 100 Best Songs"), the system assigns a **Shadow Rank** based on the list's length to ensure fair weighting without discarding valuable data.

## 🏷️ Category Decisions

Critics are grouped into "clusters" to help identify where a song's support comes from:

*   **🏛️ Critical Authority**: Essential voices from major institutions known for depth and rigorous standards (e.g., *NYT*, *The Guardian*).
*   **⚡ Tastemakers**: Digital trendsetters driving the current conversation (e.g., *Pitchfork*, *The FADER*).
*   **🧪 Specialists**: Niche expert curators focused on specific genres or avant-garde discoveries (e.g., *The Quietus*, *Resident Advisor*).
*   **📡 Mainstream**: High-frequency media tracking mass appeal (e.g., *Billboard*, *Rolling Stone*, *USA Today*).

## 👤 About

**Everett Anderson**  
*Software Engineer & Music Data Enthusiast*

I built this tool to visualize the mathematical "shape" of the year's music and to explore how we define "best" in an era of fragmented media.

[LinkedIn Profile](https://www.linkedin.com/in/everett-anderson-swe/)
