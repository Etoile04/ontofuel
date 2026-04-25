#!/usr/bin/env python3
"""
Supabase 数据恢复脚本
从本地 JSON 文件恢复材料性能数据到 Supabase
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
DB_URL = os.environ.get('DATABASE_URL', 'postgresql://postgres:postgres@localhost:54322/postgres')

class SupabaseRestorer:
    """Supabase 数据恢复器"""

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

    def insert_material(self, name: str, chemical_formula: str = "", material_type: str = "StructuralMaterial") -> Optional[str]:
        """插入材料记录"""
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

    def restore_uzr_performance_data(self, json_path: str) -> bool:
        """恢复 UZr 性能数据"""
        print(f"\n📄 处理文件: {json_path}")

        try:
            with open(json_path) as f:
                data = json.load(f)

            # 插入 U-Zr 合金材料
            material_id = self.insert_material(
                name="U-Zr alloy",
                chemical_formula="U-Zr",
                material_type="FuelMaterial"
            )

            if not material_id:
                print("❌ 插入 U-Zr 材料失败")
                return False

            print(f"✅ 材料插入成功: U-Zr alloy (ID: {material_id})")

            # 提取扩散系数数据
            if "diffusion_coefficients" in data:
                self._extract_diffusion_data(material_id, data["diffusion_coefficients"])

            # 提取辐照肿胀数据
            if "irradiation_effects" in data:
                self._extract_irradiation_data(material_id, data["irradiation_effects"])

            return True

        except Exception as e:
            self.stats["errors"].append(f"处理文件异常: {str(e)[:50]}")
            return False

    def _extract_diffusion_data(self, material_id: str, diff_data: Dict):
        """提取扩散系数数据"""
        print("\n🔍 提取扩散系数数据...")

        # 互扩散系数
        if "interdiffusion" in diff_data and "data_points" in diff_data["interdiffusion"]:
            for point in diff_data["interdiffusion"]["data_points"]:
                if "value" in point and isinstance(point["value"], (int, float)):
                    self.insert_property(
                        material_id=material_id,
                        property_name=f"互扩散系数 - {point.get('parameter', 'unknown')}",
                        property_value=float(point["value"]),
                        property_unit=point.get("unit", ""),
                        measurement_temperature=None
                    )

        # 晶界扩散
        if "grain_boundary_diffusion" in diff_data and "data_points" in diff_data["grain_boundary_diffusion"]:
            for point in diff_data["grain_boundary_diffusion"]["data_points"]:
                # 晶界数据通常没有数值，跳过
                pass

        print(f"✅ 扩散系数数据提取完成")

    def _extract_irradiation_data(self, material_id: str, irrad_data: Dict):
        """提取辐照效应数据"""
        print("\n🔍 提取辐照效应数据...")

        # 肿胀数据
        if "swelling" in irrad_data and "data_points" in irrad_data["swelling"]:
            for point in irrad_data["swelling"]["data_points"]:
                if "value" in point and isinstance(point["value"], (int, float)):
                    self.insert_property(
                        material_id=material_id,
                        property_name=f"辐照肿胀 - {point.get('parameter', 'swelling')}",
                        property_value=float(point["value"]),
                        property_unit=point.get("unit", "%"),
                        measurement_temperature=None
                    )

        # 燃耗性能
        if "burnup_performance" in irrad_data and "data_points" in irrad_data["burnup_performance"]:
            for point in irrad_data["burnup_performance"]["data_points"]:
                if "peak_cladding_temp_C" in point:
                    self.insert_property(
                        material_id=material_id,
                        property_name=f"包壳峰值温度 - {point.get('reactor', 'unknown')}",
                        property_value=float(point["peak_cladding_temp_C"]),
                        property_unit="°C",
                        measurement_temperature=None
                    )

                if "burnup_percent_FIMA" in point:
                    self.insert_property(
                        material_id=material_id,
                        property_name=f"燃耗 - {point.get('reactor', 'unknown')}",
                        property_value=float(point["burnup_percent_FIMA"]),
                        property_unit="% FIMA",
                        measurement_temperature=None
                    )

        print(f"✅ 辐照效应数据提取完成")

    def print_summary(self):
        """打印恢复摘要"""
        print(f"\n{'='*60}")
        print("数据恢复摘要:")
        print(f"  新增材料: {self.stats['materials_added']}")
        print(f"  新增性能: {self.stats['properties_added']}")
        print(f"  错误数: {len(self.stats['errors'])}")

        if self.stats['errors']:
            print(f"\n错误列表:")
            for err in self.stats['errors'][:5]:
                print(f"  - {err}")

        print(f"{'='*60}")

def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="Supabase 数据恢复工具")
    parser.add_argument("--file", required=True, help="JSON 数据文件路径")
    parser.add_argument("--url", help="Supabase URL（覆盖环境变量）")
    parser.add_argument("--key", help="Supabase Service Key（覆盖环境变量）")

    args = parser.parse_args()

    # 覆盖配置
    if args.url:
        os.environ['SUPABASE_URL'] = args.url
    if args.key:
        os.environ['SUPABASE_SERVICE_KEY'] = args.key

    try:
        restorer = SupabaseRestorer()

        # 根据文件类型选择恢复策略
        file_path = Path(args.file)

        if "uzr_performance" in file_path.name:
            success = restorer.restore_uzr_performance_data(args.file)
        else:
            print(f"⚠️ 不支持的文件类型: {file_path.name}")
            success = False

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
