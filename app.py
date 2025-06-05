import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# --------------------------------------------------------------------------
# Ce Streamlit app lit le fichier Excel « weekly_with_thresholds.xlsx »
# (contenant pour chaque semaine : %_ERV, MA_ERV, LB_ERV, UB_ERV,
#                                     %_Wild, MA_Wild, LB_Wild, UB_Wild)
# et affiche, sur un seul graphique Plotly, la courbe hebdomadaire de
# % ERV et % Wild ainsi que leurs moyennes mobiles et bornes d’IC.
# --------------------------------------------------------------------------

st.set_page_config(page_title="Dashboard ERV vs Wild", layout="wide")

@st.cache_data
def load_weekly_data(path: str) -> pd.DataFrame:
    """
    Charge le fichier Excel contenant les colonnes suivantes, par ordre :
      - Semaine               (int)
      - total_isolats         (int)
      - nb_ERV                (int)
      - nb_Wild               (int)
      - %_ERV                 (float)
      - %_Wild                (float)
      - MA_ERV                (float)
      - LB_ERV                (float)
      - UB_ERV                (float)
      - MA_Wild               (float)
      - LB_Wild               (float)
      - UB_Wild               (float)
    """
    df = pd.read_excel(path)
    return df

def plot_erv_wild_with_thresholds(df: pd.DataFrame):
    """
    Construit un graphique Plotly où :
      - l'axe X (Numéro semaine) va de min(df['Semaine']) à max(df['Semaine'])
      - l'axe Y affiche les pourcentages pour ERV et Wild, avec :
          • %_ERV en bleu (courbe pleine + marqueurs)
          • Moyenne mobile ERV en bleu (trait en tirets)
          • Bornes IC bas/haut ERV en bleu clair (traits pointillés)
          • %_Wild en vert (courbe pleine + marqueurs)
          • Moyenne mobile Wild en vert (trait en tirets)
          • Bornes IC bas/haut Wild en vert clair (traits pointillés)
      - les libellés (titres, légende, axes) sont très visibles (Arial Black, polices agrandies)
    """
    semaines = df["Semaine"]

    fig = go.Figure()

    # -- Traces pour ERV --
    fig.add_trace(go.Scatter(
        x=semaines,
        y=df["%_ERV"],
        mode='lines+markers',
        name='<b>% ERV</b>',
        line=dict(color='blue', width=3),
        marker=dict(size=8),
        hovertemplate='Semaine %{x}<br>% ERV %{y:.2f}%<extra></extra>'
    ))
    fig.add_trace(go.Scatter(
        x=semaines,
        y=df["MA_ERV"],
        mode='lines',
        name='<b>Moyenne mobile ERV</b>',
        line=dict(color='blue', width=2, dash='dash'),
        hovertemplate='Semaine %{x}<br>Moyenne mobile ERV %{y:.2f}%<extra></extra>'
    ))
    fig.add_trace(go.Scatter(
        x=semaines,
        y=df["LB_ERV"],
        mode='lines',
        name='<b>IC bas ERV</b>',
        line=dict(color='lightblue', width=1, dash='dot'),
        hovertemplate=None,
        showlegend=True
    ))
    fig.add_trace(go.Scatter(
        x=semaines,
        y=df["UB_ERV"],
        mode='lines',
        name='<b>IC haut ERV</b>',
        line=dict(color='lightblue', width=1, dash='dot'),
        hovertemplate=None,
        showlegend=True
    ))

    # -- Traces pour Wild type --
    fig.add_trace(go.Scatter(
        x=semaines,
        y=df["%_Wild"],
        mode='lines+markers',
        name='<b>% Wild type</b>',
        line=dict(color='green', width=3),
        marker=dict(size=8),
        hovertemplate='Semaine %{x}<br>% Wild %{y:.2f}%<extra></extra>'
    ))
    fig.add_trace(go.Scatter(
        x=semaines,
        y=df["MA_Wild"],
        mode='lines',
        name='<b>Moyenne mobile Wild</b>',
        line=dict(color='green', width=2, dash='dash'),
        hovertemplate='Semaine %{x}<br>Moyenne mobile Wild %{y:.2f}%<extra></extra>'
    ))
    fig.add_trace(go.Scatter(
        x=semaines,
        y=df["LB_Wild"],
        mode='lines',
        name='<b>IC bas Wild</b>',
        line=dict(color='lightgreen', width=1, dash='dot'),
        hovertemplate=None,
        showlegend=True
    ))
    fig.add_trace(go.Scatter(
        x=semaines,
        y=df["UB_Wild"],
        mode='lines',
        name='<b>IC haut Wild</b>',
        line=dict(color='lightgreen', width=1, dash='dot'),
        hovertemplate=None,
        showlegend=True
    ))

    # -- Mise à jour du layout pour avoir des textes très visibles --
    fig.update_layout(
        title=dict(
            text="Évolution hebdomadaire : % ERV vs % Wild avec seuils",
            font=dict(size=26, family="Arial Black")
        ),
        legend=dict(
            font=dict(size=20, family="Arial Black"),
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
            title=dict(text="% d’isolats", font=dict(size=22, family="Arial Black")),
            tickfont=dict(size=18, family="Arial Black"),
            rangemode="tozero"
        ),
        hovermode="x unified",
        margin=dict(l=60, r=40, t=100, b=60),
        height=600
    )

    st.plotly_chart(fig, use_container_width=True)

def main():
    st.title("📊 Dashboard hebdomadaire : ERV vs Wild")

    st.markdown(
        """
        Ce dashboard affiche, pour chaque semaine, le pourcentage d’isolats Enterococcus faecium :
        - **% ERV** (résistants à la vancomycine)  
        - **% Wild type** (sensibles à la vancomycine *et* à la téicoplanine)  

        Pour chaque série, on superpose :
        1. La courbe principale (% ERV / % Wild)  
        2. La moyenne mobile centrée (fenêtre 8)  
        3. Les bornes d’intervalle de confiance à 95 % (IC bas / IC haut).  
        """
    )

    # Charge le DataFrame pré-calculé
    df_weekly = load_weekly_data("weekly_with_thresholds.xlsx")

    # Feuille d’information rapide
    st.sidebar.header("Infos données")
    st.sidebar.write(f"Nombre de semaines : {df_weekly.shape[0]}")
    st.sidebar.write(f"Semaine min : {int(df_weekly['Semaine'].min())}")
    st.sidebar.write(f"Semaine max : {int(df_weekly['Semaine'].max())}")

    # Affiche le graphique principal
    plot_erv_wild_with_thresholds(df_weekly)

    st.sidebar.markdown("---")
    st.sidebar.markdown(
        "⚠️ **Vérifiez** que le fichier `weekly_with_thresholds.xlsx` "
        "est présent dans le même dossier que `app.py`.\n\n"
        "Si vous n’avez que `weekly_summary.xlsx`, exécutez d’abord le script "
        "de calcul des seuils (moyenne mobile + IC) pour générer `weekly_with_thresholds.xlsx`."
    )

if __name__ == "__main__":
    main()
