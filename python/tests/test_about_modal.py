from playwright.sync_api import Page, expect

def test_about_modal(page: Page, server_url):
    """Test about modal opens and contains key sections."""
    page.goto(server_url)
    
    page.locator("#open-about").click()
    
    modal = page.locator("#modal-about")
    expect(modal).to_be_visible()
    
    expect(modal).to_contain_text("Behind the project")
    expect(modal).to_contain_text("How it works")
    expect(modal).to_contain_text("Ranking methodology")
    expect(modal).to_contain_text("Decoding the UI")
    
    # Check dynamic song count
    # test_data.json has 35 songs
    expect(modal.locator("#total-songs-count")).to_contain_text("35")
    
    # Check comparison table populated
    table = modal.locator("#mode-comparison-table")
    expect(table.locator("tbody tr").first).not_to_contain_text("Loading...")
    expect(table.locator("tbody tr")).to_have_count(6) # 1, 5, 10, 25, 50, 100

