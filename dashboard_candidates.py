import streamlit as st
import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt

# ==============================================================================
# SECTION 1: STREAMLIT PAGE CONFIGURATION
# ==============================================================================
st.set_page_config(
    page_title="Colombia Road Infrastructure Dashboard",
    page_icon="🇨🇴",
    layout="wide"
)

# ==============================================================================
# SECTION 2: DATA LOADING & OPTIMIZATION (CACHING)
# ==============================================================================
GEOJSON_PATH = "https://raw.githubusercontent.com/jsyanezastudio/colombia-roads-did/main/roads_time_municipalities.json"
MUNICIPALITIES_PATH = "https://raw.githubusercontent.com/jsyanezastudio/colombia-roads-did/main/colombia_municipalities_codes.geojson"

@st.cache_data
def load_data():
    gdf_roads = gpd.read_file(GEOJSON_PATH)
    gdf_muni = gpd.read_file(MUNICIPALITIES_PATH)
    
    # Process dates for DiD Analysis (Section 2)
    for col in ['pre_date', 'start_date', 'oper_date']:
        gdf_roads[col] = pd.to_datetime(gdf_roads[col], errors='coerce', dayfirst=True)
    gdf_roads['oper_year'] = gdf_roads['oper_date'].dt.year
    
    if gdf_muni.crs != gdf_roads.crs:
        gdf_muni = gdf_muni.to_crs(gdf_roads.crs)
        
    return gdf_roads, gdf_muni

gdf_compiled, gdf_municipalities = load_data()

# Pre-calculations for baseline constants
TOTAL_MUNI_COUNT = len(gdf_municipalities)
ALL_ROAD_MUNI_HITS = gpd.sjoin(gdf_municipalities, gdf_compiled, how="inner", predicate="intersects")
TOTAL_MUNI_WITH_ROADS = len(ALL_ROAD_MUNI_HITS.index.unique())

# ==============================================================================
# SECTION 3: FILTER CONTROLS DICTIONARY GENERATION (For Section 2)
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
    st.markdown("### 🗂️ Main Menu")
    main_menu = st.selectbox(
        "Select View Module:",
        options=["1. Colombia Roads", "2. DiD Candidates", "3. City Data Exploration"]
    )
    
    st.markdown("---")
    st.markdown("### 🎛️ Dynamic Filters")

    # --- LOGIC FOR MODULE 1 ---
    if main_menu == "1. Colombia Roads":
        st.markdown("**Layer Visibility Settings:**")
        show_any_roads = st.checkbox("Show Municipalities with Roads", value=True)
        show_doble_roads = st.checkbox("Show Dual Carriageways (Doble)", value=True)

    # --- LOGIC FOR MODULE 2 ---
    elif main_menu == "2. DiD Candidates":
        filter_mode = st.radio("Filter Analysis By:", ['Project', 'Year'], horizontal=True)
        val_proj = "All"
        val_year = "All"
        is_project_mode = (filter_mode == 'Project')

        if is_project_mode:
            val_proj = st.selectbox('Select Project:', options=unique_projects, key="proj_select")
        else:
            val_year = st.selectbox('Select Operation Year:', options=years_list, key="year_select")

    # --- LOGIC FOR MODULE 3 ---
    elif main_menu == "3. City Data Exploration":
        st.info("City Data Exploration module under development.")

# ==============================================================================
# SECTION 7: GEOSPATIAL MAP PLOTTING GENERATION (col_map)
# ==============================================================================
with col_map:
    fig_map, ax_map = plt.subplots(figsize=(9, 11))
    
    # Base Layer: All Municipalities
    gdf_municipalities.plot(ax=ax_map, facecolor='#fdfdfd', edgecolor='black', linewidth=0.15)
    
    if main_menu == "1. Colombia Roads":
        # Capa Amarilla: id_type != 'Sin vías'
        if show_any_roads and 'id_type' in gdf_municipalities.columns:
            muni_with_roads = gdf_municipalities[gdf_municipalities['id_type'] != 'Sin vías']
            if not muni_with_roads.empty:
                muni_with_roads.plot(ax=ax_map, facecolor='#f4d03f', edgecolor='black', linewidth=0.2, alpha=0.7)
        
        # Capa Verde: id_type == 'Doble'
        if show_doble_roads and 'id_type' in gdf_municipalities.columns:
            muni_doble = gdf_municipalities[gdf_municipalities['id_type'] == 'Doble']
            if not muni_doble.empty:
                muni_doble.plot(ax=ax_map, facecolor='#27ae60', edgecolor='black', linewidth=0.3, alpha=0.8)

    elif main_menu == "2. DiD Candidates":
        filtered_roads = gdf_compiled.copy()
        if is_project_mode:
            if val_proj != 'All':
                filtered_roads = filtered_roads[filtered_roads['PROYECTO'] == val_proj]
        else:
            if val_year != 'All':
                filtered_roads = filtered_roads[filtered_roads['oper_year'] == val_year]

        gdf_complete = filtered_roads.dropna(subset=['pre_date', 'start_date', 'oper_date'])
        impacted_muni = gpd.GeoDataFrame()
        muni_list_data = pd.DataFrame()

        if not gdf_complete.empty:
            hits = gpd.sjoin(gdf_municipalities, gdf_complete, how="inner", predicate="intersects")
            if not hits.empty:
                impacted_muni = gdf_municipalities.loc[hits.index.unique()]
                muni_list_data = impacted_muni[['Municipality_Code_DANE', 'Municipality_Name_DANE']].drop_duplicates().sort_values('Municipality_Name_DANE')

        if not impacted_muni.empty: 
            impacted_muni.plot(ax=ax_map, facecolor='#d4e6f1', edgecolor='black', linewidth=0.4, alpha=0.6)
        if not filtered_roads.empty: 
            filtered_roads.plot(ax=ax_map, color='#5dade2', linewidth=0.8, alpha=0.5)
        if not gdf_complete.empty: 
            gdf_complete.plot(ax=ax_map, color='#cb4335', linewidth=1.5)

    # Map framing and aesthetics
    for spine in ax_map.spines.values(): 
        spine.set_visible(True)
        spine.set_color('#1a5276')
        spine.set_linewidth(2.0)
        
    ax_map.set_xticks([])
    ax_map.set_yticks([])
    ax_map.set_xlim([-79.5, -66.5])
    ax_map.set_ylim([-4.5, 13.5])
    
    st.pyplot(fig_map, use_container_width=True)

# ==============================================================================
# SECTION 8: RIGHT PANEL VISUALIZATIONS & CHARTS (col_right)
# ==============================================================================
with col_right:
    if main_menu == "1. Colombia Roads" and 'id_type' in gdf_municipalities.columns:
        st.markdown("<div style='background:#1a5276; color:white; padding:8px; font-weight:bold; border-radius:5px; font-family: monospace; font-size:12px; text-align:center;'>Infrastructure Breakdown</div>", unsafe_allow_html=True)
        
        # Calculate counts based on 'id_type' column
        count_any_roads = len(gdf_municipalities[gdf_municipalities['id_type'] != 'Sin vías'])
        count_doble_roads = len(gdf_municipalities[gdf_municipalities['id_type'] == 'Doble'])
        count_no_roads = TOTAL_MUNI_COUNT - count_any_roads
        count_other_roads = count_any_roads - count_doble_roads

        fig_pies, (ax1, ax2) = plt.subplots(2, 1, figsize=(3.5, 5))
        fig_pies.patch.set_facecolor('none')
        
        # Pie 1: Municipalities with Roads vs National Total
        ax1.pie([count_any_roads, max(0.1, count_no_roads)], 
                labels=['With Roads', 'No Roads'], autopct='%1.1f%%', 
                colors=['#f4d03f', '#eeeeee'], startangle=90, 
                textprops={'fontsize': 8, 'family': 'monospace'})
                
        ax1.set_title("Road Network vs National Total", fontsize=9, family='monospace', color='#1a5276', weight='bold')
        
        # Pie 2: Dual Carriageways vs Total Municipalities with Roads
        ax2.pie([count_doble_roads, max(0.1, count_other_roads)], 
                labels=['Dual (Doble)', 'Other Types'], autopct='%1.1f%%', 
                colors=['#27ae60', '#eeeeee'], startangle=90, 
                textprops={'fontsize': 8, 'family': 'monospace'})
        ax2.set_title("Dual Carriageways vs Road Network", fontsize=9, family='monospace', color='#1a5276', weight='bold')
        
        plt.tight_layout()
        st.pyplot(fig_pies, use_container_width=True)

    elif main_menu == "2. DiD Candidates":
        st.markdown("<div style='background:#1a5276; color:white; padding:8px; font-weight:bold; border-radius:5px 5px 0 0; font-family: monospace; font-size:12px; text-align:center;'>DiD Sample Statistics</div>", unsafe_allow_html=True)
        
        selected_count = len(muni_list_data) if 'muni_list_data' in locals() else 0
        
        fig_pies, (ax1, ax2) = plt.subplots(2, 1, figsize=(3.5, 5))
        fig_pies.patch.set_facecolor('none') 
        
        # Pie 1: Selected vs National Total
        ax1.pie([selected_count, max(0.1, TOTAL_MUNI_COUNT - selected_count)], 
                labels=['Selected', 'Other'], autopct='%1.1f%%', 
                colors=['#1a5276', '#eeeeee'], startangle=90, 
                textprops={'fontsize': 8, 'family': 'monospace'})
        ax1.set_title("vs National Total", fontsize=9, family='monospace', color='#1a5276', weight='bold')
        
        # Pie 2: Selected vs Road Network Total
        ax2.pie([selected_count, max(0.1, TOTAL_MUNI_WITH_ROADS - selected_count)], 
                labels=['Selected', 'Other'], autopct='%1.1f%%', 
                colors=['#d4e6f1', '#eeeeee'], startangle=90, 
                textprops={'fontsize': 8, 'family': 'monospace'})
        ax2.set_title("vs Road Network", fontsize=9, family='monospace', color='#1a5276', weight='bold')
        
        plt.tight_layout()
        st.pyplot(fig_pies, use_container_width=True)
        
    else:
        st.markdown("<div style='color: #999; text-align: center; margin-top: 20px; font-family: monospace;'>No active visuals.</div>", unsafe_allow_html=True)
