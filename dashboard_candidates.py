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

# Helper function to display absolute counts in pie charts
def absolute_value_format(val, allvals):
    import numpy as np
    a = int(np.round(val/100.*sum(allvals)))
    return f"{a:d} Muni."

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
    
    return sorted_projects, sorted_years, hits

unique_projects, years_list, global_spatial_hits = get_sorted_filters(gdf_compiled, gdf_municipalities)

# Exact project names in the database for Section 3
corridor_options = [
    "Corridor Armenia - Pereira - Manizales (Eje Cafetero)",
    "Corridor Bogotá - La Vega - Villeta",
    "Corridor Honda - Puerto Salgar - Girardot"
]

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
        options=["1. Colombia Roads", "2. DiD Candidates", "3. City Data Exploration"]
    )
    
    st.markdown("---")
    st.markdown("### Dynamic Filters")

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

        # Data filtering calculation logic
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

        selected_count = len(muni_list_data)

        # KPI Summary Card
        st.markdown(
            f"""
            <div style='text-align:center; padding: 10px; background: white; border: 2px solid #1a5276; border-radius: 8px; margin-top: 15px; margin-bottom: 10px; font-family: monospace;'>
                <span style='font-size: 10px; color: #555; text-transform: uppercase;'>Total Municipalities</span><br>
                <span style='font-size: 24px; color: #1a5276; font-weight: bold;'>{selected_count}</span>
            </div>
            """, 
            unsafe_allow_html=True
        )

        if is_project_mode:
            active_years = sorted(filtered_roads['oper_year'].dropna().unique().astype(int))
            years_str = ", ".join(map(str, active_years)) if active_years else "All / NA"
            st.markdown(
                f"""
                <div style='text-align:center; padding: 10px; background: #ebf5fb; border: 1px dashed #1a5276; border-radius: 8px; margin-bottom: 15px; font-family: monospace;'>
                    <span style='font-size: 10px; color: #555; text-transform: uppercase;'>Year of Operation</span><br>
                    <span style='font-size: 14px; color: #1a5276; font-weight: bold;'>{years_str}</span>
                </div>
                """, 
                unsafe_allow_html=True
            )

    # --- LOGIC FOR MODULE 3 ---
    elif main_menu == "3. City Data Exploration":
        selected_corridor = st.selectbox(
            "Select Corridor Project:",
            options=corridor_options,
            key="corridor_select"
        )
        
        muni_id_col = 'Municipality_Code_DANE' if 'Municipality_Code_DANE' in gdf_municipalities.columns else gdf_municipalities.columns[0]
        
        # FIXED: Removed the invalid .str property call on the python raw text variable
        matched_hits = global_spatial_hits[
            global_spatial_hits['PROYECTO'].str.lower().str.strip() == selected_corridor.lower().strip()
        ]
        project_muni_ids = matched_hits.index.unique()
        
        gdf_corridor_muni = gdf_municipalities.loc[project_muni_ids]
        corridor_list_data = gdf_corridor_muni[[muni_id_col, 'Municipality_Name_DANE']].drop_duplicates().sort_values('Municipality_Name_DANE')

# ==============================================================================
# SECTION 7: GEOSPATIAL MAP PLOTTING GENERATION (col_map)
# ==============================================================================
with col_map:
    if main_menu != "3. City Data Exploration":
        fig_map, ax_map = plt.subplots(figsize=(9, 11))
        
        # Render base background map
        gdf_municipalities.plot(ax=ax_map, facecolor='#fdfdfd', edgecolor='black', linewidth=0.15)
        
        if main_menu == "1. Colombia Roads":
            if show_any_roads and 'id_type' in gdf_municipalities.columns:
                muni_with_roads = gdf_municipalities[gdf_municipalities['id_type'] != 'Sin vías']
                if not muni_with_roads.empty:
                    muni_with_roads.plot(ax=ax_map, facecolor='#f4d03f', edgecolor='black', linewidth=0.2, alpha=0.7)
            
            if show_doble_roads and 'id_type' in gdf_municipalities.columns:
                muni_doble = gdf_municipalities[gdf_municipalities['id_type'] == 'Doble']
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
    else:
        st.markdown(
            """
            <div style='text-align:center; padding: 40px; color: #7f8c8d; font-family: monospace; border: 2px dashed #bdc3c7; border-radius: 10px; margin-top: 50px;'>
                <h4>Corridor Display Mode Active</h4>
                <p>The visual graphics and isolated layout configurations have moved to the Right Analytics Panel.</p>
            </div>
            """, 
            unsafe_allow_html=True
        )

# ==============================================================================
# SECTION 8: RIGHT PANEL VISUALIZATIONS & CHARTS (col_right)
# ==============================================================================
with col_right:
    if main_menu == "1. Colombia Roads" and 'id_type' in gdf_municipalities.columns:
        st.markdown("<div style='background:#1a5276; color:white; padding:8px; font-weight:bold; border-radius:5px; font-family: monospace; font-size:12px; text-align:center;'>Infrastructure Breakdown</div>", unsafe_allow_html=True)
        
        count_any_roads = len(gdf_municipalities[gdf_municipalities['id_type'] != 'Sin vías'])
        count_doble_roads = len(gdf_municipalities[gdf_municipalities['id_type'] == 'Doble'])
        count_no_roads = TOTAL_MUNI_COUNT - count_any_roads
        count_other_roads = count_any_roads - count_doble_roads

        fig_pies, (ax1, ax2) = plt.subplots(2, 1, figsize=(3.5, 5))
        fig_pies.patch.set_facecolor('none')
        
        v1 = [count_any_roads, max(0.1, count_no_roads)]
        ax1.pie(v1, labels=['With Roads', 'No Roads'], 
                autopct=lambda pct: absolute_value_format(pct, v1), 
                colors=['#f4d03f', '#eeeeee'], startangle=90, 
                textprops={'fontsize': 8, 'family': 'monospace'})
        ax1.set_title("Road Network vs National Total", fontsize=9, family='monospace', color='#1a5276', weight='bold')
        
        v2 = [count_doble_roads, max(0.1, count_other_roads)]
        ax2.pie(v2, labels=['Dual (Doble)', 'Other Types'], 
                autopct=lambda pct: absolute_value_format(pct, v2), 
                colors=['#27ae60', '#eeeeee'], startangle=90, 
                textprops={'fontsize': 8, 'family': 'monospace'})
        ax2.set_title("Dual Carriageways vs Road Network", fontsize=9, family='monospace', color='#1a5276', weight='bold')
        
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
        
        v4 = [selected_count, max(0.1, TOTAL_MUNI_WITH_ROADS - selected_count)]
        ax2.pie(v4, labels=['Selected', 'Other'], 
                autopct=lambda pct: absolute_value_format(pct, v4), 
                colors=['#d4e6f1', '#eeeeee'], startangle=90, 
                textprops={'fontsize': 8, 'family': 'monospace'})
        ax2.set_title("vs Road Network", fontsize=9, family='monospace', color='#1a5276', weight='bold')
        
        plt.tight_layout()
        st.pyplot(fig_pies, use_container_width=True)
        
        st.markdown("---")
        st.markdown("<div style='font-family: monospace; font-size: 11px; font-weight: bold; color: #1a5276; margin-bottom: 5px;'>Impacted Municipalities List</div>", unsafe_allow_html=True)
        if not muni_list_data.empty:
            st.dataframe(
                muni_list_data.rename(columns={'Municipality_Code_DANE': 'Code', 'Municipality_Name_DANE': 'Name'}),
                hide_index=True, use_container_width=True, height=250
            )
        else:
            st.info("No municipalities found.")

    elif main_menu == "3. City Data Exploration":
        # Isolated rendering for the selected project polygons
        if not gdf_corridor_muni.empty:
            fig_mini, ax_mini = plt.subplots(figsize=(4, 4))
            fig_mini.patch.set_facecolor('none')
            
            gdf_corridor_muni.plot(ax=ax_mini, facecolor='#1a5276', edgecolor='white', linewidth=0.8)
            
            ax_mini.set_title(
                f"{selected_corridor}\n({len(gdf_corridor_muni)} municipalities with full data)", 
                fontsize=8, fontweight='bold', family='monospace', color='#1a5276'
            )
            ax_mini.set_axis_off()
            plt.tight_layout()
            st.pyplot(fig_mini, use_container_width=True)
        else:
            st.warning("No spatial intersections found for this project in the dataset.")
            
        # Dataframe list rendering beneath the mini layout map
        st.markdown("<div style='font-family: monospace; font-size: 11px; font-weight: bold; color: #1a5276; margin-bottom: 5px;'>Corridor Group Mapping</div>", unsafe_allow_html=True)
        st.dataframe(
            corridor_list_data.rename(columns={muni_id_col: 'Code', 'Municipality_Name_DANE': 'Name'}),
            hide_index=True,
            use_container_width=True,
            height=280
        )
