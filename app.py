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

# Fonctions calcul et plot pour ERV + Wild (à adapter / copier depuis ton code)
def calculate_alerts(df, phenotype='ERV', window_size=8, z_score=1.96):
    # ... même fonction que précédemment ...

def plot_phenotypes(df_erv, df_wild, weeks_range, phenotype_choice):
    # ... même fonction que précédemment ...

# Fonctions calcul et plot pour Vancomycine
def plot_vanco_resistance(df_vanco_resistance, weeks_range):
    # ... même fonction que précédemment ...

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
