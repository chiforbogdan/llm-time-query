from openai import OpenAI
from typing import List
from termcolor import colored

class LLMEvaluator:
    def __init__(self, llm_querier):
        self.llm_querier = llm_querier
        self.openai_client = OpenAI()
        self.messages = [ 
            {   
                "role": "system",
                "content": (
                    "Task:\n"
                    "Validate the accuracy and completeness of the summary generated for a Linux system log against the summary provided by OpenAI.\n"
                    "Instructions:\n"
                    "- Review the provided system log and query.\n"
                    "- Compare the summary you generated with the summary provided by OpenAI.\n"
                    "- Assess if the OpenAI summary accurately reflects the key details and information from the system log related to the query.\n"
                    "- Provide feedback on the accuracy of the OpenAI summary:\n"
                    "Is it accurate? (Yes/No)\n"
                    "Are there any missing or incorrect details? (Yes/No)\n"
                    "List any discrepancies or additional insights that should be included.\n"
                )   
            },  
            {   
                "role": "user",
            }   
        ] 

    def run_status_tests_linux(self, test_set):
        for test in test_set:
            test_id = test['test_id']
            print(colored(f"\n\n####################### Running test {test_id} ################################", "red"))
            sentence = self.llm_querier.query(test['query'])

            self.messages[1]["content"] = f"Query: {test['query']} \nLogs: {test['validation_log']} \n Summary: {sentence}"
            result = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=self.messages,
                temperature=0.1,
                top_p = 0.8
            )
            print(colored("Query:", "green"))
            print(colored(test['query'], "blue"))
            print(colored("\nRAG system Output:", "green"))
            print(sentence.choices[0].message.content)
            print(colored("\nOpenAI Output:", "green"))
            print(result.choices[0].message.content)

