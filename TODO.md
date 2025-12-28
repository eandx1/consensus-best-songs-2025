# ✅ Project To-Do List

This document tracks planned features, improvements, and refactoring tasks for the Consensus Best Songs 2025 project.

## 🎨 UI & UX Improvements
- [ ] **Improve UI Design**: Refine the song card layout, spacing, and typography to align with Pico CSS best practices.
- [ ] **Theme System**: Implement a user-selectable theme switcher (e.g., Solarized, High Contrast, Synthwave) beyond just the default Dark Mode.
- [ ] **Humanize Content**: Ensure `README.md` and the About section have a welcoming, personal, and professional tone.

## 💾 Data & Export Features
- [ ] **Export JSON**: Add functionality for users to download their current custom ranking (with weights/parameters applied) as a JSON file.
- [ ] **Export to YouTube**: Create a feature to generate a YouTube playlist of the user's top 10, 25, 100, or 250 songs.
- [ ] **Export to Spotify**: Explore the Spotify API to allow users to create playlists of their ranked songs directly.

## 🛠 Refactoring & Performance
- [ ] **Code Split**: As the project grows, consider splitting `script.js` into modular files (e.g., `ranking.js`, `ui.js`, `state.js`).

## 🧪 Testing & Quality Assurance
- [ ] **Unit Tests**: Add tests for `RankingEngine` (Javascript) to ensure mathematical stability and correct logic for edge cases.
- [ ] **E2E Tests**: Implement browser automation (e.g., Playwright) to verify the site works as expected (modal interactions, URL state syncing, layout).
- [ ] **Accessibility Testing**: Ensure the site is fully navigable via keyboard and screen readers (WCAG compliance).

