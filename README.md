# OntoFuel 🏗️

**Ontology-driven knowledge extraction and management system for nuclear materials science.**

## Overview

OntoFuel is a comprehensive system for:
- 📊 **Ontology Management** — 139 classes, 755 individuals, A+ quality score
- 🔍 **Knowledge Extraction** — Extract structured data from literature (200-2000 pages)
- 👁️ **Interactive Visualization** — D3.js force-directed graph (915 nodes + 1048 relationships)
- 🗄️ **Database Storage** — Supabase (PostgreSQL) with REST API
- 📤 **Multi-format Export** — JSON, CSV, Turtle, GraphML

## Quick Start

### Portable (No Installation)

```bash
# Download and extract
unzip ontofuel-portable-latest.zip
cd ontofuel-portable

# Start (Mac/Linux)
./start.sh

# Start (Windows)
start.bat
```

Browser opens automatically at http://localhost:9999

### Docker Compose (Full Stack)

```bash
git clone https://github.com/Etoile04/ontofuel.git
cd ontofuel
docker compose up -d
./tools/restore.sh
```

### Python Package

```bash
pip install ontofuel
ontofuel viz --port 9999
```

## Features

- ✅ Zero Python dependencies (all stdlib)
- ✅ Interactive ontology visualization
- ✅ Real-time search and filtering
- ✅ Multi-format export (JSON/CSV/Turtle/GraphML)
- ✅ Ontology quality validation (5-dimension scoring)
- ✅ Supabase integration with REST API
- ✅ Docker deployment ready

## Documentation

See [docs/](docs/) for detailed guides.

## License

MIT
