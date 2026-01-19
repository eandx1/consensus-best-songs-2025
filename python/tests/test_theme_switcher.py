import pytest
from playwright.sync_api import Page, expect
import re

def test_theme_switcher_dropdown(page: Page, server_url):
    """Verify theme switcher dropdown in hamburger menu updates theme and URL."""
    # Load page
    page.goto(server_url)

    # Open hamburger menu
    page.locator("#hamburger-btn").click()

    # Wait for hamburger menu to be visible
    hamburger_menu = page.locator("#hamburger-menu")
    expect(hamburger_menu).to_be_visible()

    # Get the theme selector in the menu
    theme_select = hamburger_menu.locator("#menu-theme-select")

    # Test Studio 808 (studio808)
    theme_select.select_option("studio808")

    # Verify URL updated
    expect(page).to_have_url(re.compile(r".*theme=studio808"))

    # Verify html attributes updated
    html = page.locator("html")
    expect(html).to_have_attribute("data-theme", "dark")
    expect(html).to_have_attribute("data-style", "808")

    # Test Light theme
    theme_select.select_option("light1")

    # Verify URL updated
    expect(page).to_have_url(re.compile(r".*theme=light1"))

    # Verify html attributes updated (light mode)
    expect(html).to_have_attribute("data-theme", "light")
    expect(html).to_have_attribute("data-style", "light1")

def test_theme_switcher_shortcut(page: Page, server_url):
    """Verify Ctrl+T shortcut cycles themes when tskbd flag is enabled."""
    # Load page with tskbd flag to enable keyboard shortcuts
    page.goto(f"{server_url}?tskbd")
    
    # Default state (Original)
    html = page.locator("html")
    expect(html).to_have_attribute("data-style", "original")
    
    # Press Ctrl+T (cycles to Light)
    page.keyboard.press("Control+t")
    expect(page).to_have_url(re.compile(r".*theme=light1"))
    expect(html).to_have_attribute("data-style", "light1")
    
    # Press Ctrl+T (cycles to Studio 808)
    page.keyboard.press("Control+t")
    expect(page).to_have_url(re.compile(r".*theme=studio808"))
    expect(html).to_have_attribute("data-style", "808")
    
    # Press Ctrl+T (cycles back to Original)
    page.keyboard.press("Control+t")
    # Original is the default theme, so it may not appear in URL or may be explicit
    # Check the data-style attribute which is the source of truth
    expect(html).to_have_attribute("data-style", "original")
    # URL should either not have theme param or have theme=original
    current_url = page.url
    assert "theme=original" in current_url or "theme=" not in current_url or current_url.endswith("?tskbd=")

def test_theme_url_persistence(page: Page, server_url):
    """Verify loading page with theme param applies correct theme."""
    # Load page with Studio 808 theme
    page.goto(f"{server_url}?theme=studio808")

    html = page.locator("html")
    expect(html).to_have_attribute("data-style", "808")
    expect(html).to_have_attribute("data-theme", "dark")

    # Verify hamburger menu dropdown matches
    page.locator("#hamburger-btn").click()
    hamburger_menu = page.locator("#hamburger-menu")
    expect(hamburger_menu).to_be_visible()

    theme_select = hamburger_menu.locator("#menu-theme-select")
    expect(theme_select).to_have_value("studio808")
