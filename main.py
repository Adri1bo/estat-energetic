# -*- coding: utf-8 -*-
"""
Created on Wed Nov 27 14:05:55 2024

@author: above
"""

import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import plotly.express as px
import matplotlib.colors as mcolors
import geopandas as gpd
import folium
from streamlit_folium import st_folium
import numpy as np

st.set_page_config(layout="wide")

@st.cache_data
def carregar_geojson(path):
    return gpd.read_file(path)

@st.cache_data
def carregar_dades(path, sheet):
    return pd.read_excel(path, sheet_name=sheet)

def anys_complets(df):
    # Filtrar només consum final
    df_filtrat = df[df['Tipus energètic'] == 'Consum energia final']

    # Comptar per comarca, any i font
    comptats = (
        df_filtrat
        .groupby(['Comarca', 'Any'])['Font']
        .nunique()
        .reset_index(name='n_fonts')
    )
    
    # Seleccionar les files on hi ha exactament 3 fonts per comarca
    correctes = comptats[comptats['n_fonts'] == 3]

    # Comptar per any quantes comarques compleixen la condició
    comarques_per_any = (
        correctes.groupby('Any')['Comarca']
        .nunique()
        .reset_index(name='n_comarques_ok')
    )

    # Comptar quantes comarques hi ha en total
    total_comarques = df['Comarca'].nunique()

    # Retornar els anys on totes les comarques tenen 3 fonts
    anys_valids = comarques_per_any[
        comarques_per_any['n_comarques_ok'] == total_comarques
    ]['Any'].tolist()

    return anys_valids

def suma_nan_si_cal(df):
    return df if df.isnull().any() else df.sum()

def moda_mes_comuna(s):
    modes = s.mode()
    return modes.iloc[0] if not modes.empty else None

# Carregar les dades del fitxer Excel
excel_file = "bbdd.xlsx"
consum_electric = carregar_dades(excel_file, "consum_electric")
consum_termic = carregar_dades(excel_file, "consum_termic")
generacio_excedents = carregar_dades(excel_file, "generacio_electrica_excedents")
generacio_plantes = carregar_dades(excel_file, "generacio_electrica_plantes")
PROENCAT_demanda = carregar_dades(excel_file, "PROENCAT")

# ESPAI PER FER COMPROVACIONS DE DADES, QUE TOTES LES COMARQUES ESTIGUIN EN LA SEVA PROVÍNCIA...

#carregar dades geojson

geo_path_com = "geojson/comarques_simplificat.json"
geo_com = carregar_geojson(geo_path_com)


# Unir les taules de consum
total_consum = pd.concat([consum_electric, consum_termic])
total_generacio = pd.concat([generacio_excedents, generacio_plantes])

# Assegurar que les columnes de comarca i any coincideixen
total_consum["Comarca"] = total_consum["Comarca"].str.strip()
total_generacio["Comarca"] = total_generacio["Comarca"].str.strip()

# Unir les dades per comarca i any
macro_taula = pd.concat([total_consum, total_generacio, PROENCAT_demanda], ignore_index=True)
macro_taula['renovable'] = macro_taula['renovable'].fillna('Desconegut')
macro_taula = macro_taula.fillna(0)

macro_taula=macro_taula.groupby(['País','Comarca','Província','Tipus energètic','renovable','Font','Estat','Any']).agg({
    "Valor":"sum",
    "Unitats":moda_mes_comuna,
    "origen dades":moda_mes_comuna,
    "Potència instal·lada":"sum",
    "Unitats.1":moda_mes_comuna,
    "Superfície":"sum",
    "Unitats_sup":moda_mes_comuna
    }).reset_index()
macro_taula['Valor'] = macro_taula['Valor'].replace(0, np.nan)

# fem merges pels gràfics de mapa
macro_taula = macro_taula.merge(geo_com, left_on="Comarca", right_on="NOMCOMAR", how="left")


#taula agrupada per gràfics de mapa
taula_tipus_energetic_mare=macro_taula.groupby(['Comarca','Tipus energètic','renovable','Any']).agg({
    "Província":moda_mes_comuna,
    "Valor":"sum",
    "Unitats":moda_mes_comuna,
    "origen dades":moda_mes_comuna,
    "Potència instal·lada":"sum",
    "Unitats.1":moda_mes_comuna,
    "Superfície":"sum",
    "Unitats_sup":moda_mes_comuna,
    "geometry":moda_mes_comuna
    }).reset_index()

with st.popover("Configura filtres"):
    # Selecció de Províncies
    provincies = macro_taula["Província"].unique()
    provincies_seleccionades = st.multiselect("Selecciona Províncies:", provincies, default=provincies[0])
    
    # Selecció de comarques
    comarques = macro_taula["Comarca"].unique()
    comarques_seleccionades = st.multiselect("Selecciona comarques:", comarques, default=comarques[0])
    
    # Filtrar dades per comarca seleccionada
    # Selecció d'any
    anys = macro_taula["Any"].unique()
    anys = anys[anys != 0.0]
    any_seleccionat = st.slider("Selecciona l'any", min_value=min(anys), max_value=max(anys), step=1.0)
    # Selecció d'estats de les plantes
    estats_macro = macro_taula["Estat"].unique()
    estats = generacio_plantes["Estat"].unique()
    estats_seleccionats = st.multiselect("Selecciona els estats:", estats, default=estats)
    estats_seleccionats = list(set(estats_macro) - set(estats)) + estats_seleccionats
    renovables = st.toggle("Només generació amb renovables", value = True)
    if renovables:
        taula_tipus_energetic = taula_tipus_energetic_mare[taula_tipus_energetic_mare['renovable'] != 'No renovable']
    else:
        taula_tipus_energetic = taula_tipus_energetic_mare

# Calculem el balanç
# Primer: agrupem i calculem consum i generació per comarca i any
agrupat = taula_tipus_energetic.pivot_table(
    index=['Comarca','Província','Any',"geometry"],
    columns='Tipus energètic',
    values='Valor',
    aggfunc='sum'  # o 'mean' si vols mitjanes!
    ).reset_index()

# Calculem el balanç
agrupat['balanç'] = agrupat.get('Generació') - agrupat.get('Consum energia final')

# Convertim la columna de balanç en files i l'afegim a l'original
balanc_long = agrupat[['Comarca','Província','Any',"geometry", 'balanç']].copy()
balanc_long['Tipus energètic'] = 'balanç'
balanc_long = balanc_long.rename(columns={'balanç': 'Valor'})

# Ens quedem només amb les columnes com l'original
balanc_long = balanc_long[['Comarca','Província','Any',"geometry", 'Valor','Tipus energètic']]

# Finalment, concat amb la taula original
taula_tipus_energetic = pd.concat([taula_tipus_energetic, balanc_long], ignore_index=True)

# FILTRE TEMPORAL TARRAGONA
taula_tipus_energetic = taula_tipus_energetic[taula_tipus_energetic["Província"] == "Tarragona"]



# Crear el gràfic
st.title("Consums i Generació per Comarca")

# Agrupar dades per comarca, any i font
consum_agrupat = total_consum.groupby(["Comarca", "Any", "Font"]).sum(numeric_only=True).reset_index()
generacio_agrupat = total_generacio.groupby(["Comarca", "Any", "Font"]).sum(numeric_only=True).reset_index()



col1, col2 = st.columns([1,1])

with col1:
    tab1, tab2, tab3, tab4 = st.tabs(["Consum total", "Generació total", "Balanç energètic", "Altres indicadors"])
    
    with tab1:
        # --- Selecció del valor a mostrar ---
                
        taula_tipus_energetic_consum = taula_tipus_energetic[taula_tipus_energetic["Tipus energètic"] == "Consum energia final"]
        
        geo = gpd.GeoDataFrame(taula_tipus_energetic_consum, geometry="geometry", crs="EPSG:4326")
        geo = geo.set_index("Comarca")  # fer servir com a ID
    
        geo_filtrat = geo[geo["Any"].isin([any_seleccionat,0])]
        
        if geo_filtrat.empty:
            st.warning('Per aquest any no hi ha dades')
        else:
            fig1 = px.choropleth_mapbox(
                geo_filtrat,
                geojson=geo_filtrat.geometry,
                locations=geo_filtrat.index,
                color="Valor",
                color_continuous_scale="ylorrd",  # escala positiva
                range_color=[0, geo_filtrat['Valor'].max()],
                mapbox_style="carto-positron",
                zoom=6,
                center={"lat": 41.8, "lon": 1.5},
                height=500
            )
            fig1.update_layout(
                margin={"r":0,"t":0,"l":0,"b":0},
                coloraxis_colorbar=dict(title="Balanç (kWh)")
            )
            st.plotly_chart(fig1, use_container_width=False, key='consum')
    
    with tab2:
        # --- Selecció del valor a mostrar ---
        taula_tipus_energetic_generacio = taula_tipus_energetic[taula_tipus_energetic["Tipus energètic"] == "Generació"]
        taula_tipus_energetic_generacio = taula_tipus_energetic_generacio.groupby(['Comarca','Tipus energètic','Any']).agg({
            "Província":moda_mes_comuna,
            "Valor":"sum",
            "Unitats":moda_mes_comuna,
            "origen dades":moda_mes_comuna,
            "Potència instal·lada":"sum",
            "Unitats.1":moda_mes_comuna,
            "Superfície":"sum",
            "Unitats_sup":moda_mes_comuna,
            "geometry":moda_mes_comuna
            }).reset_index()
        geo = gpd.GeoDataFrame(taula_tipus_energetic_generacio, geometry="geometry", crs="EPSG:4326")
        geo = geo.set_index("Comarca")  # fer servir com a ID
    
        geo_filtrat = geo[geo["Any"].isin([any_seleccionat,0])]
        
        if geo_filtrat.empty:
            st.warning('Per aquest any no hi ha dades')
        else:
            fig2 = px.choropleth_mapbox(
                geo_filtrat,
                geojson=geo_filtrat.geometry,
                locations=geo_filtrat.index,
                color="Valor",
                color_continuous_scale="YlGnBu",  # escala positiva
                range_color=[0, geo_filtrat['Valor'].max()],
                mapbox_style="carto-positron",
                zoom=6,
                center={"lat": 41.8, "lon": 1.5},
                height=500
            )
            fig2.update_layout(
                margin={"r":0,"t":0,"l":0,"b":0},
                coloraxis_colorbar=dict(title="Balanç (kWh)")
            )
            st.plotly_chart(fig2, use_container_width=False, key='generacio')
    
    with tab3:
        # --- Selecció del valor a mostrar ---
        taula_tipus_energetic_balanc = taula_tipus_energetic[taula_tipus_energetic["Tipus energètic"] == "balanç"]
        
        geo = gpd.GeoDataFrame(taula_tipus_energetic_balanc, geometry="geometry", crs="EPSG:4326")
        geo = geo.set_index("Comarca")  # fer servir com a ID
    
        geo_filtrat = geo[geo["Any"].isin([any_seleccionat,0])]
        
        if geo_filtrat.empty:
            st.warning('Per aquest any no hi ha dades')
        else:
            max_abs = max(abs(geo_filtrat['Valor'].dropna()))
            fig3 = px.choropleth_mapbox(
                geo_filtrat,
                geojson=geo_filtrat.geometry,
                locations=geo_filtrat.index,
                color="Valor",  # pot ser 'balanç'
                color_continuous_scale="rdylgn",  # escala bipolar: vermell-blau
                mapbox_style="carto-positron",
                range_color=[-max_abs, max_abs],  # 
                center={"lat": 41.8, "lon": 1.5},
                zoom=6,
                height=500
            )
            fig3.update_layout(
                margin={"r":0,"t":0,"l":0,"b":0},
                coloraxis_colorbar=dict(title="Balanç (kWh)")
            )
            
            st.plotly_chart(fig3, use_container_width=False, key='balanc')
    
    with tab4:
        # --- Selecció del valor a mostrar ---
        valor = st.selectbox("Tria el valor a representar", macro_taula['Tipus energètic'].unique())
        macro_taula_filtre_map_1 = macro_taula[macro_taula["Tipus energètic"] == valor]
        valor2 = st.selectbox("Escull la font", macro_taula_filtre_map_1['Font'].unique())
        macro_taula_filtre_map_2 = macro_taula_filtre_map_1[macro_taula_filtre_map_1["Font"] == valor2]
        
        geo = gpd.GeoDataFrame(macro_taula_filtre_map_2, geometry="geometry", crs="EPSG:4326")
        geo = geo.set_index("Comarca")  # fer servir com a ID
    
        geo_filtrat = geo[geo["Any"].isin([any_seleccionat,0])]
        
        if geo_filtrat.empty:
            st.warning('Per aquest any no hi ha dades')
        else:
            fig4 = px.choropleth_mapbox(
                geo_filtrat,
                geojson=geo_filtrat.geometry,
                locations=geo_filtrat.index,
                color="Valor",
                color_continuous_scale="YlGnBu",  # escala positiva
                range_color=[0, geo_filtrat['Valor'].max()],
                mapbox_style="carto-positron",
                zoom=6,
                center={"lat": 41.7, "lon": 1.5},
                height=500
            )
            
            st.plotly_chart(fig4, use_container_width=False, key='altres')
            
            
with col2:
    # Filtrar dades per comarca i any seleccionats
    # Filtrar la macrotaula per comarca i any seleccionats
    # Filtrar dades per comarca i any seleccionats
    # Filtrar per renovables o no
    macro_taula_filtrada = macro_taula[
        ((macro_taula["Província"].isin(provincies_seleccionades)) |
        (macro_taula["Comarca"].isin(comarques_seleccionades))) &
        (macro_taula["Any"].isin([any_seleccionat,0])) & 
        (macro_taula["Estat"].isin(estats_seleccionats))
    ]
    if renovables:
        macro_taula_filtrada = macro_taula_filtrada[macro_taula_filtrada['renovable'] != 'No renovable']
    else:
        pass

    
    # Agrupar per Tipus energètic
    dades_agrupades = macro_taula_filtrada.groupby(
        ["Font", "Estat", "Tipus energètic"]
    )["Valor"].sum().unstack(fill_value=0)
    
    # Fer un join de "Font" i "Estat" per combinar els nivells d'índex
    dades_agrupades = dades_agrupades.T.reset_index()
    dades_agrupades.columns = ["_".join(col) for col in dades_agrupades.columns]
    
    #treiem la fila d'energia final 2023 proencat que ja tenim de dades reals i li afegim el barret de les renovables tèrmiques
    dades_agrupades.loc[dades_agrupades['Tipus energètic_'] == 'Consum energia final', 'Renovables ús tèrmic_Prospectiu'] = dades_agrupades.loc[dades_agrupades['Tipus energètic_'] == 'Consum energia final 2023', 'Renovables ús tèrmic_Prospectiu'].iloc[0]
    #dades_agrupades = dades_agrupades[dades_agrupades['Tipus energètic_'] != 'Consum energia final 2023']
    
    
    # Transformació a format llarg
    dades_long = dades_agrupades.melt(
        id_vars=["Tipus energètic_"],
        var_name="Font_Estat",
        value_name="Valor"
    )
    # Arrodonir els valors a 2 decimals
    dades_long["Valor"] = dades_long["Valor"].round(0)
    
    #ordenar alfabeticament
    dades_long = dades_long.sort_values(by='Font_Estat')

    
    # Definir un esquema de colors personalitzat
    color_map = {}
    default_colors = list(mcolors.TABLEAU_COLORS.values())  # Colors predeterminats
    fossil_colors = ["#2E2E2E", "#585858", "#7F7F7F"]  # Tonalitats negres
    eolic_colors = ["#006400", "#228B22", "#32CD32", "#7CFC00", "#ADFF2F"]  # Colors verds
    solar_colors = ["#FF4500", "#FF6347", "#FF7F50", "#FFA07A", "#FFDAB9"]  # Colors taronges
    electric_colors = ["#1f77b4", "#6baed6", "#9ecae1", "#c6dbef"]  # Tonalitats blaves
    
    # Classificar colors basats en paraules clau
    for index, categoria in enumerate(dades_long["Font_Estat"].unique()):
        if "fòssil" in categoria or "Gas" in categoria or "petr" in categoria:
            color_map[categoria] = fossil_colors[index % len(fossil_colors)]
        elif "enov" in categoria or "Eòl" in categoria:
            color_map[categoria] = eolic_colors[index % len(eolic_colors)]
        elif "otov" in categoria:
            color_map[categoria] = solar_colors[index % len(solar_colors)]
        elif "tric" in categoria:
            color_map[categoria] = electric_colors[index % len(electric_colors)]
        else:
            color_map[categoria] = default_colors[index % len(default_colors)]
    
    # Crear el gràfic interactiu amb colors personalitzats
    fig = px.bar(
        dades_long,
        x="Tipus energètic_",
        y="Valor",
        color="Font_Estat",
        text="Valor",
        title=f"Consum i Generació a {provincies_seleccionades}, {comarques_seleccionades} ({any_seleccionat})",
        labels={"Valor": "Energia (MWh)", "Tipus energètic_": "Tipus Energètic"},
        height=700,  # Augmentar l'alçada del gràfic
        color_discrete_map=color_map  # Assignar colors personalitzats
    )
    
    # Configurar opcions de disseny
    fig.update_layout(
        barmode="stack",  # Barres apilades
        legend_title="Font i estat",
        xaxis_title="Tipus energètic_",
        yaxis_title="Energia (MWh)",
        legend=dict(x=1.05, y=1)  # Moure llegenda fora del gràfic
    )
    
    # Mostrar el gràfic interactiu
    st.plotly_chart(fig)
    

