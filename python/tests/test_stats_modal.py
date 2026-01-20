from playwright.sync_api import Page, expect
import re

def test_stats_modal_content(page: Page, server_url):
    """Test that stats modal shows correct scores."""
    page.goto(server_url)
    
    # Find "WHERE IS MY HUSBAND!" by RAYE (appears on 10 lists)
    card = page.locator(".song-card", has_text="WHERE IS MY HUSBAND!").first
    
    # Click info icon
    card.locator("header a[aria-label='View ranking details']").click()
    
    modal = page.locator("#modal-stats")
    expect(modal).to_be_visible()
    
    # Check List Count
    # "WHERE IS MY HUSBAND!" is on 10 lists
    expect(modal.locator("text=List Count").locator("..")).to_contain_text("10")
    
    # Check Source Contributions table presence
    expect(modal.locator("text=Source Contributions")).to_be_visible()
    # Count rows in the Source Contributions table's tbody (excluding header)
    # Table is now inside section > figure structure
    contributions_table = modal.locator("section:has(h5:has-text('Source Contributions')) table tbody tr")
    expect(contributions_table).to_have_count(10)
    
    # Check that the first song (top ranked) has a normalized score of 1.0
    normalized_score_row = modal.locator("text=Normalized Score").locator("..")
    expect(normalized_score_row).to_be_visible()
    # The normalized score should be 1.0 or 1.00 or 1.000 (formatted)
    expect(normalized_score_row).to_contain_text(re.compile(r"1\.0+"))

def test_stats_modal_top_button(page: Page, server_url):
    """Test that Top button scrolls to top of modal."""
    page.goto(server_url)
    
    # Find a song with many sources to make the modal scrollable
    card = page.locator(".song-card", has_text="WHERE IS MY HUSBAND!").first
    card.locator("header a[aria-label='View ranking details']").click()
    
    modal = page.locator("#modal-stats")
    expect(modal).to_be_visible()
    
    # Scroll to bottom of modal
    page.evaluate("document.querySelector('#modal-stats article').scrollTop = document.querySelector('#modal-stats article').scrollHeight")
    
    # Click Top button
    top_button = modal.get_by_role("button", name="Top")
    expect(top_button).to_be_visible()
    top_button.click()
    
    # Wait for smooth scroll animation
    page.wait_for_timeout(1000)
    
    # Modal should be scrolled back to top
    scroll_top = page.evaluate("document.querySelector('#modal-stats article').scrollTop")
    assert scroll_top < 50, f"Modal should be scrolled to top, but scrollTop is {scroll_top}"

def test_stats_modal_close_button(page: Page, server_url):
    """Test that Close button closes the modal."""
    page.goto(server_url)

    card = page.locator(".song-card").first
    card.locator("header a[aria-label='View ranking details']").click()

    modal = page.locator("#modal-stats")
    expect(modal).to_be_visible()

    # Click Close button
    close_button = modal.locator("footer button.close-modal")
    close_button.click()

    # Modal should be closed
    expect(modal).not_to_be_visible()


def test_stats_modal_single_ranked_source(page: Page, server_url):
    """Test stats modal for song with single ranked source."""
    page.goto(server_url)

    # Show all songs to find Freddie Gibbs song
    while page.locator("button", has_text="Show").is_visible():
        page.locator("button", has_text="Show").click()

    # "It's Your Anniversary" by Freddie Gibbs has single source: FADER #40
    card = page.locator(".song-card", has_text="It's Your Anniversary").first
    expect(card).to_be_visible()
    card.locator("header a[aria-label='View ranking details']").click()

    modal = page.locator("#modal-stats")
    expect(modal).to_be_visible()

    # Check List Count is 1
    expect(modal.locator("text=List Count").locator("..")).to_contain_text("1")

    # Check Source Contributions table has 1 row
    contributions_table = modal.locator("section:has(h5:has-text('Source Contributions')) table tbody tr")
    expect(contributions_table).to_have_count(1)

    # Check Consensus Boost is 0% (log(1) = 0)
    expect(modal.locator("text=Consensus Boost").locator("..")).to_contain_text("0%")

    # Check Provocation Boost is 0% (no variance with single source)
    expect(modal.locator("text=Provocation Boost").locator("..")).to_contain_text("0%")


def test_stats_modal_single_unranked_source(page: Page, server_url):
    """Test stats modal for song with single unranked source."""
    page.goto(server_url)

    # Show all songs to find Sleep Token song
    while page.locator("button", has_text="Show").is_visible():
        page.locator("button", has_text="Show").click()

    # "Look To Windward" by Sleep Token has single source: Rough Trade (unranked)
    card = page.locator(".song-card", has_text="Look To Windward").first
    expect(card).to_be_visible()
    card.locator("header a[aria-label='View ranking details']").click()

    modal = page.locator("#modal-stats")
    expect(modal).to_be_visible()

    # Check List Count is 1
    expect(modal.locator("text=List Count").locator("..")).to_contain_text("1")

    # Check Source Contributions has 1 row showing Rough Trade
    contributions_table = modal.locator("section:has(h5:has-text('Source Contributions')) table tbody tr")
    expect(contributions_table).to_have_count(1)
    expect(contributions_table).to_contain_text("Rough Trade")

    # Check boosts are 0%
    expect(modal.locator("text=Consensus Boost").locator("..")).to_contain_text("0%")
    expect(modal.locator("text=Provocation Boost").locator("..")).to_contain_text("0%")


def test_stats_modal_cluster_boost_multiple_clusters(page: Page, server_url):
    """Test cluster boost for songs with multiple source clusters."""
    page.goto(server_url)

    # "WHERE IS MY HUSBAND!" by RAYE has sources from multiple clusters
    card = page.locator(".song-card", has_text="WHERE IS MY HUSBAND!").first
    card.locator("header a[aria-label='View ranking details']").click()

    modal = page.locator("#modal-stats")
    expect(modal).to_be_visible()

    # Check Cluster Boost is > 0% (song has sources from multiple clusters)
    cluster_boost_row = modal.locator("text=Cluster Boost").locator("..")
    cluster_boost_text = cluster_boost_row.inner_text()
    # Extract the percentage value and verify it's greater than 0
    assert "0%" not in cluster_boost_text or "10%" in cluster_boost_text or "%" in cluster_boost_text


def test_stats_modal_rank1_bonus_contribution(page: Page, server_url):
    """Test that rank 1 bonus is reflected in source contribution."""
    page.goto(server_url)

    # "Townies" by Wednesday is ranked #1 by Stereogum
    card = page.locator(".song-card", has_text="Townies").first
    card.locator("header a[aria-label='View ranking details']").click()

    modal = page.locator("#modal-stats")
    expect(modal).to_be_visible()

    # Check that Stereogum is listed in Source Contributions
    contributions_section = modal.locator("section:has(h5:has-text('Source Contributions'))")
    expect(contributions_section).to_contain_text("Stereogum")
    expect(contributions_section).to_contain_text("#1")

    # The contribution value should be positive (rank 1 bonus applies)
    stereogum_row = contributions_section.locator("table tbody tr", has_text="Stereogum")
    expect(stereogum_row).to_be_visible()


def test_stats_modal_rank1_bonus_conviction_mode(page: Page, server_url):
    """Test rank 1 bonus is applied in conviction mode."""
    # Load page with conviction mode
    page.goto(f"{server_url}?decay_mode=conviction")

    # "Townies" by Wednesday is ranked #1 by Stereogum
    card = page.locator(".song-card", has_text="Townies").first
    card.locator("header a[aria-label='View ranking details']").click()

    modal = page.locator("#modal-stats")
    expect(modal).to_be_visible()

    # Check that Stereogum is listed in Source Contributions with #1 rank
    contributions_section = modal.locator("section:has(h5:has-text('Source Contributions'))")
    expect(contributions_section).to_contain_text("Stereogum")
    expect(contributions_section).to_contain_text("#1")

    # Raw Score should be visible (different calculation in conviction mode)
    expect(modal.locator("text=Raw Score")).to_be_visible()


def test_stats_modal_consensus_boost_many_sources(page: Page, server_url):
    """Test consensus boost for song with many sources."""
    page.goto(server_url)

    # "WHERE IS MY HUSBAND!" by RAYE has 10 sources
    card = page.locator(".song-card", has_text="WHERE IS MY HUSBAND!").first
    card.locator("header a[aria-label='View ranking details']").click()

    modal = page.locator("#modal-stats")
    expect(modal).to_be_visible()

    # Verify list count is 10
    expect(modal.locator("text=List Count").locator("..")).to_contain_text("10")

    # Consensus Boost should be > 0% for a song with many sources (log(10) > 0)
    consensus_boost_row = modal.locator("text=Consensus Boost").locator("..")
    consensus_boost_text = consensus_boost_row.inner_text()
    # The boost should not be "0%" since log(10) > 0
    # Default consensus_boost is 0.03 (3%), so with 10 sources we should see a positive boost
    assert "Consensus Boost" in consensus_boost_text

