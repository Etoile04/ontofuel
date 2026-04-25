#!/usr/bin/env python3
"""本体查询工具 - 避免多次读取大文件"""

import json
import sys
from pathlib import Path
from typing import List, Dict, Any

class OntologyQueryTool:
    """本体查询工具类"""
    
    def __init__(self, ontology_file: str):
        """初始化，读取一次本体文件并缓存到内存"""
        self.ontology_file = ontology_file
        print(f"📚 加载本体: {ontology_file}")
        
        with open(ontology_file, 'r', encoding='utf-8') as f:
            self.ontology = json.load(f)
        
        self.classes = self.ontology.get('classes', {})
        self.object_properties = self.ontology.get('objectProperties', {})
        self.datatype_properties = self.ontology.get('datatypeProperties', {})
        self.individuals = self.ontology.get('individuals', {})
        self.metadata = self.ontology.get('metadata', {})
        
        print(f"✅ 加载完成")
        print(f"   类: {len(self.classes)}")
        print(f"   对象属性: {len(self.object_properties)}")
        print(f"   数据属性: {len(self.datatype_properties)}")
        print(f"   个体: {len(self.individuals)}")
    
    def list_classes(self, limit: int = 10, keyword: str = None):
        """列出类"""
        classes_list = list(self.classes.keys())
        
        if keyword:
            classes_list = [c for c in classes_list if keyword.lower() in c.lower()]
        
        total = len(classes_list)
        
        print(f"\n{'='*60}")
        print(f"类列表（共 {total} 个）")
        print(f"{'='*60}")
        
        for i, cls_name in enumerate(classes_list[:limit], 1):
            cls = self.classes[cls_name]
            print(f"\n{i}. {cls_name}")
            print(f"   URI: {cls.get('uri', 'N/A')}")
            
            # 只显示简短的注释
            comment = cls.get('rdfs:comment', '')
            if comment and len(comment) < 100:
                print(f"   注释: {comment}")
        
        if total > limit:
            print(f"\n... 还有 {total - limit} 个类")
            print(f"\n💡 查看完整列表:")
            print(f"   python3 scripts/ontology_query_tool.py --list-classes --limit {total}")
        
        if keyword:
            print(f"\n🔍 搜索关键词: '{keyword}'")
    
    def search(self, keyword: str, search_type: str = 'all'):
        """搜索"""
        print(f"\n{'='*60}")
        print(f"搜索: '{keyword}'")
        print(f"{'='*60}")
        
        results = {
            'classes': [],
            'object_properties': [],
            'datatype_properties': [],
            'individuals': []
        }
        
        if search_type in ['all', 'classes']:
            results['classes'] = [k for k in self.classes.keys() if keyword.lower() in k.lower()]
        
        if search_type in ['all', 'properties']:
            results['object_properties'] = [k for k in self.object_properties.keys() if keyword.lower() in k.lower()]
            results['datatype_properties'] = [k for k in self.datatype_properties.keys() if keyword.lower() in k.lower()]
        
        if search_type in ['all', 'individuals']:
            results['individuals'] = [k for k in self.individuals.keys() if keyword.lower() in k.lower()]
        
        # 显示结果
        total = sum(len(v) for v in results.values())
        
        if total == 0:
            print("❌ 未找到匹配结果")
            return
        
        print(f"找到 {total} 个匹配项:\n")
        
        if results['classes']:
            print(f"类 ({len(results['classes'])}):")
            for cls in results['classes'][:10]:
                print(f"  - {cls}")
            if len(results['classes']) > 10:
                print(f"  ... 还有 {len(results['classes']) - 10} 个")
        
        if results['object_properties']:
            print(f"\n对象属性 ({len(results['object_properties'])}):")
            for prop in results['object_properties'][:10]:
                print(f"  - {prop}")
            if len(results['object_properties']) > 10:
                print(f"  ... 还有 {len(results['object_properties']) - 10} 个")
        
        if results['datatype_properties']:
            print(f"\n数据属性 ({len(results['datatype_properties'])}):")
            for prop in results['datatype_properties'][:10]:
                print(f"  - {prop}")
            if len(results['datatype_properties']) > 10:
                print(f"  ... 还有 {len(results['datatype_properties']) - 10} 个")
        
        if results['individuals']:
            print(f"\n个体 ({len(results['individuals'])}):")
            for ind in results['individuals'][:10]:
                print(f"  - {ind}")
            if len(results['individuals']) > 10:
                print(f"  ... 还有 {len(results['individuals']) - 10} 个")
    
    def get_details(self, item_type: str, item_name: str):
        """获取详细信息"""
        print(f"\n{'='*60}")
        print(f"详细信息: {item_name}")
        print(f"{'='*60}")
        
        if item_type == 'class':
            if item_name in self.classes:
                cls = self.classes[item_name]
                print(f"类型: 类")
                print(f"URI: {cls.get('uri', 'N/A')}")
                print(f"标签: {cls.get('rdfs:label', [])}")
                print(f"注释: {cls.get('rdfs:comment', 'N/A')}")
                print(f"父类: {cls.get('rdfs:subClassOf', [])}")
            else:
                print(f"❌ 类 '{item_name}' 不存在")
        
        elif item_type == 'property':
            if item_name in self.object_properties:
                prop = self.object_properties[item_name]
                print(f"类型: 对象属性")
                print(f"URI: {prop.get('uri', 'N/A')}")
                print(f"Domain: {prop.get('rdfs:domain', 'N/A')}")
                print(f"Range: {prop.get('rdfs:range', 'N/A')}")
            elif item_name in self.datatype_properties:
                prop = self.datatype_properties[item_name]
                print(f"类型: 数据属性")
                print(f"URI: {prop.get('uri', 'N/A')}")
                print(f"Domain: {prop.get('rdfs:domain', 'N/A')}")
                print(f"Range: {prop.get('rdfs:range', 'N/A')}")
            else:
                print(f"❌ 属性 '{item_name}' 不存在")
        
        elif item_type == 'individual':
            if item_name in self.individuals:
                ind = self.individuals[item_name]
                print(f"类型: 个体")
                print(f"URI: {ind.get('uri', 'N/A')}")
                print(f"Class: {ind.get('rdf:type', [])}")
                
                # 显示前 5 个属性
                props = {k: v for k, v in ind.items() if not k.startswith('rdf:') and not k.startswith('rdfs:')}
                if props:
                    print(f"\n属性 ({len(props)} 个):")
                    for i, (k, v) in enumerate(list(props.items())[:5], 1):
                        if isinstance(v, list) and v:
                            print(f"  {i}. {k}: {v[0].get('value', v[0]) if isinstance(v[0], dict) else v[0]}")
                        else:
                            print(f"  {i}. {k}: {v}")
                    
                    if len(props) > 5:
                        print(f"  ... 还有 {len(props) - 5} 个属性")
            else:
                print(f"❌ 个体 '{item_name}' 不存在")
    
    def show_stats(self):
        """显示统计信息"""
        print(f"\n{'='*60}")
        print(f"本体统计")
        print(f"{'='*60}")
        print(f"版本: {self.metadata.get('version', 'N/A')}")
        print(f"最后更新: {self.metadata.get('lastUpdated', 'N/A')}")
        print(f"\n类: {len(self.classes)}")
        print(f"对象属性: {len(self.object_properties)}")
        print(f"数据属性: {len(self.datatype_properties)}")
        print(f"个体: {len(self.individuals)}")

def print_usage():
    """打印使用说明"""
    print("""
本体查询工具

用法:
    python3 scripts/ontology_query_tool.py <command> [options]

命令:
    --stats                     显示统计信息
    --list-classes [limit]      列出类（默认 10 个）
    --search <keyword>          搜索
    --class <name>              查看类详情
    --property <name>           查看属性详情
    --individual <name>         查看个体详情

示例:
    # 显示统计
    python3 scripts/ontology_query_tool.py --stats

    # 列出前 20 个类
    python3 scripts/ontology_query_tool.py --list-classes 20

    # 搜索包含 "diffus" 的所有项
    python3 scripts/ontology_query_tool.py --search diffus

    # 查看类的详细信息
    python3 scripts/ontology_query_tool.py --class DiffusionCoefficient

    # 查看属性的详细信息
    python3 scripts/ontology_query_tool.py --property hasDiffusionCoefficient

    # 查看个体的详细信息
    python3 scripts/ontology_query_tool.py --individual CoCrFeMnNi_DiffusionCoefficient_Cu_001
""")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)
    
    # 本体文件路径
    ontology_file = "memory/trustgraph-fix/material_ontology_enhanced.json"
    
    # 创建查询工具
    tool = OntologyQueryTool(ontology_file)
    
    # 解析命令
    command = sys.argv[1]
    
    if command == '--stats':
        tool.show_stats()
    
    elif command == '--list-classes':
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        keyword = sys.argv[3] if len(sys.argv) > 3 else None
        tool.list_classes(limit, keyword)
    
    elif command == '--search':
        if len(sys.argv) < 3:
            print("❌ 请提供搜索关键词")
            print("用法: python3 scripts/ontology_query_tool.py --search <keyword>")
            sys.exit(1)
        keyword = sys.argv[2]
        search_type = sys.argv[3] if len(sys.argv) > 3 else 'all'
        tool.search(keyword, search_type)
    
    elif command == '--class':
        if len(sys.argv) < 3:
            print("❌ 请提供类名")
            print("用法: python3 scripts/ontology_query_tool.py --class <name>")
            sys.exit(1)
        tool.get_details('class', sys.argv[2])
    
    elif command == '--property':
        if len(sys.argv) < 3:
            print("❌ 请提供属性名")
            print("用法: python3 scripts/ontology_query_tool.py --property <name>")
            sys.exit(1)
        tool.get_details('property', sys.argv[2])
    
    elif command == '--individual':
        if len(sys.argv) < 3:
            print("❌ 请提供个体名")
            print("用法: python3 scripts/ontology_query_tool.py --individual <name>")
            sys.exit(1)
        tool.get_details('individual', sys.argv[2])
    
    else:
        print(f"❌ 未知命令: {command}")
        print_usage()
        sys.exit(1)
