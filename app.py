import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

@st.cache_data
def load_data():
    df = pd.read_excel('Enterococcus_faecium_groupes_antibiotiques.xlsx')
    return df

def calculate_alerts(df, phenotype='ERV', window_size=8, z_score=1.96):
    # Filtrer phenotype
    if phenotype == 'ERV':
        df_pheno = df[df['Vancomycine'] == 'R']
        col_percent = 'percent_ERV'
    elif phenotype == 'Wild':
        df_pheno = df[(df['Vancomycine'] == 'S') & (df['Teicoplanine'] == 'S')]
        col_percent = 'percent_wild'
    else:
        raise ValueError("Phénotype inconnu")

    # Compter nb phenotype par semaine et UF
    pheno_counts = df_pheno.groupby(['Numéro semaine', 'UF']).size().reset_index(name='nb_pheno')

    # Compter total testés (R ou S) sur Vancomycine et Teicoplanine selon phenotype
    if phenotype == 'ERV':
        df_tested = df[df['Vancomycine'].isin(['R', 'S'])]
    else:
        df_tested = df[(df['Vancomycine'].isin(['R', 'S'])) & (df['Teicoplanine'].isin(['R', 'S']))]

    total_tested = df_tested.groupby(['Numéro semaine', 'UF']).size().reset_index(name='total_tested')

    # Fusionner
    df_merged = pd.merge(pheno_counts, total_tested, on=['Numéro semaine', 'UF'], how='left')

    # Calcul % phenotype
    df_merged[col_percent] = df_merged['nb_pheno'] / df_merged['total_tested'] * 100

    # Trier par UF et semaine
    df_merged = df_merged.sort_values(['UF', 'Numéro semaine'])

    # Calcul rolling + IC + alert
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

def plot_phenotypes(df_erv, df_wild, weeks_range):
    # Filtrer sur la plage de semaines
    df_erv = df_erv[(df_erv['Numéro semaine'] >= weeks_range[0]) & (df_erv['Numéro semaine'] <= weeks_range[1])]
    df_wild = df_wild[(df_wild['Numéro semaine'] >= weeks_range[0]) & (df_wild['Numéro semaine'] <= weeks_range[1])]

    # Agréger par semaine (moyenne sur UF)
    df_erv_weekly = df_erv.groupby('Numéro semaine').agg({
        'percent_ERV': 'mean',
        'alert': 'max'
    }).reset_index()

    df_wild_weekly = df_wild.groupby('Numéro semaine').agg({
        'percent_wild': 'mean',
        'alert': 'max'
    }).reset_index()

    fig = go.Figure()

    # % ERV
    fig.add_trace(go.Scatter(
        x=df_erv_weekly['Numéro semaine'],
        y=df_erv_weekly['percent_ERV'],
        mode='lines+markers',
        name='% ERV',
        hovertemplate='Semaine %{x}<br>% ERV %{y:.2f}%'
    ))

    # Alertes ERV
    alerts_erv = df_erv_weekly[df_erv_weekly['alert']]
    fig.add_trace(go.Scatter(
        x=alerts_erv['Numéro semaine'],
        y=alerts_erv['percent_ERV'],
        mode='markers',
        marker=dict(color='darkred', size=10),
        name='Alerte ERV',
        hovertemplate='Alerte ERV!<br>Semaine %{x}<br>% ERV %{y:.2f}%'
    ))

    # % Wild type
    fig.add_trace(go.Scatter(
        x=df_wild_weekly['Numéro semaine'],
        y=df_wild_weekly['percent_wild'],
        mode='lines+markers',
        name='% Wild type',
        hovertemplate='Semaine %{x}<br>% Wild type %{y:.2f}%'
    ))

    # Alertes Wild type
    alerts_wild = df_wild_weekly[df_wild_weekly['alert']]
    fig.add_trace(go.Scatter(
        x=alerts_wild['Numéro semaine'],
        y=alerts_wild['percent_wild'],
        mode='markers',
        marker=dict(color='darkblue', size=10),
        name='Alerte Wild type',
        hovertemplate='Alerte Wild type!<br>Semaine %{x}<br>% Wild type %{y:.2f}%'
    ))

    fig.update_layout(
        title="Évolution hebdomadaire des % de phénotypes",
        xaxis_title="Numéro semaine",
        yaxis_title="% phénotypes",
        hovermode="closest"
    )

    st.plotly_chart(fig, use_container_width=True)

def main():
    st.title("Dashboard Résistance Enterococcus faecium")

    df = load_data()

    # Calcul alertes
    df_alerts_erv = calculate_alerts(df, phenotype='ERV')
    df_alerts_wild = calculate_alerts(df, phenotype='Wild')

    # Filtre semaine
    weeks = sorted(df['Numéro semaine'].unique())
    min_week, max_week = min(weeks), max(weeks)
    selected_weeks = st.sidebar.slider("Choisir plage de semaines", min_week, max_week, (min_week, max_week))

    # Afficher graphique
    plot_phenotypes(df_alerts_erv, df_alerts_wild, selected_weeks)

    # Afficher tableau alertes
    st.header("Alertes détectées")
    combined_alerts = pd.concat([
        df_alerts_erv[df_alerts_erv['alert']][['Numéro semaine', 'UF', 'percent_ERV']].assign(Phénotype='ERV'),
        df_alerts_wild[df_alerts_wild['alert']][['Numéro semaine', 'UF', 'percent_wild']].assign(Phénotype='Wild')
    ])

    combined_alerts = combined_alerts.rename(columns={'percent_ERV': '% ERV', 'percent_wild': '% Wild type'})
    combined_alerts = combined_alerts.sort_values(['Numéro semaine', 'UF'])

    # Filtrer sur la plage de semaines sélectionnée
    combined_alerts = combined_alerts[
        (combined_alerts['Numéro semaine'] >= selected_weeks[0]) & (combined_alerts['Numéro semaine'] <= selected_weeks[1])
    ]

    if combined_alerts.empty:
        st.write("Aucune alerte détectée pour cette plage de semaines.")
    else:
        st.dataframe(combined_alerts)

if __name__ == "__main__":
    main()
