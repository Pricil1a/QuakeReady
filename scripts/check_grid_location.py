# ============================================================
# CHECK GRID LOCATION MAPPING
# ============================================================

from pathlib import Path
import pandas as pd
import geopandas as gpd

ROOT = Path(__file__).resolve().parents[1]

DATA = ROOT / "data"

MAPPING_FILE = DATA / "grid_location_mapping.csv"

BOUNDARY_FILE = DATA / "batas_kabupaten.geojson"

# ------------------------------------------------------------
# 1. CHECK FILES
# ------------------------------------------------------------

for file in [MAPPING_FILE, BOUNDARY_FILE]:

    if not file.exists():
        raise FileNotFoundError(file)

    print("[OK]", file.name)

# ------------------------------------------------------------
# 2. LOAD DATA
# ------------------------------------------------------------

mapping = pd.read_csv(MAPPING_FILE)

admin = gpd.read_file(BOUNDARY_FILE)

# ------------------------------------------------------------
# 3. VALIDATION
# ------------------------------------------------------------

assert len(mapping) == 810, (
    f"Jumlah grid tidak sesuai: {len(mapping)}"
)

assert mapping["grid_id"].nunique() == 810

assert mapping["nama_lokasi"].notna().all()

assert admin.crs is not None

print("\n================================")
print("GRID LOCATION VALIDATION")
print("================================")

print("Total grid:", len(mapping))

print("Grid unik:", mapping["grid_id"].nunique())

print("Total polygon:", len(admin))

print("CRS polygon:", admin.crs)

print("\nTOP 10 GRID")

print(
    mapping[
        [
            "grid_id",
            "nama_lokasi",
            "kabupaten_kota_tercakup",
            "provinsi_tercakup",
            "jenis_wilayah"
        ]
    ].head(10).to_string(index=False)
)

print("\nVALIDASI BERHASIL")