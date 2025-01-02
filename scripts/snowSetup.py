import os
import pandas as pd
import snowflake.connector
from queries import create_table_query, create_search_query

def dbSetup():
    conn = snowflake.connector.connect(
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        user=os.getenv("SNOWFLAKE_USER"),
        password=os.getenv("SNOWFLAKE_PASSWORD")
    )

    cursor = conn.cursor()

    try:
        # Create DB & Schema if doesn't already exist.
        print("Creating Snowflake DB")
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {os.getenv('SNOWFLAKE_DB')}")
        print("Creating Snowflake Schema")
        cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {os.getenv('SNOWFLAKE_SCHEMA')}")

        print("Creating Snowflake Table")
        cursor.execute(create_table_query)

        print("-" * 50)
        for file in os.listdir(os.getenv('CHUNK_CSV_OUTPUT')):
            print(f"Inserting data into Snowflake Table for Version: {file[:-4]}")
            cursor.execute(f"SELECT version FROM CHUNKS WHERE version='v{file[:-4]}' LIMIT 1")

            if cursor.fetchone() is not None:
                print(f"Version v{file[:-4]} Data Already Present.")
                continue
            
            values = []
            df = pd.read_csv(os.path.join(os.getenv('CHUNK_CSV_OUTPUT'), file))

            command = f"INSERT INTO {os.getenv('SNOWFLAKE_TABLE_NAME')} (RELATIVE_PATH, FILE_CONTENT, VERSION, TITLE, DESCRIPTION) VALUES (%s, %s, %s, %s, %s)"
            
            for idx, row in df.iterrows():
                values.append((str(row['path']), str(row['content']), str(row['version']), str(row['title']), str(row['description'])))

                if idx > 0 and idx % 500 == 0:
                    print(f"Running Query for idx: {idx - 500}-{idx}")
                    cursor.executemany(command, values)
                    values = []
            
            if len(values) > 0:
                print(f"Running for remaining {len(values)} values.")
                cursor.executemany(command, values)
            
            print("-" * 50)

        # Get started with cortex search
        print("Creating Snowflake Search Service. This may take some time.")
        cursor.execute(create_search_query)
    except Exception as e:
        print("Failed in Snowflake Setup. Error:", e)
    
    cursor.close()
    conn.close()