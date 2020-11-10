# -*- coding: utf-8 -*-
"""
Created on Sun Sep 20 15:39:19 2020

@author: gusts
"""

# 1. Carregando pacotes

import pandas as pd
import pandas.io.sql as DFSQL
import pyodbc
import numpy as np
np.longfloat

import plotly.express as px
import plotly.io as pio
pio.renderers.default='browser'

import dash
import dash_table
import dash_core_components as dcc
import dash_html_components as html

pd.options.display.precision = 16
pd.set_option('display.float_format', lambda x: '%.16f' % x)

def multi_period_return(period_returns):
 return np.nan_to_num(np.nanprod(period_returns + 1)) - 1


# 2. Definindo conexão do banco de dados

connFund = pyodbc.connect(r'Driver=SQL Server;Server=.\SQLEXPRESS;Database=fundos;Trusted_Connection=yes;')
cursorFund = connFund.cursor()

connMarketData = pyodbc.connect(r'Driver=SQL Server;Server=.\SQLEXPRESS;Database=DadosMercado;Trusted_Connection=yes;')
cursorMarketData = connMarketData.cursor()

# 3. Carregando dados

query = "select c.CNPJ, c.Nome, c.Classe, c.DT_INI_ATIV, i.* " \
"from InfoDiaria i " \
"inner join Cadastro c " \
"on i.CNPJ_FUNDO = c.CNPJ " \
"where c.SITUACAO = 'EM FUNCIONAMENTO NORMAL' " \
"and c.CONDOM = 'Aberto' " \
"and c.FUNDO_EXCLUSIVO = 'N' " \
"and c.INVEST_QUALIF = 'N' " \
"and c.DT_INI_ATIV <= '2017-01-01' " \
"and c.Nome not like '%MASTER%' " \
"and c.Nome not like '%ESPELHO%' " \
"and c.Nome not like '%ADVISORY%' " \
"and c.Nome not like '%PREVIDENCIA%' "
dados = DFSQL.read_sql_query(query, connFund)


queryMarketData = "select Data, Nome, Valor from DadosHistoricos"
marketData = DFSQL.read_sql_query(queryMarketData, connMarketData)

# 4. Ajustando dados

cotas = dados.pivot_table('VL_QUOTA', 'DT_COMPTC', 'CNPJ_FUNDO')
cotas = cotas[cotas.index <= '2020-06-30']
cotas.index = pd.to_datetime(cotas.index)
cotas.index.names = ['Date']

#Removendo dias em que ocorreu feriado
cotas = cotas.dropna(thresh=20)

#Removendo as duplicadas do dataframe dados para economizar espaço na alocação de memória
dados = dados.drop_duplicates(subset=['CNPJ']) 

marketData2 = marketData.pivot_table('Valor', 'Data', 'Nome')
marketData2 = marketData2[marketData2.index <= '2020-06-30']
marketData2 = marketData2[marketData2.index >= '2017-01-01']
marketData2.index = pd.to_datetime(marketData2.index)
marketData2.index.names = ['Date']
marketData2 = marketData2.assign(CDI = lambda x: (((1+marketData2['CDI']/100)**(1/252))-1))
marketData2.fillna(method='ffill', inplace=True)

#Removendo o dataframe marketData para economizar espaço na alocação de memória
del marketData 

cotas = cotas.join(marketData2['IBOV'])
cotas.fillna(method='ffill', inplace=True)

# 5. Calculando Retorno dos Fundos

Retornos = cotas.pct_change()
Retornos = Retornos.join(marketData2['CDI'])
Retornos = Retornos.dropna(thresh=2)
Retornos.fillna(method='ffill', inplace=True)

# 6. Calculando Retorno acumulado rolling dos Fundos

Ret_roll_126 = (Retornos).rolling(126).apply(multi_period_return)
Ret_roll_126 = Ret_roll_126.dropna(thresh=2)*100
Ret_roll_252 = (Retornos).rolling(252).apply(multi_period_return)
Ret_roll_252 = Ret_roll_252.dropna(thresh=2)*100
Ret_roll_504 = (Retornos).rolling(504).apply(multi_period_return)
Ret_roll_504 = Ret_roll_504.dropna(thresh=2)*100
Ret_roll_756 = (Retornos).rolling(756).apply(multi_period_return)
Ret_roll_756 = Ret_roll_756.dropna(thresh=2)*100


# 7. Calculando Retorno acumulado dos Fundos até a data de análise

Ret_126 = ((1 + Retornos.tail(126)).cumprod() - 1)
zero_ret = ((1 + Retornos.tail(127)).cumprod() - 1)
zero_ret = zero_ret.head(1)
zero_ret2 = zero_ret.replace(zero_ret, 0)
Ret_126 = zero_ret2.append(Ret_126)*100

Ret_252 = ((1 + Retornos.tail(252)).cumprod() - 1)
zero_ret = ((1 + Retornos.tail(253)).cumprod() - 1)
zero_ret = zero_ret.head(1)
zero_ret2 = zero_ret.replace(zero_ret, 0)
Ret_252 = zero_ret2.append(Ret_252)*100

Ret_504 = ((1 + Retornos.tail(504)).cumprod() - 1)
zero_ret = ((1 + Retornos.tail(505)).cumprod() - 1)
zero_ret = zero_ret.head(1)
zero_ret2 = zero_ret.replace(zero_ret, 0)
Ret_504 = zero_ret2.append(Ret_504)*100

Ret_756 = ((1 + Retornos.tail(756)).cumprod() - 1)
zero_ret = ((1 + Retornos.tail(757)).cumprod() - 1)
zero_ret = zero_ret.head(1)
zero_ret2 = zero_ret.replace(zero_ret, 0)
Ret_756 = zero_ret2.append(Ret_756)*100

# 8. Calculando Volatilidade acumulada dos Fundos

Vol_126 = Retornos.rolling(126).std()*(252**0.5)*100
Vol_126 = Vol_126.dropna(thresh=2)

Vol_252 = Retornos.rolling(252).std()*(252**0.5)*100
Vol_252 = Vol_252.dropna(thresh=2)

Vol_504 = Retornos.rolling(504).std()*(252**0.5)*100
Vol_504 = Vol_504.dropna(thresh=2)

Vol_756 = Retornos.rolling(756).std()*(252**0.5)*100
Vol_756 = Vol_756.dropna(thresh=2)


# 9. Calculando Retorno over CDI e Ibovespa

Ret_Over_CDI_126 = Retornos.sub(Retornos['CDI'], axis = 0).rolling(126).apply(multi_period_return)
Ret_Over_CDI_126 = Ret_Over_CDI_126.dropna(thresh=2)

Ret_Over_CDI_252 = Retornos.sub(Retornos['CDI'], axis = 0).rolling(252).apply(multi_period_return)
Ret_Over_CDI_252 = Ret_Over_CDI_252.dropna(thresh=2)

Ret_Over_CDI_504 = Retornos.sub(Retornos['CDI'], axis = 0).rolling(504).apply(multi_period_return)
Ret_Over_CDI_504 = Ret_Over_CDI_504.dropna(thresh=2)

Ret_Over_CDI_756 = Retornos.sub(Retornos['CDI'], axis = 0).rolling(756).apply(multi_period_return)
Ret_Over_CDI_756 = Ret_Over_CDI_756.dropna(thresh=2)

Ret_Over_IBOV_126 = Retornos.sub(Retornos['IBOV'], axis = 0).rolling(126).apply(multi_period_return)
Ret_Over_IBOV_126 = Ret_Over_IBOV_126.dropna(thresh=2)

Ret_Over_IBOV_252 = Retornos.sub(Retornos['IBOV'], axis = 0).rolling(252).apply(multi_period_return)
Ret_Over_IBOV_252 = Ret_Over_IBOV_252.dropna(thresh=2)

Ret_Over_IBOV_504 = Retornos.sub(Retornos['IBOV'], axis = 0).rolling(504).apply(multi_period_return)
Ret_Over_IBOV_504 = Ret_Over_IBOV_504.dropna(thresh=2)

Ret_Over_IBOV_756 = Retornos.sub(Retornos['IBOV'], axis = 0).rolling(756).apply(multi_period_return)
Ret_Over_IBOV_756 = Ret_Over_IBOV_756.dropna(thresh=2)

# 10. Calculando Sharpe

Sharpe_126 = ((((1+Ret_Over_CDI_126)**(252/126))-1)*100)/Vol_126
Sharpe_126 = Sharpe_126.dropna(thresh=2)

Sharpe_252 = ((((1+Ret_Over_CDI_252)**(252/252))-1)*100)/Vol_252
Sharpe_252 = Sharpe_252.dropna(thresh=2)

Sharpe_504 = ((((1+Ret_Over_CDI_504)**(252/504))-1)*100)/Vol_504
Sharpe_504 = Sharpe_504.dropna(thresh=2)

Sharpe_756 = ((((1+Ret_Over_CDI_756)**(252/756))-1)*100)/Vol_756
Sharpe_756 = Sharpe_756.dropna(thresh=2)

# 11. Calculando Betas

Cov_126 = Retornos.rolling(window=126).cov(other=Retornos['IBOV'].rolling(window=126))
Var_IBOV_126 = Retornos['IBOV'].rolling(window=126).var()
Beta_126 = Cov_126.div(Var_IBOV_126, axis=0)
Beta_126 = Beta_126.dropna(thresh=2)

Cov_252 = Retornos.rolling(window=252).cov(other=Retornos['IBOV'].rolling(window=252))
Var_IBOV_252 = Retornos['IBOV'].rolling(window=252).var()
Beta_252 = Cov_252.div(Var_IBOV_252, axis=0)
Beta_252 = Beta_252.dropna(thresh=2)

Cov_504 = Retornos.rolling(window=504).cov(other=Retornos['IBOV'].rolling(window=504))
Var_IBOV_504 = Retornos['IBOV'].rolling(window=504).var()
Beta_504 = Cov_504.div(Var_IBOV_504, axis=0)
Beta_504 = Beta_504.dropna(thresh=2)

Cov_756 = Retornos.rolling(window=756).cov(other=Retornos['IBOV'].rolling(window=756))
Var_IBOV_756 = Retornos['IBOV'].rolling(window=756).var()
Beta_756 = Cov_756.div(Var_IBOV_756, axis=0)
Beta_756 = Beta_756.dropna(thresh=2)

# 12. Calculando Índice de Treynor

Treynor_126 = ((((1+Ret_Over_CDI_126)**(252/126))-1)) / Beta_126
Treynor_126 = Treynor_126.dropna(thresh=2)

Treynor_252 = ((((1+Ret_Over_CDI_252)**(252/252))-1)) / Beta_252
Treynor_252 = Treynor_252.dropna(thresh=2)

Treynor_504 = ((((1+Ret_Over_CDI_504)**(252/504))-1)) / Beta_504
Treynor_504 = Treynor_504.dropna(thresh=2)

Treynor_756 = ((((1+Ret_Over_CDI_756)**(252/756))-1)) / Beta_756
Treynor_756 = Treynor_756.dropna(thresh=2)

# 13. Calculando Índice de Jensen

Capm_126 = Beta_126.mul(Ret_Over_CDI_126['IBOV'], axis = 0) + Ret_roll_126['CDI'][:,None]
Capm_252 = Beta_252.mul(Ret_Over_CDI_252['IBOV'], axis = 0) + Ret_roll_252['CDI'][:,None]
Capm_504 = Beta_504.mul(Ret_Over_CDI_504['IBOV'], axis = 0) + Ret_roll_504['CDI'][:,None]
Capm_756 = Beta_756.mul(Ret_Over_CDI_756['IBOV'], axis = 0) + Ret_roll_756['CDI'][:,None]

Jensen_126 = Ret_roll_126 - Capm_126
Jensen_126 = Jensen_126.dropna(thresh=2)

Jensen_252 = Ret_roll_252 - Capm_252
Jensen_252 = Jensen_252.dropna(thresh=2)

Jensen_504 = Ret_roll_504 - Capm_504
Jensen_504 = Jensen_504.dropna(thresh=2)

Jensen_756 = Ret_roll_756 - Capm_756
Jensen_756 = Jensen_756.dropna(thresh=2)

# 14. Calculando Máximo DrawDown

Roll_Max_126 = cotas.rolling(window=126, min_periods=1).max()
Daily_Drawdown_126 = cotas/Roll_Max_126 - 1.0
MDD_126 = Daily_Drawdown_126.rolling(window=126, min_periods=1).min()*100

Roll_Max_252 = cotas.rolling(window=252, min_periods=1).max()
Daily_Drawdown_252 = cotas/Roll_Max_252 - 1.0
MDD_252 = Daily_Drawdown_252.rolling(window=252, min_periods=1).min()*100

Roll_Max_504 = cotas.rolling(window=504, min_periods=1).max()
Daily_Drawdown_504 = cotas/Roll_Max_504 - 1.0
MDD_504 = Daily_Drawdown_504.rolling(window=504, min_periods=1).min()*100

Roll_Max_756 = cotas.rolling(window=756, min_periods=1).max()
Daily_Drawdown_756 = cotas/Roll_Max_252 - 1.0
MDD_756 = Daily_Drawdown_756.rolling(window=756, min_periods=1).min()*100

# 15. Montando DataFrame Resumo

dfs_126 = [Ret_roll_126.tail(1).melt(value_name = 'Ret'), 
           Vol_126.tail(1).melt(value_name = 'Vol'),
           Sharpe_126.tail(1).melt(value_name = 'Sharpe'),
           Treynor_126.tail(1).melt(value_name = 'Treynor'),
           Jensen_126.tail(1).melt(value_name = 'Jensen'),
           MDD_126.tail(1).melt(value_name = 'MDD')]

dfs = [df.set_index('variable') for df in dfs_126]
Resumo_126 = dfs[0].join(dfs[1:])
Resumo_126.index.name = 'CNPJ'
Resumo_total_126 = pd.merge(dados[['CNPJ', 'Nome', 'Classe']].drop_duplicates(), 
                            Resumo_126, on=['CNPJ'])

dfs_252 = [Ret_roll_252.tail(1).melt(value_name = 'Ret'), 
           Vol_252.tail(1).melt(value_name = 'Vol'),
           Sharpe_252.tail(1).melt(value_name = 'Sharpe'),
           Treynor_252.tail(1).melt(value_name = 'Treynor'),
           Jensen_252.tail(1).melt(value_name = 'Jensen'),
           MDD_252.tail(1).melt(value_name = 'MDD')]

dfs = [df.set_index('variable') for df in dfs_252]
Resumo_252 = dfs[0].join(dfs[1:])
Resumo_252.index.name = 'CNPJ'
Resumo_total_252 = pd.merge(dados[['CNPJ', 'Nome', 'Classe']].drop_duplicates(), 
                            Resumo_252, on=['CNPJ'])

dfs_504 = [Ret_roll_504.tail(1).melt(value_name = 'Ret'), 
           Vol_504.tail(1).melt(value_name = 'Vol'),
           Sharpe_504.tail(1).melt(value_name = 'Sharpe'),
           Treynor_504.tail(1).melt(value_name = 'Treynor'),
           Jensen_504.tail(1).melt(value_name = 'Jensen'),
           MDD_504.tail(1).melt(value_name = 'MDD')]

dfs = [df.set_index('variable') for df in dfs_504]
Resumo_504 = dfs[0].join(dfs[1:])
Resumo_504.index.name = 'CNPJ'
Resumo_total_504 = pd.merge(dados[['CNPJ', 'Nome', 'Classe']].drop_duplicates(), 
                            Resumo_504, on=['CNPJ'])

dfs_756 = [Ret_roll_756.tail(1).melt(value_name = 'Ret'), 
           Vol_756.tail(1).melt(value_name = 'Vol'),
           Sharpe_756.tail(1).melt(value_name = 'Sharpe'),
           Treynor_756.tail(1).melt(value_name = 'Treynor'),
           Jensen_756.tail(1).melt(value_name = 'Jensen'),
           MDD_756.tail(1).melt(value_name = 'MDD')]

dfs = [df.set_index('variable') for df in dfs_756]
Resumo_756 = dfs[0].join(dfs[1:])
Resumo_756.index.name = 'CNPJ'
Resumo_total_756 = pd.merge(dados[['CNPJ', 'Nome', 'Classe']].drop_duplicates(), 
                            Resumo_756, on=['CNPJ'])

# 16. Segregando as classes em Renda Fixa, Ações e Multimercados

Renda_Fixa_126 = Resumo_total_126[Resumo_total_126['Classe']=='Fundo de Renda Fixa']
Renda_Fixa_252 = Resumo_total_252[Resumo_total_252['Classe']=='Fundo de Renda Fixa']
Renda_Fixa_504 = Resumo_total_504[Resumo_total_504['Classe']=='Fundo de Renda Fixa']
Renda_Fixa_756 = Resumo_total_756[Resumo_total_756['Classe']=='Fundo de Renda Fixa']

Acoes_126 = Resumo_total_126[Resumo_total_126['Classe']=='Fundo de Ações']
Acoes_252 = Resumo_total_252[Resumo_total_252['Classe']=='Fundo de Ações']
Acoes_504 = Resumo_total_504[Resumo_total_504['Classe']=='Fundo de Ações']
Acoes_756 = Resumo_total_756[Resumo_total_756['Classe']=='Fundo de Ações']

Mult_126 = Resumo_total_126[Resumo_total_126['Classe']=='Fundo Multimercado']
Mult_252 = Resumo_total_252[Resumo_total_252['Classe']=='Fundo Multimercado']
Mult_504 = Resumo_total_504[Resumo_total_504['Classe']=='Fundo Multimercado']
Mult_756 = Resumo_total_756[Resumo_total_756['Classe']=='Fundo Multimercado']

# 17. Adicionando quartis para realizar a classificação

# Renda Fixa
Renda_Fixa_126['qSharpe'] = pd.qcut(Renda_Fixa_126['Sharpe'], 4, ['1','2','3','4'])
Renda_Fixa_126['qTreynor'] = pd.qcut(Renda_Fixa_126['Treynor'], 4, ['1','2','3','4'])
Renda_Fixa_126['qJensen'] = pd.qcut(Renda_Fixa_126['Jensen'], 4, ['1','2','3','4'])
Renda_Fixa_126['Nota'] = pd.to_numeric(Renda_Fixa_126['qSharpe']) + pd.to_numeric(Renda_Fixa_126['qTreynor']) + pd.to_numeric(Renda_Fixa_126['qJensen'])
Renda_Fixa_126 = Renda_Fixa_126.sort_values('Nota', ascending = False)
Renda_Fixa_126_Top10 = Renda_Fixa_126.head(10)[['CNPJ','Nome', 'Ret', 'Vol', 'Sharpe', 'Treynor', 'Jensen', 'MDD', 'Nota']]
Renda_Fixa_126_Top10 = Renda_Fixa_126_Top10.set_index('CNPJ')
Renda_Fixa_126_Top10 = Renda_Fixa_126_Top10.reset_index()

Renda_Fixa_252['qSharpe'] = pd.qcut(Renda_Fixa_252['Sharpe'], 4, ['1','2','3','4'])
Renda_Fixa_252['qTreynor'] = pd.qcut(Renda_Fixa_252['Treynor'], 4, ['1','2','3','4'])
Renda_Fixa_252['qJensen'] = pd.qcut(Renda_Fixa_252['Jensen'], 4, ['1','2','3','4'])
Renda_Fixa_252['Nota'] = pd.to_numeric(Renda_Fixa_252['qSharpe']) + pd.to_numeric(Renda_Fixa_252['qTreynor']) + pd.to_numeric(Renda_Fixa_252['qJensen'])
Renda_Fixa_252 = Renda_Fixa_252.sort_values('Nota', ascending = False)
Renda_Fixa_252_Top10 = Renda_Fixa_252.head(10)[['CNPJ','Nome', 'Ret', 'Vol', 'Sharpe', 'Treynor', 'Jensen', 'MDD', 'Nota']]
Renda_Fixa_252_Top10 = Renda_Fixa_252_Top10.set_index('CNPJ')
Renda_Fixa_252_Top10 = Renda_Fixa_252_Top10.reset_index()

Renda_Fixa_504['qSharpe'] = pd.qcut(Renda_Fixa_504['Sharpe'], 4, ['1','2','3','4'])
Renda_Fixa_504['qTreynor'] = pd.qcut(Renda_Fixa_504['Treynor'], 4, ['1','2','3','4'])
Renda_Fixa_504['qJensen'] = pd.qcut(Renda_Fixa_504['Jensen'], 4, ['1','2','3','4'])
Renda_Fixa_504['Nota'] = pd.to_numeric(Renda_Fixa_504['qSharpe']) + pd.to_numeric(Renda_Fixa_504['qTreynor']) + pd.to_numeric(Renda_Fixa_504['qJensen'])
Renda_Fixa_504 = Renda_Fixa_504.sort_values('Nota', ascending = False)
Renda_Fixa_504_Top10 = Renda_Fixa_504.head(10)[['CNPJ','Nome', 'Ret', 'Vol', 'Sharpe', 'Treynor', 'Jensen', 'MDD', 'Nota']]
Renda_Fixa_504_Top10 = Renda_Fixa_504_Top10.set_index('CNPJ')
Renda_Fixa_504_Top10 = Renda_Fixa_504_Top10.reset_index()

Renda_Fixa_756['qSharpe'] = pd.qcut(Renda_Fixa_756['Sharpe'], 4, ['1','2','3','4'])
Renda_Fixa_756['qTreynor'] = pd.qcut(Renda_Fixa_756['Treynor'], 4, ['1','2','3','4'])
Renda_Fixa_756['qJensen'] = pd.qcut(Renda_Fixa_756['Jensen'], 4, ['1','2','3','4'])
Renda_Fixa_756['Nota'] = pd.to_numeric(Renda_Fixa_756['qSharpe']) + pd.to_numeric(Renda_Fixa_756['qTreynor']) + pd.to_numeric(Renda_Fixa_756['qJensen'])
Renda_Fixa_756 = Renda_Fixa_756.sort_values('Nota', ascending = False)
Renda_Fixa_756_Top10 = Renda_Fixa_756.head(10)[['CNPJ','Nome', 'Ret', 'Vol', 'Sharpe', 'Treynor', 'Jensen', 'MDD', 'Nota']]
Renda_Fixa_756_Top10 = Renda_Fixa_756_Top10.set_index('CNPJ')
Renda_Fixa_756_Top10 = Renda_Fixa_756_Top10.reset_index()

Renda_Fixa_Geral = Renda_Fixa_126.iloc[:,0:2]
Renda_Fixa_Geral['Nota_Final'] = Renda_Fixa_126['Nota'] + Renda_Fixa_252['Nota'] + Renda_Fixa_504['Nota'] + Renda_Fixa_756['Nota']
Renda_Fixa_Geral = Renda_Fixa_Geral.sort_values('Nota_Final', ascending = False)
Renda_Fixa_Geral_Top10 = Renda_Fixa_Geral.head(10)[['CNPJ','Nome', 'Nota_Final']]

# Ações
Acoes_126['qSharpe'] = pd.qcut(Acoes_126['Sharpe'], 4, ['1','2','3','4'])
Acoes_126['qTreynor'] = pd.qcut(Acoes_126['Treynor'], 4, ['1','2','3','4'])
Acoes_126['qJensen'] = pd.qcut(Acoes_126['Jensen'], 4, ['1','2','3','4'])
Acoes_126['Nota'] = pd.to_numeric(Acoes_126['qSharpe']) + pd.to_numeric(Acoes_126['qTreynor']) + pd.to_numeric(Acoes_126['qJensen'])
Acoes_126 = Acoes_126.sort_values('Nota', ascending = False)
Acoes_126_Top10 = Acoes_126.head(10)[['CNPJ','Nome', 'Ret', 'Vol', 'Sharpe', 'Treynor', 'Jensen', 'MDD', 'Nota']]
Acoes_126_Top10 = Acoes_126_Top10.set_index('CNPJ')
Acoes_126_Top10 = Acoes_126_Top10.reset_index()

Acoes_252['qSharpe'] = pd.qcut(Acoes_252['Sharpe'], 4, ['1','2','3','4'])
Acoes_252['qTreynor'] = pd.qcut(Acoes_252['Treynor'], 4, ['1','2','3','4'])
Acoes_252['qJensen'] = pd.qcut(Acoes_252['Jensen'], 4, ['1','2','3','4'])
Acoes_252['Nota'] = pd.to_numeric(Acoes_252['qSharpe']) + pd.to_numeric(Acoes_252['qTreynor']) + pd.to_numeric(Acoes_252['qJensen'])
Acoes_252 = Acoes_252.sort_values('Nota', ascending = False)
Acoes_252_Top10 = Acoes_252.head(10)[['CNPJ','Nome', 'Ret', 'Vol', 'Sharpe', 'Treynor', 'Jensen', 'MDD', 'Nota']]
Acoes_252_Top10 = Acoes_252_Top10.set_index('CNPJ')
Acoes_252_Top10 = Acoes_252_Top10.reset_index()

Acoes_504['qSharpe'] = pd.qcut(Acoes_504['Sharpe'], 4, ['1','2','3','4'])
Acoes_504['qTreynor'] = pd.qcut(Acoes_504['Treynor'], 4, ['1','2','3','4'])
Acoes_504['qJensen'] = pd.qcut(Acoes_504['Jensen'], 4, ['1','2','3','4'])
Acoes_504['Nota'] = pd.to_numeric(Acoes_504['qSharpe']) + pd.to_numeric(Acoes_504['qTreynor']) + pd.to_numeric(Acoes_504['qJensen'])
Acoes_504 = Acoes_504.sort_values('Nota', ascending = False)
Acoes_504_Top10 = Acoes_504.head(10)[['CNPJ','Nome', 'Ret', 'Vol', 'Sharpe', 'Treynor', 'Jensen', 'MDD', 'Nota']]
Acoes_504_Top10 = Acoes_504_Top10.set_index('CNPJ')
Acoes_504_Top10 = Acoes_504_Top10.reset_index()

Acoes_756['qSharpe'] = pd.qcut(Acoes_756['Sharpe'], 4, ['1','2','3','4'])
Acoes_756['qTreynor'] = pd.qcut(Acoes_756['Treynor'], 4, ['1','2','3','4'])
Acoes_756['qJensen'] = pd.qcut(Acoes_756['Jensen'], 4, ['1','2','3','4'])
Acoes_756['Nota'] = pd.to_numeric(Acoes_756['qSharpe']) + pd.to_numeric(Acoes_756['qTreynor']) + pd.to_numeric(Acoes_756['qJensen'])
Acoes_756 = Acoes_756.sort_values('Nota', ascending = False)
Acoes_756_Top10 = Acoes_756.head(10)[['CNPJ','Nome', 'Ret', 'Vol', 'Sharpe', 'Treynor', 'Jensen', 'MDD', 'Nota']]
Acoes_756_Top10 = Acoes_756_Top10.set_index('CNPJ')
Acoes_756_Top10 = Acoes_756_Top10.reset_index()

Acoes_Geral = Acoes_126.iloc[:,0:2]
Acoes_Geral['Nota_Final'] = Acoes_126['Nota'] + Acoes_252['Nota'] + Acoes_504['Nota'] + Acoes_756['Nota']
Acoes_Geral = Acoes_Geral.sort_values('Nota_Final', ascending = False)
Acoes_Geral_Top10 = Acoes_Geral.head(10)[['CNPJ','Nome', 'Nota_Final']]

# Multimercado
Mult_126['qSharpe'] = pd.qcut(Mult_126['Sharpe'], 4, ['1','2','3','4'])
Mult_126['qTreynor'] = pd.qcut(Mult_126['Treynor'], 4, ['1','2','3','4'])
Mult_126['qJensen'] = pd.qcut(Mult_126['Jensen'], 4, ['1','2','3','4'])
Mult_126['Nota'] = pd.to_numeric(Mult_126['qSharpe']) + pd.to_numeric(Mult_126['qTreynor']) + pd.to_numeric(Mult_126['qJensen'])
Mult_126 = Mult_126.sort_values('Nota', ascending = False)
Mult_126_Top10 = Mult_126.head(10)[['CNPJ','Nome', 'Ret', 'Vol', 'Sharpe', 'Treynor', 'Jensen', 'MDD', 'Nota']]
Mult_126_Top10 = Mult_126_Top10.set_index('CNPJ')
Mult_126_Top10 = Mult_126_Top10.reset_index()


Mult_252['qSharpe'] = pd.qcut(Mult_252['Sharpe'], 4, ['1','2','3','4'])
Mult_252['qTreynor'] = pd.qcut(Mult_252['Treynor'], 4, ['1','2','3','4'])
Mult_252['qJensen'] = pd.qcut(Mult_252['Jensen'], 4, ['1','2','3','4'])
Mult_252['Nota'] = pd.to_numeric(Mult_252['qSharpe']) + pd.to_numeric(Mult_252['qTreynor']) + pd.to_numeric(Mult_252['qJensen'])
Mult_252 = Mult_252.sort_values('Nota', ascending = False)
Mult_252_Top10 = Mult_252.head(10)[['CNPJ','Nome', 'Ret', 'Vol', 'Sharpe', 'Treynor', 'Jensen', 'MDD', 'Nota']]
Mult_252_Top10 = Mult_252_Top10.set_index('CNPJ')
Mult_252_Top10 = Mult_252_Top10.reset_index()

Mult_504['qSharpe'] = pd.qcut(Mult_504['Sharpe'], 4, ['1','2','3','4'])
Mult_504['qTreynor'] = pd.qcut(Mult_504['Treynor'], 4, ['1','2','3','4'])
Mult_504['qJensen'] = pd.qcut(Mult_504['Jensen'], 4, ['1','2','3','4'])
Mult_504['Nota'] = pd.to_numeric(Mult_504['qSharpe']) + pd.to_numeric(Mult_504['qTreynor']) + pd.to_numeric(Mult_504['qJensen'])
Mult_504 = Mult_504.sort_values('Nota', ascending = False)
Mult_504_Top10 = Mult_504.head(10)[['CNPJ','Nome', 'Ret', 'Vol', 'Sharpe', 'Treynor', 'Jensen', 'MDD', 'Nota']]
Mult_504_Top10 = Mult_504_Top10.set_index('CNPJ')
Mult_504_Top10 = Mult_504_Top10.reset_index()

Mult_756['qSharpe'] = pd.qcut(Mult_756['Sharpe'], 4, ['1','2','3','4'])
Mult_756['qTreynor'] = pd.qcut(Mult_756['Treynor'], 4, ['1','2','3','4'])
Mult_756['qJensen'] = pd.qcut(Mult_756['Jensen'], 4, ['1','2','3','4'])
Mult_756['Nota'] = pd.to_numeric(Mult_756['qSharpe']) + pd.to_numeric(Mult_756['qTreynor']) + pd.to_numeric(Mult_756['qJensen'])
Mult_756 = Mult_756.sort_values('Nota', ascending = False)
Mult_756_Top10 = Mult_756.head(10)[['CNPJ','Nome', 'Ret', 'Vol', 'Sharpe', 'Treynor', 'Jensen', 'MDD', 'Nota']]
Mult_756_Top10 = Mult_756_Top10.set_index('CNPJ')
Mult_756_Top10 = Mult_756_Top10.reset_index()

Mult_Geral = Mult_126.iloc[:,0:2]
Mult_Geral['Nota_Final'] = Mult_126['Nota'] + Mult_252['Nota'] + Mult_504['Nota'] + Mult_756['Nota']
Mult_Geral = Mult_Geral.sort_values('Nota_Final', ascending = False)
Mult_Geral_Top10 = Mult_Geral.head(10)[['CNPJ','Nome', 'Nota_Final']]


# 18. Criação dos gráficos

# ========================================= CDI e IBOV ========================================= #
Graf_ind = px.line(marketData2, 
                   x=marketData2.index, 
                   y=['IBOV'], 
                   title='Visão geral do índice de Mercado Ibovespa para referência',
                   labels={"value":"Pontuação", "Date":"Data", "variable":"Índice"}
                   )

# ========================================= Renda Fixa ========================================= #

# ========== 126 dias ========== #

Graf_ret_Renda_Fixa_126 = px.line(Ret_126, 
                        x=Ret_126.index, 
                        y=Renda_Fixa_126_Top10.CNPJ, 
                        title='Retornos dos 10 melhores fundos Renda Fixa em uma janela de 126 dias',
                        labels={"value":"Retorno", "Date":"Data", "variable":"CNPJ do fundo"}
                )


Graf_vol_Renda_Fixa_126 = px.line(Vol_126, 
                        x=Vol_126.index, 
                        y=Renda_Fixa_126_Top10.CNPJ,  
                        title='Volatilidade acumulada dos 10 melhores fundos Renda Fixa em uma janela de 126 dias',
                        labels={"value":"Volatilidade", "Date":"Data", "variable":"CNPJ do fundo"}
                )

# ========== 252 dias ========== #
Graf_ret_Renda_Fixa_252 = px.line(Ret_252, 
                        x=Ret_252.index, 
                        y=Renda_Fixa_252_Top10.CNPJ,
                        title='Retorno dos 10 melhores Renda Fixa em uma janela de 252 dias',
                        labels={"value":"Retorno", "Date":"Data", "variable":"CNPJ do fundo"}
                         
                )

Graf_vol_Renda_Fixa_252 = px.line(Vol_252, 
                        x=Vol_252.index, 
                        y=Renda_Fixa_252_Top10.CNPJ,  
                        title='Volatilidade acumulada dos 10 melhores fundos Renda Fixa em uma janela de 252 dias',
                        labels={"value":"Volatilidade", "Date":"Data", "variable":"CNPJ do fundo"}
                )

# ========== 504 dias ========== #
Graf_ret_Renda_Fixa_504 = px.line(Ret_504, 
                        x=Ret_504.index, 
                        y=Renda_Fixa_504_Top10.CNPJ,                                               
                        title='Retorno dos 10 melhores fundos Renda Fixa em uma janela de 504 dias',
                        labels={"value":"Retorno", "Date":"Data", "variable":"CNPJ do fundo"}
                )

Graf_vol_Renda_Fixa_504 = px.line(Vol_504, 
                        x=Vol_504.index, 
                        y=Renda_Fixa_504_Top10.CNPJ,  
                        title='Volatilidade acumulada dos 10 melhores fundos Renda Fixa em uma janela de 504 dias',
                        labels={"value":"Volatilidade", "Date":"Data", "variable":"CNPJ do fundo"}
                )

# ========== 756 dias ========== #
Graf_ret_Renda_Fixa_756 = px.line(Ret_756, 
                        x=Ret_756.index, 
                        y=Renda_Fixa_756_Top10.CNPJ,
                        title='Retorno dos 10 melhores fundos Renda Fixa em uma janela de 756 dias',
                        labels={"value":"Retorno", "Date":"Data", "variable":"CNPJ do fundo"}
                )

Graf_vol_Renda_Fixa_756 = px.line(Vol_756, 
                        x=Vol_756.index, 
                        y=Renda_Fixa_756_Top10.CNPJ,  
                        title='Volatilidade acumulada dos 10 melhores fundos Renda Fixa em uma janela de 756 dias',
                        labels={"value":"Volatilidade", "Date":"Data", "variable":"CNPJ do fundo"}
                )

# ========================================= Ações ========================================= #

# ========== 126 dias ========== #

Graf_ret_Acoes_126 = px.line(Ret_126, 
                        x=Ret_126.index, 
                        y=Acoes_126_Top10.CNPJ, 
                        title='Retornos dos 10 melhores fundos de Ações em uma janela de 126 dias',
                        labels={"value":"Retorno", "Date":"Data", "variable":"CNPJ do fundo"}
                )

Graf_vol_Acoes_126 = px.line(Vol_126, 
                        x=Vol_126.index, 
                        y=Acoes_126_Top10.CNPJ,  
                        title='Volatilidade acumulada dos 10 melhores fundos de Ações em uma janela de 126 dias',
                        labels={"value":"Volatilidade", "Date":"Data", "variable":"CNPJ do fundo"}
                )

# ========== 252 dias ========== #
Graf_ret_Acoes_252 = px.line(Ret_252, 
                        x=Ret_252.index, 
                        y=Acoes_252_Top10.CNPJ,
                        title='Retorno dos 10 melhores de Ações em uma janela de 252 dias',
                        labels={"value":"Retorno", "Date":"Data", "variable":"CNPJ do fundo"}
                         
                )


Graf_vol_Acoes_252 = px.line(Vol_252, 
                        x=Vol_252.index, 
                        y=Acoes_252_Top10.CNPJ,  
                        title='Volatilidade acumulada dos 10 melhores fundos de Ações em uma janela de 252 dias',
                        labels={"value":"Volatilidade", "Date":"Data", "variable":"CNPJ do fundo"}
                )

# ========== 504 dias ========== #
Graf_ret_Acoes_504 = px.line(Ret_504, 
                        x=Ret_504.index, 
                        y=Acoes_504_Top10.CNPJ,                                               
                        title='Retorno dos 10 melhores fundos de Ações em uma janela de 504 dias',
                        labels={"value":"Retorno", "Date":"Data", "variable":"CNPJ do fundo"}
                )

Graf_vol_Acoes_504 = px.line(Vol_504, 
                        x=Vol_504.index, 
                        y=Acoes_504_Top10.CNPJ,  
                        title='Volatilidade acumulada dos 10 melhores fundos de Ações em uma janela de 504 dias',
                        labels={"value":"Volatilidade", "Date":"Data", "variable":"CNPJ do fundo"}
                )

# ========== 756 dias ========== #
Graf_ret_Acoes_756 = px.line(Ret_756, 
                        x=Ret_756.index, 
                        y=Acoes_756_Top10.CNPJ,
                        title='Retorno dos 10 melhores fundos de Ações em uma janela de 756 dias',
                        labels={"value":"Retorno", "Date":"Data", "variable":"CNPJ do fundo"}
                )


Graf_vol_Acoes_756 = px.line(Vol_756, 
                        x=Vol_756.index, 
                        y=Acoes_756_Top10.CNPJ,  
                        title='Volatilidade acumulada dos 10 melhores fundos de Ações em uma janela de 756 dias',
                        labels={"value":"Volatilidade", "Date":"Data", "variable":"CNPJ do fundo"}
                )

# ========================================= Multimercados ========================================= #

# ========== 126 dias ========== #

Graf_ret_mult_126 = px.line(Ret_126, 
                        x=Ret_126.index, 
                        y=Mult_126_Top10.CNPJ, 
                        title='Retornos dos 10 melhores fundos Mutltimercado em uma janela de 126 dias',
                        labels={"value":"Retorno", "Date":"Data", "variable":"CNPJ do fundo"}
                )

Graf_vol_mult_126 = px.line(Vol_126, 
                        x=Vol_126.index, 
                        y=Mult_126_Top10.CNPJ,  
                        title='Volatilidade acumulada dos 10 melhores fundos Mutltimercado em uma janela de 126 dias',
                        labels={"value":"Volatilidade", "Date":"Data", "variable":"CNPJ do fundo"}
                )

# ========== 252 dias ========== #
Graf_ret_mult_252 = px.line(Ret_252, 
                        x=Ret_252.index, 
                        y=Mult_252_Top10.CNPJ,
                        title='Retorno dos 10 melhores Mutltimercado em uma janela de 252 dias',
                        labels={"value":"Retorno", "Date":"Data", "variable":"CNPJ do fundo"}
                         
                )

Graf_vol_mult_252 = px.line(Vol_252, 
                        x=Vol_252.index, 
                        y=Mult_252_Top10.CNPJ,  
                        title='Volatilidade acumulada dos 10 melhores fundos Mutltimercado em uma janela de 252 dias',
                        labels={"value":"Volatilidade", "Date":"Data", "variable":"CNPJ do fundo"}
                )

# ========== 504 dias ========== #
Graf_ret_mult_504 = px.line(Ret_504, 
                        x=Ret_504.index, 
                        y=Mult_504_Top10.CNPJ,                                               
                        title='Retorno dos 10 melhores fundos Mutltimercado em uma janela de 504 dias',
                        labels={"value":"Retorno", "Date":"Data", "variable":"CNPJ do fundo"}
                )

Graf_vol_mult_504 = px.line(Vol_504, 
                        x=Vol_504.index, 
                        y=Mult_504_Top10.CNPJ,  
                        title='Volatilidade acumulada dos 10 melhores fundos Mutltimercado em uma janela de 504 dias',
                        labels={"value":"Volatilidade", "Date":"Data", "variable":"CNPJ do fundo"}
                )

# ========== 756 dias ========== #
Graf_ret_mult_756 = px.line(Ret_756, 
                        x=Ret_756.index, 
                        y=Mult_756_Top10.CNPJ,
                        title='Retorno dos 10 melhores fundos Mutltimercado em uma janela de 756 dias',
                        labels={"value":"Retorno", "Date":"Data", "variable":"CNPJ do fundo"}
                )

Graf_vol_mult_756 = px.line(Vol_756, 
                        x=Vol_756.index, 
                        y=Mult_756_Top10.CNPJ,  
                        title='Volatilidade acumulada dos 10 melhores fundos Mutltimercado em uma janela de 756 dias',
                        labels={"value":"Volatilidade", "Date":"Data", "variable":"CNPJ do fundo"}
                )


# 19. Gerando um Dashboard com uma página no navegador para cada tipo de fundo

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    html.Div(id='page-content')
])

# ======================================== Pagina inicial ===================================== #
index_page = html.Div([
    html.H1('Análises de Fundos de Investimento',
        style={'textAlign':'center'}
        ),
    dcc.Link('Relatório de Fundos Renda Fixa', href='/page-1'),
    html.Br(),
    dcc.Link('Relatório de Fundos de Ações', href='/page-2'),
    html.Br(),
    dcc.Link('Relatório de Fundos Multimercados', href='/page-3'),
    
])

# ======================================== Pagina dash dos Fundos Renda Fixa ===================================== #
page_1_layout = html.Div([
    html.H1('Relatório dos Fundos Renda Fixa',
        style={'textAlign':'center'}
        ),
    dcc.Link('Ir para os Fundos de Ações', href='/page-2'),
    html.Br(),
    dcc.Link('Ir para os Fundos Multimercados', href='/page-3'),
    html.Br(),
    dcc.Link('Retornar a página inicial', href='/'),
    html.Div(id='page-1-content'),
     
    html.Div([dcc.Graph(figure=Graf_ind)]),
    
    html.H2(children='Janela de tempo de 126 dias'),
    html.Div([
        dash_table.DataTable(
            id='table',
            columns=[{"name": i, "id": i, "type": "numeric"} for i in Renda_Fixa_126_Top10.columns],
            style_cell={'textAlign': 'center'},
            data=Renda_Fixa_126_Top10.to_dict('records'),
            )
        ]),
    html.Div([dcc.Graph(figure=Graf_ret_Renda_Fixa_126)]),
    html.Div([dcc.Graph(figure=Graf_vol_Renda_Fixa_126)]), 
    
    html.H2(children='Janela de tempo de 252 dias'),
    html.Div([
        dash_table.DataTable(
            id='table1',
            columns=[{"name": i, "id": i, "type": "numeric"} for i in Renda_Fixa_252_Top10.columns],
            style_cell={'textAlign': 'center'},
            data=Renda_Fixa_252_Top10.to_dict('records'),
            )
        ]),
    html.Div([dcc.Graph(figure=Graf_ret_Renda_Fixa_252)]),
    html.Div([dcc.Graph(figure=Graf_vol_Renda_Fixa_252)]),
    
    html.H2(children='Janela de tempo de 504 dias'),
    html.Div([
        dash_table.DataTable(
            id='table2',
            columns=[{"name": i, "id": i, "type": "numeric"} for i in Renda_Fixa_504_Top10.columns],
            style_cell={'textAlign': 'center'},
            data=Renda_Fixa_504_Top10.to_dict('records'),
            )
        ]),
    html.Div([dcc.Graph(figure=Graf_ret_Renda_Fixa_504)]),
    html.Div([dcc.Graph(figure=Graf_vol_Renda_Fixa_504)]),
    
    html.H2(children='Janela de tempo de 756 dias'),
    html.Div([
        dash_table.DataTable(
            id='table3',
            columns=[{"name": i, "id": i, "type": "numeric"} for i in Renda_Fixa_756_Top10.columns],
            style_cell={'textAlign': 'center'},
            data=Renda_Fixa_756_Top10.to_dict('records'),
            )
        ]),
    html.Div([dcc.Graph(figure=Graf_ret_Renda_Fixa_756)]),
    html.Div([dcc.Graph(figure=Graf_vol_Renda_Fixa_756)]),
    
    html.H2(children='Pontuação final dos 10 melhores fundos'),
    html.Div([
        dash_table.DataTable(
            id='table4',
            columns=[{"name": i, "id": i, "type": "numeric"} for i in Renda_Fixa_Geral_Top10.columns],
            style_cell={'textAlign': 'center'},
            data=Renda_Fixa_Geral_Top10.to_dict('records'),
            )
        ])
    
])
    

# ======================================== Pagina dash dos Fundos de Acoes ===================================== #
page_2_layout = html.Div([
    html.H1('Relatório dos Fundos de Ações',
        style={'textAlign':'center'}
        ),
    dcc.Link('Ir para os Fundos Renda Fixa', href='/page-1'),
    html.Br(),
    dcc.Link('Ir para os Fundos Multimercados', href='/page-3'),
    html.Br(),
    dcc.Link('Retornar a página inicial', href='/'),
    html.Div(id='page-2-content'),

    html.Div([dcc.Graph(figure=Graf_ind)]),

    html.H2(children='Janela de tempo de 126 dias'),
    html.Div([
        dash_table.DataTable(
            id='table',
            columns=[{"name": i, "id": i, "type": "numeric"} for i in Acoes_126_Top10.columns],
            style_cell={'textAlign': 'center'},
            data=Acoes_126_Top10.to_dict('records'),
            )
        ]),
    html.Div([dcc.Graph(figure=Graf_ret_Acoes_126)]),
    html.Div([dcc.Graph(figure=Graf_vol_Acoes_126)]), 
    
    html.H2(children='Janela de tempo de 252 dias'),
    html.Div([
        dash_table.DataTable(
            id='table1',
            columns=[{"name": i, "id": i, "type": "numeric"} for i in Acoes_252_Top10.columns],
            style_cell={'textAlign': 'center'},
            data=Acoes_252_Top10.to_dict('records'),
            )
        ]),
    html.Div([dcc.Graph(figure=Graf_ret_Acoes_252)]),
    html.Div([dcc.Graph(figure=Graf_vol_Acoes_252)]),
    
    html.H2(children='Janela de tempo de 504 dias'),
    html.Div([
        dash_table.DataTable(
            id='table2',
            columns=[{"name": i, "id": i, "type": "numeric"} for i in Acoes_504_Top10.columns],
            style_cell={'textAlign': 'center'},
            data=Acoes_504_Top10.to_dict('records'),
            )
        ]),
    html.Div([dcc.Graph(figure=Graf_ret_Acoes_504)]),
    html.Div([dcc.Graph(figure=Graf_vol_Acoes_504)]),
    
    html.H2(children='Janela de tempo de 756 dias'),
    html.Div([
        dash_table.DataTable(
            id='table3',
            columns=[{"name": i, "id": i, "type": "numeric"} for i in Acoes_756_Top10.columns],
            style_cell={'textAlign': 'center'},
            data=Acoes_756_Top10.to_dict('records'),
            )
        ]),
    html.Div([dcc.Graph(figure=Graf_ret_Acoes_756)]),
    html.Div([dcc.Graph(figure=Graf_vol_Acoes_756)]),
    
    html.H2(children='Pontuação final dos 10 melhores fundos'),
    html.Div([
        dash_table.DataTable(
            id='table4',
            columns=[{"name": i, "id": i, "type": "numeric"} for i in Acoes_Geral_Top10.columns],
            style_cell={'textAlign': 'center'},
            data=Acoes_Geral_Top10.to_dict('records'),
            )
        ])
    
])

# ======================================== Pagina dash dos Fundos Multimercados ===================================== #
page_3_layout = html.Div([
    html.H1('Relatório dos Fundos Multimercados',
        style={'textAlign':'center'}
        ),
    dcc.Link('Ir para os Fundos Renda Fixa', href='/page-1'),
    html.Br(),
    dcc.Link('Ir para os Fundos de Ações', href='/page-2'),
    html.Br(),
    dcc.Link('Retornar a página inicial', href='/'),
    html.Div(id='page-3-content'),   
    
    html.Div([dcc.Graph(figure=Graf_ind)]),
    
    html.H2(children='Janela de tempo de 126 dias'),
    html.Div([
        dash_table.DataTable(
            id='table',
            columns=[{"name": i, "id": i, "type": "numeric"} for i in Mult_126_Top10.columns],
            style_cell={'textAlign': 'center'},
            data=Mult_126_Top10.to_dict('records'),
            )
        ]),
    html.Div([dcc.Graph(figure=Graf_ret_mult_126)]),
    html.Div([dcc.Graph(figure=Graf_vol_mult_126)]), 
    
    html.H2(children='Janela de tempo de 252 dias'),
    html.Div([
        dash_table.DataTable(
            id='table1',
            columns=[{"name": i, "id": i, "type": "numeric"} for i in Mult_252_Top10.columns],
            style_cell={'textAlign': 'center'},
            data=Mult_252_Top10.to_dict('records'),
            )
        ]),
    html.Div([dcc.Graph(figure=Graf_ret_mult_252)]),
    html.Div([dcc.Graph(figure=Graf_vol_mult_252)]),
    
    html.H2(children='Janela de tempo de 504 dias'),
    html.Div([
        dash_table.DataTable(
            id='table2',
            columns=[{"name": i, "id": i, "type": "numeric"} for i in Mult_504_Top10.columns],
            style_cell={'textAlign': 'center'},
            data=Mult_504_Top10.to_dict('records'),
            )
        ]),
    html.Div([dcc.Graph(figure=Graf_ret_mult_504)]),
    html.Div([dcc.Graph(figure=Graf_vol_mult_504)]),
    
    html.H2(children='Janela de tempo de 756 dias'),
    html.Div([
        dash_table.DataTable(
            id='table3',
            columns=[{"name": i, "id": i, "type": "numeric"} for i in Mult_756_Top10.columns],
            style_cell={'textAlign': 'center'},
            data=Mult_756_Top10.to_dict('records'),
            )
        ]),
    html.Div([dcc.Graph(figure=Graf_ret_mult_756)]),
    html.Div([dcc.Graph(figure=Graf_vol_mult_756)]),
    
    html.H2(children='Pontuação final dos 10 melhores fundos'),
    html.Div([
        dash_table.DataTable(
            id='table4',
            columns=[{"name": i, "id": i, "type": "numeric"} for i in Mult_Geral_Top10.columns],
            style_cell={'textAlign': 'center'},
            data=Mult_Geral_Top10.to_dict('records'),
            )
        ])
    
])



# Update the index
@app.callback(dash.dependencies.Output('page-content', 'children'),
              [dash.dependencies.Input('url', 'pathname')])
def display_page(pathname):
    if pathname == '/page-1':
        return page_1_layout
    elif pathname == '/page-2':
        return page_2_layout
    elif pathname == '/page-3':
        return page_3_layout
    else:
        return index_page


if __name__ == '__main__':
    app.run_server(debug=False)
