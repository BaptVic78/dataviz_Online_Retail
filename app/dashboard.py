import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.io as pio

from utils import (
    load_data,
    compute_avg_purchase_frequency,
    compute_customer_lifespan,
    calculate_clv,
)

# ------------------------------------------------
#   CONFIG GLOBALE + PETIT CSS
# ------------------------------------------------

st.set_page_config(
    page_title="Dashboard Marketing",
    page_icon="📊",
    layout="wide",
)

# Un peu de style (cartes plus propres, titres)
st.markdown(
    """
    <style>
    .kpi-card {
        background-color: #1f2933;
        padding: 12px 16px;
        border-radius: 8px;
        border: 1px solid #3b4252;
    }
    .kpi-label {
        font-size: 0.8rem;
        color: #cbd5e1;
        text-transform: uppercase;
        letter-spacing: .05em;
    }
    .kpi-value {
        font-size: 1.4rem;
        font-weight: 600;
        color: #f9fafb;
    }
    .kpi-help {
        font-size: 0.7rem;
        color: #9ca3af;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def _kpi_block(label: str, value: str, help_text: str = ""):
    """Petit composant KPI custom pour avoir un look propre."""
    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{value}</div>
            <div class="kpi-help">{help_text}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ------------------------------------------------
#   FONCTION PRINCIPALE
# ------------------------------------------------

def show_dashboard():
    st.title("📊 Tableau de Bord Marketing")

    # ==========================
    # 1. Chargement des données
    # ==========================
    df = load_data()

    if df.empty:
        st.error("Impossible de charger les données.")
        return

    if "InvoiceDate" in df.columns:
        df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"])
        df["Month"] = df["InvoiceDate"].dt.to_period("M").astype(str)
        df["Quarter"] = (
            df["InvoiceDate"].dt.year.astype(str)
            + "Q"
            + df["InvoiceDate"].dt.quarter.astype(str)
        )
    else:
        st.error("La colonne 'InvoiceDate' est manquante.")
        return

    # ==========================
    # 2. FILTRES (sidebar)
    # ==========================

    with st.sidebar:
        st.header("🎛 Filtres d'analyse")

        min_date = df["InvoiceDate"].min().date()
        max_date = df["InvoiceDate"].max().date()

        start_date, end_date = st.date_input(
            "Période d'analyse",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
        )

        time_unit = st.radio("Unité de temps", ["Mois", "Trimestre"])

        countries = ["Tous"] + sorted(df["Country"].dropna().unique().tolist())
        country_choice = st.selectbox("Pays", countries)

        if "TotalPrice" in df.columns:
            max_total = float(df["TotalPrice"].quantile(0.95))
            order_threshold = st.slider(
                "Seuil minimum (€)",
                0.0,
                max_total,
                0.0,
                step=10.0,
            )
        else:
            order_threshold = 0.0

        returns_mode = st.radio(
            "Mode retours",
            ["Inclure", "Exclure", "Neutraliser"],
            index=0,
        )

    # ==========================
    # 3. Application des filtres
    # ==========================

    mask_date = (df["InvoiceDate"].dt.date >= start_date) & (
        df["InvoiceDate"].dt.date <= end_date
    )
    df_f = df.loc[mask_date].copy()

    if country_choice != "Tous":
        df_f = df_f[df_f["Country"] == country_choice]

    if "TotalPrice" in df_f.columns:
        df_f = df_f[df_f["TotalPrice"] >= order_threshold]

    # GESTION RETOURS
    if "Quantity" in df_f.columns:
        if returns_mode == "Exclure":
            df_f = df_f[df_f["Quantity"] > 0]

        elif returns_mode == "Neutraliser":
            df_f.loc[df_f["Quantity"] < 0, "TotalPrice"] = 0

    # BADGE
    if returns_mode != "Inclure":
        st.markdown(
            f"<span style='background:#FFCDD2;color:#B71C1C;padding:4px;border-radius:4px;'>Mode retours : {returns_mode}</span>",
            unsafe_allow_html=True,
        )

    # ==========================
    # 🔍 DEBUG RETOURS — Collé ici
    # ==========================

    n_retours_before = (df["Quantity"] < 0).sum()
    n_retours_after = (df_f["Quantity"] < 0).sum()

    with st.sidebar:
        st.markdown("### 🔍 Vérification Retours")
        st.write(f"Retours AVANT filtres : **{n_retours_before}**")
        st.write(f"Retours APRÈS filtres : **{n_retours_after}**")

    with st.expander("Voir les lignes de retours (debug)"):
        st.dataframe(df_f[df_f["Quantity"] < 0].head(20))

    if df_f.empty:
        st.warning("Aucune donnée après filtrage.")
        return

    # ==========================
    # 4. KPIs PRINCIPAUX
    # ==========================

    total_revenue = df_f["TotalPrice"].sum()
    n_customers = df_f["CustomerID"].nunique()
    n_orders = len(df_f)
    avg_order_value = total_revenue / n_orders if n_orders > 0 else 0

    freq = compute_avg_purchase_frequency(df_f)
    lifespan = compute_customer_lifespan(df_f)

    clv_baseline = calculate_clv(
        df_f,
        r=0.6,
        d=0.1,
        aov=avg_order_value,
        freq=freq,
        lifespan=lifespan,
        marge=30.0,
    )

    north_star = total_revenue / n_customers if n_customers > 0 else 0

    st.markdown("### 📌 KPIs - Vue d’ensemble")

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        _kpi_block("Clients actifs", f"{n_customers:,}")
    with c2:
        _kpi_block("CA total", f"{total_revenue:,.0f} €")
    with c3:
        _kpi_block("CLV baseline", f"{clv_baseline:,.2f} €")
    with c4:
        _kpi_block("North Star", f"{north_star:,.2f} €")

    st.markdown("---")

    # ==========================
    # 5. TENDANCES TEMPORELLES
    # ==========================

    st.subheader("📈 Tendances CA")

    time_col = "Month" if time_unit == "Mois" else "Quarter"

    rev_time = (
        df_f.groupby(time_col)["TotalPrice"]
        .sum()
        .reset_index()
        .sort_values(time_col)
    )

    fig_time = px.line(
        rev_time,
        x=time_col,
        y="TotalPrice",
        markers=True,
        title=f"CA par {time_unit}",
    )
    st.plotly_chart(fig_time, use_container_width=True)

    # ==========================
    # 6. CA PAR PAYS
    # ==========================

    st.subheader("🌍 Top pays par CA")

    rev_country = (
        df_f.groupby("Country")["TotalPrice"]
        .sum()
        .sort_values(ascending=False)
        .head(10)
        .reset_index()
    )

    fig_country = px.bar(
        rev_country,
        x="Country",
        y="TotalPrice",
        text_auto=True,
        title="Top 10 pays",
    )
    st.plotly_chart(fig_country, use_container_width=True)

    # ==========================
    # 7. RFM (si dispo)
    # ==========================

    st.subheader("🧩 Segments RFM")

    if "RFM_Segment" not in df_f.columns:
        st.info("Pas encore de segments RFM calculés.")
    else:
        rfm_agg = (
            df_f.groupby(["RFM_Segment", "CustomerID"])["TotalPrice"]
            .agg(["count", "sum", "mean"])
            .reset_index()
        )

        seg = (
            rfm_agg.groupby("RFM_Segment")[["count", "sum", "mean"]]
            .agg({"count": "sum", "sum": "sum", "mean": "mean"})
            .reset_index()
        )

        seg.columns = ["Segment", "Nb transactions", "CA", "Panier moyen"]

        fig_rfm = px.bar(
            seg,
            x="Segment",
            y="CA",
            text_auto=True,
            title="CA par segment RFM",
        )
        st.plotly_chart(fig_rfm, use_container_width=True)

        st.dataframe(seg, use_container_width=True)

    st.markdown("---")

    # ==========================
    # 8. EXPORTS
    # ==========================

    st.subheader("📦 Export – Plan d’action")

    activable = (
        df_f.groupby("CustomerID")
        .agg(
            {
                "TotalPrice": "sum",
                "InvoiceNo": "nunique",
                "Country": lambda x: x.mode().iloc[0],
                "RFM_Segment": lambda x: x.mode().iloc[0] if "RFM_Segment" in df_f.columns else "",
            }
        )
        .reset_index()
    )

    activable.rename(
        columns={
            "TotalPrice": "CA_période",
            "InvoiceNo": "Nb_commandes",
            "Country": "Pays principal",
            "RFM_Segment": "Segment RFM",
        },
        inplace=True,
    )

    activable["Valeur_client_estimee"] = activable["CA_période"] * 0.3

    st.dataframe(activable.head(40), use_container_width=True)

    csv_dl = activable.to_csv(index=False).encode("utf-8")

    st.download_button(
        "Télécharger CSV clients activables",
        csv_dl,
        "clients_activables.csv",
        "text/csv",
    )

    try:
        png_time = pio.to_image(fig_time, format="png")
        st.download_button(
            "Télécharger Courbe CA (PNG)",
            png_time,
            "courbe_CA.png",
            "image/png",
        )
    except:
        st.info("Installer `kaleido` pour exporter les graphiques.")


if __name__ == "__main__":
    show_dashboard()
