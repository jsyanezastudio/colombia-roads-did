import streamlit as st
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt

# ==============================================================================
# PAGE CONFIGURATION (Must be the first Streamlit command)
# ==============================================================================
st.set_page_config(
    page_title="Colombia Infrastructure & Impact Dashboard",
    page_icon="🇨🇴",
    layout="wide"
)

# ADDITIONAL FORMATTING FOR MATPLOTLIB PIE CHARTS
def absolute_value_format(val, allvals):
    import numpy as np
    a = int(np.round(val/100.*np.sum(allvals)))
    return f"{a}"

# ==============================================================================
# SECTION 1: DATA INGESTION & CACHING (Official Repository URLs)
# ==============================================================================
GITHUB_RAW_BASE = "https://raw.githubusercontent.com/jsyanezastudio/colombia-roads-did/main"

@st.cache_data
def load_geospatial_data():
    # 1. Compiled Road Network / Temporal Lines
    roads_url = f"{GITHUB_RAW_BASE}/roads_time_municipalities.json"
    try:
        gdf_roads = gpd.read_file(roads_url)
    except Exception as e:
        raise RuntimeError(f"Error loading 'roads_time_municipalities.json': {e}")
    
    # 2. Colombia Base Municipalities (Codes & Geometry)
    muni_url = f"{GITHUB_RAW_BASE}/colombia_municipalities_codes.geojson"
    try:
        gdf_muni = gpd.read_file(muni_url)
    except Exception as e:
        raise RuntimeError(f"Error loading 'colombia_municipalities_codes.geojson': {e}")
        
    # 3. Municipalities classified by road type (Support Attribute Data)
    road_type_url = f"{GITHUB_RAW_BASE}/municipalities_by_road_type.json"
    try:
        gdf_road_type = gpd.read_file(road_type_url)
    except Exception as e:
        raise RuntimeError(f"Error loading 'municipalities_by_road_type.json': {e}")
    
    return gdf_roads, gdf_muni, gdf_road_type

@st.cache_data
def load_impact_dataset():
    # 4. Municipal Socioeconomic Impact Dataset (CSV Panel Data)
    impact_url = f"{GITHUB_RAW_BASE}/colombia_infrastructure_impact_dataset.csv"
    try:
        return pd.read_csv(impact_url)
    except Exception as e:
        raise RuntimeError(f"Error loading 'colombia_infrastructure_impact_dataset.csv': {e}")

# Safe loading execution
try:
    gdf_compiled, gdf_municipalities, gdf_road_type_support = load_geospatial_data()
    df_impact = load_impact_dataset()
except Exception as e:
    st.error(f"Critical Error: {e}")
    st.stop()

# ==============================================================================
# SECTION 2: DATA PRE-PROCESSING & MERGING
# ==============================================================================
TOTAL_MUNI_COUNT = 1122

# Standardize key column types to avoid match errors
if 'Municipality_Code_DANE' in gdf_municipalities.columns:
    gdf_municipalities['Municipality_Code_DANE'] = gdf_municipalities['Municipality_Code_DANE'].astype(str)

if 'Municipality_Code_DANE' in gdf_road_type_support.columns:
    gdf_road_type_support['Municipality_Code_DANE'] = gdf_road_type_support['Municipality_Code_DANE'].astype(str)

# Map directly using your exact column name: 'Id_type' to fix KeyError
if 'id_type' not in gdf_municipalities.columns:
    if 'Municipality_Code_DANE' in gdf_road_type_support.columns and 'Id_type' in gdf_road_type_support.columns:
        bridge_df = gdf_road_type_support[['Municipality_Code_DANE', 'Id_type']].copy()
        bridge_df = bridge_df.rename(columns={'Id_type': 'id_type'})
        
        gdf_municipalities = gdf_municipalities.merge(bridge_df, on='Municipality_Code_DANE', how='left')
    else:
        gdf_municipalities['id_type'] = None

# ADVANCED LOGIC FOR PIE CHARTS (Strictly splitting valid data universes)
if 'id_type' in gdf_municipalities.columns:
    # 1. First target universe: Count actual entries that are not null, empty, or placeholder 'Sin vias'
    valid_data_mask = gdf_municipalities['id_type'].notna() & (gdf_municipalities['id_type'] != '') & (gdf_municipalities['id_type'] != 'Sin vias')
    gdf_with_data = gdf_municipalities[valid_data_mask]
    
    count_with_data = len(gdf_with_data)
    count_without_data = max(0, TOTAL_MUNI_COUNT - count_with_data)
    
    # 2. Second target universe: Calculate subsets exclusively within the valid data population
    if count_with_data > 0:
        is_doble_mask = gdf_with_data['id_type'].astype(str).str.lower().str.contains('doble|dual|2', na=False)
        count_doble_roads = len(gdf_with_data[is_doble_mask])
        count_other_with_data = max(0, count_with_data - count_doble_roads)
    else:
        count_doble_roads, count_other_with_data = 0, 0
else:
    count_with_data, count_without_data, count_doble_roads, count_other_with_data = 500, 622, 150, 350

# Extract dynamic query boundaries for Module 2 dropdown selectors
unique_projects = ["All"] + sorted(list(gdf_compiled['PROYECTO'].dropna().unique())) if 'PROYECTO' in gdf_compiled.columns else ["All"]
years_list = ["All"] + sorted(list(gdf_compiled['oper_year'].dropna().astype(int).unique())) if 'oper_year' in gdf_compiled.columns else ["All"]

# Static Mapping for Module 3 (Only Municipal Names and Identifiers needed)
project_groups_mapping = {
    "Corridor Honda - Puerto Salgar - Girardot": [
        {"Code": "73275", "Name": "Flandes"},
        {"Code": "25307", "Name": "Girardot"}
    ],
    "Corridor Armenia - Pereira - Manizales (Eje Cafetero)": [
        {"Code": "17174", "Name": "Chinchina"},
        {"Code": "17001", "Name": "Manizales"},
        {"Code": "66001", "Name": "Pereira"},
        {"Code": "63690", "Name": "Salento"},
        {"Code": "66682", "Name": "Santa Rosa de Cabal"},
        {"Code": "17873", "Name": "Villamaria"}
    ],
    "Corridor Bogotá - La Vega - Villeta": [
        {"Code": "25402", "Name": "La Vega"},
        {"Code": "25430", "Name": "Madrid"},
        {"Code": "25489", "Name": "Nocaima"},
        {"Code": "25491", "Name": "El Rosal"},
        {"Code": "25658", "Name": "San Francisco"},
        {"Code": "25769", "Name": "Subachoque"}
    ]
}

# ==============================================================================
# SECTION 3: DASHBOARD LAYOUT & COLUMNS STRUCTURING
# ==============================================================================
st.markdown("<h1 style='text-align: center; color: #1a5276;'>Colombia Infrastructure and Municipal Impact Dashboard</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #555;'>Interactive Analytical Framework for Highway Project Evaluation and Difference-in-Differences Candidates</p>", unsafe_allow_html=True)
st.markdown("---")

col_control, col_map, col_right = st.columns([1.5, 5, 2.5])

# ==============================================================================
# SECTION 4: LATERAL CONTROLS PANEL (col_control)
# ==============================================================================
with col_control:
    st.markdown("### System Modules")
    main_menu = st.selectbox(
        "Select Analytical Focus:",
        options=["1. Colombia Roads", "2. DiD Candidates", "3. City Data Exploration"]
    )
    
    st.markdown("---")
    st.markdown("### Dynamic Filters")

    # --- MODULE 1 CONTROL ---
    if main_menu == "1. Colombia Roads":
        st.markdown("**Map Layers Configuration:**")
        show_any_roads = st.checkbox("Municipalities with Road Network", value=True)
        show_doble_roads = st.checkbox("Municipalities with Dual Carriageway", value=True)

    # --- MODULE 2 CONTROL ---
    elif main_menu == "2. DiD Candidates":
        filter_mode = st.radio("Filter Sample By:", ['Project', 'Operation Year'], horizontal=True)
        val_proj = "All"
        val_year = "All"
        is_project_mode = (filter_mode == 'Project')

        if is_project_mode:
            val_proj = st.selectbox('Select Specific Project:', options=unique_projects, key="proj_select")
        else:
            val_year = st.selectbox('Select Specific Year:', options=years_list, key="year_select")

        # Live spatial calculation for DiD target boundaries
        filtered_roads = gdf_compiled.copy()
        if is_project_mode:
            if val_proj != 'All':
                filtered_roads = filtered_roads[filtered_roads['PROYECTO'] == val_proj]
        else:
            if val_year != 'All':
                filtered_roads = filtered_roads[filtered_roads['oper_year'] == val_year]

        gdf_complete = filtered_roads.dropna(subset=['pre_date', 'start_date', 'oper_date']) if not filtered_roads.empty else filtered_roads
        impacted_muni = gpd.GeoDataFrame()
        muni_list_data = pd.DataFrame()

        if not gdf_complete.empty:
            hits = gpd.sjoin(gdf_municipalities, gdf_complete, how="inner", predicate="intersects")
            if not hits.empty:
                impacted_muni = gdf_municipalities.loc[hits.index.unique()]
                muni_list_data = impacted_muni[['Municipality_Code_DANE', 'Municipality_Name_DANE']].drop_duplicates().sort_values('Municipality_Name_DANE')

        selected_count = len(muni_list_data)

        st.markdown(
            f"""
            <div style='text-align:center; padding: 10px; background: white; border: 2px solid #1a5276; border-radius: 8px; margin-top: 15px; margin-bottom: 10px; font-family: monospace;'>
                <span style='font-size: 10px; color: #555; text-transform: uppercase;'>Impacted Municipalities</span><br>
                <span style='font-size: 24px; color: #1a5276; font-weight: bold;'>{selected_count}</span>
            </div>
            """, 
            unsafe_allow_html=True
        )

    # --- MODULE 3 CONTROL ---
    elif main_menu == "3. City Data Exploration":
        st.info("Module configuration enabled. Select corridors in the central workspace viewport.")

# ==============================================================================
# SECTION 5: PRIMARY GEOSPATIAL MAPS AND STATIC REPOS (col_map)
# ==============================================================================
with col_map:
    # --- STATIC GEOPANDAS RENDER PLOTS (MODULES 1 & 2) ---
    if main_menu == "1. Colombia Roads" or main_menu == "2. DiD Candidates":
        fig_map, ax_map = plt.subplots(figsize=(9, 11))
        
        # Draw permanent grayscale baseline context layer
        gdf_municipalities.plot(ax=ax_map, facecolor='#fdfdfd', edgecolor='black', linewidth=0.15)
        
        if main_menu == "1. Colombia Roads":
            if show_any_roads and 'id_type' in gdf_municipalities.columns:
                muni_with_roads = gdf_municipalities[valid_data_mask] if 'valid_data_mask' in locals() else gdf_municipalities
                if not muni_with_roads.empty:
                    muni_with_roads.plot(ax=ax_map, facecolor='#f4d03f', edgecolor='black', linewidth=0.2, alpha=0.7)
            
            if show_doble_roads and 'id_type' in gdf_municipalities.columns:
                muni_doble = gdf_municipalities[gdf_municipalities['id_type'].str.lower().str.contains('doble|dual|2', na=False)] if 'valid_data_mask' in locals() else gpd.GeoDataFrame()
                if not muni_doble.empty:
                    muni_doble.plot(ax=ax_map, facecolor='#27ae60', edgecolor='black', linewidth=0.3, alpha=0.8)

        elif main_menu == "2. DiD Candidates":
            if not impacted_muni.empty: 
                impacted_muni.plot(ax=ax_map, facecolor='#d4e6f1', edgecolor='black', linewidth=0.4, alpha=0.6)
            if not filtered_roads.empty: 
                filtered_roads.plot(ax=ax_map, color='#5dade2', linewidth=0.8, alpha=0.5)
            if not gdf_complete.empty: 
                gdf_complete.plot(ax=ax_map, color='#cb4335', linewidth=1.5)

        for spine in ax_map.spines.values(): 
            spine.set_visible(True)
            spine.set_color('#1a5276')
            spine.set_linewidth(2.0)
            
        ax_map.set_xticks([])
        ax_map.set_yticks([])
        ax_map.set_xlim([-79.5, -66.5])
        ax_map.set_ylim([-4.5, 13.5])
        
        st.pyplot(fig_map, use_container_width=True)

    # --- TEXT-BASED EXCLUSIVE LISTING GRID (MODULE 3) ---
    elif main_menu == "3. City Data Exploration":
        st.markdown("### Strategic Highway Corridors Inventory")
        selected_project = st.selectbox("Choose Core Corridor Architecture:", options=list(project_groups_mapping.keys()))
        
        st.markdown("---")
        st.markdown(f"#### Municipalities assigned to: *{selected_project}*")
        st.markdown("Below is the complete database registry containing exclusively the target corporate metadata identifiers:")
        
        # Build strict non-downloadable markdown table syntax
        markdown_table = "| Municipality Code (DANE) | Municipality Name |\n| :--- | :--- |\n"
        for item in project_groups_mapping[selected_project]:
            markdown_table += f"| {item['Code']} | {item['Name']} |\n"
            
        st.markdown(markdown_table)

# ==============================================================================
# SECTION 6: DESCRIPTIVE STATISTICS & META-DATA EXPANDERS (col_right)
# ==============================================================================
with col_right:
    if main_menu == "1. Colombia Roads":
        st.markdown("<div style='background:#1a5276; color:white; padding:8px; font-weight:bold; border-radius:5px; font-family: monospace; font-size:12px; text-align:center;'>Infrastructure Breakdown</div>", unsafe_allow_html=True)
        
        fig_pies, (ax1, ax2) = plt.subplots(2, 1, figsize=(3.5, 5))
        fig_pies.patch.set_facecolor('none')
        
        # Pie 1: Municipalities with data registry vs national absolute remainder
        v1 = [count_with_data, max(0.1, count_without_data)]
        ax1.pie(v1, labels=['Municipalities with Data', 'Municipalities without Data'], 
                autopct=lambda pct: absolute_value_format(pct, v1), 
                colors=['#f4d03f', '#eeeeee'], startangle=90, 
                textprops={'fontsize': 8, 'family': 'monospace'})
        ax1.set_title("Network vs National Total", fontsize=9, family='monospace', color='#1a5276', weight='bold')
        
        # Pie 2: Ratio of Doble (Dual Carriageway) calculated strictly out of the known registry
        v2 = [count_doble_roads, max(0.1, count_other_with_data)]
        ax2.pie(v2, labels=['Dual Carriageway (Doble)', 'Other Roads with Data'], 
                autopct=lambda pct: absolute_value_format(pct, v2), 
                colors=['#27ae60', '#eeeeee'], startangle=90, 
                textprops={'fontsize': 8, 'family': 'monospace'})
        ax2.set_title("Dual vs Road Network Data", fontsize=9, family='monospace', color='#1a5276', weight='bold')
        
        plt.tight_layout()
        st.pyplot(fig_pies, use_container_width=True)

    elif main_menu == "2. DiD Candidates":
        st.markdown("<div style='background:#1a5276; color:white; padding:8px; font-weight:bold; border-radius:5px 5px 0 0; font-family: monospace; font-size:12px; text-align:center;'>DiD Sample Statistics</div>", unsafe_allow_html=True)
        
        fig_pies, (ax1, ax2) = plt.subplots(2, 1, figsize=(3.5, 4.5))
        fig_pies.patch.set_facecolor('none') 
        
        v3 = [selected_count, max(0.1, TOTAL_MUNI_COUNT - selected_count)]
        ax1.pie(v3, labels=['Selected', 'Other'], 
                autopct=lambda pct: absolute_value_format(pct, v3), 
                colors=['#1a5276', '#eeeeee'], startangle=90, 
                textprops={'fontsize': 8, 'family': 'monospace'})
        ax1.set_title("vs National Total", fontsize=9, family='monospace', color='#1a5276', weight='bold')
        
        total_eligible_network = count_with_data if count_with_data > 0 else 500
        v4 = [selected_count, max(0.1, total_eligible_network - selected_count)]
        ax2.pie(v4, labels=['Selected', 'Other'], 
                autopct=lambda pct: absolute_value_format(pct, v4), 
                colors=['#d4e6f1', '#eeeeee'], startangle=90, 
                textprops={'fontsize': 8, 'family': 'monospace'})
        ax2.set_title("vs Road Network", fontsize=9, family='monospace', color='#1a5276', weight='bold')
        
        plt.tight_layout()
        st.pyplot(fig_pies, use_container_width=True)
        
        st.markdown("---")
        st.markdown("<div style='font-family: monospace; font-size: 11px; font-weight: bold; color: #1a5276; margin-bottom: 5px;'>Impacted Municipalities Inventory</div>", unsafe_allow_html=True)
        if not muni_list_data.empty:
            st.dataframe(
                muni_list_data.rename(columns={'Municipality_Code_DANE': 'Code', 'Municipality_Name_DANE': 'Municipality'}),
                hide_index=True, use_container_width=True, height=220
            )
        else:
            st.info("No municipal intersections match the selected query criteria.")

    elif main_menu == "3. City Data Exploration":
        st.markdown("<div style='background:#1a5276; color:white; padding:8px; font-weight:bold; border-radius:5px; font-family: monospace; font-size:12px; text-align:center;'>Coverage Overview</div>", unsafe_allow_html=True)
        st.markdown("<p style='font-size:12px; font-family:monospace; margin-top:10px;'>This exploration frame lists the specific geographical targets assigned to Colombia's main primary highway development projects, interlinking baseline spatial assets to their official administrative DANE registry codes.</p>", unsafe_allow_html=True)
