import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(page_title="Dashboard ERV vs Wild (Exclusif)", layout="wide")

@st.cache_data
def load_raw_data(path: str) -> pd.DataFrame:
    """
    Charge le fichier brut contenant, pour chaque isolat, au minimum les colonnes :
      - Numéro semaine  (int)
      - UF              (service)
      - Vancomycine     ('R' ou 'S')
      - Teicoplanine    ('R' ou 'S')
    """
    return pd.read_excel(path)

@st.cache_data
def compute_weekly_exclusive_and_uf_alerts(
    df_raw: pd.DataFrame, window_size: int = 8, z_score: float = 1.96
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    1. On crée deux indicateurs booléens mutuellement exclusifs :
       - is_ERV  = Vancomycine == 'R'
       - is_Wild = Vancomycine == 'S' AND Teicoplanine == 'S'
       On ne garde que ces isolats (ERV ou Wild).
    2. On agrège par semaine pour obtenir le résumé global (ERV+Wild) :
       - total_exclusifs, nb_ERV, nb_Wild
       - calcul des % exclusifs de ERV et Wild
       - moyenne mobile centrée + IC 95 % (fenêtre = window_size)
    3. On agrège par (semaine, UF) pour calculer, **pour chaque UF**, le % ERV:
       - total_uf, nb_ERV_uf → percent_ERV_uf
       - on calcule la moyenne mobile et IC 95 % **par UF**
       - on marque alert_uf = True si percent_ERV_uf < LB_uf ou > UB_uf
    4. On retourne :
       - résumé : DataFrame hebdo exclusif (colonnes Semaine, total_exclusifs, nb_ERV, nb_Wild,
                   %_ERV_exclu, %_Wild_exclu, MA_ERV, LB_ERV, UB_ERV, MA_Wild, LB_Wild, UB_Wild)
       - alerts_uf_df : DataFrame des alertes ERV par UF (colonnes Semaine, UF, percent_ERV_uf)
    """
    df = df_raw.copy()
    df['is_ERV']  = df['Vancomycine'] == 'R'
    df['is_Wild'] = (df['Vancomycine'] == 'S') & (df['Teicoplanine'] == 'S')

    # Filtrer pour ne garder que ERV ou Wild
    df_exclu = df[df['is_ERV'] | df['is_Wild']].copy()

    # ----------------------------------------
    # 1) Calcul du résumé hebdomadaire global
    # ----------------------------------------
    résumé = (
        df_exclu
        .groupby('Numéro semaine')
        .agg(
            total_exclusifs=('UF', 'count'),
            nb_ERV         =('is_ERV', 'sum'),
            nb_Wild        =('is_Wild', 'sum')
        )
        .reset_index()
        .rename(columns={'Numéro semaine': 'Semaine'})
    )

    résumé['%_ERV_exclu']  = (résumé['nb_ERV']         / résumé['total_exclusifs'] * 100).round(2)
    résumé['%_Wild_exclu'] = (résumé['nb_Wild']        / résumé['total_exclusifs'] * 100).round(2)

    # Moyenne mobile + IC 95 % pour ERV (global)
    résumé['MA_ERV'] = résumé['%_ERV_exclu'].rolling(window=window_size, center=True).mean()
    std_erv         = résumé['%_ERV_exclu'].rolling(window=window_size, center=True).std()
    margin_erv      = z_score * (std_erv / np.sqrt(window_size))
    résumé['LB_ERV'] = (résumé['MA_ERV'] - margin_erv).round(2)
    résumé['UB_ERV'] = (résumé['MA_ERV'] + margin_erv).round(2)

    # Moyenne mobile + IC 95 % pour Wild (global)
    résumé['MA_Wild'] = résumé['%_Wild_exclu'].rolling(window=window_size, center=True).mean()
    std_wild         = résumé['%_Wild_exclu'].rolling(window=window_size, center=True).std()
    margin_wild      = z_score * (std_wild / np.sqrt(window_size))
    résumé['LB_Wild'] = (résumé['MA_Wild'] - margin_wild).round(2)
    résumé['UB_Wild'] = (résumé['MA_Wild'] + margin_wild).round(2)

    # ----------------------------------------
    # 2) Calcul des alertes ERV par UF
    # ----------------------------------------
    # Agréger par semaine+UF pour calculer percent_ERV_uf
    df_uf = (
        df_exclu
        .groupby(['Numéro semaine', 'UF'])
        .agg(
            total_uf=('UF',    'count'),
            nb_ERV_uf=('is_ERV', 'sum')
        )
        .reset_index()
        .rename(columns={'Numéro semaine': 'Semaine'})
    )
    df_uf['percent_ERV_uf'] = (df_uf['nb_ERV_uf'] / df_uf['total_uf'] * 100).round(2)

    # On calcule la moyenne mobile + IC 95 % pour chaque UF séparément
    df_uf = df_uf.sort_values(['UF', 'Semaine'])
    def rolling_uf(group):
        grp = group.copy()
        grp['MA_ERV_uf'] = grp['percent_ERV_uf'].rolling(window=window_size, center=True).mean()
        grp['STD_ERV_uf'] = grp['percent_ERV_uf'].rolling(window=window_size, center=True).std()
        grp['LB_ERV_uf']  = grp['MA_ERV_uf'] - z_score * (grp['STD_ERV_uf'] / np.sqrt(window_size))
        grp['UB_ERV_uf']  = grp['MA_ERV_uf'] + z_score * (grp['STD_ERV_uf'] / np.sqrt(window_size))
        # Marquer une alerte si le %_ERV_uf est en dehors des bornes IC
        grp['alert_uf'] = (grp['percent_ERV_uf'] < grp['LB_ERV_uf']) | (grp['percent_ERV_uf'] > grp['UB_ERV_uf'])
        return grp

    df_uf_alerts = df_uf.groupby('UF').apply(rolling_uf).reset_index(drop=True)

    # On récupère uniquement les lignes où alert_uf == True
    alerts_uf_df = df_uf_alerts[df_uf_alerts['alert_uf']][['Semaine', 'UF', 'percent_ERV_uf']]
    alerts_uf_df = alerts_uf_df.rename(columns={'percent_ERV_uf': '% ERV (UF)'})

    return résumé, alerts_uf_df

def plot_exclusive_erv_wild_and_show_alerts(
    df_summary: pd.DataFrame, alerts_uf_df: pd.DataFrame
):
    """
    1) Trace le graphique global hebdomadaire : % ERV vs % Wild + moyennes et IC
       Ajoute en rouge les points d'alerte sur % ERV (global).
    2) Affiche un tableau (Streamlit) des alertes ERV par UF :
       colonnes : Semaine | UF | % ERV (UF)
    """
    semaines = df_summary['Semaine']

    # Points d’alerte ERV global (hors IC 95 % globale)
    df_alert_erv = df_summary[
        (df_summary['%_ERV_exclu'] > df_summary['UB_ERV']) |
        (df_summary['%_ERV_exclu'] < df_summary['LB_ERV'])
    ]

    fig = go.Figure()

    # % ERV global
    fig.add_trace(go.Scatter(
        x=semaines,
        y=df_summary['%_ERV_exclu'],
        mode='lines+markers',
        name='% ERV',
        line=dict(color='blue', width=3),
        marker=dict(size=8),
        hovertemplate='Semaine %{x}<br>% ERV %{y:.2f}%<extra></extra>'
    ))
    # Moyenne mobile ERV global
    fig.add_trace(go.Scatter(
        x=semaines,
        y=df_summary['MA_ERV'],
        mode='lines',
        name='Moyenne ERV',
        line=dict(color='blue', width=2, dash='dash'),
        hovertemplate='Semaine %{x}<br>Moyenne ERV %{y:.2f}%<extra></extra>'
    ))
    # IC bas ERV global
    fig.add_trace(go.Scatter(
        x=semaines,
        y=df_summary['LB_ERV'],
        mode='lines',
        name='IC bas ERV',
        line=dict(color='lightblue', width=1, dash='dot'),
        hovertemplate=None
    ))
    # IC haut ERV global
    fig.add_trace(go.Scatter(
        x=semaines,
        y=df_summary['UB_ERV'],
        mode='lines',
        name='IC haut ERV',
        line=dict(color='lightblue', width=1, dash='dot'),
        hovertemplate=None
    ))
    # Points d'alerte ERV global (rouge)
    fig.add_trace(go.Scatter(
        x=df_alert_erv['Semaine'],
        y=df_alert_erv['%_ERV_exclu'],
        mode='markers',
        name='Alerte ERV',
        marker=dict(color='red', size=12),
        hovertemplate='ALERTE ERV !<br>Semaine %{x}<br>% ERV %{y:.2f}%<extra></extra>'
    ))

    # % Wild global
    fig.add_trace(go.Scatter(
        x=semaines,
        y=df_summary['%_Wild_exclu'],
        mode='lines+markers',
        name='% Wild',
        line=dict(color='green', width=3),
        marker=dict(size=8),
        hovertemplate='Semaine %{x}<br>% Wild %{y:.2f}%<extra></extra>'
    ))
    # Moyenne mobile Wild global
    fig.add_trace(go.Scatter(
        x=semaines,
        y=df_summary['MA_Wild'],
        mode='lines',
        name='Moyenne Wild',
        line=dict(color='green', width=2, dash='dash'),
        hovertemplate='Semaine %{x}<br>Moyenne Wild %{y:.2f}%<extra></extra>'
    ))
    # IC bas Wild global
    fig.add_trace(go.Scatter(
        x=semaines,
        y=df_summary['LB_Wild'],
        mode='lines',
        name='IC bas Wild',
        line=dict(color='lightgreen', width=1, dash='dot'),
        hovertemplate=None
    ))
    # IC haut Wild global
    fig.add_trace(go.Scatter(
        x=semaines,
        y=df_summary['UB_Wild'],
        mode='lines',
        name='IC haut Wild',
        line=dict(color='lightgreen', width=1, dash='dot'),
        hovertemplate=None
    ))

    # Mise en forme du layout
    fig.update_layout(
        title=dict(
            text="Répartition hebdo exclusive : % ERV vs % Wild (fenêtre 8, IC 95 %)",
            font=dict(size=26, family="Arial Black")
        ),
        legend=dict(
            font=dict(size=18, family="Arial Black"),
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        xaxis=dict(
            title=dict(text="Numéro semaine", font=dict(size=22, family="Arial Black")),
            tickfont=dict(size=18, family="Arial Black"),
            range=[semaines.min(), semaines.max()]
        ),
        yaxis=dict(
            title=dict(text="%", font=dict(size=22, family="Arial Black")),
            tickfont=dict(size=18, family="Arial Black"),
            range=[0, 100]
        ),
        hovermode="x unified",
        margin=dict(l=60, r=40, t=100, b=60),
        height=600
    )

    # Afficher le graphique
    st.plotly_chart(fig, use_container_width=True)

    # -------------------------------------------------------
    # Afficher le tableau des alertes ERV par UF en-dessous
    # -------------------------------------------------------
    st.subheader("🛎️ Alertes ERV par UF (semaine + UF + % ERV)")
    if alerts_uf_df.empty:
        st.write("Aucune alerte ERV détectée sur la période.")
    else:
        # On trie par semaine croissante puis par UF
        alerts_sorted = alerts_uf_df.sort_values(['Semaine', 'UF']).reset_index(drop=True)
        st.dataframe(alerts_sorted, use_container_width=True)
        # Option pour télécharger ce tableau au format CSV
        csv_data = alerts_sorted.to_csv(index=False)
        st.download_button(
            label="📥 Télécharger les alertes ERV par UF en CSV",
            data=csv_data,
            file_name="alertes_ERV_par_UF.csv",
            mime="text/csv"
        )

def main():
    st.title("📊 Dashboard exclusif ERV vs Wild")

    st.markdown(
        """
        Ce dashboard regroupe chaque semaine uniquement les isolats **ERV** (Vancomycine = R) 
        et les isolats **Wild type** (Vancomycine = S et Teicoplanine = S).  
        Tout isolat qui n'est ni ERV ni Wild est exclu.  

        • `% ERV` + `% Wild` font toujours 100 % chaque semaine,  
        • Moyenne mobile centrée (fenêtre de 8 semaines),  
        • Bornes d’IC 95 %,  
        • Points d'alerte ERV en rouge lorsque le % ERV sort de l'IC 95 %,  
        • Titres, axes et légendes en **Arial Black**, taille agrandie.  
        """
    )

    # 1. Charger le fichier brut des isolats
    df_raw = load_raw_data("Enterococcus_faecium_groupes_antibiotiques.xlsx")

    # 2. Calculer résumé + alertes UF
    df_summary, alerts_uf_df = compute_weekly_exclusive_and_uf_alerts(
        df_raw,
        window_size=8,
        z_score=1.96
    )

    # 3. Afficher en sidebar quelques infos
    st.sidebar.header("Infos sur les données")
    st.sidebar.write(f"Nombre de semaines : {df_summary.shape[0]}")
    st.sidebar.write(f"Semaine min : {int(df_summary['Semaine'].min())}")
    st.sidebar.write(f"Semaine max : {int(df_summary['Semaine'].max())}")
    st.sidebar.write(f"Total maximal d’isolats/semaine : {int(df_summary['total_exclusifs'].max())}")

    # 4. Tracer graphique + tableau alertes
    plot_exclusive_erv_wild_and_show_alerts(df_summary, alerts_uf_df)

if __name__ == "__main__":
    main()
