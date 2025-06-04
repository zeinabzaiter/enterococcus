import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

@st.cache_data
def load_data_erv_wild():
    return pd.read_excel('Enterococcus_faecium_groupes_antibiotiques.xlsx')

@st.cache_data
def load_data_vanco():
    return pd.read_excel('weekly_vanco_alerts.xlsx')

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
            name='<b>% ERV</b>',
            line=dict(color='blue', width=3),
            marker=dict(size=8),
            hovertemplate='Semaine %{x}<br>% ERV %{y:.2f}%'
        ))

        fig.add_trace(go.Scatter(
            x=df_erv_weekly['Numéro semaine'],
            y=df_erv_weekly['moving_avg'],
            mode='lines',
            name='<b>Moyenne mobile ERV</b>',
            line=dict(color='blue', width=2, dash='dash')
        ))

        fig.add_trace(go.Scatter(
            x=df_erv_weekly['Numéro semaine'],
            y=df_erv_weekly['lower_bound'],
            mode='lines',
            name='<b>IC bas ERV</b>',
            line=dict(color='lightblue', width=1, dash='dot')
        ))

        fig.add_trace(go.Scatter(
            x=df_erv_weekly['Numéro semaine'],
            y=df_erv_weekly['upper_bound'],
            mode='lines',
            name='<b>IC haut ERV</b>',
            line=dict(color='lightblue', width=1, dash='dot')
        ))

        alerts_erv = df_erv_weekly[df_erv_weekly['alert']]
        fig.add_trace(go.Scatter(
            x=alerts_erv['Numéro semaine'],
            y=alerts_erv['percent_ERV'],
            mode='markers',
            marker=dict(color='darkred', size=12),
            name='<b>Alerte ERV</b>',
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
            name='<b>% Wild type</b>',
            line=dict(color='green', width=3),
            marker=dict(size=8),
            hovertemplate='Semaine %{x}<br>% Wild type %{y:.2f}%'
        ))

        fig.add_trace(go.Scatter(
            x=df_wild_weekly['Numéro semaine'],
            y=df_wild_weekly['moving_avg'],
            mode='lines',
            name='<b>Moyenne mobile Wild</b>',
            line=dict(color='green', width=2, dash='dash')
        ))

        fig.add_trace(go.Scatter(
            x=df_wild_weekly['Numéro semaine'],
            y=df_wild_weekly['lower_bound'],
            mode='lines',
            name='<b>IC bas Wild</b>',
            line=dict(color='lightgreen', width=1, dash='dot')
        ))

        fig.add_trace(go.Scatter(
            x=df_wild_weekly['Numéro semaine'],
            y=df_wild_weekly['upper_bound'],
            mode='lines',
            name='<b>IC haut Wild</b>',
            line=dict(color='lightgreen', width=1, dash='dot')
        ))

        alerts_wild = df_wild_weekly[df_wild_weekly['alert']]
        fig.add_trace(go.Scatter(
            x=alerts_wild['Numéro semaine'],
            y=alerts_wild['percent_wild'],
            mode='markers',
            marker=dict(color='darkred', size=12),
            name='<b>Alerte Wild type</b>',
            hovertemplate='Alerte Wild type!<br>Semaine %{x}<br>% Wild type %{y:.2f}%'
        ))

    # Mise en forme très visible : titre en gros, axes et légende en gras
    fig.update_layout(
        title=dict(
            text="Évolution hebdomadaire des % de phénotypes avec moyenne mobile et IC",
            font=dict(size=26, family="Arial Black")
        ),
        legend=dict(
            font=dict(size=20, family="Arial Black")
        ),
        xaxis=dict(
            title=dict(text="Numéro semaine", font=dict(size=22, family="Arial Black")),
            tickfont=dict(size=18, family="Arial Black")
        ),
        yaxis=dict(
            title=dict(text="% phénotypes", font=dict(size=22, family="Arial Black")),
            tickfont=dict(size=18, family="Arial Black")
        ),
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
        name='<b>% Résistance Vancomycine</b>',
        line=dict(color='purple', width=3),
        marker=dict(size=8),
        hovertemplate='Semaine %{x}<br>% Résistance %{y:.2f}%'
    ))

    fig.add_trace(go.Scatter(
        x=df_vanco_resistance['Numéro semaine'],
        y=df_vanco_resistance['moving_avg'],
        mode='lines',
        name='<b>Moyenne mobile</b>',
        line=dict(color='purple', width=2, dash='dash')
    ))

    fig.add_trace(go.Scatter(
        x=df_vanco_resistance['Numéro semaine'],
        y=df_vanco_resistance['lower_bound'],
        mode='lines',
        name='<b>IC bas</b>',
        line=dict(color='violet', width=1, dash='dot')
    ))

    fig.add_trace(go.Scatter(
        x=df_vanco_resistance['Numéro semaine'],
        y=df_vanco_resistance['upper_bound'],
        mode='lines',
        name='<b>IC haut</b>',
        line=dict(color='violet', width=1, dash='dot')
    ))

    alerts = df_vanco_resistance[df_vanco_resistance['alert']]
    fig.add_trace(go.Scatter(
        x=alerts['Numéro semaine'],
        y=alerts['percent_R'],
        mode='markers',
        marker=dict(color='darkred', size=12),
        name='<b>Alerte</b>',
        hovertemplate='Alerte!<br>Semaine %{x}<br>% Résistance %{y:.2f}%'
    ))

    # Mise en forme très visible pour Vancomycine
    fig.update_layout(
        title=dict(
            text="Évolution hebdomadaire du % de résistance à la Vancomycine",
            font=dict(size=26, family="Arial Black")
        ),
        legend=dict(
            font=dict(size=20, family="Arial Black")
        ),
        xaxis=dict(
            title=dict(text="Numéro semaine", font=dict(size=22, family="Arial Black")),
            tickfont=dict(size=18, family="Arial Black")
        ),
        yaxis=dict(
            title=dict(text="% Résistance", font=dict(size=22, family="Arial Black")),
            tickfont=dict(size=18, family="Arial Black")
        ),
        hovermode="closest"
    )

    st.plotly_chart(fig, use_container_width=True)

def main():
    st.title("Dashboard Enterococcus faecium")

    page = st.sidebar.selectbox("Choisir la page", ["ERV + Wild", "Vancomycine"])

    if page == "ERV + Wild":
        df = load_data_erv_wild()

        df_alerts_erv = calculate_alerts(df, phenotype='ERV')
        df_alerts_wild = calculate_alerts(df, phenotype='Wild')

        weeks = sorted(df['Numéro semaine'].unique())
        min_week, max_week = min(weeks), max(weeks)
        selected_weeks = st.sidebar.slider("Choisir plage de semaines", min_week, max_week, (min_week, max_week))

        phenotype_choice = st.sidebar.selectbox(
            "Choisir phénotype à afficher",
            options=["Les deux", "Seulement ERV", "Seulement Wild type"],
            index=0
        )

        plot_phenotypes(df_alerts_erv, df_alerts_wild, selected_weeks, phenotype_choice)

        st.header("Alertes détectées")
        combined_alerts = pd.concat([
            df_alerts_erv[df_alerts_erv['alert']][['Numéro semaine', 'UF', 'percent_ERV']].assign(Phénotype='ERV'),
            df_alerts_wild[df_alerts_wild['alert']][['Numéro semaine', 'UF', 'percent_wild']].assign(Phénotype='Wild')
        ])

        combined_alerts = combined_alerts.rename(columns={'percent_ERV': '% ERV', 'percent_wild': '% Wild type'})
        combined_alerts = combined_alerts.sort_values(['Numéro semaine', 'UF'])

        combined_alerts = combined_alerts[
            (combined_alerts['Numéro semaine'] >= selected_weeks[0]) & (combined_alerts['Numéro semaine'] <= selected_weeks[1])
        ]

        if combined_alerts.empty:
            st.write("Aucune alerte détectée pour cette plage de semaines.")
        else:
            st.dataframe(combined_alerts)

    elif page == "Vancomycine":
        df_vanco = load_data_vanco()

        min_week = int(df_vanco['Numéro semaine'].min())
        max_week = int(df_vanco['Numéro semaine'].max())
        selected_weeks = st.sidebar.slider("Choisir plage de semaines", min_week, max_week, (min_week, max_week))

        st.header("Données Vancomycine")
        st.dataframe(df_vanco[(df_vanco['Numéro semaine'] >= selected_weeks[0]) & (df_vanco['Numéro semaine'] <= selected_weeks[1])])

        plot_vanco_resistance(df_vanco, selected_weeks)

if __name__ == "__main__":
    main()
