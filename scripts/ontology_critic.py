#!/usr/bin/env python3
"""
LLM 本体批判系统 - 借鉴 OntoCast 的质量评估机制

核心功能：
- LLM 驱动的本体质量评估
- 自动评分（0-100）
- 改进建议生成
- 集成到工作流

版本：v1.0.0
创建：2026-03-07
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum


class CritiqueSeverity(Enum):
    """批判严重性级别"""
    CRITICAL = "critical"    # 严重错误，必须修复
    WARNING = "warning"      # 警告，建议修复
    INFO = "info"           # 信息，可选优化


@dataclass
class Suggestion:
    """改进建议"""
    severity: CritiqueSeverity
    category: str           # 分类（命名、结构、语义等）
    description: str        # 描述
    location: Optional[str] # 位置（类/属性/个体名称）
    fix_hint: Optional[str] # 修复提示


@dataclass
class OntologyCritiqueReport:
    """本体批判报告"""
    success: bool                          # 是否通过
    score: int                             # 评分（0-100）
    systemic_critique_summary: str         # 系统性批判总结
    actionable_ontology_fixes: List[Suggestion]  # 可执行的修复建议
    categories_scores: Dict[str, int]      # 各分类评分


class OntologyCritic:
    """LLM 本体批判器"""
    
    def __init__(self, llm_client=None):
        """
        初始化批判器
        
        Args:
            llm_client: LLM 客户端（可选，用于真实 LLM 调用）
        """
        self.llm_client = llm_client
        self.criteria = self._load_criteria()
    
    def _load_criteria(self) -> Dict[str, Dict]:
        """加载批判标准"""
        return {
            "naming": {
                "weight": 0.2,
                "description": "命名规范",
                "checks": [
                    "类名是否使用 PascalCase",
                    "属性名是否使用 camelCase",
                    "名称是否清晰易懂",
                    "避免缩写和歧义"
                ]
            },
            "structure": {
                "weight": 0.25,
                "description": "层次结构",
                "checks": [
                    "类层次是否合理",
                    "属性定义是否完整",
                    "是否存在冗余定义",
                    "继承关系是否清晰"
                ]
            },
            "semantics": {
                "weight": 0.25,
                "description": "语义一致性",
                "checks": [
                    "类和属性是否匹配",
                    "是否存在矛盾定义",
                    "领域范围是否合理",
                    "关系是否双向定义"
                ]
            },
            "completeness": {
                "weight": 0.15,
                "description": "完整性",
                "checks": [
                    "必要的注释是否存在",
                    "属性类型是否定义",
                    "示例是否充分",
                    "元数据是否完整"
                ]
            },
            "domain_coverage": {
                "weight": 0.15,
                "description": "领域覆盖",
                "checks": [
                    "是否覆盖主要概念",
                    "关键属性是否缺失",
                    "个体实例是否充分",
                    "是否需要扩展"
                ]
            }
        }
    
    def critique_ontology(self, 
                         ontology: Dict,
                         use_llm: bool = False,
                         context: str = "") -> OntologyCritiqueReport:
        """
        批判本体
        
        Args:
            ontology: 本体数据
            use_llm: 是否使用 LLM（否则使用规则）
            context: 上下文信息（可选）
        
        Returns:
            OntologyCritiqueReport: 批判报告
        """
        if use_llm and self.llm_client:
            return self._critique_with_llm(ontology, context)
        else:
            return self._critique_with_rules(ontology)
    
    def _critique_with_rules(self, ontology: Dict) -> OntologyCritiqueReport:
        """基于规则的批判（快速、无需 LLM）"""
        suggestions = []
        categories_scores = {}
        
        # 1. 命名规范检查
        naming_score, naming_suggestions = self._check_naming(ontology)
        categories_scores["naming"] = naming_score
        suggestions.extend(naming_suggestions)
        
        # 2. 结构检查
        structure_score, structure_suggestions = self._check_structure(ontology)
        categories_scores["structure"] = structure_score
        suggestions.extend(structure_suggestions)
        
        # 3. 语义检查
        semantics_score, semantics_suggestions = self._check_semantics(ontology)
        categories_scores["semantics"] = semantics_score
        suggestions.extend(semantics_suggestions)
        
        # 4. 完整性检查
        completeness_score, completeness_suggestions = self._check_completeness(ontology)
        categories_scores["completeness"] = completeness_score
        suggestions.extend(completeness_suggestions)
        
        # 5. 领域覆盖检查
        coverage_score, coverage_suggestions = self._check_domain_coverage(ontology)
        categories_scores["domain_coverage"] = coverage_score
        suggestions.extend(coverage_suggestions)
        
        # 计算总分（加权平均）
        total_score = sum(
            categories_scores[cat] * self.criteria[cat]["weight"]
            for cat in self.criteria
        )
        
        # 生成总结
        summary = self._generate_summary(total_score, categories_scores, suggestions)
        
        # 判断是否通过
        success = total_score >= 70 and not any(
            s.severity == CritiqueSeverity.CRITICAL for s in suggestions
        )
        
        return OntologyCritiqueReport(
            success=success,
            score=int(total_score),
            systemic_critique_summary=summary,
            actionable_ontology_fixes=suggestions,
            categories_scores=categories_scores
        )
    
    def _check_naming(self, ontology: Dict) -> tuple[int, List[Suggestion]]:
        """检查命名规范"""
        suggestions = []
        score = 100
        
        # 检查类名
        for class_name, class_def in ontology.get("classes", {}).items():
            # PascalCase 检查
            if not class_name[0].isupper():
                suggestions.append(Suggestion(
                    severity=CritiqueSeverity.WARNING,
                    category="naming",
                    description=f"类名 '{class_name}' 应使用 PascalCase（首字母大写）",
                    location=class_name,
                    fix_hint=f"建议改为: {class_name.capitalize()}"
                ))
                score -= 10  # 增加扣分
            
            # 检查是否包含下划线
            if "_" in class_name:
                suggestions.append(Suggestion(
                    severity=CritiqueSeverity.WARNING,  # 提升为 WARNING
                    category="naming",
                    description=f"类名 '{class_name}' 包含下划线，建议使用 PascalCase",
                    location=class_name,
                    fix_hint=f"建议改为: {class_name.replace('_', '')}"
                ))
                score -= 8  # 增加扣分
        
        # 检查属性名
        for prop_name, prop_def in ontology.get("objectProperties", {}).items():
            # camelCase 检查
            if prop_name[0].isupper():
                suggestions.append(Suggestion(
                    severity=CritiqueSeverity.WARNING,
                    category="naming",
                    description=f"属性名 '{prop_name}' 应使用 camelCase（首字母小写）",
                    location=prop_name,
                    fix_hint=f"建议改为: {prop_name[0].lower() + prop_name[1:]}"
                ))
                score -= 10  # 增加扣分
        
        return max(0, score), suggestions
    
    def _check_structure(self, ontology: Dict) -> tuple[int, List[Suggestion]]:
        """检查层次结构"""
        suggestions = []
        score = 100
        
        classes = ontology.get("classes", {})
        props = ontology.get("objectProperties", {})
        
        # 检查是否有类
        if not classes:
            suggestions.append(Suggestion(
                severity=CritiqueSeverity.CRITICAL,
                category="structure",
                description="本体没有定义任何类",
                location=None,
                fix_hint="至少需要定义一个顶层类"
            ))
            score -= 50
        
        # 检查孤立类（没有属性的类）
        for class_name in classes:
            has_property = any(
                class_name in str(prop_def)
                for prop_def in props.values()
            )
            if not has_property and len(classes) > 1:
                suggestions.append(Suggestion(
                    severity=CritiqueSeverity.WARNING,  # 提升为 WARNING
                    category="structure",
                    description=f"类 '{class_name}' 没有关联任何属性",
                    location=class_name,
                    fix_hint="考虑添加相关属性或与其他类建立关系"
                ))
                score -= 5  # 增加扣分
        
        return max(0, score), suggestions
    
    def _check_semantics(self, ontology: Dict) -> tuple[int, List[Suggestion]]:
        """检查语义一致性"""
        suggestions = []
        score = 100
        
        # 检查属性是否有类型定义
        for prop_name, prop_def in ontology.get("objectProperties", {}).items():
            if "domain" not in prop_def and "range" not in prop_def:
                suggestions.append(Suggestion(
                    severity=CritiqueSeverity.WARNING,
                    category="semantics",
                    description=f"属性 '{prop_name}' 缺少 domain 或 range 定义",
                    location=prop_name,
                    fix_hint="建议添加 domain 和 range 定义"
                ))
                score -= 10  # 增加扣分
        
        return max(0, score), suggestions
    
    def _check_completeness(self, ontology: Dict) -> tuple[int, List[Suggestion]]:
        """检查完整性"""
        suggestions = []
        score = 100
        
        # 检查类是否有注释
        for class_name, class_def in ontology.get("classes", {}).items():
            if "comment" not in class_def and "description" not in class_def:
                suggestions.append(Suggestion(
                    severity=CritiqueSeverity.WARNING,  # 提升为 WARNING
                    category="completeness",
                    description=f"类 '{class_name}' 缺少注释或描述",
                    location=class_name,
                    fix_hint="建议添加 comment 字段说明类的用途"
                ))
                score -= 8  # 增加扣分
        
        # 检查元数据
        if "metadata" not in ontology:
            suggestions.append(Suggestion(
                severity=CritiqueSeverity.WARNING,
                category="completeness",
                description="本体缺少元数据（metadata）",
                location=None,
                fix_hint="建议添加 metadata 字段，包含版本、创建时间等信息"
            ))
            score -= 15  # 增加扣分
        
        return max(0, score), suggestions
    
    def _check_domain_coverage(self, ontology: Dict) -> tuple[int, List[Suggestion]]:
        """检查领域覆盖"""
        suggestions = []
        score = 100
        
        classes = ontology.get("classes", {})
        individuals = ontology.get("individuals", {})
        
        # 检查是否有足够的个体
        if classes and not individuals:
            suggestions.append(Suggestion(
                severity=CritiqueSeverity.WARNING,  # 提升为 WARNING
                category="domain_coverage",
                description="本体没有定义任何个体实例",
                location=None,
                fix_hint="建议添加一些具体的个体实例"
            ))
            score -= 15  # 增加扣分
        
        # 检查个体与类的比例
        if classes and individuals:
            ratio = len(individuals) / len(classes)
            if ratio < 0.5:
                suggestions.append(Suggestion(
                    severity=CritiqueSeverity.INFO,
                    category="domain_coverage",
                    description=f"个体实例数量较少（{len(individuals)} 个，类 {len(classes)} 个）",
                    location=None,
                    fix_hint="建议为每个类至少添加 1-2 个个体实例"
                ))
                score -= 8  # 增加扣分
        
        return max(0, score), suggestions
    
    def _generate_summary(self, 
                         total_score: float,
                         categories_scores: Dict[str, int],
                         suggestions: List[Suggestion]) -> str:
        """生成批判总结"""
        summary_parts = []
        
        # 总体评价
        if total_score >= 90:
            summary_parts.append("✅ 本体质量优秀")
        elif total_score >= 70:
            summary_parts.append("⚠️ 本体质量良好，但有改进空间")
        else:
            summary_parts.append("❌ 本体质量需要改进")
        
        # 各分类评分
        summary_parts.append("\n各维度评分：")
        for cat, score in categories_scores.items():
            emoji = "✅" if score >= 80 else "⚠️" if score >= 60 else "❌"
            summary_parts.append(f"  {emoji} {self.criteria[cat]['description']}: {score}/100")
        
        # 严重问题统计
        critical = sum(1 for s in suggestions if s.severity == CritiqueSeverity.CRITICAL)
        warnings = sum(1 for s in suggestions if s.severity == CritiqueSeverity.WARNING)
        
        if critical > 0:
            summary_parts.append(f"\n🔴 严重问题: {critical} 个")
        if warnings > 0:
            summary_parts.append(f"🟡 警告: {warnings} 个")
        
        return "\n".join(summary_parts)
    
    def _critique_with_llm(self, 
                          ontology: Dict,
                          context: str) -> OntologyCritiqueReport:
        """使用 LLM 进行批判（真实 LLM 调用）"""
        # TODO: 实现真实的 LLM 调用
        # 目前回退到规则检查
        return self._critique_with_rules(ontology)


def main():
    """测试 LLM 本体批判系统"""
    import argparse
    
    parser = argparse.ArgumentParser(description="LLM 本体批判系统")
    parser.add_argument("--ontology", required=True, help="本体文件路径")
    parser.add_argument("--use-llm", action="store_true", help="使用 LLM（需要 API）")
    parser.add_argument("--context", default="", help="上下文信息")
    
    args = parser.parse_args()
    
    print("🔍 LLM 本体批判系统启动")
    print("=" * 60)
    
    # 加载本体
    with open(args.ontology, 'r', encoding='utf-8') as f:
        ontology = json.load(f)
    
    # 创建批判器
    critic = OntologyCritic()
    
    # 执行批判
    report = critic.critique_ontology(
        ontology,
        use_llm=args.use_llm,
        context=args.context
    )
    
    # 打印报告
    print("\n" + "=" * 60)
    print("📊 批判报告")
    print("=" * 60)
    print(f"\n总分: {report.score}/100")
    print(f"状态: {'✅ 通过' if report.success else '❌ 未通过'}")
    print(f"\n{report.systemic_critique_summary}")
    
    if report.actionable_ontology_fixes:
        print("\n改进建议:")
        for i, suggestion in enumerate(report.actionable_ontology_fixes, 1):
            severity_emoji = {
                CritiqueSeverity.CRITICAL: "🔴",
                CritiqueSeverity.WARNING: "🟡",
                CritiqueSeverity.INFO: "ℹ️"
            }[suggestion.severity]
            
            print(f"\n{i}. {severity_emoji} [{suggestion.category}] {suggestion.description}")
            if suggestion.location:
                print(f"   位置: {suggestion.location}")
            if suggestion.fix_hint:
                print(f"   建议: {suggestion.fix_hint}")
    
    print("\n" + "=" * 60)
    if report.success:
        print("✅ 本体批判完成，质量合格！")
    else:
        print("❌ 本体需要改进，请参考上述建议。")
    
    return 0 if report.success else 1


if __name__ == '__main__':
    exit(main())
