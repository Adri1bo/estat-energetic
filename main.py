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

st.set_page_config(layout="wide")

# Carregar les dades del fitxer Excel
excel_file = "bbdd.xlsx"
consum_electric = pd.read_excel(excel_file, sheet_name="consum_electric")
consum_termic = pd.read_excel(excel_file, sheet_name="consum_termic")
generacio_excedents = pd.read_excel(excel_file, sheet_name="generacio_electrica_excedents")
generacio_plantes = pd.read_excel(excel_file, sheet_name="generacio_electrica_plantes")
PROENCAT_demanda = pd.read_excel(excel_file, sheet_name="PROENCAT")

# Unir les taules de consum
total_consum = pd.concat([consum_electric, consum_termic])
total_generacio = pd.concat([generacio_excedents, generacio_plantes])

# Assegurar que les columnes de comarca i any coincideixen
total_consum["Comarca"] = total_consum["Comarca"].str.strip()
total_generacio["Comarca"] = total_generacio["Comarca"].str.strip()

# Unir les dades per comarca i any
macro_taula = pd.concat([total_consum, total_generacio, PROENCAT_demanda], ignore_index=True)
macro_taula.fillna(0, inplace=True)


# Crear el gràfic
st.title("Consums i Generació per Comarca")

# Agrupar dades per comarca, any i font
consum_agrupat = total_consum.groupby(["Comarca", "Any", "Font"]).sum(numeric_only=True).reset_index()
generacio_agrupat = total_generacio.groupby(["Comarca", "Any", "Font"]).sum(numeric_only=True).reset_index()

col1, col2 = st.columns([1,2])

with col1:
    # Selecció de Províncies
    provincies = macro_taula["Província"].unique()
    provincies_seleccionades = st.multiselect("Selecciona Províncies:", provincies, default=provincies[0])
    
    # Selecció de comarques
    comarques = macro_taula["Comarca"].unique()
    comarques_seleccionades = st.multiselect("Selecciona comarques:", comarques, default=comarques[0])
    
    # Filtrar dades per comarca seleccionada
    # Selecció d'any
    anys = macro_taula["Any"].unique()
    any_seleccionat = st.selectbox("Selecciona un any:", sorted(anys))
    
    # Selecció d'estats de les plantes
    estats_macro = macro_taula["Estat"].unique()
    estats = generacio_plantes["Estat"].unique()
    estats_seleccionats = st.multiselect("Selecciona els estats:", estats, default=estats)
    estats_seleccionats = list(set(estats_macro) - set(estats)) + estats_seleccionats

with col2:
    # Filtrar dades per comarca i any seleccionats
    # Filtrar la macrotaula per comarca i any seleccionats
    # Filtrar dades per comarca i any seleccionats
    
    macro_taula_filtrada = macro_taula[
        ((macro_taula["Província"].isin(provincies_seleccionades)) |
        (macro_taula["Comarca"].isin(comarques_seleccionades))) &
        (macro_taula["Any"].isin([any_seleccionat,0])) & 
        (macro_taula["Estat"].isin(estats_seleccionats))
    ]
    
    # Agrupar per Tipus energètic
    dades_agrupades = macro_taula_filtrada.groupby(
        ["Font", "Estat", "Tipus energètic"]
    )["Valor"].sum().unstack(fill_value=0)
    # Fer un join de "Font" i "Estat" per combinar els nivells d'índex
    dades_agrupades = dades_agrupades.T.reset_index()
    dades_agrupades.columns = ["_".join(col) for col in dades_agrupades.columns]
    
    
    # Transformació a format llarg
    dades_long = dades_agrupades.melt(
        id_vars=["Tipus energètic_"],
        var_name="Font_Estat",
        value_name="Valor"
    )
    # Arrodonir els valors a 2 decimals
    dades_long["Valor"] = dades_long["Valor"].round(0)
    
    
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
        height=800,  # Augmentar l'alçada del gràfic
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
    
    """
    # Agrupar per Tipus energètic
    dades_agrupades = macro_taula_filtrada.groupby(
        ["Font","Estat","Tipus energètic"]
    )["Valor"].sum().unstack(fill_value=0)
    dades_agrupades=dades_agrupades.T
    
    # Crear el gràfic
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Dibuixar barres apilades per tipus energètic
    dades_agrupades.plot(
        kind="bar",
        stacked=True,
        ax=ax,
        colormap="tab10"
    )
    
    # Configurar el gràfic
    ax.set_title(f"Consum i Generació a {comarques_seleccionades} ({any_seleccionat})")
    ax.set_xlabel("Tipus energètic")
    ax.set_ylabel("Energia (MWh)")
    ax.legend(title="Tipus", bbox_to_anchor=(1.05, 1), loc="upper left")
    
    # Mostrar el gràfic
    st.pyplot(fig)
"""