import re
from playwright.sync_api import Page, expect


def test_tune_button_default_state(page: Page, server_url):
    """Test that the Tune button shows 'Tune' with sliders icon by default."""
    page.goto(server_url)
    page.wait_for_timeout(300)

    tune_btn = page.locator("#open-tune")
    expect(tune_btn).to_be_visible()

    # Should show "Tune" text (not "Tuned")
    expect(tune_btn).to_contain_text("Tune")
    expect(tune_btn).not_to_contain_text("Tuned")

    # Should have sliders icon
    expect(tune_btn.locator("use[href='#icon-sliders']")).to_be_visible()

    # Should not have 'tuned' class
    expect(tune_btn).not_to_have_class(re.compile("tuned"))


def test_tune_button_tuned_state_with_url_param(page: Page, server_url):
    """Test that the Tune button shows 'Tuned' with sliders icon when URL has custom params."""
    # k_value=30 differs from default (20 in test_data.json)
    page.goto(f"{server_url}/?k_value=30")
    page.wait_for_timeout(300)

    tune_btn = page.locator("#open-tune")
    expect(tune_btn).to_be_visible()

    # Should show "Tuned" text
    expect(tune_btn).to_contain_text("Tuned")

    # Should have sliders icon
    expect(tune_btn.locator("use[href='#icon-sliders']")).to_be_visible()

    # Should have 'tuned' class
    expect(tune_btn).to_have_class(re.compile("tuned"))


def test_tune_modal_header_default_state(page: Page, server_url):
    """Test that the Tune modal title is not highlighted by default."""
    page.goto(server_url)
    page.wait_for_timeout(300)

    # Open Tune modal
    page.locator("#open-tune").click()
    page.wait_for_timeout(200)

    modal = page.locator("#modal-tune")
    expect(modal).to_be_visible()

    # Header should show "Tune Ranking"
    header = modal.locator("article > header h3")
    expect(header).to_contain_text("Tune Ranking")

    # h3 should NOT have tuned class
    expect(header).not_to_have_class(re.compile(r"\btuned\b"))


def test_tune_modal_header_tuned_state(page: Page, server_url):
    """Test that the Tune modal title is highlighted when customized."""
    page.goto(f"{server_url}/?k_value=30")
    page.wait_for_timeout(300)

    # Open Tune modal
    page.locator("#open-tune").click()
    page.wait_for_timeout(200)

    modal = page.locator("#modal-tune")
    expect(modal).to_be_visible()

    # Header should show "Tuned Ranking" and have tuned class
    header = modal.locator("article > header h3")
    expect(header).to_contain_text("Tuned Ranking")
    expect(header).to_have_class(re.compile(r"\btuned\b"))


def test_youtube_modal_subtitle_default_state(page: Page, server_url):
    """Test that the YouTube modal subtitle shows default text when not customized."""
    page.goto(server_url)
    page.wait_for_timeout(300)

    # Open hamburger menu and click YouTube
    page.locator("#hamburger-btn").click()
    page.wait_for_timeout(100)
    page.locator("#open-youtube-menu").click()
    page.wait_for_timeout(200)

    modal = page.locator("#modal-youtube")
    expect(modal).to_be_visible()

    # Subtitle should show default text
    subtitle = modal.locator("article > header hgroup p")
    expect(subtitle).to_contain_text("Play the top songs as an unnamed playlist on YouTube")
    expect(subtitle).not_to_contain_text("tuned")


def test_youtube_modal_subtitle_tuned_state(page: Page, server_url):
    """Test that the YouTube modal subtitle shows tuned indicator when customized."""
    page.goto(f"{server_url}/?k_value=30")
    page.wait_for_timeout(300)

    # Open hamburger menu and click YouTube
    page.locator("#hamburger-btn").click()
    page.wait_for_timeout(100)
    page.locator("#open-youtube-menu").click()
    page.wait_for_timeout(200)

    modal = page.locator("#modal-youtube")
    expect(modal).to_be_visible()

    # Subtitle should mention "tuned" with sliders icon
    subtitle = modal.locator("article > header hgroup p")
    expect(subtitle).to_contain_text("tuned")
    expect(subtitle.locator("use[href='#icon-sliders']")).to_be_visible()


def test_download_modal_subtitle_default_state(page: Page, server_url):
    """Test that the Download modal subtitle shows default text when not customized."""
    page.goto(server_url)
    page.wait_for_timeout(300)

    # Open hamburger menu and click Download
    page.locator("#hamburger-btn").click()
    page.wait_for_timeout(100)
    page.locator("#open-download-menu").click()
    page.wait_for_timeout(200)

    modal = page.locator("#modal-download")
    expect(modal).to_be_visible()

    # Subtitle should show default text
    subtitle = modal.locator("article > header hgroup p")
    expect(subtitle).to_contain_text("Download as CSV and import to the streaming service")
    expect(subtitle).not_to_contain_text("tuned")


def test_download_modal_subtitle_tuned_state(page: Page, server_url):
    """Test that the Download modal subtitle shows tuned indicator when customized."""
    page.goto(f"{server_url}/?k_value=30")
    page.wait_for_timeout(300)

    # Open hamburger menu and click Download
    page.locator("#hamburger-btn").click()
    page.wait_for_timeout(100)
    page.locator("#open-download-menu").click()
    page.wait_for_timeout(200)

    modal = page.locator("#modal-download")
    expect(modal).to_be_visible()

    # Subtitle should mention "tuned" with sliders icon
    subtitle = modal.locator("article > header hgroup p")
    expect(subtitle).to_contain_text("tuned")
    expect(subtitle.locator("use[href='#icon-sliders']")).to_be_visible()


def test_reset_clears_tuned_state(page: Page, server_url):
    """Test that clicking Reset reverts to default state."""
    # Start with customized params
    page.goto(f"{server_url}/?k_value=30")
    page.wait_for_timeout(300)

    tune_btn = page.locator("#open-tune")

    # Should be in tuned state
    expect(tune_btn).to_contain_text("Tuned")
    expect(tune_btn).to_have_class(re.compile("tuned"))

    # Open Tune modal and click Reset
    tune_btn.click()
    page.wait_for_timeout(200)

    modal = page.locator("#modal-tune")
    expect(modal).to_be_visible()

    # h3 should have tuned class before reset
    header = modal.locator("article > header h3")
    expect(header).to_have_class(re.compile(r"\btuned\b"))
    expect(header).to_contain_text("Tuned Ranking")

    reset_btn = modal.locator("button", has_text="Reset")
    reset_btn.click()
    page.wait_for_timeout(500)  # Wait for debounce

    # h3 should NOT have tuned class after reset
    expect(header).not_to_have_class(re.compile(r"\btuned\b"))
    expect(header).to_contain_text("Tune Ranking")

    # Close modal
    modal.locator("button", has_text="Close").click()
    page.wait_for_timeout(200)

    # Tune button should revert to default state
    expect(tune_btn).to_contain_text("Tune")
    expect(tune_btn).not_to_contain_text("Tuned")
    expect(tune_btn).not_to_have_class(re.compile("tuned"))


def test_slider_change_triggers_tuned_state(page: Page, server_url):
    """Test that changing a slider triggers tuned state."""
    page.goto(server_url)
    page.wait_for_timeout(300)

    tune_btn = page.locator("#open-tune")

    # Should start in default state
    expect(tune_btn).not_to_have_class(re.compile("tuned"))

    # Open Tune modal
    tune_btn.click()
    page.wait_for_timeout(200)

    modal = page.locator("#modal-tune")

    # h3 should NOT have tuned class initially
    header = modal.locator("article > header h3")
    expect(header).not_to_have_class(re.compile(r"\btuned\b"))

    # Change K value slider
    slider = page.locator("#setting-ranking-k_value")
    page.evaluate("document.getElementById('setting-ranking-k_value').value = '35'")
    slider.dispatch_event("input")

    # Wait for debounce
    page.wait_for_timeout(500)

    # h3 should now have tuned class and show "Tuned Ranking"
    expect(header).to_have_class(re.compile(r"\btuned\b"))
    expect(header).to_contain_text("Tuned Ranking")

    # Close modal
    modal.locator("button", has_text="Close").click()
    page.wait_for_timeout(200)

    # Tune button should now show "Tuned"
    expect(tune_btn).to_contain_text("Tuned")
    expect(tune_btn).to_have_class(re.compile("tuned"))


def test_source_weight_change_triggers_tuned_state(page: Page, server_url):
    """Test that changing a source weight triggers tuned state."""
    page.goto(server_url)
    page.wait_for_timeout(300)

    tune_btn = page.locator("#open-tune")

    # Should start in default state
    expect(tune_btn).not_to_have_class(re.compile("tuned"))

    # Open Tune modal
    tune_btn.click()
    page.wait_for_timeout(200)

    modal = page.locator("#modal-tune")

    # h3 should NOT have tuned class initially
    header = modal.locator("article > header h3")
    expect(header).not_to_have_class(re.compile(r"\btuned\b"))

    # Find and change Buzzfeed weight slider
    slider = page.locator("#setting-source_weight-Buzzfeed")
    page.evaluate("document.getElementById('setting-source_weight-Buzzfeed').value = '0.75'")
    slider.dispatch_event("input")

    # Wait for debounce
    page.wait_for_timeout(500)

    # h3 should now have tuned class and show "Tuned Ranking"
    expect(header).to_have_class(re.compile(r"\btuned\b"))
    expect(header).to_contain_text("Tuned Ranking")

    # Close modal
    modal.locator("button", has_text="Close").click()
    page.wait_for_timeout(200)

    # Tune button should now show "Tuned"
    expect(tune_btn).to_contain_text("Tuned")
    expect(tune_btn).to_have_class(re.compile("tuned"))


def test_decay_mode_change_triggers_tuned_state(page: Page, server_url):
    """Test that switching decay mode triggers tuned state."""
    page.goto(server_url)
    page.wait_for_timeout(300)

    tune_btn = page.locator("#open-tune")

    # Should start in default state
    expect(tune_btn).not_to_have_class(re.compile("tuned"))

    # Open Tune modal
    tune_btn.click()
    page.wait_for_timeout(200)

    modal = page.locator("#modal-tune")

    # h3 should NOT have tuned class initially
    header = modal.locator("article > header h3")
    expect(header).not_to_have_class(re.compile(r"\btuned\b"))

    # Click on Conviction mode card
    conviction_card = page.locator("article.mode-card", has_text="🔥 Conviction")
    conviction_card.click()

    # Wait for debounce
    page.wait_for_timeout(500)

    # h3 should now have tuned class and show "Tuned Ranking"
    expect(header).to_have_class(re.compile(r"\btuned\b"))
    expect(header).to_contain_text("Tuned Ranking")

    # Close modal
    modal.locator("button", has_text="Close").click()
    page.wait_for_timeout(200)

    # Tune button should now show "Tuned"
    expect(tune_btn).to_contain_text("Tuned")
    expect(tune_btn).to_have_class(re.compile("tuned"))

    # URL should include decay_mode
    expect(page).to_have_url(re.compile("decay_mode=conviction"))
