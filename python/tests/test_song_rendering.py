import re
from playwright.sync_api import Page, expect

def test_media_links_berghain(page: Page, server_url):
    """Test that a song with YT, Apple, and Spotify renders correct links."""
    page.goto(server_url)
    
    # Find "WHERE IS MY HUSBAND!" by RAYE (has video_id, music_id, Apple, Spotify)
    card = page.locator(".song-card", has_text="WHERE IS MY HUSBAND!").first
    
    # Check links
    nav = card.locator("nav")
    expect(nav).to_be_visible()
    
    # Check for specific links
    expect(nav.locator("a", has_text="YouTube")).to_be_visible()
    expect(nav.locator("a", has_text="YTM")).to_be_visible()
    expect(nav.locator("a", has_text="Apple")).to_be_visible()
    expect(nav.locator("a", has_text="Spotify")).to_be_visible()
    
    # Check hrefs (partial match)
    expect(nav.locator("a", has_text="YouTube")).to_have_attribute("href", re.compile("youtube.com/watch"))
    expect(nav.locator("a", has_text="Apple")).to_have_attribute("href", re.compile("music.apple.com"))

def test_media_links_bandcamp(page: Page, server_url):
    """Test that a song with Bandcamp link renders it."""
    page.goto(server_url)
    
    # Find "Townies" by Wednesday (has Bandcamp link)
    card = page.locator(".song-card", has_text="Townies").first
    
    expect(card).to_be_visible()
    
    nav = card.locator("nav")
    expect(nav.locator("a", has_text="Bandcamp")).to_be_visible()
    expect(nav.locator("a", has_text="Bandcamp")).to_have_attribute("href", re.compile("bandcamp.com"))

def test_lite_youtube_player(page: Page, server_url):
    """Test that the lite-youtube component is rendered with correct video ID."""
    page.goto(server_url)
    
    # "WHERE IS MY HUSBAND!" by RAYE has video_id="rK5TyISxZ_M"
    card = page.locator(".song-card", has_text="WHERE IS MY HUSBAND!").first
    
    player = card.locator("lite-youtube")
    expect(player).to_be_visible()
    expect(player).to_have_attribute("videoid", "rK5TyISxZ_M")
    expect(player).to_have_attribute("playlabel", "Play WHERE IS MY HUSBAND!")

