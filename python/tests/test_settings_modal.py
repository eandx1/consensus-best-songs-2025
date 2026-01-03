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

