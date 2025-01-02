from dotenv import load_dotenv
load_dotenv(".env")

from snowSetup import dbSetup
from getDocs import downloadRepo
from processDocs import processAndChunk
from nextUtil import processFile, chunkMarkdown
from extractDocs import extract, filePostProcessing

# Download all the Repositories.
downloadRepo()

# filePostProcessing here can be replaced with any custom post processing function.
# This involves post-processing on the directory structure or other file-related aspects, but not the content itself.
extract(filePostProcessing)

# This will process & chunk the files extracted and save them to be directly imported into snowflake.
processAndChunk(processFile, chunkMarkdown)

# Snowflake Setup
dbSetup()

print("Setup Complete.")