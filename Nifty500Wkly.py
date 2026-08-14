import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

@st.cache_data
def load_nifty_data(csv_file):
    df = pd.read_csv(csv_file)
    df.columns = df.columns.str.strip()
    
    df['Date'] = pd.to_datetime(df['Date'], format='%d-%b-%Y')
    df.set_index('Date', inplace=True)
    df.sort_index(inplace=True)
    
    return df[['Close']]

def main():
    st.title("NSE Nifty 50 Weekly Average Closing Prices (Past 3 Years)")
    
    uploaded_file = st.file_uploader("Upload your Nifty 50 CSV file", type="csv")
    
    if uploaded_file is not None:
        df = load_nifty_data(uploaded_file)
        
        if df.empty:
            st.error("No data loaded.")
            st.stop()
        
        today = datetime.now()
        three_years_ago = today - timedelta(days=3*365)
        df_past_3y = df[df.index >= three_years_ago]
        
        st.success(f"✅ Loaded {len(df_past_3y)} trading days")
        
        # FIXED: Simple and robust weekday mapping
        df_past_3y['weekday'] = df_past_3y.index.weekday
        weekly_avg = df_past_3y.groupby('weekday')['Close'].mean().round(2)
        
        # Create new Series with day names - NO INDEX ASSIGNMENT
        day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
        weekly_avg_named = pd.Series(
            weekly_avg.values[:5], 
            index=day_names[:len(weekly_avg)]
        )
        
        st.subheader("Average Closing Price by Day of Week")
        st.bar_chart(weekly_avg_named)
        
        col1, col2 = st.columns(2)
        with col1:
            max_day = weekly_avg_named.idxmax()
            st.metric("Highest Average", f"₹{weekly_avg_named.max():,.0f}", max_day)
        with col2:
            min_day = weekly_avg_named.idxmin()
            st.metric("Lowest Average", f"₹{weekly_avg_named.min():,.0f}", min_day)
        
        st.dataframe(weekly_avg_named, use_container_width=True)
        
        with st.expander("📊 Data preview"):
            st.dataframe(df_past_3y.reset_index()[['Date', 'Close']].head(20))

if __name__ == "__main__":
    main()
