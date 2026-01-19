"""
Tests for Listen on YouTube and Download Playlist features.
"""
from playwright.sync_api import Page, expect
import re


# =============================================================================
# LISTEN ON YOUTUBE MODAL TESTS
# =============================================================================

def test_youtube_modal_opens_without_feature_flag(page: Page, server_url):
    """Test that YouTube modal is always available (no feature flag needed)."""
    page.goto(server_url)

    # Desktop link should be visible
    youtube_link = page.locator("#open-youtube")
    expect(youtube_link).to_be_visible()
    expect(youtube_link).to_have_text("Listen on YouTube")


def test_youtube_modal_opens(page: Page, server_url):
    """Test that clicking Listen on YouTube opens the modal."""
    page.goto(server_url)

    page.locator("#open-youtube").click()

    modal = page.locator("#modal-youtube")
    expect(modal).to_be_visible()
    expect(modal.locator("h3")).to_have_text("Listen on YouTube")


def test_youtube_modal_default_state(page: Page, server_url):
    """Test the default state of the YouTube modal (count=50, preference=videos)."""
    page.goto(server_url)
    page.locator("#open-youtube").click()

    modal = page.locator("#modal-youtube")
    content = modal.locator("#youtube-content")

    # Check preference buttons - Music Videos should be selected by default
    videos_btn = content.get_by_role("button", name="Music Videos")
    audio_btn = content.get_by_role("button", name="Audio Only")

    # Videos should not have outline/secondary classes (is active)
    expect(videos_btn).not_to_have_class(re.compile("outline"))
    expect(videos_btn).not_to_have_class(re.compile("secondary"))

    # Audio should have outline secondary classes (not active)
    expect(audio_btn).to_have_class(re.compile("outline"))
    expect(audio_btn).to_have_class(re.compile("secondary"))

    # Check count buttons - Top 50 should be selected by default
    btn_10 = content.get_by_role("button", name="Top 10")
    btn_25 = content.get_by_role("button", name="Top 25")
    btn_50 = content.get_by_role("button", name="Top 50")

    expect(btn_10).to_have_class(re.compile("outline"))
    expect(btn_25).to_have_class(re.compile("outline"))
    expect(btn_50).not_to_have_class(re.compile("outline"))

    # Check that Media preference legend exists
    expect(content).to_contain_text("Media preference")


def test_youtube_preference_toggle(page: Page, server_url):
    """Test that preference toggle changes ID priority."""
    page.goto(server_url)
    page.locator("#open-youtube").click()

    modal = page.locator("#modal-youtube")
    content = modal.locator("#youtube-content")

    # Start with Music Videos (default)
    expect(content).to_contain_text("Music Videos")

    # Get initial URL (anchor with role="button")
    listen_btn = modal.locator("footer a[role='button']")
    initial_url = listen_btn.get_attribute("href")

    # Switch to Audio Only
    audio_btn = content.get_by_role("button", name="Audio Only")
    audio_btn.click()
    page.wait_for_timeout(100)

    # Should now say "Audio Only"
    expect(content).to_contain_text("Audio Only")

    # URL should be different (different IDs)
    new_url = listen_btn.get_attribute("href")
    assert initial_url != new_url, "Switching preference should change the video IDs"


def test_youtube_count_selection(page: Page, server_url):
    """Test that count selection updates the summary."""
    page.goto(server_url)
    page.locator("#open-youtube").click()

    modal = page.locator("#modal-youtube")
    content = modal.locator("#youtube-content")

    # Click Top 10
    btn_10 = content.get_by_role("button", name="Top 10")
    btn_10.click()
    page.wait_for_timeout(100)

    # Summary should show 10 songs
    expect(content).to_contain_text("10")

    # Click Top 25
    btn_25 = content.get_by_role("button", name="Top 25")
    btn_25.click()
    page.wait_for_timeout(100)

    # Summary should show 24 or 25 songs (depending on test data)
    expect(content).to_contain_text("Ready to play")


def test_youtube_missing_ids_warning(page: Page, server_url):
    """Test that missing IDs warning displays correctly with song details."""
    page.goto(server_url)
    page.locator("#open-youtube").click()

    modal = page.locator("#modal-youtube")
    content = modal.locator("#youtube-content")

    # Test data has one song without YouTube IDs: "Freddie Gibbs - It's Your Anniversary"
    # Default is Top 50, which should include this song

    # Should show warning icon and message
    expect(content).to_contain_text("⚠️")
    expect(content).to_contain_text("1 song missing YouTube IDs will be skipped")

    # Should list the specific song with artist and name
    expect(content).to_contain_text("Freddie Gibbs")
    expect(content).to_contain_text("It's Your Anniversary")


def test_youtube_url_format(page: Page, server_url):
    """Test that the YouTube URL is correctly formatted."""
    page.goto(server_url)
    page.locator("#open-youtube").click()

    modal = page.locator("#modal-youtube")
    listen_btn = modal.locator("footer a[role='button']")

    url = listen_btn.get_attribute("href")

    # Should be YouTube watch_videos URL
    assert url.startswith("https://www.youtube.com/watch_videos?video_ids=")

    # Should have comma-separated IDs
    video_ids = url.split("video_ids=")[1].split(",")
    assert len(video_ids) > 0


def test_youtube_modal_close_button(page: Page, server_url):
    """Test that Close button closes the modal."""
    page.goto(server_url)
    page.locator("#open-youtube").click()

    modal = page.locator("#modal-youtube")
    expect(modal).to_be_visible()

    # Click Close button
    close_btn = modal.locator("footer button", has_text="Close")
    close_btn.click()

    expect(modal).not_to_be_visible()


# =============================================================================
# DOWNLOAD PLAYLIST MODAL TESTS
# =============================================================================

def test_download_modal_opens(page: Page, server_url):
    """Test that clicking Download Playlist opens the modal."""
    page.goto(server_url)

    page.locator("#open-download").click()

    modal = page.locator("#modal-download")
    expect(modal).to_be_visible()
    expect(modal.locator("h3")).to_have_text("Download Playlist")


def test_download_modal_default_state(page: Page, server_url):
    """Test the default state of the Download modal (count=100)."""
    page.goto(server_url)
    page.locator("#open-download").click()

    modal = page.locator("#modal-download")
    content = modal.locator("#download-content")

    # Check count buttons - Top 100 should be selected by default
    btn_25 = content.get_by_role("button", name="Top 25")
    btn_100 = content.get_by_role("button", name="Top 100")
    btn_200 = content.get_by_role("button", name="Top 200")

    expect(btn_25).to_have_class(re.compile("outline"))
    expect(btn_100).not_to_have_class(re.compile("outline"))
    expect(btn_200).to_have_class(re.compile("outline"))

    # Should show download CSV button (not "Download Again")
    footer = modal.locator("footer")
    expect(footer.get_by_role("button", name="Download CSV")).to_be_visible()


def test_download_count_selection(page: Page, server_url):
    """Test that count selection updates the summary."""
    page.goto(server_url)
    page.locator("#open-download").click()

    modal = page.locator("#modal-download")
    content = modal.locator("#download-content")

    # Click Top 25
    btn_25 = content.get_by_role("button", name="Top 25")
    btn_25.click()
    page.wait_for_timeout(100)

    # Summary should show 25 songs
    expect(content).to_contain_text("25")
    expect(content).to_contain_text("songs as CSV")


def test_download_isrc_warning(page: Page, server_url):
    """Test that ISRC warning is shown for songs with : in ID, listing song details."""
    page.goto(server_url)
    page.locator("#open-download").click()

    modal = page.locator("#modal-download")
    content = modal.locator("#download-content")

    # Test data has one song without ISRC (has ":" in ID): "Freddie Gibbs - It's Your Anniversary"
    # Default is Top 100, which should include this song

    # Should show warning icon and message
    expect(content).to_contain_text("⚠️")
    expect(content).to_contain_text("1 song missing ISRC codes")

    # Should list the specific song with artist and name
    expect(content).to_contain_text("Freddie Gibbs")
    expect(content).to_contain_text("It's Your Anniversary")


def test_download_button_triggers_download(page: Page, server_url):
    """Test that Download CSV button triggers a download."""
    page.goto(server_url)
    page.locator("#open-download").click()

    modal = page.locator("#modal-download")

    # Start waiting for download before clicking
    with page.expect_download() as download_info:
        # Click Download CSV button
        modal.get_by_role("button", name="Download CSV").click()

    download = download_info.value

    # Check filename
    assert download.suggested_filename.startswith("consensus-best-songs-2025-top-")
    assert download.suggested_filename.endswith(".csv")


def test_download_csv_content(page: Page, server_url):
    """Test that CSV content has correct headers and format."""
    page.goto(server_url)
    page.locator("#open-download").click()

    modal = page.locator("#modal-download")
    content = modal.locator("#download-content")

    # Select Top 25 for smaller download
    content.get_by_role("button", name="Top 25").click()
    page.wait_for_timeout(100)

    # Start waiting for download before clicking
    with page.expect_download() as download_info:
        modal.get_by_role("button", name="Download CSV").click()

    download = download_info.value

    # Read the downloaded file
    path = download.path()
    with open(path, 'r') as f:
        csv_content = f.read()

    # Check headers
    lines = csv_content.strip().split('\n')
    headers = lines[0]
    assert "title" in headers
    assert "artist" in headers
    assert "isrc" in headers
    assert "spotify_id" in headers
    assert "youtube_id" in headers
    assert "youtube_music_id" in headers
    assert "apple_music_url" in headers

    # Should have more than just headers
    assert len(lines) > 1


def test_download_next_steps_after_download(page: Page, server_url):
    """Test that Next Steps UI appears after download."""
    page.goto(server_url)
    page.locator("#open-download").click()

    modal = page.locator("#modal-download")

    # Download
    with page.expect_download():
        modal.get_by_role("button", name="Download CSV").click()

    page.wait_for_timeout(100)

    # Check for Next Steps
    footer = modal.locator("footer")
    expect(footer).to_contain_text("Next Steps")
    # Links have role="button" due to Pico CSS styling
    expect(footer.locator("a", has_text="Import via Soundiiz")).to_be_visible()
    expect(footer.locator("a", has_text="Import via TuneMyMusic")).to_be_visible()
    expect(footer.get_by_role("button", name="Download Again")).to_be_visible()


def test_download_again_button(page: Page, server_url):
    """Test that Download Again button triggers another download."""
    page.goto(server_url)
    page.locator("#open-download").click()

    modal = page.locator("#modal-download")

    # First download
    with page.expect_download():
        modal.get_by_role("button", name="Download CSV").click()

    page.wait_for_timeout(100)

    # Click Download Again
    with page.expect_download() as download_info:
        modal.get_by_role("button", name="Download Again").click()

    download = download_info.value
    assert download.suggested_filename.endswith(".csv")


def test_download_modal_reset_on_reopen(page: Page, server_url):
    """Test that download state resets when modal is reopened."""
    page.goto(server_url)

    # Open and download
    page.locator("#open-download").click()
    modal = page.locator("#modal-download")

    with page.expect_download():
        modal.get_by_role("button", name="Download CSV").click()

    page.wait_for_timeout(100)

    # Should see "Download Again"
    expect(modal.get_by_role("button", name="Download Again")).to_be_visible()

    # Close modal
    modal.locator("footer button", has_text="Close").click()
    expect(modal).not_to_be_visible()

    # Reopen modal
    page.locator("#open-download").click()
    expect(modal).to_be_visible()

    # Should see "Download CSV" again (not "Download Again")
    expect(modal.get_by_role("button", name="Download CSV")).to_be_visible()


# =============================================================================
# RESPONSIVE HEADER TESTS
# =============================================================================

def test_desktop_header_shows_all_links(page: Page, server_url):
    """Test that desktop viewport shows all links inline."""
    # Set desktop viewport
    page.set_viewport_size({"width": 1200, "height": 800})
    page.goto(server_url)

    # Desktop nav should be visible
    nav_desktop = page.locator(".nav-desktop")
    expect(nav_desktop).to_be_visible()

    # All links should be visible
    expect(nav_desktop.locator("#open-settings")).to_be_visible()
    expect(nav_desktop.locator("#open-youtube")).to_be_visible()
    expect(nav_desktop.locator("#open-download")).to_be_visible()
    expect(nav_desktop.locator("#open-about")).to_be_visible()

    # Hamburger should be hidden
    hamburger = page.locator("#hamburger-btn")
    expect(hamburger).not_to_be_visible()


def test_mobile_header_shows_tune_and_hamburger(page: Page, server_url):
    """Test that mobile viewport shows Tune button and hamburger, hides other links."""
    # Set mobile viewport
    page.set_viewport_size({"width": 375, "height": 667})
    page.goto(server_url)

    # Desktop nav should be hidden
    nav_desktop = page.locator(".nav-desktop")
    expect(nav_desktop).not_to_be_visible()

    # Mobile nav should be visible
    nav_mobile = page.locator(".nav-mobile")
    expect(nav_mobile).to_be_visible()

    # Tune button should be visible
    tune_mobile = page.locator("#open-settings-mobile")
    expect(tune_mobile).to_be_visible()

    # Hamburger should be visible
    hamburger = page.locator("#hamburger-btn")
    expect(hamburger).to_be_visible()


def test_hamburger_toggle_opens_menu(page: Page, server_url):
    """Test that hamburger button opens the mobile menu."""
    page.set_viewport_size({"width": 375, "height": 667})
    page.goto(server_url)

    mobile_menu = page.locator("#mobile-menu")
    hamburger = page.locator("#hamburger-btn")

    # Menu should be hidden initially
    expect(mobile_menu).to_be_hidden()
    expect(hamburger).to_have_attribute("aria-expanded", "false")

    # Click hamburger
    hamburger.click()

    # Menu should be visible
    expect(mobile_menu).to_be_visible()
    expect(hamburger).to_have_attribute("aria-expanded", "true")


def test_hamburger_toggle_closes_menu(page: Page, server_url):
    """Test that clicking hamburger again closes the menu."""
    page.set_viewport_size({"width": 375, "height": 667})
    page.goto(server_url)

    mobile_menu = page.locator("#mobile-menu")
    hamburger = page.locator("#hamburger-btn")

    # Open menu
    hamburger.click()
    expect(mobile_menu).to_be_visible()

    # Close menu
    hamburger.click()
    expect(mobile_menu).to_be_hidden()


def test_mobile_menu_items_open_modals(page: Page, server_url):
    """Test that mobile menu items open the correct modals."""
    page.set_viewport_size({"width": 375, "height": 667})
    page.goto(server_url)

    hamburger = page.locator("#hamburger-btn")
    mobile_menu = page.locator("#mobile-menu")

    # Test YouTube link
    hamburger.click()
    mobile_menu.locator("#open-youtube-mobile").click()
    expect(page.locator("#modal-youtube")).to_be_visible()
    expect(mobile_menu).to_be_hidden()  # Menu should close
    page.locator("#modal-youtube footer button", has_text="Close").click()

    # Test Download link
    hamburger.click()
    mobile_menu.locator("#open-download-mobile").click()
    expect(page.locator("#modal-download")).to_be_visible()
    expect(mobile_menu).to_be_hidden()
    page.locator("#modal-download footer button", has_text="Close").click()

    # Test About link
    hamburger.click()
    mobile_menu.locator("#open-about-mobile").click()
    expect(page.locator("#modal-about")).to_be_visible()
    expect(mobile_menu).to_be_hidden()


def test_mobile_menu_closes_on_outside_click(page: Page, server_url):
    """Test that clicking outside the menu closes it."""
    page.set_viewport_size({"width": 375, "height": 667})
    page.goto(server_url)

    hamburger = page.locator("#hamburger-btn")
    mobile_menu = page.locator("#mobile-menu")

    # Open menu
    hamburger.click()
    expect(mobile_menu).to_be_visible()

    # Click outside (on the main content area)
    page.locator("#song-list").click(force=True)

    # Menu should close
    expect(mobile_menu).to_be_hidden()


def test_tune_ranking_always_visible(page: Page, server_url):
    """Test that Tune Ranking button is always visible on both viewports."""
    # Desktop
    page.set_viewport_size({"width": 1200, "height": 800})
    page.goto(server_url)

    desktop_tune = page.locator("#open-settings")
    expect(desktop_tune).to_be_visible()
    expect(desktop_tune).to_contain_text("Tune Ranking")

    # Mobile
    page.set_viewport_size({"width": 375, "height": 667})
    page.goto(server_url)

    mobile_tune = page.locator("#open-settings-mobile")
    expect(mobile_tune).to_be_visible()
    expect(mobile_tune).to_contain_text("Tune")


def test_tune_ranking_opens_settings_modal(page: Page, server_url):
    """Test that Tune Ranking button opens the Settings modal."""
    page.goto(server_url)

    page.locator("#open-settings").click()

    modal = page.locator("#modal-settings")
    expect(modal).to_be_visible()
    expect(modal.locator("h3")).to_have_text("Tune Ranking")
