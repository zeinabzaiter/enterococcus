import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(page_title="Dashboard ERV vs Wild (Exclusif)", layout="wide")

@st.cache_data
def load_raw_data(path: str) -> pd.DataFrame:
    """
    Charge le fichier brut contenant, pour chaque isolat, les colonnes :
      - Numéro semaine  (int)
      - UF              (service)
      - Vancomycine     ('R' ou 'S')
      - Teicoplanine    ('R' ou 'S')
      - ... (autres colonnes si besoin)
    """
    df = pd.read_excel(path)
    return df

@st.cache_data
def compute_weekly_exclusive(df_raw: pd.DataFrame, window_size: int = 8, z_score: float = 1.96) -> pd.DataFrame:
    """
    À partir du DataFrame brut, on :
      1. Crée deux colonnes booléennes is_ERV, is_Wild, de façon mutuellement exclusive :
         - ERV  = Vancomycine == 'R'
         - Wild = Vancomycine == 'S' AND Teicoplanine == 'S'
         (tout isolat qui n'est ni ERV ni Wild est filtré)
      2. Filtre le DataFrame pour ne conserver que les isolats ERV ou Wild.
      3. Groupe par 'Numéro semaine' pour compter :
         - total_exclusifs = nombre d'isolats cette semaine (ERV+Wild)
         - nb_ERV          = nombre d'isolats ERV cette semaine
         - nb_Wild         = nombre d'isolats Wild cette semaine
      4. Calcule les pourcentages exclusifs :
         - %_ERV_exclu  = nb_ERV  / total_exclusifs * 100
         - %_Wild_exclu = nb_Wild / total_exclusifs * 100
      5. Calcule la moyenne mobile centrée (window_size) et les bornes d'IC 95% pour chaque série
    Retourne un DataFrame avec colonnes :
      ['Semaine', 'total_exclusifs', 'nb_ERV', 'nb_Wild',
       '%_ERV_exclu', '%_Wild_exclu',
       'MA_ERV', 'LB_ERV', 'UB_ERV',
       'MA_Wild', 'LB_Wild', 'UB_Wild']
    """
    # 1. Ajouter indicateurs ERV / Wild (exclusifs)
    df = df_raw.copy()
    df['is_ERV']  = df['Vancomycine'] == 'R'
    df['is_Wild'] = (df['Vancomycine'] == 'S') & (df['Teicoplanine'] == 'S')

    # 2. Ne conserver que les isolats marqués ERV ou Wild
    df_exclu = df[df['is_ERV'] | df['is_Wild']].copy()

    # 3. Groupe par semaine
    résumé = df_exclu.groupby('Numéro semaine').agg(
        total_exclusifs = ('UF',      'count'),
        nb_ERV          = ('is_ERV',  'sum'),
        nb_Wild         = ('is_Wild', 'sum')
    ).reset_index().rename(columns={'Numéro semaine': 'Semaine'})

    # 4. Calculer pourcentages exclusifs
    résumé['%_ERV_exclu']  = résumé['nb_ERV']  / résumé['total_exclusifs'] * 100
    résumé['%_Wild_exclu'] = résumé['nb_Wild'] / résumé['total_exclusifs'] * 100
    résumé['%_ERV_exclu']  = résumé['%_ERV_exclu'].round(2)
    résumé['%_Wild_exclu'] = résumé['%_Wild_exclu'].round(2)

    # 5. Calcul des moyennes mobiles et bornes d'IC 95%
    # Pour ERV
    résumé['MA_ERV'] = résumé['%_ERV_exclu'].rolling(window=window_size, center=True).mean()
    std_erv = résumé['%_ERV_exclu'].rolling(window=window_size, center=True).std()
    margin_erv = z_score * (std_erv / np.sqrt(window_size))
    résumé['LB_ERV'] = résumé['MA_ERV'] - margin_erv
    résumé['UB_ERV'] = résumé['MA_ERV'] + margin_erv

    # Pour Wild
    résumé['MA_Wild'] = résumé['%_Wild_exclu'].rolling(window=window_size, center=True).mean()
    std_wild = résumé['%_Wild_exclu'].rolling(window=window_size, center=True).std()
    margin_wild = z_score * (std_wild / np.sqrt(window_size))
    résumé['LB_Wild'] = résumé['MA_Wild'] - margin_wild
    résumé['UB_Wild'] = résumé['MA_Wild'] + margin_wild

    # 6. Arrondir pour plus de lisibilité
    cols_to_round = ['MA_ERV', 'LB_ERV', 'UB_ERV', 'MA_Wild', 'LB_Wild', 'UB_Wild']
    résumé[cols_to_round] = résumé[cols_to_round].round(2)

    return résumé

def plot_exclusive_erv_wild(df: pd.DataFrame):
    """
    Trace un graphique Plotly avec :
      - %_ERV_exclu  (bleu)
      - MA_ERV       (bleu, tirets)
      - LB_ERV / UB_ERV (bleu clair, pointillés)
      - %_Wild_exclu (vert)
      - MA_Wild      (vert, tirets)
      - LB_Wild / UB_Wild (vert clair, pointillés)
      - Axe X = Semaine
      - Axe Y = % d’isolats (sur l’ensemble ERV+Wild, donc toujours total = 100%)
    Légendes raccourcies, mêmes tailles de police, et axe Y uniquement "%".
    """
    semaines = df['Semaine']

    fig = go.Figure()

    # % ERV exclusif
    fig.add_trace(go.Scatter(
        x=semaines,
        y=df['%_ERV_exclu'],
        mode='lines+markers',
        name='% ERV',
        line=dict(color='blue', width=3),
        marker=dict(size=8),
        hovertemplate='Semaine %{x}<br>% ERV %{y:.2f}%<extra></extra>'
    ))
    # Moyenne mobile ERV
    fig.add_trace(go.Scatter(
        x=semaines,
        y=df['MA_ERV'],
        mode='lines',
        name='Moyenne ERV',
        line=dict(color='blue', width=2, dash='dash'),
        hovertemplate='Semaine %{x}<br>Moyenne ERV %{y:.2f}%<extra></extra>'
    ))
    # IC bas ERV
    fig.add_trace(go.Scatter(
        x=semaines,
        y=df['LB_ERV'],
        mode='lines',
        name='IC bas ERV',
        line=dict(color='lightblue', width=1, dash='dot'),
        hovertemplate=None
    ))
    # IC haut ERV
    fig.add_trace(go.Scatter(
        x=semaines,
        y=df['UB_ERV'],
        mode='lines',
        name='IC haut ERV',
        line=dict(color='lightblue', width=1, dash='dot'),
        hovertemplate=None
    ))

    # % Wild exclusif
    fig.add_trace(go.Scatter(
        x=semaines,
        y=df['%_Wild_exclu'],
        mode='lines+markers',
        name='% Wild',
        line=dict(color='green', width=3),
        marker=dict(size=8),
        hovertemplate='Semaine %{x}<br>% Wild %{y:.2f}%<extra></extra>'
    ))
    # Moyenne mobile Wild
    fig.add_trace(go.Scatter(
        x=semaines,
        y=df['MA_Wild'],
        mode='lines',
        name='Moyenne Wild',
        line=dict(color='green', width=2, dash='dash'),
        hovertemplate='Semaine %{x}<br>Moyenne Wild %{y:.2f}%<extra></extra>'
    ))
    # IC bas Wild
    fig.add_trace(go.Scatter(
        x=semaines,
        y=df['LB_Wild'],
        mode='lines',
        name='IC bas Wild',
        line=dict(color='lightgreen', width=1, dash='dot'),
        hovertemplate=None
    ))
    # IC haut Wild
    fig.add_trace(go.Scatter(
        x=semaines,
        y=df['UB_Wild'],
        mode='lines',
        name='IC haut Wild',
        line=dict(color='lightgreen', width=1, dash='dot'),
        hovertemplate=None
    ))

    # Mise en forme du layout (titre supprimé)
    fig.update_layout(
        title=None,
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
        margin=dict(l=60, r=40, t=40, b=60),
        height=600
    )

    st.plotly_chart(fig, use_container_width=True)

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
        • Titres, axes et légendes en **Arial Black**, taille agrandie.  
        """
    )

    # 1. Charger le fichier brut des isolats
    df_raw = load_raw_data("Enterococcus_faecium_groupes_antibiotiques.xlsx")

    # 2. Calculer le résumé hebdomadaire exclusif (ERV vs Wild)
    df_weekly = compute_weekly_exclusive(df_raw, window_size=8, z_score=1.96)

    # 3. Afficher en sidebar quelques infos
    st.sidebar.header("Infos sur les données")
    st.sidebar.write(f"Nombre de semaines : {df_weekly.shape[0]}")
    st.sidebar.write(f"Semaine min : {int(df_weekly['Semaine'].min())}")
    st.sidebar.write(f"Semaine max : {int(df_weekly['Semaine'].max())}")
    st.sidebar.write(f"Total maximal d’isolats/semaine : {int(df_weekly['total_exclusifs'].max())}")

    # 4. Tracer le graphique
    plot_exclusive_erv_wild(df_weekly)

if __name__ == "__main__":
    main()
