import os
import requests
import pandas as pd
import snowflake.connector
from .queries import create_docs_table_query, create_docs_search_query

class SnowSetup():
    def __init__(self):
        self._conn = snowflake.connector.connect(
            account=os.getenv("SNOWFLAKE_ACCOUNT"),
            user=os.getenv("SNOWFLAKE_USER"),
            password=os.getenv("SNOWFLAKE_PASSWORD")
        )

        self._cursor = self._conn.cursor()


    def dbSetup(self):
        """
        Snowflake Setup. Create all necessary things.
        """

        try:
            # Create DB & Schema if doesn't already exist.
            print("Creating Snowflake DB")
            self._cursor.execute(f"CREATE DATABASE IF NOT EXISTS {os.getenv('SNOWFLAKE_DB')}")
            self._cursor.execute(f"USE DATABASE {os.getenv('SNOWFLAKE_DB')}")
            print("Creating Snowflake Schema")
            self._cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {os.getenv('SNOWFLAKE_SCHEMA')}")
            self._cursor.execute(f"USE SCHEMA {os.getenv('SNOWFLAKE_SCHEMA')}")

            print("Creating Snowflake Table")
            self._cursor.execute(create_docs_table_query)

            self.dbInit()
        except Exception as e:
            print("Failed in Snowflake Setup. Error:", e)


    def dbInit(self):
        """
        This will insert all the relevant values to the DB tables.
        """
        self.insertDocs()

    
    def insertDocs(self):
        print("-" * 50)
        for file in os.listdir(os.getenv('CHUNK_CSV_OUTPUT')):
            try:
                # If data for current data already exists.
                print(f"Inserting data into Snowflake Table for Version: {file[:-4]}")
                self._cursor.execute(f"SELECT version FROM CHUNKS WHERE version='v{file[:-4]}' LIMIT 1")

                if self._cursor.fetchone() is not None:
                    print(f"Version v{file[:-4]} Data Already Present.")
                    continue
                
                values = []
                df = pd.read_csv(os.path.join(os.getenv('CHUNK_CSV_OUTPUT'), file))

                command = f"INSERT INTO {os.getenv('SNOWFLAKE_DOC_TABLE_NAME')} (RELATIVE_PATH, FILE_CONTENT, VERSION, TITLE, DESCRIPTION) VALUES (%s, %s, %s, %s, %s)"
                
                for idx, row in df.iterrows():
                    values.append((str(row['path']), str(row['content']), str(row['version']), str(row['title']), str(row['description'])))

                    if idx > 0 and idx % 500 == 0:
                        print(f"Running Query for idx: {idx - 500}-{idx}")
                        self._cursor.executemany(command, values)
                        values = []
                
                if len(values) > 0:
                    print(f"Running for remaining {len(values)} values.")
                    self._cursor.executemany(command, values)
            except Exception as e:
                print("Failed while Inserting Docs:", e)
            
            print("-" * 50)

        # Get started with cortex search
        print("Creating Snowflake Search Service over Docs. This may take some time.")
        self._cursor.execute(create_docs_search_query)


    def __del__(self):
        self._cursor.close()
        self._conn.close()