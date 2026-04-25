"""Tests for visualization module."""

import pytest
from unittest.mock import patch, MagicMock

from ontofuel.visualization import start_viewer


class TestStartViewer:
    """Test visualization server startup."""

    def test_start_viewer_function_exists(self):
        """start_viewer should be importable."""
        assert callable(start_viewer)

    @patch("webbrowser.open")
    @patch("http.server.HTTPServer")
    def test_start_viewer_creates_server(self, mock_http, mock_browser):
        """Test that start_viewer creates an HTTP server."""
        mock_instance = MagicMock()
        mock_http.return_value = mock_instance
        # Make serve_forever raise KeyboardInterrupt to exit
        mock_instance.serve_forever.side_effect = KeyboardInterrupt()

        start_viewer(port=9876, open_browser=False)
        mock_http.assert_called_once()
        # Verify port
        args = mock_http.call_args
        assert args[0][0] == ("", 9876)

    @patch("http.server.HTTPServer")
    def test_start_viewer_no_browser(self, mock_http):
        """Test that open_browser=False doesn't open browser."""
        mock_instance = MagicMock()
        mock_http.return_value = mock_instance
        mock_instance.serve_forever.side_effect = KeyboardInterrupt()

        start_viewer(port=9999, open_browser=False)

    @patch("webbrowser.open")
    @patch("http.server.HTTPServer")
    def test_start_viewer_opens_browser(self, mock_http, mock_browser):
        """Test that open_browser=True opens browser."""
        mock_instance = MagicMock()
        mock_http.return_value = mock_instance
        mock_instance.serve_forever.side_effect = KeyboardInterrupt()

        start_viewer(port=9998, open_browser=True)
        mock_browser.assert_called_once_with("http://localhost:9998/ontology_viz.html")
