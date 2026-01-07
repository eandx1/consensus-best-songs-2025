from playwright.sync_api import Page, expect
import re

def test_stats_modal_content(page: Page, server_url):
    """Test that stats modal shows correct scores."""
    page.goto(server_url)
    
    # Find "WHERE IS MY HUSBAND!" by RAYE (appears on 10 lists)
    card = page.locator(".song-card", has_text="WHERE IS MY HUSBAND!").first
    
    # Click info icon
    card.locator("header a[aria-label='View ranking details']").click()
    
    modal = page.locator("#modal-stats")
    expect(modal).to_be_visible()
    
    # Check List Count
    # "WHERE IS MY HUSBAND!" is on 10 lists
    expect(modal.locator("text=List Count").locator("..")).to_contain_text("10")
    
    # Check Source Contributions table presence
    expect(modal.locator("text=Source Contributions")).to_be_visible()
    # Count rows in the Source Contributions table's tbody (excluding header)
    # Table is now inside section > figure structure
    contributions_table = modal.locator("section:has(h5:has-text('Source Contributions')) table tbody tr")
    expect(contributions_table).to_have_count(10)
    
    # Check that the first song (top ranked) has a normalized score of 1.0
    normalized_score_row = modal.locator("text=Normalized Score").locator("..")
    expect(normalized_score_row).to_be_visible()
    # The normalized score should be 1.0 or 1.00 or 1.000 (formatted)
    expect(normalized_score_row).to_contain_text(re.compile(r"1\.0+"))

def test_stats_modal_top_button(page: Page, server_url):
    """Test that Top button scrolls to top of modal."""
    page.goto(server_url)
    
    # Find a song with many sources to make the modal scrollable
    card = page.locator(".song-card", has_text="WHERE IS MY HUSBAND!").first
    card.locator("header a[aria-label='View ranking details']").click()
    
    modal = page.locator("#modal-stats")
    expect(modal).to_be_visible()
    
    # Scroll to bottom of modal
    page.evaluate("document.querySelector('#modal-stats article').scrollTop = document.querySelector('#modal-stats article').scrollHeight")
    
    # Click Top button
    top_button = modal.get_by_role("button", name="Top")
    expect(top_button).to_be_visible()
    top_button.click()
    
    # Wait for smooth scroll animation
    page.wait_for_timeout(1000)
    
    # Modal should be scrolled back to top
    scroll_top = page.evaluate("document.querySelector('#modal-stats article').scrollTop")
    assert scroll_top < 50, f"Modal should be scrolled to top, but scrollTop is {scroll_top}"

def test_stats_modal_close_button(page: Page, server_url):
    """Test that Close button closes the modal."""
    page.goto(server_url)
    
    card = page.locator(".song-card").first
    card.locator("header a[aria-label='View ranking details']").click()
    
    modal = page.locator("#modal-stats")
    expect(modal).to_be_visible()
    
    # Click Close button
    close_button = modal.locator("footer button.close-modal")
    close_button.click()
    
    # Modal should be closed
    expect(modal).not_to_be_visible()

