import streamlit as st
import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import plotly.express as px
import requests
import numpy as np

# ==============================================================================
# SECTION 1: CONFIGURACIÓN DE PÁGINA
# ==============================================================================
st.set_page_config(page_title="Colombia Road Infrastructure Dashboard", layout="wide")

# ==============================================================================
# SECTION 2: CARGA Y OPTIMIZACIÓN DE DATOS
# ==============================================================================
GITHUB_RAW_BASE = "https://raw.githubusercontent.com/jsyanezastudio/colombia-roads-did/main"
GEOJSON_PATH = f"{GITHUB_RAW_BASE}/roads_time_municipalities.json"
MUNICIPALITIES_PATH = f"{GITHUB_RAW_BASE}/colombia_municipalities_codes.geojson"
ROAD_TYPE_MUNI_PATH = f"{GITHUB_RAW_BASE}/municipalities_by_road_type.json"

@st.cache_data
def load_data():
    gdf_roads = gpd.read_file(GEOJSON_PATH)
    gdf_muni = gpd.read_file(MUNICIPALITIES_PATH)
    response = requests.get(ROAD_TYPE_MUNI_PATH)
    json_data = response.json()
    
    records = [feat["properties"] for feat in json_data["features"]] if isinstance(json_data, dict) else json_data
    df_road_type = pd.DataFrame(records)
        
    for col in ['pre_date', 'start_date', 'oper_date']:
        gdf_roads[col] = pd.to_datetime(gdf_roads[col], errors='coerce', dayfirst=True)
    gdf_roads['oper_year'] = gdf_roads['oper_date'].dt.year
    
    if gdf_muni.crs != gdf_roads.crs:
        gdf_muni = gdf_muni.to_crs(gdf_roads.crs)
    
    muni_key = 'Municipality_Code_DANE'
    df_key = 'Municipality_Code_DANE' if 'Municipality_Code_DANE' in df_road_type.columns else df_road_type.columns[0]
    df_road_type = df_road_type.rename(columns={df_key: 'muni_code_match', 'Id_type': 'id_type'})
    
    df_road_type['is_doble'] = df_road_type['id_type'].str.lower().str.contains('doble|dual|2', na=False)
    df_road_type_clean = df_road_type.sort_values(by='is_doble', ascending=False).drop_duplicates(subset=['muni_code_match'])
    
    gdf_muni = gdf_muni.merge(df_road_type_clean[['muni_code_match', 'id_type']], left_on=muni_key, right_on='muni_code_match', how='left')
    gdf_muni['id_type'] = gdf_muni['id_type'].fillna('Sin vías')
    return gdf_roads, gdf_muni

@st.cache_data
def load_impact_dataset():
    return pd.read_csv(f"{GITHUB_RAW_BASE}/colombia_infrastructure_impact_dataset.csv")

gdf_compiled, gdf_municipalities = load_data()
df_impact = load_impact_dataset()
TOTAL_MUNI_COUNT = len(gdf_municipalities)

def absolute_value_format(val, allvals):
    return f"{int(np.round(val/100.*sum(allvals))):d} Muni."

# ==============================================================================
# SECTION 3: HEADER Y ESTRUCTURA
# ==============================================================================
st.markdown("""<div style='text-align:center; padding: 20px; background-color: #1a5276; color: white; border-radius: 8px; margin-bottom: 20px;'>
    <h1 style='color: white;'>Colombia Road Infrastructure Analytics Platform</h1>
</div>""", unsafe_allow_html=True)

col_control, col_map, col_right = st.columns([20, 55, 25])

# ==============================================================================
# SECTION 4: PANEL IZQUIERDO (CONTROLES)
# ==============================================================================
with col_control:
    main_menu = st.selectbox("Select View Module:", ["1. Colombia Roads", "2. Municipalities with Projects"])
    show_any_roads = st.checkbox("Show Municipalities with Roads", value=True)
    show_doble_roads = st.checkbox("Show Dual Carriageways", value=True)

# ==============================================================================
# SECTION 5: PANEL CENTRAL (MAPA)
# ==============================================================================
with col_map:
    fig_map, ax_map = plt.subplots(figsize=(9, 11))
    gdf_municipalities.plot(ax=ax_map, facecolor='#fdfdfd', edgecolor='black', linewidth=0.1)
    if show_any_roads:
        gdf_municipalities[gdf_municipalities['id_type'] != 'Sin vías'].plot(ax=ax_map, facecolor='#f4d03f', alpha=0.6)
    if show_doble_roads:
        gdf_municipalities[gdf_municipalities['id_type'] == 'Doble'].plot(ax=ax_map, facecolor='#27ae60', alpha=0.8)
    ax_map.set_axis_off()
    st.pyplot(fig_map)

# ==============================================================================
# SECTION 6: PANEL DERECHO (VISUALIZACIONES)
# ==============================================================================
with col_right:
    if main_menu == "1. Colombia Roads":
        st.markdown("<div style='background:#1a5276; color:white; padding:8px; font-weight:bold; border-radius:5px; font-family:sans-serif; text-align:center;'>Infrastructure Breakdown</div>", unsafe_allow_html=True)
        
        count_any = len(gdf_municipalities[gdf_municipalities['id_type'] != 'Sin vías'])
        count_doble = len(gdf_municipalities[gdf_municipalities['id_type'] == 'Doble'])
        
        fig_pies, (ax1, ax2) = plt.subplots(2, 1, figsize=(4.5, 8.5))
        
        # Gráfico 1 - Ajustado con fuente sans-serif
        ax1.pie([count_any, TOTAL_MUNI_COUNT - count_any], labels=['With Roads', 'No Roads'], 
                autopct=lambda p: absolute_value_format(p, [count_any, TOTAL_MUNI_COUNT - count_any]), 
                colors=['#f4d03f', '#eeeeee'], radius=1.2, textprops={'family':'sans-serif', 'fontsize': 10})
        ax1.set_title("Proportional Distribution:\nTreatment Stock within National Baseline", fontsize=10, family='sans-serif', weight='bold', pad=20)
        
        # Gráfico 2 - Ajustado con fuente sans-serif
        ax2.pie([count_doble, count_any - count_doble], labels=['Dual (Doble)', 'Other'], 
                autopct=lambda p: absolute_value_format(p, [count_doble, count_any - count_doble]), 
                colors=['#27ae60', '#eeeeee'], radius=1.2, textprops={'family':'sans-serif', 'fontsize': 10})
        ax2.set_title("Segment Allocation:\nHigh-Capacity (Dual) within Active Road Network", fontsize=10, family='sans-serif', weight='bold', pad=20)
        
        plt.tight_layout()
        st.pyplot(fig_pies)
