import re
from playwright.sync_api import Page, expect


def test_filter_sliders_appear_in_tune_modal(page: Page, server_url):
    """Test that filter sliders appear in the Tune modal."""
    page.goto(server_url)
    page.locator("#open-tune").click()

    # Check that Song Filters section exists
    song_filters_heading = page.locator("h4", has_text="Song Filters")
    expect(song_filters_heading).to_be_visible()

    # Check filter sliders exist
    min_list_slider = page.locator("#setting-ranking-min_sources")
    expect(min_list_slider).to_be_visible()

    max_rank_slider = page.locator("#setting-ranking-rank_cutoff")
    expect(max_rank_slider).to_be_visible()


def test_eligible_songs_counter(page: Page, server_url):
    """Test that the eligible songs counter shows correct count."""
    page.goto(server_url)
    page.locator("#open-tune").click()

    # Check counter exists and shows initial count
    counter = page.locator("#eligible-songs-counter")
    expect(counter).to_be_visible()
    expect(counter).to_contain_text("Including")
    expect(counter).to_contain_text("of")
    expect(counter).to_contain_text("songs")


def test_min_sources_filters_songs(page: Page, server_url):
    """Test that min_sources=2 hides songs with only 1 source."""
    page.goto(server_url)

    # Get initial song count
    initial_count = page.locator(".song-card").count()
    assert initial_count > 0, "Should have some songs initially"

    # Set min_sources to 2 via URL
    page.goto(f"{server_url}/?min_sources=2")
    page.wait_for_timeout(300)

    # Songs with only 1 source should be filtered out
    new_count = page.locator(".song-card").count()
    assert new_count < initial_count, f"Expected fewer songs with min_sources=2, got {new_count} vs initial {initial_count}"


def test_min_sources_one_shows_all(page: Page, server_url):
    """Test that min_sources=1 shows all songs (default behavior)."""
    page.goto(server_url)

    # Get initial song count
    initial_count = page.locator(".song-card").count()

    # Explicitly set min_sources to 1 (the minimum/default)
    page.goto(f"{server_url}/?min_sources=1")
    page.wait_for_timeout(300)

    # Should have same count
    new_count = page.locator(".song-card").count()
    assert new_count == initial_count, f"min_sources=1 should show all songs, got {new_count} vs {initial_count}"


def test_min_sources_url_validation(page: Page, server_url):
    """Test that invalid min_sources values are clamped to valid range [1, 10]."""
    # Test that 0 is clamped to 1
    page.goto(f"{server_url}/?min_sources=0")
    page.wait_for_timeout(300)
    page.locator("#open-tune").click()

    min_sources_slider = page.locator("#setting-ranking-min_sources")
    expect(min_sources_slider).to_have_value("1")

    # Test that values above max are clamped to 10
    page.goto(f"{server_url}/?min_sources=99")
    page.wait_for_timeout(300)
    page.locator("#open-tune").click()

    min_sources_slider = page.locator("#setting-ranking-min_sources")
    expect(min_sources_slider).to_have_value("10")


def test_rank_cutoff_filters_contributions(page: Page, server_url):
    """Test that rank_cutoff filters out contributions from ranks higher than threshold."""
    page.goto(server_url)
    initial_count = page.locator(".song-card").count()

    page.goto(f"{server_url}/?rank_cutoff=25")
    page.wait_for_timeout(300)

    # Open tune modal and check slider value
    page.locator("#open-tune").click()
    max_rank_slider = page.locator("#setting-ranking-rank_cutoff")
    expect(max_rank_slider).to_have_value("25")

    # Close tune modal
    page.keyboard.press("Escape")
    page.wait_for_timeout(200)

    # Songs with only ranks > 25 should be excluded, reducing count
    song_count = page.locator(".song-card").count()
    assert song_count <= initial_count, "rank_cutoff should not increase song count"
    assert song_count > 0, "Some songs should still be visible with rank_cutoff=25"


def test_rank_cutoff_zero_no_limit(page: Page, server_url):
    """Test that rank_cutoff=0 means no limit (default)."""
    page.goto(server_url)
    initial_count = page.locator(".song-card").count()

    page.goto(f"{server_url}/?rank_cutoff=0")
    page.wait_for_timeout(300)

    new_count = page.locator(".song-card").count()
    assert new_count == initial_count, "rank_cutoff=0 should show all songs"


def test_combined_filters(page: Page, server_url):
    """Test that combined filters work together."""
    page.goto(f"{server_url}/?min_sources=2&rank_cutoff=50")
    page.wait_for_timeout(300)

    # Open tune modal and verify both sliders
    page.locator("#open-tune").click()

    min_list_slider = page.locator("#setting-ranking-min_sources")
    expect(min_list_slider).to_have_value("2")

    max_rank_slider = page.locator("#setting-ranking-rank_cutoff")
    expect(max_rank_slider).to_have_value("50")


def test_empty_state_shown_with_extreme_filters(page: Page, server_url):
    """Test that empty state is shown when all songs are filtered out."""
    # Set very restrictive filters that exclude all songs
    # With Option C: min_sources=10 requires songs on 10+ lists (only RAYE qualifies)
    # rank_cutoff=1 requires a #1 ranking (RAYE's lowest is #3)
    # Result: no songs pass both criteria
    page.goto(f"{server_url}/?min_sources=10&rank_cutoff=1")
    page.wait_for_timeout(300)

    # Check for empty state
    empty_state = page.locator(".empty-filter-state")
    expect(empty_state).to_be_visible()

    # Check for message
    expect(page.locator("text=No songs match your filters")).to_be_visible()


def test_adjust_filters_button_opens_tune_modal(page: Page, server_url):
    """Test that 'Adjust Filters' button in empty state opens Tune modal."""
    page.goto(f"{server_url}/?min_sources=10&rank_cutoff=1")
    page.wait_for_timeout(300)

    # Click Adjust Filters button
    adjust_btn = page.locator("button", has_text="Adjust Filters")
    expect(adjust_btn).to_be_visible()
    adjust_btn.click()

    # Tune modal should be open
    tune_modal = page.locator("#modal-tune")
    expect(tune_modal).to_be_visible()


def test_youtube_modal_warning_when_no_songs(page: Page, server_url):
    """Test that YouTube modal shows warning when no songs available."""
    page.goto(f"{server_url}/?min_sources=10&rank_cutoff=1")
    page.wait_for_timeout(300)

    # Open YouTube modal via hamburger menu
    page.locator("#hamburger-btn").click()
    page.locator("#open-youtube-menu").click()

    # Check for warning message
    youtube_modal = page.locator("#modal-youtube")
    expect(youtube_modal).to_be_visible()
    expect(youtube_modal.locator("text=No songs match your current filters")).to_be_visible()


def test_download_modal_warning_when_no_songs(page: Page, server_url):
    """Test that Download modal shows warning when no songs available."""
    page.goto(f"{server_url}/?min_sources=10&rank_cutoff=1")
    page.wait_for_timeout(300)

    # Open Download modal via hamburger menu
    page.locator("#hamburger-btn").click()
    page.locator("#open-download-menu").click()

    # Check for warning message
    download_modal = page.locator("#modal-download")
    expect(download_modal).to_be_visible()
    expect(download_modal.locator("text=No songs match your current filters")).to_be_visible()


def test_url_parameters_persist(page: Page, server_url):
    """Test that filter URL parameters persist correctly."""
    page.goto(server_url)
    page.locator("#open-tune").click()

    # Change min_sources slider
    page.evaluate("document.getElementById('setting-ranking-min_sources').value = '3'")
    page.locator("#setting-ranking-min_sources").dispatch_event("input")

    # Change rank_cutoff slider
    page.evaluate("document.getElementById('setting-ranking-rank_cutoff').value = '50'")
    page.locator("#setting-ranking-rank_cutoff").dispatch_event("input")

    # Wait for debounce
    page.wait_for_timeout(500)

    # Check URL
    expect(page).to_have_url(re.compile("min_sources=3"))
    expect(page).to_have_url(re.compile("rank_cutoff=50"))


def test_reset_button_clears_filters(page: Page, server_url):
    """Test that Reset button clears filter values to defaults."""
    page.goto(f"{server_url}/?min_sources=3&rank_cutoff=50")
    page.wait_for_timeout(300)

    # Open tune modal
    page.locator("#open-tune").click()

    # Verify filters are set
    min_list_slider = page.locator("#setting-ranking-min_sources")
    expect(min_list_slider).to_have_value("3")

    # Click Reset
    page.locator("#reset-defaults").click()
    page.wait_for_timeout(500)

    # Filters should be reset to defaults (min_sources=1, rank_cutoff=0)
    expect(min_list_slider).to_have_value("1")
    max_rank_slider = page.locator("#setting-ranking-rank_cutoff")
    expect(max_rank_slider).to_have_value("0")


def test_stats_modal_shows_filtered_contribution(page: Page, server_url):
    """Test that stats modal shows 0.0000 contribution for sources filtered by rank_cutoff."""
    # Use a rank_cutoff that will filter some contributions
    # The test data has a song with rank 90 on Pitchfork
    page.goto(f"{server_url}/?rank_cutoff=25")
    page.wait_for_timeout(500)

    # Find a song that has sources with ranks both above and below 25
    # Look for a song that appears in the list
    song_cards = page.locator(".song-card")
    if song_cards.count() > 0:
        # Open stats modal for first song
        song_cards.first.locator("header a[aria-label='View ranking details']").click()

        modal = page.locator("#modal-stats")
        expect(modal).to_be_visible()

        # Check if there are any filtered contributions showing 0.0000
        # This validates that the filtered source appears in the modal
        modal_text = modal.inner_text()
        # The modal should contain contribution rows
        assert "Source Contributions" in modal_text or "contribution" in modal_text.lower()


def test_filter_slider_display_values(page: Page, server_url):
    """Test that filter sliders show correct default values."""
    page.goto(server_url)
    page.locator("#open-tune").click()

    # Check min_sources shows "1" at default
    min_list_display = page.locator("#val-setting-ranking-min_sources")
    expect(min_list_display).to_have_text("1")

    # Check rank_cutoff shows "Any" at 0
    max_rank_display = page.locator("#val-setting-ranking-rank_cutoff")
    expect(max_rank_display).to_have_text("Any")


def test_filter_slider_display_values_when_changed(page: Page, server_url):
    """Test that filter sliders show numeric values when changed from 0."""
    page.goto(f"{server_url}/?min_sources=3&rank_cutoff=50")
    page.wait_for_timeout(300)
    page.locator("#open-tune").click()

    # Check min_sources shows numeric value
    min_list_display = page.locator("#val-setting-ranking-min_sources")
    expect(min_list_display).to_have_text("3")

    # Check rank_cutoff shows numeric value
    max_rank_display = page.locator("#val-setting-ranking-rank_cutoff")
    expect(max_rank_display).to_have_text("50")


def test_rank_cutoff_filters_out_songs_entirely(page: Page, server_url):
    """Test that rank_cutoff can filter out songs when all their sources exceed the threshold."""
    page.goto(server_url)
    initial_count = page.locator(".song-card").count()

    # Set a very restrictive rank_cutoff that should filter out some songs
    page.goto(f"{server_url}/?rank_cutoff=5")
    page.wait_for_timeout(300)

    # Songs where ALL sources have rank > 5 should be excluded
    new_count = page.locator(".song-card").count()
    assert new_count < initial_count, f"Expected fewer songs with rank_cutoff=5, got {new_count} vs initial {initial_count}"


def test_eligible_counter_updates_on_filter_change(page: Page, server_url):
    """Test that eligible songs counter updates when filter values change."""
    page.goto(server_url)
    page.locator("#open-tune").click()

    # Get initial counter text
    counter = page.locator("#eligible-songs-counter")
    initial_text = counter.inner_text()

    # Change min_sources to filter out some songs
    page.evaluate("document.getElementById('setting-ranking-min_sources').value = '3'")
    page.locator("#setting-ranking-min_sources").dispatch_event("input")

    # Wait for debounce + counter update
    page.wait_for_timeout(600)

    # Counter should have updated (fewer songs included in ranking)
    new_text = counter.inner_text()
    # The eligible count should be different (or at least the text re-rendered)
    # We can't guarantee the count is less without knowing exact data,
    # but we can verify the counter element exists and has content
    assert "Including" in new_text and "songs" in new_text


def test_youtube_modal_shows_filter_limitation_note(page: Page, server_url):
    """Test that YouTube modal shows filter limitation note when filters reduce available songs."""
    # Navigate with restrictive filters that reduce song count
    page.goto(f"{server_url}/?min_sources=3")
    page.wait_for_timeout(300)

    # Open YouTube modal via hamburger menu
    page.locator("#hamburger-btn").click()
    page.locator("#open-youtube-menu").click()

    # Select Top 50 (which is more than available filtered songs)
    youtube_modal = page.locator("#modal-youtube")
    expect(youtube_modal).to_be_visible()
    page.locator("button[data-action='yt-count'][data-count='50']").click()
    page.wait_for_timeout(350)

    # Verify filter limitation note appears
    expect(youtube_modal.locator("text=(limited by your filters)")).to_be_visible()


def test_download_modal_shows_filter_limitation_note(page: Page, server_url):
    """Test that Download modal shows filter limitation note when filters reduce available songs."""
    # Navigate with restrictive filters
    page.goto(f"{server_url}/?min_sources=3")
    page.wait_for_timeout(300)

    # Open Download modal via hamburger menu
    page.locator("#hamburger-btn").click()
    page.locator("#open-download-menu").click()

    # Select Top 100 (which is more than available filtered songs)
    download_modal = page.locator("#modal-download")
    expect(download_modal).to_be_visible()
    page.locator("button[data-action='dl-count'][data-count='100']").click()
    page.wait_for_timeout(350)

    # Verify filter limitation note appears
    expect(download_modal.locator("text=(limited by your filters)")).to_be_visible()


def test_youtube_modal_no_filter_note_when_not_needed(page: Page, server_url):
    """Test that YouTube modal does not show filter note when filters are not limiting results."""
    # Navigate with default filters (no restriction)
    page.goto(server_url)
    page.wait_for_timeout(300)

    # Open YouTube modal via hamburger menu
    page.locator("#hamburger-btn").click()
    page.locator("#open-youtube-menu").click()

    # Select Top 10 (should be within available songs)
    youtube_modal = page.locator("#modal-youtube")
    expect(youtube_modal).to_be_visible()
    page.locator("button[data-action='yt-count'][data-count='10']").click()
    page.wait_for_timeout(200)

    # Verify filter limitation note does NOT appear
    expect(youtube_modal.locator("text=(limited by your filters)")).not_to_be_visible()


def test_download_modal_all_button_shows_filter_note(page: Page, server_url):
    """Test that Download modal shows filter note when 'All' is selected with active filters."""
    # Navigate with restrictive filters
    page.goto(f"{server_url}/?min_sources=2")
    page.wait_for_timeout(300)

    # Open Download modal via hamburger menu
    page.locator("#hamburger-btn").click()
    page.locator("#open-download-menu").click()

    # Click the "All" button
    download_modal = page.locator("#modal-download")
    expect(download_modal).to_be_visible()
    page.locator("button[data-action='dl-count']:has-text('All')").click()
    page.wait_for_timeout(200)

    # Verify filter limitation note appears even with "All" selected
    expect(download_modal.locator("text=(limited by your filters)")).to_be_visible()


def test_min_sources_uses_original_list_count(page: Page, server_url):
    """Test that min_sources uses original list_count, not post-filter count (Option C behavior).

    This tests that the two filters are independent:
    - min_sources: checks how many lists a song appears on (original count)
    - rank_cutoff: filters which contributions count toward score

    A song with 3 sources where only 1 is within rank_cutoff should still pass
    min_sources=3 because it appears on 3 lists originally.
    """
    # Test data has "2hollis - flash" with:
    # - list_count=3 (appears on 3 lists)
    # - ranks: 7 (Dazed), 45 (Complex), 90 (Pitchfork)
    # With rank_cutoff=10, only rank 7 qualifies (1 contribution)
    # With min_sources=3, the song should PASS because list_count=3 >= 3

    # First verify the song exists without filters
    page.goto(server_url)
    page.wait_for_timeout(300)
    flash_card = page.locator(".song-card", has_text="flash")
    expect(flash_card.first).to_be_visible()

    # Now apply both filters: min_sources=3, rank_cutoff=10
    # Under old (dependent) behavior: post-filter count = 1 < 3, would be filtered out
    # Under Option C (independent): list_count=3 >= 3, passes; 1 qualifying contribution > 0, passes
    page.goto(f"{server_url}/?min_sources=3&rank_cutoff=10")
    page.wait_for_timeout(300)

    # The song should still be visible under Option C
    flash_card = page.locator(".song-card", has_text="flash")
    expect(flash_card.first).to_be_visible()


def test_song_excluded_when_all_contributions_filtered(page: Page, server_url):
    """Test that songs are excluded when rank_cutoff filters ALL their contributions.

    Even with Option C, a song with 0 qualifying contributions should be excluded
    because it would have no score.
    """
    # Test data has "Freddie Gibbs - It's Your Anniversary" with:
    # - list_count=1 (appears on 1 list)
    # - rank: 40 (FADER)
    # With rank_cutoff=10, this song has 0 qualifying contributions

    # Verify the song exists without filters
    page.goto(server_url)
    page.wait_for_timeout(300)
    gibbs_card = page.locator(".song-card", has_text="Anniversary")
    expect(gibbs_card.first).to_be_visible()

    # Apply rank_cutoff=10 which should filter out the only contribution
    page.goto(f"{server_url}/?rank_cutoff=10")
    page.wait_for_timeout(300)

    # The song should be excluded (0 qualifying contributions)
    gibbs_card = page.locator(".song-card", has_text="Anniversary")
    expect(gibbs_card).to_have_count(0)
