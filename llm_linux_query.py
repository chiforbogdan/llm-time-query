from openai import OpenAI
import llm_index
from datetime import datetime
from langchain_core.messages import AIMessage, HumanMessage
    
class LLMQueryLinux:
    def __init__(self, index: llm_index.LLMIndex):
        self.index = index
        self.openai_client = OpenAI()
        self.messages = [ 
            {   
                "role": "system",
                "content": (
                    "You are an expert in analyzing Linux system logs. Your primary task is to interpret and provide insights "
                    "based on the log entries provided. Pay special attention to timestamps as they are crucial for understanding "
                    "the sequence and timing of events in the logs. You will receive a user query related to the log entries, "
                    "and you should use the information from these logs to answer the query accurately and precisely with particular emphasis "
                    "on the timestamps."
                )   
            },  
            {   
                "role": "user",
            }   
        ]   


    def query(self, query: str):
        # TODO do i wanna add this here?
        #self.chat_history = []
        db_result = self.index.query_linux_log(query)
        self.messages[1]["content"] = f"Query: {query} \nLogs: {db_result}"
        result = self.openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=self.messages,
            temperature=0.5,
        )   

        return result
