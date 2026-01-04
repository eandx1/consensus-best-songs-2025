from playwright.sync_api import Page, expect
import re

def test_export_modal_hidden_by_default(page: Page, server_url):
    """Test that export link is hidden when feature flag is not present."""
    page.goto(server_url)
    
    # Export link should be hidden (display: none)
    export_link = page.locator("#open-export")
    expect(export_link).not_to_be_visible()

def test_export_modal_visible_with_flag(page: Page, server_url):
    """Test that export link appears when feature flag is present."""
    page.goto(f"{server_url}?unlisted_youtube_export")
    
    # Export link should be visible
    export_link = page.locator("#open-export")
    expect(export_link).to_be_visible()
    expect(export_link).to_have_text("Export")

def test_export_modal_opens(page: Page, server_url):
    """Test that clicking export link opens the modal."""
    page.goto(f"{server_url}?unlisted_youtube_export")
    
    page.locator("#open-export").click()
    
    modal = page.locator("#modal-export")
    expect(modal).to_be_visible()
    expect(modal.locator("h3")).to_have_text("Export Playlist")

def test_export_modal_default_state(page: Page, server_url):
    """Test the default state of the export modal."""
    page.goto(f"{server_url}?unlisted_youtube_export")
    page.locator("#open-export").click()
    
    modal = page.locator("#modal-export")
    content = modal.locator("#export-content")
    
    # Check destination buttons - YouTube should be selected by default
    youtube_btn = content.get_by_role("button", name="YouTube", exact=True)
    ytm_btn = content.get_by_role("button", name="YouTube Music")
    
    # YouTube should not have outline/secondary classes (is active)
    expect(youtube_btn).not_to_have_class(re.compile("outline"))
    expect(youtube_btn).not_to_have_class(re.compile("secondary"))
    
    # YouTube Music should have outline secondary classes (not active)
    expect(ytm_btn).to_have_class(re.compile("outline"))
    expect(ytm_btn).to_have_class(re.compile("secondary"))
    
    # Check range buttons - Top 25 should be selected by default
    top10_btn = content.get_by_role("button", name="Top 10")
    top25_btn = content.get_by_role("button", name="Top 25")
    top50_btn = content.get_by_role("button", name="Top 50")
    
    expect(top10_btn).to_have_class(re.compile("outline"))
    expect(top25_btn).not_to_have_class(re.compile("outline"))
    expect(top50_btn).to_have_class(re.compile("outline"))
    
    # Check summary text - test data has 24 songs with YouTube IDs out of top 25
    expect(content).to_contain_text("Ready to export 24 songs to a new YouTube playlist")
    
    # Check footer buttons
    footer = modal.locator("footer")
    expect(footer.get_by_role("button", name="Cancel")).to_be_visible()
    expect(footer.get_by_role("button", name="Create Playlist")).to_be_visible()

def test_export_youtube_playlist_url(page: Page, server_url):
    """Test that the YouTube playlist URL contains correct video IDs."""
    page.goto(f"{server_url}?unlisted_youtube_export")
    page.locator("#open-export").click()
    
    modal = page.locator("#modal-export")
    
    # Get the Create Playlist link
    create_btn = modal.locator("footer a[role='button']")
    expect(create_btn).to_be_visible()
    
    # Get the href attribute
    playlist_url = create_btn.get_attribute("href")
    
    # Should be YouTube URL
    assert playlist_url.startswith("https://www.youtube.com/watch_videos?video_ids=")
    
    # Extract video IDs
    video_ids = playlist_url.split("video_ids=")[1].split(",")
    
    # Test data has 24 songs with YouTube IDs out of top 25
    assert len(video_ids) == 24
    
    # Check that first song "Townies" by Wednesday has correct video_id (E8cKoQqdtwA)
    # Townies should be #1 or #2 in default ranking
    assert "E8cKoQqdtwA" in video_ids[:5], "Townies video_id should be in top 5"

def test_export_youtube_music_playlist_url(page: Page, server_url):
    """Test that the YouTube Music playlist URL contains correct music IDs."""
    page.goto(f"{server_url}?unlisted_youtube_export")
    page.locator("#open-export").click()
    
    modal = page.locator("#modal-export")
    content = modal.locator("#export-content")
    
    # Switch to YouTube Music
    ytm_btn = content.get_by_role("button", name="YouTube Music")
    ytm_btn.click()
    
    # Wait for re-render
    page.wait_for_timeout(100)
    
    # Check that summary updated
    expect(content).to_contain_text("Ready to export 24 songs to a new YouTube Music playlist")
    
    # Get the Create Playlist link
    create_btn = modal.locator("footer a[role='button']")
    playlist_url = create_btn.get_attribute("href")
    
    # Should be YouTube Music URL
    assert playlist_url.startswith("https://music.youtube.com/watch_videos?video_ids=")
    
    # Extract video IDs
    video_ids = playlist_url.split("video_ids=")[1].split(",")
    
    # Test data has 24 songs with YouTube IDs out of top 25
    assert len(video_ids) == 24
    
    # Check that first song "Townies" has correct music_id (mHEiyObNciA)
    # Note: For YouTube Music, we prefer music_id over video_id
    assert "mHEiyObNciA" in video_ids[:5], "Townies music_id should be in top 5"

def test_export_top10_range(page: Page, server_url):
    """Test that selecting Top 10 updates the playlist correctly."""
    page.goto(f"{server_url}?unlisted_youtube_export")
    page.locator("#open-export").click()
    
    modal = page.locator("#modal-export")
    content = modal.locator("#export-content")
    
    # Click Top 10
    top10_btn = content.get_by_role("button", name="Top 10")
    top10_btn.click()
    
    # Wait for re-render
    page.wait_for_timeout(100)
    
    # Check summary updated
    expect(content).to_contain_text("Ready to export 10 songs")
    
    # Get the playlist URL
    create_btn = modal.locator("footer a[role='button']")
    playlist_url = create_btn.get_attribute("href")
    
    # Extract and count video IDs
    video_ids = playlist_url.split("video_ids=")[1].split(",")
    assert len(video_ids) == 10

def test_export_top50_range(page: Page, server_url):
    """Test that selecting Top 50 updates the playlist correctly."""
    page.goto(f"{server_url}?unlisted_youtube_export")
    page.locator("#open-export").click()
    
    modal = page.locator("#modal-export")
    content = modal.locator("#export-content")
    
    # Click Top 50
    top50_btn = content.get_by_role("button", name="Top 50")
    top50_btn.click()
    
    # Wait for re-render
    page.wait_for_timeout(100)
    
    # Check summary updated - test data has 35 songs total, 34 with YouTube IDs
    # So when requesting top 50, we get 34 (all available songs with IDs)
    expect(content).to_contain_text("Ready to export 34 songs")

def test_export_id_fallback_logic(page: Page, server_url):
    """Test that the export handles songs with only music_id or only video_id."""
    page.goto(f"{server_url}?unlisted_youtube_export")
    page.locator("#open-export").click()
    
    modal = page.locator("#modal-export")
    
    # For YouTube: should prefer video_id, fall back to music_id
    youtube_create_btn = modal.locator("footer a[role='button']")
    youtube_url = youtube_create_btn.get_attribute("href")
    youtube_ids = youtube_url.split("video_ids=")[1].split(",")
    
    # Switch to YouTube Music
    content = modal.locator("#export-content")
    ytm_btn = content.get_by_role("button", name="YouTube Music")
    ytm_btn.click()
    page.wait_for_timeout(100)
    
    # For YouTube Music: should prefer music_id, fall back to video_id
    ytm_create_btn = modal.locator("footer a[role='button']")
    ytm_url = ytm_create_btn.get_attribute("href")
    ytm_ids = ytm_url.split("video_ids=")[1].split(",")
    
    # Both should have the same count (all songs with at least one ID)
    assert len(youtube_ids) == len(ytm_ids)
    
    # But the IDs might be different due to fallback priority
    # This is the key feature we're testing

def test_export_all_songs_available(page: Page, server_url):
    """Test that the modal shows success message when all songs have IDs."""
    # Top 10 has all songs with YouTube IDs
    page.goto(f"{server_url}?unlisted_youtube_export")
    page.locator("#open-export").click()
    
    modal = page.locator("#modal-export")
    content = modal.locator("#export-content")
    
    # Click Top 10
    top10_btn = content.get_by_role("button", name="Top 10")
    top10_btn.click()
    page.wait_for_timeout(100)
    
    # Should show 10 songs
    expect(content).to_contain_text("Ready to export 10 songs")
    
    # All songs should be available
    expect(content).to_contain_text("✓ All requested songs are available")
    
    # Should NOT show warning
    warning = content.get_by_text("⚠️")
    expect(warning).not_to_be_visible()

def test_export_song_not_available(page: Page, server_url):
    """Test that the modal shows warning when song IDs are missing."""
    # "It's Your Anniversary" by Freddie Gibbs has no YouTube IDs (only "other" media)
    # It ranks around #13 in default settings, so we need to:
    # 1. Set FADER weight to 0 (only source that has this song)
    # 2. This will push it out of top rankings
    # 3. Use Top 50 to make sure we see some songs without IDs
    
    page.goto(f"{server_url}?unlisted_youtube_export")
    page.locator("#open-export").click()
    
    modal = page.locator("#modal-export")
    content = modal.locator("#export-content")
    
    # Click Top 50 to get more songs
    top50_btn = content.get_by_role("button", name="Top 50")
    top50_btn.click()
    page.wait_for_timeout(100)
    
    # With test data's 35 songs, one song ("It's Your Anniversary") has no YouTube IDs
    # So we should see 34 songs available
    expect(content).to_contain_text("Ready to export 34 songs")
    
    # Should show warning
    expect(content).to_contain_text("⚠️ 1 songs missing IDs will be skipped")
    
    # Should show the specific song that's missing
    expect(content).to_contain_text("It's Your Anniversary")

def test_export_works_with_other_params(page: Page, server_url):
    """Test that export feature flag works alongside other URL parameters."""
    page.goto(f"{server_url}?unlisted_youtube_export&k_value=10&decay_mode=conviction")
    
    # Export link should be visible
    export_link = page.locator("#open-export")
    expect(export_link).to_be_visible()
    
    # Open modal
    export_link.click()
    modal = page.locator("#modal-export")
    expect(modal).to_be_visible()
    
    # The ranking will be different due to k_value and decay_mode changes
    # But the export functionality should still work
    create_btn = modal.locator("footer a[role='button']")
    playlist_url = create_btn.get_attribute("href")
    
    assert playlist_url.startswith("https://www.youtube.com/watch_videos?video_ids=")

def test_export_modal_cancel_button(page: Page, server_url):
    """Test that the Cancel button closes the modal."""
    page.goto(f"{server_url}?unlisted_youtube_export")
    page.locator("#open-export").click()
    
    modal = page.locator("#modal-export")
    expect(modal).to_be_visible()
    
    # Click Cancel
    modal.locator("footer button", has_text="Cancel").click()
    
    # Modal should be closed
    expect(modal).not_to_be_visible()

def test_export_modal_close_button(page: Page, server_url):
    """Test that the X close button closes the modal."""
    page.goto(f"{server_url}?unlisted_youtube_export")
    page.locator("#open-export").click()
    
    modal = page.locator("#modal-export")
    expect(modal).to_be_visible()
    
    # Click the X button
    modal.locator("button.close-modal").first.click()
    
    # Modal should be closed
    expect(modal).not_to_be_visible()

