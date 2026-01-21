import re

from playwright.sync_api import Page, expect

from conftest import get_song_card, open_reviews_modal, show_all_songs


def test_reviews_modal_content(page: Page, server_url):
    """Test that clicking sources opens reviews modal with correct content."""
    page.goto(server_url)

    card = get_song_card(page, "WHERE IS MY HUSBAND!")
    open_reviews_modal(page, card)
    
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

    card = get_song_card(page, "Townies")
    open_reviews_modal(page, card)
    
    modal = page.locator("#modal-reviews")
    expect(modal).to_be_visible()
    
    npr = modal.locator("#reviews-content article", has_text="NPR Top 25")
    expect(npr).to_be_visible()
    expect(npr).to_contain_text("👻")

def test_reviews_modal_top_button(page: Page, server_url):
    """Test that Top button scrolls to top of modal."""
    page.goto(server_url)

    card = get_song_card(page, "WHERE IS MY HUSBAND!")
    open_reviews_modal(page, card)
    
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
    open_reviews_modal(page, card)

    modal = page.locator("#modal-reviews")
    expect(modal).to_be_visible()

    # Click Close button
    close_button = modal.locator("footer button.close-modal")
    close_button.click()

    # Modal should be closed
    expect(modal).not_to_be_visible()


def test_reviews_modal_quote_stereogum(page: Page, server_url):
    """Test that quote is displayed in reviews modal for Stereogum."""
    page.goto(server_url)

    card = get_song_card(page, "Townies")
    open_reviews_modal(page, card)

    modal = page.locator("#modal-reviews")
    expect(modal).to_be_visible()

    # Check Stereogum article has a blockquote with the quote
    stereogum_article = modal.locator("#reviews-content article", has_text="Stereogum")
    expect(stereogum_article).to_be_visible()
    expect(stereogum_article.locator("blockquote")).to_be_visible()
    expect(stereogum_article).to_contain_text("a master of writing grimy, evocative scenes")


def test_reviews_modal_no_quote_available(page: Page, server_url):
    """Test that 'No quote available' text is shown for sources without quotes."""
    page.goto(server_url)

    card = get_song_card(page, "Townies")
    open_reviews_modal(page, card)

    modal = page.locator("#modal-reviews")
    expect(modal).to_be_visible()

    # Check Pitchfork article exists and shows "No quote available"
    pitchfork_article = modal.locator("#reviews-content article", has_text="Pitchfork")
    expect(pitchfork_article).to_be_visible()
    expect(pitchfork_article).to_contain_text("No quote available")


def test_reviews_modal_unranked_source_shadow_rank_display(page: Page, server_url):
    """Test that unranked sources show shadow rank with ghost emoji in reviews modal."""
    page.goto(server_url)

    card = get_song_card(page, "WHERE IS MY HUSBAND!")
    open_reviews_modal(page, card)

    modal = page.locator("#modal-reviews")
    expect(modal).to_be_visible()

    # Check Independent shows ghost emoji with shadow rank (5.5)
    independent_article = modal.locator("#reviews-content article", has_text="Independent")
    expect(independent_article).to_be_visible()
    expect(independent_article).to_contain_text("👻")
    expect(independent_article).to_contain_text("5.5")

    # Check ELLE shows ghost emoji with shadow rank (24.5)
    elle_article = modal.locator("#reviews-content article", has_text="ELLE")
    expect(elle_article).to_be_visible()
    expect(elle_article).to_contain_text("👻")
    expect(elle_article).to_contain_text("24.5")


def test_reviews_modal_npr_top_125(page: Page, server_url):
    """Test that NPR Top 125 source displays correctly with ghost emoji."""
    page.goto(server_url)

    show_all_songs(page)

    card = get_song_card(page, "Ensalada")
    expect(card).to_be_visible()
    open_reviews_modal(page, card)

    modal = page.locator("#modal-reviews")
    expect(modal).to_be_visible()

    # Check NPR Top 125 article shows with ghost emoji for shadow rank
    npr_article = modal.locator("#reviews-content article", has_text="NPR Top 125")
    expect(npr_article).to_be_visible()
    expect(npr_article).to_contain_text("👻")

