from dotenv import load_dotenv
load_dotenv(".env")

from snowSetup import dbSetup
from extractDocs import extract
from getDocs import downloadRepo
from processDocs import processAndChunk
from nextUtil import processFile, chunkMarkdown

# Download all the Repositories.
downloadRepo()

# This extracts the zip files to the folder mentioned in .env file.
extract()

# This will process & chunk the files extracted and save them to be directly imported into snowflake.
processAndChunk(processFile, chunkMarkdown)

# Snowflake Setup
dbSetup()

print("Setup Complete.")