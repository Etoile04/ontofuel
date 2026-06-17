"""NFMD corpus publish pipeline (NFM-251 / NFM-226 ADR §2/§3).

A standalone, idempotent ``publish_corpus()`` orchestrates the proven chain::

    OntologyToNVLConverter -> validate_contract() -> viz_sync --check
    -> atomic publish of {corpus_id}/ontology.nvl.json + manifest.json

The extraction flow invokes it fire-and-forget (swallow + alert) so a publish
failure can never fail an extraction. No daemon, no backend API (Tier A static
manifest per NFM-226 ADR §2/§3).
"""
