import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime

@st.cache_data
def load_data():
    try:
        # Essayer deux chemins possibles pour le fichier
        try:
            df = pd.read_parquet("data/online_retail_clean.parquet")
        except:
            df = pd.read_parquet("data/processed/online_retail_clean.parquet")        
        # Renommer les colonnes si nécessaire
        if 'Customer ID' in df.columns:
            df = df.rename(columns={'Customer ID': 'CustomerID'})
        if 'Price' in df.columns:
            df = df.rename(columns={'Price': 'UnitPrice'})
        if 'Invoice' in df.columns:
            df = df.rename(columns={'Invoice': 'InvoiceNo'})
        
        # Créer la colonne Total si elle n'existe pas
        if 'Total' not in df.columns and all(col in df.columns for col in ['Quantity', 'UnitPrice']):
            df['Total'] = df['Quantity'] * df['UnitPrice']
        
        # Gestion des CustomerID manquants
        if 'CustomerID' not in df.columns or df['CustomerID'].isna().all():
            df['CustomerID'] = 'CUST_' + df.index.astype(str)
            st.warning("Aucun identifiant client trouvé. Des identifiants factices ont été générés.")
        
        # Créer les cohortes
        if 'InvoiceDate' in df.columns:
            df['InvoiceDate'] = pd.to_datetime(df['InvoiceDate'])
            df['Cohort'] = df['InvoiceDate'].dt.to_period('M').astype(str)
        else:
            df['Cohort'] = 'Toutes'
        
        # Créer des segments RFM factices si nécessaire
        if 'RFM_Segment' not in df.columns:
            df['RFM_Segment'] = 'Aucun segment'
        
        return df
        
    except Exception as e:
        st.error(f"Erreur lors du chargement des données: {str(e)}")
        return pd.DataFrame()

def compute_avg_purchase_frequency(df):
    """Calcule la fréquence moyenne d'achat"""
    if 'CustomerID' not in df.columns or 'InvoiceDate' not in df.columns:
        return 12  # Valeur par défaut
    try:
        df_dates = df.groupby("CustomerID")["InvoiceDate"].agg(["min", "max", "count"])
        df_dates["active_months"] = ((df_dates["max"] - df_dates["min"]) / np.timedelta64(30, "D")).clip(lower=1)
        df_dates["freq"] = df_dates["count"] / df_dates["active_months"]
        return df_dates["freq"].mean()
    except:
        return 12  # Valeur par défaut en cas d'erreur

def compute_customer_lifespan(df):
    """Calcule la durée de vie moyenne des clients en années"""
    if 'CustomerID' not in df.columns or 'InvoiceDate' not in df.columns:
        return 3  # Valeur par défaut
    try:
        span = df.groupby("CustomerID")["InvoiceDate"].agg(["min", "max"])
        lifespan_days = (span["max"] - span["min"]).dt.days.clip(lower=1)
        return lifespan_days.mean() / 365
    except:
        return 3  # Valeur par défaut en cas d'erreur

def calculate_clv(df, r, d, aov, freq, lifespan, marge=30.0):
    """Calcule la CLV avec marge brute"""
    if r <= 0 or d <= 0:
        return 0
    try:
        aov_with_margin = aov * (marge / 100)
        clv = (aov_with_margin * freq * r) / (1 + d - r)
        return clv * lifespan
    except:
        return 0