import streamlit as st
import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt

# ==============================================================================
# SECTION 1: STREAMLIT PAGE CONFIGURATION
# Purpose: Sets up the browser tab title, favicon, and forces a wide layout.
# ==============================================================================
st.set_page_config(
    page_title="Colombia Road Infrastructure DiD",
    page_icon="🇨🇴",
    layout="wide"
)

# ==============================================================================
# SECTION 2: DATA LOADING & OPTIMIZATION (CACHING)
# Purpose: Downloads and parses remote GeoJSON data. 
# ==============================================================================
GEOJSON_PATH = "https://raw.githubusercontent.com/jsyanezastudio/colombia-roads-did/main/roads_time_municipalities.json"
MUNICIPALITIES_PATH = "https://raw.githubusercontent.com/jsyanezastudio/colombia-roads-did/main/colombia_municipalities_codes.geojson"

@st.cache_data
def load_data():
    gdf_roads = gpd.read_file(GEOJSON_PATH)
    gdf_muni = gpd.read_file(MUNICIPALITIES_PATH)
    
    for col in ['pre_date', 'start_date', 'oper_date']:
        gdf_roads[col] = pd.to_datetime(gdf_roads[col], errors='coerce', dayfirst=True)
    
    gdf_roads['oper_year'] = gdf_roads['oper_date'].dt.year
    
    if gdf_muni.crs != gdf_roads.crs:
        gdf_muni = gdf_muni.to_crs(gdf_roads.crs)
        
    return gdf_roads, gdf_muni

gdf_compiled, gdf_municipalities = load_data()

# ==============================================================================
# SECTION 2.1: BASELINE CONSTANTS FOR PIE CHARTS
# Purpose: Pre-calculates national totals to anchor the statistical percentages.
# ==============================================================================
TOTAL_MUNI_COUNT = len(gdf_municipalities)
ALL_ROAD_MUNI_HITS = gpd.sjoin(gdf_municipalities, gdf_compiled, how="inner", predicate="intersects")
TOTAL_MUNI_WITH_ROADS = len(ALL_ROAD_MUNI_HITS.index.unique())

# ==============================================================================
# SECTION 3: FILTER CONTROLS DICTIONARY GENERATION
# Purpose: Pre-calculates valid items intersecting between layers.
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
# Purpose: Styled header component.
# ==============================================================================
st.markdown(
    """
    <div style='text-align:center; padding: 10px; background-color: #1a5276; color: white; border-radius: 8px; margin-bottom: 20px; font-family: monospace;'>
        <h3 style='margin:0; font-size: 14px; color: white !important;'>Candidates for Treatment Group: Road Infrastructure DiD</h3>
        <p style='margin:5px 0 0 0; opacity: 0.8; font-size: 11px; color: white !important;'>Geospatial Analysis (DANE Municipalities)</p>
    </div>
    """, 
    unsafe_allow_html=True
)

# ==============================================================================
# SECTION 5: RESPONSIVE DASHBOARD LAYOUT DEFINITION
# Proportions: 20% Controls & Pie Charts | 55% Main Map | 25% Data Table List
# ==============================================================================
col_control, col_map, col_table = st.columns([20, 55, 25])

# ==============================================================================
# SECTION 6: SIDE PANEL CONTROLS & DATA FILTERING LOGIC
# Purpose: Handles dropdown states and filters target data arrays sequentially.
# ==============================================================================
with col_control:
    tab_project, tab_year = st.tabs(['Project', 'Year'])
    val_proj = "All"
    val_year = "All"
    is_project_mode = True

    with tab_project:
        val_proj = st.selectbox('Select Project:', options=unique_projects, key="proj_select")
        
    with tab_year:
        val_year = st.selectbox('Select Operation Year:', options=years_list, key="year_select")
        if val_year != "All":
            is_project_mode = False

    # Apply data filtering based on the active selection tab
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

    # --- KPI METRIC RENDERING ---
    st.markdown(
        f"""
        <div style='text-align:center; padding: 10px; background: white; border: 2px solid #1a5276; border-radius: 8px; margin-top: 15px; margin-bottom: 10px; font-family: monospace;'>
            <span style='font-size: 10px; color: #555; text-transform: uppercase;'>Total Municipalities</span><br>
            <span style='font-size: 24px; color: #1a5276; font-weight: bold;'>{selected_count}</span>
        </div>
        """, 
        unsafe_allow_html=True
    )

    # --- DYNAMIC YEAR OF OPERATION CARD (HIDDEN IN YEAR TAB) ---
    # Purpose: Only displays the project's operation years if the user is in the 'Project' tab.
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

    # --- MAP LEGEND COMPONENT ---
    st.markdown(
        """
        <div style='padding: 10px; background: #fdfdfd; border: 1px solid #1a5276; border-radius: 8px; font-family: monospace; font-size: 10px;'>
            <b style='color: #1a5276;'>MAP LEGEND</b><br>
            <div style='margin-top:8px;'><span style='display:inline-block; width:10px; height:10px; background:#cb4335; margin-right:5px;'></span><b>Treated:</b> Complete dates</div>
            <div style='margin-top:4px;'><span style='display:inline-block; width:10px; height:10px; background:#5dade2; margin-right:5px;'></span><b>General:</b> Road segment</div>
            <div style='margin-top:4px;'><span style='display:inline-block; width:10px; height:10px; background:#d4e6f1; margin-right:5px;'></span><b>Impacted:</b> Municipality</div>
            <div style='margin-top:4px;'><span style='display:inline-block; width:10px; height:10px; background:#fdfdfd; border:1px solid #ccc; margin-right:5px;'></span><b>Base:</b> Boundary</div>
        </div>
        """, 
        unsafe_allow_html=True
    )

    # ==============================================================================
    # SECTION 6.1: PIE CHARTS GENERATION
    # Purpose: Generates and draws the matplotlib figure directly inside col_control.
    # ==============================================================================
    st.write("") # Spacer
    fig_pies, (ax1, ax2) = plt.subplots(2, 1, figsize=(3.5, 5))
    fig_pies.patch.set_facecolor('none') # Transparent background to match Streamlit's theme
    
    # Pie 1: vs National Total
    ax1.pie([selected_count, max(0.1, TOTAL_MUNI_COUNT - selected_count)], 
            labels=['Sel', 'Other'], autopct='%1.1f%%', 
            colors=['#1a5276', '#eeeeee'], startangle=90, 
            textprops={'fontsize': 8, 'family': 'monospace'})
    ax1.set_title("vs National Total", fontsize=9, family='monospace', color='#1a5276', weight='bold')
    
    # Pie 2: vs Road Network Total
    ax2.pie([selected_count, max(0.1, TOTAL_MUNI_WITH_ROADS - selected_count)], 
            labels=['Sel', 'Other'], autopct='%1.1f%%', 
            colors=['#d4e6f1', '#eeeeee'], startangle=90, 
            textprops={'fontsize': 8, 'family': 'monospace'})
    ax2.set_title("vs Road Network", fontsize=9, family='monospace', color='#1a5276', weight='bold')
    
    plt.tight_layout()
    st.pyplot(fig_pies, use_container_width=True)

# ==============================================================================
# SECTION 7: GEOSPATIAL MAP PLOTTING GENERATION (col_map)
# ==============================================================================
with col_map:
    fig_map, ax_map = plt.subplots(figsize=(9, 11))
    
    gdf_municipalities.plot(ax=ax_map, facecolor='#fdfdfd', edgecolor='black', linewidth=0.15)
    
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

# ==============================================================================
# SECTION 8: SCROLLABLE DATA TABLE RENDERING (col_table)
# ==============================================================================
with col_table:
    header = "<div style='background:#1a5276; color:white; padding:8px; font-weight:bold; border-radius:5px 5px 0 0; font-family: monospace; font-size:12px;'>Impacted List (DANE)</div>"
    content = "<div style='height: 680px; overflow-y: auto; border: 1px solid #ddd; padding: 10px; background: white; font-family: monospace; font-size: 11px;'>"
    
    if not muni_list_data.empty:
        rows = "".join([
            f"<div style='border-bottom: 1px solid #eee; padding: 4px 0;'><small style='color:#777;'>[{int(row['Municipality_Code_DANE'])}]</small> {row['Municipality_Name_DANE']}</div>" 
            for _, row in muni_list_data.iterrows()
        ])
        content += rows
    else: 
        content += "<p style='color: #999; text-align: center; margin-top: 20px;'>No data.</p>"
        
    st.markdown(header + content + "</div>", unsafe_allow_html=True)
