from playwright.sync_api import Page, expect
import re

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
    
    # Check that ALL reviews have links to full reviews
    # There are 10 sources for this song
    review_articles = modal.locator("#reviews-content article")
    review_count = review_articles.count()
    assert review_count == 10
    
    # Check each article has a "Read Full Review" link
    for i in range(review_count):
        article = review_articles.nth(i)
        review_link = article.locator("a", has_text="Read Full Review")
        expect(review_link).to_be_visible()
        # Verify it has a valid href
        expect(review_link).to_have_attribute("href", re.compile("^https?://"))

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

def test_reviews_modal_top_button(page: Page, server_url):
    """Test that Top button scrolls to top of modal."""
    page.goto(server_url)
    
    # Find a song with many reviews to make the modal scrollable
    card = page.locator(".song-card", has_text="WHERE IS MY HUSBAND!").first
    card.locator("[data-sources]").click()
    
    modal = page.locator("#modal-reviews")
    expect(modal).to_be_visible()
    
    # Scroll to bottom of modal
    page.evaluate("document.querySelector('#modal-reviews article').scrollTop = document.querySelector('#modal-reviews article').scrollHeight")
    
    # Click Top button
    top_button = modal.get_by_role("button", name="Top")
    expect(top_button).to_be_visible()
    top_button.click()
    
    # Wait for smooth scroll animation
    page.wait_for_timeout(1000)
    
    # Modal should be scrolled back to top
    scroll_top = page.evaluate("document.querySelector('#modal-reviews article').scrollTop")
    assert scroll_top < 50, f"Modal should be scrolled to top, but scrollTop is {scroll_top}"

def test_reviews_modal_close_button(page: Page, server_url):
    """Test that Close button closes the modal."""
    page.goto(server_url)
    
    card = page.locator(".song-card").first
    card.locator("[data-sources]").click()
    
    modal = page.locator("#modal-reviews")
    expect(modal).to_be_visible()
    
    # Click Close button
    close_button = modal.locator("footer button.close-modal")
    close_button.click()
    
    # Modal should be closed
    expect(modal).not_to_be_visible()

