"""Validasi file grid_location_mapping.csv tanpa perlu memuat ulang GeoJSON.

File GeoJSON batas kabupaten/kota diperlukan saat membangun ulang mapping spasial.
Untuk memeriksa hasil mapping yang sudah dibuat, validasi ini cukup membaca CSV.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]

MAPPING_FILE = (
    ROOT
    / "data"
    / "grid_location_mapping.csv"
)

EXPECTED_GRID_COUNT = 810

REQUIRED_COLUMNS = [
    "grid_id",
    "lat_grid",
    "lon_grid",
    "latitude",
    "longitude",
    "nama_lokasi",
    "kabupaten_kota_tercakup",
    "provinsi_tercakup",
    "jenis_wilayah",
]


def main() -> None:

    # =========================================================
    # CHECK FILE
    # =========================================================

    if not MAPPING_FILE.exists():

        raise FileNotFoundError(
            f"File tidak ditemukan: {MAPPING_FILE}\n"
            "Simpan grid_location_mapping.csv di folder data/."
        )

    # =========================================================
    # LOAD DATA
    # =========================================================

    mapping = pd.read_csv(
        MAPPING_FILE,
        low_memory=False,
        dtype={"grid_id": "string"},
    )

    mapping.columns = (
        mapping.columns
        .astype(str)
        .str.strip()
    )

    # =========================================================
    # CHECK REQUIRED COLUMNS
    # =========================================================

    missing = sorted(
        set(REQUIRED_COLUMNS)
        - set(mapping.columns)
    )

    if missing:

        raise ValueError(
            "Kolom wajib tidak ditemukan: "
            + ", ".join(missing)
        )

    # =========================================================
    # VALIDATE GRID COUNT
    # =========================================================

    if len(mapping) != EXPECTED_GRID_COUNT:

        raise ValueError(
            f"Jumlah baris mapping {len(mapping)}; "
            f"seharusnya {EXPECTED_GRID_COUNT}."
        )

    # =========================================================
    # VALIDATE GRID ID
    # =========================================================

    if (
        mapping["grid_id"].isna().any()
        or mapping["grid_id"].duplicated().any()
    ):

        raise ValueError(
            "grid_id kosong atau duplikat ditemukan."
        )

    # =========================================================
    # VALIDATE LOCATION NAME
    # =========================================================

    if mapping["nama_lokasi"].isna().any():

        raise ValueError(
            "nama_lokasi memiliki nilai kosong."
        )

    # =========================================================
    # VALIDATE NUMERIC COORDINATES
    # =========================================================

    numeric_columns = [
        "lat_grid",
        "lon_grid",
        "latitude",
        "longitude",
    ]

    for column in numeric_columns:

        mapping[column] = pd.to_numeric(
            mapping[column],
            errors="coerce",
        )

        if mapping[column].isna().any():

            raise ValueError(
                f"Kolom {column} berisi nilai kosong/non-numerik."
            )

    # =========================================================
    # VALIDATE GRID CENTER LATITUDE
    # =========================================================

    latitude_valid = (
        (
            mapping["latitude"]
            - (mapping["lat_grid"] + 0.5)
        )
        .abs()
        < 1e-8
    ).all()

    if not latitude_valid:

        raise ValueError(
            "Koordinat latitude pusat grid tidak konsisten "
            "dengan lat_grid + 0.5."
        )

    # =========================================================
    # VALIDATE GRID CENTER LONGITUDE
    # =========================================================

    longitude_valid = (
        (
            mapping["longitude"]
            - (mapping["lon_grid"] + 0.5)
        )
        .abs()
        < 1e-8
    ).all()

    if not longitude_valid:

        raise ValueError(
            "Koordinat longitude pusat grid tidak konsisten "
            "dengan lon_grid + 0.5."
        )

    # =========================================================
    # ADMINISTRATIVE COVERAGE SUMMARY
    # =========================================================

    kind_counts = (
        mapping["jenis_wilayah"]
        .fillna("Tidak diketahui")
        .value_counts()
    )

    # =========================================================
    # OUTPUT
    # =========================================================

    print("=" * 56)

    print(
        "VALIDASI GRID LOCATION MAPPING — QUAKEREADY"
    )

    print("=" * 56)

    print(
        f"File              : {MAPPING_FILE}"
    )

    print(
        f"Jumlah baris      : {len(mapping):,}"
    )

    print(
        f"Grid unik         : {mapping['grid_id'].nunique():,}"
    )

    print(
        "Status validasi   : BERHASIL"
    )

    print(
        "\nDistribusi status wilayah:"
    )

    print(
        kind_counts.to_string()
    )

    print(
        "\nContoh 10 grid:"
    )

    print(
        mapping[
            [
                "grid_id",
                "nama_lokasi",
                "kabupaten_kota_tercakup",
                "provinsi_tercakup",
                "jenis_wilayah",
            ]
        ]
        .head(10)
        .to_string(index=False)
    )

    print(
        "\nCatatan: mapping menjelaskan cakupan grid, "
    )

    print(
        "bukan lokasi administratif tepat dari titik episenter individual."
    )


if __name__ == "__main__":

    main()