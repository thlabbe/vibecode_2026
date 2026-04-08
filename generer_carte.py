"""
Génère la carte HTML à partir du cache de géocodage actuel.
Utilisation : python generer_carte.py
"""
from carte_osm import (
    CSV_PATH, CACHE_PATH, OUTPUT_HTML,
    load_and_clean_csv, load_cache, apply_geocode, generate_map,
)

df = load_and_clean_csv(CSV_PATH)
cache = load_cache(CACHE_PATH)
print(f"Cache : {len(cache)} entrées")

df_geo = apply_geocode(df, cache)
print(f"{len(df_geo)} lignes géocodées sur {len(df)}")

generate_map(df_geo, OUTPUT_HTML)
