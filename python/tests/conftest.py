import os
import json
import pytest
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler
import socket

# Define the project root relative to this file
# python/tests/conftest.py -> ... -> project root
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
TEST_DATA_PATH = os.path.join(os.path.dirname(__file__), "testdata/test_data.json")

class CORSRequestHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200, "ok")
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header("Access-Control-Allow-Headers", "X-Requested-With")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

@pytest.fixture(scope="session")
def test_data():
    with open(TEST_DATA_PATH, "r") as f:
        return json.load(f)

@pytest.fixture(scope="session")
def server_url():
    """Starts a static file server serving the project root."""
    # Find a free port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        port = s.getsockname()[1]

    def start_server():
        # Change directory to project root for the server
        # We need to be careful not to change the global CWD for the test runner if possible,
        # but SimpleHTTPRequestHandler defaults to CWD.
        # Alternatively, we can pass directory to SimpleHTTPRequestHandler in Python 3.7+
        handler = lambda *args: CORSRequestHandler(*args, directory=PROJECT_ROOT)
        httpd = HTTPServer(("localhost", port), handler)
        httpd.serve_forever()

    thread = threading.Thread(target=start_server, daemon=True)
    thread.start()
    
    yield f"http://localhost:{port}"

@pytest.fixture(autouse=True)
def mock_data_json(page, test_data):
    """Intercepts requests to data.json and serves test_data instead."""
    def handle_route(route):
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(test_data)
        )

    # Intercept any request ending in data.json
    page.route("**/data.json", handle_route)

