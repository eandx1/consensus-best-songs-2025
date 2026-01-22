"""
Shared test fixtures and helpers for Playwright tests.

This module provides:
- Server fixtures for running the static site
- Data fixtures for test data
- Helper functions for common UI operations (opening modals, etc.)
"""
import json
import os
import socket
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler

import pytest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
TEST_DATA_PATH = os.path.join(os.path.dirname(__file__), "testdata/test_data.json")


class CORSRequestHandler(SimpleHTTPRequestHandler):
    """HTTP request handler with CORS headers for local testing."""

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200, "ok")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "X-Requested-With")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()


# =============================================================================
# Session-scoped fixtures
# =============================================================================


@pytest.fixture(scope="session")
def test_data():
    """Load test data from JSON file."""
    with open(TEST_DATA_PATH, "r") as f:
        return json.load(f)


@pytest.fixture(scope="session")
def server_url():
    """Start a static file server serving the project root."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        port = s.getsockname()[1]

    def start_server():
        handler = lambda *args: CORSRequestHandler(*args, directory=PROJECT_ROOT)
        httpd = HTTPServer(("localhost", port), handler)
        httpd.serve_forever()

    thread = threading.Thread(target=start_server, daemon=True)
    thread.start()

    yield f"http://localhost:{port}"


@pytest.fixture(autouse=True)
def mock_data_json(page, test_data):
    """Intercept requests to data.json and serve test_data instead."""

    def handle_route(route):
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(test_data),
        )

    page.route("**/data.json", handle_route)


# =============================================================================
# UI Helper Functions
# =============================================================================


def open_hamburger_menu(page):
    """Open the hamburger menu."""
    page.locator("#hamburger-btn").click()


def open_tune_modal(page):
    """Open the Tune Ranking modal."""
    page.locator("#open-tune").click()


def open_about_modal(page):
    """Open the About modal via hamburger menu."""
    open_hamburger_menu(page)
    page.locator("#open-about-menu").click()


def open_youtube_modal(page):
    """Open the YouTube playlist modal via hamburger menu."""
    open_hamburger_menu(page)
    page.locator("#open-youtube-menu").click()


def open_download_modal(page):
    """Open the Download playlist modal via hamburger menu."""
    open_hamburger_menu(page)
    page.locator("#open-download-menu").click()


def open_stats_modal(page, song_card):
    """Open the Ranking Stats modal for a song card."""
    song_card.locator("header a[aria-label='View ranking details']").click()


def open_reviews_modal(page, song_card):
    """Open the Reviews modal for a song card by clicking the sources list."""
    song_card.locator("[data-sources]").click()


def close_modal(page, modal_id):
    """Close a modal by clicking its Close button."""
    page.locator(f"{modal_id} footer button.close-modal").click()


def get_song_card(page, song_title):
    """Get the first song card matching the given title."""
    return page.locator(".song-card", has_text=song_title).first


def show_all_songs(page):
    """Click 'Show More' until all songs are displayed."""
    while page.locator("#load-more").is_visible():
        page.locator("#load-more").click()
        page.wait_for_timeout(100)


def wait_for_debounce(page, ms=500):
    """Wait for debounced operations to complete."""
    page.wait_for_timeout(ms)


def disable_animations(page):
    """Disable all CSS animations and transitions for stable visual tests."""
    page.add_style_tag(
        content="""
        *, *::before, *::after {
            animation: none !important;
            animation-duration: 0s !important;
            transition: none !important;
            transition-duration: 0s !important;
        }
    """
    )


def set_theme(page, theme_name):
    """Set the theme via URL parameter and wait for it to apply."""
    current_url = page.url
    separator = "&" if "?" in current_url else "?"
    # Remove existing theme param if present
    import re

    base_url = re.sub(r"[?&]theme=[^&]*", "", current_url)
    separator = "&" if "?" in base_url else "?"
    new_url = f"{base_url}{separator}theme={theme_name}"
    page.goto(new_url)
    page.wait_for_load_state("networkidle")

