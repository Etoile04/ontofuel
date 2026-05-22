#!/usr/bin/env python3
"""Generate a fully self-contained HTML visualization file with inline D3.js and NVL data.

Reads the ontology_viz.html template and embeds D3.js library + NVL JSON data
directly into the HTML, producing a single file that can be opened by double-clicking.
"""

import json
import re
import sys
from pathlib import Path

# Resolve paths relative to project root (parent of scripts/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_PATH = PROJECT_ROOT / "ontology_viz.html"
DATA_PATH = PROJECT_ROOT / "data" / "nvl_ontology_data.json"
OUTPUT_PATH = PROJECT_ROOT / "ontology_viz_standalone.html"

# D3.js CDN fallback URLs to try downloading from
D3_CDN_URLS = [
    "https://d3js.org/d3.v7.min.js",
    "https://cdn.jsdelivr.net/npm/d3@7/dist/d3.min.js",
    "https://unpkg.com/d3@7/dist/d3.min.js",
]


def download_d3() -> str:
    """Download D3.js from CDN."""
    import urllib.request
    for url in D3_CDN_URLS:
        try:
            print(f"  Trying {url} ...")
            with urllib.request.urlopen(url, timeout=15) as resp:
                content = resp.read().decode("utf-8")
            print(f"  Downloaded D3.js ({len(content)} chars)")
            return content
        except Exception as e:
            print(f"  Failed: {e}")
    return None


def get_d3_source() -> str:
    """Get D3.js source: check local files first, then download."""
    # Check common local locations
    local_paths = [
        PROJECT_ROOT / "d3.v7.min.js",
        PROJECT_ROOT / "src" / "ontofuel" / "visualization" / "static" / "d3.v7.min.js",
        PROJECT_ROOT / "static" / "d3.v7.min.js",
    ]
    for p in local_paths:
        if p.exists():
            print(f"  Found local D3.js at {p}")
            return p.read_text(encoding="utf-8")

    print("  D3.js not found locally, downloading from CDN...")
    return download_d3()


def inline_d3(html: str, d3_source: str) -> str:
    """Replace D3.js script tags with inline script."""
    # Match various D3 script tag patterns
    patterns = [
        r'<script\s+src=["\']https?://d3js\.org/d3\.v7\.min\.js["\']\s*>\s*</script>',
        r'<script\s+src=["\']https?://cdn\.jsdelivr\.net/npm/d3@7/[^"\']*["\']\s*>\s*</script>',
        r'<script\s+src=["\']https?://unpkg\.com/d3@7/[^"\']*["\']\s*>\s*</script>',
        r'<script\s+src=["\']d3\.v7\.min\.js["\']\s*>\s*</script>',
        r'<script\s+src=["\']d3/d3\.v7\.min\.js["\']\s*>\s*</script>',
        r'<script\s+src=["\'][^"\']*d3[^"\']*\.min\.js["\']\s*>\s*</script>',
    ]
    inline_tag_open = '<script>/* D3.js v7 inline */\n'
    inline_tag_close = '\n</script>'
    for pattern in patterns:
        match = re.search(pattern, html, flags=re.IGNORECASE)
        if match:
            start, end = match.span()
            html = html[:start] + inline_tag_open + d3_source + inline_tag_close + html[end:]
            return html
    # If no pattern matched, try broader approach
    broader = r'<script\s+src=["\'][^"\']*d3[^"\']*["\']\s*>\s*</script>'
    match = re.search(broader, html, flags=re.IGNORECASE)
    if match:
        start, end = match.span()
        html = html[:start] + inline_tag_open + d3_source + inline_tag_close + html[end:]
    return html


def inline_data(html: str, data: dict) -> str:
    """Replace loadData() fetch logic with inline NVL_DATA variable."""
    data_json = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    nvl_const = f'<script>/* NVL ontology data inline */\nconst NVL_DATA = {data_json};\n</script>'

    # Find loadData function by brace matching (more reliable than regex)
    marker = "async function loadData()"
    idx = html.find(marker)
    if idx != -1:
        # Find matching closing brace
        brace_count = 0
        start_brace = html.index("{", idx)
        for i in range(start_brace, len(html)):
            if html[i] == "{":
                brace_count += 1
            elif html[i] == "}":
                brace_count -= 1
                if brace_count == 0:
                    end = i + 1
                    break
        html = html[:idx] + "async function loadData() { return NVL_DATA; }" + html[end:]

    # Insert NVL_DATA after D3 inline script
    d3_inline_marker = "/* D3.js v7 inline */"
    if d3_inline_marker in html:
        idx = html.index(d3_inline_marker)
        close_idx = html.index("</script>", idx)
        html = html[:close_idx + len("</script>")] + "\n" + nvl_const + html[close_idx + len("</script>"):]
    else:
        head_close = html.find("</head>")
        if head_close != -1:
            html = html[:head_close] + nvl_const + "\n" + html[head_close:]

    return html



def inline_fuse(html: str, fuse_source: str) -> str:
    """Replace fuse.min.js script tags with inline script."""
    patterns = [
        r'<script\s+src=["\']fuse\.min\.js["\']\s*>\s*</script>',
        r'<script\s+src=["\'][^"\']*fuse[^"\']*\.min\.js["\']\s*>\s*</script>',
    ]
    inline_tag_open = '<script>/* Fuse.js inline */\n'
    inline_tag_close = '\n</script>'
    for pattern in patterns:
        match = re.search(pattern, html, flags=re.IGNORECASE)
        if match:
            start, end = match.span()
            html = html[:start] + inline_tag_open + fuse_source + inline_tag_close + html[end:]
            return html
    return html

def generate(
    template_path: Path = TEMPLATE_PATH,
    data_path: Path = DATA_PATH,
    output_path: Path = OUTPUT_PATH,
) -> Path:
    """Generate standalone HTML visualization."""
    print(f"Reading template: {template_path}")
    if not template_path.exists():
        raise FileNotFoundError(f"Template not found: {template_path}")
    html = template_path.read_text(encoding="utf-8")
    print(f"  Template size: {len(html)} chars")

    print("Getting D3.js source...")
    d3_source = get_d3_source()
    if not d3_source:
        raise RuntimeError("Could not obtain D3.js source. Download failed and no local copy found.")
    print(f"  D3.js size: {len(d3_source)} chars")

    print(f"Reading data: {data_path}")
    if not data_path.exists():
        raise FileNotFoundError(f"Data file not found: {data_path}")
    data = json.loads(data_path.read_text(encoding="utf-8"))
    print(f"  Data: {len(data.get('nodes', []))} nodes, {len(data.get('relationships', []))} relationships")

    print("Inlining D3.js...")
    html = inline_d3(html, d3_source)

    # Inline Fuse.js if referenced
    fuse_local = template_path.parent / "fuse.min.js"
    if fuse_local.exists() and "fuse.min.js" in html:
        print("Inlining Fuse.js...")
        fuse_source = fuse_local.read_text(encoding="utf-8")
        html = inline_fuse(html, fuse_source)

    print("Inlining NVL data...")
    html = inline_data(html, data)

    print(f"Writing output: {output_path}")
    output_path.write_text(html, encoding="utf-8")
    size_kb = len(html.encode("utf-8")) / 1024
    print(f"  Output size: {size_kb:.0f} KB")
    print("Done! ✓")

    return output_path


if __name__ == "__main__":
    generate()
