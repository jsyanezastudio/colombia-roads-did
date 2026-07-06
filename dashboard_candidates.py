import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

# --- 1. CONFIGURACIÓN DE MAPEOS Y VARIABLES (Pools en Español) ---
categories_map = {
    'Educación': ['s11_total', 'alumn_total', 'docen_total'],
    'Servicios e Infraestructura': ['tacued', 'turbacued', 'truracued', 'talcan'],
    'Fiscal e Impacto': ['inv_total', 'TMI', 'y_total', 'y_corr']
}

all_variables_map = {
    's11_total': 'Prueba Saber11', 
    'alumn_total': 'Estudiantes', 
    'docen_total': 'Maestros',
    'tacued': 'Acueducto Total', 
    'turbacued': 'Acueducto Urbano', 
    'truracued': 'Acueducto Rural', 
    'talcan': 'Alcantarillado',
    'inv_total': 'Inversión Total', 
    'TMI': 'Mortalidad Infantil', 
    'y_total': 'Ingresos Totales', 
    'y_corr': 'Ingresos Corrientes'
}

project_groups_mapping = {
    "Corridor Honda - Puerto Salgar - Girardot": [73275, 25307],
    "Corridor Armenia - Pereira - Manizales (Eje Cafetero)": [17174, 17001, 66001, 63690, 66682, 17873],
    "Corridor Bogotá - La Vega - Villeta": [25402, 25430, 25489, 25491, 25658, 25769]
}

# Colores base por municipio para generar gradientes estables
mun_color_pairs = [
    ('#1A5276', '#5DADE2'), # Azul oscuro a claro
    ('#1E8449', '#58D68D'), # Verde oscuro a claro
    ('#A93226', '#E74C3C'), # Rojo oscuro a claro
    ('#7D3C98', '#BB8FCE'), # Morado oscuro a claro
    ('#B05C00', '#F39C12'), # Naranja oscuro a claro
    ('#2C3E50', '#7F8C8D'), # Gris oscuro a claro
    ('#4A232A', '#8D6E63'), # Café oscuro a claro
    ('#1C2833', '#5D6D7E')  # Azul grisáceo oscuro a claro
]

# --- 2. FUNCIÓN DE RENDERIZADO DEL MÓDULO ---
def render_city_data_exploration(df_master):
    st.markdown("## 🏙️ Módulo 3: City Data Exploration")
    st.markdown("Analiza de forma interactiva el impacto de los proyectos viales a nivel municipal combinando diferentes dimensiones de desarrollo.")

    # 2.1. Carga y preparación inicial de datos filtrados
    df_filtered = df_master.copy()
    
    # Inyectar la columna de Grupo de Proyecto basada en el mapeo oficial
    def assign_project_group(code):
        for group_name, codes in project_groups_mapping.items():
            if code in codes:
                return group_name
        return None

    df_filtered['Project_Group'] = df_filtered['Municipality_Code_Dane'].apply(assign_project_group)
    df_filtered = df_filtered.dropna(subset=['Project_Group']).copy()
    df_filtered['ano'] = df_filtered['ano'].astype(int)

    # 2.2. ESTRUCTURA DE FILTROS NATIVOS EN STREAMLIT (Triple Filtro Jerárquico)
    st.markdown("### 🎛️ Panel de Control Jerárquico")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Filtro 1: Selección del Proyecto Core
        selected_project = st.selectbox(
            "1. Selecciona el Corredor Vial:",
            options=list(project_groups_mapping.keys())
        )
        
    with col2:
        # Filtro 2: Tipo de Categoría Macro
        selected_category = st.selectbox(
            "2. Selecciona la Dimensión de Análisis:",
            options=list(categories_map.keys())
        )
        
    with col3:
        # Filtro 3: Variable Específica (Heredada dinámicamente según la categoría macro)
        available_columns = categories_map[selected_category]
        available_options = {col: all_variables_map[col] for col in available_columns}
        
        selected_var_code = st.selectbox(
            "3. Selecciona la Métrica Detallada:",
            options=list(available_options.keys()),
            format_func=lambda x: available_options[x]
        )

    # 2.3. FILTRADO DE DATOS FINAL
    df_plot = df_filtered[df_filtered['Project_Group'] == selected_project].copy()
    unique_muns = df_plot['Municipality_Code_Dane'].unique()
    
    # Variable legible para títulos y etiquetas
    var_label_es = all_variables_map[selected_var_code]

    if len(unique_muns) == 0:
        st.warning(f"No se encontraron registros municipales para el proyecto: {selected_project}")
        return

    # 2.4. CONSTRUCCIÓN DE LA GRÁFICA INTERACTIVA CON PLOTLY
    fig = go.Figure()
    num_vars = len(all_variables_map)

    # Ciclo iterativo por municipio aplicando la lógica de gradientes estéticos
    for idx, mun_code in enumerate(unique_muns):
        df_mun = df_plot[df_plot['Municipality_Code_Dane'] == mun_code].sort_values(by='ano')
        
        # Ignorar si no hay datos válidos para la métrica seleccionada
        if df_mun[selected_var_code].isna().all():
            continue

        # Selección de paleta y muestreo para gradiente del municipio
        start_color, end_color = mun_color_pairs[idx % len(mun_color_pairs)]
        color_positions = [i / (num_vars - 1) if num_vars > 1 else 0.5 for i in range(num_vars)]
        colors_sampled = px.colors.sample_colorscale([start_color, end_color], color_positions)
        
        # Usamos un color promedio o representativo de la escala para la línea del municipio
        mun_color = colors_sampled[len(colors_sampled) // 2]

        fig.add_trace(go.Scatter(
            x=df_mun['ano'],
            y=df_mun[selected_var_code],
            mode='lines+markers',
            name=f'Municipio {mun_code}',
            line=dict(color=mun_color, width=2.5),
            marker=dict(size=6),
            hovertemplate=(
                '<b>Año</b>: %{x}<br>' +
                f'<b>{var_label_es}</b>: %{{y:.2f}}<br>' +
                f'<b>Código DANE</b>: {mun_code}<extra></extra>'
            )
        ))

    # Estilización del layout de la gráfica
    fig.update_layout(
        title=dict(
            text=f"Evolución Temporal de {var_label_es}<br><sub>{selected_project}</sub>",
            x=0,
            font=dict(size=18)
        ),
        xaxis_title="Año",
        yaxis_title=var_label_es,
        hovermode='x unified',
        legend_title="Municipios",
        height=550,
        margin=dict(t=100, b=50, l=50, r=50),
        template="plotly_white"
    )
    
    fig.update_xaxes(tickformat=".0f", dtick=1, gridcolor="#EAECEE")
    fig.update_yaxes(gridcolor="#EAECEE")

    # 2.5. DESPLIEGUE EN LA INTERFAZ
    st.plotly_chart(fig, use_container_width=True)
    
    # Tabla de datos complementaria para inspección rápida (opcional pero recomendada)
    with st.expander("📊 Ver matriz de datos resumida"):
        df_table = df_plot[['Municipality_Code_Dane', 'ano', selected_var_code]].copy()
        df_table.columns = ['Código Municipio DANE', 'Año', var_label_es]
        st.dataframe(df_table.dropna().reset_index(drop=True), use_container_width=True)
