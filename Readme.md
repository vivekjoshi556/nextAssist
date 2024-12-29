# NextAssist
This project builds a RAG pipeline on last 6 (major & minor releases) versions of [NextJS](https://nextjs.org/). This will allow for better next.js related query resolution.

I have ignored the canary and minor releases and focus only on major & minor releases only.

## Tech Stack
Cortex Search, Mistral LLM, & Streamlit Community Cloud


## Overview
Let's look into the building 
### Data Preparation (Cleaning & Chunking):
- In the documentation next avoids repeating the content for both it's routers (app & pages) so they write all the content in one of the place using tags like (`<AppOnlyl>` & `<PagesOnly>`) and then mentions the source in the other file. I wrote a simple script to get complete files for both router so it would be easier to chunk both the files.

- The chunking strategy plays an important role in the final result. According to the Cortex Search Documentation:
    > For optimal search results with Cortex Search, Snowflake recommends splitting the text in your search column into chunks of no more than 512 tokens (about 385 English words). When an entry in the search column contains more than 512 tokens, Cortex Search performs keyword-based retrieval on the entire body of text, but only uses the first 512 tokens for semantic (i.e., vector-based) retrieval.

    So keeping this in mind we have to think about chunking strategy. I wrote a bit custom code for that the idea is this:
    
    - I took the first heading present and entire content inside it as the first chunk entirely and then kept recursively splitting it based on headings until the chunk size became smaller than expected (385 words). 
    - Also, I made sure that the code blocks don't get split between two chunks. This is sometimes leading to a chunk size bigger than expected. I am just keeping it for now.

### Building the Search


## Setting Up Locally:
- The `scripts` folder contains all the required scripts. You just have to follow these steps: 
    - Create a `.env` file with appropriate values (a sample .env.example file is already given, you can directly rename that file to .env as well)
    - Then just run `index.py` and you will have a list of csv files inside the folder that you mentioned in your env file. Here each csv file contains chunks and other related information. These files can be directly uploaded to snowflake database.

        ```python 
        python scripts/index.py  
        ```

## Using for Other Repo:
I have tried to keep the code modularized, so it can be used for other similar projects (documentations in markdown). There are some things that you might wanna look into before getting started:
- First thing to do is change the REPO_NAME & CONTENT_FOLDER in the `.env` file with the information of your repo.
- Next thing to look into is `nextUtil.py` file. There are 2 methods inside it that you just need to create 2 functions (`processFile`, `chunkMarkdown`) with same signature in another file, then again run the `index.py` script & you should directly be able to update import in index.py file to see the updated index.
## Further Ideas

- I saw that there were chunks which contained single lines after removing headings and extra spaces. I feel we should remove these because however very significantly these might create performance issue. Because let's say we are pulling 5 chunks and 1 of these gets pulled, it's a waste since it is not providing any information.

- Right now for each version we are processing we are creating a separate file, but we can maybe try creating a single file. Creating a single file would allow us to remove duplicate data which can be a lot between version. But think about the implications it will have on adding new data or updating old one. Also, the working of filter when multiple version info is saved in same place.