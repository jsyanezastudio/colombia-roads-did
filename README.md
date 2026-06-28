
# Colombia Roads DiD: Infrastructure and Municipal Impact

This repository contains the dataset and replication codes for an academic research project evaluating the impact of road infrastructure in Colombia using a **Difference-in-Differences (DiD)** econometric approach at the municipal level.

## Data Description

The repository includes the following initial geospatial and structured datasets required to construct the panel data:

* **`road_network_municipal_db.gpkg`**: A GeoPackage database containing the spatial network of Colombian roads snapped or aggregated at the municipal boundary level.
* Headers: NOMB_TRAMO, PROYECTO, GEN, ESTADO, COD_PR_IRE, ID_UF_IRE, AMB_TIPO, AMB_DESC, pre_date, start_date, oper_date, Department_Code_DANE, Department_Name_DANE, Municipality_Code_DANE, Municipality_Name_DANE, Entity_Code_DANE, Entity_Name_DANE, Type_DANE, Longitude_DANE, Latitude_DANE

* **`colombia_municipalities_codes.geojson`**: A geographic file (GeoJSON) containing the administrative boundaries of Colombian municipalities along with their official DANE (Departamento Administrativo Nacional de Estadística) identification codes.
* Headers: id, ADM0_CODE, ADM0_NAME, ADM1_CODE, ADM1_NAME, ADM2_CODE, ADM2_NAME, DISP_AREA, EXP2_YEAR, STATUS, STR2_YEAR, Shape_Area, Shape_Leng, Department_Code_DANE, Department_Name_DANE, Municipality_Code_DANE, Municipality_Name_DANE, Entity_Code_DANE, Entity_Name_DANE, Type_DANE, Longitude_DANE, Latitude_DANE

* **`roads_time_municipalities.json`**: A structured JSON dataset containing temporal data (e.g., travel times, construction phases, or year of intervention) calculated for each municipality.
* Headers: category_code, segment_code, start_post, start_distance, end_post, end_distance, route_name, sector, admin_entity_code, admin_group_code, surface_code, carriageway_code, route_id, data_source, global_id, segment_name, created_by, created_at, updated_by, updated_at, territory_code, status_code, category_type, surface_type, carriageway_type, admin_entity_name, admin_group_desc, status_desc, territory_name, road_width_m, Municipality_Code_DANE, ADM2_CODE, geometry
## Methodology Brief
The project utilizes these datasets to calculate accessibility shocks or infrastructure changes over time, mapping them to municipal-level outcomes to estimate causal effects through a DiD framework.
