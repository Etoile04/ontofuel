#!/usr/bin/env bash
# OntoFuel Portable Packager
# Creates a self-contained zip for distribution (no Python install needed)

set -euo pipefail

VERSION=${1:-"0.1.0-alpha"}
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
DIST_DIR="${PROJECT_DIR}/dist"
PKG_NAME="ontofuel-portable-${VERSION}"
PKG_DIR="${DIST_DIR}/${PKG_NAME}"

echo "═══ OntoFuel Portable Packager ═══"
echo "Version: ${VERSION}"
echo ""

# Clean previous build
rm -rf "${PKG_DIR}"
mkdir -p "${PKG_DIR}"

# 1. Copy Python package
echo "📦 Copying Python package..."
mkdir -p "${PKG_DIR}/src/"
cp -r "${PROJECT_DIR}/src/ontofuel" "${PKG_DIR}/src/"
cp "${PROJECT_DIR}/pyproject.toml" "${PKG_DIR}/"

# 2. Copy ontology data
echo "📊 Copying ontology data..."
cp -r "${PROJECT_DIR}/ontology" "${PKG_DIR}/ontology/"

# 3. Copy visualization
echo "🎨 Copying visualization..."
mkdir -p "${PKG_DIR}/src/ontofuel/visualization/templates/"
cp "${PROJECT_DIR}/src/ontofuel/visualization/templates/ontology_viz.html" \
   "${PKG_DIR}/src/ontofuel/visualization/templates/"

# 4. Copy docs
echo "📄 Copying documentation..."
mkdir -p "${PKG_DIR}/docs/"
cp "${PROJECT_DIR}/README.md" "${PKG_DIR}/"
cp "${PROJECT_DIR}/LICENSE" "${PKG_DIR}/"

# 5. Copy tests
echo "🧪 Copying tests..."
cp -r "${PROJECT_DIR}/tests" "${PKG_DIR}/tests/"

# 6. Create start script
echo "🚀 Creating start script..."
cat > "${PKG_DIR}/start.sh" << 'START_EOF'
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Check Python3
if ! command -v python3 &>/dev/null; then
    echo "❌ Python 3.10+ is required. Install it from https://python.org"
    exit 1
fi

# Check if ontofuel is installed
if ! python3 -c "import ontofuel" 2>/dev/null; then
    echo "📦 Installing OntoFuel..."
    pip3 install -e ".[dev]" --quiet 2>/dev/null || pip install -e ".[dev]" --quiet
fi

echo ""
echo "═══ OntoFuel Quick Start ═══"
echo ""
echo "Available commands:"
echo "  ontofuel stats          # View ontology statistics"
echo "  ontofuel query 'U-10Mo' # Search materials"
echo "  ontofuel validate       # Quality assessment"
echo "  ontofuel export json out.json  # Export data"
echo "  ontofuel viz            # Start web visualization"
echo ""

# Run command if provided
if [ $# -gt 0 ]; then
    ontofuel "$@"
else
    ontofuel stats -v
fi
START_EOF
chmod +x "${PKG_DIR}/start.sh"

# 7. Create zip
echo "📦 Creating zip archive..."
cd "${DIST_DIR}"
zip -qr "${PKG_NAME}.zip" "${PKG_NAME}"

# 8. Report
SIZE=$(du -sh "${PKG_NAME}.zip" | cut -f1)
FILES=$(find "${PKG_NAME}" -type f | wc -l | tr -d ' ')

echo ""
echo "═══ Build Complete ═══"
echo "  Package: ${DIST_DIR}/${PKG_NAME}.zip"
echo "  Size:    ${SIZE}"
echo "  Files:   ${FILES}"
echo ""
echo "Usage:"
echo "  unzip ${PKG_NAME}.zip"
echo "  cd ${PKG_NAME}"
echo "  ./start.sh"
