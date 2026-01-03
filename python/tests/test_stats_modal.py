from playwright.sync_api import Page, expect

def test_stats_modal_content(page: Page, server_url):
    """Test that stats modal shows correct scores."""
    page.goto(server_url)
    
    # Find Berghain
    card = page.locator(".song-card", has_text="Berghain").first
    
    # Click info icon
    card.locator("header a[aria-label='View ranking details']").click()
    
    modal = page.locator("#modal-stats")
    expect(modal).to_be_visible()
    
    # Check List Count
    # Berghain is on 9 lists
    expect(modal.locator("text=List Count").locator("..")).to_contain_text("9")
    
    # Check Source Contributions table presence
    expect(modal.locator("text=Source Contributions")).to_be_visible()
    expect(modal.locator(".contribution-row")).to_have_count(9)

