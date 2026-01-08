import streamlit as st
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import folium
from streamlit_folium import st_folium
import shapely
from shapely.ops import transform
from datetime import time

# =========================
# CONFIG STREAMLIT
# =========================
st.set_page_config(
    page_title="Zones d'intervention Julien FATNASSI",
    layout="wide"
)

st.title("Visualisation des zones d'intervention")

# =========================
# TRAITEMENT
# =========================
def normalize_polygons(gdf):
    gdf = gdf[gdf.geometry.notnull()]
    gdf = gdf[gdf.geometry.geom_type.isin(["Polygon", "MultiPolygon"])]
    gdf = gdf.explode(index_parts=False)
    
    return gdf

# --- Chargement des zones ---
zone1 = gpd.read_file('Zone_1.geojson')
zone1["geometry"] = zone1["geometry"].simplify(tolerance=0.001, preserve_topology=True)

zone2 = gpd.read_file('Zone_2.geojson')
zone2["geometry"] = zone2["geometry"].simplify(tolerance=0.01, preserve_topology=True)

zone3 = gpd.read_file('Zone_3.geojson')
zone3["geometry"] = zone3["geometry"].simplify(tolerance=0.05, preserve_topology=True)


# --- Chargement CSV ---
df = pd.read_csv('communes_FR.csv', sep=";")
df['id'] = [f"{nom} - {int(code):05d}" for nom, code in zip(df['nom_commune'], df['code_postal'])]

geometry = gpd.points_from_xy(df["longitude"], df["latitude"])
communes = gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")


# =========================
# ANALYSE SPATIALE
# =========================
zone1_clean = normalize_polygons(zone1)
zone2_clean = normalize_polygons(zone2)
zone3_clean = normalize_polygons(zone3)

zone2_sans_zone1 = gpd.overlay(zone2_clean, zone1_clean, how="difference")
zone3_sans_zone2 = gpd.overlay(zone3_clean, zone2_clean, how="difference")

communes_zone1 = gpd.sjoin(communes, zone1, how="inner", predicate="within")
communes_zone2 = gpd.sjoin(communes, zone2_sans_zone1, how="inner", predicate="within")
communes_zone3 = gpd.sjoin(communes, zone3_sans_zone2, how="inner", predicate="within")

# Ajouter la colonne "zone"
communes_zone1["zone"] = "Zone 1"
communes_zone2["zone"] = "Zone 2"
communes_zone3["zone"] = "Zone 3"

# Toutes les communes avec zone
communes_zones = pd.concat([communes_zone1, communes_zone2, communes_zone3])
communes_zones['id'] = [f"{nom} - {int(code):05d}" for nom, code in zip(communes_zones['nom_commune'], communes_zones['code_postal'])]
communes_zones['departement'] = communes_zones['code_postal'].astype(str).str[:-3].astype(int)
communes_zones.sort_values(by=['departement', 'code_commune'],inplace=True)

df= pd.merge(df, communes_zones[['id', 'zone']], on='id', how='left')
df['zone'] = df['zone'].fillna("Hors zone")

# =========================
# SELECTBOX MULTIPLE POUR CHOIX DES COMMUNES
# =========================

c3, col01, col02 = st.columns(3)

# Affiche le multiselect
commune_selection = col01.multiselect(
    "Choisissez les communes à afficher (nom ou code postal)",
    options=df['id'],
    placeholder="Sélectionnez une ou plusieurs communes"
)

# Affiche le détail des sélections$
if commune_selection:
    df_selection = df[df['id'].isin(commune_selection)]
    #df_selection.sort_values(by='zone', inplace=True)
    col02.markdown("Détails des communes sélectionnées :")
    col02.dataframe(df_selection[["nom_commune", "code_postal", "zone"]]
                 .style.format({"code_postal": "{:05d}"}),
                 hide_index=True
                 )
else:
    col02.markdown("")
    col02.info("Veuillez sélectionner au moins une commune.")


# Extraire uniquement les noms des communes sélectionnées
noms_selectionnes = df[df['id'].isin(commune_selection)]
selected = noms_selectionnes["id"]

# =========================
# CARTE FOLIUM
# =========================

# Carte centrée sur st etienne
lat_centre = 45.4396
lon_centre = 4.38717
m = folium.Map(location=[lat_centre, lon_centre], zoom_start=8, scrollWheelZoom=False,  tiles="OpenStreetMap")

# Ajouter contours zones
folium.GeoJson(zone3, style_function=lambda _: {"fillOpacity": 0, "color": "blue", "weight": 2}, name="Zone 3").add_to(m)
folium.GeoJson(zone2, style_function=lambda _: {"fillOpacity": 0, "color": "yellow", "weight": 2}, name="Zone 2").add_to(m)
folium.GeoJson(zone1_clean, style_function=lambda _: {"fillOpacity": 0, "color": "green", "weight": 2}, name="Zone 1").add_to(m)

# Afficher les points des communes sélectionnées
for nom in selected:
    row = communes[communes["id"] == nom].iloc[0]
    # Déterminer la zone
    if row.name in communes_zone1.index:
        zone_nom = "Zone 1"
        couleur = "green"
    elif row.name in communes_zone2.index:
        zone_nom = "Zone 2"
        couleur = "yellow"
    elif row.name in communes_zone3.index:
        zone_nom = "Zone 3"
        couleur = "blue"
    else:
        zone_nom = "Hors zone"
        couleur = "gray"

    folium.CircleMarker(
        location=[row.latitude, row.longitude],
        radius=6,
        color=couleur,
        fill=True,
        fill_opacity=0.8,
        popup=f"{row.nom_commune} ({zone_nom})"
    ).add_to(m)


with c3:
    st_folium(m, use_container_width=True)

col5, col6 = st.columns(2)

# =========================
# STATISTIQUES ET EXPORT
# =========================
st.subheader("Résultats")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total communes en France", len(communes))
col2.metric("Communes en zone 1", len(communes_zone1))
col3.metric("Communes en zone 2", len(communes_zone2))
col4.metric("Communes en zone 3", len(communes_zone3))

st.subheader(f"Téléchargement des {len(communes_zones)} communes classées par zones")

export_df = communes_zones[[
    "nom_commune",
    "code_postal",
    "zone"
]]

csv_result = export_df.to_csv(index=False)

st.download_button(
    label="Télécharger les communes (format .CSV)",
    data=csv_result,
    file_name="communes_zones.csv",
    mime="text/csv"
)
