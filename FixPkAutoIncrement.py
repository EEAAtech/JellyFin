#!/usr/bin/env python3
import sqlite3
import argparse
import sys
import os

# This script works around the issue that Sqlite forbids alteration to Pk cols. The script auto backsup the specified table, creates a new empty one, copies over the data and then drops the original table. At the cmd prompt use it like this:
# first ensure you chmod +x the script, then run it like this:
# ./FixPkAutoIncrement.py /home/ea/TTMbak/JellyFin/JellyFin.db MF


def convert_pk_to_integer_safe(db_path, table_name):
    # Check if the database file exists before opening
    if not os.path.exists(db_path):
        print(f"Error: Database file '{db_path}' not found.", file=sys.stderr)
        sys.exit(1)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 1. Turn OFF foreign key enforcement for this connection
        cursor.execute("PRAGMA foreign_keys = OFF;")
        
        # Fetch current table structure
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        
        if not columns:
            print(f"Error: Table '{table_name}' does not exist in '{db_path}'.", file=sys.stderr)
            sys.exit(1)

        new_columns_defs = []
        select_columns = []
        pk_column_name = None

        for cid, name, col_type, notnull, dflt_value, pk in columns:
            select_columns.append(name)
            if pk == 1:
                new_columns_defs.append(f'"{name}" INTEGER PRIMARY KEY')
                pk_column_name = name
            else:
                notnull_str = " NOT NULL" if notnull else ""
                dflt_str = f" DEFAULT {dflt_value}" if dflt_value is not None else ""
                new_columns_defs.append(f'"{name}" {col_type}{notnull_str}{dflt_str}')

        if not pk_column_name:
            print(f"Error: No primary key found in table '{table_name}'. Skipping.", file=sys.stderr)
            sys.exit(1)

        columns_sql = ", ".join(new_columns_defs)
        select_sql = ", ".join(select_columns)
        
        # 2. Migration Statements
        create_temp_sql = f"CREATE TABLE {table_name}_new ({columns_sql});"
        copy_data_sql = f"INSERT INTO {table_name}_new ({select_sql}) SELECT {select_sql} FROM {table_name};"
        drop_old_sql = f"DROP TABLE {table_name};"
        rename_new_sql = f"ALTER TABLE {table_name}_new RENAME TO {table_name};"

        # 3. Execute inside a transaction
        cursor.execute("BEGIN TRANSACTION;")
        cursor.execute(create_temp_sql)
        cursor.execute(copy_data_sql)
        cursor.execute(drop_old_sql)
        cursor.execute(rename_new_sql)
        
        # 4. Safety Check: Verify foreign key integrity before committing
        cursor.execute("PRAGMA foreign_key_check;")
        violations = cursor.fetchall()
        
        if violations:
            print("Error: Foreign key integrity check failed! Rolling back changes.", file=sys.stderr)
            for v in violations:
                print(f"Violation: Table '{v[0]}' rowid {v[1]} references missing/invalid key in '{v[2]}'", file=sys.stderr)
            conn.rollback()
            sys.exit(1)

        conn.commit()
        print(f"Success: Migrated table '{table_name}'. Primary key '{pk_column_name}' is now INTEGER PRIMARY KEY.")

    except sqlite3.Error as e:
        conn.rollback()
        print(f"Migration failed due to SQL error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        # 5. Always restore foreign key settings
        cursor.execute("PRAGMA foreign_keys = ON;")
        conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Safely migrate an SQLite column type to INTEGER PRIMARY KEY NOT NULL.")
    parser.add_argument("db_path", help="Path to the SQLite database file (e.g., app.db)")
    parser.add_argument("table_name", help="Name of the table to modify")
    
    args = parser.parse_args()
    convert_pk_to_integer_safe(args.db_path, args.table_name)
