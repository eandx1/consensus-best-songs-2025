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
    
    # Check preference buttons - Videos should be selected by default
    videos_btn = content.get_by_role("button", name="Videos", exact=True)
    songs_btn = content.get_by_role("button", name="Songs")
    
    # Videos should not have outline/secondary classes (is active)
    expect(videos_btn).not_to_have_class(re.compile("outline"))
    expect(videos_btn).not_to_have_class(re.compile("secondary"))
    
    # Songs should have outline secondary classes (not active)
    expect(songs_btn).to_have_class(re.compile("outline"))
    expect(songs_btn).to_have_class(re.compile("secondary"))
    
    # Check range buttons - Top 25 should be selected by default
    top10_btn = content.get_by_role("button", name="Top 10")
    top25_btn = content.get_by_role("button", name="Top 25")
    top50_btn = content.get_by_role("button", name="Top 50")
    
    expect(top10_btn).to_have_class(re.compile("outline"))
    expect(top25_btn).not_to_have_class(re.compile("outline"))
    expect(top50_btn).to_have_class(re.compile("outline"))
    
    # Check summary text - test data has 24 videos with YouTube IDs out of top 25
    expect(content).to_contain_text("Ready to export 24 videos to a new YouTube playlist")
    
    # Check footer buttons
    footer = modal.locator("footer")
    expect(footer.get_by_role("button", name="Cancel")).to_be_visible()
    expect(footer.get_by_role("button", name="Create Playlist")).to_be_visible()

def test_export_videos_preference_url(page: Page, server_url):
    """Test that Videos preference uses video_id with music_id fallback."""
    page.goto(f"{server_url}?unlisted_youtube_export")
    page.locator("#open-export").click()
    
    modal = page.locator("#modal-export")
    
    # Videos is default, so just check the URL
    create_btn = modal.locator("footer a[role='button']")
    expect(create_btn).to_be_visible()
    
    # Get the href attribute
    playlist_url = create_btn.get_attribute("href")
    
    # Should be YouTube URL (not music.youtube.com)
    assert playlist_url.startswith("https://www.youtube.com/watch_videos?video_ids=")
    
    # Extract video IDs
    video_ids = playlist_url.split("video_ids=")[1].split(",")
    
    # Test data has 24 songs with YouTube IDs out of top 25
    assert len(video_ids) == 24
    
    # Check that first song "Townies" by Wednesday has correct video_id (E8cKoQqdtwA)
    # When preferring videos, we should get video_id
    assert "E8cKoQqdtwA" in video_ids[:5], "Townies video_id should be in top 5"

def test_export_songs_preference_url(page: Page, server_url):
    """Test that Songs preference uses music_id with video_id fallback."""
    page.goto(f"{server_url}?unlisted_youtube_export")
    page.locator("#open-export").click()
    
    modal = page.locator("#modal-export")
    content = modal.locator("#export-content")
    
    # Switch to Songs preference
    songs_btn = content.get_by_role("button", name="Songs")
    songs_btn.click()
    
    # Wait for re-render
    page.wait_for_timeout(100)
    
    # Check that summary updated to say "songs"
    expect(content).to_contain_text("Ready to export 24 songs to a new YouTube playlist")
    
    # Get the Create Playlist link
    create_btn = modal.locator("footer a[role='button']")
    playlist_url = create_btn.get_attribute("href")
    
    # Should still be YouTube URL (music.youtube.com doesn't support this feature)
    assert playlist_url.startswith("https://www.youtube.com/watch_videos?video_ids=")
    
    # Extract IDs
    ids = playlist_url.split("video_ids=")[1].split(",")
    
    # Test data has 24 songs with YouTube IDs
    assert len(ids) == 24
    
    # When preferring songs, "Townies" should use music_id (mHEiyObNciA) instead of video_id
    # Note: The URL still goes to youtube.com, but uses the music_id
    assert "mHEiyObNciA" in ids[:5], "Townies music_id should be in top 5 when Songs preference is selected"

def test_export_preference_switch(page: Page, server_url):
    """Test switching between Videos and Songs preferences."""
    page.goto(f"{server_url}?unlisted_youtube_export")
    page.locator("#open-export").click()
    
    modal = page.locator("#modal-export")
    content = modal.locator("#export-content")
    
    # Start with Videos (default)
    expect(content).to_contain_text("videos")
    
    # Switch to Songs
    songs_btn = content.get_by_role("button", name="Songs")
    songs_btn.click()
    page.wait_for_timeout(100)
    
    # Should now say "songs"
    expect(content).to_contain_text("songs")
    expect(content).not_to_contain_text("videos to a new")
    
    # Switch back to Videos
    videos_btn = content.get_by_role("button", name="Videos")
    videos_btn.click()
    page.wait_for_timeout(100)
    
    # Should say "videos" again
    expect(content).to_contain_text("videos")

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
    expect(content).to_contain_text("Ready to export 10 videos")

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
    expect(content).to_contain_text("Ready to export 34 videos")

def test_export_id_fallback_logic(page: Page, server_url):
    """Test that the ID fallback logic works correctly."""
    page.goto(f"{server_url}?unlisted_youtube_export")
    page.locator("#open-export").click()
    
    modal = page.locator("#modal-export")
    content = modal.locator("#export-content")
    
    # Get URL with Videos preference (video_id > music_id)
    create_btn = modal.locator("footer a[role='button']")
    videos_url = create_btn.get_attribute("href")
    videos_ids = videos_url.split("video_ids=")[1].split(",")
    
    # Switch to Songs preference (music_id > video_id)
    songs_btn = content.get_by_role("button", name="Songs")
    songs_btn.click()
    page.wait_for_timeout(100)
    
    songs_url = create_btn.get_attribute("href")
    songs_ids = songs_url.split("video_ids=")[1].split(",")
    
    # The IDs should be different because priorities are different
    # Both should have the same number of songs (24)
    assert len(videos_ids) == 24
    assert len(songs_ids) == 24
    
    # At least some IDs should be different
    assert videos_ids != songs_ids, "Videos and Songs preferences should use different IDs"

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
    expect(content).to_contain_text("Ready to export 10 videos")
    
    # All songs should be available
    expect(content).to_contain_text("✓ All requested songs are available")
    
    # Should NOT show warning
    warning = content.get_by_text("⚠️")
    expect(warning).not_to_be_visible()

def test_export_song_not_available(page: Page, server_url):
    """Test that the modal shows warning when song IDs are missing."""
    # "It's Your Anniversary" by Freddie Gibbs has no YouTube IDs (only "other" media)
    # It ranks around #13 in default settings
    
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
    expect(content).to_contain_text("Ready to export 34 videos")
    
    # Should show warning
    expect(content).to_contain_text("⚠️ 1 songs missing IDs will be skipped")
    
    # Should show the specific song that's missing
    expect(content).to_contain_text("It's Your Anniversary")

def test_export_works_with_other_params(page: Page, server_url):
    """Test that export works alongside other URL parameters."""
    page.goto(f"{server_url}?unlisted_youtube_export&k_value=10&decay_mode=conviction")
    
    # Export link should still be visible
    export_link = page.locator("#open-export")
    expect(export_link).to_be_visible()
    
    # Modal should still work
    page.locator("#open-export").click()
    modal = page.locator("#modal-export")
    expect(modal).to_be_visible()

def test_export_modal_cancel_button(page: Page, server_url):
    """Test that Cancel button closes the modal."""
    page.goto(f"{server_url}?unlisted_youtube_export")
    page.locator("#open-export").click()
    
    modal = page.locator("#modal-export")
    expect(modal).to_be_visible()
    
    # Click Cancel
    cancel_btn = modal.locator("footer button", has_text="Cancel")
    cancel_btn.click()
    
    # Modal should be closed
    expect(modal).not_to_be_visible()

def test_export_modal_close_button(page: Page, server_url):
    """Test that Close button (X) closes the modal."""
    page.goto(f"{server_url}?unlisted_youtube_export")
    page.locator("#open-export").click()
    
    modal = page.locator("#modal-export")
    expect(modal).to_be_visible()
    
    # Click close button
    close_btn = modal.locator("header button[aria-label='Close']")
    close_btn.click()
    
    # Modal should be closed
    expect(modal).not_to_be_visible()
