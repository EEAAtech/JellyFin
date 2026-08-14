import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import altair as alt
import db_manager as db
from datetime import datetime, timedelta
import numpy as np
import os

# Page configuration
st.set_page_config(
    page_title="Personal Wealth Hub",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling (Glassmorphism & Modern typography)
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');

/* Global Font Override */
html, body, [class*="css"], .stMarkdown {
    font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
}

/* Sidebar Styling */
.css-1d391kg {
    background-color: #0f172a;
}

/* Glassmorphism Metric Cards */
.kpi-container {
    display: flex;
    flex-wrap: wrap;
    gap: 1rem;
    margin-bottom: 1.5rem;
}

.kpi-card {
    flex: 1;
    min-width: 180px;
    background: rgba(30, 41, 59, 0.45);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 16px;
    padding: 1.5rem;
    box-shadow: 0 10px 30px 0 rgba(0, 0, 0, 0.15);
    transition: all 0.3s ease;
    position: relative;
    overflow: hidden;
}

.kpi-card:hover {
    transform: translateY(-3px);
    border-color: rgba(255, 255, 255, 0.15);
    box-shadow: 0 15px 35px 0 rgba(0, 0, 0, 0.25);
    background: rgba(30, 41, 59, 0.6);
}

.kpi-title {
    font-size: 0.8rem;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    font-weight: 600;
    margin-bottom: 0.5rem;
}

.kpi-value {
    font-size: 1.35rem;
    font-weight: 700;
    color: #f8fafc;
    margin-bottom: 0.25rem;
    line-height: 1.2;
}

.kpi-delta {
    font-size: 0.75rem;
    font-weight: 600;
    display: inline-flex;
    align-items: center;
}

.delta-up {
    color: #34d399;
}

.delta-down {
    color: #f87171;
}

.delta-neutral {
    color: #94a3b8;
}

/* Card Accent Bars */
.kpi-card::before {
    content: "";
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 4px;
}
.kpi-earn::before { background: linear-gradient(90deg, #10b981, #34d399); }
.kpi-spend::before { background: linear-gradient(90deg, #ef4444, #f87171); }
.kpi-invest::before { background: linear-gradient(90deg, #3b82f6, #60a5fa); }
.kpi-net::before { background: linear-gradient(90deg, #8b5cf6, #a78bfa); }
.kpi-rate::before { background: linear-gradient(90deg, #f59e0b, #fbbf24); }

/* Bank Card Styling */
.bank-container {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
}

.bank-card {
    background: rgba(30, 41, 59, 0.35);
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-left: 5px solid #3b82f6;
    border-radius: 12px;
    padding: 1.25rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    transition: all 0.2s ease;
}

.bank-card:hover {
    background: rgba(30, 41, 59, 0.55);
    border-color: rgba(255, 255, 255, 0.1);
    transform: translateX(4px);
}

.bank-details {
    display: flex;
    flex-direction: column;
}

.bank-name {
    font-weight: 700;
    font-size: 1.05rem;
    color: #e2e8f0;
}

.bank-acc {
    font-size: 0.8rem;
    color: #64748b;
    margin-top: 0.1rem;
}

.bank-balance {
    font-size: 1.3rem;
    font-weight: 800;
    color: #34d399;
}

/* Health Badge Indicator */
.health-badge {
    padding: 0.35rem 0.75rem;
    border-radius: 50px;
    font-size: 0.8rem;
    font-weight: 700;
    display: inline-block;
}
.badge-excellent { background-color: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.3); }
.badge-healthy { background-color: rgba(59, 130, 246, 0.15); color: #60a5fa; border: 1px solid rgba(59, 130, 246, 0.3); }
.badge-warning { background-color: rgba(245, 158, 11, 0.15); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.3); }
.badge-critical { background-color: rgba(239, 68, 68, 0.15); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.3); }

/* Custom Scrollbar */
::-webkit-scrollbar {
    width: 8px;
    height: 8px;
}
::-webkit-scrollbar-track {
    background: #0f172a;
}
::-webkit-scrollbar-thumb {
    background: #1e293b;
    border-radius: 4px;
}
::-webkit-scrollbar-thumb:hover {
    background: #334155;
}
</style>
""", unsafe_allow_html=True)

# Custom color palette constants for Plotly
COLOR_INFLOW = '#10b981'   # Green
COLOR_OUTFLOW = '#ef4444'  # Red
COLOR_INVEST = '#3b82f6'   # Blue
COLOR_ACCENT = '#8b5cf6'   # Purple
COLOR_CARD_BG = 'rgba(15, 23, 42, 0.3)'

def format_inr(amount, include_symbol=True):
    if amount is None or pd.isna(amount):
        return "₹0.00" if include_symbol else "0.00"
    
    try:
        val = float(amount)
    except (ValueError, TypeError):
        return "₹0.00" if include_symbol else "0.00"
        
    is_negative = val < 0
    val = abs(val)
    
    s = f"{val:.2f}"
    parts = s.split('.')
    dec = parts[1]
    integer_part = parts[0]
    
    n = len(integer_part)
    if abs(val) >= 100000:
        lakhs = val / 100000.0
        result = f"₹{lakhs:,.2f}L" if include_symbol else f"{lakhs:,.2f}L"
    else:
        if n <= 3:
            formatted = integer_part
        else:
            last_three = integer_part[-3:]
            remaining = integer_part[:-3]
            remaining_reversed = remaining[::-1]
            groups = [remaining_reversed[i:i+2] for i in range(0, len(remaining_reversed), 2)]
            remaining_formatted = ",".join(groups)[::-1]
            formatted = f"{remaining_formatted},{last_three}"
        result = f"₹{formatted}.{dec}" if include_symbol else f"{formatted}.{dec}"
    if is_negative:
        result = f"-{result}"
    return result


def format_amount_lakh(value):
    """Return a formatted string using Indian lakh notation for chart labels."""
    if value is None or pd.isna(value):
        return "₹0.00"
    try:
        val = float(value)
    except (ValueError, TypeError):
        return "₹0.00"

    if abs(val) >= 100000:
        lakhs = val / 100000.0
        return f"₹{lakhs:,.2f}L"
    return format_inr(val)


def rupees_to_lakhs(value):
    try:
        return float(value) / 100000.0
    except (ValueError, TypeError):
        return 0.0


def build_altair_bar_chart(df, x_col, y_col, title, color, y_title='Amount (Lakhs)'):
    chart_df = df.copy()
    chart_df[y_col] = chart_df[y_col].fillna(0.0).astype(float)
    chart_df['AmountLakhs'] = chart_df[y_col].apply(rupees_to_lakhs)
    chart_df['Label'] = chart_df[y_col].apply(format_amount_lakh)

    base = alt.Chart(chart_df).mark_bar(color=color).encode(
        x=alt.X(f"{x_col}:N", axis=alt.Axis(labelColor='#e2e8f0', titleColor='#94a3b8')),
        y=alt.Y('AmountLakhs:Q', axis=alt.Axis(title=y_title, labelColor='#e2e8f0', titleColor='#94a3b8')),
        tooltip=[
            alt.Tooltip(f"{x_col}:N", title=x_col),
            alt.Tooltip(f"{y_col}:Q", title='Amount (₹)', format=',.2f'),
            alt.Tooltip('AmountLakhs:Q', title='Amount (Lakhs)', format='.2f')
        ]
    ).properties(title=title, height=360)

    text = base.mark_text(dy=-10, color='#ffffff', size=12).encode(text='Label:N')
    return alt.layer(base, text).configure_view(stroke='transparent').configure_title(color='#e2e8f0')

# Helper function to style Plotly charts
def style_chart(fig):
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#e2e8f0', family='Plus Jakarta Sans'),
        margin=dict(l=10, r=10, t=40, b=10),
        xaxis=dict(gridcolor='rgba(255,255,255,0.05)', zeroline=False),
        yaxis=dict(gridcolor='rgba(255,255,255,0.05)', zeroline=False, tickprefix='₹'),
        legend=dict(
            bgcolor='rgba(15, 23, 42, 0.5)',
            bordercolor='rgba(255, 255, 255, 0.05)',
            borderwidth=1
        )
    )
    return fig

# Check DB Setup Status
db_status = db.check_db_setup()

# Sidebar: App State Info
st.sidebar.markdown(f"### ⚡ WealthHub DB Status")
if db_status["exists"] and not db_status["errors"]:
    st.sidebar.success("Database Connected")
    st.sidebar.caption(f"Connected to: `{os.path.basename(db_status['path'])}`")
else:
    st.sidebar.error("Database Issue Detected")
    for err in db_status["errors"]:
        st.sidebar.caption(f"⚠️ {err}")
    if st.sidebar.button("Auto-Initialize Blank Database"):
        db.get_connection()
        st.rerun()

# Dynamic Budgets Storage inside Session State (persists during Streamlit session)
if "budgets" not in st.session_state:
    st.session_state.budgets = {}

# Load Data
df_trans = db.get_all_transactions()
df_cats = db.get_categories()
df_banks = db.get_banks()

# If session state budgets are empty, initialize them with default category values or BudgetName parsing
if df_cats is not None and not df_cats.empty:
    for _, cat in df_cats.iterrows():
        cat_id = int(cat['CategoryId'])
        cat_name = cat['CategoryName']
        budget_str = cat['BudgetName']
        
        # Try to initialize from BudgetName if we can parse a number, else default to 500
        if cat_id not in st.session_state.budgets:
            default_val = 500.0
            if budget_str:
                try:
                    # Clean budget name and extract numbers (e.g. "Rent 2000" -> 2000)
                    numbers = ''.join(c for c in budget_str if c.isdigit() or c == '.')
                    if numbers:
                        default_val = float(numbers)
                except:
                    pass
            st.session_state.budgets[cat_id] = default_val

# Empty Database Handling
if df_trans.empty:
    st.warning("📊 No transaction records found in the database. Please add some transactions in the 'Transaction Ledger & Editor' tab to view your dashboard charts!")
    
# Primary Filters in Sidebar
st.sidebar.markdown("### 🔍 Filters")

# Filter by Date Range
current_date = datetime.now()
default_start = current_date - timedelta(days=365)
default_end = current_date

min_date = datetime(2000, 1, 1)
max_date = current_date + timedelta(days=365)
if not df_trans.empty and df_trans['DateT'].notna().any():
    min_date = df_trans['DateT'].min().to_pydatetime()
    max_date = df_trans['DateT'].max().to_pydatetime()

# Ensure default values are within bounds
min_limit = min(min_date, default_start)
max_limit = max(max_date, default_end)

selected_dates = st.sidebar.date_input(
    "Date Range",
    value=(default_start.date(), default_end.date()),
    min_value=min_limit.date(),
    max_value=max_limit.date()
)

# Filter by Bank Account
bank_options = []
if df_banks is not None and not df_banks.empty:
    bank_options = df_banks['BankName'].tolist()
selected_banks = st.sidebar.multiselect("Filter Bank", options=bank_options, default=[])

# Filter by Category
cat_options = []
if df_cats is not None and not df_cats.empty:
    cat_options = df_cats['CategoryName'].tolist()
selected_categories = st.sidebar.multiselect("Filter Category", options=cat_options, default=[])

# Apply filters to Dataframe
df_filtered = df_trans.copy()
start_date = pd.to_datetime(default_start.date())
end_date = pd.to_datetime(default_end.date())

if not df_filtered.empty:
    # Date Filtering
    if isinstance(selected_dates, (tuple, list)) and len(selected_dates) == 2:
        start_date = pd.to_datetime(selected_dates[0])
        end_date = pd.to_datetime(selected_dates[1]) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
        df_filtered = df_filtered[(df_filtered['DateT'] >= start_date) & (df_filtered['DateT'] <= end_date)]
    
    # Bank Filtering
    if selected_banks:
        df_filtered = df_filtered[df_filtered['BankName'].isin(selected_banks)]
        
    # Category Filtering
    if selected_categories:
        df_filtered = df_filtered[df_filtered['CategoryName'].isin(selected_categories)]

# --- DATA PRE-CALCULATIONS FOR DASHBOARD METRICS ---
if not df_filtered.empty:
    # Fill NaN values in inflow/outflow
    df_filtered['AmtIn'] = df_filtered['AmtIn'].fillna(0.0).astype(float)
    df_filtered['AmtOut'] = df_filtered['AmtOut'].fillna(0.0).astype(float)
    
    total_inflow = df_filtered['AmtIn'].sum()
    # More robust and readable version
    total_earned = df_filtered.loc[
        (df_filtered['BudgetName'].notna()) & 
        (df_filtered['BudgetName'].str.strip() != "") & 
        (df_filtered['BudgetName'] == "Earn")
    ]['AmtIn'].astype(float).sum()
    total_outflow = df_filtered['AmtOut'].sum()
    total_spent = df_filtered.loc[
        (df_filtered['BudgetName'].notna()) & 
        (df_filtered['BudgetName'].str.strip() != "") & 
        (df_filtered['BudgetName'] != "Invest")
    ]['AmtOut'].astype(float).sum()

    # Investment Categorization Heuristic
    def is_investment_row(row):
        cat_name = str(row['CategoryName']).lower() if pd.notna(row['CategoryName']) else ""
        budget_name = str(row['BudgetName']).lower() if pd.notna(row['BudgetName']) else ""
        keywords = ['invest', 'stock', 'mutual fund', 'mf', 'crypto', 'savings', 'equity', 'gold', 'fd', 'ppf', 'epf', 'sip']
        return any(k in cat_name or k in budget_name for k in keywords)

    df_filtered['IsInvestment'] = df_filtered.apply(is_investment_row, axis=1)
    


    total_invested = df_filtered.loc[
        (df_filtered['BudgetName'].notna()) & 
        (df_filtered['BudgetName'].str.strip() != "") & 
        (df_filtered['BudgetName'] == "Invest")
    ]['AmtOut'].astype(float).sum()

    # Pure Spending (outflow minus investments)
    total_spending = total_outflow
    
    net_savings = total_earned - total_spent
    savings_rate = (net_savings / total_earned * 100) if total_earned > 0 else 0.0
else:
    total_inflow = 0.0
    total_outflow = 0.0
    total_invested = 0.0
    total_spending = 0.0
    net_savings = 0.0
    savings_rate = 0.0

# Layout Tabs
tab_overview, tab_income, tab_spending, tab_invest, tab_ledger, tab_coach = st.tabs([
    "📊 Overview", 
    "📈 Income & Sources", 
    "💸 Spending & Budget", 
    "🛡️ Investments & Wealth", 
    "📋 Ledger & Editor", 
    "🧠 Wealth Coach"
])

# ==========================================
# 📊 TAB 1: OVERVIEW
# ==========================================
with tab_overview:
    # Dashboard Header
    st.markdown("<h2 style='margin-bottom: 0.5rem;'>⚡ Personal Wealth Hub</h2>", unsafe_allow_html=True)
    st.caption("Gain ultimate clarity over your bank transactions, categorizations, and investment habits.")
    st.markdown("<hr style='margin-top: 0.25rem; margin-bottom: 1.5rem; border-color: rgba(255,255,255,0.05);'>", unsafe_allow_html=True)
    
    # 1. Metric Cards Row
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.markdown(f"""
        <div class="kpi-card kpi-earn">
            <div class="kpi-title">Total Inflow, earnings</div>
            <div class="kpi-value">{format_inr(total_inflow)}</div>
            <div class="kpi-value">{format_inr(total_earned)}</div>
            <div class="kpi-delta delta-up">▲ Inflow</div>
        </div>
        """, unsafe_allow_html=True)
        
    with col2:
        st.markdown(f"""
        <div class="kpi-card kpi-spend">
            <div class="kpi-title">Total Outflow, expenses</div>
            <div class="kpi-value">{format_inr(total_spending)}</div>
            <div class="kpi-value">{format_inr(total_spent)}</div>
            <div class="kpi-delta delta-down">▼ Operational</div>
        </div>
        """, unsafe_allow_html=True)
        
    with col3:
        st.markdown(f"""
        <div class="kpi-card kpi-invest">
            <div class="kpi-title">Total Investing</div>
            <div class="kpi-value">{format_inr(total_invested)}</div>
            <div class="kpi-delta delta-up" style="color: #60a5fa;">★ Assets</div>
        </div>
        """, unsafe_allow_html=True)
        
    with col4:
        delta_class = "delta-up" if net_savings >= 0 else "delta-down"
        delta_symbol = "▲" if net_savings >= 0 else "▼"
        st.markdown(f"""
        <div class="kpi-card kpi-net">
            <div class="kpi-title">Net Savings</div>
            <div class="kpi-value">{format_inr(net_savings)}</div>
            <div class="kpi-delta {delta_class}">{delta_symbol} Cashflow</div>
        </div>
        """, unsafe_allow_html=True)
        
    with col5:
        rate_class = "badge-excellent" if savings_rate >= 30 else ("badge-healthy" if savings_rate >= 15 else ("badge-warning" if savings_rate >= 0 else "badge-critical"))
        st.markdown(f"""
        <div class="kpi-card kpi-rate">
            <div class="kpi-title">Savings Rate</div>
            <div class="kpi-value">{savings_rate:.1f}%</div>
            <div class="kpi-delta" style="color: #fbbf24;">⚡ Score</div>
        </div>
        """, unsafe_allow_html=True)

    # 2. Main Content Visualizations
    st.markdown("<br>", unsafe_allow_html=True)

    # --- Budget-wise Inflow & Outflow Bar Charts ---
    st.markdown("### 📊 Budget-wise Inflow & Outflow")
    if not df_filtered.empty:
        # Prepare Inflow data
        df_budget_in = df_filtered[df_filtered['AmtIn'] > 0].copy()
        df_budget_in['BudgetName'] = df_budget_in['BudgetName'].fillna("Uncategorized").replace("", "Uncategorized")
        df_budget_in_grouped = df_budget_in.groupby('BudgetName')['AmtIn'].sum().reset_index()
        
        # Prepare Outflow data
        df_budget_out = df_filtered[df_filtered['AmtOut'] > 0].copy()
        df_budget_out['BudgetName'] = df_budget_out['BudgetName'].fillna("Uncategorized").replace("", "Uncategorized")
        df_budget_out_grouped = df_budget_out.groupby('BudgetName')['AmtOut'].sum().reset_index()
        
        col_b_in, col_b_out = st.columns(2)
        with col_b_in:
            chart_in = build_altair_bar_chart(
                df_budget_in_grouped,
                x_col='BudgetName',
                y_col='AmtIn',
                title='Total Inflow by Budget Group',
                color=COLOR_INFLOW
            )
            st.altair_chart(chart_in, use_container_width=True)

        with col_b_out:
            chart_out = build_altair_bar_chart(
                df_budget_out_grouped,
                x_col='BudgetName',
                y_col='AmtOut',
                title='Total Outflow by Budget Group',
                color=COLOR_OUTFLOW
            )
            st.altair_chart(chart_out, use_container_width=True)
    else:
        st.info("No data available for budget-wise cashflow charts.")

    st.markdown("<br>", unsafe_allow_html=True)

    # --- Category Budget Summary (Month-wise Net Outflows) ---
    st.markdown("<br>## 📊 Month‑wise Net Outflows per Category (by Budget)", unsafe_allow_html=True)
    if not df_filtered.empty:
        # Only consider records where AmtOut > 0
        df_netout_filtered = df_filtered[df_filtered['AmtOut'] > 0].copy()
        if not df_netout_filtered.empty:
            df_netout_filtered['NetOut'] = df_netout_filtered['AmtOut'].fillna(0.0) - df_netout_filtered['AmtIn'].fillna(0.0)
            df_netout_filtered['Month'] = df_netout_filtered['DateT'].dt.to_period('M').astype(str)
            df_budget_month = (
                df_netout_filtered
                .groupby(['BudgetName', 'Month', 'CategoryId', 'CategoryName'])
                .agg({'NetOut': 'sum'})
                .reset_index()
            )
            df_budget_month = df_budget_month[df_budget_month['BudgetName'].notna()]
            # Show sections per BudgetName
            for budget, group in df_budget_month.groupby('BudgetName'): 
                with st.expander(f"**Budget: {budget}**"):
                    pivot = group.pivot(index='CategoryName', columns='Month', values='NetOut').fillna(0.0)
                    st.dataframe(pivot.style.format('{:,.2f}'), hide_index=False)
                    if st.button('Show Total Records', key=f'total_{budget}'):
                        total_detail_df = df_netout_filtered[df_netout_filtered['BudgetName'] == budget][['DateT', 'BankName', 'SBName', 'AmtIn', 'AmtOut', 'Comment']].copy()
                        total_detail_df['DateT'] = pd.to_datetime(total_detail_df['DateT']).dt.strftime('%Y-%m-%d')
                        st.dataframe(total_detail_df.style.format({'AmtIn': lambda x: format_inr(x), 'AmtOut': lambda x: format_inr(x)}), hide_index=True)
                    
                    cat_options = group['CategoryName'].unique().tolist()
                    selected_cat = st.selectbox("Show transactions for category", ["-- Select --"] + cat_options, key=f"detail_{budget}")
                    if selected_cat != "-- Select --":
                        cat_id = group[group['CategoryName'] == selected_cat]['CategoryId'].iloc[0]
                        detail_df = df_netout_filtered[df_netout_filtered['CategoryId'] == cat_id][['DateT', 'BankName', 'SBName', 'AmtIn', 'AmtOut', 'Comment']].copy()
                        detail_df['DateT'] = pd.to_datetime(detail_df['DateT']).dt.strftime('%Y-%m-%d')
                        st.dataframe(detail_df.style.format({'AmtIn': lambda x: format_inr(x), 'AmtOut': lambda x: format_inr(x)}), hide_index=True)
                        
                        if pivot.columns.size > 0:
                            month_options = list(pivot.columns)
                            selected_month = st.selectbox("Show transactions for month", ["-- Select Month --"] + month_options, key=f"month_detail_{budget}")
                            if selected_month != "-- Select Month --":
                                month_detail_df = df_netout_filtered[(df_netout_filtered['BudgetName'] == budget) & (df_netout_filtered['Month'] == selected_month)][['DateT', 'BankName', 'SBName', 'AmtIn', 'AmtOut', 'Comment']].copy()
                                month_detail_df['DateT'] = pd.to_datetime(month_detail_df['DateT']).dt.strftime('%Y-%m-%d')
                                st.dataframe(month_detail_df.style.format({'AmtIn': lambda x: format_inr(x), 'AmtOut': lambda x: format_inr(x)}), hide_index=True)
        else:
            st.info("No records with AmtOut > 0 found for month‑wise analysis.")
    else:
        st.info("No transactions available for month‑wise analysis.")

    viz_col1, viz_col2 = st.columns([1, 2])
    
    with viz_col1:
        st.markdown("### 🏦 Savings Account Balances")
        # Calculate Running Balance for each Bank
        # Bank Balance = Running Total (Inflow) - Running Total (Outflow) for that BankId.
        if df_trans is not None and not df_trans.empty:
            df_full_clean = df_trans.copy()
            df_full_clean['AmtIn'] = df_full_clean['AmtIn'].fillna(0.0).astype(float)
            df_full_clean['AmtOut'] = df_full_clean['AmtOut'].fillna(0.0).astype(float)
            
            st.markdown('<div class="bank-container">', unsafe_allow_html=True)
            for _, b in df_banks.iterrows():
                b_id = b['BankId']
                b_name = b['BankName']
                b_acc = b['AccNo']
                # Use opening balance (before selected date range) and closing balance (end of selected date range)
                opening_bal = db.get_closing_balance(b_id, (start_date - pd.Timedelta(days=1)).strftime('%Y-%m-%d'))
                closing_bal = db.get_closing_balance(b_id, end_date.strftime('%Y-%m-%d'))
                st.markdown(f"""
                <div class="bank-card">
                    <div class="bank-details">
                        <span class="bank-name">{b_name}</span>
                        <span class="bank-acc">Acc No: {b_acc}</span>
                        <span class="bank-acc" style="font-size: 0.7rem; color: #888;">Opening: {format_inr(opening_bal)}</span>
                    </div>
                    <span class="bank-balance" style="color: {'#34d399' if closing_bal >= 0 else '#f87171'};">
                        {format_inr(closing_bal)}
                    </span>
                </div>
                """, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

            
            

        else:
            st.info("No balances available.")
            
    with viz_col2:
        st.markdown("### 📊 Inflow vs Outflow Cashflow Trend")
        if not df_filtered.empty and df_filtered['DateT'].notna().any():
            # Resample by Month
            df_trend = df_filtered.copy()
            df_trend['Month'] = df_trend['DateT'].dt.to_period('M').astype(str)
            df_monthly = df_trend.groupby('Month')[['AmtIn', 'AmtOut']].sum().reset_index()
            df_monthly.rename(columns={'AmtIn': 'Inflow', 'AmtOut': 'Outflow'}, inplace=True)
            
            df_monthly['InflowLabel'] = df_monthly['Inflow'].apply(format_amount_lakh)
            df_monthly['OutflowLabel'] = df_monthly['Outflow'].apply(format_amount_lakh)
            df_monthly['Month'] = df_monthly['Month'].astype(str)

            trend_df = df_monthly.melt(
                id_vars=['Month'],
                value_vars=['Inflow', 'Outflow'],
                var_name='Type',
                value_name='Amount'
            )
            trend_df['AmountLakhs'] = trend_df['Amount'].apply(rupees_to_lakhs)
            trend_df['Label'] = trend_df['Amount'].apply(format_amount_lakh)
            """trend_df['Label'] = trend_df.apply(
                lambda row: row['InflowLabel'] if row['Type'] == 'Inflow' else row['OutflowLabel'],
                axis=1
            )"""

            bar = alt.Chart(trend_df).mark_bar().encode(
                x=alt.X('Month:N', axis=alt.Axis(labelColor='#e2e8f0', titleColor='#94a3b8', title='Month')),
                y=alt.Y('AmountLakhs:Q', axis=alt.Axis(title='Amount (Lakhs)', labelColor='#e2e8f0', titleColor='#94a3b8')),
                color=alt.Color('Type:N', scale=alt.Scale(domain=['Inflow', 'Outflow'], range=[COLOR_INFLOW, COLOR_OUTFLOW]), legend=alt.Legend(title='Cashflow Type')),
                tooltip=[
                    alt.Tooltip('Month:N'),
                    alt.Tooltip('Type:N'),
                    alt.Tooltip('Amount:Q', title='Amount (₹)', format=',.2f'),
                    alt.Tooltip('AmountLakhs:Q', title='Amount (Lakhs)', format='.2f')
                ]
            ).properties(title='Monthly Cashflow Breakdown', height=360)

            labels = bar.mark_text(dy=-10, color='#ffffff', size=12).encode(text='Label:N')
            st.altair_chart(alt.layer(bar, labels).configure_view(stroke='transparent').configure_title(color='#e2e8f0'), use_container_width=True)
        else:
            st.info("Insufficient timeline data to display cashflow trend.")

    # 3. Quick Spend Categories
    st.markdown("### 🏷️ Top Spending Categories")
    if not df_filtered.empty:
        df_top_cats_filtered = df_filtered[
            (df_filtered['AmtOut'] > 0) &
            (df_filtered['BudgetName'].notna()) &
            (df_filtered['BudgetName'].str.strip() != "") &
            (df_filtered['BudgetName'] != "Invest")
        ]
        if not df_top_cats_filtered.empty:
            df_top_cats = df_top_cats_filtered.groupby('CategoryName')['AmtOut'].sum().reset_index().sort_values(by='AmtOut', ascending=False).head(5)
            top_spend_chart = build_altair_bar_chart(
                df_top_cats,
                x_col='CategoryName',
                y_col='AmtOut',
                title='Top Spending Categories',
                color='#f43f5e',
                y_title='Amount (Lakhs)'
            )
            st.altair_chart(top_spend_chart, use_container_width=True)
        else:
            st.info("No spending data available for Top Spending Categories (excluding Investment and Uncategorized).")
    else:
        st.info("No expense data available for categorization.")

    # 4. Budget Quick Check Progress
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### 🎯 Monthly Budget Threshold Tracker")
    
    if not df_filtered.empty and df_cats is not None and not df_cats.empty:
        # Sum spending by category in the selected timeframe
        df_spent_by_cat = df_filtered.groupby('CategoryId')[['AmtOut']].sum().reset_index()
        
        # Merge with all categories
        df_budget_progress = pd.merge(df_cats, df_spent_by_cat, on='CategoryId', how='left').fillna(0.0)
        
        # Calculate budget limits
        df_budget_progress['Budget'] = df_budget_progress['CategoryId'].map(st.session_state.budgets).fillna(500.0)
        df_budget_progress['Percentage'] = (df_budget_progress['AmtOut'] / df_budget_progress['Budget'] * 100).round(1)
        
        # Grid of budgets
        budget_cols = st.columns(4)
        for idx, row in df_budget_progress.iterrows():
            col_slot = budget_cols[idx % 4]
            with col_slot:
                pct = row['Percentage']
                progress_val = min(pct / 100.0, 1.0)
                
                # Check status
                if pct > 100:
                    status_text = f"🚨 Over budget by {format_inr(row['AmtOut'] - row['Budget'])}"
                    progress_color = "red"
                elif pct >= 85:
                    status_text = "⚠️ Warning: Near budget threshold"
                    progress_color = "orange"
                else:
                    status_text = "✅ Safe range"
                    progress_color = "green"
                
                with st.container(border=True):
                    st.write(f"**{row['CategoryName']}**")
                    st.caption(f"{row['CategoryDesc'] or 'No description'}")
                    st.progress(progress_val)
                    st.markdown(
                        f"<div style='display:flex; justify-content:space-between; font-size:0.8rem;'>"
                        f"<span>Spent: <b>{format_inr(row['AmtOut'])}</b></span>"
                        f"<span>Limit: <b>{format_inr(row['Budget'])}</b></span>"
                        f"</div>", 
                        unsafe_allow_html=True
                    )
                    st.caption(f"{status_text} ({pct}%)")

# ==========================================
# 📈 TAB 2: INCOME ANALYSIS
with tab_income:
    st.markdown("## 📈 Income & Earning Analysis")
    st.caption("Trace your primary cash flow sources and analyze growth in earnings over time.")
    st.markdown("<hr style='margin-top: 0.25rem; margin-bottom: 1.5rem; border-color: rgba(255,255,255,0.05);'>", unsafe_allow_html=True)
    
    # Filter only records where BudgetName is 'Earn'
    earn_records = df_filtered[(df_filtered['AmtIn'] > 0) & (df_filtered['BudgetName'] == "Earn")]
    
    if not earn_records.empty:
        inc_df = earn_records.copy()
        
        # Group by CategoryName (Source Names derived from Category Table)
        df_inc_cat = inc_df.groupby('CategoryName')['AmtIn'].sum().reset_index()
        
        inc_col1, inc_col2 = st.columns([1, 1])
        
        with inc_col1:
            st.markdown("### 🍩 Earning Allocation by Category")
            fig_inc_donut = px.pie(
                df_inc_cat, 
                values='AmtIn', 
                names='CategoryName',
                hole=0.5,
                color_discrete_sequence=px.colors.sequential.Greens
            )
            fig_inc_donut.update_traces(textposition='inside', textinfo='percent+label')
            style_chart(fig_inc_donut)
            
            # Interactive Donut Chart Selection
            event = st.plotly_chart(fig_inc_donut, use_container_width=True, on_select="rerun", key="earnings_donut_chart")
            
        selected_earning_cat = None
        if event and hasattr(event, "selection") and event.selection:
            indices = event.selection.point_indices
            points = event.selection.points
            if indices:
                clicked_idx = indices[0]
                if clicked_idx < len(df_inc_cat):
                    selected_earning_cat = df_inc_cat.iloc[clicked_idx]['CategoryName']
            elif points:
                selected_earning_cat = points[0].get("label") or points[0].get("legendgroup")
                
        if selected_earning_cat:
            st.info(f"Filtering results by category: **{selected_earning_cat}** (Click the slice again to reset filter)")
            
        with inc_col2:
            st.markdown("### 📈 Monthly Earnings Inflow Trend")
            df_inc_trend = inc_df.copy()
            if selected_earning_cat:
                df_inc_trend = df_inc_trend[df_inc_trend['CategoryName'] == selected_earning_cat]
                
            df_inc_trend['Month'] = df_inc_trend['DateT'].dt.to_period('M').astype(str)
            df_inc_monthly = df_inc_trend.groupby('Month')['AmtIn'].sum().reset_index()
            
            if not df_inc_monthly.empty:
                fig_inc_trend = px.area(
                    df_inc_monthly, 
                    x='Month', 
                    y='AmtIn',
                    color_discrete_sequence=[COLOR_INFLOW],
                    labels={'AmtIn': 'Total Earnings (₹)'}
                )
                style_chart(fig_inc_trend)
                st.plotly_chart(fig_inc_trend, use_container_width=True)
            else:
                st.info("No timeline trend data available for this selection.")
            
        st.markdown("### 📋 Earning Ledger List")
        # Display income transaction list
        display_cols = ['DateT', 'BankName', 'CategoryName', 'SBName', 'AmtIn', 'Comment']
        inc_display = inc_df[display_cols].copy()
        if selected_earning_cat:
            inc_display = inc_display[inc_display['CategoryName'] == selected_earning_cat]
            
        inc_display = inc_display.sort_values(by='DateT', ascending=False)
        inc_display['DateT'] = inc_display['DateT'].dt.strftime('%Y-%m-%d')
        
        st.dataframe(
            inc_display.style.format({'AmtIn': lambda x: format_inr(x)}), 
            use_container_width=True,
            hide_index=True
        )
        
        # YoY Earnings Section
        st.markdown("<br>### 📅 Year on Year (YoY) Earnings", unsafe_allow_html=True)
        df_yoy_base = df_trans[df_trans['AmtIn'] > 0].copy()
        df_yoy_base['BudgetName'] = df_yoy_base['BudgetName'].fillna("")
        df_yoy_base = df_yoy_base[df_yoy_base['BudgetName'].str.strip() == "Earn"]
        
        # Apply sidebar bank filters
        if selected_banks:
            df_yoy_base = df_yoy_base[df_yoy_base['BankName'].isin(selected_banks)]
            
        # Apply sidebar category filters
        if selected_categories:
            df_yoy_base = df_yoy_base[df_yoy_base['CategoryName'].isin(selected_categories)]
            
        # Apply selected donut slice filter
        if selected_earning_cat:
            df_yoy_base = df_yoy_base[df_yoy_base['CategoryName'] == selected_earning_cat]
            
        if not df_yoy_base.empty:
            df_yoy_base['Year'] = df_yoy_base['DateT'].dt.year.astype(str)
            df_yoy = df_yoy_base.groupby('Year')['AmtIn'].sum().reset_index()
            df_yoy.rename(columns={'AmtIn': 'Earnings'}, inplace=True)
            df_yoy = df_yoy.sort_values('Year')
            
            yoy_chart = build_altair_bar_chart(
                df_yoy,
                x_col='Year',
                y_col='Earnings',
                title=f"Year on Year (YoY) Earnings {'- ' + selected_earning_cat if selected_earning_cat else ''}",
                color=COLOR_INFLOW,
                y_title='Amount (Lakhs)'
            )
            st.altair_chart(yoy_chart, use_container_width=True)
        else:
            st.info("No historical earnings data available for YoY analysis.")
    else:
        st.info("No positive income / earning records with BudgetName 'Earn' found in the filtered timeline.")

# ==========================================
# 💸 TAB 3: SPENDING ANALYSIS & BUDGETS
# ==========================================
with tab_spending:
    st.markdown("## 💸 Spending, Outflow & Budget Analysis")
    st.caption("Discover where your capital flows. Compare category spending directly against budget limits.")
    st.markdown("<hr style='margin-top: 0.25rem; margin-bottom: 1.5rem; border-color: rgba(255,255,255,0.05);'>", unsafe_allow_html=True)

    # --- Initialize drill-down session state keys ---
    for _skey in ["sb_drill_budget", "sb_drill_cat", "sb_drill_month", "sb_monthly_drill_month"]:
        if _skey not in st.session_state:
            st.session_state[_skey] = None

    # Filter only records whose Category's BudgetName is not null and not "Invest"
    spend_records = df_filtered[
        (df_filtered['AmtOut'] > 0) &
        (df_filtered['BudgetName'].notna()) &
        (df_filtered['BudgetName'].str.strip() != "") &
        (df_filtered['BudgetName'] != "Invest")
    ]

    if not spend_records.empty:
        spend_df = spend_records.copy()

        # Group by CategoryName (Expenses)
        df_spend_cat = spend_df.groupby('CategoryName')['AmtOut'].sum().reset_index()

        spend_col1, spend_col2 = st.columns([1, 1])

        with spend_col1:
            st.markdown("### 🍩 Operational Expenses by Category")
            fig_spend_donut = px.pie(
                df_spend_cat,
                values='AmtOut',
                names='CategoryName',
                hole=0.5,
                color_discrete_sequence=px.colors.sequential.Reds
            )
            fig_spend_donut.update_traces(textposition='inside', textinfo='percent+label')
            style_chart(fig_spend_donut)

            # Interactive Donut Selection
            donut_event = st.plotly_chart(
                fig_spend_donut, use_container_width=True,
                on_select="rerun", key="spending_donut_chart"
            )

        selected_spending_cat = None
        if donut_event and hasattr(donut_event, "selection") and donut_event.selection:
            d_indices = donut_event.selection.point_indices
            d_points = donut_event.selection.points
            if d_indices:
                clicked_idx = d_indices[0]
                if clicked_idx < len(df_spend_cat):
                    selected_spending_cat = df_spend_cat.iloc[clicked_idx]['CategoryName']
            elif d_points:
                selected_spending_cat = d_points[0].get("label") or d_points[0].get("legendgroup")

        if selected_spending_cat:
            st.info(f"Filtering results by category: **{selected_spending_cat}** (Click the slice again to reset filter)")

        # ================================================================
        # INTERACTIVE MONTHLY SPENDING OUTFLOW TREND (2-level drill-down)
        # ================================================================
        with spend_col2:
            st.markdown("### 📉 Monthly Spending Outflow Trend")
            df_spend_trend = spend_df.copy()
            if selected_spending_cat:
                df_spend_trend = df_spend_trend[df_spend_trend['CategoryName'] == selected_spending_cat]
            df_spend_trend['Month'] = df_spend_trend['DateT'].dt.to_period('M').astype(str)

            if st.session_state.sb_monthly_drill_month is None:
                # Level 0 — Monthly total bar chart
                df_spend_monthly = (
                    df_spend_trend.groupby('Month')['AmtOut']
                    .sum().reset_index()
                    .sort_values('Month')
                )
                if not df_spend_monthly.empty:
                    df_spend_monthly['AmountLakhs'] = df_spend_monthly['AmtOut'].apply(rupees_to_lakhs)
                    df_spend_monthly['Label'] = df_spend_monthly['AmtOut'].apply(format_amount_lakh)

                    fig_monthly_bar = go.Figure()
                    fig_monthly_bar.add_trace(go.Bar(
                        x=df_spend_monthly['Month'],
                        y=df_spend_monthly['AmountLakhs'],
                        marker_color=COLOR_OUTFLOW,
                        text=df_spend_monthly['Label'],
                        textposition='outside',
                        customdata=df_spend_monthly[['AmtOut']].values,
                        hovertemplate='<b>%{x}</b><br>₹%{customdata[0]:,.2f}<extra></extra>'
                    ))
                    fig_monthly_bar.update_layout(
                        title='Monthly Outflow — Click a bar to see categories',
                        xaxis_title='Month',
                        yaxis_title='Amount (Lakhs)',
                        height=360
                    )
                    style_chart(fig_monthly_bar)

                    monthly_event = st.plotly_chart(
                        fig_monthly_bar,
                        use_container_width=True,
                        on_select="rerun",
                        key="monthly_trend_bar"
                    )

                    if monthly_event and hasattr(monthly_event, "selection") and monthly_event.selection:
                        m_pts = monthly_event.selection.points
                        if m_pts:
                            clicked_mth = m_pts[0].get("x")
                            if clicked_mth:
                                st.session_state.sb_monthly_drill_month = str(clicked_mth)[:7]  # Ensure it's in YYYY-MM format
                                st.rerun()
                else:
                    st.info("No timeline trend data available for this selection.")

            else:
                # Level 1 — Category breakdown for the drilled month
                drill_mth = st.session_state.sb_monthly_drill_month
                if st.button("← Back to Monthly", key="back_monthly_trend"):
                    st.session_state.sb_monthly_drill_month = None
                    st.rerun()
                st.caption(f"Showing categories in **{drill_mth}**")

                df_month_cats_grp = (
                    df_spend_trend[df_spend_trend['Month'] == drill_mth]
                    .groupby('CategoryName')['AmtOut']
                    .sum().reset_index()
                    .sort_values('AmtOut', ascending=False)
                )

                if not df_month_cats_grp.empty:
                    df_month_cats_grp['AmountLakhs'] = df_month_cats_grp['AmtOut'].apply(rupees_to_lakhs)
                    df_month_cats_grp['Label'] = df_month_cats_grp['AmtOut'].apply(format_amount_lakh)

                    fig_month_cat = go.Figure()
                    fig_month_cat.add_trace(go.Bar(
                        x=df_month_cats_grp['CategoryName'],
                        y=df_month_cats_grp['AmountLakhs'],
                        marker=dict(
                            color=df_month_cats_grp['AmountLakhs'],
                            colorscale='Oranges',
                            showscale=False
                        ),
                        text=df_month_cats_grp['Label'],
                        textposition='outside',
                        customdata=df_month_cats_grp[['AmtOut']].values,
                        hovertemplate='<b>%{x}</b><br>₹%{customdata[0]:,.2f}<extra></extra>'
                    ))
                    fig_month_cat.update_layout(
                        title=f'Category Breakdown — {drill_mth}',
                        xaxis_title='Category',
                        yaxis_title='Amount (Lakhs)',
                        height=360
                    )
                    style_chart(fig_month_cat)
                    st.plotly_chart(fig_month_cat, use_container_width=True, key="monthly_cat_bar")
                else:
                    st.info(f"No spending data for {drill_mth}.")

        # ================================================================
        # INTERACTIVE SPENDING DRILL-DOWN (replaces flat Spending Ledger)
        # ================================================================
        st.markdown("### 📊 Spending Drill-Down")

        if st.session_state.sb_drill_budget is None:
            # ---- Level 0: BudgetName bars ----
            df_by_budget = (
                spend_df.groupby('BudgetName')['AmtOut']
                .sum().reset_index()
                .sort_values('AmtOut', ascending=False)
            )
            df_by_budget['AmountLakhs'] = df_by_budget['AmtOut'].apply(rupees_to_lakhs)
            df_by_budget['Label'] = df_by_budget['AmtOut'].apply(format_amount_lakh)

            fig_budget_bars = go.Figure()
            fig_budget_bars.add_trace(go.Bar(
                x=df_by_budget['BudgetName'],
                y=df_by_budget['AmountLakhs'],
                marker=dict(
                    color=df_by_budget['AmountLakhs'],
                    colorscale='Reds',
                    showscale=False
                ),
                text=df_by_budget['Label'],
                textposition='outside',
                customdata=df_by_budget[['AmtOut']].values,
                hovertemplate='<b>%{x}</b><br>Total Spending: ₹%{customdata[0]:,.2f}<extra></extra>'
            ))
            fig_budget_bars.update_layout(
                title='Spending by Budget Group — Click a bar to drill into categories',
                xaxis_title='Budget Group',
                yaxis_title='Amount (Lakhs)',
                height=420
            )
            style_chart(fig_budget_bars)

            budget_event = st.plotly_chart(
                fig_budget_bars,
                use_container_width=True,
                on_select="rerun",
                key="budget_drill_bar"
            )

            if budget_event and hasattr(budget_event, "selection") and budget_event.selection:
                b_pts = budget_event.selection.points
                if b_pts:
                    clicked_budget = b_pts[0].get("x")
                    if clicked_budget:
                        st.session_state.sb_drill_budget = str(clicked_budget)
                        st.session_state.sb_drill_cat = None
                        st.session_state.sb_drill_month = None
                        st.rerun()

        elif st.session_state.sb_drill_cat is None:
            # ---- Level 1: Category bars within the selected Budget ----
            drill_budget = st.session_state.sb_drill_budget
            nav_col, info_col = st.columns([1, 6])
            with nav_col:
                if st.button("← Budgets", key="back_to_budgets"):
                    st.session_state.sb_drill_budget = None
                    st.rerun()
            with info_col:
                st.caption(f"Budget: **{drill_budget}** — Click a category bar to see its monthly trend")

            df_by_cat = (
                spend_df[spend_df['BudgetName'] == drill_budget]
                .groupby('CategoryName')['AmtOut']
                .sum().reset_index()
                .sort_values('AmtOut', ascending=False)
            )
            df_by_cat['AmountLakhs'] = df_by_cat['AmtOut'].apply(rupees_to_lakhs)
            df_by_cat['Label'] = df_by_cat['AmtOut'].apply(format_amount_lakh)

            fig_cat_bars = go.Figure()
            fig_cat_bars.add_trace(go.Bar(
                x=df_by_cat['CategoryName'],
                y=df_by_cat['AmountLakhs'],
                marker=dict(
                    color=df_by_cat['AmountLakhs'],
                    colorscale='Oranges',
                    showscale=False
                ),
                text=df_by_cat['Label'],
                textposition='outside',
                customdata=df_by_cat[['AmtOut']].values,
                hovertemplate='<b>%{x}</b><br>Total: ₹%{customdata[0]:,.2f}<extra></extra>'
            ))
            fig_cat_bars.update_layout(
                title=f'Categories in "{drill_budget}"',
                xaxis_title='Category',
                yaxis_title='Amount (Lakhs)',
                height=420
            )
            style_chart(fig_cat_bars)

            cat_event = st.plotly_chart(
                fig_cat_bars,
                use_container_width=True,
                on_select="rerun",
                key="cat_drill_bar"
            )

            if cat_event and hasattr(cat_event, "selection") and cat_event.selection:
                c_pts = cat_event.selection.points
                if c_pts:
                    clicked_cat = c_pts[0].get("x")
                    if clicked_cat:
                        st.session_state.sb_drill_cat = str(clicked_cat)
                        st.session_state.sb_drill_month = None
                        st.rerun()

        else:
            # ---- Level 2: Monthly line chart for the selected Category ----
            drill_budget = st.session_state.sb_drill_budget
            drill_cat = st.session_state.sb_drill_cat

            nav_col1, nav_col2, info_col = st.columns([1, 1, 5])
            with nav_col1:
                if st.button("← Budgets", key="back_to_budgets2"):
                    st.session_state.sb_drill_budget = None
                    st.session_state.sb_drill_cat = None
                    st.session_state.sb_drill_month = None
                    st.rerun()
            with nav_col2:
                if st.button(f"← {drill_budget}", key="back_to_cats"):
                    st.session_state.sb_drill_cat = None
                    st.session_state.sb_drill_month = None
                    st.rerun()
            with info_col:
                st.caption(f"**{drill_budget}** → **{drill_cat}** — Click a point on the chart to see individual records")

            df_cat_filtered = spend_df[
                (spend_df['BudgetName'] == drill_budget) &
                (spend_df['CategoryName'] == drill_cat)
            ].copy()
            df_cat_filtered['Month'] = df_cat_filtered['DateT'].dt.to_period('M').astype(str)
            df_cat_monthly = (
                df_cat_filtered.groupby('Month')['AmtOut']
                .sum().reset_index()
                .sort_values('Month')
            )

            if not df_cat_monthly.empty:
                df_cat_monthly['AmountLakhs'] = df_cat_monthly['AmtOut'].apply(rupees_to_lakhs)
                df_cat_monthly['Label'] = df_cat_monthly['AmtOut'].apply(format_amount_lakh)

                fig_cat_line = go.Figure()
                fig_cat_line.add_trace(go.Scatter(
                    x=df_cat_monthly['Month'],
                    y=df_cat_monthly['AmountLakhs'],
                    mode='lines+markers+text',
                    line=dict(color=COLOR_OUTFLOW, width=2),
                    marker=dict(size=10, color=COLOR_OUTFLOW, line=dict(color='white', width=2)),
                    text=df_cat_monthly['Label'],
                    textposition='top center',
                    customdata=df_cat_monthly[['AmtOut']].values,
                    hovertemplate='<b>%{x}</b><br>₹%{customdata[0]:,.2f}<extra></extra>',
                    name=drill_cat
                ))
                fig_cat_line.update_layout(
                    title=f'Monthly Spending — {drill_cat} (Click a point to view records)',
                    xaxis_title='Month',
                    yaxis_title='Amount (Lakhs)',
                    height=420
                )
                style_chart(fig_cat_line)

                line_event = st.plotly_chart(
                    fig_cat_line,
                    use_container_width=True,
                    on_select="rerun",
                    key="cat_line_chart"
                )

                if line_event and hasattr(line_event, "selection") and line_event.selection:
                    l_pts = line_event.selection.points
                    if l_pts:
                        clicked_month_pt = l_pts[0].get("x")
                        if clicked_month_pt:
                            st.session_state.sb_drill_month = str(clicked_month_pt)[:7]  # Extract YYYY-MM
                            # st.rerun()
                    else:
                        # Optional: If the user clicks empty space, clear the table
                        st.session_state.sb_drill_month = None
            else:
                st.info(f"No monthly data found for {drill_cat}.")

            # ---- Level 3: Editable records table for the clicked line point ----
            if st.session_state.sb_drill_month:
                drill_month = st.session_state.sb_drill_month
                st.markdown(f"#### 📋 Records: **{drill_cat}** in **{drill_month}**")
                st.caption("Edit the Category column using the dropdown below, then click **Save Changes** to write back to the database.")

                df_point_records = df_cat_filtered[df_cat_filtered['Month'] == drill_month].copy()

                if not df_point_records.empty:
                    all_cat_names = sorted(df_cats['CategoryName'].tolist()) if (df_cats is not None and not df_cats.empty) else []

                    edit_cols = ['SBId', 'DateT', 'BankName', 'CategoryName', 'SBName', 'AmtOut', 'Comment']
                    df_editable = df_point_records[edit_cols].copy()
                    df_editable['DateT'] = df_editable['DateT'].dt.strftime('%Y-%m-%d')
                    df_editable_sorted = df_editable.sort_values('DateT').reset_index(drop=True)

                    edited_df = st.data_editor(
                        df_editable_sorted,
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            'SBId': st.column_config.NumberColumn('ID', disabled=True),
                            'DateT': st.column_config.TextColumn('Date', disabled=True),
                            'BankName': st.column_config.TextColumn('Bank', disabled=True),
                            'CategoryName': st.column_config.SelectboxColumn(
                                'Category',
                                options=all_cat_names,
                                required=True
                            ),
                            'SBName': st.column_config.TextColumn('Payee / Merchant', disabled=True),
                            'AmtOut': st.column_config.NumberColumn(
                                'Amount Out (₹)', disabled=True, format='₹%.2f'
                            ),
                            'Comment': st.column_config.TextColumn('Comment', disabled=True),
                        },
                        key="spend_edit_table"
                    )

                    if st.button("💾 Save Category Changes", key="save_cat_changes"):
                        changes_made = 0
                        save_errors = []
                        for i, orig_row in df_editable_sorted.iterrows():
                            sb_id = int(orig_row['SBId'])
                            orig_cat_name = orig_row['CategoryName']
                            new_cat_name = edited_df.loc[i, 'CategoryName']

                            if new_cat_name != orig_cat_name:
                                cat_row = df_cats[df_cats['CategoryName'] == new_cat_name]
                                if not cat_row.empty:
                                    new_cat_id = int(cat_row.iloc[0]['CategoryId'])
                                    full_orig = df_point_records[df_point_records['SBId'] == sb_id]
                                    if not full_orig.empty:
                                        r = full_orig.iloc[0]
                                        success = db.update_transaction(
                                            sb_id,
                                            int(r['BankId']),
                                            str(r['SBName'] or ''),
                                            float(r['AmtIn'] or 0.0),
                                            float(r['AmtOut'] or 0.0),
                                            new_cat_id,
                                            str(r['Comment'] or ''),
                                            pd.to_datetime(r['DateT']).strftime('%Y-%m-%d')
                                        )
                                        if success:
                                            changes_made += 1
                                        else:
                                            save_errors.append(sb_id)

                        if changes_made > 0:
                            st.success(f"✅ Updated {changes_made} record(s) successfully.")
                            st.rerun()
                        elif save_errors:
                            st.error(f"Failed to update records with IDs: {save_errors}")
                        else:
                            st.info("No category changes detected.")
                else:
                    st.info(f"No records found for {drill_cat} in {drill_month}.")

        # YoY Spending Section
        st.markdown("<br>### 📅 Year on Year (YoY) Spending", unsafe_allow_html=True)
        df_yoy_spend_base = df_trans[df_trans['AmtOut'] > 0].copy()
        df_yoy_spend_base['BudgetName'] = df_yoy_spend_base['BudgetName'].fillna("")
        df_yoy_spend_base = df_yoy_spend_base[
            (df_yoy_spend_base['BudgetName'].str.strip() != "") &
            (df_yoy_spend_base['BudgetName'] != "Invest")
        ]

        # Apply sidebar bank filters
        if selected_banks:
            df_yoy_spend_base = df_yoy_spend_base[df_yoy_spend_base['BankName'].isin(selected_banks)]

        # Apply sidebar category filters
        if selected_categories:
            df_yoy_spend_base = df_yoy_spend_base[df_yoy_spend_base['CategoryName'].isin(selected_categories)]

        # Apply selected donut slice filter
        if selected_spending_cat:
            df_yoy_spend_base = df_yoy_spend_base[df_yoy_spend_base['CategoryName'] == selected_spending_cat]

        if not df_yoy_spend_base.empty:
            df_yoy_spend_base['Year'] = df_yoy_spend_base['DateT'].dt.year.astype(str)
            df_yoy_spend = df_yoy_spend_base.groupby('Year')['AmtOut'].sum().reset_index()
            df_yoy_spend.rename(columns={'AmtOut': 'Spending'}, inplace=True)
            df_yoy_spend = df_yoy_spend.sort_values('Year')

            yoy_spend_chart = build_altair_bar_chart(
                df_yoy_spend,
                x_col='Year',
                y_col='Spending',
                title=f"Year on Year (YoY) Spending {'- ' + selected_spending_cat if selected_spending_cat else ''}",
                color=COLOR_OUTFLOW,
                y_title='Amount (Lakhs)'
            )
            st.altair_chart(yoy_spend_chart, use_container_width=True)
        else:
            st.info("No historical spending data available for YoY analysis.")

        st.markdown("<br><hr style='border-color: rgba(255,255,255,0.05);'><br>", unsafe_allow_html=True)
        st.markdown("## 🎯 Budget Configuration & Breakdown")

        # Interactive budget config section and breakdown table at the bottom
        cols_config1, cols_config2 = st.columns([1, 1])

        with cols_config1:
            st.markdown("### 🛠️ Interactive Category Budget Configuration")
            st.write("Configure maximum monthly spend parameters. Progress bars adjust automatically.")

            if df_cats is not None and not df_cats.empty:
                cols_b1, cols_b2 = st.columns(2)
                for i, row in df_cats.iterrows():
                    c_id = int(row['CategoryId'])
                    c_name = row['CategoryName']

                    target_col = cols_b1 if i % 2 == 0 else cols_b2
                    with target_col:
                        st.session_state.budgets[c_id] = st.number_input(
                            f"Monthly Budget: {c_name}",
                            min_value=0.0,
                            max_value=100000.0,
                            value=float(st.session_state.budgets.get(c_id, 500.0)),
                            step=50.0,
                            key=f"input_bud_{c_id}"
                        )
            else:
                st.info("No categories registered yet.")

        with cols_config2:
            st.markdown("### 📊 Budget vs. Actual Breakdown")
            if df_cats is not None and not df_cats.empty:
                df_spent_by_cat = spend_df.groupby('CategoryId')[['AmtOut']].sum().reset_index()
                df_b_table = pd.merge(df_cats, df_spent_by_cat, on='CategoryId', how='left').fillna(0.0)
                df_b_table['BudgetLimit'] = df_b_table['CategoryId'].map(st.session_state.budgets).fillna(500.0)
                df_b_table['Status'] = df_b_table['BudgetLimit'] - df_b_table['AmtOut']
                df_b_table['Progress %'] = ((df_b_table['AmtOut'] / df_b_table['BudgetLimit']) * 100).round(1)

                df_b_display = df_b_table[['CategoryName', 'BudgetName', 'AmtOut', 'BudgetLimit', 'Status', 'Progress %']]
                df_b_display.rename(columns={
                    'CategoryName': 'Category',
                    'BudgetName': 'Budget Group',
                    'AmtOut': 'Spent Actual',
                    'BudgetLimit': 'Budget Limit',
                    'Status': 'Remaining Balance'
                }, inplace=True)

                def style_budget_rows(val):
                    color = '#f87171' if val > 100 else '#34d399'
                    return f'color: {color}; font-weight: bold;'

                st.dataframe(
                    df_b_display.style.format({
                        'Spent Actual': lambda x: format_inr(x),
                        'Budget Limit': lambda x: format_inr(x),
                        'Remaining Balance': lambda x: format_inr(x),
                        'Progress %': '{:.1f}%'
                    }).map(style_budget_rows, subset=['Progress %']),
                    use_container_width=True,
                    hide_index=True
                )
    else:
        st.info("No expense / spending outflow records (excluding Investment and Uncategorized) found in the filtered timeline.")


# ==========================================
# 🛡️ TAB 4: INVESTMENTS & WEALTH
# ==========================================
with tab_invest:
    st.markdown("## 🛡️ Asset Allocation & Wealth Accumulation")
    st.caption("Track capital allocation to assets and watch your net worth accumulate over multiple years.")
    st.markdown("<hr style='margin-top: 0.25rem; margin-bottom: 1.5rem; border-color: rgba(255,255,255,0.05);'>", unsafe_allow_html=True)
    
    inv_col1, inv_col2 = st.columns([1, 1])
    
    with inv_col1:
        st.markdown("### 🍩 Asset / Investment Allocation")
        if not df_filtered.empty and total_invested > 0:
            df_inv = df_filtered[df_filtered['IsInvestment'] & (df_filtered['AmtOut'] > 0)]
            df_inv_cat = df_inv.groupby('CategoryName')['AmtOut'].sum().reset_index()
            
            fig_inv_donut = px.pie(
                df_inv_cat, 
                values='AmtOut', 
                names='CategoryName',
                hole=0.5,
                color_discrete_sequence=px.colors.sequential.Blues
            )
            fig_inv_donut.update_traces(textposition='inside', textinfo='percent+label')
            style_chart(fig_inv_donut)
            st.plotly_chart(fig_inv_donut, use_container_width=True)
        else:
            st.info("No active investments detected in filtered data. Note: Investment categories are detected automatically by looking for terms like 'Invest', 'Stock', 'Crypto', 'SIP' etc. in Category or Budget Names.")
            
    with inv_col2:
        st.markdown("### 📈 Cumulative Invested Capital Growth")
        if not df_trans.empty:
            # We calculate this using the complete database for full historical scope
            df_full_sorted = df_trans.copy().sort_values('DateT')
            df_full_sorted['AmtOut'] = df_full_sorted['AmtOut'].fillna(0.0).astype(float)
            df_full_sorted['IsInvestment'] = df_full_sorted.apply(is_investment_row, axis=1)
            
            df_full_sorted['CumulativeInvestments'] = df_full_sorted[df_full_sorted['IsInvestment']]['AmtOut'].cumsum()
            # Forward fill cumulative sum to account for days without transactions
            df_full_sorted['CumulativeInvestments'] = df_full_sorted['CumulativeInvestments'].ffill().fillna(0.0)
            
            fig_cum_inv = px.line(
                df_full_sorted,
                x='DateT',
                y='CumulativeInvestments',
                color_discrete_sequence=[COLOR_INVEST],
                labels={'CumulativeInvestments': 'Total Capital Invested (₹)'}
            )
            style_chart(fig_cum_inv)
            st.plotly_chart(fig_cum_inv, use_container_width=True)
            
    # Wealth Growth Accumulation Trend (Net balance of all bank accounts over time)
    st.markdown("<br>### 🪙 Running Net Worth (Cumulative Net Inflow Growth)", unsafe_allow_html=True)
    if not df_trans.empty:
        df_net_worth = df_trans.copy().sort_values('DateT')
        df_net_worth['AmtIn'] = df_net_worth['AmtIn'].fillna(0.0).astype(float)
        df_net_worth['AmtOut'] = df_net_worth['AmtOut'].fillna(0.0).astype(float)
        df_net_worth['NetChange'] = df_net_worth['AmtIn'] - df_net_worth['AmtOut']
        df_net_worth['CumulativeNetBalance'] = df_net_worth['NetChange'].cumsum()
        
        fig_net_worth = px.area(
            df_net_worth,
            x='DateT',
            y='CumulativeNetBalance',
            color_discrete_sequence=[COLOR_ACCENT],
            labels={'CumulativeNetBalance': 'Total Net Account Balances (₹)'}
        )
        style_chart(fig_net_worth)
        st.plotly_chart(fig_net_worth, use_container_width=True)

# ==========================================
# 📋 TAB 5: TRANSACTION LEDGER & EDITOR
# ==========================================
with tab_ledger:
    st.markdown("## 📋 Transaction Ledger & Database Management")
    st.caption("Browse all raw data records and use write-back forms to modify banks, categories, and transactions.")
    st.markdown("<hr style='margin-top: 0.25rem; margin-bottom: 1.5rem; border-color: rgba(255,255,255,0.05);'>", unsafe_allow_html=True)
    
    # 1. Primary Filterable Ledger
    st.markdown("### 🔍 Search & Filter Ledger Table")
    search_query = st.text_input("Search transactions by comment, category, or merchant description", "")
    
    df_ledger_display = df_filtered.copy()
    if not df_ledger_display.empty:
        if search_query:
            df_ledger_display = df_ledger_display[
                df_ledger_display['SBName'].astype(str).str.contains(search_query, case=False) |
                df_ledger_display['Comment'].astype(str).str.contains(search_query, case=False) |
                df_ledger_display['CategoryName'].astype(str).str.contains(search_query, case=False)
            ]
        
        # Prepare for nice looking table
        df_ledger_display['DateT'] = df_ledger_display['DateT'].dt.strftime('%Y-%m-%d')
        df_ledger_display = df_ledger_display.fillna("")
        
        ledger_cols = ['SBId', 'DateT', 'BankName', 'CategoryName', 'SBName', 'AmtIn', 'AmtOut', 'Comment']
        st.dataframe(
            df_ledger_display[ledger_cols].style.format({
                'AmtIn': lambda x: format_inr(x) if isinstance(x, (int, float)) and x > 0 else "-",
                'AmtOut': lambda x: format_inr(x) if isinstance(x, (int, float)) and x > 0 else "-"
            }),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No ledger items found.")
        
    st.markdown("<br><hr style='border-color: rgba(255,255,255,0.05);'><br>", unsafe_allow_html=True)
    
    # 2. Database Write-Back Editors (Forms)
    st.markdown("### 🛠️ Write-Back Database Editor Operations")
    
    editor_tab_trans, editor_tab_bank, editor_tab_cat = st.tabs([
        "✏️ Manage Transactions", 
        "🏦 Manage Bank Accounts", 
        "🏷️ Manage Categories"
    ])
    
    # --- Form: Manage Transactions ---
    with editor_tab_trans:
        action_opt = st.radio("Choose Action", ["Add New Transaction", "Edit Existing Transaction", "Delete Transaction"], horizontal=True)
        
        if action_opt == "Add New Transaction":
            if (df_banks is None or df_banks.empty) or (df_cats is None or df_cats.empty):
                st.warning("⚠️ You must have at least one Bank and one Category before creating transactions.")
            else:
                with st.form("add_transaction_form"):
                    st.write("#### Add a New Transaction")
                    col_t1, col_t2 = st.columns(2)
                    with col_t1:
                        t_date = st.date_input("Transaction Date", datetime.now())
                        # Dropdown for Bank
                        bank_dict = dict(zip(df_banks['BankName'], df_banks['BankId']))
                        t_bank_name = st.selectbox("Select Bank Account", list(bank_dict.keys()))
                        t_bank_id = bank_dict[t_bank_name]
                        # Dropdown for Category
                        cat_dict = dict(zip(df_cats['CategoryName'], df_cats['CategoryId']))
                        t_cat_name = st.selectbox("Select Category", list(cat_dict.keys()))
                        t_cat_id = cat_dict[t_cat_name]
                    with col_t2:
                        t_name = st.text_input("Payee / Merchant Name (SBName)", max_chars=300)
                        t_in = st.number_input("Inflow Amount (AmtIn)", min_value=0.0, value=0.0, step=10.0)
                        t_out = st.number_input("Outflow Amount (AmtOut)", min_value=0.0, value=0.0, step=10.0)
                        t_comment = st.text_input("Comment", max_chars=300)
                        
                    submit_btn = st.form_submit_button("Add Transaction ⚡")
                    if submit_btn:
                        new_id = db.add_transaction(t_bank_id, t_name, t_in, t_out, t_cat_id, t_comment, t_date.strftime('%Y-%m-%d'))
                        st.success(f"Added transaction successfully (ID: {new_id})")
                        st.rerun()
                        
        elif action_opt == "Edit Existing Transaction":
            if df_trans.empty:
                st.info("No transactions to edit.")
            else:
                # Select transaction to edit
                # Display transactions list
                trans_map = {}
                for idx, row in df_trans.iterrows():
                    val = f"ID: {row['SBId']} | {row['DateT'].strftime('%Y-%m-%d') if pd.notna(row['DateT']) else ''} | {row['CategoryName']} | {row['SBName']} | In: {format_inr(row['AmtIn'])} Out: {format_inr(row['AmtOut'])}"
                    trans_map[val] = row['SBId']
                    
                selected_edit_str = st.selectbox("Select Transaction to Modify", list(trans_map.keys()))
                edit_id = trans_map[selected_edit_str]
                row_to_edit = df_trans[df_trans['SBId'] == edit_id].iloc[0]
                
                with st.form("edit_transaction_form"):
                    st.write(f"#### Edit Transaction ID: {edit_id}")
                    col_e1, col_e2 = st.columns(2)
                    with col_e1:
                        curr_date = row_to_edit['DateT'].to_pydatetime() if pd.notna(row_to_edit['DateT']) else datetime.now()
                        t_date = st.date_input("Transaction Date", curr_date)
                        # Bank selection
                        bank_dict = dict(zip(df_banks['BankName'], df_banks['BankId']))
                        default_bank_idx = list(bank_dict.values()).index(row_to_edit['BankId']) if row_to_edit['BankId'] in bank_dict.values() else 0
                        t_bank_name = st.selectbox("Select Bank Account", list(bank_dict.keys()), index=default_bank_idx)
                        t_bank_id = bank_dict[t_bank_name]
                        # Category selection
                        cat_dict = dict(zip(df_cats['CategoryName'], df_cats['CategoryId']))
                        default_cat_idx = list(cat_dict.values()).index(row_to_edit['CategoryId']) if row_to_edit['CategoryId'] in cat_dict.values() else 0
                        t_cat_name = st.selectbox("Select Category", list(cat_dict.keys()), index=default_cat_idx)
                        t_cat_id = cat_dict[t_cat_name]
                    with col_e2:
                        t_name = st.text_input("Payee / Merchant Name (SBName)", value=str(row_to_edit['SBName'] or ''), max_chars=300)
                        t_in = st.number_input("Inflow Amount (AmtIn)", min_value=0.0, value=float(row_to_edit['AmtIn'] or 0.0), step=10.0)
                        t_out = st.number_input("Outflow Amount (AmtOut)", min_value=0.0, value=float(row_to_edit['AmtOut'] or 0.0), step=10.0)
                        t_comment = st.text_input("Comment", value=str(row_to_edit['Comment'] or ''), max_chars=300)
                        
                    submit_btn = st.form_submit_button("Update Transaction ✏️")
                    if submit_btn:
                        success = db.update_transaction(edit_id, t_bank_id, t_name, t_in, t_out, t_cat_id, t_comment, t_date.strftime('%Y-%m-%d'))
                        if success:
                            st.success("Transaction updated successfully!")
                            st.rerun()
                        else:
                            st.error("Error updating transaction in SQLite.")
                            
        elif action_opt == "Delete Transaction":
            if df_trans.empty:
                st.info("No transactions to delete.")
            else:
                trans_map = {}
                for idx, row in df_trans.iterrows():
                    val = f"ID: {row['SBId']} | {row['DateT'].strftime('%Y-%m-%d') if pd.notna(row['DateT']) else ''} | {row['CategoryName']} | {row['SBName']} | In: {format_inr(row['AmtIn'])} Out: {format_inr(row['AmtOut'])}"
                    trans_map[val] = row['SBId']
                    
                selected_del_str = st.selectbox("Select Transaction to Permanent Delete", list(trans_map.keys()))
                del_id = trans_map[selected_del_str]
                
                st.warning(f"⚠️ Are you absolutely sure you want to delete transaction ID {del_id}? This operation cannot be undone.")
                col_d1, col_d2 = st.columns(2)
                with col_d1:
                    if st.button("CONFIRM DELETE 🚨", use_container_width=True):
                        success = db.delete_transaction(del_id)
                        if success:
                            st.success("Transaction deleted successfully.")
                            st.rerun()
                        else:
                            st.error("Failed to delete from SQLite.")
                with col_d2:
                    st.caption("Click confirm to verify transaction erasure.")

    # --- Form: Manage Bank Accounts ---
    with editor_tab_bank:
        action_opt_bank = st.radio("Bank Actions", ["Add Bank Account", "Edit Bank Details"], horizontal=True)
        
        if action_opt_bank == "Add Bank Account":
            with st.form("add_bank_form"):
                st.write("#### Add a New Bank Account Details")
                b_name = st.text_input("Bank Name (e.g. JPMorgan Chase)", max_chars=50)
                b_acc = st.text_input("Account Number", max_chars=50)
                b_ifsc = st.text_input("IFSC / Routing / Swift Code", max_chars=15)
                
                submit_bank = st.form_submit_button("Add Bank Account 🏦")
                if submit_bank:
                    if b_name and b_acc:
                        new_id = db.add_bank(b_name, b_acc, b_ifsc)
                        st.success(f"Added Bank Account successfully (ID: {new_id})")
                        st.rerun()
                    else:
                        st.error("Bank Name and Account Number are required fields.")
                        
        elif action_opt_bank == "Edit Bank Details":
            if df_banks is None or df_banks.empty:
                st.info("No bank accounts registered.")
            else:
                bank_dict = dict(zip(df_banks['BankName'], df_banks['BankId']))
                selected_edit_bank = st.selectbox("Select Bank to Edit", list(bank_dict.keys()))
                edit_b_id = bank_dict[selected_edit_bank]
                row_b = df_banks[df_banks['BankId'] == edit_b_id].iloc[0]
                
                with st.form("edit_bank_form"):
                    st.write(f"#### Edit Bank ID: {edit_b_id}")
                    eb_name = st.text_input("Bank Name", value=row_b['BankName'], max_chars=50)
                    eb_acc = st.text_input("Account Number", value=row_b['AccNo'], max_chars=50)
                    eb_ifsc = st.text_input("IFSC / Routing / Swift Code", value=row_b['IFSC'] or '', max_chars=15)
                    
                    submit_eb = st.form_submit_button("Update Bank Account Details")
                    if submit_eb:
                        if eb_name and eb_acc:
                            success = db.update_bank(edit_b_id, eb_name, eb_acc, eb_ifsc)
                            if success:
                                st.success("Bank details updated successfully!")
                                st.rerun()
                            else:
                                st.error("Failed to update bank in database.")
                        else:
                            st.error("Bank Name and Account Number are required fields.")

    # --- Form: Manage Categories ---
    with editor_tab_cat:
        action_opt_cat = st.radio("Category Actions", ["Add Category", "Edit Category Details"], horizontal=True)
        
        if action_opt_cat == "Add Category":
            with st.form("add_category_form"):
                st.write("#### Add a New Category Details")
                c_name = st.text_input("Category Name (e.g. Dining Out)", max_chars=50)
                c_desc = st.text_input("Category Description", max_chars=150)
                c_budget = st.text_input("Budget Group Name (e.g. Monthly Living, Investments)", max_chars=50)
                
                submit_cat = st.form_submit_button("Add Category 🏷️")
                if submit_cat:
                    if c_name:
                        new_id = db.add_category(c_name, c_desc, c_budget)
                        st.success(f"Added Category successfully (ID: {new_id})")
                        st.rerun()
                    else:
                        st.error("Category Name is required.")
                        
        elif action_opt_cat == "Edit Category Details":
            if df_cats is None or df_cats.empty:
                st.info("No categories registered.")
            else:
                cat_dict = dict(zip(df_cats['CategoryName'], df_cats['CategoryId']))
                selected_edit_cat = st.selectbox("Select Category to Edit", list(cat_dict.keys()))
                edit_c_id = cat_dict[selected_edit_cat]
                row_c = df_cats[df_cats['CategoryId'] == edit_c_id].iloc[0]
                
                with st.form("edit_category_form"):
                    st.write(f"#### Edit Category ID: {edit_c_id}")
                    ec_name = st.text_input("Category Name", value=row_c['CategoryName'], max_chars=50)
                    ec_desc = st.text_input("Category Description", value=row_c['CategoryDesc'] or '', max_chars=150)
                    ec_budget = st.text_input("Budget Group Name", value=row_c['BudgetName'] or '', max_chars=50)
                    
                    submit_ec = st.form_submit_button("Update Category Details")
                    if submit_ec:
                        if ec_name:
                            success = db.update_category(edit_c_id, ec_name, ec_desc, ec_budget)
                            if success:
                                st.success("Category details updated successfully!")
                                st.rerun()
                            else:
                                st.error("Failed to update category in database.")
                        else:
                            st.error("Category Name is required.")

# ==========================================
# 🧠 TAB 6: WEALTH COACH (HEALTH CHECKER)
# ==========================================
with tab_coach:
    st.markdown("## 🧠 Intelligent Financial Health Coach")
    st.caption("Rule-based behavioral heuristics running across your transaction history to flag outliers, recurring expenses, and progress metrics.")
    st.markdown("<hr style='margin-top: 0.25rem; margin-bottom: 1.5rem; border-color: rgba(255,255,255,0.05);'>", unsafe_allow_html=True)
    
    if not df_filtered.empty:
        # Heuristic Analysis
        coach_col1, coach_col2 = st.columns([1, 1])
        
        with coach_col1:
            st.markdown("### 🛡️ Wealth Health Heuristics Status")
            
            # Savings Rate Score
            if savings_rate >= 30.0:
                score_badge = '<span class="health-badge badge-excellent">Excellent (30%+)</span>'
                score_txt = "You are saving more than 30% of your earnings. This accelerates compound interest growth and puts you on track for early financial freedom."
            elif savings_rate >= 15.0:
                score_badge = '<span class="health-badge badge-healthy">Healthy (15-30%)</span>'
                score_txt = "You are in a stable financial zone, matching average recommended savings indices. You can look at optimizing minor utility costs to hit the 30% mark."
            elif savings_rate >= 0.0:
                score_badge = '<span class="health-badge badge-warning">Cautionary (0-15%)</span>'
                score_txt = "Your cash buffer is low. You are living paycheck-to-paycheck. Review your operational spending on dining out and subscriptions to increase your margin."
            else:
                score_badge = '<span class="health-badge badge-critical">Critical (Negative Savings)</span>'
                score_txt = "Your monthly expenditures exceed inflow. You are accumulating debt or depleting resources. Restructure your budget immediately!"
                
            st.markdown(f"**Savings Rate Score**: {score_badge}", unsafe_allow_html=True)
            st.markdown(f"<div style='margin-top: 0.5rem; color: #cbd5e1; font-size: 0.95rem;'>{score_txt}</div>", unsafe_allow_html=True)
            
            # Budget overruns summary
            st.markdown("<br>**Overspent Categories Alerts**:", unsafe_allow_html=True)
            overspent_found = False
            if df_cats is not None and not df_cats.empty:
                df_spent_by_cat = df_filtered[df_filtered['AmtOut'] > 0].groupby('CategoryId')[['AmtOut']].sum().reset_index()
                df_o = pd.merge(df_cats, df_spent_by_cat, on='CategoryId', how='left').fillna(0.0)
                df_o['Limit'] = df_o['CategoryId'].map(st.session_state.budgets).fillna(500.0)
                
                for _, row in df_o.iterrows():
                    if row['AmtOut'] > row['Limit']:
                        overspent_found = True
                        st.markdown(
                            f"⚠️ **{row['CategoryName']}** exceeds monthly threshold: "
                            f"Spent **{format_inr(row['AmtOut'])}** against **{format_inr(row['Limit'])}** limit "
                            f"(Over by <span style='color:#f87171; font-weight:700;'>{format_inr(row['AmtOut'] - row['Limit'])}</span>)", 
                            unsafe_allow_html=True
                        )
            if not overspent_found:
                st.success("All operational spending categories are currently within limits!")
                
        with coach_col2:
            st.markdown("### 🚨 Large Outflow/Expense Auditing")
            # Alert on transactions exceeding 5x the average transaction amount
            df_out_non_zero = df_filtered[df_filtered['AmtOut'] > 0]
            if not df_out_non_zero.empty:
                avg_out = df_out_non_zero['AmtOut'].mean()
                threshold_out = avg_out * 5.0
                
                df_outliers = df_out_non_zero[df_out_non_zero['AmtOut'] > threshold_out].sort_values(by='AmtOut', ascending=False)
                st.write(f"Average outflow size: **{format_inr(avg_out)}**. Flagging transactions exceeding **{format_inr(threshold_out)}** (5x average):")
                
                if not df_outliers.empty:
                    for _, row in df_outliers.iterrows():
                        st.markdown(
                            f"🔴 **{format_inr(row['AmtOut'])}** on **{row['DateT'].strftime('%Y-%m-%d')}** | "
                            f"{row['CategoryName']} - *{row['SBName']}* | "
                            f"Comment: *{row['Comment'] or 'None'}*"
                        )
                else:
                    st.success("No anomalous transaction spikes found. Spending values remain statistically uniform.")
            else:
                st.info("No outflows found to calculate averages.")
                
        # Recurring Transaction Detection Heuristic
        st.markdown("<br><hr style='border-color: rgba(255,255,255,0.05);'><br>", unsafe_allow_html=True)
        st.markdown("### 🔄 Recurring Subscriptions & Fixed Costs Detector")
        st.write("Detecting repeating expenses (matching merchant names, category, and amount patterns happening at least twice):")
        
        if not df_filtered.empty:
            df_rec = df_filtered[df_filtered['AmtOut'] > 0].copy()
            if not df_rec.empty:
                # Group by description and amount
                df_rec_grouped = df_rec.groupby(['SBName', 'CategoryId', 'CategoryName', 'AmtOut']).size().reset_index(name='Occurrences')
                df_rec_matches = df_rec_grouped[df_rec_grouped['Occurrences'] >= 2].sort_values(by='Occurrences', ascending=False)
                
                if not df_rec_matches.empty:
                    rec_cols = st.columns(3)
                    for idx, row in df_rec_matches.iterrows():
                        col_idx = idx % 3
                        with rec_cols[col_idx]:
                            with st.container(border=True):
                                st.markdown(f"**🔄 {row['SBName']}**")
                                st.write(f"Amt: **{format_inr(row['AmtOut'])}** | Occurrences: **{row['Occurrences']}**")
                                st.caption(f"Category: {row['CategoryName']}")
                else:
                    st.info("No clear repeating subscription behavior detected. (Uniform naming matches not found)")
            else:
                st.info("No outflows found.")
    else:
        st.info("No transactions found in filtered timeline.")
