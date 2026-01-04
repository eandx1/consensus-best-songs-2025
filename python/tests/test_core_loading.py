import re
from playwright.sync_api import Page, expect

def test_page_loads(page: Page, server_url):
    """Test that the page loads and the title is correct."""
    page.goto(server_url)
    expect(page).to_have_title(re.compile("Consensus Best Songs 2025"))

def test_initial_song_list(page: Page, server_url):
    """Test that the initial list of songs is rendered."""
    page.goto(server_url)
    
    # Wait for the song list to be populated (look for at least one song card)
    song_cards = page.locator(".song-card")
    expect(song_cards.first).to_be_visible()
    
    # Check default progressive loading count (25)
    count = song_cards.count()
    
    assert count == 25

def test_specific_song_content(page: Page, server_url):
    """Test that a specific song from test_data.json is rendered correctly."""
    page.goto(server_url)
    
    # Look for the top ranked song. Based on test_data.json with consensus mode,
    # "RAYE - WHERE IS MY HUSBAND!" appears on 10 lists and should rank highly.
    
    first_card = page.locator(".song-card").first
    
    # Check rank
    expect(first_card.locator(".rank-display")).to_contain_text("#1")
    
    # Check title and artist - RAYE's song should be #1 with 10 list appearances
    expect(first_card.locator("h3")).to_contain_text("WHERE IS MY HUSBAND!")
    expect(first_card.locator("h4")).to_contain_text("RAYE")
    
    # Check genre pill
    expect(first_card.locator(".song-genres")).to_contain_text("Pop")

def test_show_more_functionality(page: Page, server_url):
    """Test the 'Show More' button if applicable."""
    # test_data.json has 35 songs, so with default page size of 25,
    # the Show More button should be visible with "Show All (10 more)"
    page.goto(server_url)
    
    show_more_btn = page.locator("#load-more")
    
    # Wait for data to load
    page.locator(".song-card").first.wait_for()
    
    # With 35 songs and page size 25, button should be visible
    expect(show_more_btn).to_be_visible()
    expect(show_more_btn).to_contain_text("10")

