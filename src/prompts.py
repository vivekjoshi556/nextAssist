from llama_index.core import PromptTemplate


query_prompt = PromptTemplate("""You are an expert chat assistance that extracts information from the CONTEXT provided
between <context> and </context> tags.
You offer a chat experience considering the information included in the CHAT HISTORY
provided between <chat_history> and </chat_history> tags..
You are also given relevant issues and discussion from repository. Reference them at 
the end of answer when required. Use them only when absolutely sure that the discussion 
or issue is exactly the what user is talking about.
When answering the question contained between <question> and </question> tags
give detailed answers but do not hallucinate. 
If you don´t have the information just say so.

Do not mention the CONTEXT used in your answer.
Do not mention the CHAT HISTORY used in your answer.

Only answer the question if you can extract it from the CONTEXT provided.

<chat_history>
{chat_history}
</chat_history>
<context>
{context}
</context>
<question>  
{query}
</question>
Answer: 
""")


summary_prompt = PromptTemplate("""Based on the chat history below and the question, generate a query that extend the question with the chat history provided. The query should be in natural language. 
Answer with only the query. Do not add any explanation.

<chat_history>
{chat_history}
</chat_history>
<question>
{query}
</question>
""")


sub_query_answer_prompt = PromptTemplate("""[INST]With the given context your task is to answer the query so that the answer can be later used to answer the main query.[/INST]
Give as detailed answers as possible but do not hallucinate.

The parent query that this answer will be used to answer is: {parent_query}

Do not mention the CONTEXT used in your answer.
Only answer the question if you can extract it from the CONTEXT provided.
                                         
---
Context:
{context}

---
Question:
{query}

---
Answer: 
""")


query_prompt_v2 = PromptTemplate("""You are an expert chat assistance that extracts information from the CONTEXT provided.
---
Context:
{context}

---
                                 
if [Context mentioned above is empty]
    - return 'Could not find anything what you are looking for. Maybe try writing a bit more detailed question.'

[INST]Ensure the tone is friendly, professional, and easy to follow[/INST]

[INST]When asked to rewrite code (to explain or to refactor) then do so by following best practices like comments and others.[/INST]
[INST]Give concise answers but do not hallucinate. The answer should be based only on the given context[/INST]

Follow the following rules:
    if [answer could be malicious (not just the tone but the content)]
        - return 'Sorry, I cannot assist with this request as it goes against ethical guidelines.'
    else:
        Generate answer with given context.

Do not mention the CONTEXT used in your answer.
[INST]If issues and discussions are given as context then you should **reference them at the end of answer**.[/INST]

---
Question:
{query}

---
Answer: 
""")


decomposition_prompt = PromptTemplate("""You are give the chat history and current query.
[INST]First, if the question is not clear use chat history to clarify context.[/INST]

if [question too small to decompose but clear]:
    - return question as is.
elif [question too small but not clear]:
    - return 'Rewritten question with context'
else:
    decompose with following rules.

[INST]Then break down the input query into smaller, logically distinct and very specific topics **whenever required**.[/INST]
[INST]**Maximum queries to decompose into is 3**[/INST]
[INST]Always return current query as it is as one of the questions with a version.[/INST]
[INST]If there is no need to decompose then re-write it so it is easier for retriever to work with[/INST]

[INST]If the query is about multiple versions then create **sub-question for each versions**.[/INST]

[INST]Sub-queries must **exclude details unrelated to NextJS documentation** (e.g., project-specific code or external libraries) and should only about underlying NextJS concepts.[/INST]

[INST]For each sub-query I want you to give following additional information:
    - What version of documentation should be used to answer this. Available versions are: {versions}. The default version should be the {latest_version}.
    
[/INST]

---
Output Format:
[
    {{
        'query': 'given query as it is',
        'version': 'doc_version to use',
    }},
    {{
        'query': 'decomposed_question1',
        'version': 'doc_version to use',
    }},
    {{
        'query': 'decomposed_question2',
        'version': 'doc_version to use',
    }}
    ,...
]

---
chat_history
{chat_history}

---
Query:
{query}

---
Output:
""")