"""CSV bridge for an explicit editable World Package country store."""

from __future__ import annotations

import argparse

from pathlib import Path
from beta_engine.application.countries_service import CountriesConfigService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Countries authoring bridge: CSV <-> canonical JSON")
    subparsers = parser.add_subparsers(dest="command", required=True)

    export_parser = subparsers.add_parser("export-csv", help="Export canonical countries JSON into tabular CSV")
    export_parser.add_argument("--package-root", required=True, help="Editable World Package root")
    export_parser.add_argument("--csv", required=True, help="Output CSV path")

    import_parser = subparsers.add_parser("import-csv", help="Import tabular CSV into canonical countries JSON")
    import_parser.add_argument("--csv", required=True, help="Input CSV path")
    import_parser.add_argument("--package-root", required=True, help="Editable World Package root")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "export-csv":
        path = Path(args.csv); path.write_text(CountriesConfigService(package_root=Path(args.package_root)).export_countries_csv(), encoding="utf-8")
        print(f"Exported countries CSV: {path}")
        return

    if args.command == "import-csv":
        service = CountriesConfigService(package_root=Path(args.package_root))
        result = service.import_countries_csv(csv_text=Path(args.csv).read_text(encoding="utf-8"), dry_run=False)
        if not result.ok: raise ValueError(result.errors)
        print(f"Imported {result.summary.total_records} countries into {args.package_root}")
        return

    raise ValueError(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    main()
