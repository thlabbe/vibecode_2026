"""
Carte scolaire Toulouse — Visualisation OpenStreetMap
=====================================================
Génère une carte interactive (HTML) montrant les rues de Toulouse
colorées par lycée de rattachement, à partir du fichier carte-scolaire.csv.

Le HTML est régénéré toutes les 50 rues géocodées — on peut donc
ouvrir / rafraîchir la carte pendant que le géocodage tourne.
"""

import json
from pathlib import Path

import folium
import pandas as pd
from geopy.extra.rate_limiter import RateLimiter
from geopy.geocoders import Nominatim

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
CSV_PATH = Path("carte-scolaire.csv")
CACHE_PATH = Path("geocode_cache.json")
OUTPUT_HTML = Path("carte_rues_lycees_toulouse.html")
TOULOUSE_CENTER = (43.6045, 1.444)

COLORS = [
    "#e6194b", "#3cb44b", "#ffe119", "#4363d8", "#f58231",
    "#911eb4", "#42d4f4", "#f032e6", "#bfef45", "#fabed4",
    "#469990", "#dcbeff", "#9A6324", "#800000", "#aaffc3",
    "#808000", "#ffd8b1", "#000075", "#a9a9a9", "#000000",
]


# ---------------------------------------------------------------------------
# Fonctions réutilisables
# ---------------------------------------------------------------------------
def load_and_clean_csv(csv_path: Path) -> pd.DataFrame:
    """Phase 1 — Charge et nettoie le CSV."""
    df = pd.read_csv(csv_path, sep=";", dtype=str).fillna("")
    df = df[df["COMMUNE"] != "COMMUNE"].copy()
    df = df[df["COMMUNE"].str.upper() == "TOULOUSE"].copy()
    df["rue"] = (df["TYPE DE VOIE"].str.strip() + " " + df["LIBELLE DE VOIE"].str.strip()).str.strip()
    df["adresse"] = df["rue"] + ", Toulouse, France"
    return df


def load_cache(cache_path: Path) -> dict:
    if cache_path.exists():
        with cache_path.open("r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_cache(cache: dict, cache_path: Path) -> None:
    with cache_path.open("w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def apply_geocode(df: pd.DataFrame, cache: dict) -> pd.DataFrame:
    """Ajoute lat/lon au DataFrame à partir du cache."""
    df = df.copy()
    df["lat"] = df["adresse"].map(lambda a: cache.get(a, {}).get("lat") if cache.get(a) else None)
    df["lon"] = df["adresse"].map(lambda a: cache.get(a, {}).get("lon") if cache.get(a) else None)
    return df.dropna(subset=["lat", "lon"]).copy()


def generate_map(df_geo: pd.DataFrame, output_html: Path) -> None:
    """Phase 3 — Génère la carte HTML à partir des données géocodées."""
    if df_geo.empty:
        print("  ⚠ Aucune donnée géocodée — carte non générée.")
        return

    lycees = sorted(df_geo["LYCEE DE RATTACHEMENT"].unique())
    lycee_color = {lycee: COLORS[i % len(COLORS)] for i, lycee in enumerate(lycees)}

    m = folium.Map(location=TOULOUSE_CENTER, zoom_start=13, control_scale=True)

    groups = {}
    for lycee in lycees:
        fg = folium.FeatureGroup(name=lycee)
        fg.add_to(m)
        groups[lycee] = fg

    seen = set()
    for _, row in df_geo.iterrows():
        key = (row["rue"], row["LYCEE DE RATTACHEMENT"])
        if key in seen:
            continue
        seen.add(key)

        lycee = row["LYCEE DE RATTACHEMENT"]
        color = lycee_color[lycee]

        popup_html = (
            f"<b>{row['rue']}</b><br>"
            f"Lycée : {lycee}<br>"
            f"Parité : {row.get('PARITE', '')}<br>"
            f"N° début : {row.get('NUMERO (DEBUT DE VOIE)', '')} "
            f"{row.get('INDICE DE REPETITION DE DEBUT', '')}<br>"
            f"N° fin : {row.get('NUMERO (FIN DE VOIE, INCLUS)', '')} "
            f"{row.get('INDICE DE REPETITION DE FIN', '')}"
        )

        folium.CircleMarker(
            location=[row["lat"], row["lon"]],
            radius=6,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.8,
            popup=folium.Popup(popup_html, max_width=350),
            tooltip=f"{row['rue']} → {lycee}",
        ).add_to(groups[lycee])

    folium.LayerControl(collapsed=False).add_to(m)
    m.save(str(output_html))
    print(f"  → Carte mise à jour : {output_html}  ({len(seen)} rues)")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # Phase 1
    print("Phase 1 — Chargement du CSV …")
    df = load_and_clean_csv(CSV_PATH)
    df_unique_rues = df[["rue", "adresse"]].drop_duplicates(subset=["rue"]).copy()
    print(f"  → {len(df)} lignes, {df_unique_rues.shape[0]} rues uniques, "
          f"{df['LYCEE DE RATTACHEMENT'].nunique()} lycées distincts.")

    # Phase 2 — Géocodage incrémental avec régénération de la carte
    print("Phase 2 — Géocodage des rues …")
    cache = load_cache(CACHE_PATH)
    if cache:
        print(f"  → Cache chargé : {len(cache)} entrées existantes.")

    geolocator = Nominatim(user_agent="toulouse-lycee-sectorisation-2023")
    geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1.1)

    new_lookups = 0
    for _, row in df_unique_rues.iterrows():
        adresse = row["adresse"]
        if adresse not in cache:
            location = geocode(adresse)
            if location:
                cache[adresse] = {"lat": location.latitude, "lon": location.longitude}
            else:
                cache[adresse] = None
            new_lookups += 1
            if new_lookups % 50 == 0:
                print(f"  … {new_lookups} nouvelles requêtes effectuées …")
                save_cache(cache, CACHE_PATH)
                # Régénère la carte avec les données disponibles
                df_geo = apply_geocode(df, cache)
                generate_map(df_geo, OUTPUT_HTML)

    save_cache(cache, CACHE_PATH)
    print(f"  → {new_lookups} nouvelles requêtes, cache total : {len(cache)} entrées.")

    # Phase 3 — Carte finale
    print("Phase 3 — Génération de la carte finale …")
    df_geo = apply_geocode(df, cache)
    print(f"  → {len(df_geo)}/{len(df)} lignes géocodées avec succès.")
    generate_map(df_geo, OUTPUT_HTML)
    print("Ouvrez ce fichier dans votre navigateur pour visualiser la carte.")
