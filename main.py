# =========================
# IMPORTS
# =========================
import streamlit as st
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import folium
from streamlit_folium import st_folium

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

# --- Chargement des zones ---
zone1 = gpd.read_file('Zone_1.geojson')
zone1["geometry"] = zone1["geometry"].simplify(tolerance=0.001, preserve_topology=True)
zone2 = gpd.read_file('Zone_2.geojson')
zone2["geometry"] = zone2["geometry"].simplify(tolerance=0.01, preserve_topology=True)
zone3 = gpd.read_file('Zone_3.geojson')
zone3["geometry"] = zone3["geometry"].simplify(tolerance=0.05, preserve_topology=True)

for zone in [zone1, zone2, zone3]:
    if zone.crs is None:
        zone.set_crs(epsg=4326, inplace=True)
    else:
        zone.to_crs(epsg=4326, inplace=True)

# --- Chargement CSV ---
df = pd.read_csv('communes_FR.csv', sep=";")
required_columns = {"nom_commune", "latitude", "longitude", "code_postal"}
if not required_columns.issubset(df.columns):
    st.error(f"Le CSV doit contenir les colonnes : {required_columns}")
    st.stop()

geometry = [Point(lon, lat) for lon, lat in zip(df["longitude"], df["latitude"])]
communes = gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")

# =========================
# ANALYSE SPATIALE
# =========================
communes_zone1 = gpd.sjoin(communes, zone1, how="inner", predicate="within")
communes_zone2 = gpd.sjoin(communes, zone2, how="inner", predicate="within")
communes_zone2 = communes_zone2[~communes_zone2.index.isin(communes_zone1.index)]
communes_zone3 = gpd.sjoin(communes, zone3, how="inner", predicate="within")
communes_zone3 = communes_zone3[~communes_zone3.index.isin(communes_zone2.index)]

# Ajouter la colonne "zone"
communes_zone1["zone"] = "Zone 1"
communes_zone2["zone"] = "Zone 2"
communes_zone3["zone"] = "Zone 3"

# Toutes les communes avec zone
communes_zones = pd.concat([communes_zone1, communes_zone2, communes_zone3])

# =========================
# SELECTBOX MULTIPLE POUR CHOIX DES COMMUNES
# =========================


# Crée une liste d'options combinant nom_commune et code_postal (5 premiers chiffres)
options = [
    f"{nom} ({str(cp).split('.')[0][:5]})"
    for nom, cp in zip(communes["nom_commune"], communes["code_postal"])
]
options = sorted(options)

# Affiche le multiselect
commune_selection = st.multiselect(
    "Choisissez les communes à afficher",
    options=options,
    placeholder="Sélectionnez une ou plusieurs communes"
)

# Extraire uniquement les noms des communes sélectionnées
noms_selectionnes = [option.split(" (")[0] for option in commune_selection]

# =========================
# CARTE FOLIUM
# =========================
st.subheader("Visualisation cartographique")

st.markdown(
    """
    <p style="font-size:14px; color:gray;">
        Zone 1 <span style="color:green; font-weight:600;">en vert</span> ·
        Zone 2 <span style="color:goldenrod; font-weight:600;">en jaune</span> ·
        Zone 3 <span style="color:royalblue; font-weight:600;">en bleu</span>
    </p>
    """,
    unsafe_allow_html=True
)

# Carte centrée sur toutes les communes
lat_centre = 45.4396
lon_centre = 4.38717
m = folium.Map(location=[lat_centre, lon_centre], zoom_start=8, scrollWheelZoom=False,  tiles="OpenStreetMap")

# Ajouter contours zones
folium.GeoJson(zone3, style_function=lambda _: {"fillOpacity": 0, "color": "blue", "weight": 2}, name="Zone 3").add_to(m)
folium.GeoJson(zone2, style_function=lambda _: {"fillOpacity": 0, "color": "yellow", "weight": 2}, name="Zone 2").add_to(m)
folium.GeoJson(zone1, style_function=lambda _: {"fillOpacity": 0, "color": "green", "weight": 2}, name="Zone 1").add_to(m)

# Afficher les points des communes sélectionnées
for nom in noms_selectionnes:
    row = communes[communes["nom_commune"] == nom].iloc[0]
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

    # Afficher infos sur une seule ligne
    cp = str(row.get("code_postal", "")).split(".")[0][:5] if pd.notna(row.get("code_postal")) else "N/A"
    st.markdown(f"**{row.nom_commune}**  |  {cp}  |  **{zone_nom}**")

st_folium(m, use_container_width=True)

# =========================
# STATISTIQUES ET EXPORT
# =========================
st.subheader("Résultats")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total communes en France", len(communes))
col2.metric("Communes en zone 1", len(communes_zone1))
col3.metric("Communes en zone 2", len(communes_zone2))
col4.metric("Communes en zone 3", len(communes_zone3))

st.subheader(f"Téléchargement des {len(communes_zone1)+len(communes_zone2)+len(communes_zone3)} communes classées par zones")

export_df = pd.concat([communes_zone1, communes_zone2, communes_zone3])

export_df = export_df[[
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
