"""OntoFuel CLI — command-line interface for ontology operations."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def cmd_stats(args):
    """Show ontology statistics."""
    from .core.ontology import load_ontology, get_stats

    ont = load_ontology(args.ontology)
    stats = get_stats(ont)

    print("═══ OntoFuel Ontology Stats ═══")
    print(f"  Classes:            {stats['classes']}")
    print(f"  Object Properties:  {stats['object_properties']}")
    print(f"  Datatype Properties:{stats['datatype_properties']}")
    print(f"  Individuals:        {stats['individuals']}")

    if args.verbose:
        from .core.query import OntologyQuery
        q = OntologyQuery(ont)

        # Class distribution
        class_counts = {}
        for ind in q.individuals:
            cls = ind.get("class", "Unknown")
            if isinstance(cls, list):
                cls = cls[0] if cls else "Unknown"
            class_counts[cls] = class_counts.get(cls, 0) + 1

        print(f"\n  Top classes by individuals:")
        for cls, count in sorted(class_counts.items(), key=lambda x: -x[1])[:10]:
            print(f"    {cls}: {count}")


def cmd_query(args):
    """Search ontology entities."""
    from .core.ontology import load_ontology
    from .core.query import OntologyQuery

    ont = load_ontology(args.ontology)
    q = OntologyQuery(ont)

    if args.class_name:
        results = q.by_class(args.class_name)
        print(f"Individuals of class '{args.class_name}': {len(results)}")
    elif args.property:
        prop, _, value = args.property.partition("=")
        results = q.by_property(prop, value if value else None)
        print(f"Results for property '{prop}': {len(results)}")
    elif args.hierarchy:
        result = q.get_class_hierarchy(args.hierarchy)
        if result["class"]:
            print(f"Class: {result['class']['name']}")
        else:
            print(f"Class '{args.hierarchy}' not found")
        for child in result["children"]:
            print(f"  └─ {child['name']}")
        return
    else:
        results = q.search(args.query or "", category=args.category)
        print(f"Search '{args.query}': {len(results)} results")

    # Display results
    limit = args.limit or 20
    for r in results[:limit]:
        match_type = r.get("_match_type", "")
        name = r.get("name", "?")
        comment = r.get("comment", "")
        cls = r.get("class", "")

        if match_type == "class":
            print(f"  [CLASS] {name}" + (f" — {comment}" if comment else ""))
        elif cls:
            print(f"  [IND]   {name} → {cls}")
        else:
            print(f"  [ITEM]  {name}")

    if len(results) > limit:
        print(f"  ... and {len(results) - limit} more")

    # Export if requested
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2, default=str)
        print(f"\nExported to {args.output}")


def cmd_export(args):
    """Export ontology to various formats."""
    from .core.ontology import load_ontology
    from .core.exporter import OntologyExporter

    ont = load_ontology(args.ontology)
    exp = OntologyExporter(ont)

    format_map = {
        "json": lambda p: exp.export_json(p),
        "csv-classes": lambda p: exp.export_csv_classes(p),
        "csv-individuals": lambda p: exp.export_csv_individuals(p),
        "csv-properties": lambda p: exp.export_csv_properties(p),
        "graphml": lambda p: exp.export_graphml(p),
        "markdown": lambda p: exp.export_markdown_report(p),
    }

    if args.format not in format_map:
        print(f"Unknown format: {args.format}")
        print(f"Available: {', '.join(format_map.keys())}")
        sys.exit(1)

    out = format_map[args.format](args.output)
    size = out.stat().st_size
    print(f"✅ Exported {args.format} → {out} ({size:,} bytes)")


def cmd_validate(args):
    """Validate and score ontology quality."""
    from .core.ontology import load_ontology
    from .core.validator import OntologyValidator

    ont = load_ontology(args.ontology)
    v = OntologyValidator(ont)

    if args.quick:
        result = v.quick_check()
        print("═══ Quick Health Check ═══")
        for k, val in result.items():
            icon = "✅" if val is True else "❌" if val is False else f"  {val}"
            print(f"  {k}: {icon}")
        return

    result = v.validate()
    print("═══ Ontology Quality Report ═══")
    print(f"  Total Score: {result['total_score']}/100 ({result['grade']})")
    print()
    print("  Dimensions:")
    for dim, score in result["dimension_scores"].items():
        bar = "█" * (score // 5) + "░" * (20 - score // 5)
        print(f"    {dim:15s} {bar} {score}/100")
    print()
    print("  Issues:")
    for issue in result["issues"]:
        print(f"    {issue}")
    print()
    print(f"  Stats: {result['stats']}")

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2, default=str)
        print(f"  Report saved to {args.output}")


def cmd_viz(args):
    """Start the visualization web server."""
    from .visualization import start_viewer

    print(f"Starting OntoFuel visualization on port {args.port}...")
    start_viewer(port=args.port, ontology_dir=args.data_dir, open_browser=not args.no_browser)


def main(argv=None):
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="ontofuel",
        description="OntoFuel — Ontology-driven knowledge extraction for nuclear materials",
    )
    parser.add_argument("--ontology", "-o", type=Path, default=None,
                        help="Path to ontology JSON file (default: auto-detect)")

    sub = parser.add_subparsers(dest="command", help="Available commands")

    # stats
    p_stats = sub.add_parser("stats", help="Show ontology statistics")
    p_stats.add_argument("-v", "--verbose", action="store_true", help="Show detailed stats")
    p_stats.set_defaults(func=cmd_stats)

    # query
    p_query = sub.add_parser("query", help="Search ontology entities")
    p_query.add_argument("query", nargs="?", default="", help="Search query")
    p_query.add_argument("--class", "-c", dest="class_name", help="Filter by class name")
    p_query.add_argument("--property", "-p", help="Filter by property (name or name=value)")
    p_query.add_argument("--hierarchy", "-H", help="Show class hierarchy for given class")
    p_query.add_argument("--category", choices=["all", "classes", "individuals"], default="all")
    p_query.add_argument("--limit", "-n", type=int, default=20, help="Max results")
    p_query.add_argument("--output", "-O", help="Export results to JSON file")
    p_query.set_defaults(func=cmd_query)

    # export
    p_export = sub.add_parser("export", help="Export ontology to various formats")
    p_export.add_argument("format", choices=["json", "csv-classes", "csv-individuals",
                                              "csv-properties", "graphml", "markdown"],
                          help="Export format")
    p_export.add_argument("output", type=Path, help="Output file path")
    p_export.set_defaults(func=cmd_export)

    # validate
    p_validate = sub.add_parser("validate", help="Validate ontology quality")
    p_validate.add_argument("--quick", "-q", action="store_true", help="Quick health check")
    p_validate.add_argument("--output", "-O", help="Save report to JSON file")
    p_validate.set_defaults(func=cmd_validate)

    # viz
    p_viz = sub.add_parser("viz", help="Start visualization server")
    p_viz.add_argument("--port", "-p", type=int, default=9999, help="Port (default: 9999)")
    p_viz.add_argument("--data-dir", "-d", help="Ontology data directory")
    p_viz.add_argument("--no-browser", action="store_true", help="Don't open browser")
    p_viz.set_defaults(func=cmd_viz)

    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        sys.exit(0)

    args.func(args)


if __name__ == "__main__":
    main()
