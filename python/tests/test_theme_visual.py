"""
Visual regression tests for theme styling.

This module uses pytest-playwright-visual to detect visual regressions in theme
styling. Screenshots are compared pixel-by-pixel against baseline images.

Visual regression tests are automatically skipped when running `uv run pytest`
locally because font rendering differs between macOS and Linux. CI runs these
tests in Docker where rendering matches the baselines.

To run visual tests locally or update baselines, use Docker:
    ./scripts/test-docker.sh                                      # Run all tests
    ./scripts/test-docker.sh tests/test_theme_visual.py --update-snapshots  # Update baselines

Coverage:
- 5 themes: original, light1, studio808, muthur, hyperneon
- 7 targets per theme: song card, tune modal, stats modal, reviews modal,
  youtube modal, download modal, about modal
- Total: 35 visual regression tests
"""
import pytest
from playwright.sync_api import Page, expect

from conftest import (
    disable_animations,
    get_song_card,
    open_about_modal,
    open_download_modal,
    open_reviews_modal,
    open_stats_modal,
    open_tune_modal,
    open_youtube_modal,
)

# Threshold for pixel comparison (0-1, lower = stricter)
# 0.1 allows for minor anti-aliasing differences across platforms
SNAPSHOT_THRESHOLD = 0.1

# All themes to test
THEMES = ["original", "light1", "studio808", "muthur", "hyperneon"]


def mask_dynamic_content(page: Page):
    """Hide dynamic content that varies between runs (e.g., lite-youtube embeds)."""
    page.add_style_tag(
        content="""
        lite-youtube, .video-placeholder {
            visibility: hidden !important;
        }
    """
    )


def wait_for_fonts(page: Page):
    """Wait for web fonts to be fully loaded."""
    page.evaluate("() => document.fonts.ready")


def setup_page(page: Page, server_url: str, theme: str):
    """Common setup for visual tests: navigate, wait for load, disable animations."""
    url = server_url if theme == "original" else f"{server_url}?theme={theme}"
    page.goto(url)
    page.wait_for_load_state("networkidle")
    wait_for_fonts(page)
    disable_animations(page)


def wait_for_modal(page: Page):
    """Wait for modal animations to settle."""
    page.wait_for_timeout(300)


@pytest.mark.visual
class TestVisualRegression:
    """Visual regression tests comparing screenshots against baselines.

    These tests are automatically skipped when running locally. To run them,
    use Docker: ./scripts/test-docker.sh
    """

    # =========================================================================
    # Song Card Tests (Main Page)
    # =========================================================================

    @pytest.mark.parametrize("theme", THEMES)
    def test_song_card(self, page: Page, server_url, assert_snapshot, theme):
        """Test song card rendering for each theme."""
        setup_page(page, server_url, theme)
        mask_dynamic_content(page)

        card = page.locator(".song-card").first
        expect(card).to_be_visible()

        assert_snapshot(
            card.screenshot(),
            name=f"{theme}-song-card.png",
            threshold=SNAPSHOT_THRESHOLD,
        )

    # =========================================================================
    # Tune Modal Tests
    # =========================================================================

    @pytest.mark.parametrize("theme", THEMES)
    def test_tune_modal(self, page: Page, server_url, assert_snapshot, theme):
        """Test Tune modal styling for each theme."""
        setup_page(page, server_url, theme)

        open_tune_modal(page)
        modal = page.locator("#modal-tune")
        expect(modal).to_be_visible()
        wait_for_modal(page)

        assert_snapshot(
            modal.screenshot(),
            name=f"{theme}-tune-modal.png",
            threshold=SNAPSHOT_THRESHOLD,
        )

    # =========================================================================
    # Stats Modal Tests
    # =========================================================================

    @pytest.mark.parametrize("theme", THEMES)
    def test_stats_modal(self, page: Page, server_url, assert_snapshot, theme):
        """Test Stats modal styling for each theme."""
        setup_page(page, server_url, theme)

        card = get_song_card(page, "WHERE IS MY HUSBAND!")
        open_stats_modal(page, card)

        modal = page.locator("#modal-stats")
        expect(modal).to_be_visible()
        wait_for_modal(page)

        assert_snapshot(
            modal.screenshot(),
            name=f"{theme}-stats-modal.png",
            threshold=SNAPSHOT_THRESHOLD,
        )

    # =========================================================================
    # Reviews Modal Tests
    # =========================================================================

    @pytest.mark.parametrize("theme", THEMES)
    def test_reviews_modal(self, page: Page, server_url, assert_snapshot, theme):
        """Test Reviews modal styling for each theme."""
        setup_page(page, server_url, theme)

        card = get_song_card(page, "WHERE IS MY HUSBAND!")
        open_reviews_modal(page, card)

        modal = page.locator("#modal-reviews")
        expect(modal).to_be_visible()
        wait_for_modal(page)

        assert_snapshot(
            modal.screenshot(),
            name=f"{theme}-reviews-modal.png",
            threshold=SNAPSHOT_THRESHOLD,
        )

    # =========================================================================
    # YouTube Modal Tests
    # =========================================================================

    @pytest.mark.parametrize("theme", THEMES)
    def test_youtube_modal(self, page: Page, server_url, assert_snapshot, theme):
        """Test YouTube modal styling for each theme."""
        setup_page(page, server_url, theme)

        open_youtube_modal(page)
        modal = page.locator("#modal-youtube")
        expect(modal).to_be_visible()
        wait_for_modal(page)

        assert_snapshot(
            modal.screenshot(),
            name=f"{theme}-youtube-modal.png",
            threshold=SNAPSHOT_THRESHOLD,
        )

    # =========================================================================
    # Download Modal Tests
    # =========================================================================

    @pytest.mark.parametrize("theme", THEMES)
    def test_download_modal(self, page: Page, server_url, assert_snapshot, theme):
        """Test Download modal styling for each theme."""
        setup_page(page, server_url, theme)

        open_download_modal(page)
        modal = page.locator("#modal-download")
        expect(modal).to_be_visible()
        wait_for_modal(page)

        assert_snapshot(
            modal.screenshot(),
            name=f"{theme}-download-modal.png",
            threshold=SNAPSHOT_THRESHOLD,
        )

    # =========================================================================
    # About Modal Tests
    # =========================================================================

    @pytest.mark.parametrize("theme", THEMES)
    def test_about_modal(self, page: Page, server_url, assert_snapshot, theme):
        """Test About modal styling for each theme."""
        setup_page(page, server_url, theme)

        open_about_modal(page)
        modal = page.locator("#modal-about")
        expect(modal).to_be_visible()
        wait_for_modal(page)

        assert_snapshot(
            modal.screenshot(),
            name=f"{theme}-about-modal.png",
            threshold=SNAPSHOT_THRESHOLD,
        )


class TestVisualSanity:
    """
    Basic sanity checks that run on all platforms.
    These don't compare screenshots but verify elements render without errors.
    """

    @pytest.mark.parametrize("theme", THEMES)
    def test_theme_renders_without_console_errors(self, page: Page, server_url, theme):
        """Verify each theme loads without JavaScript errors."""
        errors = []
        page.on("pageerror", lambda err: errors.append(str(err)))

        page.goto(f"{server_url}?theme={theme}")
        page.wait_for_load_state("networkidle")

        # Filter out known non-critical errors (e.g., third-party script issues)
        critical_errors = [e for e in errors if "lite-youtube" not in e.lower()]

        assert len(critical_errors) == 0, f"Console errors in {theme} theme: {critical_errors}"

    @pytest.mark.parametrize("theme", THEMES)
    def test_modals_open_in_theme(self, page: Page, server_url, theme):
        """Verify all modals can be opened in each theme."""
        page.goto(f"{server_url}?theme={theme}")
        page.wait_for_load_state("networkidle")

        # Test Tune modal
        open_tune_modal(page)
        expect(page.locator("#modal-tune")).to_be_visible()
        page.keyboard.press("Escape")
        page.wait_for_timeout(100)

        # Test Reviews modal
        card = page.locator(".song-card").first
        open_reviews_modal(page, card)
        expect(page.locator("#modal-reviews")).to_be_visible()
        page.keyboard.press("Escape")
        page.wait_for_timeout(100)

        # Test Stats modal
        open_stats_modal(page, card)
        expect(page.locator("#modal-stats")).to_be_visible()
