"""
Accessibility testing using axe-core via Playwright.

These tests check for WCAG 2.1 AA compliance on the main page and modals.

Note: Color contrast violations (color-contrast rule) are excluded from blocking
tests because they require coordinated design changes. They are logged for
tracking but don't fail the CI. To fix contrast issues, update the CSS custom
properties in the theme definitions.
"""
from playwright.sync_api import Page, expect
from axe_playwright_python.sync_playwright import Axe
import pytest

from conftest import (
    open_tune_modal,
    open_about_modal,
    open_youtube_modal,
    open_download_modal,
    open_stats_modal,
    open_reviews_modal,
    get_song_card,
)

# Rules to exclude from blocking tests (tracked separately)
EXCLUDED_RULES = {"color-contrast"}


@pytest.fixture
def axe():
    """Create an Axe instance for accessibility testing."""
    return Axe()


def get_violations_summary(violations):
    """Extract a readable summary of accessibility violations."""
    if not violations:
        return None

    summary = []
    for v in violations:
        impact = v.get("impact", "unknown")
        description = v.get("description", "No description")
        nodes_count = len(v.get("nodes", []))
        summary.append(f"[{impact}] {description} ({nodes_count} occurrences)")

    return "\n".join(summary)


def filter_violations(violations, excluded_rules=EXCLUDED_RULES):
    """Filter violations to serious/critical, excluding specified rules."""
    return [
        v for v in violations
        if v.get("impact") in ["critical", "serious"]
        and v.get("id") not in excluded_rules
    ]


def log_excluded_violations(violations, excluded_rules=EXCLUDED_RULES):
    """Log violations that were excluded from blocking tests."""
    excluded = [v for v in violations if v.get("id") in excluded_rules]
    if excluded:
        for v in excluded:
            nodes_count = len(v.get("nodes", []))
            print(f"[INFO] Excluded violation: {v.get('id')} ({nodes_count} occurrences) - tracked for design review")


def test_main_page_accessibility(page: Page, server_url, axe):
    """Test accessibility of the main page with song list."""
    page.goto(server_url)

    # Wait for content to load
    page.locator(".song-card").first.wait_for()

    # Run axe analysis
    results = axe.run(page)

    # Check for violations (access via .response property)
    violations = results.response.get("violations", [])

    # Log excluded violations for tracking
    log_excluded_violations(violations)

    # Filter to only serious/critical violations, excluding tracked rules
    serious_violations = filter_violations(violations)

    if serious_violations:
        summary = get_violations_summary(serious_violations)
        pytest.fail(f"Found {len(serious_violations)} serious accessibility violations:\n{summary}")


def test_tune_modal_accessibility(page: Page, server_url, axe):
    """Test accessibility of the Tune Ranking modal."""
    page.goto(server_url)
    page.locator(".song-card").first.wait_for()

    open_tune_modal(page)
    expect(page.locator("#modal-tune")).to_be_visible()

    # Run axe on the modal
    results = axe.run(page, context="#modal-tune")

    violations = results.response.get("violations", [])
    log_excluded_violations(violations)
    serious_violations = filter_violations(violations)

    if serious_violations:
        summary = get_violations_summary(serious_violations)
        pytest.fail(f"Tune modal has {len(serious_violations)} serious accessibility violations:\n{summary}")


def test_about_modal_accessibility(page: Page, server_url, axe):
    """Test accessibility of the About modal."""
    page.goto(server_url)
    page.locator(".song-card").first.wait_for()

    open_about_modal(page)
    expect(page.locator("#modal-about")).to_be_visible()

    results = axe.run(page, context="#modal-about")

    violations = results.response.get("violations", [])
    log_excluded_violations(violations)
    serious_violations = filter_violations(violations)

    if serious_violations:
        summary = get_violations_summary(serious_violations)
        pytest.fail(f"About modal has {len(serious_violations)} serious accessibility violations:\n{summary}")


def test_reviews_modal_accessibility(page: Page, server_url, axe):
    """Test accessibility of the Reviews modal."""
    page.goto(server_url)
    page.locator(".song-card").first.wait_for()

    # Open reviews modal for first song
    song_card = page.locator(".song-card").first
    open_reviews_modal(page, song_card)
    expect(page.locator("#modal-reviews")).to_be_visible()

    results = axe.run(page, context="#modal-reviews")

    violations = results.response.get("violations", [])
    log_excluded_violations(violations)
    serious_violations = filter_violations(violations)

    if serious_violations:
        summary = get_violations_summary(serious_violations)
        pytest.fail(f"Reviews modal has {len(serious_violations)} serious accessibility violations:\n{summary}")


def test_stats_modal_accessibility(page: Page, server_url, axe):
    """Test accessibility of the Stats modal."""
    page.goto(server_url)
    page.locator(".song-card").first.wait_for()

    # Open stats modal for first song
    song_card = page.locator(".song-card").first
    open_stats_modal(page, song_card)
    expect(page.locator("#modal-stats")).to_be_visible()

    results = axe.run(page, context="#modal-stats")

    violations = results.response.get("violations", [])
    log_excluded_violations(violations)
    serious_violations = filter_violations(violations)

    if serious_violations:
        summary = get_violations_summary(serious_violations)
        pytest.fail(f"Stats modal has {len(serious_violations)} serious accessibility violations:\n{summary}")


def test_youtube_modal_accessibility(page: Page, server_url, axe):
    """Test accessibility of the YouTube playlist modal."""
    page.goto(server_url)
    page.locator(".song-card").first.wait_for()

    open_youtube_modal(page)
    expect(page.locator("#modal-youtube")).to_be_visible()

    results = axe.run(page, context="#modal-youtube")

    violations = results.response.get("violations", [])
    log_excluded_violations(violations)
    serious_violations = filter_violations(violations)

    if serious_violations:
        summary = get_violations_summary(serious_violations)
        pytest.fail(f"YouTube modal has {len(serious_violations)} serious accessibility violations:\n{summary}")


def test_download_modal_accessibility(page: Page, server_url, axe):
    """Test accessibility of the Download modal."""
    page.goto(server_url)
    page.locator(".song-card").first.wait_for()

    open_download_modal(page)
    expect(page.locator("#modal-download")).to_be_visible()

    results = axe.run(page, context="#modal-download")

    violations = results.response.get("violations", [])
    log_excluded_violations(violations)
    serious_violations = filter_violations(violations)

    if serious_violations:
        summary = get_violations_summary(serious_violations)
        pytest.fail(f"Download modal has {len(serious_violations)} serious accessibility violations:\n{summary}")


def test_keyboard_navigation_song_cards(page: Page, server_url):
    """Test that song cards are keyboard navigable."""
    page.goto(server_url)
    page.locator(".song-card").first.wait_for()

    # The sources div should be focusable with tabindex
    sources_div = page.locator("[data-sources]").first
    expect(sources_div).to_have_attribute("tabindex", "0")

    # The info icon should be a focusable link
    info_link = page.locator(".song-card").first.locator("header a[aria-label='View ranking details']")
    expect(info_link).to_have_attribute("aria-label", "View ranking details")


def test_aria_labels_present(page: Page, server_url):
    """Test that important interactive elements have ARIA labels."""
    page.goto(server_url)
    page.locator(".song-card").first.wait_for()

    # Check tune button accessibility
    tune_btn = page.locator("#open-tune")
    expect(tune_btn).to_be_visible()

    # Check hamburger menu has aria-expanded
    hamburger_btn = page.locator("#hamburger-btn")
    expect(hamburger_btn).to_have_attribute("aria-expanded", "false")

    # Check song sources have aria-label (must provide expected value pattern)
    sources = page.locator("[data-sources]").first
    aria_label = sources.get_attribute("aria-label")
    assert aria_label is not None, "Sources element should have aria-label"
    assert len(aria_label) > 0, "aria-label should not be empty"

    # Check media nav has aria-label
    media_nav = page.locator(".song-card nav[aria-label='Listen links']").first
    expect(media_nav).to_be_visible()
