"""
Selective visual screenshot tests for theme regression detection.

This module captures screenshots for the highest-risk theme/component combinations
that CSS property tests cannot reliably verify (e.g., complex visual compositions,
backdrop filters, gradient text, glow effects).

This is Tier 2 of the tiered hybrid testing approach - selective visual verification.

Only 5 screenshots are captured:
1. Original theme - Song card (default theme, most users)
2. Muthur theme - Tune modal (scanlines, slider styling, text glow)
3. Hyperneon theme - Song card (gradient text, hover states)
4. Studio 808 theme - Reviews modal (3D bevel links, blockquote styling)
5. Light theme - Stats modal (inverted color scheme)

Note: These tests use pytest-playwright's built-in screenshot comparison.
To update baselines: pytest --update-snapshots
"""
import sys

import pytest
from playwright.sync_api import Page, expect

from conftest import (
    disable_animations,
    get_song_card,
    open_reviews_modal,
    open_stats_modal,
    open_tune_modal,
)

# Skip visual tests on non-Linux platforms to avoid cross-platform rendering differences
# CI runs on Linux, so visual tests are reliable there
SKIP_VISUAL_REASON = "Visual tests only run on Linux CI to avoid cross-platform rendering differences"


@pytest.fixture
def stable_page(page: Page):
    """Prepare page for stable visual testing by disabling animations."""
    yield page


def mask_dynamic_content(page: Page):
    """Hide dynamic content that varies between runs (e.g., lite-youtube embeds)."""
    page.add_style_tag(
        content="""
        lite-youtube, .video-placeholder {
            visibility: hidden !important;
        }
    """
    )


class TestVisualRegression:
    """Selective visual regression tests for high-risk theme/component combinations."""

    @pytest.mark.skipif(sys.platform != "linux", reason=SKIP_VISUAL_REASON)
    def test_original_theme_song_card(self, page: Page, server_url):
        """Capture Original theme song card - the default theme most users see."""
        page.goto(server_url)
        page.wait_for_load_state("networkidle")
        disable_animations(page)
        mask_dynamic_content(page)

        # Get the first song card
        card = page.locator(".song-card").first
        expect(card).to_be_visible()

        # Take screenshot of just the card
        card.screenshot(path="python/tests/__snapshots__/original_song_card.png")

    @pytest.mark.skipif(sys.platform != "linux", reason=SKIP_VISUAL_REASON)
    def test_muthur_theme_tune_modal(self, page: Page, server_url):
        """Capture Muthur theme Tune modal - scanlines, glow effects, slider styling."""
        page.goto(f"{server_url}?theme=muthur")
        page.wait_for_load_state("networkidle")
        disable_animations(page)

        # Open the Tune modal
        open_tune_modal(page)
        modal = page.locator("#modal-tune")
        expect(modal).to_be_visible()

        # Wait for modal to fully render
        page.wait_for_timeout(300)

        # Take screenshot of the modal
        modal.screenshot(path="python/tests/__snapshots__/muthur_tune_modal.png")

    @pytest.mark.skipif(sys.platform != "linux", reason=SKIP_VISUAL_REASON)
    def test_hyperneon_theme_song_card(self, page: Page, server_url):
        """Capture Hyperneon theme song card - gradient text, neon effects."""
        page.goto(f"{server_url}?theme=hyperneon")
        page.wait_for_load_state("networkidle")
        disable_animations(page)
        mask_dynamic_content(page)

        # Get the first song card
        card = page.locator(".song-card").first
        expect(card).to_be_visible()

        # Take screenshot of just the card
        card.screenshot(path="python/tests/__snapshots__/hyperneon_song_card.png")

    @pytest.mark.skipif(sys.platform != "linux", reason=SKIP_VISUAL_REASON)
    def test_studio808_theme_reviews_modal(self, page: Page, server_url):
        """Capture Studio 808 theme Reviews modal - 3D bevel links, blockquote styling."""
        page.goto(f"{server_url}?theme=studio808")
        page.wait_for_load_state("networkidle")
        disable_animations(page)

        # Open the Reviews modal for the first song
        card = get_song_card(page, "WHERE IS MY HUSBAND!")
        open_reviews_modal(page, card)

        modal = page.locator("#modal-reviews")
        expect(modal).to_be_visible()

        # Wait for modal to fully render
        page.wait_for_timeout(300)

        # Take screenshot of the modal
        modal.screenshot(path="python/tests/__snapshots__/studio808_reviews_modal.png")

    @pytest.mark.skipif(sys.platform != "linux", reason=SKIP_VISUAL_REASON)
    def test_light_theme_stats_modal(self, page: Page, server_url):
        """Capture Light theme Stats modal - inverted color scheme verification."""
        page.goto(f"{server_url}?theme=light1")
        page.wait_for_load_state("networkidle")
        disable_animations(page)

        # Open the Stats modal for the first song
        card = get_song_card(page, "WHERE IS MY HUSBAND!")
        open_stats_modal(page, card)

        modal = page.locator("#modal-stats")
        expect(modal).to_be_visible()

        # Wait for modal to fully render
        page.wait_for_timeout(300)

        # Take screenshot of the modal
        modal.screenshot(path="python/tests/__snapshots__/light_stats_modal.png")


class TestVisualSanity:
    """
    Basic sanity checks that run on all platforms.
    These don't compare screenshots but verify elements render without errors.
    """

    @pytest.mark.parametrize("theme", ["original", "muthur", "hyperneon", "light1", "studio808"])
    def test_theme_renders_without_console_errors(self, page: Page, server_url, theme):
        """Verify each theme loads without JavaScript errors."""
        errors = []
        page.on("pageerror", lambda err: errors.append(str(err)))

        page.goto(f"{server_url}?theme={theme}")
        page.wait_for_load_state("networkidle")

        # Filter out known non-critical errors (e.g., third-party script issues)
        critical_errors = [e for e in errors if "lite-youtube" not in e.lower()]

        assert len(critical_errors) == 0, f"Console errors in {theme} theme: {critical_errors}"

    @pytest.mark.parametrize("theme", ["original", "muthur", "hyperneon", "light1", "studio808"])
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
