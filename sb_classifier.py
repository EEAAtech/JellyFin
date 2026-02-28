import sqlite3
import pandas as pd
import streamlit as st
import re
import os

# --- Configuration ---
DB_PATH = "/home/ea/JellyFin.db"

def initialize_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS SBClassMeta (
            Pattern TEXT,
            TxType TEXT,
            CategoryId INTEGER,
            Frequency INTEGER DEFAULT 1,
            PRIMARY KEY (Pattern, TxType, CategoryId)
        )
    """)
    conn.commit()
    conn.close()

def clean_sb_name(text):
    if not text: return ""
    text = re.sub(r'\d+', '', str(text)) 
    text = re.sub(r'[^a-zA-Z\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip().upper()

def get_lcp(s1, s2):
    """Returns the Longest Common Prefix between two strings."""
    return os.path.commonprefix([s1, s2]).strip()

# --- Core Classifier Logic ---

def get_proposed_category(conn, sb_name, amt_in, amt_out):
    """
    Finds if the incoming string contains any known pattern.
    SQL Note: 'WHERE ? LIKE '%' || Pattern || '%'' checks if the stored 
    Pattern (e.g. 'UPI GENERIC') exists inside the input SBName.
    """
    clean_name = clean_sb_name(sb_name)
    tx_type = 'Inflow' if float(amt_in or 0) > 0 else 'Outflow'
    
    query = """
        SELECT CategoryId 
        FROM SBClassMeta 
        WHERE ? LIKE '%' || Pattern || '%' 
          AND TxType = ?
        ORDER BY LENGTH(Pattern) DESC, Frequency DESC 
        LIMIT 1
    """
    cursor = conn.cursor()
    cursor.execute(query, (clean_name, tx_type))
    result = cursor.fetchone()
    return result[0] if result else None

def update_sb_meta(conn, sb_name, amt_in, amt_out, category_id):
    """
    SMART UPDATE: 
    1. Checks for a direct parent pattern.
    2. If none, looks for a 'sibling' (sharing the same first two words).
    3. If a sibling is found, it shrinks the record to their LCP (Longest Common Prefix).
    """
    clean_name = clean_sb_name(sb_name)
    tx_type = 'Inflow' if float(amt_in or 0) > 0 else 'Outflow'
    words = clean_name.split()
    # We define a 'sibling' as a pattern sharing the first two words
    prefix_key = " ".join(words[:2]) if len(words) >= 2 else clean_name
    
    cursor = conn.cursor()

    # STEP 1: Check for a direct match or parent (Existing behavior)
    cursor.execute("""
        SELECT Pattern, Frequency FROM SBClassMeta 
        WHERE ? LIKE '%' || Pattern || '%' AND TxType = ? AND CategoryId = ?
    """, (clean_name, tx_type, category_id))
    match = cursor.fetchone()

    if match:
        # We found a parent (e.g., 'UPI GENERIC' exists for 'UPI GENERIC LUNCH')
        # Just increment the weight of the existing parent.
        cursor.execute("""
            UPDATE SBClassMeta SET Frequency = Frequency + 1 
            WHERE Pattern = ? AND TxType = ? AND CategoryId = ?
        """, (match[0], tx_type, category_id))
    else:
        # STEP 2: Look for a sibling to merge with (The LCP improvement)
        cursor.execute("""
            SELECT Pattern, Frequency FROM SBClassMeta 
            WHERE Pattern LIKE ? || '%' AND TxType = ? AND CategoryId = ?
            LIMIT 1
        """, (prefix_key, tx_type, category_id))
        sibling = cursor.fetchone()

        if sibling:
            # We found a sibling (e.g., 'UPI GENERIC LUNCH' exists for 'UPI GENERIC DINNER')
            # Calculate the new common root
            old_pattern = sibling[0]
            new_pattern = get_lcp(old_pattern, clean_name)
            
            # If the new LCP is meaningful (not just 'UPI'), replace the old one
            if len(new_pattern) >= 8:
                cursor.execute("DELETE FROM SBClassMeta WHERE Pattern = ? AND TxType = ? AND CategoryId = ?", 
                               (old_pattern, tx_type, category_id))
                cursor.execute("""
                    INSERT INTO SBClassMeta (Pattern, TxType, CategoryId, Frequency)
                    VALUES (?, ?, ?, ?)
                """, (new_pattern, tx_type, category_id, sibling[1] + 1))
            else:
                # LCP was too short/noisy, just insert as a new distinct record
                cursor.execute("""
                    INSERT INTO SBClassMeta (Pattern, TxType, CategoryId, Frequency)
                    VALUES (?, ?, ?, 1)
                """, (clean_name, tx_type, category_id))
        else:
            # STEP 3: No parent or sibling found, insert as new pattern
            cursor.execute("""
                INSERT INTO SBClassMeta (Pattern, TxType, CategoryId, Frequency)
                VALUES (?, ?, ?, 1)
            """, (clean_name, tx_type, category_id))
    
    conn.commit()

# --- Migration / Initial Load ---

def migrate_and_compress():
    """Wipes and rebuilds the meta table from the SB table history."""
    conn = sqlite3.connect(DB_PATH)
    # Clear current meta
    conn.execute("DELETE FROM SBClassMeta")
    
    # Load history
    df = pd.read_sql_query("SELECT SBName, AmtIn, AmtOut, CategoryId FROM SB", conn)
    
    # We use the smart update function for every historical record to rebuild the table
    for _, row in df.iterrows():
        update_sb_meta(conn, row['SBName'], row['AmtIn'], row['AmtOut'], row['CategoryId'])
    
    conn.close()

# --- Streamlit UI ---

def run_ui():
    st.set_page_config(page_title="SB Smart Manager", layout="wide")
    initialize_db()

    st.title("🧠 Adaptive SB Pattern Classifier")
    
    if st.button("🚀 Run Full Migration/Re-Compression"):
        with st.spinner("Processing historical records..."):
            migrate_and_compress()
        st.success("Table re-built and compressed!")

    conn = sqlite3.connect(DB_PATH)
    df_meta = pd.read_sql_query("""
        SELECT m.Pattern, m.TxType, c.CategoryName, m.Frequency 
        FROM SBClassMeta m
        JOIN Category c ON m.CategoryId = c.CategoryId
        ORDER BY m.Frequency DESC
    """, conn)
    conn.close()

    st.subheader(f"Current Lean Knowledge Base ({len(df_meta)} records)")
    st.dataframe(df_meta, use_container_width=True, hide_index=True)

if __name__ == "__main__":
    run_ui()