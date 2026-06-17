#!/usr/bin/env python3
"""
OntoFuel 本体到 Neo4j NVL 数据转换器

功能：
1. 将 OntoFuel 本体 JSON 转换为 NVL 格式
2. 支持类层次、对象属性、数据属性、个体
3. 支持自定义样式和布局
4. 支持过滤和导出

作者: OntoFuel Extractor
创建时间: 2026-03-10
"""

import json
import argparse
import hashlib
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Set, Tuple
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# --- NVL 数据契约（NFM-227 / NFM-226 ADR D2）-----------------------------
# 版本化契约的语义版本。breaking 变更 nodes/relationships 元素结构时升级主版本。
NVL_SCHEMA_VERSION = "1.0"
# 仓库内 JSON Schema 文件路径（Draft 2020-12），用于 conformance 校验。
NVL_SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schemas" / "nvl_contract.schema.json"
# source_digest 取 sha256 的前 16 个十六进制字符（64 位）。
DIGEST_LENGTH = 16


class OntologyToNVLConverter:
    """本体到 NVL 转换器"""
    
    def __init__(self, ontology_path: str):
        """初始化转换器
        
        Args:
            ontology_path: 本体 JSON 文件路径
        """
        self.ontology_path = Path(ontology_path)
        self.ontology = self._load_ontology()
        
        # NVL 节点和关系
        self.nodes: List[Dict[str, Any]] = []
        self.relationships: List[Dict[str, Any]] = []
        
        # 样式配置
        self.node_styles = {
            'class': {
                'color': '#4A90E2',
                'size': 30,
                'label': '{name}'
            },
            'individual': {
                'color': '#7ED321',
                'size': 20,
                'label': '{name}'
            }
        }
        
        # 类型和层级映射
        self.class_hierarchy: Dict[str, str] = {}  # class_name -> parent_class
        
    def _load_ontology(self) -> Dict[str, Any]:
        """加载本体文件"""
        logger.info(f"加载本体文件: {self.ontology_path}")
        with open(self.ontology_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def convert(self, 
                include_classes: bool = True,
                include_individuals: bool = True,
                include_hierarchy: bool = True,
                include_properties: bool = True,
                max_nodes: Optional[int] = None) -> Dict[str, Any]:
        """转换本体到 NVL 格式
        
        Args:
            include_classes: 是否包含类节点
            include_individuals: 是否包含个体节点
            include_hierarchy: 是否包含类层次关系
            include_properties: 是否包含属性关系
            max_nodes: 最大节点数（用于性能优化）
        
        Returns:
            NVL 格式的数据
        """
        logger.info("开始转换本体到 NVL 格式")
        
        # 1. 处理类节点
        if include_classes:
            self._process_classes()
        
        # 2. 处理个体节点
        if include_individuals:
            self._process_individuals()
        
        # 3. 处理类层次关系
        if include_hierarchy:
            self._process_class_hierarchy()
        
        # 4. 处理对象属性关系
        if include_properties:
            self._process_object_properties()
        
        # 5. 处理数据属性（作为节点属性）
        self._process_datatype_properties()
        
        # 6. 限制节点数（如果指定）
        if max_nodes and len(self.nodes) > max_nodes:
            logger.warning(f"节点数 {len(self.nodes)} 超过限制 {max_nodes}，将截断")
            self.nodes = self.nodes[:max_nodes]
            # 过滤关系
            node_ids = {node['id'] for node in self.nodes}
            self.relationships = [
                rel for rel in self.relationships
                if rel['from'] in node_ids and rel['to'] in node_ids
            ]
        
        logger.info(f"转换完成: {len(self.nodes)} 个节点, {len(self.relationships)} 个关系")

        # 返回带版本与溯源的契约（NFM-227）。nodes/relationships 结构保持不变，
        # 仅在外层增加 schema_version/generated_at/source_ontology/source_digest/stats。
        return self.build_contract()
    

    def _normalize_ref(self, value: Any) -> str:
        """归一化本体中的类/属性引用为简单名称"""
        if value is None:
            return ''

        # 列表：取第一个有效值
        if isinstance(value, list):
            for item in value:
                norm = self._normalize_ref(item)
                if norm:
                    return norm
            return ''

        # 字典：优先取 uri / value
        if isinstance(value, dict):
            for key in ('uri', 'value', '@id', 'id', 'name'):
                if key in value:
                    norm = self._normalize_ref(value[key])
                    if norm:
                        return norm
            return ''

        s = str(value).strip()
        if not s:
            return ''

        # 处理箭头写法，只保留左侧核心类名，避免 class_A -> B 这种脏值
        if '→' in s:
            s = s.split('→', 1)[0].strip()
        if '->' in s:
            s = s.split('->', 1)[0].strip()

        # 处理 URI
        if s.startswith('http://') or s.startswith('https://'):
            if '#' in s:
                s = s.split('#')[-1]
            else:
                s = s.rstrip('/').split('/')[-1]

        # 去掉多余前缀
        if s.startswith('class_'):
            s = s[6:]
        if s.startswith('ind_') and ' ' not in s and ':' not in s and '/' not in s:
            # 个体 id 不在这里作为类名处理，保留原样给调用方判断
            pass

        return s.strip()

    def _ensure_class_node(self, class_name: str):
        """为缺失但被引用的类补一个占位节点，避免关系断裂"""
        class_name = self._normalize_ref(class_name)
        if not class_name:
            return
        class_id = f'class_{class_name}'
        if any(node.get('id') == class_id for node in self.nodes):
            return
        self.nodes.append({
            'id': class_id,
            'type': 'class',
            'name': class_name,
            'label': class_name,
            'comment': 'Auto-generated placeholder for referenced class',
            'uri': '',
            **self.node_styles['class']
        })

    def _extract_label(self, label_value, fallback: str = '') -> str:
        """安全提取 rdfs:label 值，兼容字符串/列表/字典/None"""
        if label_value is None:
            return fallback
        if isinstance(label_value, str):
            return label_value or fallback
        if isinstance(label_value, list) and len(label_value) > 0:
            first = label_value[0]
            if isinstance(first, dict):
                return first.get('value', '') or first.get('@value', '') or fallback
            return str(first) or fallback
        if isinstance(label_value, dict):
            return label_value.get('value', '') or label_value.get('@value', '') or fallback
        return fallback

    def _process_classes(self):
        """处理类节点"""
        logger.info("处理类节点...")
        classes = self.ontology.get('classes', {})
        
        for class_name, class_data in classes.items():
            # 记录类层次
            parent = self._normalize_ref(class_data.get('parent'))
            if parent:
                self.class_hierarchy[class_name] = parent
            
            # 创建节点
            node = {
                'id': f'class_{class_name}',
                'type': 'class',
                'name': class_name,
                'label': self._extract_label(class_data.get('rdfs:label'), class_name) or class_name,
                'comment': class_data.get('comment', ''),
                'uri': class_data.get('uri', ''),
                **self.node_styles['class']
            }
            
            self.nodes.append(node)
        
        logger.info(f"创建了 {len(classes)} 个类节点")
    
    def _process_individuals(self):
        """处理个体节点"""
        logger.info("处理个体节点...")
        individuals = self.ontology.get('individuals', {})
        
        for ind_name, ind_data in individuals.items():
            # 获取个体类型（类）
            ind_type = self._normalize_ref(ind_data.get('type', ''))
            
            # 创建节点
            node = {
                'id': f'ind_{ind_name}',
                'type': 'individual',
                'name': ind_name,
                'label': ind_name,
                'class': ind_type,
                'uri': ind_data.get('uri', ''),
                **self.node_styles['individual']
            }
            
            # 添加数据属性作为节点属性
            for key, value in ind_data.items():
                if key not in ['type', 'uri']:
                    node[f'prop_{key}'] = value
            
            self.nodes.append(node)
            
            # 创建个体到类的关系
            if ind_type:
                self._ensure_class_node(ind_type)
                rel = {
                    'id': f'rel_ind_{ind_name}_type',
                    'from': f'ind_{ind_name}',
                    'to': f'class_{ind_type}',
                    'type': 'INSTANCE_OF',
                    'label': 'instance of'
                }
                self.relationships.append(rel)
        
        logger.info(f"创建了 {len(individuals)} 个个体节点")
    
    def _process_class_hierarchy(self):
        """处理类层次关系"""
        logger.info("处理类层次关系...")
        
        for child_class, parent_class in self.class_hierarchy.items():
            child_class = self._normalize_ref(child_class)
            parent_class = self._normalize_ref(parent_class)
            if not child_class or not parent_class:
                continue
            self._ensure_class_node(child_class)
            self._ensure_class_node(parent_class)
            rel = {
                'id': f'rel_hier_{child_class}_{parent_class}',
                'from': f'class_{child_class}',
                'to': f'class_{parent_class}',
                'type': 'SUBCLASS_OF',
                'label': 'subclass of'
            }
            self.relationships.append(rel)
        
        logger.info(f"创建了 {len(self.class_hierarchy)} 个层次关系")
    
    def _process_object_properties(self):
        """处理对象属性关系"""
        logger.info("处理对象属性关系...")
        object_properties = self.ontology.get('objectProperties', {})
        
        count = 0
        for prop_name, prop_data in object_properties.items():
            domain = self._normalize_ref(prop_data.get('domain'))
            range_class = self._normalize_ref(prop_data.get('range'))
            
            if domain and range_class:
                self._ensure_class_node(domain)
                self._ensure_class_node(range_class)
                # 创建属性关系（域类 -> 值域类）
                rel = {
                    'id': f'rel_prop_{prop_name}',
                    'from': f'class_{domain}',
                    'to': f'class_{range_class}',
                    'type': prop_name,
                    'label': self._extract_label(prop_data.get('rdfs:label'), prop_name),
                    'comment': prop_data.get('rdfs:comment', '')
                }
                self.relationships.append(rel)
                count += 1
        
        logger.info(f"创建了 {count} 个对象属性关系")
    
    def _process_datatype_properties(self):
        """处理数据属性（作为节点属性）"""
        logger.info("处理数据属性...")
        datatype_properties = self.ontology.get('datatypeProperties', {})
        
        # 数据属性主要用于增强节点信息，已在 _process_individuals 中处理
        logger.info(f"共有 {len(datatype_properties)} 个数据属性定义")
    
    def save_nvl_json(self, output_path: str, generated_at: Optional[str] = None) -> Dict[str, Any]:
        """保存带版本与溯源的 NVL 契约 JSON 文件

        Args:
            output_path: 输出文件路径
            generated_at: 可选的 ISO-8601 时间戳（测试确定性用）；默认取当前 UTC 时间

        Returns:
            写入的契约 dict
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        contract = self.build_contract(generated_at=generated_at)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(contract, f, indent=2, ensure_ascii=False)

        logger.info(f"NVL 契约数据已保存到: {output_path}")
        return contract

    # ------------------------------------------------------------------
    # NVL 数据契约（NFM-227）
    # ------------------------------------------------------------------

    def _source_ontology_label(self) -> str:
        """溯源标识：优先用相对仓库根的路径，便于可读与跨机器一致。"""
        try:
            repo_root = Path(__file__).resolve().parent.parent
            return str(self.ontology_path.resolve().relative_to(repo_root))
        except ValueError:
            return str(self.ontology_path)

    def _compute_source_digest(self) -> str:
        """规范本体 sha256 短摘要。

        对确定性序列化（键排序、无多余空格、ensure_ascii=False）取 sha256，
        截取前 ``DIGEST_LENGTH`` 个十六进制字符。键排序使摘要与字段书写顺序无关，
        跨重新保存稳定。
        """
        with open(self.ontology_path, 'r', encoding='utf-8') as f:
            ontology = json.load(f)
        canonical = json.dumps(
            ontology, sort_keys=True, ensure_ascii=False, separators=(',', ':')
        )
        return hashlib.sha256(canonical.encode('utf-8')).hexdigest()[:DIGEST_LENGTH]

    def _build_stats(self) -> Dict[str, int]:
        """NVL 派生计数。classes 计入转换器自动补齐的占位类节点。"""
        classes = sum(1 for n in self.nodes if n.get('type') == 'class')
        individuals = sum(1 for n in self.nodes if n.get('type') == 'individual')
        return {
            'nodes': len(self.nodes),
            'relationships': len(self.relationships),
            'classes': classes,
            'individuals': individuals,
        }

    def build_contract(self, generated_at: Optional[str] = None) -> Dict[str, Any]:
        """组装带版本与溯源的 NVL 契约。

        nodes/relationships 元素结构保持不变，仅在外层包裹版本与溯源信息。
        """
        return {
            'schema_version': NVL_SCHEMA_VERSION,
            'generated_at': generated_at or datetime.now(timezone.utc).isoformat(),
            'source_ontology': self._source_ontology_label(),
            'source_digest': self._compute_source_digest(),
            'stats': self._build_stats(),
            'nodes': self.nodes,
            'relationships': self.relationships,
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取转换统计信息"""
        return {
            'total_nodes': len(self.nodes),
            'total_relationships': len(self.relationships),
            'class_nodes': len([n for n in self.nodes if n['type'] == 'class']),
            'individual_nodes': len([n for n in self.nodes if n['type'] == 'individual']),
            'hierarchy_relations': len([r for r in self.relationships if r['type'] == 'SUBCLASS_OF']),
            'property_relations': len([r for r in self.relationships if r['type'] not in ['SUBCLASS_OF', 'INSTANCE_OF']])
        }


def load_contract_schema(schema_path: Optional[Path] = None) -> Dict[str, Any]:
    """加载仓库内 NVL 契约 JSON Schema（Draft 2020-12）。"""
    path = Path(schema_path) if schema_path else NVL_SCHEMA_PATH
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def _validate_contract_fallback(contract: Dict[str, Any]) -> List[str]:
    """jsonschema 未安装时的精简结构校验（仅覆盖契约必需项 + 节点 type 枚举 + 关系端点）。

    与 schemas/nvl_contract.schema.json 在结构上一致，但仅做必要检查；
    完整校验请安装 jsonschema（见 tests/test_nvl_contract.py）。
    """
    errors: List[str] = []
    required = [
        'schema_version', 'generated_at', 'source_ontology',
        'source_digest', 'stats', 'nodes', 'relationships',
    ]
    for key in required:
        if key not in contract:
            errors.append(f"<root>: '{key}' is required")
    if errors:
        return errors
    for i, node in enumerate(contract.get('nodes', [])):
        if not isinstance(node, dict) or 'id' not in node:
            errors.append(f"nodes/{i}: missing 'id'")
        elif node.get('type') not in ('class', 'individual'):
            errors.append(
                f"nodes/{i}: 'type' must be 'class' or 'individual', got {node.get('type')!r}"
            )
    for i, rel in enumerate(contract.get('relationships', [])):
        for k in ('id', 'from', 'to', 'type'):
            if not isinstance(rel, dict) or k not in rel:
                errors.append(f"relationships/{i}: missing '{k}'")
    return errors


def validate_contract(
    contract: Dict[str, Any], schema_path: Optional[Path] = None
) -> List[str]:
    """用 JSON Schema（Draft 2020-12）校验 NVL 契约。

    返回错误消息列表；空列表表示通过。jsonschema 不可用时回退到精简结构校验。
    """
    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        return _validate_contract_fallback(contract)
    schema = load_contract_schema(schema_path)
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(contract), key=lambda e: list(e.path))
    return [f"{'/'.join(map(str, e.path)) or '<root>'}: {e.message}" for e in errors]


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='OntoFuel 本体到 Neo4j NVL 转换器')
    parser.add_argument('ontology', nargs='?', default=None, help='本体 JSON 文件路径（位置参数）')
    parser.add_argument('-i', '--input', dest='input_alias', default=None, help='本体 JSON 文件路径（--input 别名，兼容子代理调用）')
    parser.add_argument('-o', '--output', default='nvl_data.json', help='输出 NVL JSON 文件路径')
    parser.add_argument('--no-classes', action='store_true', help='不包含类节点')
    parser.add_argument('--no-individuals', action='store_true', help='不包含个体节点')
    parser.add_argument('--no-hierarchy', action='store_true', help='不包含类层次关系')
    parser.add_argument('--no-properties', action='store_true', help='不包含属性关系')
    parser.add_argument('--max-nodes', type=int, help='最大节点数（用于性能优化）')
    parser.add_argument('--stats', action='store_true', help='显示统计信息')
    parser.add_argument(
        '--validate', action='store_true',
        help='生成后用 JSON Schema 校验契约，失败时以非零状态退出',
    )

    args = parser.parse_args()

    # 兼容：支持 --input 别名
    ontology_path = args.ontology or args.input_alias
    if not ontology_path:
        parser.error('必须提供本体 JSON 文件路径（位置参数或 --input）')

    # 创建转换器
    converter = OntologyToNVLConverter(ontology_path)

    # 转换
    nvl_data = converter.convert(
        include_classes=not args.no_classes,
        include_individuals=not args.no_individuals,
        include_hierarchy=not args.no_hierarchy,
        include_properties=not args.no_properties,
        max_nodes=args.max_nodes
    )

    # 保存（带版本与溯源的契约）
    converter.save_nvl_json(args.output)

    # 契约校验（可选）
    if args.validate:
        errors = validate_contract(nvl_data)
        if errors:
            print(f"\n❌ 契约校验失败（{len(errors)} 项）:")
            for msg in errors:
                print(f"  - {msg}")
            raise SystemExit(1)
        print("\n✅ 契约校验通过")

    # 显示统计信息
    if args.stats:
        stats = converter.get_statistics()
        print("\n转换统计:")
        print("=" * 60)
        for key, value in stats.items():
            print(f"{key}: {value}")


if __name__ == '__main__':
    main()
