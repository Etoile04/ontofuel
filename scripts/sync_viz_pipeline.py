#!/usr/bin/env python3
"""一键同步：本体 JSON → NVL JSON → Standalone HTML"""

import os
import sys
import json
import subprocess
import argparse
from pathlib import Path
from datetime import datetime


def find_ontology_to_nvl():
    """查找 ontology_to_nvl.py（可能在 worktree 或主仓库中）"""
    candidates = [
        Path(__file__).parent / "ontology_to_nvl.py",
        Path(__file__).resolve().parent.parent.parent / "scripts" / "ontology_to_nvl.py",
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


def ontology_to_nvl(ontology_path, nvl_output):
    """调用 ontology_to_nvl.py 生成 NVL 数据"""
    script = find_ontology_to_nvl()
    if script is None:
        raise FileNotFoundError(
            "找不到 ontology_to_nvl.py，请确保它在 scripts/ 或主仓库 scripts/ 目录中"
        )
    result = subprocess.run(
        [sys.executable, str(script), str(ontology_path), "-o", str(nvl_output)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"NVL 转换失败:\nstdout: {result.stdout}\nstderr: {result.stderr}")
    with open(nvl_output) as f:
        return json.load(f)


def fallback_nvl(nvl_output):
    """如果 ontology_to_nvl.py 不可用，使用已有的 NVL 文件"""
    root = Path(__file__).resolve().parent.parent
    existing = root / "data" / "nvl_ontology_data.json"
    if existing.exists():
        import shutil

        shutil.copy2(existing, nvl_output)
        with open(nvl_output) as f:
            return json.load(f)
    raise FileNotFoundError("无法生成 NVL：找不到 ontology_to_nvl.py 和已有 NVL 文件")


def sync_pipeline(ontology_path, nvl_output, html_output, template_path=None, d3_path=None):
    """完整同步管道，返回统计信息 dict"""
    # 延迟导入，确保 scripts/ 目录在路径中
    scripts_dir = str(Path(__file__).resolve().parent)
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    from generate_standalone_viz import generate

    start = datetime.now()

    # Step 1: 本体 → NVL
    try:
        nvl = ontology_to_nvl(ontology_path, nvl_output)
    except FileNotFoundError:
        print("⚠️  ontology_to_nvl.py 不可用，使用已有 NVL 数据")
        nvl = fallback_nvl(nvl_output)

    nodes = len(nvl.get("nodes", []))
    rels = len(nvl.get("relationships", []))

    # Step 2: 生成 standalone HTML
    root = Path(__file__).resolve().parent.parent
    if template_path is None:
        template_path = root / "ontology_viz.html"
    if d3_path is None:
        d3_path = root / "d3.v7.min.js"
    generate(Path(template_path), Path(nvl_output), Path(html_output))

    elapsed = (datetime.now() - start).total_seconds()
    return {
        "nvl_path": str(nvl_output),
        "html_path": str(html_output),
        "nodes": nodes,
        "relationships": rels,
        "elapsed_seconds": elapsed,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="一键同步本体可视化")
    parser.add_argument(
        "--ontology", default="data/material_ontology_enhanced.json", help="本体 JSON 路径"
    )
    parser.add_argument(
        "--nvl-output", default="data/nvl_ontology_data.json", help="NVL JSON 输出路径"
    )
    parser.add_argument(
        "--html-output", default="ontology_viz_standalone.html", help="Standalone HTML 输出路径"
    )
    args = parser.parse_args()

    # 相对路径基于项目根目录
    root = Path(__file__).resolve().parent.parent
    ontology = root / args.ontology if not os.path.isabs(args.ontology) else args.ontology
    nvl_out = root / args.nvl_output if not os.path.isabs(args.nvl_output) else args.nvl_output
    html_out = root / args.html_output if not os.path.isabs(args.html_output) else args.html_output

    result = sync_pipeline(str(ontology), str(nvl_out), str(html_out))
    print(
        f"✅ 同步完成！{result['nodes']} 节点, {result['relationships']} 关系, "
        f"{result['elapsed_seconds']:.1f}s"
    )
    print(f"   NVL:  {result['nvl_path']}")
    print(f"   HTML: {result['html_path']}")
