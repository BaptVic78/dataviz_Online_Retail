import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

@st.cache_data
def load_data():
    df = pd.read_parquet("data/processed/online_retail_rca.parquet")
    return df

@st.cache_data
def compute_cohort_matrix(df):
    cohort_counts = df.groupby(['Cohort', 'CohortIndex'])['Customer ID'].nunique()
    cohort_counts_df = cohort_counts.to_frame().rename(columns={'Customer ID' : 'Total Customers'}).sort_values(by='Total Customers', ascending=False)
    cohort_counts_df['retention_rate'] = cohort_counts_df['Total Customers'] / cohort_counts_df.groupby(['Cohort'])['Total Customers'].transform('max')
    cohorts_pivot = cohort_counts_df.pivot_table(index='Cohort', columns='CohortIndex', values='retention_rate') 
    return cohorts_pivot

def plot_retention_heatmap(cohorts_pivot):
    fig, ax = plt.subplots(figsize=(20, 10))

    with plt.style.context('dark_background'):
        sns.heatmap(data=cohorts_pivot, 
            annot=True, 
            fmt='.0%', 
            cmap='Blues', 
            vmin=0.0,
            vmax=0.5,
            ax=ax
        )
        fig.patch.set_alpha(0.0)
        ax.patch.set_alpha(0.0)
        ax.set_title('Heatmap des taux de rétention par cohortes', fontsize=16, color='white')
        ax.set_xlabel('Mois depuis l\'acquisition', fontsize=14)
        ax.set_ylabel('Cohorte d\'acquisition', fontsize=14)
        ax.tick_params(colors='white')
        ax.xaxis.label.set_color('white')
        ax.yaxis.label.set_color('white')
        cbar = ax.collections[0].colorbar
        cbar.ax.tick_params(colors='white')

    st.pyplot(fig, transparent=True, use_container_width=True)

def densite(df):
    st.subheader("Analyse de la densité")
    
    subset = subset = df[(df['TotalPrice'] > 0) & (df['TotalPrice'] < 75)]

    all_ages = sorted(subset['CohortIndex'].unique()) #on recupère tous les âges de cohortes (0 à 24)

    with st.expander("🔽 Filtres", expanded=True):
        selected_cohorts = st.multiselect(
            "Sélectionner les âges (Mois) à comparer :",
            options=all_ages,
            default=all_ages[:5] # On en limite 5 par défaut pour la lisibilité
        )

    if not selected_cohorts:
        st.warning("Sélectionnez au moins un âge.")
        return
    
    plot_data = subset[subset['CohortIndex'].isin(selected_cohorts)]

    if len(plot_data) > 10000:
        plot_data = plot_data.sample(n=10000, random_state=42)

    fig, ax = plt.subplots(figsize=(10, 6))

    with plt.style.context('dark_background'):
        fig.patch.set_alpha(0.0)
        ax.patch.set_alpha(0.0)

        sns.kdeplot(
            data=plot_data,
            x='TotalPrice',    
            hue='CohortIndex',   
            fill=True,         
            common_norm=False,  
            palette='viridis',
            alpha=0.3,
            linewidth=1.5,
            ax=ax,
            warn_singular=False
        ) 
        ax.set_title('courbes de densité de CA par Cohorte d\'acquisition', fontsize=16, color='white')
        ax.set_xlabel('Total du CA', fontsize=14)
        ax.set_ylabel('Densité', fontsize=14)
        ax.tick_params(colors='white')
        ax.xaxis.label.set_color('white')
        ax.yaxis.label.set_color('white')
        if ax.legend_:
            plt.setp(ax.get_legend().get_texts(), color='white')

    st.pyplot(fig, transparent=True, use_container_width=True)

def main():
    st.title("Rétentions par Cohortes d'Acquisition")
    df = load_data()
    with st.expander("Voir un aperçu des données brutes"):
        st.dataframe(df.head(100))
    cohort_matrix = compute_cohort_matrix(df)
    plot_retention_heatmap(cohort_matrix)
    densite(df)

if __name__ == "__main__":
    main()


