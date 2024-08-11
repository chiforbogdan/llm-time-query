from typing import List
from langchain.llms import OpenAI
from langchain.output_parsers import PydanticOutputParser
from langchain.prompts import PromptTemplate
from langchain.pydantic_v1 import BaseModel, Field, validator
from datetime import datetime
from typing import Optional
import llm_index

class UserId(BaseModel):
    user_id: str = Field(description="id of a user given his firstname, lastname or a combination of these")

class UserSubject(BaseModel):
    user_names: List[str] = Field(description="name of the user specified in the query")

class TimeFilter(BaseModel):
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

class LLMQuery:
    def __init__(self, index: llm_index.LLMIndex):
        self.index = index
        self.model = OpenAI(temperature=0)

    def query(self, query: str):
        time_filter = self._get_timestamps(query)

        user_subject = self._get_user_subject(query)
        user_ids = self._get_user_id(user_subject)

        prompt = PromptTemplate(
            template="Logcat logs for user with name {user_name} are the following:\n{logcat_logs}\n",
            input_variables=["user_name", "logcat_logs"],
        )
        context = ""
        for user_name, uid in user_ids.items():
            rag_logcat = self.index.query_logcat(uid, time_filter.start_date, time_filter.end_date, query)
            context = context + prompt.format_prompt(user_name=user_name, logcat_logs=rag_logcat).to_string()
        return self._answer_query(context, query)

    def _answer_query(self, logcat_logs, query):
        prompt = PromptTemplate(
            template="You are an expert system administrator with advanced Android operating system knowledge"
                    " which is tasked to debug and analyze the state of an Android system."
                    "You are given the following Android logcat logs for several users:\n{logcat_logs}"
                    "Analyze the logs for each user individually and give an accurate answer to the following question:\n{query}",
            input_variables=["logcat_logs", "query"],
        )

        _input = prompt.format_prompt(logcat_logs=logcat_logs, query=query)
        output = self.model(_input.to_string())

        return output

    def _get_timestamps(self, query: str) -> TimeFilter:
        parser = PydanticOutputParser(pydantic_object=TimeFilter)

        prompt = PromptTemplate(
            template="You are a query generator for customer support tickets."
                    "You need to extract the start time and the end time of the query."
                    "The current date is {current_timestamp}\n{format_instructions}\n{query}\n",
            input_variables=["current_timestamp", "query"],
            partial_variables={"format_instructions": parser.get_format_instructions()},
        )

        current_datetime = datetime.now()
        datetime_string = current_datetime.strftime("%Y-%m-%d %H:%M:%S")
        _input = prompt.format_prompt(query=query, current_timestamp=datetime_string)
        output = self.model(_input.to_string())

        return parser.parse(output)

    def _get_user_subject(self, query: str) -> UserSubject:
        parser = PydanticOutputParser(pydantic_object=UserSubject)
        prompt = PromptTemplate(
            template="You are a query generator for customer support tickets."
                    "You need to extract the user name referred in the query."
                    "If there are multiple users list all of them."
                    "\n{format_instructions}\n{query}\n",
            input_variables=["query"],
            partial_variables={"format_instructions": parser.get_format_instructions()},
        )
        _input = prompt.format_prompt(query=query)
        output = self.model(_input.to_string())

        return parser.parse(output)

    def _get_user_id(self, user_subject: UserSubject):
        users_db = self.index.get_users()

        parser = PydanticOutputParser(pydantic_object=UserId)
        prompt = PromptTemplate(
            template="You are a database expert which is given a JSON file containing a list of users with the following fields: e-mail, name, ID."
                    "You are given a user's name or a partial name. You need to deliver the user ID which best matches the given name."
                    "For matching the given input name with an ID you need to analyze the e-mail and name fields from the given JSON file."
                    "\n{format_instructions}"
                    "\n The JSON file containing the user data the following:{users_db}"
                    "\nThe name for which you need to deliver the ID is the following: {user}\n",
            input_variables=["query", "users_db"],
            partial_variables={"format_instructions": parser.get_format_instructions()},
        )

        user_ids = {}
        for user in user_subject.user_names:
            _input = prompt.format_prompt(user=user, users_db=users_db)
            output = self.model(_input.to_string())
            user_ids[user] = parser.parse(output).user_id

        return user_ids
