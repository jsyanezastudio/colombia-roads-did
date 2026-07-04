import streamlit as st
import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt
import requests

# ==============================================================================
# SECTION 1: STREAMLIT PAGE CONFIGURATION
# ==============================================================================
st.set_page_config(
    page_title="Colombia Road Infrastructure Dashboard",
    layout="wide"
)

# ==============================================================================
# SECTION 2: DATA LOADING & OPTIMIZATION (CACHING - THREE DISTINCT SOURCES)
# ==============================================================================
GEOJSON_PATH = "https://raw.githubusercontent.com/jsyanezastudio/colombia-roads-did/main/roads_time_municipalities.json"
MUNICIPALITIES_PATH = "https://raw.githubusercontent.com/jsyanezastudio/colombia-roads-did/main/colombia_municipalities_codes.geojson"
ROAD_TYPE_MUNI_PATH = "https://raw.githubusercontent.com/jsyanezastudio/colombia-roads-did/main/municipalities_by_road_type.json"

@st.cache_data
def load_data():
    # Source 1: Road geometries and dates
    gdf_roads = gpd.read_file(GEOJSON_PATH)
    
    # Source 2: Base geographic shapes for municipalities
    gdf_muni = gpd.read_file(MUNICIPALITIES_PATH)
    
    # Source 3: Plain JSON file containing the verified 'Id_type' mapping
    response = requests.get(ROAD_TYPE_MUNI_PATH)
    json_data = response.json()
    
    # Convert plain JSON to standard DataFrame safely
    if isinstance(json_data, dict) and "features" in json_data:
        records = [feat["properties"] for feat in json_data["features"]]
        df_road_type = pd.DataFrame(records)
    else:
        df_road_type = pd.DataFrame(json_data)
        
    # Standardize date objects for DiD Analysis
    for col in ['pre_date', 'start_date', 'oper_date']:
        gdf_roads[col] = pd.to_datetime(gdf_roads[col], errors='coerce', dayfirst=True)
    gdf_roads['oper_year'] = gdf_roads['oper_date'].dt.year
    
    # Match Coordinate Reference Systems (CRS)
    if gdf_muni.crs != gdf_roads.crs:
        gdf_muni = gdf_muni.to_crs(gdf_roads.crs)
        
    # Standardize keys for the merge process
    muni_key = 'Municipality_Code_DANE' if 'Municipality_Code_DANE' in gdf_muni.columns else gdf_muni.columns[0]
    df_key = 'Municipality_Code_DANE' if 'Municipality_Code_DANE' in df_road_type.columns else df_road_type.columns[0]
    
    # Cast keys to string to prevent format mismatch
    gdf_muni[muni_key] = gdf_muni[muni_key].astype(str)
    df_road_type[df_key] = df_road_type[df_key].astype(str)
    
    # Rename explicitly using 'Id_type' to create a clean 'id_type' column for the map layout
    df_road_type = df_road_type.rename(columns={df_key: 'muni_code_match', 'Id_type': 'id_type'})
    
    # Drop duplicates to prevent row multiplication during merge
    df_road_type_clean = df_road_type[['muni_code_match', 'id_type']].drop_duplicates(subset=['muni_code_match'])
    
    # Final merge
    gdf_muni = gdf_muni.merge(df_road_type_clean, left_on=muni_key, right_on='muni_code_match', how='left')
    gdf_muni['id_type'] = gdf_muni['id_type'].fillna('Sin vías')
        
    return gdf_roads, gdf_muni, df_road_type

gdf_compiled, gdf_municipalities, df_muni_road_type = load_data()

# Pre-calculations for baseline constants
TOTAL_MUNI_COUNT = len(gdf_municipalities)
ALL_ROAD_MUNI_HITS = gpd.sjoin(gdf_municipalities, gdf_compiled, how="inner", predicate="intersects")
TOTAL_MUNI_WITH_ROADS = len(ALL_ROAD_MUNI_HITS.index.unique())

# ==============================================================================
# SECTION 3: FILTER CONTROLS DICTIONARY GENERATION
# ==============================================================================
@st.cache_data
def get_sorted_filters(_gdf_r, _gdf_m):
    gdf_complete = _gdf_r.dropna(subset=['pre_date', 'start_date', 'oper_date'])
    hits = gpd.sjoin(_gdf_m, gdf_complete, how="inner", predicate="intersects")
    muni_id_col = 'Municipality_Code_DANE' if 'Municipality_Code_DANE' in hits.columns else hits.columns[0]
    
    proj_counts = hits.groupby('PROYECTO')[muni_id_col].nunique().sort_values(ascending=False)
    sorted_projects = ['All'] + proj_counts.index.tolist()
    
    year_counts = hits.groupby('oper_year')[muni_id_col].nunique().sort_values(ascending=False)
    sorted_years = ['All'] + [int(y) for y in year_counts.index.tolist()]
    
    return sorted_projects, sorted_years

unique_projects, years_list = get_sorted_filters(gdf_compiled, gdf_municipalities)

# ==============================================================================
# SECTION 4: HEADER DISPLAY BLOCK
# ==============================================================================
st.markdown(
    """
    <div style='text-align:center; padding: 10px; background-color: #1a5276; color: white; border-radius: 8px; margin-bottom: 20px; font-family: monospace;'>
        <h3 style='margin:0; font-size: 14px; color: white !important;'>Colombia Road Infrastructure Analytics Platform</h3>
        <p style='margin:5px 0 0 0; opacity: 0.8; font-size: 11px; color: white !important;'>Geospatial Analysis Base Layer & DiD Treatment Evaluation</p>
    </div>
    """, 
    unsafe_allow_html=True
)

# ==============================================================================
# SECTION 5: RESPONSIVE DASHBOARD LAYOUT DEFINITION
# ==============================================================================
col_control, col_map, col_right = st.columns([20, 55, 25])

# ==============================================================================
# SECTION 6: SIDE PANEL CONTROLS (UPPER & LOWER BLOCKS)
# ==============================================================================
with col_control:
    st.markdown("### Main Menu")
    main_menu = st.selectbox(
        "Select View Module:",
        options=
