import sqlite3
import pandas as pd
import streamlit as st
import re

# --- Configuration ---
DB_PATH = "/home/ea/JellyFin.db"

def get_data():
    conn = sqlite3.connect(DB_PATH)
    # Using exact casing SBName as requested
    query = """
    SELECT 
        SB.SBName, 
        SB.AmtIn, 
        SB.AmtOut, 
        Category.CategoryName 
    FROM SB 
    JOIN Category ON SB.categoryid = Category.CategoryId
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def clean_sb_name(text):
    if not text:
        return ""
    # 1. Remove all digits
    text = re.sub(r'\d+', '', text)
    # 2. Replace multiple spaces/special chars with a single space
    text = re.sub(r'[^a-zA-Z\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip().upper()

def process_correlations(df):
    # Determine Transaction Type
    df['TxType'] = df.apply(lambda x: 'Inflow' if x['AmtIn'] > 0 else 'Outflow', axis=1)
    
    # Create the normalized pattern (The "Substring" entity)
    df['Pattern'] = df['SBName'].apply(clean_sb_name)
    
    # Group by Pattern, TxType, and CategoryName to count occurrences
    grouped = df.groupby(['Pattern', 'TxType', 'CategoryName']).size().reset_index(name='Count')
    
    # For each (Pattern, TxType) pair, find the most frequent category
    # This helps identify which category is the "True North" for that phrase
    total_counts = df.groupby(['Pattern', 'TxType']).size().reset_index(name='Total')
    
    final = pd.merge(grouped, total_counts, on=['Pattern', 'TxType'])
    final['Confidence (%)'] = (final['Count'] / final['Total'] * 100).round(2)
    
    # Sort by the most frequent patterns
    return final.sort_values(by='Count', ascending=False)

# --- Streamlit UI ---
st.set_page_config(page_title="SB Pattern Analyzer", layout="wide")

st.title("🔍 SB Pattern & Category Correlation")
st.markdown("""
This analysis treats continuous non-numeric text as a single entity and incorporates 
**AmtIn/AmtOut** logic to differentiate between inflows and outflows.
""")

try:
    raw_data = get_data()
    processed_df = process_correlations(raw_data)

    # --- Metrics ---
    m1, m2, m3 = st.columns(3)
    m1.metric("Total Transactions", len(raw_data))
    m2.metric("Unique Text Patterns", processed_df['Pattern'].nunique())
    m3.metric("Avg Confidence", f"{processed_df['Confidence (%)'].mean():.1f}%")

    # --- Filters ---
    st.divider()
    col_a, col_b = st.columns([2, 1])
    with col_a:
        search = st.text_input("Search Patterns (e.g., 'INTEREST')", "")
    with col_b:
        tx_filter = st.multiselect("Filter Type", ["Inflow", "Outflow"], default=["Inflow", "Outflow"])

    # Apply Filters
    display_df = processed_df[processed_df['TxType'].isin(tx_filter)]
    if search:
        display_df = display_df[display_df['Pattern'].str.contains(search.upper())]

    # --- Main Table ---
    st.subheader("Correlation Findings")
    st.dataframe(
        display_df[['Pattern', 'TxType', 'CategoryName', 'Count', 'Confidence (%)']], 
        use_container_width=True,
        hide_index=True,
        column_config={
            "Pattern": "Normalized SBName",
            "TxType": "Type",
            "CategoryName": "Assigned Category",
            "Count": "Occurrences",
            "Confidence (%)": st.column_config.ProgressColumn(
                "Confidence",
                format="%f%%",
                min_value=0,
                max_value=100,
            ),
        }
    )

except Exception as e:
    st.error(f"Database Error: {e}")
    st.info("Check if '/home/ea/JellyFin.db' exists and contains 'SBName', 'AmtIn', and 'AmtOut' columns.")