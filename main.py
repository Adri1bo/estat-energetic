# -*- coding: utf-8 -*-
"""
Created on Wed Nov 27 14:05:55 2024

@author: above
"""

import pandas as pd
import streamlit as st
import plotly.express as px
import matplotlib.colors as mcolors
import geopandas as gpd
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

def preparar_dades_si(df, columna_valor='valor', base_unit='Wh', decimals=2):
    """
    Converteix una columna numèrica a una escala SI coherent per visualització.
    
    Parameters:
        df (pd.DataFrame): DataFrame original
        columna_valor (str): nom de la columna amb els valors numèrics (ex: 'valor')
        base_unit (str): unitat original (ex: 'Wh', 'W', etc.)
        decimals (int): decimals a mostrar

    Returns:
        df (pd.DataFrame): amb columnes 'valor_si' i 'unitat_si'
    """
    escales_si = {
        0: '',
        1: 'k',
        2: 'M',
        3: 'G',
        4: 'T',
        5: 'P'
    }

    # Filtra valors positius per calcular logaritme
    valors = df[columna_valor].replace(0, np.nan).dropna().abs()
    if valors.empty:
        ordre = 0
    else:
        log10_mean = np.log10(valors.mean())
        ordre = min(max(int(log10_mean // 3), 0), max(escales_si.keys()))

    factor = 10 ** (ordre * 3)
    prefix_si = escales_si[ordre]

    # Crea nova columna amb valor convertit i unitat nova
    df = df.copy()
    df['valor_si'] = df[columna_valor] / factor
    df['unitat_si'] = prefix_si + base_unit

    # Opcional: arrodonim (per si vols mostrar valors)
    df['valor_si'] = df['valor_si'].round(decimals)

    return df

def grafic_mapa(df,tema,nombres='enters',colors="YlGnBu"):
    if nombres == 'enters':
        range_color=[0, df['valor_si'].abs().max()]
    elif nombres =='reals':
        range_color=[-df['valor_si'].abs().max(), df['valor_si'].abs().max()]
        
    fig1 = px.choropleth_mapbox(
        df,
        geojson=df.geometry,
        locations=df.index,
        color="valor_si",
        color_continuous_scale=colors,  # escala positiva
        range_color=range_color,
        hover_name='Comarca',
        custom_data=['valor_si', 'unitat_si'],
        mapbox_style="carto-positron",
        zoom=6,
        center={"lat": 41.8, "lon": 1.5},
        height=500
    )
    fig1.update_layout(
        margin={"r":0,"t":0,"l":0,"b":0},
        coloraxis_colorbar=dict(title="Consum (MWh)"),
        yaxis_title="Consum (Wh)",
        hoverlabel=dict(
            font_size=18,
            font_family="Arial"
        )
    )
    # Indiquem quines columnes volem passar al hover mitjançant customdata
    fig1.update_traces(
        hovertemplate=f"%{{hovertext}}<br>{tema}: %{{customdata[0]:.2f}} %{{customdata[1]}}<extra></extra>"
    )
    
    fig1.update_coloraxes(
        colorbar_title=df['unitat_si'].iloc[0]
    )
    
    return fig1

def grafic_barres(df, tema, nombres='enters', colors="YlGnBu"):
    if nombres == 'enters':
        range_color = [0, df['valor_si'].abs().max()]
    elif nombres == 'reals':
        range_color = [-df['valor_si'].abs().max(), df['valor_si'].abs().max()]
    
    # Crear un gràfic de barres en lloc d'un mapa
    fig = px.bar(
        df,
        x='Comarca',  # Assumeix que tens una columna amb noms de comarca
        y='valor_si',
        color='valor_si',
        color_continuous_scale=colors,
        custom_data=['valor_si', 'unitat_si'],
        range_color=range_color,
        labels={'valor_si': 'Consum (Wh)', 'Comarca': 'Comarca'},
        hover_data=['valor_si', 'unitat_si'],
        hover_name='Comarca',
    )

    fig.update_layout(
        margin={"r":0,"t":0,"l":0,"b":0},
        coloraxis_colorbar=dict(title="Consum (MWh)"),
        hoverlabel=dict(
            font_size=18,
            font_family="Arial"
        ),
        yaxis_title="Energia "+df['unitat_si'].iloc[0],
    )
    # Indiquem quines columnes volem passar al hover mitjançant customdata
    fig.update_traces(
        hovertemplate="%{x}: %{customdata[0]:.2f} %{customdata[1]}<extra></extra>"
    )

    fig.update_coloraxes(
        colorbar_title=df['unitat_si'].iloc[0]
    )

    return fig

st.title("Visor dades de la transició energètica")

# Carregar les dades del fitxer Excel
excel_file = "bbdd.xlsx"
consum_electric = carregar_dades(excel_file, "consum_electric")
consum_termic = carregar_dades(excel_file, "consum_termic")
generacio_excedents = carregar_dades(excel_file, "generacio_electrica_excedents")
generacio_plantes = carregar_dades(excel_file, "generacio_electrica_plantes")
PROENCAT_demanda = carregar_dades(excel_file, "PROENCAT")
generacio_potencial = carregar_dades(excel_file, "Potencial")

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
macro_taula = pd.concat([total_consum, total_generacio, PROENCAT_demanda,generacio_potencial], ignore_index=True)
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
    provincies_seleccionades = list(st.segmented_control("Selecciona Províncies:", provincies, default=provincies[0],selection_mode="multi"))
    
    # Selecció de comarques
    comarques = macro_taula["Comarca"].unique()
    comarques_seleccionades = st.multiselect("Selecciona comarques:", comarques, default=None)
    
    # Filtrar dades per comarca seleccionada
    # Selecció d'any
    anys = macro_taula["Any"].unique()
    anys = anys[anys != 0.0]
    any_seleccionat = st.slider("Selecciona l'any", min_value=min(anys), max_value=max(anys), step=1.0, value = 2023.0)
    # Selecció d'estats de les plantes
    estats_macro = macro_taula["Estat"].unique()
    estats = generacio_plantes["Estat"].unique()
    estats_seleccionats = st.pills("Selecciona els estats:", estats, default=estats, selection_mode="multi")
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
#taula_tipus_energetic = taula_tipus_energetic[taula_tipus_energetic["Província"] == "Tarragona"]



# Crear el gràfic


# Agrupar dades per comarca, any i font
#consum_agrupat = total_consum.groupby(["Comarca", "Any", "Font"]).sum(numeric_only=True).reset_index()
#generacio_agrupat = total_generacio.groupby(["Comarca", "Any", "Font"]).sum(numeric_only=True).reset_index()



col1, col2 = st.columns([1,1])

with col1:
    tab1, tab2, tab3, tab4 = st.tabs(["Consum total", "Generació total", "Balanç energètic", "Altres indicadors"])
    
    with tab1:
        # --- Selecció del valor a mostrar ---
                
        taula_tipus_energetic_consum = taula_tipus_energetic[taula_tipus_energetic["Tipus energètic"] == "Consum energia final"]
        
        geo = gpd.GeoDataFrame(taula_tipus_energetic_consum, geometry="geometry", crs="EPSG:4326")
        #geo = geo.set_index("Comarca")  # fer servir com a ID
    
        geo_filtrat = geo[geo["Any"].isin([any_seleccionat,0])]
        geo_filtrat= preparar_dades_si(geo_filtrat, columna_valor='Valor', base_unit='Wh', decimals=2)
        
        if geo_filtrat.empty:
            st.warning('Per aquest any no hi ha dades')
        else:
            # Crear una selecció per triar el tipus de gràfic
            opcio_grafic = st.pills("Selecciona el tipus de gràfic:",('Mapa', 'Gràfic de barres'), default = 'Mapa',key='pill1')
        
            if opcio_grafic == 'Mapa':
                fig1 = grafic_mapa(geo_filtrat, tema='Consum', colors="ylorrd")
                st.plotly_chart(fig1, use_container_width=True, key='consum')
            elif opcio_grafic == 'Gràfic de barres':
                fig = grafic_barres(geo_filtrat, tema='Consum', colors="ylorrd")
                st.plotly_chart(fig, use_container_width=True, key='consumbarres')
    
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
        #geo = geo.set_index("Comarca")  # fer servir com a ID
    
        geo_filtrat = geo[geo["Any"].isin([any_seleccionat,0])]
        geo_filtrat= preparar_dades_si(geo_filtrat, columna_valor='Valor', base_unit='Wh', decimals=2)
        
        if geo_filtrat.empty:
            st.warning('Per aquest any no hi ha dades')
        else:
            # Crear una selecció per triar el tipus de gràfic
            opcio_grafic = st.pills("Selecciona el tipus de gràfic:",('Mapa', 'Gràfic de barres'), default = 'Mapa',key='pill2')
        
            if opcio_grafic == 'Mapa':
                fig2 = grafic_mapa(geo_filtrat,tema = 'Generació',colors="YlGnBu")
                st.plotly_chart(fig2, use_container_width=False, key='generacio')
            elif opcio_grafic == 'Gràfic de barres':
                fig = grafic_barres(geo_filtrat,tema = 'Generació',colors="YlGnBu")
                st.plotly_chart(fig, use_container_width=True, key='generaciobarres')
    
    with tab3:
        # --- Selecció del valor a mostrar ---
        taula_tipus_energetic_balanc = taula_tipus_energetic[taula_tipus_energetic["Tipus energètic"] == "balanç"]
        
        geo = gpd.GeoDataFrame(taula_tipus_energetic_balanc, geometry="geometry", crs="EPSG:4326")
        #geo = geo.set_index("Comarca")  # fer servir com a ID
    
        geo_filtrat = geo[geo["Any"].isin([any_seleccionat,0])]
        geo_filtrat= preparar_dades_si(geo_filtrat, columna_valor='Valor', base_unit='Wh', decimals=2)
        
        if geo_filtrat.empty:
            st.warning('Per aquest any no hi ha dades')
        else:            
            # Crear una selecció per triar el tipus de gràfic
            opcio_grafic = st.pills("Selecciona el tipus de gràfic:",('Mapa', 'Gràfic de barres'), default = 'Mapa',key='pill3')
        
            if opcio_grafic == 'Mapa':
                fig3 = grafic_mapa(geo_filtrat,tema = 'Balanç',nombres='reals', colors="rdylgn")
                st.plotly_chart(fig3, use_container_width=False, key='balanc')
            elif opcio_grafic == 'Gràfic de barres':
                fig = grafic_barres(geo_filtrat,tema = 'Balanç',nombres='reals', colors="rdylgn")
                st.plotly_chart(fig, use_container_width=True, key='balancbarres')
    
    with tab4:
        # --- Selecció del valor a mostrar ---
        valor = st.selectbox("Tria el valor a representar", macro_taula['Tipus energètic'].unique())
        macro_taula_filtre_map_1 = macro_taula[macro_taula["Tipus energètic"] == valor]
        valor2 = [st.segmented_control("Escull la font", macro_taula_filtre_map_1['Font'].unique(),
                                      default=macro_taula_filtre_map_1['Font'].unique()[0],selection_mode = "single")]
        macro_taula_filtre_map_2 = macro_taula_filtre_map_1[macro_taula_filtre_map_1["Font"].isin(valor2)]
        
        geo = gpd.GeoDataFrame(macro_taula_filtre_map_2, geometry="geometry", crs="EPSG:4326")
        #geo = geo.set_index("Comarca")  # fer servir com a ID
    
        geo_filtrat = geo[geo["Any"].isin([any_seleccionat,0])]
        geo_filtrat= preparar_dades_si(geo_filtrat, columna_valor='Valor', base_unit='Wh', decimals=2)
        if geo_filtrat.empty:
            st.warning('Per aquest any no hi ha dades')
        else:
            # Crear una selecció per triar el tipus de gràfic
            opcio_grafic = st.pills("Selecciona el tipus de gràfic:",('Mapa', 'Gràfic de barres'), default = 'Mapa',key='pill4')
        
            if opcio_grafic == 'Mapa':
                fig4 = grafic_mapa(geo_filtrat,tema = 'Balanç',nombres='reals', colors="rdylgn")
                st.plotly_chart(fig4, use_container_width=False, key='altres')
            elif opcio_grafic == 'Gràfic de barres':
                fig = grafic_barres(geo_filtrat,tema = 'Balanç',nombres='reals', colors="rdylgn")
                st.plotly_chart(fig, use_container_width=True, key='altresbarres')
            st.markdown("per alguns ítems només hi ha dades de la província de Tarragona")   
            
with col2:
    # Filtrar dades per comarca i any seleccionats
    # Filtrar la macrotaula per comarca i any seleccionats
    # Filtrar dades per comarca i any seleccionats
    # Filtrar per renovables o no
    macro_taula_filtrada_wo_any = macro_taula[
        ((macro_taula["Província"].isin(provincies_seleccionades)) |
        (macro_taula["Comarca"].isin(comarques_seleccionades))) &
        (macro_taula["Estat"].isin(estats_seleccionats))
    ]
    if renovables:
        macro_taula_filtrada_wo_any = macro_taula_filtrada_wo_any[macro_taula_filtrada_wo_any['renovable'] != 'No renovable']
    else:
        pass
    
    macro_taula_filtrada = macro_taula_filtrada_wo_any[(macro_taula_filtrada_wo_any["Any"].isin([any_seleccionat,0]))]

    
    # Agrupar per Tipus energètic
    dades_agrupades = macro_taula_filtrada.groupby(
        ["Font", "Estat", "Tipus energètic"]
    )["Valor"].sum().unstack(fill_value=0)
    
    # Fer un join de "Font" i "Estat" per combinar els nivells d'índex
    dades_agrupades = dades_agrupades.T.reset_index()
    dades_agrupades.columns = ["_".join(col) for col in dades_agrupades.columns]
    
    #treiem la fila d'energia final 2023 proencat que ja tenim de dades reals i li afegim el barret de les renovables tèrmiques
    dades_agrupades.loc[dades_agrupades['Tipus energètic_'] == 'Consum energia final', 'Renovables ús tèrmic_Prospectiu'] = dades_agrupades.loc[dades_agrupades['Tipus energètic_'] == 'Consum energia final 2023', 'Renovables ús tèrmic_Prospectiu'].iloc[0]
    dades_agrupades = dades_agrupades[dades_agrupades['Tipus energètic_'] != 'Consum energia final 2023']
    
    
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
    dades_long= preparar_dades_si(dades_long, columna_valor='Valor', base_unit='Wh', decimals=2)
    
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
        y="valor_si",
        color="Font_Estat",
        custom_data=['unitat_si'],
        text="valor_si",
        title=f"Consum i Generació a {provincies_seleccionades}, {comarques_seleccionades} ({any_seleccionat})",
        height=700,  # Augmentar l'alçada del gràfic
        color_discrete_map=color_map  # Assignar colors personalitzats
    )
    
    # Configurar opcions de disseny
    fig.update_layout(
        barmode="stack",  # Barres apilades
        legend_title="Font i estat",
        xaxis_title="Tipus energètic",
        yaxis_title="Energia "+dades_long['unitat_si'][0],
        legend=dict(x=1.05, y=1),  # Moure llegenda fora del gràfic
        hoverlabel=dict(
            font_size=18,
            font_family="Arial"
        )
    )
    
    # Indiquem quines columnes volem passar al hover mitjançant customdata
    fig.update_traces(
        texttemplate="%{y:.2f} ",
        textposition="auto",
        textfont=dict(size=16),
        hovertemplate = "%{x}<br>%{fullData.name}: %{y:.2f} %{customdata[0]}<extra></extra>"
    )
    
    # Mostrar el gràfic interactiu
    st.plotly_chart(fig)
    

col1, col3, col4, col5 = st.columns(4)

pot_autoconsum = macro_taula_filtrada_wo_any[macro_taula_filtrada_wo_any['Font'] == 'Excedents autoconsum fotovoltaic'].filter(
    items=['Any','Potència instal·lada']).groupby('Any').sum('Potència instal·lada')
pot_autoconsum= preparar_dades_si(pot_autoconsum, columna_valor='Potència instal·lada', base_unit='W', decimals=2)

potencial_cobertes = macro_taula_filtrada_wo_any[macro_taula_filtrada_wo_any['Font'] == 'autoconsum fotovoltaic cobertes'].filter(
    items=['Any','Potència instal·lada']).groupby('Any').sum('Potència instal·lada')
potencial_cobertes= preparar_dades_si(potencial_cobertes, columna_valor='Potència instal·lada', base_unit='W', decimals=2)

pot_FV = macro_taula_filtrada_wo_any[macro_taula_filtrada_wo_any['Font'] == 'Fotovoltaica'].filter(
    items=['Any','Potència instal·lada']).groupby('Any').sum('Potència instal·lada')
pot_FV= preparar_dades_si(pot_FV, columna_valor='Potència instal·lada', base_unit='W', decimals=2)

pot_eolica = macro_taula_filtrada_wo_any[macro_taula_filtrada_wo_any['Font'] == 'Eòlica'].filter(
    items=['Any','Potència instal·lada']).groupby('Any').sum('Potència instal·lada')
pot_eolica= preparar_dades_si(pot_eolica, columna_valor='Potència instal·lada', base_unit='W', decimals=2)

pot_hidr = macro_taula_filtrada_wo_any[macro_taula_filtrada_wo_any['Font'] == 'Hidràulica'].filter(
    items=['Any','Potència instal·lada']).groupby('Any').sum('Potència instal·lada')
pot_hidr= preparar_dades_si(pot_hidr, columna_valor='Potència instal·lada', base_unit='W', decimals=2)

pot_nuclear = macro_taula_filtrada_wo_any[macro_taula_filtrada_wo_any['Font'] == 'Nuclear'].filter(
    items=['Any','Potència instal·lada']).groupby('Any').sum('Potència instal·lada')
pot_nuclear= preparar_dades_si(pot_nuclear, columna_valor='Potència instal·lada', base_unit='W', decimals=2)

pot_cogeneracio = macro_taula_filtrada_wo_any[macro_taula_filtrada_wo_any['Font'] == 'Cogeneració'].filter(
    items=['Any','Potència instal·lada']).groupby('Any').sum('Potència instal·lada')
pot_cogeneracio= preparar_dades_si(pot_cogeneracio, columna_valor='Potència instal·lada', base_unit='W', decimals=2)

col1.metric("Potència autoconsum 2023", str(pot_autoconsum.loc[2023]['valor_si'])+' '+pot_autoconsum.loc[2023]['unitat_si'], 
            str(round(pot_autoconsum.loc[2023]['valor_si']-pot_autoconsum.loc[2022]['valor_si'],1))+' '+pot_autoconsum.loc[2023]['unitat_si'], 
            border=True)
#col2.metric("Potencial autoconsum", str(potencial_cobertes.loc[0]['valor_si'])+' '+potencial_cobertes.loc[0]['unitat_si'], border=True)
try: #en cas de que no tingui dades que aparegui la mètrica com a 0
    pot_FV_metric_value = pot_FV.loc[2023]['valor_si']
    pot_FV_metric_unitat = pot_FV.loc[2023]['unitat_si']
except:
    pot_FV_metric_value = 0
    pot_FV_metric_unitat='W'

col3.metric("Potència fotovoltaica", str(pot_FV_metric_value)+' '+pot_FV_metric_unitat, 
            #str(pot_FV.loc[2023]['valor_si']-pot_FV.loc[2022]['valor_si'])+' '+pot_FV.loc[2023]['unitat_si'],
            border=True)

try: #en cas de que no tingui dades que aparegui la mètrica com a 0
    pot_eolic_metric_value = pot_eolica.loc[2023]['valor_si']
    pot_eolic_metric_unitat = pot_eolica.loc[2023]['unitat_si']
except:
    pot_eolic_metric_value = 0
    pot_eolic_metric_unitat='W'
    
col4.metric("Potència eòlica", str(pot_eolic_metric_value)+' '+pot_eolic_metric_unitat, 
            #str(pot_eolica.loc[2023]['valor_si']-pot_eolica.loc[2022]['valor_si'])+' '+pot_eolica.loc[2023]['unitat_si'],
            border=True)

try: #en cas de que no tingui dades que aparegui la mètrica com a 0
    pot_hidr_metric_value = pot_hidr.loc[2023]['valor_si']
    pot_hidr_metric_unitat = pot_hidr.loc[2023]['unitat_si']
except:
    pot_hidr_metric_value = 0
    pot_hidr_metric_unitat='W'
    
col5.metric("Potència hidràulica", str(pot_hidr_metric_value)+' '+pot_hidr_metric_unitat, 
            #str(pot_eolica.loc[2023]['valor_si']-pot_eolica.loc[2022]['valor_si'])+' '+pot_eolica.loc[2023]['unitat_si'],
            border=True)

try: #en cas de que no tingui dades que aparegui la mètrica com a 0
    pot_nuclear_metric_value = pot_nuclear.loc[2023]['valor_si']
    pot_nuclear_metric_unitat = pot_nuclear.loc[2023]['unitat_si']
except:
    pot_nuclear_metric_value = 0
    pot_nuclear_metric_unitat='W'
    
col1.metric("Potència nuclear", str(pot_nuclear_metric_value)+' '+pot_nuclear_metric_unitat, 
            #str(pot_eolica.loc[2023]['valor_si']-pot_eolica.loc[2022]['valor_si'])+' '+pot_eolica.loc[2023]['unitat_si'],
            border=True)

try: #en cas de que no tingui dades que aparegui la mètrica com a 0
    pot_cogeneracio_metric_value = pot_cogeneracio.loc[2023]['valor_si']
    pot_cogeneracio_metric_unitat = pot_cogeneracio.loc[2023]['unitat_si']
except:
    pot_cogeneracio_metric_value = 0
    pot_cogeneracio_metric_unitat='W'
    
col3.metric("Potència cogeneració", str(pot_cogeneracio_metric_value)+' '+pot_cogeneracio_metric_unitat, 
            #str(pot_eolica.loc[2023]['valor_si']-pot_eolica.loc[2022]['valor_si'])+' '+pot_eolica.loc[2023]['unitat_si'],
            border=True)

st.markdown("Fonts:")
st.markdown('''Datadis  
            1. Dades obertes de Catalunya  
            2. Consum provincials de productes petrolífers de la CNMC  
            3. Registre d'Autoconsum de Catalunya  
            4. Registre RAIPRE (PRETOR)  
            5. Ponència d'energies renovables   
            6. DGT parc automobilistic  
            7. ROMA vehicles agrícoles  
            8. IDESCAT embarcacions, captures, cens habitatges, població  
            9. Protecció civil i altres cerques per dades dels aeroports  
            10. Determinació del potencial d'autoabastiment elèctric dels municipis de la demarcació de Tarragona a partir d'energia fotovoltaica i eòlica. Conveni marc DIPTA-URV 2020-2023. Codi Oficial: URV.FC03.01.00 (2021/ 09)
              
            Visor desenvolupat per les Oficines Comarcals de Transició Energètica del Baix Ebre (Gemma) i l'Alt Camp (Adrià)
            © 2025''')