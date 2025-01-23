# NextAssist
This project builds a RAG pipeline on last 6 (major & minor releases) versions of [NextJS](https://nextjs.org/). This will allow for better next.js related query resolution.

I have ignored the canary and minor releases and focus only on major & minor releases only.

## Tech Stack
[Cortex Search](https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-search/cortex-search-overview), [Mistral LLM](https://mistral.ai/), & [Streamlit Community Cloud](https://streamlit.io/cloud)

## Setting Up Locally:
- The `scripts` folder contains all the required scripts. You just have to follow these steps: 
    - Create a `.env` file with appropriate values (a sample `.env.example` file is already given, you can directly rename that file to .env as well and update)

    ### To setup for NextJS:
    Nothing needs to be done for this. You can look into configurations and look around to play with things (like chunking strategy or so on).
    ### Using for Other Repo:
    I have tried to keep the code modularized, so it can be used for other similar projects (documentations in markdown). There are some things that you might wanna look into before getting started:

    - You need to change the necessary env variables (like `REPO_NAME`, `MAJOR_VERSION`, `MINOR_VERSION` and so on) first.
    - Then you need to write a version of function `processFile` with same signature as in `scripts/nextUtil.py`. This is the function that determines how each doc file will be parsed.
    - If the current chunking strategy doesn't work for you then you can re-write the `chunkMarkdown` function in same file as well.
    - And don't forget to update the import for these new methods in your index.py file.

    - **Note**: You can ignore other functions in `scripts/nextUtil.py` other than these 2. Those are nextjs specific and won't be very helpful to you.

        **Note**: Keep the function signature of the function you are writing exactly the same as already written versions.

- Then just install the dependencies:
    ```python 
    poetry install
    ```

- Then just run `index.py` and it will take care of everything (Download the data -> processing files -> Chunking -> Setting up the DB -> Inserting Data -> Creation of Search Service)

    ```python 
    python scripts/index.py
    ```

## Starting the Service:
You can use:

```python 
streamlit run app.py
```

OR 

```shell
docker-compose up --build
```


## Overview
### Data Preparation (Cleaning & Chunking):
#### Documentation
- In the documentation next avoids repeating the content for both it's routers (app & pages) so they write all the content in one of the place using tags like (`<AppOnlyl>` & `<PagesOnly>`) and then mentions the source in the other file. I wrote a simple script to get complete files for both router so it would be easier to chunk both the files.

- The chunking strategy plays an important role in the final result. According to the Cortex Search Documentation:
    > For optimal search results with Cortex Search, Snowflake recommends splitting the text in your search column into chunks of no more than 512 tokens (about 385 English words). When an entry in the search column contains more than 512 tokens, Cortex Search performs keyword-based retrieval on the entire body of text, but only uses the first 512 tokens for semantic (i.e., vector-based) retrieval.

    So keeping this in mind we have to think about chunking strategy. I wrote a bit custom code for that the idea is this:
    
    - I took the first heading present and entire content inside it as the first chunk entirely and then kept recursively splitting it based on headings until the chunk size became smaller than expected (385 words). 
    - Also, I made sure that the code blocks don't get split between two chunks. This is sometimes leading to a chunk size bigger than expected. I am just keeping it for now.

#### Issues & Discussions
- The `snowSetup.py` file contains code to pull new discussions and issues and insert them to the DB. If there are no issues and discussion then the issues and discussions after "2024-01-01" will be pulled and inserted.
- For discussion I am using "is:answered" filter and for issues "state:closed interactions:>1".

### Building the Search
- The search service for both docs and posts (issues & discussions) is different. This allows us to look into issues and discussion only when required.
- The parameters for building the search service search as database name, embedding model to use and others can be configured in the env file.

## Guardrails:
- [Trulens](https://www.trulens.org/) helps with that. You can set your provider and what metrics you want to set on what part (input or output).
- We are using guardrails to filter out the irrelevant contexts during retrieval
- I am using **OpenAI** provider for this right now because other models available on cortex seemed to be failing for some queries which caused problem during runtime.

## Evaluations
- [Trulens](https://www.trulens.org/) allowed us to test the application as well.
- For evaluations I have a `tests.json` file in my tests directory.
- For running your own evaluation directly run:
```python
python eval.py
```

## Further Ideas
- The second version has a latency issue. We can fix it by using an async version of `Complete` function for LLM completion from snowflake. I couldn't find anything on that. I tried writing the requests manually (by backtracking Complete) but it was also slow for some reason. This needs to be fixed.

- Creating an integration for docusaurus will have a huge impact becauuse it will allow to parse all the projects using docusaurus. 

- I saw that there were chunks which contained single lines after removing headings and extra spaces. I feel we should remove these because however very significantly these might create performance issue. Because let's say we are pulling 5 chunks and 1 of these gets pulled, it's a waste since it is not providing any information.

- Right now for each version we are processing we are creating a separate file, but we can maybe try creating a single file. Creating a single file would allow us to remove duplicate data which can be a lot between version. But think about the implications it will have on adding new data or updating old one. Also, the working of filter when multiple version info is saved in same place.