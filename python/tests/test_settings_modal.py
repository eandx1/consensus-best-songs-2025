import re
from playwright.sync_api import Page, expect

def test_settings_modal_structure(page: Page, server_url):
    """Test that settings modal has correct sections."""
    page.goto(server_url)
    
    page.locator("#open-settings").click()
    modal = page.locator("#modal-settings")
    expect(modal).to_be_visible()
    
    content = page.locator("#settings-content")
    expect(content.locator("h4", has_text="Ranking Parameters")).to_be_visible()
    expect(content.locator("h4", has_text="Source Weights")).to_be_visible()
    expect(content.locator("h4", has_text="Shadow Ranks")).to_be_visible()
    expect(content.locator("h4", has_text="Interface")).to_be_visible()

def test_settings_values_match_data(page: Page, server_url):
    """Test that sliders reflect values from test_data.json."""
    page.goto(server_url)
    page.locator("#open-settings").click()
    
    # k_value = 20
    k_slider = page.locator("#setting-ranking-k_value")
    expect(k_slider).to_have_value("20")
    
    # Check a specific source weight
    # "LA Times" weight = 1.0
    latimes_slider = page.locator("#setting-source_weight-LA_Times")
    expect(latimes_slider).to_have_value("1")

def test_reset_defaults(page: Page, server_url):
    """Test that the Defaults button resets modified values."""
    page.goto(server_url)
    page.locator("#open-settings").click()
    
    # Change k_value
    k_slider = page.locator("#setting-ranking-k_value")
    k_slider.fill("50")
    k_slider.dispatch_event("input")
    expect(k_slider).to_have_value("50")
    
    # Click Defaults
    page.locator("#reset-defaults").click()
    
    # Check it reverted to 20
    expect(k_slider).to_have_value("20")

def test_theme_dropdown_updates_url_and_style(page: Page, server_url):
    """Test that selecting a theme in dropdown updates URL and HTML attributes."""
    page.goto(server_url)
    page.locator("#open-settings").click()
    
    # Find the theme selector (last select in settings)
    theme_select = page.locator("#settings-content select").last
    
    # Verify initial state
    html = page.locator("html")
    expect(html).to_have_attribute("data-style", "original")
    expect(html).to_have_attribute("data-theme", "dark")
    
    # Change to light1 theme
    theme_select.select_option("light1")
    
    # Verify URL updated
    page.wait_for_url("**/?**theme=light1**")
    
    # Verify HTML attributes updated
    expect(html).to_have_attribute("data-style", "light1")
    expect(html).to_have_attribute("data-theme", "light")
    
    # Verify dropdown stayed selected
    expect(theme_select).to_have_value("light1")
    
    # Change to studio808 theme (dark mode)
    theme_select.select_option("studio808")
    
    # Verify URL updated
    page.wait_for_url("**/?**theme=studio808**")
    
    # Verify HTML attributes updated (should be dark mode)
    expect(html).to_have_attribute("data-style", "808")
    expect(html).to_have_attribute("data-theme", "dark")
    
    # Verify dropdown stayed selected
    expect(theme_select).to_have_value("studio808")

def test_theme_url_parameter_loads_correct_theme(page: Page, server_url):
    """Test that loading page with theme parameter applies correct theme."""
    # Load with studio808 theme
    page.goto(f"{server_url}/?theme=studio808")
    
    html = page.locator("html")
    expect(html).to_have_attribute("data-style", "808")
    expect(html).to_have_attribute("data-theme", "dark")
    
    # Verify settings dropdown matches
    page.locator("#open-settings").click()
    theme_select = page.locator("#settings-content select").last
    expect(theme_select).to_have_value("studio808")

def test_ctrl_t_cycles_themes_with_flag(page: Page, server_url):
    """Test that Ctrl+T keyboard shortcut cycles through themes when tskbd flag is present."""
    page.goto(f"{server_url}/?tskbd")
    
    html = page.locator("html")
    
    # Initial state should be original
    expect(html).to_have_attribute("data-style", "original")
    
    # Press Ctrl+T -> should cycle to light1
    page.keyboard.press("Control+t")
    page.wait_for_timeout(300)  # Wait for debounce
    expect(html).to_have_attribute("data-style", "light1")
    expect(page).to_have_url(re.compile(r".*theme=light1"))
    
    # Press Ctrl+T -> should cycle to studio808
    page.keyboard.press("Control+t")
    page.wait_for_timeout(300)
    expect(html).to_have_attribute("data-style", "808")
    expect(page).to_have_url(re.compile(r".*theme=studio808"))
    
    # Press Ctrl+T -> should cycle back to original
    page.keyboard.press("Control+t")
    page.wait_for_timeout(300)
    expect(html).to_have_attribute("data-style", "original")

def test_ctrl_t_disabled_without_flag(page: Page, server_url):
    """Test that Ctrl+T keyboard shortcut does NOT cycle themes without tskbd flag."""
    page.goto(server_url)
    
    html = page.locator("html")
    
    # Initial state should be original
    expect(html).to_have_attribute("data-style", "original")
    
    # Press Ctrl+T -> should NOT change theme
    page.keyboard.press("Control+t")
    page.wait_for_timeout(300)  # Wait for any potential change
    
    # Theme should still be original
    expect(html).to_have_attribute("data-style", "original")
    
    # URL should not have theme parameter
    expect(page).not_to_have_url(re.compile(r".*theme="))

def test_ctrl_t_updates_settings_dropdown(page: Page, server_url):
    """Test that Ctrl+T updates the settings modal dropdown."""
    page.goto(f"{server_url}/?tskbd")
    page.locator("#open-settings").click()
    
    theme_select = page.locator("#settings-content select").last
    
    # Initial value
    expect(theme_select).to_have_value("original")
    
    # Cycle theme with Ctrl+T
    page.keyboard.press("Control+t")
    page.wait_for_timeout(300)
    
    # Dropdown should update (may need to reopen settings to see update)
    # Close and reopen settings to refresh
    page.locator(".close-modal").first.click()
    page.locator("#open-settings").click()
    
    theme_select = page.locator("#settings-content select").last
    expect(theme_select).to_have_value("light1")

def test_theme_switch(page: Page, server_url):
    """Test theme switching updates URL and HTML attribute."""
    page.goto(server_url)
    
    # Verify default theme
    expect(page.locator("html")).to_have_attribute("data-theme", "dark")
    
    # Open settings and switch theme
    page.locator("#open-settings").click()
    # Find the theme selector (last select in settings)
    theme_select = page.locator("#settings-content select").last
    expect(theme_select).to_be_visible()
    
    # Verify the default theme is selected
    expect(theme_select).to_have_value("original")
    
    # Switch to light1 theme
    theme_select.select_option("light1")
    
    # Verify URL updated
    page.wait_for_url("**/?**theme=light1**")
    
    # Verify HTML attributes updated
    expect(page.locator("html")).to_have_attribute("data-style", "light1")
    expect(page.locator("html")).to_have_attribute("data-theme", "light")

def test_ctrl_t_updates_dropdown_while_modal_open(page: Page, server_url):
    """Test that Ctrl+T updates the dropdown value while settings modal is open."""
    page.goto(f"{server_url}/?tskbd")
    page.locator("#open-settings").click()
    
    theme_select = page.locator("#settings-content select").last
    
    # Initial value should be original
    expect(theme_select).to_have_value("original")
    
    # Press Ctrl+T while modal is open
    page.keyboard.press("Control+t")
    page.wait_for_timeout(300)
    
    # Dropdown should update immediately without closing/reopening modal
    expect(theme_select).to_have_value("light1")
    
    # Press Ctrl+T again
    page.keyboard.press("Control+t")
    page.wait_for_timeout(300)
    
    # Should now be studio808
    expect(theme_select).to_have_value("studio808")

def test_settings_modal_top_button(page: Page, server_url):
    """Test that Top button scrolls to top of modal."""
    page.goto(server_url)
    
    page.locator("#open-settings").click()
    
    modal = page.locator("#modal-settings")
    expect(modal).to_be_visible()
    
    # Scroll to bottom of modal
    page.evaluate("document.querySelector('#modal-settings article').scrollTop = document.querySelector('#modal-settings article').scrollHeight")
    
    # Click Top button
    top_button = modal.get_by_role("button", name="Top")
    expect(top_button).to_be_visible()
    top_button.click()

    # Wait for smooth scroll animation to complete by polling until scroll position stabilizes near top
    # This is more robust than a fixed timeout, especially in CI environments
    page.wait_for_function(
        """() => {
            const article = document.querySelector('#modal-settings article');
            return article && article.scrollTop < 100;
        }""",
        timeout=3000
    )

    # Modal should be scrolled back to top
    scroll_top = page.evaluate("document.querySelector('#modal-settings article').scrollTop")
    assert scroll_top < 100, f"Modal should be scrolled to top, but scrollTop is {scroll_top}"

def test_settings_modal_close_button(page: Page, server_url):
    """Test that Close button closes the modal."""
    page.goto(server_url)
    
    page.locator("#open-settings").click()
    
    modal = page.locator("#modal-settings")
    expect(modal).to_be_visible()
    
    # Click Close button
    close_button = modal.locator("footer button.close-modal")
    close_button.click()
    
    # Modal should be closed
    expect(modal).not_to_be_visible()

