import streamlit as st
import numpy as np
import pandas as pd

@st.cache_data
def load_data():
    df = pd.read_parquet("data/processed/online_retail_clean.parquet")
    return df

st.dataframe(load_data())