from typing import List
from langchain.llms import OpenAI
from langchain.output_parsers import PydanticOutputParser
from langchain.prompts import PromptTemplate
from langchain.pydantic_v1 import BaseModel, Field, validator
from datetime import datetime
from typing import Optional
import llm_index

from langchain.tools import BaseTool
from langchain import hub
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.agents.format_scratchpad.openai_tools import (
    format_to_openai_tool_messages,
)
from langchain.agents.output_parsers.openai_tools import OpenAIToolsAgentOutputParser
from langchain.tools.render import format_tool_to_openai_function
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage, HumanMessage

from typing import Type

class UserId(BaseModel):
    user_id: str = Field(description="id of a user given his firstname, lastname or a combination of these")

class UserSubject(BaseModel):
    user_names: List[str] = Field(description="name of the user specified in the query")

class LogcatInput(BaseModel):
    user_id: str = Field(description="android user id")
    start_time: datetime = Field(description="start time for logcat queries")
    end_time: datetime = Field(description="end time for logcat queries")
    android_query: str = Field(description="android specific query for a user. What should you query in the logcat file.")

class IpWhitelistTool(BaseTool):
    name = "get_whitelist_ip"
    description = "use this tool when you need to get a list of whitelist IP addresses"

    def _run(self):
        print(f"DBG get whitelist IP")
        return "1.1.1.1"

    def _arun(self):
        raise NotImplementedError("This tool does not support async")

class IpBlacklistTool(BaseTool):
    name = "get_blacklist_ip"
    description = "use this tool when you need to get a list of blacklist IP addresses"

    def _run(self):
        print(f"DBG get blacklist IP")
        return "8.8.8.8"

    def _arun(self):
        raise NotImplementedError("This tool does not support async")

class CurrentTimeTool(BaseTool):
    name = "get_current_time"
    description = "use this tool when you need to get the current time"

    def _run(self):
        current_time = datetime.now().isoformat()
        print(f"DBG get current time {current_time}")
        return current_time

    def _arun(self):
        raise NotImplementedError("This tool does not support async")

class LogcatTool(BaseTool):
    name = "get_logcat"
    description = "use this tool when you need to get android logs for a certain user id"
    args_schema: Type[BaseModel] = LogcatInput

    def _run(self, user_id: str, start_time: datetime, end_time: datetime, android_query: str):
        print(f"DBG GET LOGCAT for {user_id} start time: {start_time} end time: {end_time} android_query: {android_query}")
        return self.metadata['index'].query_logcat(user_id, start_time, end_time, android_query)

    def _arun(self):
        raise NotImplementedError("This tool does not support async")

class AndroidUserIdTool(BaseTool):
    name = "get_android_user_id"
    description = "use this tool when you need to find the Android user identifier (user ID) for a single name that appears in the query. The input must be a name or a Firstname Lastname combination."

    def _run(self, user: str):
        print(f"DBG GET USER ID for {user}")

        users_db = self.metadata['index'].get_users()

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
        
        input = prompt.format_prompt(user=user, users_db=users_db)
        output = self.metadata['llm'](input.to_string())
        user_id = parser.parse(output.content).user_id
        print(f"DBG USER ID for name: {user} is {user_id}")

        return user_id

    def _arun(self):
        raise NotImplementedError("This tool does not support async")

class LLMQuery:
    def __init__(self, index: llm_index.LLMIndex):
        self.index = index
        llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are an expert system administrator with can interpret Android logs (logcat)."
                    "You can get the logcat information using the user ID."

                    "When querying a log tool you need to specify the start time and end time of the query relative to the current time which you must get using a tool."
                    "If there is no time interval specified by human, query log with end time as current time and start time is beggining of current day: get this info using time tool."
                    "If there are multiple users in the query you need to get individual information for each user."
                    
                ),
                MessagesPlaceholder(variable_name='chat_history'),
                ("user", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ]
        )

        tools = [AndroidUserIdTool(metadata={'index': index, 'llm': llm}),
                 LogcatTool(metadata={'index': index}),
                 CurrentTimeTool(),
                 IpBlacklistTool(),
                 IpWhitelistTool()]
        llm_with_tools = llm.bind_tools(tools)

        agent = (
            {
                "input": lambda x: x["input"],
                "agent_scratchpad": lambda x: format_to_openai_tool_messages(
                    x["intermediate_steps"]
                ),
                "chat_history": lambda x: x["chat_history"],
            }
            | prompt
            | llm_with_tools
            | OpenAIToolsAgentOutputParser()
        )

        self.agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
        self.chat_history = []

    def query(self, query: str):
        result = self.agent_executor.invoke({"input": query, "chat_history": self.chat_history})
        self.chat_history.extend(
            [
                HumanMessage(content=query),
                AIMessage(content=result["output"]),
            ]
        )