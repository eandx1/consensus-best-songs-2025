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


def test_no_youtube_placeholder(page: Page, server_url):
    """Test that songs without YouTube IDs render a placeholder instead of lite-youtube."""
    page.goto(server_url)

    # Show all songs to find Freddie Gibbs song (it ranks lower)
    while page.locator("button", has_text="Show").is_visible():
        page.locator("button", has_text="Show").click()

    # "It's Your Anniversary" by Freddie Gibbs has no YouTube IDs in test_data.json
    card = page.locator(".song-card", has_text="It's Your Anniversary").first
    expect(card).to_be_visible()

    # Should NOT have lite-youtube
    expect(card.locator("lite-youtube")).not_to_be_attached()

    # Should have video-placeholder with the disc icon and text
    placeholder = card.locator(".video-placeholder")
    expect(placeholder).to_be_visible()
    expect(placeholder.locator("use")).to_have_attribute("href", "#icon-disc")
    expect(placeholder.locator("span")).to_have_text("Video unavailable")
    expect(placeholder).to_have_attribute("aria-label", "No video available for It's Your Anniversary")


def test_placeholder_has_correct_dimensions(page: Page, server_url):
    """Test that the video placeholder has 16:9 aspect ratio like lite-youtube."""
    page.goto(server_url)

    # Show all songs to find Freddie Gibbs song
    while page.locator("button", has_text="Show").is_visible():
        page.locator("button", has_text="Show").click()

    card = page.locator(".song-card", has_text="It's Your Anniversary").first
    placeholder = card.locator(".video-placeholder")

    # Get computed style to verify aspect ratio is applied
    aspect_ratio = placeholder.evaluate("el => getComputedStyle(el).aspectRatio")
    assert aspect_ratio == "16 / 9", f"Expected aspect-ratio '16 / 9', got '{aspect_ratio}'"


def test_song_with_youtube_has_player(page: Page, server_url):
    """Test that songs WITH YouTube IDs still render lite-youtube correctly."""
    page.goto(server_url)

    # "WHERE IS MY HUSBAND!" has both video_id and music_id
    card = page.locator(".song-card", has_text="WHERE IS MY HUSBAND!").first

    # Should have lite-youtube, NOT placeholder
    expect(card.locator("lite-youtube")).to_be_visible()
    expect(card.locator(".video-placeholder")).not_to_be_attached()


def test_media_links_other_url(page: Page, server_url):
    """Test that a song with only an 'Other' URL renders the Other link."""
    page.goto(server_url)

    # Show all songs to find Freddie Gibbs song (it ranks lower)
    while page.locator("button", has_text="Show").is_visible():
        page.locator("button", has_text="Show").click()

    # "It's Your Anniversary" by Freddie Gibbs has only media.other.url
    card = page.locator(".song-card", has_text="It's Your Anniversary").first
    expect(card).to_be_visible()

    nav = card.locator("nav")
    expect(nav.locator("a", has_text="Other")).to_be_visible()
    expect(nav.locator("a", has_text="Other")).to_have_attribute("href", re.compile("youonlydie1nce.com"))

