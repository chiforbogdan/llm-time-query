from langchain.pydantic_v1 import BaseModel
from langchain.prompts import PromptTemplate
from langchain.pydantic_v1 import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain.output_parsers import PydanticOutputParser
from typing import List

class AndroidApplicationStatusInfo(BaseModel):
    user: str = Field(description="the user name referred in the text")
    application: str = Field(description="the android application name referred in the text")
    status: str = Field(description="the status of the application name referred in the text: must be running or stopped")

class AndroidApplicationStatus(BaseModel):
    application_status: List[AndroidApplicationStatusInfo]

class LLMEvaluator:
    def __init__(self, llm_querier):
        self.llm_querier = llm_querier
        self.model = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)

    def run_status_tests(self, tests):
        parser = PydanticOutputParser(pydantic_object=AndroidApplicationStatus)
        prompt = PromptTemplate(
            template="You are an Android technical expert which analyzes a sentence regarding Android application statuses.\n"
                    "This sentence should contain an Android user name, an application name and the running status of the application.\n"
                    "\n{format_instructions}"
                    "\nThe sentence is the following: {sentence}\n",
            input_variables=["sentence"],
            partial_variables={"format_instructions": parser.get_format_instructions()},
        )

        for test in tests:
            test_id = test['test_id']
            print(f"####################### Running test {test_id} ################################")
            sentence = self.llm_querier.query(test['query'])
            input=prompt.format_prompt(sentence=sentence).to_string()
            output = self.model(input)
            application_statuses = parser.parse(output.content).application_status
            passed = True
            for response in test['responses']:
                found = False
                for application_status in application_statuses:
                    if response['user'].lower() == application_status.user.lower() and \
                        response['application'].lower() == application_status.application.lower() and \
                        response['status'].lower() == application_status.status.lower():
                        found = True
                        break
                if not found:
                    passed = False
                    break
            if passed == True:
                print(f"Test {test_id}: PASS")
            else:
                print(f"Test {test_id}: FAIL")
                print(application_statuses)