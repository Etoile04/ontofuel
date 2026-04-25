#!/usr/bin/env python3
"""
本体语义一致性优化脚本
目标：将语义一致性从 0/100 提升到 90+/100（A级）

主要优化：
1. 为对象属性添加 domain 和 range 定义
2. 为关键类添加属性关联
3. 为关键类添加注释

作者：OntoFuel Extractor
日期：2026-03-09
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any


class OntologySemanticEnhancer:
    """本体语义一致性优化器"""
    
    def __init__(self, ontology_path: str):
        self.ontology_path = Path(ontology_path)
        self.ontology = None
        self.stats = {
            "properties_fixed": 0,
            "classes_annotated": 0,
            "classes_linked": 0
        }
        
    def load_ontology(self):
        """加载本体文件"""
        print(f"📂 加载本体文件: {self.ontology_path}")
        with open(self.ontology_path, 'r', encoding='utf-8') as f:
            self.ontology = json.load(f)
        print(f"✅ 本体加载成功")
        
    def save_ontology(self, output_path: str = None):
        """保存优化后的本体"""
        if output_path is None:
            output_path = self.ontology_path
            
        # 更新元数据
        self.ontology['metadata']['modified'] = datetime.now().isoformat()
        
        # 备份原文件
        backup_path = self.ontology_path.with_suffix('.json.backup')
        if not backup_path.exists():
            import shutil
            shutil.copy(self.ontology_path, backup_path)
            print(f"💾 已创建备份: {backup_path}")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.ontology, f, indent=2, ensure_ascii=False)
        print(f"✅ 本体已保存: {output_path}")
        
    def enhance_object_properties(self):
        """优化对象属性：添加 domain 和 range 定义"""
        print("\n" + "="*60)
        print("🔧 优化对象属性语义一致性")
        print("="*60)
        
        # 定义对象属性的 domain 和 range（基于本体语义）
        property_definitions = {
            # 材料关系属性
            "hasFiber": {
                "domain": "CompositeMaterial",
                "range": "SiCFiber",
                "comment": "Indicates the fiber component in a composite material"
            },
            "hasMatrix": {
                "domain": "CompositeMaterial",
                "range": "SiCMatrix",
                "comment": "Indicates the matrix component in a composite material"
            },
            "hasComponent": {
                "domain": "Material",
                "range": "Component",
                "comment": "Indicates a component of a material"
            },
            "hasComposition": {
                "domain": "Material",
                "range": "Element",
                "comment": "Indicates the elemental composition of a material"
            },
            "composedOf": {
                "domain": "Material",
                "range": "Element",
                "comment": "Indicates the elements that compose a material"
            },
            
            # 材料属性关系
            "hasProperty": {
                "domain": "Material",
                "range": "Property",
                "comment": "Indicates a property of a material"
            },
            "hasMechanicalProperty": {
                "domain": "Material",
                "range": "MechanicalProperty",
                "comment": "Indicates a mechanical property of a material"
            },
            "hasThermalProperty": {
                "domain": "Material",
                "range": "ThermalProperty",
                "comment": "Indicates a thermal property of a material"
            },
            "hasPhysicalProperty": {
                "domain": "Material",
                "range": "PhysicalProperty",
                "comment": "Indicates a physical property of a material"
            },
            "hasChemicalProperty": {
                "domain": "Material",
                "range": "ChemicalProperty",
                "comment": "Indicates a chemical property of a material"
            },
            "hasCrystalStructure": {
                "domain": "Material",
                "range": "CrystalStructure",
                "comment": "Indicates the crystal structure of a material"
            },
            "hasDiffusionCoefficient": {
                "domain": "Material",
                "range": "DiffusionCoefficient",
                "comment": "Indicates the diffusion coefficient of a material"
            },
            
            # 现象和行为关系
            "hasIrradiationEffect": {
                "domain": "Material",
                "range": "IrradiationEffect",
                "comment": "Indicates an irradiation effect on a material"
            },
            "exhibitsIrradiationEffect": {
                "domain": "Material",
                "range": "IrradiationEffect",
                "comment": "Indicates that a material exhibits an irradiation effect"
            },
            "exhibitsPhenomenon": {
                "domain": "Material",
                "range": "Phenomenon",
                "comment": "Indicates that a material exhibits a phenomenon"
            },
            "hasPhenomenon": {
                "domain": "Material",
                "range": "Phenomenon",
                "comment": "Indicates a phenomenon associated with a material"
            },
            "exhibitsFissionGasBehavior": {
                "domain": "NuclearFuel",
                "range": "FissionGasBehavior",
                "comment": "Indicates fission gas behavior in nuclear fuel"
            },
            "hasSwellingMechanism": {
                "domain": "Material",
                "range": "Swelling",
                "comment": "Indicates the swelling mechanism of a material"
            },
            
            # 因果关系
            "causes": {
                "domain": "Phenomenon",
                "range": "Phenomenon",
                "comment": "Indicates that one phenomenon causes another"
            },
            "leadsTo": {
                "domain": "Phenomenon",
                "range": "Phenomenon",
                "comment": "Indicates that one phenomenon leads to another"
            },
            "resultsIn": {
                "domain": "Process",
                "range": "Phenomenon",
                "comment": "Indicates that a process results in a phenomenon"
            },
            "affects": {
                "domain": "Phenomenon",
                "range": "Material",
                "comment": "Indicates that a phenomenon affects a material"
            },
            
            # 应用关系
            "usedFor": {
                "domain": "Material",
                "range": "Application",
                "comment": "Indicates the application of a material"
            },
            "usedIn": {
                "domain": "Material",
                "range": "NuclearApplication",
                "comment": "Indicates the nuclear application of a material"
            },
            "usedForApplication": {
                "domain": "Material",
                "range": "Application",
                "comment": "Indicates the application of a material"
            },
            "usedInReactorType": {
                "domain": "Material",
                "range": "ReactorType",
                "comment": "Indicates the reactor type where a material is used"
            },
            "hasApplication": {
                "domain": "Material",
                "range": "Application",
                "comment": "Indicates an application of a material"
            },
            
            # 反应和过程关系
            "undergoesReaction": {
                "domain": "Material",
                "range": "ChemicalReaction",
                "comment": "Indicates that a material undergoes a chemical reaction"
            },
            "forms": {
                "domain": "Material",
                "range": "Phase",
                "comment": "Indicates that a material forms a phase"
            },
            "formsPhase": {
                "domain": "Material",
                "range": "IntermetallicPhase",
                "comment": "Indicates that a material forms an intermetallic phase"
            },
            
            # 容易受到的影响
            "subjectTo": {
                "domain": "Material",
                "range": "Phenomenon",
                "comment": "Indicates that a material is subject to a phenomenon"
            },
            "susceptibleTo": {
                "domain": "Material",
                "range": "Phenomenon",
                "comment": "Indicates that a material is susceptible to a phenomenon"
            },
            
            # 加工技术
            "hasProcessingTechnique": {
                "domain": "Material",
                "range": "ProcessingTechnique",
                "comment": "Indicates the processing technique for a material"
            },
            
            # 冷却剂功能
            "coolantFunction": {
                "domain": "CoolantMaterial",
                "range": "CoolantFunction",
                "comment": "Indicates the function of a coolant material"
            },
            
            # 比较
            "comparesWith": {
                "domain": "Material",
                "range": "Material",
                "comment": "Indicates a comparison between materials"
            },
            
            # FCCI 相关
            "hasFCCI": {
                "domain": "NuclearFuel",
                "range": "FuelCladdingChemicalInteraction",
                "comment": "Indicates FCCI in nuclear fuel"
            },
            "causesWastage": {
                "domain": "FuelCladdingChemicalInteraction",
                "range": "CladdingWastage",
                "comment": "Indicates that FCCI causes cladding wastage"
            },
            "mitigatesFCCI": {
                "domain": "DiffusionBarrier",
                "range": "FuelCladdingChemicalInteraction",
                "comment": "Indicates that a barrier mitigates FCCI"
            },
            "preventsDiffusionOf": {
                "domain": "DiffusionBarrier",
                "range": "Element",
                "comment": "Indicates the element whose diffusion is prevented"
            },
            
            # 扩散相关
            "measuredInMaterial": {
                "domain": "DiffusionCoefficient",
                "range": "Material",
                "comment": "Indicates the material in which diffusion is measured"
            },
            "forElement": {
                "domain": "DiffusionCoefficient",
                "range": "Element",
                "comment": "Indicates the element for which diffusion coefficient is defined"
            },
            "conversionFrom": {
                "domain": "DiffusionCoefficient",
                "range": "DiffusionCoefficient",
                "comment": "Indicates conversion from one diffusion coefficient type"
            },
            "conversionTo": {
                "domain": "DiffusionCoefficient",
                "range": "DiffusionCoefficient",
                "comment": "Indicates conversion to one diffusion coefficient type"
            },
            "usedInConversion": {
                "domain": "Material",
                "range": "NuclearApplication",
                "comment": "Indicates the nuclear conversion application"
            },
            
            # 反应堆性能
            "hasReactorPerformance": {
                "domain": "Material",
                "range": "ReactorPerformance",
                "comment": "Indicates the reactor performance of a material"
            },
            "supportsObjective": {
                "domain": "Material",
                "range": "NonProliferationObjective",
                "comment": "Indicates that a material supports a non-proliferation objective"
            },
            
            # 稳定性
            "stabilizedBy": {
                "domain": "Phase",
                "range": "Element",
                "comment": "Indicates that a phase is stabilized by an element"
            },
            
            # 多型性
            "hasPolytype": {
                "domain": "CeramicMaterial",
                "range": "Polytype",
                "comment": "Indicates the polytype of a ceramic material"
            },
            "hasThermochemicalProperty": {
                "domain": "Material",
                "range": "ThermochemicalProperty",
                "comment": "Indicates the thermochemical property of a material"
            },
            
            # 模型和参数
            "governedBy": {
                "domain": "Phenomenon",
                "range": "ConstitutiveEquation",
                "comment": "Indicates that a phenomenon is governed by an equation"
            },
            "hasParameter": {
                "domain": "ConstitutiveEquation",
                "range": "DiffusionParameter",
                "comment": "Indicates a parameter of an equation"
            },
            "operatesIn": {
                "domain": "ConstitutiveEquation",
                "range": "TemperatureRegime",
                "comment": "Indicates the temperature regime where an equation operates"
            },
            "triggersAt": {
                "domain": "Swelling",
                "range": "BurnupThreshold",
                "comment": "Indicates the burnup threshold that triggers swelling"
            },
            "validFor": {
                "domain": "ConstitutiveEquation",
                "range": "Material",
                "comment": "Indicates the material for which an equation is valid"
            },
            
            # 气密性
            "hasGasLeakTightness": {
                "domain": "CladdingMaterial",
                "range": "GasLeakage",
                "comment": "Indicates the gas leak tightness of cladding material"
            }
        }
        
        # 更新对象属性
        object_properties = self.ontology.get('objectProperties', [])
        fixed_count = 0
        
        for prop in object_properties:
            prop_name = prop.get('name')
            if prop_name in property_definitions:
                definition = property_definitions[prop_name]
                
                # 添加 domain
                if 'domain' not in prop or not prop['domain']:
                    prop['domain'] = definition['domain']
                    fixed_count += 1
                    
                # 添加 range
                if 'range' not in prop or not prop['range']:
                    prop['range'] = definition['range']
                    fixed_count += 1
                    
                # 添加注释
                if 'comment' not in prop or not prop['comment']:
                    prop['comment'] = definition['comment']
                    fixed_count += 1
        
        self.stats['properties_fixed'] = fixed_count
        print(f"✅ 已修复 {fixed_count} 个对象属性定义")
        
    def add_class_annotations(self):
        """为关键类添加注释"""
        print("\n" + "="*60)
        print("📝 为关键类添加注释")
        print("="*60)
        
        # 关键类的注释定义
        class_annotations = {
            # 核心材料类
            "Material": "Base class for all materials in the ontology",
            "NuclearMaterial": "Materials used in nuclear applications",
            "StructuralMaterial": "Materials used for structural components in nuclear reactors",
            "CladdingMaterial": "Materials used as cladding in nuclear fuel elements",
            "CoolantMaterial": "Materials used as coolants in nuclear reactors",
            "CompositeMaterial": "Materials composed of two or more distinct phases",
            "CeramicMaterial": "Ceramic materials used in nuclear applications",
            "MetalAlloy": "Metallic alloys used in nuclear applications",
            
            # 高熵合金类
            "HighEntropyAlloy": "Alloys with five or more principal elements in equal or near-equal atomic percentages",
            "MediumEntropyAlloy": "Alloys with three or four principal elements",
            "UraniumHighEntropyAlloy": "High-entropy alloys containing uranium as a principal element",
            "UraniumMediumEntropyAlloy": "Medium-entropy alloys containing uranium",
            "CoCrFeMnNiAlloy": "Cantor alloy - a specific high-entropy alloy composition",
            
            # 性能类
            "Property": "Base class for material properties",
            "MechanicalProperty": "Mechanical properties of materials",
            "ThermalProperty": "Thermal properties of materials",
            "PhysicalProperty": "Physical properties of materials",
            "ChemicalProperty": "Chemical properties of materials",
            "NuclearProperty": "Nuclear-specific properties of materials",
            "ThermochemicalProperty": "Thermochemical properties of materials",
            
            # 现象类
            "Phenomenon": "Base class for material phenomena",
            "IrradiationEffect": "Effects caused by neutron irradiation",
            "Swelling": "Volume increase in materials due to irradiation",
            "VoidSwelling": "Swelling caused by void formation",
            "FissionGasBehavior": "Behavior of fission gases in nuclear fuel",
            "FissionGasRelease": "Release of fission gases from nuclear fuel",
            "Corrosion": "Degradation of materials by chemical reaction",
            "Embrittlement": "Loss of ductility in materials",
            
            # 核反应堆类
            "ReactorType": "Types of nuclear reactors",
            "FastBreederReactor": "Fast neutron spectrum breeder reactors",
            "NuclearApplication": "Applications in nuclear technology",
            
            # 燃料相关
            "NuclearFuel": "Materials used as nuclear fuel",
            "MOXFuel": "Mixed oxide nuclear fuel",
            "FuelCladdingChemicalInteraction": "Chemical interaction between fuel and cladding",
            
            # 扩散相关
            "DiffusionCoefficient": "Coefficients describing diffusion rates in materials",
            "TracerDiffusionCoefficient": "Diffusion coefficient measured by tracer methods",
            "DiffusionBarrier": "Barriers to prevent diffusion between materials",
            
            # 模型和方程
            "ConstitutiveEquation": "Equations describing material behavior",
            "RateEquation": "Equations describing rate processes",
            "DiffusionEquation": "Equations describing diffusion processes",
            "RateTheoryModel": "Models based on rate theory for defect evolution",
            "PhaseFieldModel": "Models using phase field methods",
            
            # 结构和相
            "CrystalStructure": "Crystal structure types of materials",
            "Phase": "Phases in materials",
            "IntermetallicPhase": "Intermetallic phases formed between elements",
            "SolidSolution": "Solid solution phases in alloys",
            
            # 其他重要类
            "Element": "Chemical elements",
            "Component": "Components in composite materials",
            "ProcessingTechnique": "Techniques for processing materials",
            "Application": "Applications of materials"
        }
        
        classes = self.ontology.get('classes', [])
        annotated_count = 0
        
        for cls in classes:
            cls_name = cls.get('name')
            if cls_name in class_annotations:
                if 'comment' not in cls or not cls['comment']:
                    cls['comment'] = class_annotations[cls_name]
                    annotated_count += 1
        
        self.stats['classes_annotated'] = annotated_count
        print(f"✅ 已为 {annotated_count} 个类添加注释")
        
    def add_class_property_links(self):
        """为关键类添加属性关联"""
        print("\n" + "="*60)
        print("🔗 为关键类添加属性关联")
        print("="*60)
        
        # 关键类的属性关联
        class_properties = {
            "HighEntropyAlloy": {
                "properties": ["configurationalEntropy", "mixingEntropy", "valenceElectronConcentration"],
                "objectProperties": ["hasMechanicalProperty", "hasThermalProperty"]
            },
            "UraniumHighEntropyAlloy": {
                "properties": ["uraniumContent", "density", "yieldStrength"],
                "objectProperties": ["hasMechanicalProperty", "hasReactorPerformance"]
            },
            "NuclearFuel": {
                "properties": ["enrichment", "burnup", "fissionGasRelease"],
                "objectProperties": ["hasProperty", "exhibitsFissionGasBehavior", "hasFCCI"]
            },
            "CladdingMaterial": {
                "properties": ["corrosionResistance", "creepResistance", "yieldStrength"],
                "objectProperties": ["hasProperty", "hasGasLeakTightness"]
            },
            "CoolantMaterial": {
                "properties": ["thermalConductivity", "density", "viscosity"],
                "objectProperties": ["coolantFunction"]
            },
            "CompositeMaterial": {
                "properties": ["fiberVolumeFraction", "matrixVolumeFraction"],
                "objectProperties": ["hasFiber", "hasMatrix", "hasComponent"]
            },
            "DiffusionCoefficient": {
                "properties": ["preExponentialFactor", "activationEnergy", "temperature"],
                "objectProperties": ["measuredInMaterial", "forElement"]
            }
        }
        
        classes = self.ontology.get('classes', [])
        linked_count = 0
        
        for cls in classes:
            cls_name = cls.get('name')
            if cls_name in class_properties:
                props = class_properties[cls_name]
                
                # 添加数据属性关联
                if 'properties' not in cls:
                    cls['properties'] = []
                for prop in props['properties']:
                    if prop not in cls['properties']:
                        cls['properties'].append(prop)
                        linked_count += 1
                
                # 添加对象属性关联
                if 'objectProperties' not in cls:
                    cls['objectProperties'] = []
                for prop in props['objectProperties']:
                    if prop not in cls['objectProperties']:
                        cls['objectProperties'].append(prop)
                        linked_count += 1
        
        self.stats['classes_linked'] = linked_count
        print(f"✅ 已为类添加 {linked_count} 个属性关联")
        
    def print_summary(self):
        """打印优化摘要"""
        print("\n" + "="*60)
        print("📊 优化摘要")
        print("="*60)
        print(f"✅ 对象属性修复: {self.stats['properties_fixed']}")
        print(f"✅ 类注释添加: {self.stats['classes_annotated']}")
        print(f"✅ 类属性关联: {self.stats['classes_linked']}")
        print(f"📊 总计优化: {sum(self.stats.values())} 项")
        print("="*60)
        
    def run(self):
        """运行优化流程"""
        print("\n" + "="*60)
        print("🚀 本体语义一致性优化开始")
        print("="*60)
        
        # 1. 加载本体
        self.load_ontology()
        
        # 2. 优化对象属性
        self.enhance_object_properties()
        
        # 3. 添加类注释
        self.add_class_annotations()
        
        # 4. 添加类属性关联
        self.add_class_property_links()
        
        # 5. 保存优化后的本体
        self.save_ontology()
        
        # 6. 打印摘要
        self.print_summary()
        
        print("\n✅ 优化完成！")


def main():
    if len(sys.argv) < 2:
        print("使用方法: python ontology_semantic_enhancer.py <ontology_path>")
        print("示例: python ontology_semantic_enhancer.py memory/trustgraph-fix/material_ontology_enhanced.json")
        sys.exit(1)
    
    ontology_path = sys.argv[1]
    enhancer = OntologySemanticEnhancer(ontology_path)
    enhancer.run()


if __name__ == "__main__":
    main()
