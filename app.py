import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

@st.cache_data
def load_data():
    df = pd.read_excel('Enterococcus_faecium_groupes_antibiotiques.xlsx')
    return df

def calculate_alerts(df, phenotype='ERV', window_size=8, z_score=1.96):
    if phenotype == 'ERV':
        df_pheno = df[df['Vancomycine'] == 'R']
        col_percent = 'percent_ERV'
    elif phenotype == 'Wild':
        df_pheno = df[(df['Vancomycine'] == 'S') & (df['Teicoplanine'] == 'S')]
        col_percent = 'percent_wild'
    else:
        raise ValueError("Phénotype inconnu")

    pheno_counts = df_pheno.groupby(['Numéro semaine', 'UF']).size().reset_index(name='nb_pheno')

    if phenotype == 'ERV':
        df_tested = df[df['Vancomycine'].isin(['R', 'S'])]
    else:
        df_tested = df[(df['Vancomycine'].isin(['R', 'S'])) & (df['Teicoplanine'].isin(['R', 'S']))]

    total_tested = df_tested.groupby(['Numéro semaine', 'UF']).size().reset_index(name='total_tested')

    df_merged = pd.merge(pheno_counts, total_tested, on=['Numéro semaine', 'UF'], how='left')

    df_merged[col_percent] = df_merged['nb_pheno'] / df_merged['total_tested'] * 100

    df_merged = df_merged.sort_values(['UF', 'Numéro semaine'])

    def rolling_alerts(group):
        group = group.copy()
        group['moving_avg'] = group[col_percent].rolling(window=window_size, center=True).mean()
        group['moving_std'] = group[col_percent].rolling(window=window_size, center=True).std()
        group['lower_bound'] = group['moving_avg'] - z_score * (group['moving_std'] / np.sqrt(window_size))
        group['upper_bound'] = group['moving_avg'] + z_score * (group['moving_std'] / np.sqrt(window_size))
        group['alert'] = (group[col_percent] < group['lower_bound']) | (group[col_percent] > group['upper_bound'])
        return group

    df_alerts = df_merged.groupby('UF').apply(rolling_alerts).reset_index(drop=True)
    return df_alerts

def calculate_vanco_resistance(df, window_size=8, z_score=1.96):
    df_vanco = df[df['Vancomycine'].isin(['R', 'S'])]

    counts = df_vanco.groupby('Numéro semaine')['Vancomycine'].value_counts().unstack(fill_value=0).reset_index()
    counts['total_tested'] = counts['R'] + counts['S']
    counts['percent_R'] = counts['R'] / counts['total_tested'] * 100

    counts = counts.sort_values('Numéro semaine')
    counts['moving_avg'] = counts['percent_R'].rolling(window=window_size, center=True).mean()
    counts['moving_std'] = counts['percent_R'].rolling(window=window_size, center=True).std()
    counts['lower_bound'] = counts['moving_avg'] - z_score * (counts['moving_std'] / np.sqrt(window_size))
    counts['upper_bound'] = counts['moving_avg'] + z_score * (counts['moving_std'] / np.sqrt(window_size))

    counts['alert'] = (counts['percent_R'] < counts['lower_bound']) | (counts['percent_R'] > counts['upper_bound'])

    return counts

def plot_phenotypes(df_erv, df_wild, weeks_range, phenotype_choice):
    df_erv = df_erv[(df_erv['Numéro semaine'] >= weeks_range[0]) & (df_erv['Numéro semaine'] <= weeks_range[1])]
    df_wild = df_wild[(df_wild['Numéro semaine'] >= weeks_range[0]) & (df_wild['Numéro semaine'] <= weeks_range[1])]

    fig = go.Figure()

    if phenotype_choice in ["Les deux", "Seulement ERV"]:
        df_erv_weekly = df_erv.groupby('Numéro semaine').agg({
            'percent_ERV': 'mean',
            'moving_avg': 'mean',
            'lower_bound': 'mean',
            'upper_bound': 'mean',
            'alert': 'max'
        }).reset_index()

        fig.add_trace(go.Scatter(
            x=df_erv_weekly['Numéro semaine'],
            y=df_erv_weekly['percent_ERV'],
            mode='lines+markers',
            name='% ERV',
            line=dict(color='blue', width=3),
            marker=dict(size=8),
            hovertemplate='Semaine %{x}<br>% ERV %{y:.2f}%'
        ))

        fig.add_trace(go.Scatter(
            x=df_erv_weekly['Numéro semaine'],
            y=df_erv_weekly['moving_avg'],
            mode='lines',
            name='Moyenne mobile ERV',
            line=dict(color='blue', width=2, dash='dash')
        ))

        fig.add_trace(go.Scatter(
            x=df_erv_weekly['Numéro semaine'],
            y=df_erv_weekly['lower_bound'],
            mode='lines',
            name='IC bas ERV',
            line=dict(color='lightblue', width=1, dash='dot')
        ))

        fig.add_trace(go.Scatter(
            x=df_erv_weekly['Numéro semaine'],
            y=df_erv_weekly['upper_bound'],
            mode='lines',
            name='IC haut ERV',
            line=dict(color='lightblue', width=1, dash='dot')
        ))

        alerts_erv = df_erv_weekly[df_erv_weekly['alert']]
        fig.add_trace(go.Scatter(
            x=alerts_erv['Numéro semaine'],
            y=alerts_erv['percent_ERV'],
            mode='markers',
            marker=dict(color='darkred', size=12),
            name='Alerte ERV',
            hovertemplate='Alerte ERV!<br>Semaine %{x}<br>% ERV %{y:.2f}%'
        ))

    if phenotype_choice in ["Les deux", "Seulement Wild type"]:
        df_wild_weekly = df_wild.groupby('Numéro semaine').agg({
            'percent_wild': 'mean',
            'moving_avg': 'mean',
            'lower_bound': 'mean',
            'upper_bound': 'mean',
            'alert': 'max'
        }).reset_index()

        fig.add_trace(go.Scatter(
            x=df_wild_weekly['Numéro semaine'],
            y=df_wild_weekly['percent_wild'],
            mode='lines+markers',
            name='% Wild type',
            line=dict(color='green', width=3),
            marker=dict(size=8),
            hovertemplate='Semaine %{x}<br>% Wild type %{y:.2f}%'
        ))

        fig.add_trace(go.Scatter(
            x=df_wild_weekly['Numéro semaine'],
            y=df_wild_weekly['moving_avg'],
            mode='lines',
            name='Moyenne mobile Wild',
            line=dict(color='green', width=2, dash='dash')
        ))

        fig.add_trace(go.Scatter(
            x=df_wild_weekly['Numéro semaine'],
            y=df_wild_weekly['lower_bound'],
            mode='lines',
            name='IC bas Wild',
            line=dict(color='lightgreen', width=1, dash='dot')
        ))

        fig.add_trace(go.Scatter(
            x=df_wild_weekly['Numéro semaine'],
            y=df_wild_weekly['upper_bound'],
            mode='lines',
            name='IC haut Wild',
            line=dict(color='lightgreen', width=1, dash='dot')
        ))

        alerts_wild = df_wild_weekly[df_wild_weekly['alert']]
        fig.add_trace(go.Scatter(
            x=alerts_wild['Numéro semaine'],
            y=alerts_wild['percent_wild'],
            mode='markers',
            marker=dict(color='darkred', size=12),
            name='Alerte Wild type',
            hovertemplate='Alerte Wild type!<br>Semaine %{x}<br>% Wild type %{y:.2f}%'
        ))

    fig.update_layout(
        title="Évolution hebdomadaire des % de phénotypes avec moyenne mobile et IC",
        xaxis_title="Numéro semaine",
        yaxis_title="% phénotypes",
        hovermode="closest"
    )

    st.plotly_chart(fig, use_container_width=True)

def plot_vanco_resistance(df_vanco_resistance, weeks_range):
    df_vanco_resistance = df_vanco_resistance[
        (df_vanco_resistance['Numéro semaine'] >= weeks_range[0]) & 
        (df_vanco_resistance['Numéro semaine'] <= weeks_range[1])
    ]

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df_vanco_resistance['Numéro semaine'],
        y=df_vanco_resistance['percent_R'],
        mode='lines+markers',
        name='% Résistance Vancomycine',
        line=dict(color='purple', width=3),
        marker=dict(size=8),
        hovertemplate='Semaine %{x}<br>% Résistance %{y:.2f}%'
    ))

    fig.add_trace(go.Scatter(
        x=df_vanco_resistance['Numéro semaine'],
        y=df_vanco_resistance['moving_avg'],
        mode='lines',
        name='Moyenne mobile',
        line=dict(color='purple', width=2, dash='dash')
    ))

    fig.add_trace(go.Scatter(
        x=df_vanco_resistance['Numéro semaine'],
        y=df_vanco_resistance['lower_bound'],
        mode='lines',
        name))
