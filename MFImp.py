import streamlit as st

# import os
# st.write("Working directory:", os.getcwd())
# st.stop()

with st.spinner("Processing data..."):
    import pandas as pd
    import plotly.graph_objects as go
    import re
    


st.set_page_config(layout="wide")

st.title("Mutual Fund Portfolio Parser")


raw_text = st.text_area(
    "Paste data here:",
    height=300,
    placeholder="Paste data copied from NSDL Wondershare here..."
)

process_button = st.button("Process Data")

if not process_button:
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

    chart_df = df[["Name", "TotCost", "Value"]].dropna()
    chart_df = df.sort_values("TotCost", ascending=False)

        
    fig = go.Figure()

    fig.add_trace(go.Bar(
        y=chart_df["Name"],
        x=chart_df["TotCost"],
        name="TotCost",
        orientation='h'
    ))

    fig.add_trace(go.Bar(
        y=chart_df["Name"],
        x=chart_df["Value"],
        name="Value",
        orientation='h'
    ))

    fig.update_layout(
        barmode='group',
        height=500 + len(chart_df) * 20,
        yaxis=dict(autorange="reversed"),
        margin=dict(l=200)
    )

    st.plotly_chart(fig, use_container_width=True)