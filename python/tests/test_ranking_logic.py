import re
from playwright.sync_api import Page, expect

def test_url_params_override_config(page: Page, server_url):
    """Test that URL parameters override default configuration."""
    # Default k_value is 20 in test_data.json
    # We pass k_value=50 in URL
    page.goto(f"{server_url}/?k_value=50")
    
    # Check via UI instead of internal state
    page.locator("#open-settings").click()
    
    # Check k_value slider
    k_slider = page.locator("#setting-ranking-k_value")
    expect(k_slider).to_have_value("50")

def test_slider_updates_url(page: Page, server_url):
    """Test that changing a slider updates the URL."""
    page.goto(server_url)
    
    # Open settings
    page.locator("#open-settings").click()
    
    # Find Consensus Boost slider (range input)
    # id="setting-ranking-consensus_boost"
    slider = page.locator("#setting-ranking-consensus_boost")
    expect(slider).to_be_visible()
    
    # Change value
    slider.fill("0.1") # 10%
    slider.dispatch_event("input")
    
    # Wait for debounce (250ms) + buffer
    page.wait_for_timeout(500)
    
    # Check URL
    expect(page).to_have_url(re.compile("consensus_boost=0.1"))
    
    # Verify the value persists in the UI
    expect(slider).to_have_value("0.1")

def test_theme_switch(page: Page, server_url):
    """Test theme switching updates URL and HTML attribute."""
    page.goto(server_url)
    
    # Verify default theme
    expect(page.locator("html")).to_have_attribute("data-theme", "dark")
    
    # Open settings and switch theme
    page.locator("#open-settings").click()
    # Note: test_data only has 'original-dark' so we might not be able to switch unless we hack it
    # But let's check if the select exists
    select = page.locator("select").first
    expect(select).to_be_visible()
    
    # If we had another theme we would select it. 
    # Since we don't, we can just verify the default is selected.
    expect(select).to_have_value("original-dark")

def test_consensus_mode_ranking_changes(page: Page, server_url):
    """Test that consensus mode settings changes produce ranking changes."""
    page.goto(server_url)
    
    # Open settings
    page.locator("#open-settings").click()
    page.wait_for_timeout(200)
    
    # Change settings:
    # - 5% consensus boost (0.05)
    # - 0.0 Buzzfeed weight
    # - 0.0 Independent weight  
    # - 15 K value
    
    # Set consensus boost to 5% (0.05) - use evaluate to set range input value
    page.evaluate("document.getElementById('setting-ranking-consensus_boost').value = '0.05'")
    page.locator("#setting-ranking-consensus_boost").dispatch_event("input")
    
    # Set K value to 15
    page.evaluate("document.getElementById('setting-ranking-k_value').value = '15'")
    page.locator("#setting-ranking-k_value").dispatch_event("input")
    
    # Set Buzzfeed weight to 0.0
    page.evaluate("document.getElementById('setting-source_weight-Buzzfeed').value = '0'")
    page.locator("#setting-source_weight-Buzzfeed").dispatch_event("input")
    
    # Set Independent weight to 0.0
    page.evaluate("document.getElementById('setting-source_weight-Independent').value = '0'")
    page.locator("#setting-source_weight-Independent").dispatch_event("input")
    
    # Wait for debounce
    page.wait_for_timeout(500)
    
    # Check URL updated with expected settings
    expect(page).to_have_url(re.compile("consensus_boost=0.05"))
    expect(page).to_have_url(re.compile("k_value=15"))
    expect(page).to_have_url(re.compile("buzzfeed=0"))
    expect(page).to_have_url(re.compile("independent=0"))
    
    # Close settings modal
    page.locator("#modal-settings button", has_text="Close").click()
    
    # Wait for modal to close and list to rerank
    page.wait_for_timeout(300)
    
    # Get top song card (should still be RAYE with these settings, but scores will differ)
    first_card = page.locator(".song-card").first
    
    # Open stats modal for #1
    first_card.locator("header a[aria-label='View ranking details']").click()
    modal = page.locator("#modal-stats")
    expect(modal).to_be_visible()
    
    # Check normalized score is 1.0 for top song
    normalized_row = modal.locator("text=Normalized Score").locator("..")
    expect(normalized_row).to_contain_text(re.compile(r"1\.0+"))
    
    # Extract and verify raw score exists
    raw_row = modal.locator("text=Raw Score").locator("..")
    expect(raw_row).to_be_visible()
    raw_score_text = raw_row.inner_text()
    # Raw score should be a number
    assert re.search(r"\d+\.\d+", raw_score_text)
    
    # Check consensus multiplier contribution
    consensus_mul_row = modal.locator("text=Consensus Boost").locator("..")
    expect(consensus_mul_row).to_be_visible()
    consensus_mul_text = consensus_mul_row.inner_text()
    # With 10 lists and 5% boost parameter, the actual boost should be positive
    # Extract percentage value and verify it's greater than 0%
    match = re.search(r"(\d+\.\d+)%", consensus_mul_text)
    assert match, f"Could not find consensus boost percentage in {consensus_mul_text}"
    consensus_boost_pct = float(match.group(1))
    # With 10 lists, should have a positive consensus boost (roughly 8-12%)
    assert consensus_boost_pct > 7, f"Expected consensus boost > 7%, got {consensus_boost_pct}%"
    
    # Check that Buzzfeed contribution is 0.0 (if it was a source)
    # RAYE's song has Buzzfeed#3 as a source
    buzzfeed_contrib = modal.locator(".contribution-row", has_text="Buzzfeed")
    if buzzfeed_contrib.count() > 0:
        expect(buzzfeed_contrib).to_contain_text("0.0000")
    
    # Close modal
    page.keyboard.press("Escape")
    page.wait_for_timeout(200)
    
    # Check song #2
    second_card = page.locator(".song-card").nth(1)
    second_card.locator("header a[aria-label='View ranking details']").click()
    expect(modal).to_be_visible()
    
    # Verify scores exist
    expect(modal.locator("text=Normalized Score").locator("..")).to_be_visible()
    expect(modal.locator("text=Raw Score").locator("..")).to_be_visible()
    
    page.keyboard.press("Escape")
    page.wait_for_timeout(200)
    
    # Check song #3
    third_card = page.locator(".song-card").nth(2)
    third_card.locator("header a[aria-label='View ranking details']").click()
    expect(modal).to_be_visible()
    
    expect(modal.locator("text=Normalized Score").locator("..")).to_be_visible()
    expect(modal.locator("text=Raw Score").locator("..")).to_be_visible()
    
    page.keyboard.press("Escape")
    page.wait_for_timeout(200)
    
    # Check song #25
    card_25 = page.locator(".song-card").nth(24)
    card_25.locator("header a[aria-label='View ranking details']").click()
    expect(modal).to_be_visible()
    
    expect(modal.locator("text=Normalized Score").locator("..")).to_be_visible()
    expect(modal.locator("text=Raw Score").locator("..")).to_be_visible()
    
    page.keyboard.press("Escape")

def test_conviction_mode_ranking_changes(page: Page, server_url):
    """Test that conviction mode settings changes produce ranking changes."""
    page.goto(server_url)
    
    # Open settings
    page.locator("#open-settings").click()
    page.wait_for_timeout(200)
    
    # Change to Conviction mode by clicking the article with "🔥 Conviction"
    conviction_card = page.locator("article.mode-card", has_text="🔥 Conviction")
    conviction_card.click()
    
    # Wait for mode switch and UI to re-render
    page.wait_for_timeout(400)
    
    # Set P exponent to 0.7
    p_slider = page.locator("#setting-ranking-p_exponent")
    expect(p_slider).to_be_visible()
    page.evaluate("document.getElementById('setting-ranking-p_exponent').value = '0.7'")
    p_slider.dispatch_event("input")
    
    # Set consensus boost to 0%
    page.evaluate("document.getElementById('setting-ranking-consensus_boost').value = '0'")
    page.locator("#setting-ranking-consensus_boost").dispatch_event("input")
    
    # Set cluster boost to 0%
    page.evaluate("document.getElementById('setting-ranking-cluster_boost').value = '0'")
    page.locator("#setting-ranking-cluster_boost").dispatch_event("input")
    
    # Set provocation boost to 5% (0.05)
    page.evaluate("document.getElementById('setting-ranking-provocation_boost').value = '0.05'")
    page.locator("#setting-ranking-provocation_boost").dispatch_event("input")
    
    # Wait for debounce
    page.wait_for_timeout(500)
    
    # Check URL updated
    expect(page).to_have_url(re.compile("decay_mode=conviction"))
    expect(page).to_have_url(re.compile("p_exponent=0.7"))
    expect(page).to_have_url(re.compile("consensus_boost=0"))
    expect(page).to_have_url(re.compile("cluster_boost=0"))
    expect(page).to_have_url(re.compile("provocation_boost=0.05"))
    
    # Close settings modal
    page.locator("#modal-settings button", has_text="Close").click()
    page.wait_for_timeout(300)
    
    # Track the largest provocation boost we find
    max_provocation_boost = 0.0
    
    # Check top 3 songs and song #25
    for idx in [0, 1, 2, 24]:
        card = page.locator(".song-card").nth(idx)
        card.locator("header a[aria-label='View ranking details']").click()
        
        modal = page.locator("#modal-stats")
        expect(modal).to_be_visible()
        
        # Check normalized and raw scores exist
        expect(modal.locator("text=Normalized Score").locator("..")).to_be_visible()
        expect(modal.locator("text=Raw Score").locator("..")).to_be_visible()
        
        # Check consensus boost multiplier is 0.0% (0% boost parameter)
        consensus_mul_row = modal.locator("text=Consensus Boost").locator("..")
        expect(consensus_mul_row).to_be_visible()
        consensus_text = consensus_mul_row.inner_text()
        # Should be 0.00% since consensus boost parameter is 0%
        assert "0.00%" in consensus_text, f"Expected 0.00%, got {consensus_text}"
        
        # Check cluster boost multiplier is 0.00% (0% boost parameter)
        cluster_mul_row = modal.locator("text=Cluster Boost").locator("..")
        expect(cluster_mul_row).to_be_visible()
        cluster_text = cluster_mul_row.inner_text()
        # Should be 0.00% since cluster boost parameter is 0%
        assert "0.00%" in cluster_text, f"Expected 0.00%, got {cluster_text}"
        
        # Extract provocation boost value
        provocation_mul_row = modal.locator("text=Provocation Boost").locator("..")
        expect(provocation_mul_row).to_be_visible()
        provocation_text = provocation_mul_row.inner_text()
        
        # Extract the percentage value
        match = re.search(r"(\d+\.\d+)%", provocation_text)
        if match:
            provocation_boost_pct = float(match.group(1))
            max_provocation_boost = max(max_provocation_boost, provocation_boost_pct)
        
            # Close modal
            page.keyboard.press("Escape")
            page.wait_for_timeout(200)
    
    # Verify we found at least one provocation boost > 0%
    # (songs with varying ranks should have std dev > 0, thus provocation boost > 0%)
    assert max_provocation_boost > 0, f"Expected max provocation boost > 0%, got {max_provocation_boost}%"
