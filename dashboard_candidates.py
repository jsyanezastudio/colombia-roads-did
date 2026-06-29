import streamlit as st
import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt

# ==============================================================================
# SECTION 1: STREAMLIT PAGE CONFIGURATION
# Purpose: Sets up the browser tab title, favicon, and forces a wide layout 
#          harnessing the maximum screen real estate for our 3-column dashboard.
# ==============================================================================
st.set_page_config(
    page_title="Colombia Road Infrastructure DiD",
    page_icon="🇨🇴",
    layout="wide"
)

# ==============================================================================
# SECTION 2: DATA LOADING & OPTIMIZATION (CACHING)
# Purpose: Downloads and parses remote GeoJSON data. 
# Design Note: '@st.cache_data' ensures data is loaded ONLY ONCE into memory. 
#              Subsequent filter changes won't trigger re-downloads, ensuring fast rendering.
# ==============================================================================
GEOJSON_PATH = "https://raw.githubusercontent.com/jsyanezastudio/colombia-roads-did/main/roads_time_municipalities.json"
MUNICIPALITIES_PATH = "https://raw.githubusercontent.com/jsyanezastudio/colombia-roads-did/main/colombia_municipalities_codes.geojson"

@st.cache_data
def load_data():
    # Load geospatial vector data
    gdf_roads = gpd.read_file(GEOJSON_PATH)
    gdf_muni = gpd.read_file(MUNICIPALITIES_PATH)
    
    # Preprocess date columns securely
    for col in ['pre_date', 'start_date', 'oper_date']:
        gdf_roads[col] = pd.to_datetime(gdf_roads[col], errors='coerce', dayfirst=True)
    
    # Extract operational year for filtering purposes
    gdf_roads['oper_year'] = gdf_roads['oper_date'].dt.year
    
    # Project both layers to the exact same Coordinate Reference System (CRS)
    if gdf_muni.crs != gdf_roads.crs:
        gdf_muni = gdf_muni.to_crs(gdf_roads.crs)
        
    return gdf_roads, gdf_muni

gdf_compiled, gdf_municipalities = load_data()

# ==============================================================================
# SECTION 3: FILTER CONTROLS DICTIONARY GENERATION
# Purpose: Pre-calculates valid items intersecting between roads and municipalities
#          to populate dropdown selectors in descending order of impact size.
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
# SECTION 4: HEADER DISPLAY BLOCK (HTML CUSTOM INJECTION)
# Purpose: Custom branded title section matching the original notebook style.
# Styling details: Dark corporate blue background (#1a5276), white readable text,
#                  centered alignment, and sleek rounded corners (border-radius).
# ==============================================================================
st.markdown(
    """
    <div style='text-align:center; padding: 15px; background-color: #1a5276; color: white; border-radius: 8px; margin-bottom: 20px; font-family: sans-serif;'>
        <h2 style='margin:0; color: white !important;'>Candidates for Treatment Group in DiD of Road Infrastructure Improvements</h2>
        <p style='margin:5px 0 0 0; opacity: 0.8; color: white !important;'>Geospatial Analysis sorted by impact magnitude (DANE Municipalities)</p>
    </div>
    """, 
    unsafe_allow_html=True
)

# ==============================================================================
# SECTION 5: RESPONSIVE DASHBOARD LAYOUT DEFINITION
# Purpose: Assigns specific proportional widths to create a balanced viewport.
# Proportions: 
#   - col_control (20% Width): Side panel housing KPIs, parameters, and Map Legend.
#   - col_map     (55% Width): Main focus center piece containing the Matplotlib plot.
#   - col_table   (25% Width): Data list panel supporting vertical scrolling tracking.
# ==============================================================================
col_control, col_map, col_table = st.columns([20, 55, 25])

# ==============================================================================
# SECTION 6: SIDE PANEL CONTROLS & FILTERING INPUTS (col_control)
# Purpose: Handles client selection inputs via interactive Streamlit Tab views.
# ==============================================================================
with col_control:
    # Render Streamlit Tab navigation
    tab_project, tab_year = st.tabs(['By Project', 'By Year'])
    
    # Initialize variables to keep tracking logic clean
    val_proj = "All"
    val_year = "All"
    is_project_mode = True

    with tab_project:
        val_proj = st.selectbox('Select Project:', options=unique_projects, key="proj_select")
        
    with tab_year:
        val_year = st.selectbox('Select Operation Year:', options=years_list, key="year_select")
        # Check which tab is currently interacting based on system state
        if val_year != "All":
            is_project_mode = False

    # Apply Filtering Rules directly to DataFrames based on Active Tabs
    filtered_roads = gdf_compiled.copy()
    if is_project_mode:
        if val_proj != 'All':
            filtered_roads = filtered_roads[filtered_roads['PROYECTO'] == val_proj]
    else:
        if val_year != 'All':
            filtered_roads = filtered_roads[filtered_roads['oper_year'] == val_year]

    # Clean subset focusing exclusively on complete evaluation timelines
    gdf_complete = filtered_roads.dropna(subset=['pre_date', 'start_date', 'oper_date'])
    impacted_muni = gpd.GeoDataFrame()
    muni_list_data = pd.DataFrame()

    if not gdf_complete.empty:
        hits = gpd.sjoin(gdf_municipalities, gdf_complete, how="inner", predicate="intersects")
        if not hits.empty:
            impacted_muni = gdf_municipalities.loc[hits.index.unique()]
            muni_list_data = impacted_muni[['Municipality_Code_DANE', 'Municipality_Name_DANE']].drop_duplicates().sort_values('Municipality_Name_DANE')

    # --- KPI METRIC RENDERING ---
    count = len(muni_list_data) if not muni_list_data.empty else 0
    st.markdown(
        f"""
        <div style='text-align:center; padding: 10px; background: white; border: 2px solid #1a5276; border-radius: 8px; margin-top: 15px; margin-bottom: 10px;'>
            <span style='font-size: 11px; color: #555; text-transform: uppercase; font-weight: bold;'>Total Municipalities</span><br>
            <span style='font-size: 28px; color: #1a5276; font-weight: bold;'>{count}</span>
        </div>
        """, 
        unsafe_allow_html=True
    )

    # --- HISTORICAL CONTEXT METRIC ---
    if is_project_mode and val_proj != 'All':
        active_years = sorted(filtered_roads['oper_year'].dropna().unique().astype(int))
        years_str = ", ".join(map(str, active_years)) if active_years else "N/A"
        st.markdown(
            f"""
            <div style='text-align:center; padding: 10px; background: #ebf5fb; border: 1px dashed #1a5276; border-radius: 8px; margin-bottom: 15px;'>
                <span style='font-size: 11px; color: #555; text-transform: uppercase; font-weight: bold;'>Year of Operation</span><br>
                <span style='font-size: 16px; color: #1a5276; font-weight: bold;'>{years_str}</span>
            </div>
            """, 
            unsafe_allow_html=True
        )

    # --- MAP LEGEND COMPONENT ---
    st.markdown(
        """
        <div style='padding: 10px; background: #fdfdfd; border: 1px solid #1a5276; border-radius: 8px; font-family: sans-serif; font-size: 12px;'>
            <b style='color: #1a5276;'>MAP LEGEND</b><br>
            <div style='margin-top:8px;'><span style='display:inline-block; width:12px; height:12px; background:#cb4335; margin-right:5px;'></span><b>Treated:</b> Road with complete dates</div>
            <div style='margin-top:4px;'><span style='display:inline-block; width:12px; height:12px; background:#5dade2; margin-right:5px;'></span><b>General:</b> Filtered road segment</div>
            <div style='margin-top:4px;'><span style='display:inline-block; width:12px; height:12px; background:#d4e6f1; margin-right:5px;'></span><b>Impacted:</b> Municipality (DANE)</div>
            <div style='margin-top:4px;'><span style='display:inline-block; width:12px; height:12px; background:#fdfdfd; border:1px solid #ccc; margin-right:5px;'></span><b>Base:</b> Administrative boundary</div>
        </div>
        """, 
        unsafe_allow_html=True
    )

# ==============================================================================
# SECTION 7: GEOSPATIAL MAP PLOTTING GENERATION (col_map)
# Purpose: Configures a crisp Matplotlib visualization layout and prints via Streamlit.
# Design Details: Explicit bounding coordinate box targets Colombia boundaries cleanly.
# ==============================================================================
with col_map:
    fig, ax = plt.subplots(figsize=(9, 11))
    
    # 1. Base Layer (All municipalities)
    gdf_municipalities.plot(ax=ax, facecolor='#fdfdfd', edgecolor='black', linewidth=0.15)
    
    # 2. Impacted Layer Highlight
    if not impacted_muni.empty: 
        impacted_muni.plot(ax=ax, facecolor='#d4e6f1', edgecolor='black', linewidth=0.4, alpha=0.6)
        
    # 3. Filtered Roads network Layer
    if not filtered_roads.empty: 
        filtered_roads.plot(ax=ax, color='#5dade2', linewidth=0.8, alpha=0.5)
        
    # 4. Completed DiD Roadmap Targets Layer
    if not gdf_complete.empty: 
        gdf_complete.plot(ax=ax, color='#cb4335', linewidth=1.5)
    
    # Spines and Boundary frame configurations
    for spine in ax.spines.values(): 
        spine.set_visible(True)
        spine.set_color('#1a5276')
        spine.set_linewidth(2.0)
        
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_xlim([-79.5, -66.5])
    ax.set_ylim([-4.5, 13.5])
    
    # Output the element securely using Streamlit engine wrapper
    st.pyplot(fig, use_container_width=True)

# ==============================================================================
# SECTION 8: SCROLLABLE DATA TABLE RENDERING (col_table)
# Purpose: Outputs structured lists inside a CSS styled HTML container block 
#          emulating native scrolling lists efficiently.
# ==============================================================================
with col_table:
    header = "<div style='background:#1a5276; color:white; padding:8px; font-weight:bold; border-radius:5px 5px 0 0; font-family:sans-serif;'>Impacted List (DANE)</div>"
    content = "<div style='height: 680px; overflow-y: auto; border: 1px solid #ddd; padding: 10px; background: white; font-family: monospace;'>"
    
    if not muni_list_data.empty:
        rows = "".join([
            f"<div style='border-bottom: 1px solid #eee; padding: 4px 0;'><small style='color:#777;'>[{int(row['Municipality_Code_DANE'])}]</small> {row['Municipality_Name_DANE']}</div>" 
            for _, row in muni_list_data.iterrows()
        ])
        content += rows
    else: 
        content += "<p style='color: #999; text-align: center; margin-top: 20px;'>No municipalities selected.</p>"
        
    st.markdown(header + content + "</div>", unsafe_allow_html=True)
