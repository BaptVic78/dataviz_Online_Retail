import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from utils import compute_cohort_matrix, load_data, plot_retention_heatmap, densite

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


