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
    
    # Check media links with correct URLs
    nav = first_card.locator("nav")
    expect(nav).to_be_visible()
    
    # YouTube link with video_id
    yt_link = nav.locator("a", has_text="YouTube")
    expect(yt_link).to_be_visible()
    expect(yt_link).to_have_attribute("href", "https://www.youtube.com/watch?v=rK5TyISxZ_M")
    
    # YouTube Music link with music_id
    ytm_link = nav.locator("a", has_text="YTM")
    expect(ytm_link).to_be_visible()
    expect(ytm_link).to_have_attribute("href", "https://music.youtube.com/watch?v=V3NbrjVPIHM")
    
    # Spotify link
    spotify_link = nav.locator("a", has_text="Spotify")
    expect(spotify_link).to_be_visible()
    expect(spotify_link).to_have_attribute("href", re.compile("spotify.*55lijDD6OAjLFFUHU9tcDm"))
    
    # Apple Music link
    apple_link = nav.locator("a", has_text="Apple")
    expect(apple_link).to_be_visible()
    expect(apple_link).to_have_attribute("href", "https://geo.music.apple.com/us/album/where-is-my-husband/1838737596?i=1838737598")
    
    # Check sources list and ranks
    # Expected: Buzzfeed#3 · The Independent (Top 10) · NPR Top 25 · Billboard (Staff Picks)#16 · 
    # The Guardian#17 · NME#18 · Rolling Stone#24 · ELLE (Top 48) · Rough Trade (Top 63) · Consequence#129
    sources = first_card.locator("[data-sources]")
    expect(sources).to_be_visible()
    expect(sources).to_contain_text("Buzzfeed#3")
    expect(sources).to_contain_text("Independent")
    expect(sources).to_contain_text("NPR Top 25")
    expect(sources).to_contain_text("Billboard")
    expect(sources).to_contain_text("#16")
    expect(sources).to_contain_text("Guardian#17")
    expect(sources).to_contain_text("NME#18")
    expect(sources).to_contain_text("Rolling Stone#24")
    expect(sources).to_contain_text("ELLE")
    expect(sources).to_contain_text("Rough Trade")
    expect(sources).to_contain_text("Consequence#129")

def test_show_more_functionality(page: Page, server_url):
    """Test the 'Show More' button expands the song list."""
    # test_data.json has 35 songs, so with default page size of 25,
    # clicking the button should expand to show all 35 songs
    page.goto(server_url)
    
    show_more_btn = page.locator("#load-more")
    
    # Wait for data to load
    page.locator(".song-card").first.wait_for()
    
    # Initially should have 25 songs displayed
    song_cards = page.locator(".song-card")
    initial_count = song_cards.count()
    assert initial_count == 25
    
    # Button should be visible and show "10" remaining
    expect(show_more_btn).to_be_visible()
    expect(show_more_btn).to_contain_text("10")
    
    # Click the button
    show_more_btn.click()
    
    # Wait a moment for the list to update
    page.wait_for_timeout(100)
    
    # Now should have all 35 songs displayed
    expanded_count = song_cards.count()
    assert expanded_count == 35
    
    # Button should now be hidden since all songs are shown
    expect(show_more_btn).to_be_hidden()

def test_back_to_top_button(page: Page, server_url):
    """Test that the Back to Top button scrolls to the top of the page."""
    page.goto(server_url)
    
    # Wait for page to load
    page.locator(".song-card").first.wait_for()
    
    # Click Show More to load all songs and make page scrollable
    show_more_btn = page.locator("#load-more")
    show_more_btn.click()
    page.wait_for_timeout(100)
    
    # Back to Top button should be visible
    btt_button = page.locator("#main-btt")
    expect(btt_button).to_be_visible()
    expect(btt_button).to_contain_text("Back to top")
    
    # Scroll down the page
    page.evaluate("window.scrollTo({ top: 2000, behavior: 'instant' })")
    page.wait_for_timeout(100)
    
    # Verify we scrolled
    scroll_position = page.evaluate("window.scrollY")
    assert scroll_position > 500, f"Page should be scrolled down, but scrollY is {scroll_position}"
    
    # Scroll button into view first
    btt_button.scroll_into_view_if_needed()
    page.wait_for_timeout(100)
    
    # Click Back to Top button
    btt_button.click()
    
    # Wait for smooth scroll animation
    page.wait_for_timeout(1500)
    
    # Verify we scrolled back to top
    scroll_position = page.evaluate("window.scrollY")
    assert scroll_position < 100, f"Page should be scrolled to top, but scrollY is {scroll_position}"

