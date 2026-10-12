"""Join the zone lookup with the zone polygons and convert them to the GeoJSON"""

import json
from pathlib import Path
import geopandas as gpd
import pandas as pd
from . import config as cfg
from .load_data import load_lookup

SQFT_TO_KM2 = 9.290304e-8   # EPSG:2263 is measured in US survey feet

def build_zone_assets(lookup_csv: Path, shapefile: Path, out_dir: Path) -> pd.DataFrame:
    out_dir.mkdir(parents=True, exist_ok=True)
    lookup = load_lookup(lookup_csv)

    gdf = gpd.read_file(shapefile)
    # There are some zone which are split into several polygons(for example LocationID 56 and 103), they need to be merge
    gdf = gdf[["LocationID", "geometry"]].dissolve(by="LocationID", as_index=False)
    gdf = gdf.rename(columns={"LocationID": "location_id"})
    gdf["location_id"] = gdf["location_id"].astype(int)

    # Area and centroid are computed in feet, where distance are accurate
    projected = gdf.to_crs(2263)
    gdf["area_km2"] = (projected.geometry.area * SQFT_TO_KM2).round(4)
    centroids = gpd.GeoSeries(projected.geometry.centroid, crs=2263).to_crs(4326)
    gdf["centroid_lon"] = centroids.x.round(6)
    gdf["centroid_lat"] = centroids.y.round(6)

    # Convert the shapes to lat/lon ans simplify them to keep the file small
    gdf = gdf.to_crs(4326)
    gdf["geometry"] = gdf.geometry.simplify(0.00003, preserve_topology=True)

    zones = lookup.merge(gdf[["location_id", "area_km2", "centroid_lat", "centroid_lon"]],
                         on="location_id", how="left")
    zones["has_geometry"] = zones["area_km2"].notna().astype(int)
    zones["is_mappable"] = (zones["has_geometry"].astype(bool)
                            & ~zones["location_id"].isin(cfg.UNKNOWN_ZONE_IDS)).astype(int)
    zones = zones.sort_values("location_id").reset_index(drop=True)
    zones.to_csv(out_dir / "zones_dim.csv", index=False)

    features = gdf.merge(lookup, on="location_id", how="left")
    collection = json.loads(features[["location_id", "zone_name", "borough", "service_zone", "geometry"]]
                            .to_json(drop_id=True))
    (out_dir / "zones.geojson").write_text(json.dumps(collection, separators=(",", ":")), encoding="utf-8")
    return zones


