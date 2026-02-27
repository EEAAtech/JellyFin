import sqlite3
import pandas as pd
import streamlit as st
import re
from collections import Counter

# --- Configuration ---
DB_PATH = "/home/ea/JellyFin.db"

def get_data():
    conn = sqlite3.connect(DB_PATH)
    # Join SB and Category to get the human-readable names immediately
    query = """
    SELECT SB.SBName, Category.CategoryName 
    FROM SB 
    JOIN Category ON SB.categoryid = Category.CategoryId
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def extract_pure_alpha(text):
    # Removes numbers and special characters, keeps only alphabetic substrings
    # Returns a list of strings found in the name
    return re.findall(r'[a-zA-Z]{3,}', text.lower())

def analyze_correlations(df):
    mapping = {}
    
    for _, row in df.iterrows():
        substrings = extract_pure_alpha(row['SBName'])
        cat_name = row['CategoryName']
        
        for sub in substrings:
            if sub not in mapping:
                mapping[sub] = Counter()
            mapping[sub][cat_name] += 1
            
    # Process findings into a list for the UI
    results = []
    for sub, counts in mapping.items():
        # Get the most common category for this substring
        top_cat, count = counts.most_common(1)[0]
        total = sum(counts.values())
        confidence = (count / total) * 100
        
        results.append({
            "Substring": sub,
            "Most Frequent Category": top_cat,
            "Occurrence Count": count,
            "Confidence (%)": round(confidence, 2)
        })
        
    return pd.DataFrame(results).sort_values(by="Occurrence Count", ascending=False)

# --- Streamlit UI ---
st.set_page_config(page_title="SB Category Correlation", layout="wide")

st.title("📊 SB Substring & Category Correlation")
st.markdown(f"Analyzing patterns in `{DB_PATH}` to find links between text patterns and categories.")

try:
    with st.spinner("Fetching and processing data..."):
        raw_data = get_data()
        correlation_df = analyze_correlations(raw_data)

    # --- Stats ---
    col1, col2 = st.columns(2)
    col1.metric("Total Records Analyzed", len(raw_data))
    col2.metric("Unique Substrings Found", len(correlation_df))

    # --- Table ---
    st.subheader("Correlation Findings")
    st.write("This table shows which non-numeric strings appear most often in specific categories.")
    
    # Filter functionality
    search = st.text_input("Filter by Substring", "")
    if search:
        correlation_df = correlation_df[correlation_df['Substring'].str.contains(search.lower())]

    st.dataframe(
        correlation_df, 
        use_container_width=True,
        hide_index=True
    )

except Exception as e:
    st.error(f"Error accessing the database: {e.__class__.__name__}: {e}")
    st.info("Check if the path '/home/ea/JellyFin.db' is correct and accessible.")