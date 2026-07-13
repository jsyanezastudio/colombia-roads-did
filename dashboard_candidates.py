import streamlit as st
import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import plotly.express as px
import requests

# ==============================================================================
# SECTION 1: STREAMLIT PAGE CONFIGURATION
# ==============================================================================
st.set_page_config(
    page_title="Colombia Road Infrastructure Dashboard",
    layout="wide"
)

# ==============================================================================
# SECTION 2: DATA LOADING & OPTIMIZATION (CACHING)
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
    
    if isinstance(json_data, dict) and "features" in json_data:
        records = [feat["properties"] for feat in json_data["features"]]
        df_road_type = pd.DataFrame(records)
    else:
        df_road_type = pd.DataFrame(json_data)
        
    for col in ['pre_date', 'start_date', 'oper_date']:
        gdf_roads[col] = pd.to_datetime(gdf_roads[col], errors='coerce', dayfirst=True)
    gdf_roads['oper_year'] = gdf_roads['oper_date'].dt.year
    
    if gdf_muni.crs != gdf_roads.crs:
        gdf_muni = gdf_muni.to_crs(gdf_roads.crs)
        
    muni_key = 'Municipality_Code_DANE' if 'Municipality_Code_DANE' in gdf_muni.columns else gdf_muni.columns[0]
    df_key = 'Municipality_Code_DANE' if 'Municipality_Code_DANE' in df_road_type.columns else df_road_type.columns[0]
    
    gdf_muni[muni_key] = gdf_muni[muni_key].astype(str).str.strip()
    df_road_type[df_key] = df_road_type[df_key].astype(str).str.strip()
    
    df_road_type = df_road_type.rename(columns={df_key: 'muni_code_match', 'Id_type': 'id_type'})
    
    df_road_type['is_doble'] = df_road_type['id_type'].str.lower().str.contains('doble|dual|2', na=False)
    df_road_type = df_road_type.sort_values(by='is_doble', ascending=False)
    df_road_type_clean = df_road_type[['muni_code_match', 'id_type']].drop_duplicates(subset=['muni_code_match'])
    
    gdf_muni = gdf_muni.merge(df_road_type_clean, left_on=muni_key, right_on='muni_code_match', how='left')
    gdf_muni['id_type'] = gdf_muni['id_type'].fillna('Sin vías')
        
    return gdf_roads, gdf_muni, df_road_type

@st.cache_data
def load_impact_dataset():
    impact_url = f"{GITHUB_RAW_BASE}/colombia_infrastructure_impact_dataset.csv"
    try:
        return pd.read_csv(impact_url)
    except Exception as e:
        raise RuntimeError(f"Error loading impact dataset: {e}")

try:
    gdf_compiled, gdf_municipalities, df_muni_road_type = load_data()
    df_impact = load_impact_dataset()
except Exception as e:
    st.error(f"Critical Error: {e}")
    st.stop()

TOTAL_MUNI_COUNT = len(gdf_municipalities)
ALL_ROAD_MUNI_HITS = gpd.sjoin(gdf_municipalities, gdf_compiled, how="inner", predicate="intersects")
TOTAL_MUNI_WITH_ROADS = len(ALL_ROAD_MUNI_HITS.index.unique())

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
    
    return sorted_projects, sorted_years

unique_projects, years_list = get_sorted_filters(gdf_compiled, gdf_municipalities)

project_groups_mapping = {
    "Bogotá – La Vega – Villeta": {
        "codes": [25402, 25430, 25489, 25491, 25658, 25769]
    },
    "Desarrollo Vial del Oriente de Medellín – DEVIMED": {
        "codes": [17174, 17001, 66001, 63690, 66682, 17873]
    },
    "Honda – Puerto Salgar – Girardot": {
        "codes": [73275, 25307]
    }
}

# ==============================================================================
# SECTION 4: HEADER DISPLAY BLOCK
# ==============================================================================
st.markdown(
    """
    <div style='text-align:center; padding: 20px 15px; background-color: #1a5276; color: white; border-radius: 8px; margin-bottom: 20px; font-family: monospace;'>
        <h1 style='margin: 0 0 10px 0; font-size: 32px; font-weight: 800; color: white !important; letter-spacing: -0.5px;'>
            Colombia Road Infrastructure Analytics Platform
        </h1>
        <p style='margin: 0 auto; opacity: 0.9; font-size: 13.5px; color: white !important; max-width: 85%; line-height: 1.4; font-weight: 500;'>
            Visualizes multi-layered municipal and road datasets. 
            Evaluates treatment trends over dynamic operational timelines. 
            Provides empirical baseline data for impact models.
        </p>
    </div>
    """, 
    unsafe_allow_html=True
)

# ==============================================================================
# SECTION 5: RESPONSIVE DASHBOARD LAYOUT DEFINITION
# ==============================================================================
col_control, col_map, col_right = st.columns([20, 55, 25])

# ==============================================================================
# SECTION 6: SIDE PANEL CONTROLS
# ==============================================================================
with col_control:
    st.markdown("### Main Menu")
    main_menu = st.selectbox(
        "Select View Module:",
        options=["1. Colombia Roads", "2. Municipalities with Projects", "3. Municipality Data Exploration"]
    )
    
    st.markdown("---")
    st.markdown("### Dynamic Filters")

    if main_menu == "1. Colombia Roads":
        st.markdown("**Layer Visibility Settings:**")
        show_any_roads = st.checkbox("Show Municipalities with Roads", value=True)
        show_doble_roads = st.checkbox("Show Dual Carriageways (Doble)", value=True)

    elif main_menu == "2. Municipalities with Projects":
        filter_mode = st.radio("Filter Analysis By:", ['Project', 'Year'], horizontal=True)
        val_proj, val_year = "All", "All"
        is_project_mode = (filter_mode == 'Project')

        if is_project_mode:
            val_proj = st.selectbox('Select Project:', options=unique_projects, key="proj_select")
        else:
            val_year = st.selectbox('Select Operation Year:', options=years_list, key="year_select")

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

        st.markdown(
            f"""
            <div style='text-align:center; padding: 10px; background: white; border: 2px solid #1a5276; border-radius: 8px; margin-top: 15px; margin-bottom: 10px; font-family: monospace;'>
                <span style='font-size: 10px; color: #555; text-transform: uppercase;'>Total Municipalities</span><br>
                <span style='font-size: 24px; color: #1a5276; font-weight: bold;'>{selected_count}</span>
            </div>
            """, 
            unsafe_allow_html=True
        )

    elif main_menu == "3. Municipality Data Exploration":
        st.markdown(
            """
            <div style='background-color: #ebf5fb; color: #2e4053; font-size: 11px; padding: 10px; border-radius: 5px; border-left: 3px solid #3498db;'>
                Interactive dimensions enabled. Modify variables inside the viewport setup panels directly.
            </div>
            """, unsafe_allow_html=True
        )

    st.markdown("---")
    st.markdown("### Module Description")
    if main_menu == "1. Colombia Roads":
        st.markdown("<div style='background-color: #f8f9f9; padding: 12px; border-left: 4px solid #1a5276; font-size: 15px; font-family: sans-serif; color: #2c3e50; line-height: 1.4;'>Global analysis of Colombian municipalities targeting active road networks alongside explicit tracking of structural improvements and highway upgrades within these zones.</div>", unsafe_allow_html=True)
    elif main_menu == "2. Municipalities with Projects":
        st.markdown("<div style='background-color: #f8f9f9; padding: 12px; border-left: 4px solid #1a5276; font-size: 15px; font-family: sans-serif; color: #2c3e50; line-height: 1.4;'>Granular analysis of targeted territories hosting specific road network segments fully upgraded and actively in operation, filtered interactively by operational calendar years.</div>", unsafe_allow_html=True)
    elif main_menu == "3. Municipality Data Exploration":
        st.markdown("<div style='background-color: #f8f9f9; padding: 12px; border-left: 4px solid #1a5276; font-size: 15px; font-family: sans-serif; color: #2c3e50; line-height: 1.4;'>Strategic performance evaluation isolating core infrastructure projects displaying optimal econometric projections for rigorous impact evaluations using Difference-in-Differences (DiD) or Synthetic Control methodologies.</div>", unsafe_allow_html=True)

# ==============================================================================
# SECTION 7: GEOSPATIAL MAP / PLOTLY TRENDS PLOTTING (col_map)
# ==============================================================================
with col_map:
    if main_menu != "3. Municipality Data Exploration":
        fig_map, ax_map = plt.subplots(figsize=(9, 11))
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

        elif main_menu == "2. Municipalities with Projects":
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
        # --- SECCIÓN 3: EXPLORACIÓN DE DATOS CON PLOTLY ---
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
            for g_name, meta in project_groups_mapping.items():
                if int(code) in meta["codes"]: return g_name
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
            selected_var_code = st.selectbox("3. Granular Metric Target:", options=available_cols, format_func=lambda x: all_variables_map[x])

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
# SECTION 8: RIGHT PANEL VISUALIZATIONS & CHARTS (col_right)
# ==============================================================================
with col_right:
    if main_menu == "1. Colombia Roads" and 'id_type' in gdf_municipalities.columns:
        st.markdown("<div style='background:#1a5276; color:white; padding:8px; font-weight:bold; border-radius:5px; font-family: monospace; font-size:12px; text-align:center;'>Infrastructure Breakdown</div>", unsafe_allow_html=True)
        
        count_any_roads = len(gdf_municipalities[gdf_municipalities['id_type'] != 'Sin vías'])
        count_doble_roads = len(gdf_municipalities[gdf_municipalities['id_type'] == 'Doble'])
        count_no_roads = TOTAL_MUNI_COUNT - count_any_roads
        count_other_roads = count_any_roads - count_doble_roads

        # OPTIMIZACIÓN: Aumentado el tamaño vertical y horizontal del canvas (figsize)
        fig_pies, (ax1, ax2) = plt.subplots(2, 1, figsize=(4.5, 8.5))
        fig_pies.patch.set_facecolor('none')
        
        v1 = [count_any_roads, max(0.1, count_no_roads)]
        # OPTIMIZACIÓN: Añadido radius=1.2 para expandir el pastel dentro de su eje
        ax1.pie(v1, labels=['With Roads', 'No Roads'], 
                autopct=lambda pct: absolute_value_format(pct, v1), 
                colors=['#f4d03f', '#eeeeee'], startangle=90, radius=1.2,
                textprops={'fontsize': 9, 'family': 'monospace'})
        ax1.set_title("Proportional Distribution:\nTreatment Stock within National Baseline", fontsize=9.5, family='monospace', color='#1a5276', weight='bold', pad=15)
        
        v2 = [count_doble_roads, max(0.1, count_other_roads)]
        # OPTIMIZACIÓN: Añadido radius=1.2 para expandir el segundo pastel
        ax2.pie(v2, labels=['Dual (Doble)', 'Other Types'], 
                autopct=lambda pct: absolute_value_format(pct, v2), 
                colors=['#27ae60', '#eeeeee'], startangle=90, radius=1.2,
                textprops={'fontsize': 9, 'family': 'monospace'})
        ax2.set_title("Segment Allocation:\nHigh-Capacity (Dual) within Active Road Network", fontsize=9.5, family='monospace', color='#1a5276', weight='bold', pad=15)
        
        plt.tight_layout()
        st.pyplot(fig_pies, use_container_width=True)

    elif main_menu == "2. Municipalities with Projects":
        st.markdown("<div style='background:#1a5276; color:white; padding:8px; font-weight:bold; border-radius:5px 5px 0 0; font-family: monospace; font-size:12px; text-align:center;'>DiD Sample Statistics</div>", unsafe_allow_html=True)
        
        # OPTIMIZACIÓN: Aumentado el tamaño vertical del canvas para el módulo de proyectos
        fig_pies, (ax1, ax2) = plt.subplots(2, 1, figsize=(4.5, 7.5))
        fig_pies.patch.set_facecolor('none') 
        
        v3 = [selected_count, max(0.1, TOTAL_MUNI_COUNT - selected_count)]
        ax1.pie(v3, labels=['Selected', 'Other'], 
                autopct=lambda pct: absolute_value_format(pct, v3), 
                colors=['#1a5276', '#eeeeee'], startangle=90, radius=1.2,
                textprops={'fontsize': 9, 'family': 'monospace'})
        ax1.set_title("vs National Total", fontsize=9.5, family='monospace', color='#1a5276', weight='bold', pad=15)
        
        v4 = [selected_count, max(0.1, TOTAL_MUNI_WITH_ROADS - selected_count)]
        ax2.pie(v4, labels=['Selected', 'Other'], 
                autopct=lambda pct: absolute_value_format(pct, v4), 
                colors=['#d4e6f1', '#eeeeee'], startangle=90, radius=1.2,
                textprops={'fontsize': 9, 'family': 'monospace'})
        ax2.set_title("vs Road Network", fontsize=9.5, family='monospace', color='#1a5276', weight='bold', pad=15)
        
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

    elif main_menu == "3. Municipality Data Exploration":
        # --------------------------------------------------------------------------
        # SECCIÓN 3: COMPONENTES DINÁMICOS DE LA COLUMNA DERECHA
        # --------------------------------------------------------------------------
        st.markdown("<div style='background:#1a5276; color:white; padding:8px; font-weight:bold; border-radius:5px; font-family: monospace; font-size:12px; text-align:center;'>Project Corridor Zoom</div>", unsafe_allow_html=True)
        
        gdf_project_roads = gdf_compiled[gdf_compiled['PROYECTO'] == selected_project]
        active_years = gdf_project_roads['oper_year'].dropna().unique()
        year_display = str(int(active_years[0])) if len(active_years) > 0 else "N/A"
        
        st.markdown(
            f"""
            <div style='text-align:center; padding: 6px; background: #ebf5fb; border: 1px dashed #1a5276; border-radius: 6px; margin-top: 10px; margin-bottom: 10px; font-family: monospace;'>
                <span style='font-size: 10px; color: #555; text-transform: uppercase;'>Project Operation Year</span><br>
                <span style='font-size: 15px; color: #1a5276; font-weight: bold;'>{year_display}</span>
            </div>
            """, 
            unsafe_allow_html=True
        )
        
        spatial_hits = gpd.sjoin(gdf_municipalities, gdf_project_roads, how="inner", predicate="intersects")
        
        fig_zoom, ax_zoom = plt.subplots(figsize=(4, 4))
        fig_zoom.patch.set_facecolor('none')
        gdf_municipalities.plot(ax=ax_zoom, facecolor='#f4f6f6', edgecolor='#d5dbdb', linewidth=0.2)
        
        if not spatial_hits.empty:
            gdf_zoom_muni = gdf_municipalities.loc[spatial_hits.index.unique()]
            gdf_zoom_muni.plot(ax=ax_zoom, facecolor='#d4e6f1', edgecolor='#1a5276', linewidth=0.5, alpha=0.7)
            gdf_project_roads.plot(ax=ax_zoom, color='#cb4335', linewidth=1.5)
            
            minx, miny, maxx, maxy = gdf_zoom_muni.total_bounds
            ax_zoom.set_xlim([minx - 0.4, maxx + 0.4])
            ax_zoom.set_ylim([miny - 0.4, maxy + 0.4])
        else:
            target_codes = [str(c) for c in project_groups_mapping[selected_project]["codes"]]
            gdf_zoom_muni = gdf_municipalities[gdf_municipalities['Municipality_Code_DANE'].astype(str).isin(target_codes)]
            if not gdf_zoom_muni.empty:
                gdf_zoom_muni.plot(ax=ax_zoom, facecolor='#d4e6f1', edgecolor='#1a5276', linewidth=0.5, alpha=0.7)
                minx, miny, maxx, maxy = gdf_zoom_muni.total_bounds
                ax_zoom.set_xlim([minx - 0.5, maxx + 0.5])
                ax_zoom.set_ylim([miny - 0.5, maxy + 0.5])
                
        ax_zoom.set_axis_off()
        plt.tight_layout()
        st.pyplot(fig_zoom, use_container_width=True)
        
        st.markdown("<div style='font-family: monospace; font-size: 11px; font-weight: bold; color: #1a5276; margin-top:12px; margin-bottom: 5px;'>Corridor Group Mapping</div>", unsafe_allow_html=True)
        
        if not spatial_hits.empty:
            corridor_list_data = gdf_zoom_muni[['Municipality_Name_DANE', 'Municipality_Code_DANE']].drop_duplicates().sort_values('Municipality_Name_DANE')
            st.dataframe(
                corridor_list_data.rename(columns={'Municipality_Name_DANE': 'Municipality', 'Municipality_Code_DANE': 'Code'}),
                hide_index=True, use_container_width=True, height=220
            )
        else:
            target_codes = [str(c) for c in project_groups_mapping[selected_project]["codes"]]
            gdf_table_muni = gdf_municipalities[gdf_municipalities['Municipality_Code_DANE'].astype(str).isin(target_codes)]
            if not gdf_table_muni.empty:
                corridor_list_data = gdf_table_muni[['Municipality_Name_DANE', 'Municipality_Code_DANE']].drop_duplicates().sort_values('Municipality_Name_DANE')
                st.dataframe(
                    corridor_list_data.rename(columns={'Municipality_Name_DANE': 'Municipality', 'Municipality_Code_DANE': 'Code'}),
                    hide_index=True, use_container_width=True, height=220
                )
            else:
                st.info("No municipal items found matching the current cluster index.")
