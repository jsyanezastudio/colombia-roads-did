import streamlit as st
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import plotly.express as px

# ==============================================================================
# CONFIGURACIÓN DE PÁGINA (Debe ser la primera instrucción de Streamlit)
# ==============================================================================
st.set_page_config(
    page_title="Colombia Infrastructure & Impact Dashboard",
    page_icon="🇨🇴",
    layout="wide"
)

# FORMATO ADICIONAL PARA GRÁFICAS DE MATPLOTLIB
def absolute_value_format(val, allvals):
    import numpy as np
    a = int(np.round(val/100.*np.sum(allvals)))
    return f"{a}"

# ==============================================================================
# SECCIÓN 1: INGESTIÓN Y CACHÉ DE DATOS (URLs Oficiales del Repositorio)
# ==============================================================================
@st.cache_data
def load_geospatial_data():
    # 1. Municipios Base de Colombia
    muni_url = "https://github.com/jsyanezastudio/colombia-roads-did/raw/refs/heads/main/colombia_municipalities_base.geojson"
    gdf_muni = gpd.read_file(muni_url)
    
    # 2. Red de Vías Compiladas (Líneas)
    roads_url = "https://github.com/jsyanezastudio/colombia-roads-did/raw/refs/heads/main/colombia_compiled_roads_network.geojson"
    gdf_roads = gpd.read_file(roads_url)
    
    return gdf_muni, gdf_roads

@st.cache_data
def load_impact_dataset():
    # 3. Dataset de Impacto Municipal (Panel de Series de Tiempo)
    impact_url = "https://github.com/jsyanezastudio/colombia-roads-did/raw/refs/heads/main/colombia_infrastructure_impact_dataset.csv"
    return pd.read_csv(impact_url)

# Carga segura de los datos corporativos
try:
    gdf_municipalities, gdf_compiled = load_geospatial_data()
    df_impact = load_impact_dataset()
except Exception as e:
    st.error(f"❌ Error crítico al conectar con el repositorio de datos de GitHub: {e}")
    st.stop()

# ==============================================================================
# SECCIÓN 2: PROCESAMIENTO PREVIO Y CONSTANTES MUNICIPALES
# ==============================================================================
TOTAL_MUNI_COUNT = 1122
if 'id_type' in gdf_municipalities.columns:
    TOTAL_MUNI_WITH_ROADS = len(gdf_municipalities[gdf_municipalities['id_type'] != 'Sin vías'])
else:
    TOTAL_MUNI_WITH_ROADS = 500  # Valor fallback seguro

# Extraer parámetros dinámicos para los filtros del Módulo 2
unique_projects = ["All"] + sorted(list(gdf_compiled['PROYECTO'].dropna().unique())) if 'PROYECTO' in gdf_compiled.columns else ["All"]
years_list = ["All"] + sorted(list(gdf_compiled['oper_year'].dropna().astype(int).unique())) if 'oper_year' in gdf_compiled.columns else ["All"]

# ==============================================================================
# SECCIÓN 3: ARQUITECTURA ESTRUCTURAL DE COLUMNAS (Streamlit Layout)
# ==============================================================================
st.markdown("<h1 style='text-align: center; color: #1a5276;'>🇨🇴 Infraestructura Vial e Impacto Municipal en Colombia</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #555;'>Plataforma Analítica Interactiva para la evaluación de proyectos viales y Diferencia en Diferencias (DiD)</p>", unsafe_allow_html=True)
st.markdown("---")

col_control, col_map, col_right = st.columns([1.5, 5, 2.5])

# ==============================================================================
# SECCIÓN 4: CONTROL DE FILTROS LATERALES (col_control)
# ==============================================================================
with col_control:
    st.markdown("### 🗺️ Módulos del Sistema")
    main_menu = st.selectbox(
        "Selecciona el Enfoque:",
        options=["1. Colombia Roads", "2. DiD Candidates", "3. City Data Exploration"]
    )
    
    st.markdown("---")
    st.markdown("### 🎛️ Filtros Dinámicos")

    # --- CONTROL MÓDULO 1 ---
    if main_menu == "1. Colombia Roads":
        st.markdown("**Capas del Mapa:**")
        show_any_roads = st.checkbox("Municipios con Red Vial", value=True)
        show_doble_roads = st.checkbox("Municipios con Doble Calzada", value=True)

    # --- CONTROL MÓDULO 2 ---
    elif main_menu == "2. DiD Candidates":
        filter_mode = st.radio("Filtrar Muestra Por:", ['Proyecto', 'Año de Operación'], horizontal=True)
        val_proj = "All"
        val_year = "All"
        is_project_mode = (filter_mode == 'Proyecto')

        if is_project_mode:
            val_proj = st.selectbox('Selecciona Proyecto:', options=unique_projects, key="proj_select")
        else:
            val_year = st.selectbox('Selecciona Año:', options=years_list, key="year_select")

        # Cómputo espacial en caliente para candidatos DiD
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

        # Métrica KPI integrada en el menú lateral
        st.markdown(
            f"""
            <div style='text-align:center; padding: 10px; background: white; border: 2px solid #1a5276; border-radius: 8px; margin-top: 15px; margin-bottom: 10px; font-family: monospace;'>
                <span style='font-size: 10px; color: #555; text-transform: uppercase;'>Municipios Impactados</span><br>
                <span style='font-size: 24px; color: #1a5276; font-weight: bold;'>{selected_count}</span>
            </div>
            """, 
            unsafe_allow_html=True
        )

    # --- CONTROL MÓDULO 3 ---
    elif main_menu == "3. City Data Exploration":
        st.info("💡 Panel interactivo configurado. Selecciona las variables directamente en la sección central.")

# ==============================================================================
# SECCIÓN 5: VISUALIZACIONES PRINCIPALES: MAPAS Y SERIES DE TIEMPO (col_map)
# ==============================================================================
with col_map:
    # --- PROCESO PARA MAPAS ESTÁTICOS (MÓDULOS 1 Y 2) ---
    if main_menu == "1. Colombia Roads" or main_menu == "2. DiD Candidates":
        fig_map, ax_map = plt.subplots(figsize=(9, 11))
        
        # Capa municipal base de fondo
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

    # --- PROCESO PARA GRÁFICAS DE IMPACTO TEMPORAL (MÓDULO 3) ---
    elif main_menu == "3. City Data Exploration":
        # Diccionarios estructurados del Pipeline de Municipios
        categories_map = {
            'Educación': ['s11_total', 'alumn_total', 'docen_total'],
            'Servicios e Infraestructura': ['tacued', 'turbacued', 'truracued', 'talcan'],
            'Fiscal e Impacto': ['inv_total', 'TMI', 'y_total', 'y_corr']
        }
        all_variables_map = {
            's11_total': 'Prueba Saber11', 'alumn_total': 'Estudiantes', 'docen_total': 'Maestros',
            'tacued': 'Acueducto Total', 'turbacued': 'Acueducto Urbano', 'truracued': 'Acueducto Rural', 'talcan': 'Alcantarillado',
            'inv_total': 'Inversión Total', 'TMI': 'Mortalidad Infantil', 'y_total': 'Ingresos Totales', 'y_corr': 'Ingresos Corrientes'
        }
        project_groups_mapping = {
            "Corridor Honda - Puerto Salgar - Girardot": [73275, 25307],
            "Corridor Armenia - Pereira - Manizales (Eje Cafetero)": [17174, 17001, 66001, 63690, 66682, 17873],
            "Corridor Bogotá - La Vega - Villeta": [25402, 25430, 25489, 25491, 25658, 25769]
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

        # UI de Triple Filtro Jerárquico Horizontal nativo de Streamlit
        st.markdown("### 🎛️ Variables de Desarrollo Socioeconómico")
        c1, c2, c3 = st.columns(3)
        with c1:
            selected_project = st.selectbox("1. Corredor Vial Core:", options=list(project_groups_mapping.keys()))
        with c2:
            selected_category = st.selectbox("2. Dimensión de Análisis:", options=list(categories_map.keys()))
        with c3:
            available_cols = categories_map[selected_category]
            available_opts = {col: all_variables_map[col] for col in available_cols}
            selected_var_code = st.selectbox("3. Métrica Detallada:", options=list(available_opts.keys()), format_func=lambda x: available_opts[x])

        df_plot = df_filtered[df_filtered['Project_Group'] == selected_project].copy()
        unique_muns = df_plot['Municipality_Code_Dane'].unique()
        var_label_es = all_variables_map[selected_var_code]

        # Creación de la gráfica de líneas interactiva (Plotly)
        fig = go.Figure()
        for idx, mun_code in enumerate(unique_muns):
            df_mun = df_plot[df_plot['Municipality_Code_Dane'] == mun_code].sort_values(by='ano')
            if df_mun[selected_var_code].isna().all(): continue
            
            s_col, e_col = mun_color_pairs[idx % len(mun_color_pairs)]
            colors_sampled = px.colors.sample_colorscale([s_col, e_col], [0.5])
            
            fig.add_trace(go.Scatter(
                x=df_mun['ano'], y=df_mun[selected_var_code], mode='lines+markers',
                name=f'Muni DANE {mun_code}', line=dict(color=colors_sampled[0], width=2.5),
                hovertemplate=f'<b>Año</b>: %{{x}}<br><b>{var_label_es}</b>: %{{y:.2f}}<extra></extra>'
            ))

        fig.update_layout(
            title=f"Tendencia de: {var_label_es} ({selected_project})", xaxis_title="Año", yaxis_title=var_label_es,
            hovermode='x unified', template="plotly_white", height=520, margin=dict(t=60, b=30, l=40, r=40)
        )
        fig.update_xaxes(tickformat=".0f", dtick=1, gridcolor="#F2F4F4")
        fig.update_yaxes(gridcolor="#F2F4F4")
        
        st.plotly_chart(fig, use_container_width=True)

# ==============================================================================
# SECCIÓN 6: PANELES DE ESTADÍSTICAS COMPLEMENTARIAS (col_right)
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
        ax1.set_title("Network vs National Total", fontsize=9, family='monospace', color='#1a5276', weight='bold')
        
        v2 = [count_doble_roads, max(0.1, count_other_roads)]
        ax2.pie(v2, labels=['Dual (Doble)', 'Other'], 
                autopct=lambda pct: absolute_value_format(pct, v2), 
                colors=['#27ae60', '#eeeeee'], startangle=90, 
                textprops={'fontsize': 8, 'family': 'monospace'})
        ax2.set_title("Dual vs Road Network", fontsize=9, family='monospace', color='#1a5276', weight='bold')
        
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
        st.markdown("<div style='font-family: monospace; font-size: 11px; font-weight: bold; color: #1a5276; margin-bottom: 5px;'>Listado de Municipios</div>", unsafe_allow_html=True)
        if not muni_list_data.empty:
            st.dataframe(
                muni_list_data.rename(columns={'Municipality_Code_DANE': 'Código', 'Municipality_Name_DANE': 'Municipio'}),
                hide_index=True, use_container_width=True, height=220
            )
        else:
            st.info("Ningún municipio intersecta los criterios.")

    elif main_menu == "3. City Data Exploration":
        st.markdown("<div style='background:#1a5276; color:white; padding:8px; font-weight:bold; border-radius:5px; font-family: monospace; font-size:12px; text-align:center;'>Detalles de Cobertura</div>", unsafe_allow_html=True)
        st.markdown("<p style='font-size:12px; font-family:monospace; margin-top:10px;'>Este panel consolida variables clave de los censos y registros del DANE e interconecta las métricas de educación y servicios públicos con el año de entrega del corredor vial correspondiente.</p>", unsafe_allow_html=True)
        
        # Mini matriz con datos brutos para auditoría rápida
        if 'df_plot' in locals() and not df_plot.empty:
            with st.expander("🔍 Ver Matriz Numérica"):
                st.dataframe(
                    df_plot[['Municipality_Code_Dane', 'ano', selected_var_code]]
                    .rename(columns={'Municipality_Code_Dane': 'Muni', 'ano': 'Año', selected_var_code: 'Valor'})
                    .dropna(),
                    hide_index=True, height=250
                )
