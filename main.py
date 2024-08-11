import llm_query
import llm_index
import os

def main():
    query = "Was application MyAppTag1 running yesterday for Bogdan & Lasse's CVD?"

    index = llm_index.LLMIndex()
    index.load_users('data/users.json')
    index.load_logcat('data/logcat')
    
    querier = llm_query.LLMQuery(index)
    response = querier.query(query)   
    print(response)

if __name__ == "__main__":
    main()