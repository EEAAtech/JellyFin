import streamlit as st

# import os
# st.write("Working directory:", os.getcwd())
# st.stop()

with st.spinner("Processing data..."):
    import pandas as pd
    import plotly.graph_objects as go
    import re
    import sqlite3
    from datetime import datetime
    


st.set_page_config(layout="wide")

st.title("Mutual Fund Portfolio Parser")


raw_text = st.text_area(
    "Paste data here:",
    height=300,
    placeholder="Paste data copied from NSDL Wondershare here..."
)

process_button = st.button("Process Data")

#Save the fact that it was clicked in session state, so that we can use it to control flow. This is needed because when we click the button, the whole script runs again and we need to know that it was clicked at least once.
if process_button:
    st.session_state["process_clicked"] = True

if "process_clicked" not in st.session_state:
    st.stop()


if not raw_text.strip():
    st.info("Please paste your portfolio data to begin.")
    st.stop()

with st.spinner("Processing portfolio data..."):
    # Remove commas globally
    raw_text = raw_text.replace(",", "")


    # --------------------------------------------------
    # STEP 1: READ RAW CSV (single column expected)
    # --------------------------------------------------
    
    # For each list value from splitlines, check if after triming there is any value. If not empty, them trim and add to list. This will remove empty lines and trim spaces.
    raw_values = [line.strip() for line in raw_text.splitlines() if line.strip()]
    
    records = []
    current_record = []

    for line in raw_values:

        if line.startswith("INF"):
            if current_record:
                records.append(current_record)
            current_record = []

            parts = line.split()
            current_record.append(parts[0])  # ISIN

            if len(parts) > 1:
                current_record.append(parts[1])  # UCC

        else:
            current_record.append(line)

    if current_record:
        records.append(current_record)

    # --------------------------------------------------
    # CLEANING FUNCTION (same logic as Excel script)
    # --------------------------------------------------

    def fix_record(record):
        # Rule 1: Column 4 (index 3) must be numeric
        if len(record) >= 4 and re.search(r"[A-Za-z]", record[3]):
            record[2] = record[2] + " " + record[3]
            record.pop(3)

        # Rule 2: AvgCost (index 5) must not be 1 or 2 digits
        if len(record) >= 6 and re.fullmatch(r"\d{1,2}", record[5]):
            record[4] = record[4] + record[5]
            record.pop(5)

        # Pad to 11 columns
        record = record[:11]
        while len(record) < 11:
            record.append("")

        return record

    cleaned_records = [fix_record(r) for r in records]

    columns = [
        "ISIN", "UCC", "Name", "Folio", "Units",
        "AvgCost", "TotCost", "Nav", "Value", "PL", "XIRR"
    ]

    df = pd.DataFrame(cleaned_records, columns=columns)

    # --------------------------------------------------
    # NUMERIC CLEANUP
    # --------------------------------------------------

    numeric_cols = ["Units", "AvgCost", "TotCost", "Nav", "Value", "PL", "XIRR"]

    for col in numeric_cols:
        df[col] = (
            df[col]
            .astype(str)
            .str.replace(",", "", regex=False)
        )
        df[col] = pd.to_numeric(df[col], errors="coerce")


    # --------------------------------------------------
    # DISPLAY TABLE
    # --------------------------------------------------

    st.subheader("Parsed Portfolio Data")
    st.dataframe(df, use_container_width=True)


    # --------------------------------------------------
    # PORTFOLIO SUMMARY
    # --------------------------------------------------

    total_totcost = df["TotCost"].sum(skipna=True)
    total_value = df["Value"].sum(skipna=True)
    avg_xirr = df["XIRR"].mean(skipna=True)

    st.subheader("Portfolio Summary")

    col1, col2, col3 = st.columns(3)

    col1.metric("Total Cost", f"{total_totcost:,.2f}")
    col2.metric("Total Value", f"{total_value:,.2f}")
    col3.metric("Average XIRR", f"{avg_xirr:.2f}%")

    # --------------------------------------------------
    # HORIZONTAL CLUSTERED BAR CHART
    # --------------------------------------------------

    st.subheader("TotCost vs Value (Sorted by Cost)")

    # chart_df = df[["Name", "TotCost", "Value"]].dropna()
    # chart_df = df.sort_values("TotCost", ascending=False)

        
    # fig = go.Figure()

    # fig.add_trace(go.Bar(
    #     y=chart_df["Name"],
    #     x=chart_df["TotCost"],
    #     name="TotCost",
    #     orientation='h'
    # ))

    # fig.add_trace(go.Bar(
    #     y=chart_df["Name"],
    #     x=chart_df["Value"],
    #     name="Value",
    #     orientation='h'
    # ))

    # fig.update_layout(
    #     barmode='group',
    #     height=500 + len(chart_df) * 20,
    #     yaxis=dict(autorange="reversed"),
    #     margin=dict(l=200)
    # )

    # st.plotly_chart(fig, use_container_width=True)


# --------------------------------------------------
# SQLITE SECTION
# --------------------------------------------------

st.divider()
st.subheader("Quarterly Selection & Import")

DB_PATH = "/home/ea/JellyFin.db"


conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# --------------------------------------------------
# A. TOP 3 MONTH/YEAR FROM MFQuarterly
# --------------------------------------------------

top_query = """
SELECT TMonth, TYear
FROM MFQuarterly
GROUP BY TMonth, TYear
ORDER BY TYear DESC, TMonth DESC
LIMIT 3
"""

top_df = pd.read_sql_query(top_query, conn)

st.markdown("### Latest 3 Imported Periods")
st.dataframe(top_df, use_container_width=True)


# --------------------------------------------------
# B & C DROPDOWNS
# --------------------------------------------------

current_month = datetime.now().month
current_year = datetime.now().year

col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
with col1:
    month = st.selectbox(
        "Select Month",
        list(range(1, 13)),
        index=current_month - 1
)

with col2:
    year = st.selectbox(
        "Select Year",
        [current_year, current_year - 1],
        index=0
    )


with col3:
    # Populate owner selectbox from Owner table and map to OwnerId; fall back to hard-coded list
    try:
        owner_query = "SELECT OwnerId, OwnerName FROM Owner ORDER BY OwnerId"
        owners_df = pd.read_sql_query(owner_query, conn)
        if not owners_df.empty:
            owner_names = owners_df["OwnerName"].tolist()
        else:
            st.error("No owners found in the database.")
            st.stop()
    except Exception:
            st.error("No owners found in the database.")
            st.stop()


    selected_owner_name = st.selectbox(
        "Select Owner",
        owner_names,
        index=0
    )

    # Resolve selected OwnerId (None if fallback/static used)
    sel_row = owners_df[owners_df["OwnerName"] == selected_owner_name]
    if not sel_row.empty and pd.notna(sel_row.iloc[0]["OwnerId"]):
        selected_owner_id = int(sel_row.iloc[0]["OwnerId"])
    else:
        st.info("Owners found but OwnerId is missing.")
        st.stop()

with col4:
    st.write("Ready to go!")
    import_clicked = st.button("Import to MFQuarterly")
# --------------------------------------------------
# D. IMPORT BUTTON
# --------------------------------------------------

if import_clicked:

    # --------------------------------------------------
    # Get Active MFTrans records (ClosedDate IS NULL)
    # --------------------------------------------------

    # Use OwnerId if available, otherwise fall back to Owner name column
    if selected_owner_id is not None:
        mftrans_query = """
        SELECT MFTransId, ISIN, Folio
        FROM MFTrans
        WHERE ClosedDate IS NULL
        AND OwnerId = ?
        """
        mftrans_df = pd.read_sql_query(mftrans_query, conn, params=(selected_owner_id,))
    else:
        st.info("Owners found but OwnerId is missing.")
        st.stop()


    # --------------------------------------------------
    # Merge Raw Data (df) with MFTrans
    # --------------------------------------------------

    merged = df.merge(
        mftrans_df,
        on=["ISIN", "Folio"],
        how="left",
        indicator=True
    )

    # Records that matched
    matched = merged[merged["_merge"] == "both"].copy()

    # Records in Raw but NOT in MFTrans
    raw_unmapped = merged[merged["_merge"] == "left_only"].copy()

    # --------------------------------------------------
    # Prepare Insert Data
    # --------------------------------------------------

    insert_df = matched.copy()

    insert_df["TMonth"] = month
    insert_df["TYear"] = year

    insert_cols = [
        "MFTransId",
        "TMonth",
        "TYear",
        "Units",
        "TotCost",
        "Nav",
        "Value",
        "XIRR"
    ]

    records_to_insert = insert_df[insert_cols].values.tolist()

    insert_sql = """
    INSERT INTO MFQuarterly
    (MFTransId, TMonth, TYear, Units, TotCost, Nav, Value, XIRR)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """

    # cursor.executemany(insert_sql, records_to_insert)
    # conn.commit()

    st.success(f"{len(records_to_insert)} records imported successfully.")

    # --------------------------------------------------
    # E. UNMAPPED TABLES
    # --------------------------------------------------

    st.divider()
    st.subheader("Unmapped Records")

    # Raw → MFTrans unmapped
    st.markdown("### Raw Data NOT Found in MFTrans (ClosedDate IS NULL)")
    st.dataframe(raw_unmapped[["ISIN", "Folio", "Name"]], use_container_width=True)

    # MFTrans → Raw unmapped
    raw_keys = df[["ISIN", "Folio"]].drop_duplicates()

    mf_unmapped = mftrans_df.merge(
        raw_keys,
        on=["ISIN", "Folio"],
        how="left",
        indicator=True
    )

    mf_unmapped = mf_unmapped[mf_unmapped["_merge"] == "left_only"]

    st.markdown("### MFTrans Records (ClosedDate IS NULL) NOT Found in Raw Data")
    st.dataframe(mf_unmapped[["ISIN", "Folio", "MFTransId"]], use_container_width=True)

conn.close()
