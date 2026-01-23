"""
Visual regression tests for theme styling.

This module uses pytest-playwright-visual to detect visual regressions in theme
styling. Screenshots are compared pixel-by-pixel against baseline images.

Key components tested:
1. Original theme - Song card (default theme, most users)
2. Muthur theme - Tune modal (scanlines, slider styling, text glow)
3. Hyperneon theme - Song card (gradient text, neon effects)
4. Studio 808 theme - Reviews modal (3D bevel links, blockquote styling)
5. Light theme - Stats modal (inverted color scheme)

To update baselines when intentional changes are made:
    uv run pytest tests/test_theme_visual.py --update-snapshots

Note: All themes use web fonts (Sora, Michroma, etc.) loaded from Google Fonts,
which ensures consistent rendering across platforms.
"""
import pytest
from playwright.sync_api import Page, expect

from conftest import (
    disable_animations,
    get_song_card,
    open_reviews_modal,
    open_stats_modal,
    open_tune_modal,
)

# Threshold for pixel comparison (0-1, lower = stricter)
# 0.1 allows for minor anti-aliasing differences across platforms
SNAPSHOT_THRESHOLD = 0.1


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


class TestVisualRegression:
    """Visual regression tests comparing screenshots against baselines."""

    def test_original_theme_song_card(self, page: Page, server_url, assert_snapshot):
        """Original theme song card - the default theme most users see."""
        page.goto(server_url)
        page.wait_for_load_state("networkidle")
        wait_for_fonts(page)
        disable_animations(page)
        mask_dynamic_content(page)

        card = page.locator(".song-card").first
        expect(card).to_be_visible()

        assert_snapshot(
            card.screenshot(),
            name="original-song-card.png",
            threshold=SNAPSHOT_THRESHOLD,
        )

    def test_muthur_theme_tune_modal(self, page: Page, server_url, assert_snapshot):
        """Muthur theme Tune modal - scanlines, glow effects, slider styling."""
        page.goto(f"{server_url}?theme=muthur")
        page.wait_for_load_state("networkidle")
        wait_for_fonts(page)
        disable_animations(page)

        open_tune_modal(page)
        modal = page.locator("#modal-tune")
        expect(modal).to_be_visible()

        # Wait for modal animations to settle
        page.wait_for_timeout(300)

        assert_snapshot(
            modal.screenshot(),
            name="muthur-tune-modal.png",
            threshold=SNAPSHOT_THRESHOLD,
        )

    def test_hyperneon_theme_song_card(self, page: Page, server_url, assert_snapshot):
        """Hyperneon theme song card - gradient text, neon effects."""
        page.goto(f"{server_url}?theme=hyperneon")
        page.wait_for_load_state("networkidle")
        wait_for_fonts(page)
        disable_animations(page)
        mask_dynamic_content(page)

        card = page.locator(".song-card").first
        expect(card).to_be_visible()

        assert_snapshot(
            card.screenshot(),
            name="hyperneon-song-card.png",
            threshold=SNAPSHOT_THRESHOLD,
        )

    def test_studio808_theme_reviews_modal(self, page: Page, server_url, assert_snapshot):
        """Studio 808 theme Reviews modal - 3D bevel links, blockquote styling."""
        page.goto(f"{server_url}?theme=studio808")
        page.wait_for_load_state("networkidle")
        wait_for_fonts(page)
        disable_animations(page)

        card = get_song_card(page, "WHERE IS MY HUSBAND!")
        open_reviews_modal(page, card)

        modal = page.locator("#modal-reviews")
        expect(modal).to_be_visible()

        # Wait for modal animations to settle
        page.wait_for_timeout(300)

        assert_snapshot(
            modal.screenshot(),
            name="studio808-reviews-modal.png",
            threshold=SNAPSHOT_THRESHOLD,
        )

    def test_light_theme_stats_modal(self, page: Page, server_url, assert_snapshot):
        """Light theme Stats modal - inverted color scheme verification."""
        page.goto(f"{server_url}?theme=light1")
        page.wait_for_load_state("networkidle")
        wait_for_fonts(page)
        disable_animations(page)

        card = get_song_card(page, "WHERE IS MY HUSBAND!")
        open_stats_modal(page, card)

        modal = page.locator("#modal-stats")
        expect(modal).to_be_visible()

        # Wait for modal animations to settle
        page.wait_for_timeout(300)

        assert_snapshot(
            modal.screenshot(),
            name="light-stats-modal.png",
            threshold=SNAPSHOT_THRESHOLD,
        )


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
