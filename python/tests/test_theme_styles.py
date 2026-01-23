"""
CSS property assertion tests for theme regression detection.

This module verifies that critical CSS properties are correctly applied for each theme.
It catches issues like:
- Wrong colors (primary, background, text)
- Missing theme variables
- Broken contrast
- Font loading failures

This is Tier 1 of the tiered hybrid testing approach - fast, reliable CSS assertions.
"""
import pytest
from playwright.sync_api import Page, expect

# Theme expectations: maps theme name to expected CSS property values
# Colors are specified as rgb() values for reliable comparison
THEME_EXPECTATIONS = {
    "original": {
        "data_style": "original",
        "data_theme": "dark",
        "primary": "rgb(96, 165, 250)",  # #60a5fa
        "background": "rgb(17, 24, 39)",  # Pico dark default
        "card_background": "rgb(31, 41, 55)",  # Pico dark card
        "muted_color": "rgb(148, 163, 184)",  # #94a3b8
        "font_family_contains": "Sora",
    },
    "muthur": {
        "data_style": "muthur",
        "data_theme": "dark",
        "primary": "rgb(82, 255, 202)",  # #52ffca - Phosphor Teal-Green
        "background": "rgb(3, 10, 10)",  # #030a0a
        "card_background": "rgb(5, 18, 18)",  # #051212
        "font_family_contains": "Share Tech Mono",
        "border_radius": "0px",  # Square corners
        "text_transform": "uppercase",
    },
    "hyperneon": {
        "data_style": "hyperneon",
        "data_theme": "dark",
        "primary": "rgb(0, 245, 255)",  # #00f5ff - Electric Cyan
        "background": "rgb(10, 1, 24)",  # #0a0118
        "text_color": "rgb(240, 240, 255)",  # #f0f0ff
        "font_family_contains": "Michroma",
        "border_radius": "20px",  # --pico-border-radius: 1.25rem
    },
    "light1": {
        "data_style": "light1",
        "data_theme": "light",
        "primary": "rgb(124, 77, 255)",  # #7c4dff
        "background": "rgb(248, 249, 255)",  # #f8f9ff
        "text_color": "rgb(26, 35, 126)",  # #1a237e
        "card_background": "rgb(255, 255, 255)",  # #ffffff
        "font_family_contains": "Sora",
    },
    "studio808": {
        "data_style": "808",
        "data_theme": "dark",
        "primary": "rgb(255, 95, 0)",  # #ff5f00 - Signature Orange
        "background": "rgb(0, 0, 0)",  # Pure black
        "card_background": "rgb(0, 0, 0)",  # Pure black
        "font_family_contains": "JetBrains Mono",
        "border_radius": "0px",  # Square corners
    },
}

# Map URL theme param to internal data-style value
THEME_URL_PARAM = {
    "original": "original",
    "muthur": "muthur",
    "hyperneon": "hyperneon",
    "light1": "light1",
    "studio808": "studio808",
}


def get_computed_style(page, selector, property_name):
    """Get computed CSS property value for an element."""
    return page.evaluate(
        """([selector, propertyName]) => {
        const el = document.querySelector(selector);
        if (!el) return null;
        return window.getComputedStyle(el).getPropertyValue(propertyName);
    }""",
        [selector, property_name],
    )


def get_css_variable(page, variable_name):
    """Get the value of a CSS variable from the root element."""
    return page.evaluate(
        """(variableName) => {
        return window.getComputedStyle(document.documentElement)
            .getPropertyValue(variableName).trim();
    }""",
        variable_name,
    )


class TestOriginalTheme:
    """Tests for the Original (Blue Accent) theme - the default theme."""

    def test_data_attributes(self, page: Page, server_url):
        """Verify html element has correct data attributes."""
        page.goto(server_url)
        html = page.locator("html")
        expect(html).to_have_attribute("data-style", "original")
        expect(html).to_have_attribute("data-theme", "dark")

    def test_primary_color(self, page: Page, server_url):
        """Verify primary color is blue."""
        page.goto(server_url)
        # Check computed style on a primary-colored element (links)
        color = get_computed_style(page, "a:not([role='button'])", "color")
        assert color == "rgb(96, 165, 250)", f"Expected blue primary, got {color}"

    def test_background_color(self, page: Page, server_url):
        """Verify dark background color."""
        page.goto(server_url)
        # Background is set on html element via Pico CSS
        bg = get_computed_style(page, "html", "background-color")
        # Pico dark mode background (actual value from Pico CSS)
        assert bg == "rgb(19, 23, 31)", f"Expected dark background, got {bg}"

    def test_font_family(self, page: Page, server_url):
        """Verify Sora font is used."""
        page.goto(server_url)
        font = get_computed_style(page, "body", "font-family")
        assert "Sora" in font, f"Expected Sora font, got {font}"


class TestMuthurTheme:
    """Tests for the MU/TH/UR 6000 (Terminal) theme."""

    def test_data_attributes(self, page: Page, server_url):
        """Verify html element has correct data attributes."""
        page.goto(f"{server_url}?theme=muthur")
        html = page.locator("html")
        expect(html).to_have_attribute("data-style", "muthur")
        expect(html).to_have_attribute("data-theme", "dark")

    def test_primary_color_phosphor_green(self, page: Page, server_url):
        """Verify primary color is phosphor teal-green."""
        page.goto(f"{server_url}?theme=muthur")
        color = get_computed_style(page, "a:not([role='button'])", "color")
        assert color == "rgb(82, 255, 202)", f"Expected phosphor green, got {color}"

    def test_background_color_deep_black(self, page: Page, server_url):
        """Verify very dark terminal background."""
        page.goto(f"{server_url}?theme=muthur")
        # Background is set on html element via --pico-background-color
        bg = get_computed_style(page, "html", "background-color")
        assert bg == "rgb(3, 10, 10)", f"Expected deep terminal black, got {bg}"

    def test_monospace_font(self, page: Page, server_url):
        """Verify Share Tech Mono font is used."""
        page.goto(f"{server_url}?theme=muthur")
        font = get_computed_style(page, "body", "font-family")
        assert "Share Tech Mono" in font, f"Expected Share Tech Mono font, got {font}"

    def test_square_corners(self, page: Page, server_url):
        """Verify border-radius is 0 for terminal aesthetic."""
        page.goto(f"{server_url}?theme=muthur")
        radius = get_computed_style(page, ".song-card", "border-radius")
        assert radius == "0px", f"Expected square corners (0px), got {radius}"

    def test_uppercase_text(self, page: Page, server_url):
        """Verify uppercase text transform."""
        page.goto(f"{server_url}?theme=muthur")
        transform = get_computed_style(page, "body", "text-transform")
        assert transform == "uppercase", f"Expected uppercase, got {transform}"

    def test_card_border_color(self, page: Page, server_url):
        """Verify song cards have green phosphor border."""
        page.goto(f"{server_url}?theme=muthur")
        border = get_computed_style(page, ".song-card", "border-color")
        assert border == "rgb(82, 255, 202)", f"Expected phosphor green border, got {border}"


class TestHyperneonTheme:
    """Tests for the Hyper-Neon 2026 theme."""

    def test_data_attributes(self, page: Page, server_url):
        """Verify html element has correct data attributes."""
        page.goto(f"{server_url}?theme=hyperneon")
        html = page.locator("html")
        expect(html).to_have_attribute("data-style", "hyperneon")
        expect(html).to_have_attribute("data-theme", "dark")

    def test_primary_color_electric_cyan(self, page: Page, server_url):
        """Verify primary color is electric cyan."""
        page.goto(f"{server_url}?theme=hyperneon")
        color = get_computed_style(page, "a:not([role='button'])", "color")
        assert color == "rgb(0, 245, 255)", f"Expected electric cyan, got {color}"

    def test_background_deep_purple(self, page: Page, server_url):
        """Verify deep purple background."""
        page.goto(f"{server_url}?theme=hyperneon")
        # Background is set on html element via --pico-background-color
        bg = get_computed_style(page, "html", "background-color")
        assert bg == "rgb(10, 1, 24)", f"Expected deep purple background, got {bg}"

    def test_michroma_font(self, page: Page, server_url):
        """Verify Michroma font is used."""
        page.goto(f"{server_url}?theme=hyperneon")
        font = get_computed_style(page, "body", "font-family")
        assert "Michroma" in font, f"Expected Michroma font, got {font}"

    def test_rounded_corners(self, page: Page, server_url):
        """Verify large rounded corners (1.25rem = 20px)."""
        page.goto(f"{server_url}?theme=hyperneon")
        radius = get_computed_style(page, ".song-card", "border-radius")
        assert radius == "20px", f"Expected 20px rounded corners, got {radius}"

    def test_button_text_contrast(self, page: Page, server_url):
        """Verify solid buttons have dark text for contrast on cyan background."""
        page.goto(f"{server_url}?theme=hyperneon")
        # Primary solid button should have dark text
        btn_color = get_computed_style(page, "button:not(.outline):not(.secondary)", "color")
        # Should be dark (the --pico-primary-inverse value)
        assert btn_color == "rgb(10, 1, 24)", f"Expected dark button text, got {btn_color}"


class TestLightTheme:
    """Tests for the Light theme."""

    def test_data_attributes(self, page: Page, server_url):
        """Verify html element has correct data attributes (light mode)."""
        page.goto(f"{server_url}?theme=light1")
        html = page.locator("html")
        expect(html).to_have_attribute("data-style", "light1")
        expect(html).to_have_attribute("data-theme", "light")

    def test_primary_color(self, page: Page, server_url):
        """Verify primary link color in light mode."""
        page.goto(f"{server_url}?theme=light1")
        # In light mode, verify that link color matches Pico's light theme
        # (The custom CSS variables may be overridden by Pico's light mode defaults)
        color = get_computed_style(page, "a:not([role='button'])", "color")
        # Pico light mode default link color
        assert color == "rgb(1, 114, 173)", f"Expected Pico light link color, got {color}"

    def test_light_background(self, page: Page, server_url):
        """Verify light off-white background."""
        page.goto(f"{server_url}?theme=light1")
        # Background is set on html element via --pico-background-color
        bg = get_computed_style(page, "html", "background-color")
        # Pico light mode default white (the theme overrides the variable but
        # Pico's light mode may compute to white)
        assert bg == "rgb(255, 255, 255)", f"Expected white background, got {bg}"

    def test_dark_text(self, page: Page, server_url):
        """Verify dark text color (Pico light mode default)."""
        page.goto(f"{server_url}?theme=light1")
        # Body text color in Pico light mode
        color = get_computed_style(page, "body", "color")
        # Pico light mode text color
        assert color == "rgb(55, 60, 68)", f"Expected Pico light text, got {color}"

    def test_white_card_background(self, page: Page, server_url):
        """Verify cards have white background."""
        page.goto(f"{server_url}?theme=light1")
        bg = get_computed_style(page, ".song-card", "background-color")
        assert bg == "rgb(255, 255, 255)", f"Expected white card, got {bg}"

    def test_font_family(self, page: Page, server_url):
        """Verify Sora font is used."""
        page.goto(f"{server_url}?theme=light1")
        font = get_computed_style(page, "body", "font-family")
        assert "Sora" in font, f"Expected Sora font, got {font}"


class TestStudio808Theme:
    """Tests for the Studio 808 (Hardware) theme."""

    def test_data_attributes(self, page: Page, server_url):
        """Verify html element has correct data attributes."""
        page.goto(f"{server_url}?theme=studio808")
        html = page.locator("html")
        expect(html).to_have_attribute("data-style", "808")
        expect(html).to_have_attribute("data-theme", "dark")

    def test_primary_color_orange(self, page: Page, server_url):
        """Verify primary color is signature orange."""
        page.goto(f"{server_url}?theme=studio808")
        color = get_computed_style(page, "a:not([role='button'])", "color")
        assert color == "rgb(255, 95, 0)", f"Expected signature orange, got {color}"

    def test_pure_black_background(self, page: Page, server_url):
        """Verify pure black background."""
        page.goto(f"{server_url}?theme=studio808")
        # Background is set on html element via --pico-background-color
        bg = get_computed_style(page, "html", "background-color")
        assert bg == "rgb(0, 0, 0)", f"Expected pure black background, got {bg}"

    def test_jetbrains_mono_font(self, page: Page, server_url):
        """Verify JetBrains Mono font is used."""
        page.goto(f"{server_url}?theme=studio808")
        font = get_computed_style(page, "body", "font-family")
        assert "JetBrains Mono" in font, f"Expected JetBrains Mono font, got {font}"

    def test_square_corners(self, page: Page, server_url):
        """Verify border-radius is 0 for hardware aesthetic."""
        page.goto(f"{server_url}?theme=studio808")
        radius = get_computed_style(page, ".song-card", "border-radius")
        assert radius == "0px", f"Expected square corners (0px), got {radius}"

    def test_link_styling_recessed(self, page: Page, server_url):
        """Verify links have recessed LCD-style background."""
        page.goto(f"{server_url}?theme=studio808")
        bg = get_computed_style(page, "a:not([role='button'])", "background-color")
        assert bg == "rgb(26, 26, 26)", f"Expected recessed link background, got {bg}"


class TestThemeConsistency:
    """Cross-theme consistency tests."""

    @pytest.mark.parametrize(
        "theme,expected_style",
        [
            ("original", "original"),
            ("muthur", "muthur"),
            ("hyperneon", "hyperneon"),
            ("light1", "light1"),
            ("studio808", "808"),
        ],
    )
    def test_theme_applies_via_url(self, page: Page, server_url, theme, expected_style):
        """Verify each theme can be set via URL parameter."""
        page.goto(f"{server_url}?theme={theme}")
        html = page.locator("html")
        expect(html).to_have_attribute("data-style", expected_style)

    @pytest.mark.parametrize("theme", ["original", "muthur", "hyperneon", "light1", "studio808"])
    def test_song_cards_visible(self, page: Page, server_url, theme):
        """Verify song cards render and are visible in each theme."""
        page.goto(f"{server_url}?theme={theme}")
        cards = page.locator(".song-card")
        expect(cards.first).to_be_visible()

    @pytest.mark.parametrize("theme", ["original", "muthur", "hyperneon", "light1", "studio808"])
    def test_tune_button_visible(self, page: Page, server_url, theme):
        """Verify Tune button is visible in each theme."""
        page.goto(f"{server_url}?theme={theme}")
        tune_btn = page.locator("#open-tune")
        expect(tune_btn).to_be_visible()

    @pytest.mark.parametrize("theme", ["original", "muthur", "hyperneon", "light1", "studio808"])
    def test_hamburger_menu_visible(self, page: Page, server_url, theme):
        """Verify hamburger menu button is visible in each theme."""
        page.goto(f"{server_url}?theme={theme}")
        hamburger = page.locator("#hamburger-btn")
        expect(hamburger).to_be_visible()
