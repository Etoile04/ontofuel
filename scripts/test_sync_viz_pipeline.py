import pytest
import os
import sys
import json
from pathlib import Path

# 确保 scripts/ 目录在路径中
sys.path.insert(0, os.path.dirname(__file__))

from sync_viz_pipeline import sync_pipeline

# 项目根目录
ROOT = Path(__file__).resolve().parent.parent
ONTOLOGY_PATH = str(ROOT / "data" / "material_ontology_enhanced.json")


def test_sync_produces_all_outputs(tmp_path):
    """管道应同时生成 NVL JSON 和 standalone HTML"""
    result = sync_pipeline(
        ontology_path=ONTOLOGY_PATH,
        nvl_output=str(tmp_path / "nvl.json"),
        html_output=str(tmp_path / "standalone.html"),
    )
    assert os.path.exists(result["nvl_path"]), "NVL 输出文件不存在"
    assert os.path.exists(result["html_path"]), "HTML 输出文件不存在"
    assert result["nodes"] > 0, "节点数应大于 0"
    assert result["relationships"] >= 0, "关系数应为非负"
    assert result["elapsed_seconds"] >= 0, "耗时应为非负"


def test_sync_nvl_is_valid_json(tmp_path):
    """生成的 NVL 应是合法 JSON 且包含 nodes/relationships"""
    result = sync_pipeline(
        ontology_path=ONTOLOGY_PATH,
        nvl_output=str(tmp_path / "nvl.json"),
        html_output=str(tmp_path / "standalone.html"),
    )
    with open(result["nvl_path"]) as f:
        nvl = json.load(f)
    assert "nodes" in nvl, "NVL 应包含 nodes 字段"
    assert "relationships" in nvl, "NVL 应包含 relationships 字段"


def test_sync_html_contains_data(tmp_path):
    """生成的 HTML 应内嵌 NVL 数据"""
    result = sync_pipeline(
        ontology_path=ONTOLOGY_PATH,
        nvl_output=str(tmp_path / "nvl.json"),
        html_output=str(tmp_path / "standalone.html"),
    )
    html = Path(result["html_path"]).read_text()
    # standalone HTML 应内嵌数据，包含 D3 和 NVL 数据
    assert "d3" in html.lower(), "HTML 应包含 D3 引用"
    assert "nodes" in html, "HTML 应包含节点数据"


def test_sync_nvl_node_count_covers_individuals(tmp_path):
    """NVL 节点数应至少覆盖本体中的 individuals"""
    result = sync_pipeline(
        ontology_path=ONTOLOGY_PATH,
        nvl_output=str(tmp_path / "nvl.json"),
        html_output=str(tmp_path / "standalone.html"),
    )
    with open(ONTOLOGY_PATH) as f:
        ont = json.load(f)
    with open(result["nvl_path"]) as f:
        nvl = json.load(f)
    # NVL nodes 应包含 individuals（可能还包含 classes 等）
    individuals_count = len(ont.get("individuals", []))
    assert len(nvl["nodes"]) >= individuals_count, (
        f"NVL 节点数 ({len(nvl['nodes'])}) 应 >= individuals 数 ({individuals_count})"
    )
