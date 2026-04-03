"""CSV <-> canonical JSON bridge for country authoring workflow."""

from __future__ import annotations

import argparse

from beta_engine.infrastructure.world_config import export_countries_to_csv, import_countries_from_csv


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Countries authoring bridge: CSV <-> canonical JSON")
    subparsers = parser.add_subparsers(dest="command", required=True)

    export_parser = subparsers.add_parser("export-csv", help="Export canonical countries JSON into tabular CSV")
    export_parser.add_argument("--json", default="config/world/countries.json", help="Input canonical countries JSON")
    export_parser.add_argument("--csv", default="config/world/countries.seed.demo.csv", help="Output CSV path")

    import_parser = subparsers.add_parser("import-csv", help="Import tabular CSV into canonical countries JSON")
    import_parser.add_argument("--csv", required=True, help="Input CSV path")
    import_parser.add_argument("--json", default="config/world/countries.json", help="Output canonical countries JSON")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "export-csv":
        path = export_countries_to_csv(json_path=args.json, csv_path=args.csv)
        print(f"Exported countries CSV: {path}")
        return

    if args.command == "import-csv":
        config = import_countries_from_csv(csv_path=args.csv, json_path=args.json)
        print(f"Imported {len(config.countries)} countries into {args.json}")
        return

    raise ValueError(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    main()
