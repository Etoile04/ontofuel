# `ontofuel.visualization` — DEPRECATED

> Status: **Deprecated** as of OntoFuel v1.2 (NFM-229 D2 / NFM-231).
> The code is **retained and still functional** for backward compatibility —
> it is not removed. It will not receive new features.

## What is deprecated

The Python viewer shipped in this package:

- `start_viewer()` — an `http.server` + D3-template viewer (`templates/`).
- The `ontofuel viz` CLI command, which calls `start_viewer()`.

Both now emit a deprecation signal:

- `start_viewer()` raises a `DeprecationWarning` (via `warnings.warn`) on every
  call.
- `ontofuel viz` prints a deprecation notice to **stderr** before starting the
  server (the server still starts — behavior is unchanged).

## Why

The canonical OntoFuel viewer is the **React NVL app** in `visualization-app/`
(separate repository: `github.com/Etoile04/ontofuel-nvl-visualization`). It is
a richer, embeddable, runtime-configurable viewer and is the supported surface
going forward. Maintaining two viewers duplicates effort and drifts.

## Migration

### Development / interactive viewing

Use the React app:

```bash
cd visualization-app
npm install
npm start            # dev server
npm run build        # production static build -> visualization-app/build/
```

Point it at any NVL JSON via the runtime data source
(`?data=<URL>`, `REACT_APP_DATA_URL`, etc.) — see
[`visualization-app/EMBEDDING.md`](../../../visualization-app/EMBEDDING.md)
for the full parameter reference and priority chain.

### Production / embedding

Serve the React `build/` as static assets, or use the **Docker embed entry**
shipped in the main repo (`docker/`). The Docker setup builds the React app
and serves it behind a container — this is the recommended production path.

For NFMD site integration (iframe, CORS contract, iframe sizing, deep links),
follow [`visualization-app/EMBEDDING.md`](../../../visualization-app/EMBEDDING.md).

### If you called `start_viewer()` from Python

```python
# Before (deprecated)
from ontofuel.visualization import start_viewer
start_viewer(port=9999)
```

Replace with the React app served statically (or via Docker). There is no
Python-callable replacement — the viewer is now a standalone web app. If you
need programmatic ontology access (not visualization), use the CLI export
commands (`ontofuel export json|graphml|markdown ...`) or the `ontofuel.core`
API directly.

## Timeline

No removal date is set yet. Removal will be announced with a full release
cycle of notice after the React app + Docker embed are validated for all
existing consumers. Track via NFM-229 / NFM-231.
