"""Provider abstraction for federated potential data access.

Supports local PostgreSQL and OpenKIM repository as data sources.
"""
from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from contextlib import contextmanager

import psycopg2
import requests
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------


class PotentialSummary(BaseModel):
    """Summary view of a potential for list views."""

    id: str = Field(
        ..., description="Unique identifier (KIM code for OpenKIM, UUID for local)"
    )
    title: str = Field(..., description="Potential title/name")
    element: list[str] = Field(
        default_factory=list, description="Element(s) this potential applies to"
    )
    functional_form: str | None = Field(None, description="Functional form (EAM, MEAM, etc.)")
    provider: str = Field(..., description="Data provider: 'local' or 'openkim'")


class PotentialDetail(BaseModel):
    """Full details of a potential."""

    id: str
    title: str
    element: list[str] = Field(default_factory=list)
    functional_form: str | None = None
    provider: str
    citation: str | None = Field(None, description="Citation information")
    description: str | None = Field(None, description="Detailed description")
    notes: str | None = Field(None, description="Additional notes")
    metadata: dict = Field(
        default_factory=dict, description="Additional provider-specific metadata"
    )


# ---------------------------------------------------------------------------
# Provider Interface
# ---------------------------------------------------------------------------


class PotentialProvider(ABC):
    """Abstract base for potential data providers."""

    @abstractmethod
    def list_potentials(self, limit: int = 100, offset: int = 0) -> list[PotentialSummary]:
        """List available potentials.

        Args:
            limit: Maximum number of results to return
            offset: Number of results to skip

        Returns:
            List of potential summaries
        """
        ...

    @abstractmethod
    def get_potential(self, potential_id: str) -> PotentialDetail | None:
        """Get detailed information about a specific potential.

        Args:
            potential_id: Unique identifier for the potential

        Returns:
            Potential detail if found, None otherwise
        """
        ...


# ---------------------------------------------------------------------------
# Local PostgreSQL Provider
# ---------------------------------------------------------------------------


class LocalPotentialProvider(PotentialProvider):
    """PostgreSQL-backed potential provider."""

    def __init__(self, database_url: str | None = None):
        """Initialize provider.

        Args:
            database_url: PostgreSQL connection string.
                Defaults to DATABASE_URL env var or localhost.
        """
        import os

        self.database_url = database_url or os.environ.get(
            "DATABASE_URL",
            "postgresql://postgres:password@localhost:5432/postgres",
        )

    @contextmanager
    def get_conn(self):
        """Yield a psycopg2 connection; commit on success, rollback on error."""
        conn = psycopg2.connect(self.database_url)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def list_potentials(self, limit: int = 100, offset: int = 0) -> list[PotentialSummary]:
        """List potentials from local database."""
        try:
            with self.get_conn() as conn, conn.cursor() as cur:
                cur.execute(
                    "SELECT id, title, elements, functional_form FROM potentials "
                    "ORDER BY title LIMIT %s OFFSET %s",
                    (limit, offset),
                )
                rows = cur.fetchall()
                return [
                    PotentialSummary(
                        id=str(r[0]),
                        title=r[1],
                        element=json.loads(r[2]) if r[2] else [],
                        functional_form=r[3],
                        provider="local",
                    )
                    for r in rows
                ]
        except Exception as e:
            logger.error(f"Local provider list failed: {e}")
            return []  # Graceful degradation

    def get_potential(self, potential_id: str) -> PotentialDetail | None:
        """Get potential detail from local database."""
        try:
            with self.get_conn() as conn, conn.cursor() as cur:
                cur.execute(
                    "SELECT id, title, elements, functional_form, citation, description, notes "
                    "FROM potentials WHERE id = %s",
                    (potential_id,),
                )
                r = cur.fetchone()
                if not r:
                    return None
                return PotentialDetail(
                    id=str(r[0]),
                    title=r[1],
                    element=json.loads(r[2]) if r[2] else [],
                    functional_form=r[3],
                    provider="local",
                    citation=r[4],
                    description=r[5],
                    notes=r[6],
                )
        except Exception as e:
            logger.error(f"Local provider get failed: {e}")
            return None


# ---------------------------------------------------------------------------
# OpenKIM Provider
# ---------------------------------------------------------------------------


class OpenKIMPotentialProvider(PotentialProvider):
    """OpenKIM repository provider.

    Fetches potentials from the OpenKIM repository API.
    Implements caching and graceful degradation.
    """

    def __init__(
        self,
        api_key: str | None = None,
        cache_ttl_seconds: int = 300,  # 5 minutes default
        base_url: str = "https://query.openkim.org",
    ):
        """Initialize OpenKIM provider.

        Args:
            api_key: OpenKIM API key (if required)
            cache_ttl_seconds: Cache TTL for responses
            base_url: OpenKIM API base URL
        """
        self.api_key = api_key
        self.cache_ttl_seconds = cache_ttl_seconds
        self.base_url = base_url
        self._cache: dict[str, tuple[list[PotentialSummary], float]] = {}

    def _is_cache_valid(self, timestamp: float) -> bool:
        """Check if cache entry is still valid."""
        import time

        return time.time() - timestamp < self.cache_ttl_seconds

    def list_potentials(self, limit: int = 100, offset: int = 0) -> list[PotentialSummary]:
        """List potentials from OpenKIM with caching."""
        cache_key = f"list_{limit}_{offset}"

        # Check cache
        if cache_key in self._cache:
            cached_data, timestamp = self._cache[cache_key]
            if self._is_cache_valid(timestamp):
                return cached_data

        # Fetch from OpenKIM
        try:
            response = requests.get(
                f"{self.base_url}/kimcodes",
                params={"limit": limit, "offset": offset},
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()

            # Map to PotentialSummary
            summaries = self._map_openkim_to_summaries(data)

            # Cache the result
            import time

            self._cache[cache_key] = (summaries, time.time())

            return summaries

        except Exception as e:
            logger.warning(f"OpenKIM provider list failed: {e}")
            return []  # Graceful degradation

    def get_potential(self, potential_id: str) -> PotentialDetail | None:
        """Get potential detail from OpenKIM."""
        cache_key = f"detail_{potential_id}"

        # Check cache
        if cache_key in self._cache:
            # Note: caching details as list for consistency with list cache structure
            cached_list, timestamp = self._cache[cache_key]
            if self._is_cache_valid(timestamp) and cached_list:
                return cached_list[0]

        try:
            response = requests.get(
                f"{self.base_url}/kimcodes/{potential_id}",
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()

            detail = self._map_openkim_to_detail(data)

            # Cache the result
            import time

            self._cache[cache_key] = ([detail], time.time())

            return detail

        except Exception as e:
            logger.warning(f"OpenKIM provider get failed: {e}")
            return None  # Graceful degradation

    def _map_openkim_to_summaries(self, data: dict) -> list[PotentialSummary]:
        """Map OpenKIM API response to PotentialSummary list."""
        summaries = []
        for kimcode in data.get("kimcodes", []):
            # Parse KIM code to extract elements if available
            elements = self._extract_elements_from_kimcode(kimcode)

            summaries.append(
                PotentialSummary(
                    id=kimcode,
                    title=f"KIM Code {kimcode}",
                    element=elements,
                    functional_form=None,  # Would need detail call
                    provider="openkim",
                )
            )

        return summaries

    def _map_openkim_to_detail(self, data: dict) -> PotentialDetail:
        """Map OpenKIM API response to PotentialDetail."""
        kimcode = data.get("kimcode", "")

        return PotentialDetail(
            id=kimcode,
            title=data.get("title", f"KIM Code {kimcode}"),
            element=self._extract_elements_from_kimcode(kimcode),
            functional_form=data.get("functional_form"),
            provider="openkim",
            citation=data.get("citation"),
            description=data.get("description"),
            notes=data.get("notes"),
            metadata={"contributor": data.get("contributor")},
        )

    def _extract_elements_from_kimcode(self, kimcode: str) -> list[str]:
        """Extract element symbols from KIM code.

        KIM codes follow pattern like "MO_1234567890_1234567"
        where the first part may encode elements.
        This is a placeholder implementation.
        """
        # Simple extraction: common elements in KIM codes
        common_elements = ["Cu", "Ag", "Au", "Ni", "Pd", "Pt", "Al", "Pb", "Fe", "Mo", "W"]

        # Try to parse from kimcode if it contains element hints
        # This is a simplified version - real implementation would use KIM API
        for elem in common_elements:
            if elem in kimcode.upper():
                return [elem]

        return []


# ---------------------------------------------------------------------------
# Federated Provider
# ---------------------------------------------------------------------------


class FederatedPotentialProvider(PotentialProvider):
    """Federated provider combining local and OpenKIM sources.

    Priority:
    1. Local provider (first for listing, priority for get by ID)
    2. OpenKIM provider (graceful degradation on failure)

    Read-only: No write-back to OpenKIM.
    """

    def __init__(
        self,
        local: LocalPotentialProvider | None = None,
        openkim: OpenKIMPotentialProvider | None = None,
    ):
        """Initialize federated provider.

        Args:
            local: Local PostgreSQL provider (created if None)
            openkim: OpenKIM provider (created if None)
        """
        self.local = local or LocalPotentialProvider()
        self.openkim = openkim or OpenKIMPotentialProvider()

    def list_potentials(self, limit: int = 100, offset: int = 0) -> list[PotentialSummary]:
        """List potentials from both providers.

        Returns combined results with provider field indicating source.
        Gracefully degrades to local-only if OpenKIM fails.
        """
        # Get local results
        local_results = self.local.list_potentials(limit=limit, offset=offset)

        # Get OpenKIM results (may fail gracefully)
        openkim_limit = max(10, limit // 2)  # Reserve half for OpenKIM
        openkim_results = self.openkim.list_potentials(limit=openkim_limit, offset=0)

        # Combine and return
        return local_results + openkim_results

    def get_potential(self, potential_id: str) -> PotentialDetail | None:
        """Get potential detail.

        Priority: Local first, then OpenKIM.
        Returns None if not found in either.
        """
        # Try local first
        result = self.local.get_potential(potential_id)
        if result:
            return result

        # Fallback to OpenKIM
        return self.openkim.get_potential(potential_id)


# ---------------------------------------------------------------------------
# Convenience function
# ---------------------------------------------------------------------------


def create_provider(
    provider_type: str = "federated",
    database_url: str | None = None,
    openkim_api_key: str | None = None,
    cache_ttl_seconds: int = 300,
) -> PotentialProvider:
    """Factory function to create a potential provider.

    Args:
        provider_type: Type of provider ("local", "openkim", "federated")
        database_url: PostgreSQL URL for local provider
        openkim_api_key: API key for OpenKIM provider
        cache_ttl_seconds: Cache TTL for OpenKIM responses

    Returns:
        Configured provider instance
    """
    if provider_type == "local":
        return LocalPotentialProvider(database_url=database_url)

    if provider_type == "openkim":
        return OpenKIMPotentialProvider(
            api_key=openkim_api_key,
            cache_ttl_seconds=cache_ttl_seconds,
        )

    if provider_type == "federated":
        local = LocalPotentialProvider(database_url=database_url)
        openkim = OpenKIMPotentialProvider(
            api_key=openkim_api_key,
            cache_ttl_seconds=cache_ttl_seconds,
        )
        return FederatedPotentialProvider(local=local, openkim=openkim)

    raise ValueError(f"Unknown provider type: {provider_type}")
