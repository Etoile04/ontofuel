"""Extractor — extract structured knowledge from text chunks.

Supports two extraction strategies:
  1. Rule-based: Pattern matching for common material science data
  2. Template-based: Structured extraction using property templates

For LLM-enhanced extraction, use the full OntoFuel pipeline with
an LLM backend (see docs/extraction_guide.md).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from ..core.ontology import load_ontology, get_classes


@dataclass
class ExtractionResult:
    """Result of extracting knowledge from a chunk.

    Attributes:
        source: Source chunk title or identifier.
        individuals: List of extracted individuals (material instances).
        properties: List of extracted property values.
        relationships: List of extracted relationships.
        metadata: Extraction metadata (method, confidence, etc.).
    """
    source: str
    individuals: list[dict[str, Any]] = field(default_factory=list)
    properties: list[dict[str, Any]] = field(default_factory=list)
    relationships: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def total_items(self) -> int:
        return len(self.individuals) + len(self.properties) + len(self.relationships)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "individuals": self.individuals,
            "properties": self.properties,
            "relationships": self.relationships,
            "total_items": self.total_items,
            "metadata": self.metadata,
        }


# ---- Common patterns for materials science ----

# Alloy composition: U-10Mo, U-10Zr-4.5Sn, Fe-25Cr-20Ni-0.5C
ALLOY_PATTERN = re.compile(
    r"\b([A-Z][a-z]?(?:-\d+\.?\d*(?:[A-Z][a-z]?)?)+(?:-\d+\.?\d*(?:[A-Z][a-z]?)?)*)\b"
)

# Numeric property: density: 15.8 g/cm³, Tm = 1132°C
NUMERIC_PROP_PATTERN = re.compile(
    r"([\w\s]+?)(?:[:=]\s*| is\s+| of\s+)(\d+\.?\d*)\s*([°%\w/³²·]+)"
)

# Temperature range: 25–800°C, 300-500 K
TEMP_RANGE_PATTERN = re.compile(
    r"(\d+\.?\d*)\s*[–\-]\s*(\d+\.?\d*)\s*(°[CF]|K)"
)

# Phase: γ phase, BCC, FCC, α-U
PHASE_PATTERN = re.compile(
    r"\b(?:γ|α|β|δ|BCC|FCC|HCP|bcc|fcc|hcp)\s*(?:phase|Phase|U|structure)?\b",
    re.IGNORECASE,
)

# Percentage: 10 wt%, 5 at%, 20%
PERCENTAGE_PATTERN = re.compile(
    r"(\d+\.?\d*)\s*(wt%|at%|vol%|mol%)"
)

# Property keywords common in materials science
PROPERTY_KEYWORDS = {
    "density": ["density", "ρ", "mass density"],
    "melting_point": ["melting point", "Tm", "melting temperature"],
    "thermal_conductivity": ["thermal conductivity", "κ", "k", "λ"],
    "specific_heat": ["specific heat", "Cp", "heat capacity"],
    "thermal_expansion": ["thermal expansion", "CTE", "α", "coefficient of thermal expansion"],
    "yield_strength": ["yield strength", "σy", "YS"],
    "tensile_strength": ["tensile strength", "ultimate tensile", "UTS", "σu"],
    "elastic_modulus": ["elastic modulus", "Young's modulus", "E"],
    "hardness": ["hardness", "HB", "HV", "HRC"],
    "diffusivity": ["diffusion coefficient", "diffusivity", "D"],
    "swelling": ["swelling", "ΔV/V", "volume change"],
    "irradiation": ["irradiation", "fluence", "dpa", "displacement"],
    "conductivity_electrical": ["electrical conductivity", "resistivity", "ρe"],
    "corrosion_rate": ["corrosion rate", "corrosion resistance"],
}


class Extractor:
    """Extract structured knowledge from text.

    Uses rule-based pattern matching for common material science data.
    Can be extended with LLM backends for more complex extraction.

    Example:
        >>> ext = Extractor()
        >>> result = ext.extract("U-10Mo alloy has density 15.8 g/cm³")
        >>> print(result.individuals)
    """

    def __init__(self, ontology: dict | None = None):
        """Initialize extractor.

        Args:
            ontology: Optional pre-loaded ontology for matching.
        """
        self._ontology = ontology
        self._class_names: set[str] | None = None

    @property
    def ontology(self) -> dict:
        if self._ontology is None:
            self._ontology = load_ontology()
        return self._ontology

    @property
    def class_names(self) -> set[str]:
        if self._class_names is None:
            classes = get_classes(self.ontology)
            self._class_names = {
                c.get("name", c.get("className", ""))
                for c in classes
            }
            self._class_names.discard("")
        return self._class_names

    def extract(self, text: str, source: str = "unknown") -> ExtractionResult:
        """Extract knowledge from a text chunk.

        Args:
            text: Input text to extract from.
            source: Source identifier (chunk title, file name, etc.).

        Returns:
            ExtractionResult with extracted individuals, properties, relationships.
        """
        result = ExtractionResult(
            source=source,
            metadata={
                "method": "rule-based",
                "text_length": len(text),
            },
        )

        # 1. Extract alloy compositions
        alloys = self._extract_alloys(text)
        result.individuals.extend(alloys)

        # 2. Extract numeric properties
        props = self._extract_properties(text)
        result.properties.extend(props)

        # 3. Extract phases
        phases = self._extract_phases(text)
        result.relationships.extend(phases)

        # 4. Extract temperature ranges
        temps = self._extract_temperatures(text)
        result.metadata["temperature_ranges"] = temps

        return result

    def extract_with_template(
        self,
        text: str,
        template: dict[str, Any],
        source: str = "unknown",
    ) -> ExtractionResult:
        """Extract using a property template.

        Args:
            text: Input text.
            template: Dict with property names and extraction rules.
            source: Source identifier.

        Returns:
            ExtractionResult with template-matched properties.
        """
        result = ExtractionResult(
            source=source,
            metadata={"method": "template-based", "template": list(template.keys())},
        )

        for prop_name, rules in template.items():
            if isinstance(rules, str):
                # Simple string pattern
                patterns = [rules]
            elif isinstance(rules, list):
                patterns = rules
            elif isinstance(rules, dict):
                patterns = rules.get("patterns", [])
            else:
                continue

            for pattern_str in patterns:
                regex = re.compile(pattern_str, re.IGNORECASE)
                for match in regex.finditer(text):
                    groups = match.groups()
                    if groups:
                        value = groups[0] if len(groups) == 1 else list(groups)
                        result.properties.append({
                            "name": prop_name,
                            "value": value,
                            "context": match.group(0),
                            "position": match.start(),
                        })

        return result

    def _extract_alloys(self, text: str) -> list[dict[str, Any]]:
        """Extract alloy compositions from text."""
        individuals = []
        seen = set()

        for match in ALLOY_PATTERN.finditer(text):
            name = match.group(1)
            if name in seen or len(name) < 3:
                continue
            seen.add(name)

            # Parse composition
            composition = self._parse_alloy_composition(name)

            individuals.append({
                "name": name,
                "type": "Alloy",
                "composition": composition,
                "extraction_confidence": 0.8,
            })

        return individuals

    def _extract_properties(self, text: str) -> list[dict[str, Any]]:
        """Extract numeric properties from text."""
        props = []

        for match in NUMERIC_PROP_PATTERN.finditer(text):
            prop_name = match.group(1).strip().lower()
            value = float(match.group(2))
            unit = match.group(3).strip()

            # Match against known property keywords
            matched_prop = None
            for canonical, keywords in PROPERTY_KEYWORDS.items():
                if any(kw in prop_name for kw in keywords):
                    matched_prop = canonical
                    break

            if matched_prop:
                props.append({
                    "name": matched_prop,
                    "value": value,
                    "unit": unit,
                    "raw_name": prop_name,
                    "context": match.group(0),
                })

        return props

    def _extract_phases(self, text: str) -> list[dict[str, Any]]:
        """Extract crystal phase information."""
        phases = []

        for match in PHASE_PATTERN.finditer(text):
            phase_str = match.group(0).strip()
            # Normalize
            phase_str = phase_str.replace("phase", "").replace("Phase", "").strip()
            if phase_str:
                phases.append({
                    "type": "phase",
                    "phase": phase_str,
                    "context": match.group(0),
                })

        return phases

    def _extract_temperatures(self, text: str) -> list[dict[str, Any]]:
        """Extract temperature ranges."""
        temps = []
        for match in TEMP_RANGE_PATTERN.finditer(text):
            temps.append({
                "min": float(match.group(1)),
                "max": float(match.group(2)),
                "unit": match.group(3),
            })
        return temps

    def _parse_alloy_composition(self, name: str) -> dict[str, float]:
        """Parse alloy name into element composition.

        Example: "U-10Mo" -> {"U": 90.0, "Mo": 10.0}
        """
        parts = name.split("-")
        composition: dict[str, float] = {}
        total_pct = 0.0

        for part in parts:
            # Split element symbol from number
            match = re.match(r"([A-Z][a-z]?)(\d+\.?\d*)?", part)
            if match:
                element = match.group(1)
                pct = float(match.group(2)) if match.group(2) else None
                if pct is not None:
                    composition[element] = pct
                    total_pct += pct

        # If there's a base element without percentage, calculate it
        if composition and total_pct < 100:
            base = parts[0]
            base_match = re.match(r"([A-Z][a-z]?)", base)
            if base_match and base_match.group(1) not in composition:
                composition[base_match.group(1)] = 100.0 - total_pct

        return composition
