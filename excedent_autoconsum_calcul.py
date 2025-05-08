# -*- coding: utf-8 -*-
"""
Created on Tue Apr 22 11:05:18 2025

@author: above
"""

import pandas as pd
from datetime import datetime

#paràmetres
# el repartiment es realitza en funció de la potència instal·lada, però els factors de capacitat 
#de cada tecnologia difereixen, per això es defineixen usn factors de capacitat basats en la informació extreta de ree pel 2023
#https://www.ree.es/es/datos/balance/balance-electrico
#https://www.ree.es/es/datos/generacion/potencia-instalada

potencia = {'HIDROELECTRICA':17097, 
             'COGENERACIO':5611, 
             'RESIDUS':170, 
             'BIOGÀS':1108/2, # EXTRET DE LA SECCIÓ 'OTRAS RENOVABLES' 50%
             'FOTOVOLTAICA':26351, 
             'ENERGIES RESIDUALS':1108/2, # EXTRET DE LA SECCIÓ 'OTRAS RENOVABLES' 50%
             'EÒLICA':30842}

generacio = {'HIDROELECTRICA':25761, 
             'COGENERACIO':17293, 
             'RESIDUS':707, 
             'BIOGÀS':3587/2, # EXTRET DE LA SECCIÓ 'OTRAS RENOVABLES' 50%
             'FOTOVOLTAICA':36717, 
             'ENERGIES RESIDUALS':3587/2, # EXTRET DE LA SECCIÓ 'OTRAS RENOVABLES' 50%
             'EÒLICA':61344}

#els factors de capacitat s'eleven a un factor y per amplair diferències excedentaries entre tecnologies
#i evitar desajustos en els que un poble de diferents provincies amb la mateixa potencia FV tenen excedents 5 vegades superiors
factors_capacitat = {x:(generacio[x]/potencia[x]/8.760)**1.5 for x in potencia}


def get_year(I_DAT_INSCRIP_RAC):
    return I_DAT_INSCRIP_RAC.year

def calcul_pot_capacitat(I_KW_TOT, I_TECNOLOGIA, factors_capacitat):
    return I_KW_TOT*factors_capacitat[I_TECNOLOGIA]

def get_province(I_INE_MUNICIPI):
    I_INE_MUNICIPI = str(I_INE_MUNICIPI)
    if I_INE_MUNICIPI.startswith("8"):
        province = 'Barcelona'
    elif I_INE_MUNICIPI.startswith("25"):
        province = 'Lleida'
    elif I_INE_MUNICIPI.startswith("43"):
        province = 'Tarragona'
    elif I_INE_MUNICIPI.startswith("17"):
        province = 'Girona'
    else:
        province = 'Desconeguda'
    return province
    
#importem dades d'excedents
excedents = pd.DataFrame([])
anys = range(2022,datetime.now().year)

for year in anys:
    try:
        df = pd.read_csv('raw data/Catalunya autoconsum '+str(year)+'.csv')
        #escurcem la informació
        df = df.loc[df["selfConsumption"] !='Sin Excedentes Individual']
        df = df.groupby(['dataYear','province','selfConsumption']).agg({'sumPower' : 'first',
                                                                  'sumContracts' : 'first',
                                                                  'sumEnergy' : 'sum'}).reset_index()
        df = df.groupby(['dataYear','province']).agg({'sumPower' : 'sum',
                                                      'sumContracts' : 'sum',
                                                      'sumEnergy' : 'sum'}).reset_index()
        #concatenem dades
        excedents = pd.concat([excedents, df], ignore_index=True)
        
    except:
        pass


#importem dades del RAC i netegem els que no tenen excedents i agrupem per anys, municipis i tecnologia
RAC = pd.read_excel('RAC.xlsx')
RAC = RAC.dropna(subset=['S-SUBSECCIO-REGISTRE'])
RAC['ANY'] = RAC['I_DAT_INSCRIP_RAC'].apply(get_year)
RAC = RAC.groupby(['ANY', 'I_TECNOLOGIA', 'I_MUNICIPI', 'I_COMARCA']).agg({'I_KW_TOT':'sum','I_INE_MUNICIPI':'first'}).reset_index()
RAC['province'] = RAC['I_INE_MUNICIPI'].apply(get_province)

# apliquem els factors de capacitat per obtenir una nova potencia calculada que ens permetrà fer millor el repartiment
RAC['POT_CAPACITAT'] = RAC.apply(lambda x: calcul_pot_capacitat(x.I_KW_TOT, x.I_TECNOLOGIA,factors_capacitat), axis=1)

#volem obtenir per cada any de dades d'excedents que tenim la generació distribuida en municipis, 
#Per fer això fem un bucle for per cada any, filtrem el RAC de l'any en qüestió cap avall i sumem la potència total capacitat
#creem un DATAFRAME en cada iteració i finalment els unic i agrupem per obtenir ara sí la ifnormació que voliem
resultat = pd.DataFrame([])
for year in anys:
    if year in list(excedents['dataYear']):
        excedents_any = excedents[excedents['dataYear']==year]
        RAC_any = RAC[RAC['ANY'] <= year]
        RAC_any = RAC_any.groupby(['I_MUNICIPI','I_COMARCA','province']).agg({'I_KW_TOT':'sum','POT_CAPACITAT':'sum'}).reset_index()
        RAC_potencia_total = RAC_any.groupby(['province']).agg({'POT_CAPACITAT':'sum'}).reset_index()
        RAC_any = pd.merge(RAC_any, excedents_any[['province','sumEnergy','dataYear']], how="left", on='province')
        RAC_any = pd.merge(RAC_any, RAC_potencia_total[['province','POT_CAPACITAT']], how="left", on='province')
        RAC_any['energia_municipi'] = RAC_any['POT_CAPACITAT_x']*RAC_any['sumEnergy']/RAC_any['POT_CAPACITAT_y']
        
        #concatenem els df
        resultat = pd.concat([resultat, RAC_any], ignore_index=True)

#li fem unes esmenes a les comarques
resultat['I_COMARCA'] = resultat['I_COMARCA'].replace({'Aran': "Val d'Aran",'Lluçanes':'Lluçanès'})
resultat.to_excel('generacio_excedents_resultat.xlsx')