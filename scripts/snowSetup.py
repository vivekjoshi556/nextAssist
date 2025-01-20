import os
import requests
import pandas as pd
import snowflake.connector
from queries import (
    create_docs_table_query, create_docs_search_query, 
    create_dis_issue_table_query, create_dis_issue_search_query
)

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
            self._cursor.execute(create_dis_issue_table_query)

            self.dbInit()
        except Exception as e:
            print("Failed in Snowflake Setup. Error:", e)


    def dbInit(self):
        """
        This will insert all the relevant values to the DB tables.
        """
        self.insertDocs()
        self.insertPosts()

    
    def insertDocs(self):
        print("-" * 50)
        for file in os.listdir(os.getenv('CHUNK_CSV_OUTPUT')):
            if not file.endswith('.csv'):
                continue

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
    

    def insertPosts(self):
        self.processGithubPost("Issue")
        self.processGithubPost("Discussion")
        
        print("Creating Snowflake Search Service over Posts. This may take some time.")
        self._cursor.execute(create_dis_issue_search_query)

    
    def processGithubPost(self, type):
        if type not in ["Issue", "Discussion"]:
            raise ValueError("Invalid content type. Must be 'Issue' or 'Discussion'")
        
        print(f"Will try to insert {type}s")

        url = "https://api.github.com/graphql"

        query = f"""
            query($query: String!, $cursor: String) {{
                search(query: $query, type: { type.upper() }, first: 10, after: $cursor) {{
                    discussionCount
                    pageInfo {{
                        hasNextPage
                        endCursor
                    }}
                    nodes {{
                        ... on { type } {{
                            title
                            url
                            body
                            updatedAt
                        }}
                    }}
                }}
            }}
        """
        
        headers = {
            "Authorization": f"Bearer {os.getenv('GITHUB_TOKEN')}",
            "Content-Type": "application/json"
        }

        posts = []
        cursor = None
        has_next_page = True

        updated_after = self._cursor.execute(
            f"SELECT TO_CHAR(COALESCE(MAX(UPDATED_AT), '2024-01-01'::TIMESTAMP_NTZ), 'YYYY-MM-DD') FROM POSTS WHERE TYPE='{type}' LIMIT 1"
        ).fetchone()[0]

        condition = "state:closed interactions:>1" if type == "Issue" else "is:answered"
        print(f"Inserting {type}s updated_after: {updated_after} with condition: {condition}")

        try:
            while has_next_page:
                search_query = f"repo:{os.getenv('REPO_NAME')} updated:>={updated_after} {condition}"
                variables = {
                    "query": search_query,
                    "cursor": cursor
                }
                response = requests.post(
                    url, 
                    json = {
                        "query": query,
                        "variables": variables
                    }, 
                    headers=headers
                )
                if response.status_code != 200:
                    raise Exception(f"Query failed: {response.status_code}, {response.text}")

                data = response.json()
                search_data = data["data"]["search"]
                posts.extend(search_data["nodes"])

                # Pagination handling
                has_next_page = search_data["pageInfo"]["hasNextPage"]
                cursor = search_data["pageInfo"]["endCursor"]
        except Exception as e:
            print(f"Failed when trying to read Repo {type}: {e}")

        print(f"Found {len(posts)} {type}s to insert.")
        values = []
        command = f"INSERT INTO {os.getenv('SNOWFLAKE_POSTS_TABLE_NAME')} (TITLE, URL, CONTENT, TYPE, UPDATED_AT) VALUES (%s, %s, %s, %s, %s)"

        insertion_group_size = 100
        try:
            for idx, row in enumerate(posts):
                if len(row.keys()) == 0:
                    continue

                values.append((str(row['title']), str(row['url']), str(row['body']), type, str(row['updatedAt'])))

                if idx > 0 and idx % insertion_group_size == 0:
                    print(f"Running Query for idx: {idx - insertion_group_size}-{idx}")
                    self._cursor.executemany(command, values)
                    values = []

            if len(values) > 0:
                print(f"Running for remaining {len(values)} values.")
                self._cursor.executemany(command, values)
        
        except Exception as e:
            print(f"Failed when trying to insert {type}s into table: {e}")


    def __del__(self):
        self._cursor.close()
        self._conn.close()