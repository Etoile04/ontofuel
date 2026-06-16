"""Visualization modules.

.. deprecated::
    This Python ``start_viewer`` (``http.server`` + D3 templates) is
    **DEPRECATED**. The canonical OntoFuel viewer is the React NVL app in
    ``visualization-app/`` — build with ``npm run build`` and embed via Docker
    (see ``visualization-app/EMBEDDING.md``). This module is retained for
    backward compatibility only and will not receive new features. See
    ``DEPRECATED.md`` next to this file for the migration guide.
"""

import http.server
import threading  # noqa: F401
import warnings
import webbrowser
from pathlib import Path

TEMPLATES_DIR = Path(__file__).parent / "templates"

_DEPRECATION_MSG = (
    "ontofuel.visualization.start_viewer is DEPRECATED. Use the React NVL "
    "viewer in visualization-app/ (npm run build) or the Docker embed entry "
    "(see visualization-app/EMBEDDING.md). See DEPRECATED.md for migration. "
    "This legacy viewer is retained for compatibility only."
)


def start_viewer(port: int = 9999, ontology_dir: str | None = None, open_browser: bool = True):
    """Start the (deprecated) ontology visualization web server.

    .. deprecated::
        Use the React NVL viewer in ``visualization-app/`` instead. This
        function emits a ``DeprecationWarning`` on every call.

    Args:
        port: Port number (default 9999)
        ontology_dir: Directory containing ontology data files.
                      Defaults to the package ontology/ directory.
        open_browser: Whether to open the browser automatically.
    """
    warnings.warn(_DEPRECATION_MSG, DeprecationWarning, stacklevel=2)

    # Determine serving directory (templates has the HTML)
    serve_dir = str(TEMPLATES_DIR)

    # If ontology_dir provided, symlink data files into serve dir
    if ontology_dir:  # pragma: no cover — integration-level
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

    if open_browser:  # pragma: no cover — integration-level
        webbrowser.open(f"http://localhost:{port}/ontology_viz.html")

    try:
        server.serve_forever()
    except KeyboardInterrupt:  # pragma: no cover — integration-level
        print("\nServer stopped.")
        server.server_close()
