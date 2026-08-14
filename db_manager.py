import os
import glob
import sqlite3
import pandas as pd

def get_db_path():
    """
    Returns path to SQLite database file.
    Checks the local workspace directory for 'Jel.db' first, then defaults to the user's Downloads directory.
    """
    dir_path = os.path.dirname(os.path.abspath(__file__))
    local_path = os.path.join(dir_path, "Jel.db")
    """ if os.path.exists(local_path):
        return local_path """
    return "/home/ea/TTMbak/JellyFin/JellyFin.db"

def initialize_empty_db(db_path):
    """
    Creates empty Bank, Category, and SB tables if they do not exist.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        # Create Bank table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS "Bank" (
            "BankId" INTEGER PRIMARY KEY AUTOINCREMENT,
            "BankName" varchar(50) NOT NULL,
            "AccNo" varchar(50) NOT NULL,
            "IFSC" varchar(15)
        )
        """)
        # Create Category table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS "Category" (
            "CategoryId" INTEGER PRIMARY KEY AUTOINCREMENT,
            "CategoryName" varchar(50) NOT NULL,
            "CategoryDesc" varchar(150),
            "BudgetName" varchar(50)
        )
        """)
        # Create SB table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS SB (
            SBId INTEGER PRIMARY KEY AUTOINCREMENT,
            BankId int NOT NULL,
            SBName varchar(300) NULL,
            AmtIn decimal(10, 2) NULL,
            AmtOut decimal(10, 2) NULL,
            CategoryId int NULL,
            Comment varchar(300) NULL,
            DateT TEXT,
            CONSTRAINT FK_SB_ToBank FOREIGN KEY (BankId) REFERENCES Bank (BankId),
            CONSTRAINT FK_SB_ToCategory FOREIGN KEY (CategoryId) REFERENCES Category (CategoryId)
        )
        """)
        conn.commit()
    finally:
        conn.close()

def get_connection():
    db_path = get_db_path()
    # Check if the database needs initialization
    if not os.path.exists(db_path):
        initialize_empty_db(db_path)
    else:
        # Also check if tables exist inside the existing file
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='SB';")
            if not cursor.fetchone():
                conn.close()
                initialize_empty_db(db_path)
            else:
                conn.close()
        except:
            pass
            
    conn = sqlite3.connect(db_path)
    # Enable foreign keys
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def check_db_setup():
    """
    Checks if the required tables (SB, Category, Bank) exist in the database.
    Returns a dict containing information about the database status.
    """
    db_path = get_db_path()
    status = {
        "exists": os.path.exists(db_path),
        "path": db_path,
        "tables": [],
        "errors": []
    }
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        status["tables"] = tables
        conn.close()
        
        required_tables = ["SB", "Category", "Bank"]
        missing = [t for t in required_tables if t not in tables]
        if missing:
            status["errors"].append(f"Missing tables in database: {', '.join(missing)}")
    except Exception as e:
        status["errors"].append(str(e))
        
    return status

def get_all_transactions():
    """
    Fetch all transactions joined with Category and Bank details.
    """
    query = """
        SELECT 
            s.SBId,
            s.BankId,
            b.BankName,
            b.AccNo,
            s.SBName,
            s.AmtIn,
            s.AmtOut,
            s.CategoryId,
            c.CategoryName,
            c.CategoryDesc,
            c.BudgetName,
            s.Comment,
            s.DateT
        FROM SB s
        LEFT JOIN Bank b ON s.BankId = b.BankId
        LEFT JOIN Category c ON s.CategoryId = c.CategoryId
        ORDER BY s.DateT DESC, s.SBId DESC
    """
    conn = get_connection()
    try:
        df = pd.read_sql_query(query, conn)
        # Parse dates and handle numeric formatting
        if not df.empty and 'DateT' in df.columns:
            df['DateT'] = pd.to_datetime(df['DateT'], errors='coerce')
        return df
    finally:
        conn.close()

def get_categories():
    query = "SELECT CategoryId, CategoryName, CategoryDesc, BudgetName FROM Category ORDER BY CategoryName ASC"
    conn = get_connection()
    try:
        return pd.read_sql_query(query, conn)
    finally:
        conn.close()

def get_banks():
    query = "SELECT BankId, BankName, AccNo, IFSC FROM Bank ORDER BY BankName ASC"
    conn = get_connection()
    try:
        return pd.read_sql_query(query, conn)
    finally:
        conn.close()

# C.U.D. Operations for Transactions (SB)
def add_transaction(bank_id, sb_name, amt_in, amt_out, category_id, comment, date_t):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO SB (BankId, SBName, AmtIn, AmtOut, CategoryId, Comment, DateT)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (bank_id, sb_name, amt_in, amt_out, category_id, comment, date_t)
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()

def update_transaction(sb_id, bank_id, sb_name, amt_in, amt_out, category_id, comment, date_t):
    conn = get_connection()
    try:
        conn.execute(
            """
            UPDATE SB 
            SET BankId = ?, SBName = ?, AmtIn = ?, AmtOut = ?, CategoryId = ?, Comment = ?, DateT = ?
            WHERE SBId = ?
            """,
            (bank_id, sb_name, amt_in, amt_out, category_id, comment, date_t, sb_id)
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"Error updating transaction: {e}")
        return False
    finally:
        conn.close()

def delete_transaction(sb_id):
    conn = get_connection()
    try:
        conn.execute("DELETE FROM SB WHERE SBId = ?", (sb_id,))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error deleting transaction: {e}")
        return False
    finally:
        conn.close()

# C.U.D. Operations for Category
def add_category(category_name, category_desc, budget_name):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO Category (CategoryName, CategoryDesc, BudgetName)
            VALUES (?, ?, ?)
            """,
            (category_name, category_desc, budget_name)
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()

def update_category(category_id, category_name, category_desc, budget_name):
    conn = get_connection()
    try:
        conn.execute(
            """
            UPDATE Category
            SET CategoryName = ?, CategoryDesc = ?, BudgetName = ?
            WHERE CategoryId = ?
            """,
            (category_name, category_desc, budget_name, category_id)
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"Error updating category: {e}")
        return False
    finally:
        conn.close()

# C.U.D. Operations for Bank
def add_bank(bank_name, acc_no, ifsc):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO Bank (BankName, AccNo, IFSC)
            VALUES (?, ?, ?)
            """,
            (bank_name, acc_no, ifsc)
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()

def update_bank(bank_id, bank_name, acc_no, ifsc):
    conn = get_connection()
    try:
        conn.execute(
            """
            UPDATE Bank
            SET BankName = ?, AccNo = ?, IFSC = ?
            WHERE BankId = ?
            """,
            (bank_name, acc_no, ifsc, bank_id)
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"Error updating bank: {e}")
        return False
    finally:
        conn.close()

def get_closing_balance(bank_id, end_date):
    """
    Retrieve the closing balance for a specific bank account as of the given end_date.
    The view `vwSBRunningTotal` is expected to have columns: BankId, DateT, RunningTotal.
    This function returns the RunningTotal of the latest record on or before end_date.
    If no record is found, returns 0.0.
    """
    conn = get_connection()
    try:
        query = """
            SELECT RunningTotal
            FROM vwSBRunningTotal
            WHERE BankId = ? AND DateT <= ?
            ORDER BY DateT DESC
            LIMIT 1
        """
        cur = conn.execute(query, (bank_id, end_date))
        row = cur.fetchone()
        if row:
            return float(row[0])
        else:
            return 0.0
    except Exception as e:
        print(f"Error fetching closing balance: {e}")
        return 0.0
    finally:
        conn.close()
