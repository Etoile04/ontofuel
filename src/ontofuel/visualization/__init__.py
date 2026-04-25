"""Visualization modules."""

import webbrowser
import http.server
import threading
from pathlib import Path

TEMPLATES_DIR = Path(__file__).parent / "templates"


def start_viewer(port: int = 9999, ontology_dir: str | None = None, open_browser: bool = True):
    """Start the ontology visualization web server.

    Args:
        port: Port number (default 9999)
        ontology_dir: Directory containing ontology data files.
                      Defaults to the package ontology/ directory.
        open_browser: Whether to open the browser automatically.
    """
    # Determine serving directory (templates has the HTML)
    serve_dir = str(TEMPLATES_DIR)

    # If ontology_dir provided, symlink data files into serve dir
    if ontology_dir:
        import os
        for f in Path(ontology_dir).glob("*.json"):
            target = Path(serve_dir) / f.name
            if not target.exists():
                os.symlink(str(f), str(target))

    handler = http.server.SimpleHTTPRequestHandler

    class QuietHandler(handler):
        def log_message(self, format, *args):
            pass  # Suppress logs

    server = http.server.HTTPServer(("", port), QuietHandler)
    print(f"OntoFuel visualization running at http://localhost:{port}")

    if open_browser:
        webbrowser.open(f"http://localhost:{port}/ontology_viz.html")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
        server.server_close()
