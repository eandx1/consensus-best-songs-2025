from playwright.sync_api import Page, expect

def test_tune_modal_structure(page: Page, server_url):
    """Test that Tune modal has correct sections (theme moved to hamburger menu)."""
    page.goto(server_url)

    page.locator("#open-tune").click()
    modal = page.locator("#modal-tune")
    expect(modal).to_be_visible()

    content = page.locator("#tune-content")
    expect(content.locator("h4", has_text="Ranking Parameters")).to_be_visible()
    expect(content.locator("h4", has_text="Source Weights")).to_be_visible()
    expect(content.locator("h4", has_text="Shadow Ranks")).to_be_visible()
    # Note: Interface section (with theme) has been moved to hamburger menu

def test_settings_values_match_data(page: Page, server_url):
    """Test that sliders reflect values from test_data.json."""
    page.goto(server_url)
    page.locator("#open-tune").click()
    
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
    page.locator("#open-tune").click()
    
    # Change k_value
    k_slider = page.locator("#setting-ranking-k_value")
    k_slider.fill("50")
    k_slider.dispatch_event("input")
    expect(k_slider).to_have_value("50")
    
    # Click Defaults
    page.locator("#reset-defaults").click()
    
    # Check it reverted to 20
    expect(k_slider).to_have_value("20")

def test_tune_modal_top_button(page: Page, server_url):
    """Test that Top button scrolls to top of modal."""
    page.goto(server_url)
    
    page.locator("#open-tune").click()
    
    modal = page.locator("#modal-tune")
    expect(modal).to_be_visible()
    
    # Scroll to bottom of modal
    page.evaluate("document.querySelector('#modal-tune article').scrollTop = document.querySelector('#modal-tune article').scrollHeight")
    
    # Click Top button
    top_button = modal.get_by_role("button", name="Top")
    expect(top_button).to_be_visible()
    top_button.click()

    # Wait for smooth scroll animation to complete by polling until scroll position stabilizes near top
    # This is more robust than a fixed timeout, especially in CI environments
    page.wait_for_function(
        """() => {
            const article = document.querySelector('#modal-tune article');
            return article && article.scrollTop < 100;
        }""",
        timeout=3000
    )

    # Modal should be scrolled back to top
    scroll_top = page.evaluate("document.querySelector('#modal-tune article').scrollTop")
    assert scroll_top < 100, f"Modal should be scrolled to top, but scrollTop is {scroll_top}"

def test_tune_modal_close_button(page: Page, server_url):
    """Test that Close button closes the modal."""
    page.goto(server_url)

    page.locator("#open-tune").click()

    modal = page.locator("#modal-tune")
    expect(modal).to_be_visible()

    # Click Close button
    close_button = modal.locator("footer button.close-modal")
    close_button.click()

    # Modal should be closed
    expect(modal).not_to_be_visible()

