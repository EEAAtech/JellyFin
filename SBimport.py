import streamlit as st
import pandas as pd
from io import BytesIO
import sqlite3
from datetime import datetime

DB_PATH = "/home/ea/JellyFin.db"
st.set_page_config(layout="wide")

# Initialize session state variables
if "import_completed" not in st.session_state:
    st.session_state.import_completed = False
if "imported_data" not in st.session_state:
    st.session_state.imported_data = None
if "selected_bank_id" not in st.session_state:
    st.session_state.selected_bank_id = None
if "last_import_date" not in st.session_state:
    st.session_state.last_import_date = None

# Function to covert Sqlite date string from '%d/%m/%y' to '%Y-%m-%d' 
def convert_date_format(date_str):
    try:
        # Try parsing as '%d/%m/%y'
        dt = datetime.strptime(date_str, '%d/%m/%y')
        return dt.strftime('%Y-%m-%d')
    except ValueError:
        # If parsing fails, return the original string
        return date_str

# Connect to SQLite database
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Read Bank table and create a select box for the user to choose bank
query_bank = "SELECT BankId, BankName FROM Bank"
bank_df = pd.read_sql_query(query_bank, conn)
bank_dict = dict(zip(bank_df['BankName'], bank_df['BankId']))

selected_bank = st.selectbox('Select bank', list(bank_dict.keys()))

# Allow user to upload xls file
uploaded_file = st.file_uploader("Choose an Excel (.xls) file", type=['xls'])

# Only process file upload if import hasn't been completed yet
if uploaded_file is not None and not st.session_state.import_completed:
    # Read the xls file without assuming row 0 is the header
    xls_data = pd.read_excel(uploaded_file, header=None)
    
    # Set a flag in session state to indicate that the file has been imported
    # st.session_state["process_clicked"] = True
    # if "process_clicked" not in st.session_state:
    #     st.stop()

    # Step 3: Find the row with "Date" in column A (first column)
    date_row_index = None
    for i in range(len(xls_data)):
        if xls_data.iloc[i, 0] == 'Date':  # Check first column
            date_row_index = i
            break
    
    if date_row_index is not None:
        # Step 4: Check if the next row has "*" characters in the Date column
        if date_row_index + 1 < len(xls_data):
            next_row_value = xls_data.iloc[date_row_index + 1, 0]
            if isinstance(next_row_value, str) and all(c == '*' for c in next_row_value if c is not None):
                # Step 5: Start of data is the row after the "*" row
                start_row = date_row_index + 2
                
                # Set the column headers from the date_row_index row
                xls_data.columns = xls_data.iloc[date_row_index]
                
                # Keep only the data rows and reset index
                xls_data = xls_data.iloc[start_row:].reset_index(drop=True)
                
                # Get the selected BankId
                selected_bank_id = bank_dict[selected_bank]
                
                # Step 7a: Find the last date in SB that data was imported for the selected BankId
                query_last_import_date = "SELECT MAX(DateT) FROM SB WHERE BankId = ?"
                cursor.execute(query_last_import_date, (selected_bank_id,))
                last_import_date = cursor.fetchone()[0]
                
                # Step 7b/7c: Import data into the SB table
                imported_count = 0
                for i in range(len(xls_data)):
                    # Stop at blank row
                    if pd.isnull(xls_data.iloc[i, 0]):
                        break
                    
                    # Stop at another "*" row
                    cell_value = xls_data.iloc[i, 0]
                    if isinstance(cell_value, str) and all(c == '*' for c in cell_value if c is not None):
                        break
                    
                    # Only import if date is after last_import_date
                    row_date = xls_data.iloc[i].iloc[0]  # First column is the Date column
                    if not pd.isnull(row_date):
                        # Convert row_date to date string for comparison
                        row_date_str = convert_date_format(row_date)
                        
                        # Only import if this date is after the last import date
                        if last_import_date is None or row_date_str > last_import_date:
                            # Get values by column position since they're accessed by name in the header row
                            narration = xls_data.iloc[i].iloc[1] if len(xls_data.columns) > 2 else None
                            withdrawal_amt = xls_data.iloc[i].iloc[4] if len(xls_data.columns) > 4 else None
                            deposit_amt = xls_data.iloc[i].iloc[5] if len(xls_data.columns) > 3 else None
                            
                            query_insert_sb = """INSERT INTO SB (BankId, DateT, SBName, AmtIn, AmtOut) 
                                                 VALUES (?, ?, ?, ?, ?)"""
                            cursor.execute(query_insert_sb, (
                                selected_bank_id,
                                row_date_str,
                                str(narration) if not pd.isnull(narration) else None,
                                deposit_amt if not pd.isnull(deposit_amt) else None,
                                withdrawal_amt if not pd.isnull(withdrawal_amt) else None
                            ))
                            imported_count += 1
                
                conn.commit()
                st.success(f"Successfully imported {imported_count} records")
                
                # Store in session state for display
                st.session_state.imported_data = imported_count
                st.session_state.selected_bank_id = selected_bank_id
                st.session_state.last_import_date = last_import_date
                st.session_state.import_completed = True
                
                # Auto-categorize newly imported records based on SBName patterns
                if imported_count > 0:
                    update_queries = [
                        ("UPDATE SB SET CategoryId=1 WHERE DateT>? AND CategoryId IS NULL AND AmtIn>0 AND (SBName LIKE '%CREDIT INTEREST CAPITALISED%' OR SBName LIKE '%interest paid%' OR SBName LIKE '%Int.Pd%')", "bank interest"),
                        ("UPDATE SB SET CategoryId=2 WHERE DateT>? AND CategoryId IS NULL AND AmtOut>0 AND (SBName LIKE '%cc 00055%' OR SBName LIKE '%cc0xx%')", "cc"),
                        ("UPDATE SB SET CategoryId=3 WHERE DateT>? AND CategoryId IS NULL AND AmtIn>0 AND SBName LIKE '%idcw%'", "idcw"),
                        ("UPDATE SB SET CategoryId=5 WHERE DateT>? AND CategoryId IS NULL AND AmtOut>0 AND SBName LIKE '%TTM%'", "TTM"),
                        ("UPDATE SB SET CategoryId=9 WHERE DateT>? AND CategoryId IS NULL AND AmtOut>0 AND (SBName LIKE '%pay to ramya%' OR SBName LIKE '%lunch%' OR SBName LIKE '%dinner%' OR SBName LIKE '%swiggy%' OR SBName LIKE '%zomat%' OR SBName LIKE '%bfast%' OR SBName LIKE '%breakfasat%' OR SBName LIKE '%snacks%' OR SBName LIKE '%cred%' OR SBName LIKE '%-Tea')", "meals"),
                        ("UPDATE SB SET CategoryId=10 WHERE DateT>? AND CategoryId IS NULL AND AmtOut>0 AND SBName LIKE '%Holiday%'", "Holiday"),
                        ("UPDATE SB SET CategoryId=13 WHERE DateT>? AND CategoryId IS NULL AND AmtOut>0 AND SBName LIKE '%BY%_NET_RENEWAL'", "Insurance"),
                        ("UPDATE SB SET CategoryId=15 WHERE DateT>? AND CategoryId IS NULL AND AmtOut>0 AND (SBName LIKE '%shopping%' OR SBName LIKE '%home%' OR SBName LIKE '%electricity%' OR SBName LIKE '%locker%' OR SBName LIKE '%UPI-CCP%')", "Home/Shopping"),
                        ("UPDATE SB SET CategoryId=17 WHERE DateT>? AND CategoryId IS NULL AND AmtOut>0 AND (SBName LIKE '%Med%' OR SBName LIKE '%doc%')", "Medical"),
                        ("UPDATE SB SET CategoryId=20 WHERE DateT>? AND CategoryId IS NULL AND AmtOut>0 AND SBName LIKE '%Family%'", "Family"),
                        ("UPDATE SB SET CategoryId=21 WHERE DateT>? AND CategoryId IS NULL AND AmtIn>0 AND SBName LIKE '%inttrans%'", "Inttrans in"),
                        ("UPDATE SB SET CategoryId=22 WHERE DateT>? AND CategoryId IS NULL AND AmtOut>0 AND SBName LIKE '%inttrans%'", "Inttrans out"),
                        ("UPDATE SB SET CategoryId=23 WHERE DateT>? AND CategoryId IS NULL AND AmtOut>0 AND SBName LIKE 'ACH D-%'", "MF invest"),
                        ("UPDATE SB SET CategoryId=24 WHERE DateT>? AND CategoryId IS NULL AND AmtOut>0 AND (SBName LIKE '%haircut%' OR SBName LIKE '%water%' OR SBName LIKE '%amazon%')", "self"),
                        ("UPDATE SB SET CategoryId=26 WHERE DateT>? AND CategoryId IS NULL AND AmtIn>0 AND SBName LIKE '%elait%'", "Salary"),
                        ("UPDATE SB SET CategoryId=29 WHERE DateT>? AND CategoryId IS NULL AND AmtOut>0 AND (SBName LIKE '%PUC%' OR SBName LIKE '%parking%' OR SBName LIKE '%carfix%' OR SBName LIKE '%tyres%' OR SBName LIKE '%MANOJSUTAR%' OR SBName LIKE '%taxi%')", "Car Maintenance"),
                        ("UPDATE SB SET CategoryId=30 WHERE DateT>? AND CategoryId IS NULL AND AmtOut>0 AND SBName LIKE '%petrol%'", "petrol"),
                        ("UPDATE SB SET CategoryId=1009 WHERE DateT>? AND CategoryId IS NULL AND AmtIn>0 AND SBName LIKE '%PRUDENTIAL MUTUAL FUND RED A/C%'", "SWP"),
                    ]
                    
                    for query, category_name in update_queries:
                        cursor.execute(query, (last_import_date,))
                    
                    conn.commit()
                
                # Step 8: Display a table listing the records from vwSBRunningTotal
                query_running_total = """SELECT SBId, DateT, SBName, AmtIn, AmtOut, BankId, RunningTotal FROM vwSBRunningTotal 
                                         WHERE BankId = ? AND DateT > ?"""
                running_total_data = pd.read_sql_query(query_running_total, conn, 
                                                       params=(selected_bank_id, last_import_date))
                st.dataframe(running_total_data)
            else:
                st.error("The row after 'Date' does not contain all '*' characters. Cannot find data start.")
        else:
            st.error("No row after 'Date' header found in the Excel file.")
    else:
        st.error("Could not find 'Date' header in column A of the Excel file.")

# If import is already completed, display the editable section without re-running imports
if st.session_state.import_completed:
    st.divider()
    st.subheader("Edit Comments and Categories for Newly Imported Records")
    
    # Fetch category data
    query_categories = "SELECT CategoryId, CategoryName FROM Category ORDER BY CategoryName"
    categories_df = pd.read_sql_query(query_categories, conn)
    category_dict = dict(zip(categories_df['CategoryName'], categories_df['CategoryId']))
    category_names = [''] + list(category_dict.keys())  # Add empty option at the beginning
    
    # Fetch newly imported records with their SBId for updating
    query_new_records = """SELECT SBId, DateT, SBName, AmtIn, AmtOut, Comment, CategoryId FROM SB 
                           WHERE BankId = ? AND DateT > ?
                           ORDER BY DateT DESC"""
    new_records = pd.read_sql_query(query_new_records, conn, 
                                   params=(st.session_state.selected_bank_id, st.session_state.last_import_date))
    
    if len(new_records) > 0:
        # Create table header
        col1, col2, col3, col4, col5, col6, col7 = st.columns([1, 3, 1, 1, 2, 2, 1])
        with col1:
            st.write("**Date**")
        with col2:
            st.write("**Description**")
        with col3:
            st.write("**In**")
        with col4:
            st.write("**Out**")
        with col5:
            st.write("**Comment**")
        with col6:
            st.write("**Category**")
        with col7:
            st.write("")
        
        # Create editable rows
        edited_data = []
        for idx, row in new_records.iterrows():
            col1, col2, col3, col4, col5, col6, col7 = st.columns([1, 3, 1, 1, 2, 2, 1])
            
            with col1:
                st.write(row['DateT'])
            with col2:
                st.write(row['SBName'])
            with col3:
                st.write(f"{row['AmtIn']}" if row['AmtIn'] else "")
            with col4:
                st.write(f"{row['AmtOut']}" if row['AmtOut'] else "")
            with col5:
                comment = st.text_input(f"Comment {idx}", value=row['Comment'] if row['Comment'] else "", key=f"comment_{row['SBId']}")
            with col6:
                # Get current category name if available
                current_category = ""
                if row['CategoryId']:
                    current_category = categories_df[categories_df['CategoryId'] == row['CategoryId']]['CategoryName'].values
                    current_category = current_category[0] if len(current_category) > 0 else ""
                
                category = st.selectbox(f"Category {idx}", category_names, 
                                       index=category_names.index(current_category) if current_category in category_names else 0,
                                       key=f"category_{row['SBId']}")
            with col7:
                st.write("")
            
            edited_data.append({
                'SBId': row['SBId'],
                'Comment': comment,
                'CategoryId': category_dict[category] if category else None
            })
        
        # Save button
        if st.button("Save"):
            try:
                for item in edited_data:
                    update_query = "UPDATE SB SET Comment = ?, CategoryId = ? WHERE SBId = ?"
                    cursor.execute(update_query, (item['Comment'], item['CategoryId'], item['SBId']))
                conn.commit()
                st.success("Comments and categories saved successfully!")
            except Exception as e:
                st.error(f"Error saving comments and categories: {str(e)}")
    else:
        st.info("No newly imported records to edit.")

conn.close()

