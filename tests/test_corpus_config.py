"""Config for the NFMD corpus publish pipeline (NFM-251 / NFM-226 ADR §2/§3).

Env-driven, no hardcoded absolute paths. Auto-publish is opt-in (``ONTOFUEL_AUTO_PUBLISH=1``)
so extraction behavior is byte-identical until enabled (binding non-regression).
"""
from __future__ import annotations

from ontofuel.viz_corpus.config import CorpusPublishConfig


def test_default_config(monkeypatch):
    for key in ("ONTOFUEL_CORPUS_ROOT", "ONTOFUEL_CORPUS_ID", "ONTOFUEL_AUTO_PUBLISH"):
        monkeypatch.delenv(key, raising=False)
    cfg = CorpusPublishConfig.from_env()
    assert cfg.corpus_id == "ontofuel"
    assert cfg.corpus_root.name == "corpus"  # <repo>/data/corpus
    assert cfg.auto_publish is False  # opt-in (non-regressive)


def test_auto_publish_opt_in(monkeypatch):
    monkeypatch.setenv("ONTOFUEL_AUTO_PUBLISH", "1")
    assert CorpusPublishConfig.from_env().auto_publish is True


def test_corpus_id_and_root_overridable(monkeypatch):
    import os

    monkeypatch.setenv("ONTOFUEL_CORPUS_ID", "experimental")
    monkeypatch.setenv("ONTOFUEL_CORPUS_ROOT", os.path.join("/tmp", "custom_corpus_root"))
    cfg = CorpusPublishConfig.from_env()
    assert cfg.corpus_id == "experimental"
    assert cfg.corpus_root.name == "custom_corpus_root"


def test_frozen_config_is_immutable(monkeypatch):
    cfg = CorpusPublishConfig.from_env()
    try:
        cfg.corpus_id = "mutated"  # type: ignore[misc]
    except Exception:
        return
    raise AssertionError("CorpusPublishConfig must be frozen (immutable)")
