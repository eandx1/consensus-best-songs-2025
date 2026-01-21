from playwright.sync_api import Page, expect

from conftest import open_about_modal


def test_about_modal(page: Page, server_url):
    """Test about modal opens and contains key sections."""
    page.goto(server_url)

    open_about_modal(page)

    modal = page.locator("#modal-about")
    expect(modal).to_be_visible()

    expect(modal).to_contain_text("Behind the project")
    expect(modal).to_contain_text("How it works")
    expect(modal).to_contain_text("Sources")

    # Check dynamic song count
    # test_data.json has 35 songs
    expect(modal.locator("#total-songs-count")).to_contain_text("35")


def test_about_modal_top_button(page: Page, server_url):
    """Test that Back to top button scrolls to top of modal."""
    page.goto(server_url)

    open_about_modal(page)

    modal = page.locator("#modal-about")
    expect(modal).to_be_visible()

    # Scroll to bottom of modal
    page.evaluate("document.querySelector('#modal-about article').scrollTop = document.querySelector('#modal-about article').scrollHeight")

    # Click Back to top button
    top_button = modal.get_by_role("button", name="Back to top")
    expect(top_button).to_be_visible()
    top_button.click()

    # Wait for smooth scroll animation
    page.wait_for_timeout(1000)

    # Modal should be scrolled back to top
    scroll_top = page.evaluate("document.querySelector('#modal-about article').scrollTop")
    assert scroll_top < 50, f"Modal should be scrolled to top, but scrollTop is {scroll_top}"


def test_about_modal_close_button(page: Page, server_url):
    """Test that Close button closes the modal."""
    page.goto(server_url)

    open_about_modal(page)

    modal = page.locator("#modal-about")
    expect(modal).to_be_visible()

    # Click Close button
    close_button = modal.locator("footer button.close-modal")
    close_button.click()

    # Modal should be closed
    expect(modal).not_to_be_visible()

