#!/usr/bin/env python3
"""
Supabase 全量数据恢复脚本
支持多种 JSON 格式的批量恢复
"""

import json
import sys
import uuid
from pathlib import Path
from typing import Dict, List, Any, Optional
import requests
from datetime import datetime
import os

# Supabase 配置
SUPABASE_URL = os.environ.get('SUPABASE_URL', 'http://localhost:54321')
SUPABASE_SERVICE_KEY = os.environ.get('SUPABASE_SERVICE_KEY', '')

class SupabaseBulkRestorer:
    """Supabase 批量恢复器"""

    def __init__(self):
        """初始化"""
        self.url = SUPABASE_URL
        self.key = SUPABASE_SERVICE_KEY

        if not self.url or not self.key:
            raise ValueError("请设置 SUPABASE_URL 和 SUPABASE_SERVICE_KEY 环境变量")

        self.headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal"
        }

        # 统计
        self.stats = {
            "materials_added": 0,
            "properties_added": 0,
            "errors": []
        }

        # 材料缓存（避免重复插入）
        self.material_cache: Dict[str, str] = {}

    def get_or_create_material(self, name: str, chemical_formula: str = "", material_type: str = "StructuralMaterial") -> Optional[str]:
        """获取或创建材料记录"""
        # 检查缓存
        cache_key = f"{name}:{chemical_formula}"
        if cache_key in self.material_cache:
            return self.material_cache[cache_key]

        # 尝试查询已存在的材料
        try:
            response = requests.get(
                f"{self.url}/rest/v1/materials?name=eq.{name}&limit=1",
                headers=self.headers,
                timeout=10
            )

            if response.status_code == 200 and response.json():
                material_id = response.json()[0]['id']
                self.material_cache[cache_key] = material_id
                return material_id
        except:
            pass

        # 插入新材料
        try:
            material = {
                "id": str(uuid.uuid4()),
                "name": name,
                "chemical_formula": chemical_formula,
                "material_type": material_type,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }

            response = requests.post(
                f"{self.url}/rest/v1/materials",
                headers=self.headers,
                json=material,
                timeout=30
            )

            if response.status_code in [200, 201]:
                self.stats["materials_added"] += 1
                self.material_cache[cache_key] = material["id"]
                print(f"  ✅ 新增材料: {name}")
                return material["id"]
            else:
                self.stats["errors"].append(f"插入材料失败 ({name}): HTTP {response.status_code}")
                return None

        except Exception as e:
            self.stats["errors"].append(f"插入材料异常 ({name}): {str(e)[:50]}")
            return None

    def insert_property(
        self,
        material_id: str,
        property_name: str,
        property_value: float,
        property_unit: str = "",
        measurement_temperature: Optional[float] = None
    ) -> bool:
        """插入性能记录"""
        try:
            prop = {
                "id": str(uuid.uuid4()),
                "material_id": material_id,
                "property_name": property_name,
                "property_value": property_value,
                "property_unit": property_unit,
                "measurement_temperature": measurement_temperature,
                "created_at": datetime.now().isoformat()
            }

            response = requests.post(
                f"{self.url}/rest/v1/material_properties",
                headers=self.headers,
                json=prop,
                timeout=30
            )

            if response.status_code in [200, 201]:
                self.stats["properties_added"] += 1
                return True
            else:
                self.stats["errors"].append(f"插入性能失败 ({property_name}): HTTP {response.status_code}")
                return False

        except Exception as e:
            self.stats["errors"].append(f"插入性能异常 ({property_name}): {str(e)[:50]}")
            return False

    def restore_uhea_extraction(self, json_path: str) -> bool:
        """恢复 U-HEA / 通用 alloy 提取数据"""
        print(f"\n📄 处理合金提取数据: {json_path}")

        try:
            with open(json_path) as f:
                data = json.load(f)

            if "alloys" not in data:
                print("  ⚠️ 未找到 alloys 数据")
                return True

            for alloy in data["alloys"]:
                name = alloy.get("name", "Unknown")
                composition = alloy.get("composition", {})
                chemical_formula = ",".join([f"{k}:{v}" for k, v in composition.items()])

                material_id = self.get_or_create_material(
                    name=name,
                    chemical_formula=chemical_formula,
                    material_type="FuelMaterial"
                )

                if not material_id:
                    continue

                properties = alloy.get("properties", {})
                self._insert_numeric_properties(material_id, properties)

            return True

        except Exception as e:
            self.stats["errors"].append(f"处理合金数据异常: {str(e)[:50]}")
            return False

    def restore_materials_extraction(self, json_path: str) -> bool:
        """恢复包含 materials 数组的提取数据（如 U-Mo）"""
        print(f"\n📄 处理 materials 提取数据: {json_path}")

        try:
            with open(json_path) as f:
                data = json.load(f)

            if "materials" not in data:
                print("  ⚠️ 未找到 materials 数据")
                return True

            for material in data["materials"]:
                name = material.get("name", "Unknown")
                composition = material.get("composition", {})
                chemical_formula = ",".join([f"{k}:{v}" for k, v in composition.items()])
                raw_type = material.get("type", "FuelMaterial")
                material_type = "FuelMaterial" if raw_type in ["NuclearFuel", "FuelMaterial"] else "StructuralMaterial"

                material_id = self.get_or_create_material(
                    name=name,
                    chemical_formula=chemical_formula,
                    material_type=material_type
                )

                if not material_id:
                    continue

                properties = material.get("properties", {})
                self._insert_numeric_properties(material_id, properties)

            return True

        except Exception as e:
            self.stats["errors"].append(f"处理 materials 数据异常: {str(e)[:50]}")
            return False

    def restore_datapoints_format(self, json_path: str) -> bool:
        """恢复包含 data_points 结构的 JSON 文件"""
        print(f"\n📄 处理 data_points 格式: {json_path}")

        try:
            with open(json_path) as f:
                data = json.load(f)

            data_points = data.get("data_points", {})
            if not data_points:
                print("  ⚠️ 未找到 data_points 数据")
                return True

            # 获取材料名
            alloy_system = data.get("metadata", {}).get("alloy_system", "Unknown")
            # 提取材料简称
            material_name = alloy_system.split("(")[0].strip() if "(" in alloy_system else alloy_system.strip()

            material_id = self.get_or_create_material(
                name=material_name,
                material_type="FuelMaterial"
            )

            if not material_id:
                return False

            # 遍历 data_points 下的所有类别
            for category, points in data_points.items():
                if isinstance(points, list):
                    for point in points:
                        value = point.get("value")
                        if isinstance(value, (int, float)):
                            param = point.get("parameter", category)
                            self.insert_property(
                                material_id=material_id,
                                property_name=f"{category} - {param}",
                                property_value=float(value),
                                property_unit=point.get("unit", "")
                            )

            return True

        except Exception as e:
            self.stats["errors"].append(f"处理 data_points 格式异常: {str(e)[:50]}")
            return False

    def _insert_numeric_properties(self, material_id: str, properties: Dict[str, Any]):
        """递归插入 properties 中的数值型属性"""
        for prop_name, prop_data in properties.items():
            if isinstance(prop_data, dict):
                if "value" in prop_data and isinstance(prop_data["value"], (int, float)):
                    self.insert_property(
                        material_id=material_id,
                        property_name=prop_name,
                        property_value=float(prop_data["value"]),
                        property_unit=prop_data.get("unit", "")
                    )
                else:
                    nested_numeric = {k: v for k, v in prop_data.items() if isinstance(v, (int, float))}
                    for nested_name, nested_value in nested_numeric.items():
                        self.insert_property(
                            material_id=material_id,
                            property_name=f"{prop_name}.{nested_name}",
                            property_value=float(nested_value),
                            property_unit=prop_data.get("unit", "")
                        )
    def restore_uzr_performance(self, json_path: str) -> bool:
        """恢复 UZr 性能数据（已有实现）"""
        print(f"\n📄 处理 UZr 性能数据: {json_path}")

        try:
            with open(json_path) as f:
                data = json.load(f)

            # 插入 U-Zr 合金材料
            material_id = self.get_or_create_material(
                name="U-Zr alloy",
                chemical_formula="U-Zr",
                material_type="FuelMaterial"
            )

            if not material_id:
                print("  ❌ 插入 U-Zr 材料失败")
                return False

            # 提取扩散系数数据
            if "diffusion_coefficients" in data:
                self._extract_diffusion_data(material_id, data["diffusion_coefficients"])

            # 提取辐照肿胀数据
            if "irradiation_effects" in data:
                self._extract_irradiation_data(material_id, data["irradiation_effects"])

            return True

        except Exception as e:
            self.stats["errors"].append(f"处理 UZr 数据异常: {str(e)[:50]}")
            return False

    def _extract_diffusion_data(self, material_id: str, diff_data: Dict):
        """提取扩散系数数据"""
        if "interdiffusion" in diff_data and "data_points" in diff_data["interdiffusion"]:
            for point in diff_data["interdiffusion"]["data_points"]:
                if "value" in point and isinstance(point["value"], (int, float)):
                    self.insert_property(
                        material_id=material_id,
                        property_name=f"互扩散系数 - {point.get('parameter', 'unknown')}",
                        property_value=float(point["value"]),
                        property_unit=point.get("unit", "")
                    )

    def _extract_irradiation_data(self, material_id: str, irrad_data: Dict):
        """提取辐照效应数据"""
        # 肿胀数据
        if "swelling" in irrad_data and "data_points" in irrad_data["swelling"]:
            for point in irrad_data["swelling"]["data_points"]:
                if "value" in point and isinstance(point["value"], (int, float)):
                    self.insert_property(
                        material_id=material_id,
                        property_name=f"辐照肿胀 - {point.get('parameter', 'swelling')}",
                        property_value=float(point["value"]),
                        property_unit=point.get("unit", "%")
                    )

        # 燃耗性能
        if "burnup_performance" in irrad_data and "data_points" in irrad_data["burnup_performance"]:
            for point in irrad_data["burnup_performance"]["data_points"]:
                if "peak_cladding_temp_C" in point:
                    self.insert_property(
                        material_id=material_id,
                        property_name=f"包壳峰值温度 - {point.get('reactor', 'unknown')}",
                        property_value=float(point["peak_cladding_temp_C"]),
                        property_unit="°C"
                    )

                if "burnup_percent_FIMA" in point:
                    self.insert_property(
                        material_id=material_id,
                        property_name=f"燃耗 - {point.get('reactor', 'unknown')}",
                        property_value=float(point["burnup_percent_FIMA"]),
                        property_unit="% FIMA"
                    )

    def restore_file(self, json_path: str) -> bool:
        """根据文件类型自动选择恢复策略"""
        file_path = Path(json_path)
        file_name = file_path.name.lower()

        try:
            if "uhea" in file_name or "xu_2024" in file_name:
                return self.restore_uhea_extraction(json_path)
            elif "uzr_performance" in file_name:
                return self.restore_uzr_performance(json_path)
            elif "umo" in file_name or "u-mo" in file_name:
                return self.restore_materials_extraction(json_path)
            else:
                # 尝试通用 data_points 格式
                return self.restore_datapoints_format(json_path)

        except Exception as e:
            self.stats["errors"].append(f"处理文件异常 ({file_name}): {str(e)[:50]}")
            return False

    def print_summary(self):
        """打印恢复摘要"""
        print(f"\n{'='*60}")
        print("数据恢复摘要:")
        print(f"  新增材料: {self.stats['materials_added']}")
        print(f"  新增性能: {self.stats['properties_added']}")
        print(f"  错误数: {len(self.stats['errors'])}")

        if self.stats['errors']:
            print(f"\n错误列表:")
            for err in self.stats['errors'][:10]:
                print(f"  - {err}")
            if len(self.stats['errors']) > 10:
                print(f"  ... 还有 {len(self.stats['errors']) - 10} 个错误")

        print(f"{'='*60}")

def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="Supabase 批量数据恢复工具")
    parser.add_argument("--file", help="单个 JSON 文件路径")
    parser.add_argument("--dir", help="包含 JSON 文件的目录路径")
    parser.add_argument("--pattern", default="*.json", help="文件匹配模式（默认: *.json）")

    args = parser.parse_args()

    try:
        restorer = SupabaseBulkRestorer()

        if args.file:
            # 单文件恢复
            success = restorer.restore_file(args.file)
        elif args.dir:
            # 目录批量恢复
            dir_path = Path(args.dir)
            json_files = list(dir_path.glob(args.pattern))

            print(f"找到 {len(json_files)} 个 JSON 文件")

            for json_file in json_files:
                restorer.restore_file(str(json_file))

            success = True
        else:
            print("请指定 --file 或 --dir 参数")
            sys.exit(1)

        if success:
            restorer.print_summary()
            sys.exit(0)
        else:
            print("\n❌ 恢复失败")
            sys.exit(1)

    except Exception as e:
        print(f"\n❌ 恢复异常: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
