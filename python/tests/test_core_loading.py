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
    # Note: data.json might have fewer than 25 songs in test data, 
    # but our test data has 18 songs based on the file read earlier.
    # So we expect 18 songs (all of them) if the limit is 25.
    count = song_cards.count()
    assert count > 0
    assert count <= 25

def test_specific_song_content(page: Page, server_url):
    """Test that a specific song from test_data.json is rendered correctly."""
    page.goto(server_url)
    
    # Look for the top ranked song. Based on test_data.json, "Berghain" should be #1.
    
    first_card = page.locator(".song-card").first
    
    # Check rank
    expect(first_card.locator(".rank-display")).to_contain_text("#1")
    
    # Check title and artist
    expect(first_card.locator("h3")).to_contain_text("Berghain")
    expect(first_card.locator("h4")).to_contain_text("ROSALÍA")
    
    # Check genre pill
    expect(first_card.locator(".song-genres")).to_contain_text("Latin")

def test_show_more_functionality(page: Page, server_url):
    """Test the 'Show More' button if applicable."""
    # Since our test data only has ~18 songs, the 'Show More' button might not appear 
    # or might behave differently if the default page size is 25.
    # Let's check if it's hidden since 18 < 25.
    page.goto(server_url)
    
    show_more_btn = page.locator("#load-more-btn")
    
    # Wait for data to load
    page.locator(".song-card").first.wait_for()
    
    # With 18 songs and page size 25, button should be hidden
    expect(show_more_btn).to_be_hidden()

