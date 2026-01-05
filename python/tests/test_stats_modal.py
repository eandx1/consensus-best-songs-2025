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
    expect(modal.locator(".contribution-row")).to_have_count(10)
    
    # Check that the first song (top ranked) has a normalized score of 1.0
    normalized_score_row = modal.locator("text=Normalized Score").locator("..")
    expect(normalized_score_row).to_be_visible()
    # The normalized score should be 1.0 or 1.00 or 1.000 (formatted)
    expect(normalized_score_row).to_contain_text(re.compile(r"1\.0+"))

