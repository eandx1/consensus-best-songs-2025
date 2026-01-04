from playwright.sync_api import Page, expect

def test_reviews_modal_content(page: Page, server_url):
    """Test that clicking sources opens reviews modal with correct content."""
    page.goto(server_url)
    
    # Find "WHERE IS MY HUSBAND!" by RAYE (appears on many lists including Guardian #17)
    card = page.locator(".song-card", has_text="WHERE IS MY HUSBAND!").first
    
    # Click the sources list
    card.locator("[data-sources]").click()
    
    modal = page.locator("#modal-reviews")
    expect(modal).to_be_visible()
    
    # Check for specific reviews
    # Guardian #17
    guardian_review = modal.locator("#reviews-content article", has_text="The Guardian")
    expect(guardian_review).to_be_visible()
    expect(guardian_review).to_contain_text("#17")
    expect(guardian_review).to_contain_text("delivered so knowingly")
    
    # Check link
    expect(guardian_review.locator("a", has_text="Read Full Review")).to_have_attribute("href", "https://www.theguardian.com/music/ng-interactive/2025/dec/03/the-20-best-songs-of-2025")

def test_shadow_rank_display(page: Page, server_url):
    """Test that shadow ranks are displayed with the ghost emoji."""
    page.goto(server_url)
    
    # Use "Townies" by Wednesday which has "NPR Top 25" (shadow rank)
    card = page.locator(".song-card", has_text="Townies").first
    card.locator("[data-sources]").click()
    
    modal = page.locator("#modal-reviews")
    expect(modal).to_be_visible()
    
    npr = modal.locator("#reviews-content article", has_text="NPR Top 25")
    expect(npr).to_be_visible()
    expect(npr).to_contain_text("👻")

