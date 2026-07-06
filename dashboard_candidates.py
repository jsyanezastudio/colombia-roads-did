import streamlit as st
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import plotly.express as px

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
# SECTION 2: DATA PRE-PROCESSING & MERGING (Deduplication Fix Applied)
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
        
        # --- SOLUCIÓN AL DOBLE CONTEO / TRASLAPE OSCURO DE MUNICIPIOS ---
        # Priorizamos registros que contengan calzadas dobles antes de remover duplicados por código DANE
        bridge_df['is_doble'] = bridge_df['id_type'].str.lower().str.contains('doble|dual|2', na=False)
        bridge_df = bridge_df.sort_values(by='is_doble', ascending=False)
        bridge_df = bridge_df.drop_duplicates(subset=['Municipality_Code_DANE']).drop(columns=['is_doble'])
        # ----------------------------------------------------------------
        
        gdf_municipalities = gdf_municipalities.merge(bridge_df, on='Municipality_Code_DANE', how='left')
    else:
        gdf_municipalities['id_type'] = 'Sin vias'

# Calculate metrics safely for visualizations based on standard classes
if 'id_type' in gdf_municipalities.columns:
    gdf_municipalities['id_type'] = gdf_municipalities['id_type'].fillna('Sin vias')
    # Cuenta única estricta de municipios con red vial
    count_any_roads = len(gdf_municipalities[gdf_municipalities['id_type'] != 'Sin vias'])
    # Cuenta única estricta de municipios con doble calzada
    count_doble_roads = len(gdf_municipalities[gdf_municipalities['id_type'].str.lower().str.contains('doble|dual|2', na=False)])
    count_no_roads = TOTAL_MUNI_COUNT - count_any_roads
    count_other_roads = count_any_roads - count_doble_roads
else:
    count_any_roads, count_doble_roads, count_no_roads, count_other_roads = 500, 150, 622, 350

# Extract dynamic query boundaries for Module 2 dropdown selectors
unique_projects = ["All"] + sorted(list(gdf_compiled['PROYECTO'].dropna().unique())) if 'PROYECTO' in gdf_compiled.columns else ["All"]
years_list = ["All"] + sorted(list(gdf_compiled['oper_year'].dropna().astype(int).unique())) if 'oper_year' in gdf_compiled.columns else ["All"]

# Pre-declared variables for multi-column mapping integrity
project_groups_mapping = {
    "Corridor Honda - Puerto Salgar - Girardot": [73275, 25307],
    "Corridor Armenia - Pereira - Manizales (Eje Cafetero)": [17174, 17001, 66001, 63690, 66682, 17873],
    "Corridor Bogotá - La Vega - Villeta": [25402, 25430, 25489, 25491, 25658, 25769]
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
        st.info("Interactive panel enabled. Adjust analytical dimensions directly in the central viewport section.")

# ==============================================================================
# SECTION 5: PRIMARY GEOSPATIAL MAPS AND PLOTLY CHARTS (col_map)
# ==============================================================================
with col_map:
    # --- STATIC GEOPANDAS RENDER PLOTS (MODULES 1 & 2) ---
    if main_menu == "1. Colombia Roads" or main_menu == "2. DiD Candidates":
        fig_map, ax_map = plt.subplots(figsize=(9, 11))
        
        # Draw permanent grayscale baseline context layer
        gdf_municipalities.plot(ax=ax_map, facecolor='#fdfdfd', edgecolor='black', linewidth=0.15)
        
        if main_menu == "1. Colombia Roads":
            if show_any_roads and 'id_type' in gdf_municipalities.columns:
                muni_with_roads = gdf_municipalities[gdf_municipalities['id_type'] != 'Sin vias']
                if not muni_with_roads.empty:
                    muni_with_roads.plot(ax=ax_map, facecolor='#f4d03f', edgecolor='black', linewidth=0.2, alpha=0.7)
            
            if show_doble_roads and 'id_type' in gdf_municipalities.columns:
                muni_doble = gdf_municipalities[gdf_municipalities['id_type'].str.lower().str.contains('doble|dual|2', na=False)]
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

    # --- PLOTLY HIGH-RESOLUTION INTERACTIVE CHARTS (MODULE 3) ---
    elif main_menu == "3. City Data Exploration":
        categories_map = {
            'Education': ['s11_total', 'alumn_total', 'docen_total'],
            'Services and Infrastructure': ['tacued', 'turbacued', 'truracued', 'talcan'],
            'Fiscal and Impact': ['inv_total', 'TMI', 'y_total', 'y_corr']
        }
        all_variables_map = {
            's11_total': 'Saber11 Standardized Score', 'alumn_total': 'Total Enrolled Students', 'docen_total': 'Total Active Teachers',
            'tacued': 'Water Access Coverage (Total)', 'turbacued': 'Urban Water Coverage', 'truracued': 'Rural Water Coverage', 'talcan': 'Sewage Infrastructure Coverage',
            'inv_total': 'Total Public Investment', 'TMI': 'Infant Mortality Rate', 'y_total': 'Total Municipal Revenues', 'y_corr': 'Current Operating Revenues'
        }
        mun_color_pairs = [
            ('#1A5276', '#5DADE2'), ('#1E8449', '#58D68D'), ('#A93226', '#E74C3C'), 
            ('#7D3C98', '#BB8FCE'), ('#B05C00', '#F39C12'), ('#2C3E50', '#7F8C8D')
        ]

        df_filtered = df_impact.copy()
        def assign_group(code):
            for g_name, codes in project_groups_mapping.items():
                if code in codes: return g_name
            return None
        df_filtered['Project_Group'] = df_filtered['Municipality_Code_Dane'].apply(assign_group)
        df_filtered = df_filtered.dropna(subset=['Project_Group']).copy()
        df_filtered['ano'] = df_filtered['ano'].astype(int)

        st.markdown("### Socioeconomic Development Indicators")
        c1, c2, c3 = st.columns(3)
        with c1:
            selected_project = st.selectbox("1. Core Strategic Highway Corridor:", options=list(project_groups_mapping.keys()))
        with c2:
            selected_category = st.selectbox("2. Analytical Dimension:", options=list(categories_map.keys()))
        with c3:
            available_cols = categories_map[selected_category]
            available_opts = {col: all_variables_map[col] for col in available_cols}
            selected_var_code = st.selectbox("3. Granular Metric Target:", options=list(available_opts.keys()), format_func=lambda x: available_opts[x])

        df_plot = df_filtered[df_filtered['Project_Group'] == selected_project].copy()
        unique_muns = df_plot['Municipality_Code_Dane'].unique()
        var_label_en = all_variables_map[selected_var_code]

        fig = go.Figure()
        for idx, mun_code in enumerate(unique_muns):
            df_mun = df_plot[df_plot['Municipality_Code_Dane'] == mun_code].sort_values(by='ano')
            if df_mun[selected_var_code].isna().all(): continue
            
            s_col, e_col = mun_color_pairs[idx % len(mun_color_pairs)]
            colors_sampled = px.colors.sample_colorscale([s_col, e_col], [0.5])
            
            fig.add_trace(go.Scatter(
                x=df_mun['ano'], y=df_mun[selected_var_code], mode='lines+markers',
                name=f'Muni DANE {mun_code}', line=dict(color=colors_sampled[0], width=2.5),
                hovertemplate=f'<b>Year</b>: %{{x}}<br><b>{var_label_en}</b>: %{{y:.2f}}<extra></extra>'
            ))

        fig.update_layout(
            title=f"Evolution Trend: {var_label_en} ({selected_project})", xaxis_title="Year", yaxis_title=var_label_en,
            hovermode='x unified', template="plotly_white", height=520, margin=dict(t=60, b=30, l=40, r=40)
        )
        fig.update_xaxes(tickformat=".0f", dtick=1, gridcolor="#F2F4F4")
        fig.update_yaxes(gridcolor="#F2F4F4")
        
        st.plotly_chart(fig, use_container_width=True)

# ==============================================================================
# SECTION 6: DESCRIPTIVE STATISTICS & META-DATA EXPANDERS (col_right)
# ==============================================================================
with col_right:
    if main_menu == "1. Colombia Roads":
        st.markdown("<div style='background:#1a5276; color:white; padding:8px; font-weight:bold; border-radius:5px; font-family: monospace; font-size:12px; text-align:center;'>Infrastructure Breakdown</div>", unsafe_allow_html=True)
        
        fig_pies, (ax1, ax2) = plt.subplots(2, 1, figsize=(3.5, 5))
        fig_pies.patch.set_facecolor('none')
        
        # Pie 1: Entries with data/routes vs Municipalities without routes
        v1 = [count_any_roads, max(0.1, count_no_roads)]
        ax1.pie(v1, labels=['With Roads', 'No Roads'], 
                autopct=lambda pct: absolute_value_format(pct, v1), 
                colors=['#f4d03f', '#eeeeee'], startangle=90, 
                textprops={'fontsize': 8, 'family': 'monospace'})
        ax1.set_title("Network vs National Total", fontsize=9, family='monospace', color='#1a5276', weight='bold')
        
        # Pie 2: Inside entries with data -> Double/Dual vs others
        v2 = [count_doble_roads, max(0.1, count_other_roads)]
        ax2.pie(v2, labels=['Dual (Doble)', 'Other Types'], 
                autopct=lambda pct: absolute_value_format(pct, v2), 
                colors=['#27ae60', '#eeeeee'], startangle=90, 
                textprops={'fontsize': 8, 'family': 'monospace'})
        ax2.set_title("Dual vs Active Road Dataset", fontsize=9, family='monospace', color='#1a5276', weight='bold')
        
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
        
        total_eligible_network = count_any_roads if count_any_roads > 0 else 500
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
        # TOP SUBSECTION: Regional Map Zoom
        st.markdown("<div style='background:#1a5276; color:white; padding:8px; font-weight:bold; border-radius:5px; font-family: monospace; font-size:12px; text-align:center;'>Corridor Geospatial Zoom</div>", unsafe_allow_html=True)
        
        # Filter spatial layer to match targets based on current dropdown selection
        target_codes = [str(code) for code in project_groups_mapping[selected_project]]
        gdf_zoom_muni = gdf_municipalities[gdf_municipalities['Municipality_Code_DANE'].isin(target_codes)]
        
        fig_zoom, ax_zoom = plt.subplots(figsize=(3.5, 3.5))
        fig_zoom.patch.set_facecolor('none')
        
        # Plot gray baseline context and highlight targeted corridor nodes
        gdf_municipalities.plot(ax=ax_zoom, facecolor='#f4f4f4', edgecolor='#dddddd', linewidth=0.2)
        if not gdf_zoom_muni.empty:
            gdf_zoom_muni.plot(ax=ax_zoom, facecolor='#1a5276', edgecolor='black', linewidth=0.5)
            # Clip bounds specifically targeting the highlighted cluster
            minx,
