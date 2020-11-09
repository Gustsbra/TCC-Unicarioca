# -*- coding: utf-8 -*-
"""
Created on Mon Sep 21 22:20:00 2020

@author: gusts
"""
# 1. Carregando pacotes

import pandas as pd
import pandas.io.sql as DFSQL
import pyodbc
import numpy as np
import matplotlib.pyplot as plt
import quandl as ql
import yfinance as yf
import datetime as dt
from datetime import datetime
from datetime import date
from datetime import timedelta
from workalendar.america import Brazil

# 2. Definindo conexão do banco de dados

conn_fundos = pyodbc.connect(r'Driver=SQL Server;Server=.\SQLEXPRESS;Database=Fundos;Trusted_Connection=yes;')
cursor_fundos = conn_fundos.cursor()

conn_dados = pyodbc.connect(r'Driver=SQL Server;Server=.\SQLEXPRESS;Database=DadosMercado;Trusted_Connection=yes;')
cursor_dados = conn_dados.cursor()

# 3. Definindo datas

data_ref = date(2017, 1, 1)

cal = Brazil()
now=datetime.now()
data = cal.add_working_days(now, -1)

d=data.strftime('%d')
m=data.strftime('%m')
a=data.strftime('%Y')

# 4. Baixando dados de cadastro dos fundos na CVM

url = "http://dados.cvm.gov.br/dados/FI/CAD/DADOS/inf_cadastral_fi_"+ a + m + d + ".csv"
df = pd.read_csv(url, sep=';', encoding='latin_1', keep_default_na=False)

# 5. Tratando dados de cadastro

df['DENOM_SOCIAL'] = df['DENOM_SOCIAL'].str.replace("'", '')
df['DIRETOR'] = df['DIRETOR'].str.replace("'", '')
df['INF_TAXA_ADM'] = df['INF_TAXA_ADM'].str.replace("'", '')
df['INF_TAXA_PERFM'] = df['INF_TAXA_PERFM'].str.replace("'", '')

# 6. Inserindo dados de cadastro dos fundos

DimCadastro = len(df)

for i in range(DimCadastro): 
    
    query = "exec spInsereDadosCadastro " \
        "'" + str(df['CNPJ_FUNDO'][i]) + "',"\
        "'" + str(df['DENOM_SOCIAL'][i]) + "',"\
        "'" + str(df['DT_REG'][i]) + "',"\
        "'" + str(df['DT_CONST'][i]) + "',"\
        "'" + str(df['DT_CANCEL'][i]) + "',"\
        "'" + str(df['SIT'][i]) + "',"\
        "'" + str(df['DT_INI_SIT'][i]) + "',"\
        "'" + str(df['DT_INI_ATIV'][i]) + "',"\
        "'" + str(df['DT_INI_EXERC'][i]) + "',"\
        "'" + str(df['DT_FIM_EXERC'][i]) + "',"\
        "'" + str(df['CLASSE'][i]) + "',"\
        "'" + str(df['DT_INI_CLASSE'][i]) + "',"\
        "'" + str(df['RENTAB_FUNDO'][i]) + "',"\
        "'" + str(df['CONDOM'][i]) + "',"\
        "'" + str(df['FUNDO_COTAS'][i]) + "',"\
        "'" + str(df['FUNDO_EXCLUSIVO'][i]) + "',"\
        "'" + str(df['TRIB_LPRAZO'][i]) + "',"\
        "'" + str(df['INVEST_QUALIF'][i]) + "',"\
        "'" + str(df['TAXA_PERFM'][i]) + "',"\
        "'" + str(df['INF_TAXA_PERFM'][i]) + "',"\
        "'" + str(df['TAXA_ADM'][i]) + "',"\
        "'" + str(df['INF_TAXA_ADM'][i]) + "',"\
        "'" + str(df['VL_PATRIM_LIQ'][i]) + "',"\
        "'" + str(df['DT_PATRIM_LIQ'][i]) + "',"\
        "'" + str(df['DIRETOR'][i]) + "',"\
        "'" + str(df['CNPJ_ADMIN'][i]) + "',"\
        "'" + str(df['ADMIN'][i]) + "',"\
        "'" + str(df['PF_PJ_GESTOR'][i]) + "',"\
        "'" + str(df['CPF_CNPJ_GESTOR'][i]) + "',"\
        "'" + str(df['GESTOR'][i]) + "',"\
        "'" + str(df['CNPJ_AUDITOR'][i]) + "',"\
        "'" + str(df['AUDITOR'][i]) + "',"\
        "'" + str(df['CNPJ_CUSTODIANTE'][i]) + "',"\
        "'" + str(df['CUSTODIANTE'][i]) + "',"\
        "'" + str(df['CNPJ_CONTROLADOR'][i]) + "',"\
        "'" + str(df['CONTROLADOR'][i]) + "'"           
    print(query)
    cursor_fundos.execute(query)
    conn_fundos.commit()
    
conn_fundos.close()

# 6. Baixando dados de informe diário dos fundos na CVM e inserindo no banco de dados

num_meses = (data.year - data_ref.year) * 12 + (data.month - data_ref.month)

for j in range(num_meses):
    
    print(j)
    
    m=data.strftime('%m')
    a=data.strftime('%Y')
    
    url_inf = "http://dados.cvm.gov.br/dados/FI/DOC/INF_DIARIO/DADOS/inf_diario_fi_"+ a + m + ".csv"
    df_inf = pd.read_csv(url_inf, sep=';', encoding='latin_1', keep_default_na=False)
    
    DimInfo = len(df_inf)
    print(DimInfo)
    
    for i in range(DimInfo): 
    
        query = "exec spInsereInfoDia " \
            "'" + str(df_inf['CNPJ_FUNDO'][i]) + "',"\
            "'" + str(df_inf['DT_COMPTC'][i]) + "',"\
            + str(df_inf['VL_TOTAL'][i]) + ","\
            + str(df_inf['VL_QUOTA'][i]) + ","\
            + str(df_inf['VL_PATRIM_LIQ'][i]) + ","\
            + str(df_inf['CAPTC_DIA'][i]) + ","\
            + str(df_inf['RESG_DIA'][i]) + ","\
            + str(df_inf['NR_COTST'][i])        
        print(query)
        cursor_fundos.execute(query)
        conn_fundos.commit()
        
    data = data.replace(day=1) - timedelta(days=1)

# 7. Baixando dados CDI e Ibovespa do pacote quandl e do yfinance 

ql.ApiConfig.api_key = "7TvuerEzwBAsuxUNqodm"

cdi = ql.get("BCB/4389")
cdi.index = pd.to_datetime(cdi.index)

ibov = yf.Ticker("^BVSP").history(period="1000d")

# 8. Inserindo dados CDI e Ibovespa no banco de dados

DimCDI = len(cdi)

for i in range(DimCDI): 
    
    query = "exec spInsereDadosMercado '" + str(cdi.index[i].strftime('%Y-%m-%d')) + "','CDI'," + str(cdi['Value'][i])
    print(query)
    cursor_dados.execute(query)
    conn_dados.commit()

DimIbov = len(ibov)

for i in range(DimIbov): 
    
    query = "exec spInsereDadosMercado '" + str(ibov.index[i].strftime('%Y-%m-%d')) + "','IBOV'," + str(ibov['Close'][i])
    print(query)
    cursor_dados.execute(query)
    conn_dados.commit()
    
conn_dados.close()


