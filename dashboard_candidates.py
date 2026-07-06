# ==============================================================================
# SECTION 8: RIGHT PANEL VISUALIZATIONS & CHARTS (col_right)
# ==============================================================================
with col_right:
    if main_menu == "1. Colombia Roads" and 'id_type' in gdf_municipalities.columns:
        st.markdown("<div style='background:#1a5276; color:white; padding:8px; font-weight:bold; border-radius:5px; font-family: sans-serif; font-size:12px; text-align:center;'>Infrastructure Breakdown</div>", unsafe_allow_html=True)
        
        count_any_roads = len(gdf_municipalities[gdf_municipalities['id_type'] != 'Sin vías'])
        count_doble_roads = len(gdf_municipalities[gdf_municipalities['id_type'] == 'Doble'])
        count_no_roads = TOTAL_MUNI_COUNT - count_any_roads
        count_other_roads = count_any_roads - count_doble_roads

        fig_pies, (ax1, ax2) = plt.subplots(2, 1, figsize=(4.5, 8.5))
        fig_pies.patch.set_facecolor('none')
        
        v1 = [count_any_roads, max(0.1, count_no_roads)]
        # FUENTE CAMBIADA A SANS-SERIF PARA IGUALAR ETIQUETAS DE STREAMLIT
        ax1.pie(v1, labels=['With Roads', 'No Roads'], 
                autopct=lambda pct: absolute_value_format(pct, v1), 
                colors=['#f4d03f', '#eeeeee'], startangle=90, radius=1.2,
                textprops={'fontsize': 9, 'family': 'sans-serif'})
        ax1.set_title("Proportional Distribution:\nTreatment Stock within National Baseline", fontsize=10, family='sans-serif', color='#262730', weight='bold', pad=15)
        
        v2 = [count_doble_roads, max(0.1, count_other_roads)]
        # FUENTE CAMBIADA A SANS-SERIF PARA IGUALAR ETIQUETAS DE STREAMLIT
        ax2.pie(v2, labels=['Dual (Doble)', 'Other Types'], 
                autopct=lambda pct: absolute_value_format(pct, v2), 
                colors=['#27ae60', '#eeeeee'], startangle=90, radius=1.2,
                textprops={'fontsize': 9, 'family': 'sans-serif'})
        ax2.set_title("Segment Allocation:\nHigh-Capacity (Dual) within Active Road Network", fontsize=10, family='sans-serif', color='#262730', weight='bold', pad=15)
        
        plt.tight_layout()
        st.pyplot(fig_pies, use_container_width=True)

    elif main_menu == "2. Municipalities with Projects":
        st.markdown("<div style='background:#1a5276; color:white; padding:8px; font-weight:bold; border-radius:5px 5px 0 0; font-family: sans-serif; font-size:12px; text-align:center;'>DiD Sample Statistics</div>", unsafe_allow_html=True)
        
        fig_pies, (ax1, ax2) = plt.subplots(2, 1, figsize=(4.5, 7.5))
        fig_pies.patch.set_facecolor('none') 
        
        v3 = [selected_count, max(0.1, TOTAL_MUNI_COUNT - selected_count)]
        # FUENTE CAMBIADA A SANS-SERIF PARA IGUALAR ETIQUETAS DE STREAMLIT
        ax1.pie(v3, labels=['Selected', 'Other'], 
                autopct=lambda pct: absolute_value_format(pct, v3), 
                colors=['#1a5276', '#eeeeee'], startangle=90, radius=1.2,
                textprops={'fontsize': 9, 'family': 'sans-serif'})
        ax1.set_title("vs National Total", fontsize=10, family='sans-serif', color='#262730', weight='bold', pad=15)
        
        v4 = [selected_count, max(0.1, TOTAL_MUNI_WITH_ROADS - selected_count)]
        # FUENTE CAMBIADA A SANS-SERIF PARA IGUALAR ETIQUETAS DE STREAMLIT
        ax2.pie(v4, labels=['Selected', 'Other'], 
                autopct=lambda pct: absolute_value_format(pct, v4), 
                colors=['#d4e6f1', '#eeeeee'], startangle=90, radius=1.2,
                textprops={'fontsize': 9, 'family': 'sans-serif'})
        ax2.set_title("vs Road Network", fontsize=10, family='sans-serif', color='#262730', weight='bold', pad=15)
        
        plt.tight_layout()
        st.pyplot(fig_pies, use_container_width=True)
        
        st.markdown("---")
        st.markdown("<div style='font-family: sans-serif; font-size: 11px; font-weight: bold; color: #1a5276; margin-bottom: 5px;'>Impacted Municipalities List</div>", unsafe_allow_html=True)
        if not muni_list_data.empty:
            st.dataframe(
                muni_list_data.rename(columns={'Municipality_Code_DANE': 'Code', 'Municipality_Name_DANE': 'Name'}),
                hide_index=True, use_container_width=True, height=250
            )
        else:
            st.info("No municipalities found.")
