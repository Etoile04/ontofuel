"""Tests for potentials provider federation."""
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.ontofuel.database.providers import (
    FederatedPotentialProvider,
    LocalPotentialProvider,
    OpenKIMPotentialProvider,
    PotentialDetail,
    PotentialSummary,
)


@pytest.mark.unit
class TestPotentialModels:
    """Test potential data models."""

    def test_potential_summary_validation(self):
        """Test PotentialSummary validates required fields."""
        summary = PotentialSummary(
            id="kim_1234567890",
            title="EAM potential for Cu",
            element=["Cu"],
            functional_form="EAM",
            provider="local",
        )
        assert summary.id == "kim_1234567890"
        assert summary.provider == "local"

    def test_potential_detail_validation(self):
        """Test PotentialDetail includes all required fields."""
        detail = PotentialDetail(
            id="kim_1234567890",
            title="EAM potential for Cu",
            element=["Cu"],
            functional_form="EAM",
            provider="openkim",
            citation="Author et al. (2020)",
            description="Embedded atom method potential",
        )
        assert detail.provider == "openkim"
        assert detail.description is not None


@pytest.mark.unit
class TestLocalProvider:
    """Test local PostgreSQL provider."""

    def test_list_potentials_empty(self, mock_db_empty):
        """Test listing potentials when database is empty."""
        provider = LocalPotentialProvider()
        results = provider.list_potentials(limit=10)
        assert results == []

    def test_get_potential_by_id_not_found(self, mock_db_empty):
        """Test getting non-existent potential returns None."""
        provider = LocalPotentialProvider()
        result = provider.get_potential("kim_nonexistent")
        assert result is None

    @pytest.mark.integration
    def test_list_potentials_from_db(self, test_db_with_potentials):
        """Test listing potentials from actual database."""
        provider = LocalPotentialProvider()
        results = provider.list_potentials(limit=10)
        assert len(results) > 0
        assert all(r.provider == "local" for r in results)


@pytest.mark.unit
class TestOpenKIMProvider:
    """Test OpenKIM provider."""

    def test_list_potential_success(self, mock_openkim_api):
        """Test successful listing from OpenKIM."""
        provider = OpenKIMPotentialProvider(api_key="test_key")
        results = provider.list_potentials(limit=5)
        assert len(results) > 0
        assert all(r.provider == "openkim" for r in results)

    def test_get_potential_by_id_success(self, mock_openkim_api):
        """Test getting specific potential from OpenKIM."""
        provider = OpenKIMPotentialProvider(api_key="test_key")
        result = provider.get_potential("kim_1234567890")
        assert result is not None
        assert result.id == "kim_1234567890"
        assert result.provider == "openkim"

    def test_openkim_unreachable_degrades_gracefully(self):
        """Test OpenKIM outage returns empty list, not exception."""
        provider = OpenKIMPotentialProvider(api_key="test_key")
        with patch("requests.get", side_effect=Exception("Network error")):
            results = provider.list_potentials(limit=10)
            assert results == []  # Graceful degradation, not crash

    def test_openkim_timeout_returns_empty(self):
        """Test OpenKIM timeout returns empty list."""
        provider = OpenKIMPotentialProvider(api_key="test_key")
        with patch("requests.get", side_effect=TimeoutError("Request timeout")):
            results = provider.list_potentials(limit=10)
            assert results == []


@pytest.mark.unit
class TestFederatedProvider:
    """Test federated provider combining local + OpenKIM."""

    def test_federated_list_combines_providers(self, mock_db_with_potentials, mock_openkim_api):
        """Test federated list merges results from both providers."""
        local = LocalPotentialProvider()
        openkim = OpenKIMPotentialProvider(api_key="test_key")
        federated = FederatedPotentialProvider(local=local, openkim=openkim)

        results = federated.list_potentials(limit=20)
        # Should have results from both providers
        providers = {r.provider for r in results}
        assert providers == {"local", "openkim"}

    def test_federated_degrades_to_local_on_openkim_failure(self, mock_db_with_potentials):
        """Test federated falls back to local when OpenKIM fails."""
        local = LocalPotentialProvider()
        openkim = OpenKIMPotentialProvider(api_key="test_key")
        federated = FederatedPotentialProvider(local=local, openkim=openkim)

        with patch("requests.get", side_effect=Exception("OpenKIM down")):
            results = federated.list_potentials(limit=20)
            # Should only have local results, no crash
            assert all(r.provider == "local" for r in results)
            assert len(results) > 0  # Local still works

    def test_federated_get_by_id_local_priority(self, mock_db_with_potentials):
        """Test federated get prioritizes local over OpenKIM."""
        local = LocalPotentialProvider()
        openkim = OpenKIMPotentialProvider(api_key="test_key")
        federated = FederatedPotentialProvider(local=local, openkim=openkim)

        # If ID exists in local, return it (local priority)
        result = federated.get_potential("1")
        assert result is not None
        assert result.provider == "local"
        assert result.title == "Cu EAM"


@pytest.fixture
def mock_db_empty():
    """Mock empty database response."""
    with patch("src.ontofuel.database.providers.LocalPotentialProvider.get_conn") as mock_get_conn:
        # Create a properly mocked connection context manager
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_cursor.fetchone.return_value = None

        # Setup the context manager chain
        mock_conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = Mock(return_value=False)
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=False)

        mock_get_conn.return_value = mock_conn
        yield mock_get_conn


@pytest.fixture
def mock_db_with_potentials():
    """Mock database with sample potentials."""
    with patch("src.ontofuel.database.providers.LocalPotentialProvider.get_conn") as mock_get_conn:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ("1", "Cu EAM", '["Cu"]', "EAM", "2024-01-01"),
        ]
        # Detail query returns: id, title, elements, functional_form, citation, description, notes
        mock_cursor.fetchone.return_value = (
            "1", "Cu EAM", '["Cu"]', "EAM", "Author et al.", "Test potential", None
        )

        # Setup the context manager chain
        mock_conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = Mock(return_value=False)
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=False)

        mock_get_conn.return_value = mock_conn
        yield mock_get_conn


@pytest.fixture
def mock_openkim_api():
    """Mock OpenKIM API responses."""
    with patch("requests.get") as mock_get:
        def mock_response(url, **kwargs):
            """Dynamic mock response based on URL."""
            mock_resp = Mock()
            mock_resp.status_code = 200
            mock_resp.raise_for_status = Mock()

            if "/kimcodes" in url and "kim_1234567890" not in url:
                # List endpoint
                mock_resp.json.return_value = {
                    "kimcodes": ["kim_1234567890", "kim_0987654321"],
                    "contributor": "Test Lab",
                }
            elif "kim_1234567890" in url:
                # Detail endpoint
                mock_resp.json.return_value = {
                    "kimcode": "kim_1234567890",
                    "title": "Test KIM Potential",
                    "functional_form": "EAM",
                    "citation": "Test Author et al.",
                    "description": "Test potential for unit tests",
                    "contributor": "Test Lab",
                }
            else:
                mock_resp.json.return_value = {}

            return mock_resp

        mock_get.side_effect = mock_response
        yield mock_get


@pytest.fixture
def test_db_with_potentials():
    """Fixture for integration tests with real database."""
    import os

    from src.ontofuel.database.providers import LocalPotentialProvider
    from src.ontofuel.database.schema import generate_create_sql

    database_url = os.environ.get("DATABASE_URL", "postgresql://postgres:password@localhost:5432/postgres")

    # Create potentials table
    provider = LocalPotentialProvider(database_url=database_url)
    try:
        with provider.get_conn() as conn, conn.cursor() as cur:
            cur.execute(generate_create_sql("potentials"))
            # Insert test data
            cur.execute(
                "INSERT INTO potentials (id, title, elements, functional_form) "
                "VALUES (%s, %s, %s, %s)",
                ("test-id-1", "Test Potential", '["Cu"]', "EAM"),
            )
            conn.commit()
        yield provider

        # Cleanup
        with provider.get_conn() as conn, conn.cursor() as cur:
            cur.execute("DROP TABLE IF EXISTS potentials")
            conn.commit()
    except Exception as e:
        pytest.skip(f"Database not available: {e}")
