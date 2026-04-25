#!/usr/bin/env python3
"""
本体升华机制 - 借鉴 OntoCast 的本体/事实分离

核心功能：
- 自动分离本体概念（schema）和具体实例（facts）
- 本体可跨 chunks 复用
- 事实独立管理
- 支持 SPARQL 查询

版本：v1.0.0
创建：2026-03-07
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Tuple, Set, Any
from collections import defaultdict


class OntologySublimator:
    """本体升华器 - 分离本体和事实"""
    
    def __init__(self):
        self.ontology_triples = []  # 本体三元组
        self.fact_triples = []      # 事实三元组
        self.chunk_pattern = re.compile(r'chunk_\d+|cd:')  # chunk IRI 模式
    
    def is_fact_triple(self, subject: str) -> bool:
        """
        判断是否为事实三元组
        
        规则：
        - 主体包含 chunk IRI → 事实
        - 否则 → 本体
        
        Args:
            subject: 三元组的主体
        
        Returns:
            bool: 是否为事实
        """
        # 检查是否包含 chunk 标识
        if 'chunk_' in subject or subject.startswith('cd:'):
            return True
        
        # 检查是否为个体（通常包含具体值）
        if any(char.isdigit() for char in subject):
            # 排除版本号等
            if not re.search(r'v\d+\.\d+\.\d+', subject):
                return True
        
        return False
    
    def separate_ontology_facts(self, extraction_data: Dict) -> Tuple[Dict, Dict]:
        """
        分离本体和事实
        
        Args:
            extraction_data: 提取的数据
        
        Returns:
            (ontology, facts): 本体和事实
        """
        ontology = {
            "classes": {},
            "objectProperties": {},
            "datatypeProperties": {}
        }
        
        facts = {
            "individuals": {},
            "propertyValues": {},
            "relations": {}
        }
        
        # 分类类（都是本体）
        if "classes" in extraction_data:
            ontology["classes"] = extraction_data["classes"]
        
        # 分类属性（都是本体）
        if "objectProperties" in extraction_data:
            ontology["objectProperties"] = extraction_data["objectProperties"]
        
        if "datatypeProperties" in extraction_data:
            ontology["datatypeProperties"] = extraction_data["datatypeProperties"]
        
        # 分类个体（都是事实）
        if "individuals" in extraction_data:
            for ind_name, ind_def in extraction_data["individuals"].items():
                # 判断是否包含 chunk 标识
                if self.is_fact_triple(ind_name):
                    facts["individuals"][ind_name] = ind_def
                else:
                    # 如果个体是通用概念，归入本体
                    ontology["classes"][ind_name] = {
                        "comment": ind_def.get("label", ""),
                        "type": "owl:Class"
                    }
        
        return ontology, facts
    
    def sublimate(self, 
                 merged_data: Dict,
                 source_chunks: List[str] = None) -> Dict[str, Any]:
        """
        升华合并数据
        
        Args:
            merged_data: 合并后的数据
            source_chunks: 来源 chunk 列表
        
        Returns:
            升华结果
        """
        ontology, facts = self.separate_ontology_facts(merged_data)
        
        # 添加元数据
        ontology["metadata"] = {
            "type": "ontology",
            "source": "sublimated",
            "reusable": True,
            "chunks": source_chunks or []
        }
        
        facts["metadata"] = {
            "type": "facts",
            "source": "sublimated",
            "reusable": False,
            "chunks": source_chunks or []
        }
        
        # 统计
        stats = {
            "ontology": {
                "classes": len(ontology["classes"]),
                "objectProperties": len(ontology["objectProperties"]),
                "datatypeProperties": len(ontology["datatypeProperties"])
            },
            "facts": {
                "individuals": len(facts["individuals"]),
                "propertyValues": len(facts.get("propertyValues", {})),
                "relations": len(facts.get("relations", {}))
            }
        }
        
        return {
            "ontology": ontology,
            "facts": facts,
            "statistics": stats
        }


class SmartMerger:
    """智能合并器 - 支持本体升华"""
    
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.sublimator = OntologySublimator()
    
    def merge_extractions(self,
                         extraction_files: List[Path],
                         enable_sublimation: bool = True) -> Dict[str, Any]:
        """
        合并多个提取结果
        
        Args:
            extraction_files: 提取文件列表
            enable_sublimation: 是否启用升华
        
        Returns:
            合并结果
        """
        print(f"📦 合并 {len(extraction_files)} 个提取文件...")
        
        # 读取所有提取结果
        all_extractions = []
        for file_path in extraction_files:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                all_extractions.append(data)
            print(f"  ✅ {file_path.name}")
        
        # 基础合并
        merged = self._basic_merge(all_extractions)
        
        if enable_sublimation:
            # 升华分离
            print("\n🔄 执行本体升华...")
            source_chunks = [f.stem for f in extraction_files]
            sublime_result = self.sublimator.sublimate(merged, source_chunks)
            
            # 保存分离结果
            self._save_sublimated(sublime_result)
            
            return sublime_result
        else:
            # 传统合并
            return merged
    
    def _basic_merge(self, all_extractions: List[Dict]) -> Dict:
        """基础合并逻辑"""
        merged = {
            "classes": {},
            "objectProperties": {},
            "datatypeProperties": {},
            "individuals": {}
        }
        
        # 用于去重
        seen = defaultdict(set)
        
        for extraction in all_extractions:
            # 合并类
            for cls_name, cls_def in extraction.get("classes", {}).items():
                if cls_name not in merged["classes"]:
                    merged["classes"][cls_name] = cls_def
                    seen["classes"].add(cls_name)
            
            # 合并属性
            for prop_name, prop_def in extraction.get("objectProperties", {}).items():
                if prop_name not in merged["objectProperties"]:
                    merged["objectProperties"][prop_name] = prop_def
                    seen["properties"].add(prop_name)
            
            # 合并个体（不去重，保留所有）
            for ind_name, ind_def in extraction.get("individuals", {}).items():
                # 如果个体已存在，添加来源信息
                if ind_name in merged["individuals"]:
                    # 保留多个来源
                    if "sources" not in merged["individuals"][ind_name]:
                        merged["individuals"][ind_name]["sources"] = []
                    merged["individuals"][ind_name]["sources"].append(ind_def)
                else:
                    merged["individuals"][ind_name] = ind_def
        
        return merged
    
    def _save_sublimated(self, sublime_result: Dict):
        """保存升华结果"""
        # 保存本体
        ontology_path = self.output_dir / "sublimated_ontology.json"
        with open(ontology_path, 'w', encoding='utf-8') as f:
            json.dump(sublime_result["ontology"], f, indent=2, ensure_ascii=False)
        print(f"💾 本体已保存: {ontology_path}")
        
        # 保存事实
        facts_path = self.output_dir / "sublimated_facts.json"
        with open(facts_path, 'w', encoding='utf-8') as f:
            json.dump(sublime_result["facts"], f, indent=2, ensure_ascii=False)
        print(f"💾 事实已保存: {facts_path}")
        
        # 保存统计
        stats_path = self.output_dir / "sublimation_stats.json"
        with open(stats_path, 'w', encoding='utf-8') as f:
            json.dump(sublime_result["statistics"], f, indent=2, ensure_ascii=False)
        print(f"📊 统计已保存: {stats_path}")


def main():
    """测试本体升华机制"""
    import argparse
    
    parser = argparse.ArgumentParser(description="本体升华机制")
    parser.add_argument("--input", nargs='+', required=True, help="输入 JSON 文件")
    parser.add_argument("--output", required=True, help="输出目录")
    parser.add_argument("--no-sublimation", action="store_true", help="禁用升华")
    
    args = parser.parse_args()
    
    print("🚀 本体升华系统启动")
    print("=" * 60)
    
    # 创建合并器
    merger = SmartMerger(Path(args.output))
    
    # 执行合并
    result = merger.merge_extractions(
        [Path(f) for f in args.input],
        enable_sublimation=not args.no_sublimation
    )
    
    # 打印统计
    print("\n" + "=" * 60)
    print("📊 升华统计")
    print("=" * 60)
    
    if "statistics" in result:
        stats = result["statistics"]
        print("\n本体:")
        for key, value in stats["ontology"].items():
            print(f"  - {key}: {value}")
        
        print("\n事实:")
        for key, value in stats["facts"].items():
            print(f"  - {key}: {value}")
    
    print("\n✅ 升华完成！")


if __name__ == '__main__':
    main()
