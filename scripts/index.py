from dotenv import load_dotenv
load_dotenv(".env")

from extractDocs import extract
from getDocs import downloadRepo
from snowSetup import SnowSetup
from processDocs import processAndChunk
from nextUtil import processFile, chunkMarkdown

db = SnowSetup()

# Data Prep from Docs
downloadRepo()
extract()
processAndChunk(processFile, chunkMarkdown)

# Data Prep from Discussion & Issues
db.dbSetup()

print("Setup Complete.")