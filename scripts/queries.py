import os

# Queries for table containing Docs.
create_docs_table_query = f"""CREATE TABLE IF NOT EXISTS {os.getenv('SNOWFLAKE_DOC_TABLE_NAME')} (
    RELATIVE_PATH STRING,
    FILE_CONTENT STRING,
    VERSION VARCHAR(15),
    TITLE VARCHAR(100),
    DESCRIPTION VARCHAR(500),
    PROCESSED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

create_docs_search_query = f"""CREATE CORTEX SEARCH SERVICE IF NOT EXISTS {os.getenv('CORTEX_DOC_SEARCH_SERVICE')}
ON FILE_CONTENT
ATTRIBUTES RELATIVE_PATH, VERSION, TITLE, DESCRIPTION 
TARGET_LAG = '60 seconds'
EMBEDDING_MODEL = '{os.getenv('CORTEX_EMBEDDING_MODEL')}'
WAREHOUSE = COMPUTE_WH
AS (
	SELECT
		RELATIVE_PATH,FILE_CONTENT,VERSION,TITLE,DESCRIPTION
	FROM "{os.getenv('SNOWFLAKE_DB')}".{os.getenv('SNOWFLAKE_SCHEMA')}.{os.getenv('SNOWFLAKE_DOC_TABLE_NAME')}
)
"""

# Queries for table containing Discussion & Issues Data.
create_dis_issue_table_query = f"""CREATE TABLE IF NOT EXISTS {os.getenv('SNOWFLAKE_POSTS_TABLE_NAME')} (
    TITLE VARCHAR(256),
    URL VARCHAR(2048),
    CONTENT STRING,
    TYPE VARCHAR(20),
    UPDATED_AT TIMESTAMP
);
"""

create_dis_issue_search_query = f"""CREATE CORTEX SEARCH SERVICE IF NOT EXISTS {os.getenv('CORTEX_POSTS_SEARCH_SERVICE')}
ON CONTENT
ATTRIBUTES TITLE, URL, TYPE 
TARGET_LAG = '5 minute'
EMBEDDING_MODEL = '{os.getenv('CORTEX_EMBEDDING_MODEL')}'
WAREHOUSE = COMPUTE_WH
AS (
	SELECT
		CONTENT, TITLE, URL, TYPE
	FROM "{os.getenv('SNOWFLAKE_DB')}".{os.getenv('SNOWFLAKE_SCHEMA')}.{os.getenv('SNOWFLAKE_POSTS_TABLE_NAME')}
)
"""