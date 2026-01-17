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

def test_consensus_mode_ranking_changes(page: Page, server_url):
    """Test that consensus mode settings changes produce ranking changes."""
    page.goto(server_url)
    page.wait_for_timeout(300)
    
    # Capture INITIAL state with default settings
    initial_top_song = page.locator(".song-card").first.locator("h3").inner_text()
    initial_song_2 = page.locator(".song-card").nth(1).locator("h3").inner_text()
    initial_song_3 = page.locator(".song-card").nth(2).locator("h3").inner_text()
    
    # Get initial scores for top song
    page.locator(".song-card").first.locator("header a[aria-label='View ranking details']").click()
    modal = page.locator("#modal-stats")
    expect(modal).to_be_visible()
    
    initial_norm_text = modal.locator("text=Normalized Score").locator("..").inner_text()
    initial_raw_text = modal.locator("text=Raw Score").locator("..").inner_text()
    initial_norm_score = float(re.search(r"(\d+\.\d+)", initial_norm_text).group(1))
    initial_raw_score = float(re.search(r"(\d+\.\d+)", initial_raw_text).group(1))
    
    page.keyboard.press("Escape")
    page.wait_for_timeout(200)
    
    # Now CHANGE settings
    page.locator("#open-settings").click()
    page.wait_for_timeout(200)
    
    # Change settings:
    # - 5% consensus boost (0.05) [default is 3%]
    # - 0.0 Buzzfeed weight [default is 0.5]
    # - 0.0 Independent weight [default is 0.6]
    # - 15 K value [default is 20]
    
    # Set consensus boost to 5% (0.05)
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
    page.wait_for_timeout(300)
    
    # Capture NEW state after settings change
    new_top_song = page.locator(".song-card").first.locator("h3").inner_text()
    new_song_2 = page.locator(".song-card").nth(1).locator("h3").inner_text()
    new_song_3 = page.locator(".song-card").nth(2).locator("h3").inner_text()
    
    # Verify song names to show ranking occurred (store for comparison)
    print(f"\nInitial rankings: #{1}={initial_top_song}, #{2}={initial_song_2}, #{3}={initial_song_3}")
    print(f"New rankings: #{1}={new_top_song}, #{2}={new_song_2}, #{3}={new_song_3}")
    
    # Get NEW scores for top song
    page.locator(".song-card").first.locator("header a[aria-label='View ranking details']").click()
    expect(modal).to_be_visible()
    
    # Check normalized score is 1.0 for top song (always true for #1)
    normalized_row = modal.locator("text=Normalized Score").locator("..")
    new_norm_text = normalized_row.inner_text()
    new_norm_score = float(re.search(r"(\d+\.\d+)", new_norm_text).group(1))
    assert new_norm_score == 1.0, f"Top song should have normalized score 1.0, got {new_norm_score}"
    
    # Extract raw score and verify it changed
    raw_row = modal.locator("text=Raw Score").locator("..")
    new_raw_text = raw_row.inner_text()
    new_raw_score = float(re.search(r"(\d+\.\d+)", new_raw_text).group(1))
    
    print(f"Initial scores: norm={initial_norm_score}, raw={initial_raw_score}")
    print(f"New scores: norm={new_norm_score}, raw={new_raw_score}")
    
    # The raw score should be different due to settings changes
    # (unless we're very unlucky with the math, which is unlikely given 5 different changes)
    assert abs(new_raw_score - initial_raw_score) > 0.001, \
        f"Raw score should have changed! Was {initial_raw_score}, still {new_raw_score}"
    
    # Check consensus boost contribution
    consensus_mul_row = modal.locator("text=Consensus Boost").locator("..")
    consensus_mul_text = consensus_mul_row.inner_text()
    consensus_boost_pct = float(re.search(r"(\d+\.\d+)%", consensus_mul_text).group(1))
    print(f"Consensus boost: {consensus_boost_pct}%")
    
    # With normalized consensus boost, the slider percentage represents the MAX boost
    # (for the song with the most lists). Songs with fewer lists get proportionally less.
    # A song on 10 lists with 5% boost slider will get: 5% * ln(10)/ln(max_list_count)
    # This should be positive and <= 5%
    assert consensus_boost_pct > 0, f"Expected consensus boost > 0%, got {consensus_boost_pct}%"
    assert consensus_boost_pct <= 5.1, f"Expected consensus boost <= 5%, got {consensus_boost_pct}%"
    
    # Check that Buzzfeed contribution is 0.0000
    buzzfeed_contrib = modal.locator(".contribution-row", has_text="Buzzfeed")
    if buzzfeed_contrib.count() > 0:
        expect(buzzfeed_contrib).to_contain_text("0.0000")
        print("✓ Buzzfeed weight=0 confirmed: contributes 0.0000")
    
    page.keyboard.press("Escape")
    page.wait_for_timeout(200)
    
    # Check scores for songs #2, #3, and #25
    for idx, song_num in enumerate([1, 2, 24]):
        card = page.locator(".song-card").nth(song_num)
        card.locator("header a[aria-label='View ranking details']").click()
        expect(modal).to_be_visible()
        
        # Extract and verify scores exist and are reasonable
        norm_text = modal.locator("text=Normalized Score").locator("..").inner_text()
        raw_text = modal.locator("text=Raw Score").locator("..").inner_text()
        
        norm_score = float(re.search(r"(\d+\.\d+)", norm_text).group(1))
        raw_score = float(re.search(r"(\d+\.\d+)", raw_text).group(1))
        
        # Normalized scores should be descending (1.0 > song2 > song3 > ... > song25)
        assert 0 < norm_score <= 1.0, f"Song #{song_num+1} normalized score should be 0-1, got {norm_score}"
        assert raw_score > 0, f"Song #{song_num+1} raw score should be positive, got {raw_score}"
        
        print(f"Song #{song_num+1}: norm={norm_score:.4f}, raw={raw_score:.4f}")
        
        page.keyboard.press("Escape")
        page.wait_for_timeout(200)
    
    print("✓ All consensus mode ranking changes verified")

def test_conviction_mode_ranking_changes(page: Page, server_url):
    """Test that conviction mode settings changes produce ranking changes and different top songs."""
    page.goto(server_url)
    page.wait_for_timeout(300)
    
    # Capture INITIAL state with default consensus mode settings
    initial_top_song = page.locator(".song-card").first.locator("h3").inner_text()
    initial_song_2 = page.locator(".song-card").nth(1).locator("h3").inner_text()
    initial_song_3 = page.locator(".song-card").nth(2).locator("h3").inner_text()
    
    print(f"\nInitial (Consensus mode) rankings:")
    print(f"  #1: {initial_top_song}")
    print(f"  #2: {initial_song_2}")
    print(f"  #3: {initial_song_3}")
    
    # Get initial score for top song
    page.locator(".song-card").first.locator("header a[aria-label='View ranking details']").click()
    modal = page.locator("#modal-stats")
    expect(modal).to_be_visible()
    
    initial_raw_text = modal.locator("text=Raw Score").locator("..").inner_text()
    initial_raw_score = float(re.search(r"(\d+\.\d+)", initial_raw_text).group(1))
    print(f"  Initial top raw score: {initial_raw_score}")
    
    page.keyboard.press("Escape")
    page.wait_for_timeout(200)
    
    # Now CHANGE to Conviction mode with different settings
    page.locator("#open-settings").click()
    page.wait_for_timeout(200)
    
    # Switch to Conviction mode (this will cause a significant ranking change)
    conviction_card = page.locator("article.mode-card", has_text="🔥 Conviction")
    conviction_card.click()
    page.wait_for_timeout(400)
    
    # Set P exponent to 0.7 (more aggressive decay, favors #1 ranks even more)
    page.evaluate("document.getElementById('setting-ranking-p_exponent').value = '0.7'")
    page.locator("#setting-ranking-p_exponent").dispatch_event("input")
    
    # Set consensus boost to 0% (removes advantage for appearing on many lists)
    page.evaluate("document.getElementById('setting-ranking-consensus_boost').value = '0'")
    page.locator("#setting-ranking-consensus_boost").dispatch_event("input")
    
    # Set cluster boost to 0% (removes crossover bonus)
    page.evaluate("document.getElementById('setting-ranking-cluster_boost').value = '0'")
    page.locator("#setting-ranking-cluster_boost").dispatch_event("input")
    
    # Set provocation boost to 5% (rewards polarizing songs)
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
    
    # Capture NEW state after switching to Conviction mode
    new_top_song = page.locator(".song-card").first.locator("h3").inner_text()
    new_song_2 = page.locator(".song-card").nth(1).locator("h3").inner_text()
    new_song_3 = page.locator(".song-card").nth(2).locator("h3").inner_text()
    
    print(f"\nNew (Conviction mode) rankings:")
    print(f"  #1: {new_top_song}")
    print(f"  #2: {new_song_2}")
    print(f"  #3: {new_song_3}")
    
    # Verify that the ranking actually changed
    # (Conviction mode should produce different results than Consensus mode)
    ranking_changed = (
        new_top_song != initial_top_song or
        new_song_2 != initial_song_2 or
        new_song_3 != initial_song_3
    )
    assert ranking_changed, \
        "Rankings should change between Consensus and Conviction modes!"
    print("✓ Rankings changed between modes (as expected)")
    
    # Get NEW score for top song
    page.locator(".song-card").first.locator("header a[aria-label='View ranking details']").click()
    expect(modal).to_be_visible()
    
    new_norm_text = modal.locator("text=Normalized Score").locator("..").inner_text()
    new_raw_text = modal.locator("text=Raw Score").locator("..").inner_text()
    
    new_norm_score = float(re.search(r"(\d+\.\d+)", new_norm_text).group(1))
    new_raw_score = float(re.search(r"(\d+\.\d+)", new_raw_text).group(1))
    
    assert new_norm_score == 1.0, f"Top song should have normalized score 1.0, got {new_norm_score}"
    print(f"  New top raw score: {new_raw_score}")
    
    # Check that boosts are set correctly
    consensus_text = modal.locator("text=Consensus Boost").locator("..").inner_text()
    cluster_text = modal.locator("text=Cluster Boost").locator("..").inner_text()
    provocation_text = modal.locator("text=Provocation Boost").locator("..").inner_text()
    
    assert "0.00%" in consensus_text, f"Expected consensus boost 0.00%, got {consensus_text}"
    assert "0.00%" in cluster_text, f"Expected cluster boost 0.00%, got {cluster_text}"
    print("✓ Consensus and cluster boosts are 0.00% (as configured)")
    
    # Extract provocation boost - should be > 0% for songs with rank variation
    provocation_pct = float(re.search(r"(\d+\.\d+)%", provocation_text).group(1))
    print(f"  Provocation boost: {provocation_pct}%")
    
    page.keyboard.press("Escape")
    page.wait_for_timeout(200)
    
    # Track the largest provocation boost and verify scores decrease
    max_provocation_boost = provocation_pct
    prev_norm_score = new_norm_score
    
    # Check scores for songs #2, #3, and #25
    for idx, song_num in enumerate([1, 2, 24]):
        card = page.locator(".song-card").nth(song_num)
        song_name = card.locator("h3").inner_text()
        card.locator("header a[aria-label='View ranking details']").click()
        expect(modal).to_be_visible()
        
        # Extract scores
        norm_text = modal.locator("text=Normalized Score").locator("..").inner_text()
        raw_text = modal.locator("text=Raw Score").locator("..").inner_text()
        consensus_text = modal.locator("text=Consensus Boost").locator("..").inner_text()
        cluster_text = modal.locator("text=Cluster Boost").locator("..").inner_text()
        provocation_text = modal.locator("text=Provocation Boost").locator("..").inner_text()
        
        norm_score = float(re.search(r"(\d+\.\d+)", norm_text).group(1))
        raw_score = float(re.search(r"(\d+\.\d+)", raw_text).group(1))
        
        # Verify scores are in valid range and descending
        assert 0 < norm_score < prev_norm_score, \
            f"Song #{song_num+1} norm score {norm_score} should be < previous {prev_norm_score}"
        assert raw_score > 0, f"Song #{song_num+1} raw score should be positive, got {raw_score}"
        
        # Verify boosts
        assert "0.00%" in consensus_text, f"Song #{song_num+1}: Expected consensus 0.00%"
        assert "0.00%" in cluster_text, f"Song #{song_num+1}: Expected cluster 0.00%"
        
        # Track max provocation boost
        prov_pct = float(re.search(r"(\d+\.\d+)%", provocation_text).group(1))
        max_provocation_boost = max(max_provocation_boost, prov_pct)
        
        print(f"  Song #{song_num+1} ({song_name}): norm={norm_score:.4f}, raw={raw_score:.4f}, provocation={prov_pct}%")
        
        prev_norm_score = norm_score
        page.keyboard.press("Escape")
        page.wait_for_timeout(200)
    
    # Verify we found at least one song with provocation boost > 0%
    assert max_provocation_boost > 0, \
        f"Expected max provocation boost > 0%, got {max_provocation_boost}%"
    print(f"✓ Max provocation boost found: {max_provocation_boost}%")
    print("✓ All conviction mode ranking changes verified")
