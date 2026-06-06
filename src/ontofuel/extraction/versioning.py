"""Git-style version control for extracted ontologies.

Provides content-addressable versioning with SHA-256 hashing, semantic
versioning, branch/merge support, and history tracking.  All version
metadata is persisted in a single ``versions.json`` file (D006 decision).

Zero runtime dependencies — only the Python standard library is used.

Classes:
    OntologyVersion: Immutable snapshot of a single ontology version.
    OntologyVersionControl: Full VCS operations (commit, checkout, log, diff, branch, merge).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class OntologyVersion:
    """A single ontology version snapshot.

    Attributes:
        hash: SHA-256 content hash, first 16 hex chars.
        parent_hashes: Hashes of parent versions (lineage tracking).
        version: Semantic version string (MAJOR.MINOR.PATCH).
        created_at: ISO-8601 timestamp of creation.
        message: Human-readable commit message.
        author: Author identifier.
        changes: Counts of added/removed classes, properties, individuals.
    """

    hash: str
    parent_hashes: list[str] = field(default_factory=list)
    version: str = "1.0.0"
    created_at: str = ""
    message: str = ""
    author: str = ""
    changes: dict[str, int] = field(default_factory=dict)


class OntologyVersionControl:
    """Git-style version control for an extracted ontology.

    Versions are stored in ``versions_dir/versions.json``.  Individual
    ontology snapshots are saved as ``<hash>.json`` alongside it so that
    ``checkout`` and ``diff`` can reconstruct any historical state.

    Version bumping rules (D006):
    - Removing classes or properties → MAJOR (x.0.0)
    - Adding classes or properties → MINOR (0.x.0)
    - Only individuals changed       → PATCH (0.0.x)
    """

    def __init__(self, ontology_path: Path, versions_dir: Path | None = None) -> None:
        self.ontology_path = ontology_path
        self.versions_dir = versions_dir or ontology_path.parent / "versions"
        self.versions_dir.mkdir(parents=True, exist_ok=True)

        self.versions_file = self.versions_dir / "versions.json"
        self.current_version: dict[str, Any] | None = self._load_current_version()
        self.versions_history: dict[str, OntologyVersion] = self._load_versions_history()

    # -- internal helpers ---------------------------------------------------

    def _compute_hash(self, ontology: dict[str, Any]) -> str:
        content = json.dumps(ontology, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _load_current_version(self) -> dict[str, Any] | None:
        if not self.ontology_path.exists():
            return None
        with open(self.ontology_path, encoding="utf-8") as f:
            return json.load(f)

    def _load_versions_history(self) -> dict[str, OntologyVersion]:
        if not self.versions_file.exists():
            return {}
        with open(self.versions_file, encoding="utf-8") as f:
            data = json.load(f)
        return {k: OntologyVersion(**v) for k, v in data.items()}

    def _save_versions_history(self) -> None:
        data = {k: asdict(v) for k, v in self.versions_history.items()}
        with open(self.versions_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    @staticmethod
    def _calculate_changes(
        old_onto: dict[str, Any] | None,
        new_onto: dict[str, Any],
    ) -> dict[str, int]:
        if old_onto is None:
            return {
                "classes_added": len(new_onto.get("classes", {})),
                "properties_added": (
                    len(new_onto.get("objectProperties", {}))
                    + len(new_onto.get("datatypeProperties", {}))
                ),
                "individuals_added": len(new_onto.get("individuals", {})),
                "classes_removed": 0,
                "properties_removed": 0,
                "individuals_removed": 0,
            }

        old_classes = set(old_onto.get("classes", {}))
        new_classes = set(new_onto.get("classes", {}))
        old_props = set(old_onto.get("objectProperties", {}))
        new_props = set(new_onto.get("objectProperties", {}))
        old_inds = set(old_onto.get("individuals", {}))
        new_inds = set(new_onto.get("individuals", {}))

        return {
            "classes_added": len(new_classes - old_classes),
            "classes_removed": len(old_classes - new_classes),
            "properties_added": len(new_props - old_props),
            "properties_removed": len(old_props - new_props),
            "individuals_added": len(new_inds - old_inds),
            "individuals_removed": len(old_inds - new_inds),
        }

    @staticmethod
    def _upgrade_version(current_version: str, changes: dict[str, int]) -> str:
        if not current_version:
            return "1.0.0"
        parts = current_version.split(".")
        if len(parts) != 3:
            return "1.0.0"
        major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])

        if changes.get("classes_removed", 0) > 0 or changes.get("properties_removed", 0) > 0:
            major += 1
            minor = 0
            patch = 0
        elif changes.get("classes_added", 0) > 0 or changes.get("properties_added", 0) > 0:
            minor += 1
            patch = 0
        else:
            patch += 1

        return f"{major}.{minor}.{patch}"

    # -- public API ---------------------------------------------------------

    def commit(
        self,
        message: str = "",
        author: str = "OntoFuel Extractor",
        ontology_data: dict[str, Any] | None = None,
    ) -> OntologyVersion:
        """Commit a new ontology version.

        If *ontology_data* is ``None`` the current on-disk ontology is used.
        Returns the created (or existing) ``OntologyVersion``.
        """
        if ontology_data is None:
            ontology_data = self._load_current_version()
        if ontology_data is None:
            raise ValueError("本体数据为空")

        new_hash = self._compute_hash(ontology_data)

        if new_hash in self.versions_history:
            return self.versions_history[new_hash]

        parent_hashes: list[str] = []
        old_onto: dict[str, Any] | None = None

        if self.current_version and "metadata" in self.current_version:
            parent_hash = self.current_version["metadata"].get("hash")
            if parent_hash:
                parent_hashes.append(parent_hash)
                old_onto = self.current_version

        changes = self._calculate_changes(old_onto, ontology_data)

        if old_onto is None:
            new_version = "1.0.0"
        else:
            cur_ver = (
                self.current_version.get("metadata", {}).get("version", "1.0.0")
                if self.current_version
                else "1.0.0"
            )
            new_version = self._upgrade_version(cur_ver, changes)

        version_record = OntologyVersion(
            hash=new_hash,
            parent_hashes=parent_hashes,
            version=new_version,
            created_at=datetime.now().isoformat(),
            message=message,
            author=author,
            changes=changes,
        )

        # Embed metadata in ontology
        ontology_data.setdefault("metadata", {})
        ontology_data["metadata"]["hash"] = new_hash
        ontology_data["metadata"]["version"] = new_version
        ontology_data["metadata"]["parent_hashes"] = parent_hashes
        ontology_data["metadata"]["created_at"] = version_record.created_at

        # Persist ontology snapshot
        with open(self.ontology_path, "w", encoding="utf-8") as f:
            json.dump(ontology_data, f, indent=2, ensure_ascii=False)

        snapshot_path = self.versions_dir / f"{new_hash}.json"
        with open(snapshot_path, "w", encoding="utf-8") as f:
            json.dump(ontology_data, f, indent=2, ensure_ascii=False)

        self.versions_history[new_hash] = version_record
        self._save_versions_history()
        self.current_version = ontology_data

        return version_record

    def checkout(self, version_hash: str) -> dict[str, Any]:
        """Restore ontology to a historical version identified by *version_hash*."""
        if version_hash not in self.versions_history:
            raise ValueError(f"版本 {version_hash} 不存在")

        version_file = self.versions_dir / f"{version_hash}.json"
        if not version_file.exists():
            raise FileNotFoundError(f"版本文件 {version_file} 不存在")

        with open(version_file, encoding="utf-8") as f:
            ontology = json.load(f)

        with open(self.ontology_path, "w", encoding="utf-8") as f:
            json.dump(ontology, f, indent=2, ensure_ascii=False)

        self.current_version = ontology
        return ontology

    def log(self, limit: int = 10) -> list[OntologyVersion]:
        """Return version history sorted newest-first, up to *limit* entries."""
        sorted_versions = sorted(
            self.versions_history.values(),
            key=lambda v: v.created_at,
            reverse=True,
        )
        return sorted_versions[:limit]

    def diff(self, hash1: str, hash2: str) -> dict[str, Any]:
        """Compare two versions and return a structured diff report."""
        if hash1 not in self.versions_history or hash2 not in self.versions_history:
            raise ValueError("版本不存在")

        v1 = self.versions_history[hash1]
        v2 = self.versions_history[hash2]

        with open(self.versions_dir / f"{hash1}.json") as f:
            onto1 = json.load(f)
        with open(self.versions_dir / f"{hash2}.json") as f:
            onto2 = json.load(f)

        return {
            "version1": {"hash": hash1, "version": v1.version, "date": v1.created_at},
            "version2": {"hash": hash2, "version": v2.version, "date": v2.created_at},
            "changes": self._calculate_changes(onto1, onto2),
        }

    def branch(self, branch_name: str) -> str:
        """Create a named branch as a copy of the current ontology."""
        if self.current_version is None:
            raise ValueError("没有当前版本")

        branch_path = self.versions_dir / f"branch_{branch_name}.json"
        with open(branch_path, "w", encoding="utf-8") as f:
            json.dump(self.current_version, f, indent=2, ensure_ascii=False)

        return str(branch_path)

    def merge(self, branch_name: str, message: str = "") -> OntologyVersion:
        """Merge a branch into the current version using union semantics."""
        branch_path = self.versions_dir / f"branch_{branch_name}.json"
        if not branch_path.exists():
            raise FileNotFoundError(f"分支 {branch_name} 不存在")

        with open(branch_path, encoding="utf-8") as f:
            branch_ontology = json.load(f)

        cur = self.current_version or {}
        merged: dict[str, Any] = {
            "classes": {
                **cur.get("classes", {}),
                **branch_ontology.get("classes", {}),
            },
            "objectProperties": {
                **cur.get("objectProperties", {}),
                **branch_ontology.get("objectProperties", {}),
            },
            "datatypeProperties": {
                **cur.get("datatypeProperties", {}),
                **branch_ontology.get("datatypeProperties", {}),
            },
            "individuals": {
                **cur.get("individuals", {}),
                **branch_ontology.get("individuals", {}),
            },
        }

        return self.commit(message=message or f"合并分支: {branch_name}", ontology_data=merged)
