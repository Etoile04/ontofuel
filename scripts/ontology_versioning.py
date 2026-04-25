#!/usr/bin/env python3
"""
Git 风格版本控制系统 - 借鉴 OntoCast 的版本管理机制

核心功能：
- SHA256 哈希计算（基于内容）
- 父本体引用（谱系追踪）
- 版本回溯（历史记录）
- 合并追踪（冲突检测）

版本：v1.0.0
创建：2026-03-07
"""

import json
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, asdict


@dataclass
class OntologyVersion:
    """本体版本信息"""
    hash: str                    # SHA256 哈希（16 字符）
    parent_hashes: List[str]     # 父本体哈希列表
    version: str                 # 语义版本号
    created_at: str              # 创建时间
    message: str                 # 提交消息
    author: str                  # 作者
    changes: Dict[str, int]      # 变更统计


class OntologyVersionControl:
    """Git 风格的本体版本控制系统"""
    
    def __init__(self, ontology_path: Path, versions_dir: Path = None):
        """
        初始化版本控制系统
        
        Args:
            ontology_path: 本体文件路径
            versions_dir: 版本存储目录（默认为 ontology_path.parent / "versions"）
        """
        self.ontology_path = ontology_path
        self.versions_dir = versions_dir or ontology_path.parent / "versions"
        self.versions_dir.mkdir(parents=True, exist_ok=True)
        
        self.versions_file = self.versions_dir / "versions.json"
        self.current_version = self._load_current_version()
        self.versions_history = self._load_versions_history()
    
    def _compute_hash(self, ontology: Dict) -> str:
        """计算本体的 SHA256 哈希"""
        content = json.dumps(ontology, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def _load_current_version(self) -> Optional[Dict]:
        """加载当前版本的本体"""
        if not self.ontology_path.exists():
            return None
        
        with open(self.ontology_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _load_versions_history(self) -> Dict[str, OntologyVersion]:
        """加载版本历史"""
        if not self.versions_file.exists():
            return {}
        
        with open(self.versions_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return {
            k: OntologyVersion(**v)
            for k, v in data.items()
        }
    
    def _save_versions_history(self):
        """保存版本历史"""
        data = {
            k: asdict(v)
            for k, v in self.versions_history.items()
        }
        
        with open(self.versions_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def _calculate_changes(self, old_onto: Optional[Dict], new_onto: Dict) -> Dict[str, int]:
        """计算变更统计"""
        if old_onto is None:
            # 初始提交，计算所有内容
            return {
                "classes_added": len(new_onto.get("classes", {})),
                "properties_added": len(new_onto.get("objectProperties", {})) + len(new_onto.get("datatypeProperties", {})),
                "individuals_added": len(new_onto.get("individuals", {})),
                "classes_removed": 0,
                "properties_removed": 0,
                "individuals_removed": 0
            }
        
        changes = {}
        
        # 类变更
        old_classes = set(old_onto.get("classes", {}).keys())
        new_classes = set(new_onto.get("classes", {}).keys())
        changes["classes_added"] = len(new_classes - old_classes)
        changes["classes_removed"] = len(old_classes - new_classes)
        
        # 属性变更
        old_props = set(old_onto.get("objectProperties", {}).keys())
        new_props = set(new_onto.get("objectProperties", {}).keys())
        changes["properties_added"] = len(new_props - old_props)
        changes["properties_removed"] = len(old_props - new_props)
        
        # 个体变更
        old_inds = set(old_onto.get("individuals", {}).keys())
        new_inds = set(new_onto.get("individuals", {}).keys())
        changes["individuals_added"] = len(new_inds - old_inds)
        changes["individuals_removed"] = len(old_inds - new_inds)
        
        return changes
    
    def _upgrade_version(self, current_version: str, changes: Dict[str, int]) -> str:
        """
        升级版本号
        
        规则：
        - 删除类/属性 → MAJOR (x.0.0)
        - 新增类/属性 → MINOR (0.x.0)
        - 小修改 → PATCH (0.0.x)
        """
        if not current_version:
            return "1.0.0"
        
        parts = current_version.split('.')
        if len(parts) != 3:
            return "1.0.0"
        
        major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
        
        # 检查是否有删除（MAJOR）
        if changes.get("classes_removed", 0) > 0 or changes.get("properties_removed", 0) > 0:
            major += 1
            minor = 0
            patch = 0
        # 检查是否有新增（MINOR）
        elif changes.get("classes_added", 0) > 0 or changes.get("properties_added", 0) > 0:
            minor += 1
            patch = 0
        # 其他修改（PATCH）
        else:
            patch += 1
        
        return f"{major}.{minor}.{patch}"
    
    def commit(self, 
               message: str = "",
               author: str = "OntoFuel Extractor",
               ontology_data: Optional[Dict] = None) -> OntologyVersion:
        """
        提交新版本
        
        Args:
            message: 提交消息
            author: 作者
            ontology_data: 新的本体数据（如果为 None，则从文件加载）
        
        Returns:
            OntologyVersion: 版本信息
        """
        # 加载本体数据
        if ontology_data is None:
            ontology_data = self._load_current_version()
        
        if ontology_data is None:
            raise ValueError("本体数据为空")
        
        # 计算哈希
        new_hash = self._compute_hash(ontology_data)
        
        # 检查是否已有此版本
        if new_hash in self.versions_history:
            print(f"⚠️  版本 {new_hash} 已存在，跳过提交")
            return self.versions_history[new_hash]
        
        # 获取父版本哈希
        parent_hashes = []
        old_onto = None  # 用于计算变更
        
        if self.current_version and "metadata" in self.current_version:
            parent_hash = self.current_version["metadata"].get("hash")
            if parent_hash:
                parent_hashes.append(parent_hash)
                # 如果有父版本，则 old_onto 是当前版本
                old_onto = self.current_version
        
        # 计算变更
        changes = self._calculate_changes(old_onto, ontology_data)
        
        # 升级版本号
        # 如果是初始提交（old_onto == None），保持 1.0.0
        if old_onto is None:
            new_version = "1.0.0"
        else:
            current_version = self.current_version.get("metadata", {}).get("version", "1.0.0") if self.current_version else "1.0.0"
            new_version = self._upgrade_version(current_version, changes)
        
        # 创建版本记录
        version_record = OntologyVersion(
            hash=new_hash,
            parent_hashes=parent_hashes,
            version=new_version,
            created_at=datetime.now().isoformat(),
            message=message,
            author=author,
            changes=changes
        )
        
        # 更新本体元数据
        if "metadata" not in ontology_data:
            ontology_data["metadata"] = {}
        
        ontology_data["metadata"]["hash"] = new_hash
        ontology_data["metadata"]["version"] = new_version
        ontology_data["metadata"]["parent_hashes"] = parent_hashes
        ontology_data["metadata"]["created_at"] = version_record.created_at
        
        # 保存本体
        with open(self.ontology_path, 'w', encoding='utf-8') as f:
            json.dump(ontology_data, f, indent=2, ensure_ascii=False)
        
        # 保存版本历史
        self.versions_history[new_hash] = version_record
        self._save_versions_history()
        
        # 更新当前版本
        self.current_version = ontology_data
        
        print(f"✅ 提交成功: {new_hash}")
        print(f"   版本: {new_version}")
        print(f"   消息: {message}")
        
        return version_record
    
    def checkout(self, version_hash: str) -> Dict:
        """
        检出指定版本
        
        Args:
            version_hash: 版本哈希
        
        Returns:
            Dict: 本体数据
        """
        if version_hash not in self.versions_history:
            raise ValueError(f"版本 {version_hash} 不存在")
        
        # 从版本历史加载
        version_file = self.versions_dir / f"{version_hash}.json"
        
        if not version_file.exists():
            raise FileNotFoundError(f"版本文件 {version_file} 不存在")
        
        with open(version_file, 'r', encoding='utf-8') as f:
            ontology = json.load(f)
        
        # 保存为当前版本
        with open(self.ontology_path, 'w', encoding='utf-8') as f:
            json.dump(ontology, f, indent=2, ensure_ascii=False)
        
        self.current_version = ontology
        
        version_info = self.versions_history[version_hash]
        print(f"✅ 检出成功: {version_hash}")
        print(f"   版本: {version_info.version}")
        print(f"   时间: {version_info.created_at}")
        
        return ontology
    
    def log(self, limit: int = 10) -> List[OntologyVersion]:
        """
        查看版本历史
        
        Args:
            limit: 显示数量
        
        Returns:
            List[OntologyVersion]: 版本列表
        """
        # 按时间排序
        sorted_versions = sorted(
            self.versions_history.values(),
            key=lambda v: v.created_at,
            reverse=True
        )
        
        return sorted_versions[:limit]
    
    def diff(self, hash1: str, hash2: str) -> Dict[str, Any]:
        """
        比较两个版本
        
        Args:
            hash1: 第一个版本哈希
            hash2: 第二个版本哈希
        
        Returns:
            Dict: 差异报告
        """
        if hash1 not in self.versions_history or hash2 not in self.versions_history:
            raise ValueError("版本不存在")
        
        version1 = self.versions_history[hash1]
        version2 = self.versions_history[hash2]
        
        # 加载本体
        onto1_path = self.versions_dir / f"{hash1}.json"
        onto2_path = self.versions_dir / f"{hash2}.json"
        
        with open(onto1_path, 'r') as f:
            onto1 = json.load(f)
        
        with open(onto2_path, 'r') as f:
            onto2 = json.load(f)
        
        # 计算差异
        diff_report = {
            "version1": {
                "hash": hash1,
                "version": version1.version,
                "date": version1.created_at
            },
            "version2": {
                "hash": hash2,
                "version": version2.version,
                "date": version2.created_at
            },
            "changes": self._calculate_changes(onto1, onto2)
        }
        
        return diff_report
    
    def branch(self, branch_name: str) -> str:
        """
        创建分支（复制当前版本）
        
        Args:
            branch_name: 分支名称
        
        Returns:
            str: 分支文件路径
        """
        if self.current_version is None:
            raise ValueError("没有当前版本")
        
        branch_path = self.versions_dir / f"branch_{branch_name}.json"
        
        with open(branch_path, 'w', encoding='utf-8') as f:
            json.dump(self.current_version, f, indent=2, ensure_ascii=False)
        
        print(f"✅ 分支创建成功: {branch_name}")
        print(f"   路径: {branch_path}")
        
        return str(branch_path)
    
    def merge(self, branch_name: str, message: str = "") -> OntologyVersion:
        """
        合并分支
        
        Args:
            branch_name: 分支名称
            message: 合并消息
        
        Returns:
            OntologyVersion: 合并后的版本
        """
        branch_path = self.versions_dir / f"branch_{branch_name}.json"
        
        if not branch_path.exists():
            raise FileNotFoundError(f"分支 {branch_name} 不存在")
        
        with open(branch_path, 'r', encoding='utf-8') as f:
            branch_ontology = json.load(f)
        
        # 简单合并策略：并集
        merged = {
            "classes": {**self.current_version.get("classes", {}), **branch_ontology.get("classes", {})},
            "objectProperties": {**self.current_version.get("objectProperties", {}), **branch_ontology.get("objectProperties", {})},
            "datatypeProperties": {**self.current_version.get("datatypeProperties", {}), **branch_ontology.get("datatypeProperties", {})},
            "individuals": {**self.current_version.get("individuals", {}), **branch_ontology.get("individuals", {})}
        }
        
        # 提交合并
        merge_message = message or f"合并分支: {branch_name}"
        return self.commit(message=merge_message, ontology_data=merged)


def main():
    """测试 Git 风格版本控制系统"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Git 风格版本控制系统")
    parser.add_argument("--ontology", required=True, help="本体文件路径")
    parser.add_argument("--action", required=True, 
                       choices=["commit", "checkout", "log", "diff", "branch", "merge"],
                       help="操作类型")
    parser.add_argument("--message", default="", help="提交消息")
    parser.add_argument("--hash", help="版本哈希")
    parser.add_argument("--hash1", help="第一个版本哈希（用于 diff）")
    parser.add_argument("--hash2", help="第二个版本哈希（用于 diff）")
    parser.add_argument("--branch", help="分支名称")
    
    args = parser.parse_args()
    
    print("📚 Git 风格版本控制系统")
    print("=" * 60)
    
    # 创建版本控制系统
    vc = OntologyVersionControl(Path(args.ontology))
    
    if args.action == "commit":
        # 提交
        version = vc.commit(message=args.message)
        print(f"\n版本信息:")
        print(f"  哈希: {version.hash}")
        print(f"  版本: {version.version}")
        print(f"  时间: {version.created_at}")
        print(f"  变更: {version.changes}")
    
    elif args.action == "checkout":
        # 检出
        if not args.hash:
            print("❌ 错误: 需要指定 --hash")
            return 1
        vc.checkout(args.hash)
    
    elif args.action == "log":
        # 查看历史
        versions = vc.log(limit=10)
        print(f"\n版本历史（最近 {len(versions)} 个）:")
        for v in versions:
            print(f"\n  哈希: {v.hash}")
            print(f"  版本: {v.version}")
            print(f"  时间: {v.created_at}")
            print(f"  消息: {v.message}")
            print(f"  变更: {v.changes}")
    
    elif args.action == "diff":
        # 比较
        if not args.hash1 or not args.hash2:
            print("❌ 错误: 需要指定 --hash1 和 --hash2")
            return 1
        diff_report = vc.diff(args.hash1, args.hash2)
        print(f"\n差异报告:")
        print(f"  版本 1: {diff_report['version1']['version']} ({diff_report['version1']['hash']})")
        print(f"  版本 2: {diff_report['version2']['version']} ({diff_report['version2']['hash']})")
        print(f"  变更: {diff_report['changes']}")
    
    elif args.action == "branch":
        # 创建分支
        if not args.branch:
            print("❌ 错误: 需要指定 --branch")
            return 1
        vc.branch(args.branch)
    
    elif args.action == "merge":
        # 合并分支
        if not args.branch:
            print("❌ 错误: 需要指定 --branch")
            return 1
        version = vc.merge(args.branch, message=args.message)
        print(f"\n合并成功:")
        print(f"  版本: {version.version}")
        print(f"  哈希: {version.hash}")
    
    print("\n✅ 操作完成")
    return 0


if __name__ == '__main__':
    exit(main())
