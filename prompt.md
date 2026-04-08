# Carte scolaire Toulouse — Visualisation OpenStreetMap

## Objectif

Visualiser sur une carte OpenStreetMap les rues de Toulouse et leur lycée de rattachement à partir du fichier `carte-scolaire.csv` extrait du PDF.

---

## Phase 1 — Chargement et nettoyage du CSV

- Charger `carte-scolaire.csv` (séparateur `;`)
- Supprimer les lignes d'en-tête répétées (changements de page PDF)
- Filtrer uniquement les lignes de Toulouse
- Construire le nom complet de la rue : `TYPE DE VOIE` + `LIBELLE DE VOIE`
- Dédupliquer les rues uniques

## Phase 2 — Géocodage des rues (Nominatim / OpenStreetMap)

- Utiliser `geopy.geocoders.Nominatim` pour géocoder chaque rue unique
- Respecter la politique d'usage OSM : 1 requête/seconde max
- Mettre en cache les résultats dans un fichier local (`geocode_cache.json`) pour ne pas relancer les requêtes à chaque exécution
- Joindre les coordonnées (lat/lon) aux données du CSV

## Phase 3 — Génération de la carte interactive (Folium)

- Créer une carte `folium.Map` centrée sur Toulouse (43.6045, 1.444)
- Attribuer une couleur stable par lycée (hash MD5 du nom → couleur hex)
- Ajouter un `CircleMarker` par rue avec popup (nom rue, lycée, numéros)
- Regrouper les marqueurs avec `MarkerCluster`
- Ajouter une légende par lycée
- Sauvegarder en `carte_rues_lycees_toulouse.html`

---

## Dépendances

```
pandas
geopy
folium
```

## Usage

```bash
# Installer les dépendances
pip install pandas geopy folium

# Lancer le script
python carte_osm.py
```
