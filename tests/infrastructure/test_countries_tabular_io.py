from __future__ import annotations

import csv

from beta_engine.infrastructure.world_config import export_countries_to_csv, import_countries_from_csv, load_countries_config


def test_export_and_import_roundtrip(tmp_path) -> None:
    json_input = tmp_path / "countries.json"
    json_input.write_text(
        """
{
  "dataset_status": "temporary_seed_demo",
  "countries": [
    {
      "code": "AAA",
      "name": "Alpha",
      "flag_asset": null,
      "region": "EUROPE",
      "population": 1000000,
      "wealth_support": 3,
      "squash_popularity": 4,
      "squash_tradition": 2,
      "system_quality": 5,
      "competition_density": 4.5,
      "federation_quality": 4.0,
      "court_count": 120,
      "style_dna": {"front_court": 0.2}
    }
  ]
}
""".strip()
        + "\n",
        encoding="utf-8",
    )

    csv_path = tmp_path / "countries.csv"
    export_countries_to_csv(json_path=json_input, csv_path=csv_path)

    output_json = tmp_path / "countries_out.json"
    imported = import_countries_from_csv(csv_path=csv_path, json_path=output_json)

    assert imported.countries[0].code == "AAA"
    loaded = load_countries_config(output_json)
    assert loaded.countries[0].system_quality == 5
    assert loaded.countries[0].competition_density == 4.5
    assert loaded.countries[0].federation_quality == 4.0
    assert loaded.countries[0].court_count == 120
    assert loaded.countries[0].style_dna == {}


def test_import_rejects_missing_columns(tmp_path) -> None:
    csv_path = tmp_path / "bad.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["code", "name"])
        writer.writeheader()
        writer.writerow({"code": "AAA", "name": "Alpha"})

    try:
        import_countries_from_csv(csv_path=csv_path, json_path=tmp_path / "unused.json")
    except ValueError as exc:
        assert "missing required columns" in str(exc)
    else:
        raise AssertionError("import should fail when required columns are missing")
