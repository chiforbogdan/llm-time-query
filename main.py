import llm_query
import llm_index
import os
from datetime import datetime


def main():
    query = "Was Android application MyAppTag1 running for Bogdan on 10th August?"

    os.environ["OPENAI_API_KEY"] = "OPENAI_API_KEY"

    index = llm_index.LLMIndex()
    index.load_users('data/users.json')
    index.load_logcat('data/logcat')
    index.load_linux_log('data/linux')
    
    querier = llm_query.LLMQuery(index)
    response = querier.query(query)   
    print(response)
  
if __name__ == "__main__":
    main()
