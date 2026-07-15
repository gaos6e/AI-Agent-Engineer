---
title: SQL 代理
aliases:
  - SQL Agent
  - SQL 代理
source: https://docs.langchain.com/oss/python/langchain/sql-agent
source_md: https://docs.langchain.com/oss/python/langchain/sql-agent.md
retrieved: 2026-05-07
tags:
  - langchain
  - python
  - docs/learn
license: MIT
---

# SQL 代理

## 概述

在本教程中，您将学习如何使用 LangChain [agents](https://docs.langchain.com/oss/python/langchain/agents) 构建一个可以回答有关 SQL 数据库问题的代理。

在较高层面上，代理人将：

### 从数据库中获取可用表和 schema

### 确定哪些表格与问题相关

### 获取相关表的 schema

### 根据问题和 schema 信息生成查询

### 使用 LLM 仔细检查查询是否存在常见错误

### 执行查询并返回结果

### 纠正数据库引擎出现的错误，直到查询成功

### 根据结果​​制定响应

> [!warning]
构建 SQL 数据库的问答系统需要执行模型生成的 SQL 查询。这样做存在固有的风险。确保数据库连接权限的范围始终尽可能缩小，以满足代理的需求。这将减轻（但不能消除）构建模型驱动系统的风险。

### 概念

我们将涵盖以下概念：

* [工具](https://docs.langchain.com/oss/python/langchain/tools) 用于从 SQL 数据库读取
* LangChain[代理商](https://docs.langchain.com/oss/python/langchain/agents)
* [人在回路](https://docs.langchain.com/oss/python/langchain/human-in-the-loop) 流程

## 设置

### 安装
```bash
# 安装依赖：先把示例需要的包安装到当前 Python 环境。
pip install langchain  langgraph  langchain-community
```
### LangSmith

设置 [LangSmith](https://smith.langchain.com?utm_source=docs\&utm_medium=cta\&utm_campaign=langsmith-signup\&utm_content=oss-langchain-sql-agent) 来检查您的链或代理内部发生的情况。然后设置以下环境变量：
```shell
# 配置环境变量：示例会从环境变量读取 API key、模型名或服务地址。
export LANGSMITH_TRACING="true"
export LANGSMITH_API_KEY="..."
```
## 1. 选择LLM

选择支持[工具调用](https://docs.langchain.com/oss/python/integrations/providers/overview)的模型：

#### OpenAI
👉 阅读[OpenAI 聊天模型集成文档](https://docs.langchain.com/oss/python/integrations/chat/openai/)
```shell
# 安装依赖：先把示例需要的包安装到当前 Python 环境。
pip install -U "langchain[openai]"
```

```python
import os
from langchain.chat_models import init_chat_model

os.environ["OPENAI_API_KEY"] = "sk-..."

# 初始化 chat model：后续 agent、chain 或 graph 都会通过这个模型向 LLM 发请求。
model = init_chat_model("gpt-5.4")
```

```python
import os
from langchain_openai import ChatOpenAI

os.environ["OPENAI_API_KEY"] = "sk-..."

# 这里创建具体 provider 的聊天模型对象；保留 provider 名称，便于和官方文档对照。
model = ChatOpenAI(model="gpt-5.4")
```
#### Anthropic
👉 阅读[Anthropic聊天模型集成文档](https://docs.langchain.com/oss/python/integrations/chat/anthropic/)
```shell
# 安装依赖：先把示例需要的包安装到当前 Python 环境。
pip install -U "langchain[anthropic]"
```

```python
import os
from langchain.chat_models import init_chat_model

os.environ["ANTHROPIC_API_KEY"] = "sk-..."

# 初始化 chat model：后续 agent、chain 或 graph 都会通过这个模型向 LLM 发请求。
model = init_chat_model("claude-sonnet-4-6")
```

```python
import os
from langchain_anthropic import ChatAnthropic

os.environ["ANTHROPIC_API_KEY"] = "sk-..."

# 这里创建具体 provider 的聊天模型对象；保留 provider 名称，便于和官方文档对照。
model = ChatAnthropic(model="claude-sonnet-4-6")
```
#### Azure
👉 阅读[Azure 聊天模型集成文档](https://docs.langchain.com/oss/python/integrations/chat/azure_chat_openai/)
```shell
# 安装依赖：先把示例需要的包安装到当前 Python 环境。
pip install -U "langchain[openai]"
```

```python
import os
from langchain.chat_models import init_chat_model

os.environ["AZURE_OPENAI_API_KEY"] = "..."
os.environ["AZURE_OPENAI_ENDPOINT"] = "..."
os.environ["OPENAI_API_VERSION"] = "2025-03-01-preview"

# 初始化 chat model：后续 agent、chain 或 graph 都会通过这个模型向 LLM 发请求。
model = init_chat_model(
    "azure_openai:gpt-5.4",
    azure_deployment=os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"],
)
```

```python
import os
from langchain_openai import AzureChatOpenAI

os.environ["AZURE_OPENAI_API_KEY"] = "..."
os.environ["AZURE_OPENAI_ENDPOINT"] = "..."
os.environ["OPENAI_API_VERSION"] = "2025-03-01-preview"

model = AzureChatOpenAI(
    model="gpt-5.4",
    azure_deployment=os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"]
)
```
#### Google Gemini
👉 阅读 [Google GenAI 聊天模型集成文档](https://docs.langchain.com/oss/python/integrations/chat/google_generative_ai/)
```shell
# 安装依赖：先把示例需要的包安装到当前 Python 环境。
pip install -U "langchain[google-genai]"
```

```python
import os
from langchain.chat_models import init_chat_model

os.environ["GOOGLE_API_KEY"] = "..."

# 初始化 chat model：后续 agent、chain 或 graph 都会通过这个模型向 LLM 发请求。
model = init_chat_model("google_genai:gemini-2.5-flash-lite")
```

```python
import os
from langchain_google_genai import ChatGoogleGenerativeAI

os.environ["GOOGLE_API_KEY"] = "..."

model = ChatGoogleGenerativeAI(model="gemini-2.5-flash-lite")
```
#### AWS Bedrock
👉 阅读 [AWS Bedrock 聊天模型集成文档](https://docs.langchain.com/oss/python/integrations/chat/bedrock/)
```shell
# 安装依赖：先把示例需要的包安装到当前 Python 环境。
pip install -U "langchain[aws]"
```

```python
from langchain.chat_models import init_chat_model

# 按这里的步骤配置凭据：
# 参考链接：https://docs.aws.amazon.com/bedrock/latest/userguide/getting-started.html

model = init_chat_model(
    "anthropic.claude-3-5-sonnet-20240620-v1:0",
    model_provider="bedrock_converse",
)
```

```python
from langchain_aws import ChatBedrock

# 这里创建具体 provider 的聊天模型对象；保留 provider 名称，便于和官方文档对照。
model = ChatBedrock(model="anthropic.claude-3-5-sonnet-20240620-v1:0")
```
#### Hugging Face
👉 阅读 [HuggingFace 聊天模型集成文档](https://docs.langchain.com/oss/python/integrations/chat/huggingface/)
```shell
# 安装依赖：先把示例需要的包安装到当前 Python 环境。
pip install -U "langchain[huggingface]"
```

```python
import os
from langchain.chat_models import init_chat_model

os.environ["HUGGINGFACEHUB_API_TOKEN"] = "hf_..."

# 初始化 chat model：后续 agent、chain 或 graph 都会通过这个模型向 LLM 发请求。
model = init_chat_model(
    "microsoft/Phi-3-mini-4k-instruct",
    model_provider="huggingface",
    temperature=0.7,
    max_tokens=1024,
)
```

```python
import os
from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint

os.environ["HUGGINGFACEHUB_API_TOKEN"] = "hf_..."

llm = HuggingFaceEndpoint(
    repo_id="microsoft/Phi-3-mini-4k-instruct",
    temperature=0.7,
    max_length=1024,
)
model = ChatHuggingFace(llm=llm)
```
#### OpenRouter
👉 阅读[OpenRouter聊天模型集成文档](https://docs.langchain.com/oss/python/integrations/chat/openrouter/)
```shell
# 安装依赖：先把示例需要的包安装到当前 Python 环境。
pip install -U "langchain-openrouter"
```

```python
import os
from langchain.chat_models import init_chat_model

os.environ["OPENROUTER_API_KEY"] = "sk-..."

# 初始化 chat model：后续 agent、chain 或 graph 都会通过这个模型向 LLM 发请求。
model = init_chat_model(
    "auto",
    model_provider="openrouter",
)
```

```python
import os
from langchain_openrouter import ChatOpenRouter

os.environ["OPENROUTER_API_KEY"] = "sk-..."

model = ChatOpenRouter(model="auto")
```
以下示例中显示的输出使用 OpenAI。

## 2.配置数据库

您将为本教程创建一个 [SQLite 数据库](https://www.sqlitetutorial.net/sqlite-sample-database/)。 SQLite 是一个轻量级数据库，易于设置和使用。我们将加载 `chinook` 数据库，这是一个代表数字媒体商店的示例数据库。

为方便起见，我们将数据库 (`Chinook.db`) 托管在公共 GCS 存储桶上。
```python
import requests, pathlib

url = "https://storage.googleapis.com/benchmarks-artifacts/chinook/Chinook.db"
local_path = pathlib.Path("Chinook.db")

if local_path.exists():
    print(f"{local_path} already exists, skipping download.")
else:
    response = requests.get(url)
    if response.status_code == 200:
        local_path.write_bytes(response.content)
        print(f"File downloaded and saved as {local_path}")
    else:
        print(f"Failed to download the file. Status code: {response.status_code}")
```
我们将使用 `langchain_community` 包中提供的方便的 SQL 数据库包装器来与数据库交互。包装器提供了一个简单的接口来执行 SQL 查询并获取结果：
```python
from langchain_community.utilities import SQLDatabase

# SQLDatabase 连接示例数据库，后续 SQL agent 会通过 tools 查看 schema 并执行查询。
db = SQLDatabase.from_uri("sqlite:///Chinook.db")

print(f"Dialect: {db.dialect}")
print(f"Available tables: {db.get_usable_table_names()}")
print(f'Sample output: {db.run("SELECT * FROM Artist LIMIT 5;")}')
```

```
Dialect: sqlite
Available tables: ['Album', 'Artist', 'Customer', 'Employee', 'Genre', 'Invoice', 'InvoiceLine', 'MediaType', 'Playlist', 'PlaylistTrack', 'Track']
Sample output: [(1, 'AC/DC'), (2, 'Accept'), (3, 'Aerosmith'), (4, 'Alanis Morissette'), (5, 'Alice In Chains')]
```
## 3.添加数据库交互工具

使用 `langchain_community` 包中提供的 `SQLDatabase` 包装器与数据库交互。包装器提供了一个简单的接口来执行 SQL 查询并获取结果：
```python
from langchain_community.agent_toolkits import SQLDatabaseToolkit

toolkit = SQLDatabaseToolkit(db=db, llm=model)

tools = toolkit.get_tools()

for tool in tools:
    print(f"{tool.name}: {tool.description}\n")
```

```
sql_db_query: Input to this tool is a detailed and correct SQL query, output is a result from the database. If the query is not correct, an error message will be returned. If an error is returned, rewrite the query, check the query, and try again. If you encounter an issue with Unknown column 'xxxx' in 'field list', use sql_db_schema to query the correct table fields.

sql_db_schema: Input to this tool is a comma-separated list of tables, output is the schema and sample rows for those tables. Be sure that the tables actually exist by calling sql_db_list_tables first! Example Input: table1, table2, table3

sql_db_list_tables: Input is an empty string, output is a comma-separated list of tables in the database.

sql_db_query_checker: Use this tool to double check if your query is correct before executing it. Always use this tool before executing a query with sql_db_query!
```
## 4.使用`create_agent`

使用 [`create_agent`](https://reference.langchain.com/python/langchain/agents/factory/create_agent) 以最少的代码构建 [ReAct 代理](https://arxiv.org/pdf/2210.03629)。代理将解释请求并生成 SQL 命令，工具将执行该命令。如果命令有错误，错误消息将返回给模型。然后，该模型可以检查原始请求和新的错误消息并生成新命令。这可以继续，直到 LLM 成功生成命令或达到停止条件。这种为模型提供反馈（本例中为错误消息）的模式非常强大。

使用描述性系统提示初始化代理以自定义其行为：
```python
system_prompt = """
You are an agent designed to interact with a SQL database.
Given an input question, create a syntactically correct {dialect} query to run,
then look at the results of the query and return the answer. Unless the user
specifies a specific number of examples they wish to obtain, always limit your
query to at most {top_k} results.

You can order the results by a relevant column to return the most interesting
examples in the database. Never query for all the columns from a specific table,
only ask for the relevant columns given the question.

You MUST double check your query before executing it. If you get an error while
executing a query, rewrite the query and try again.

DO NOT make any DML statements (INSERT, UPDATE, DELETE, DROP etc.) to the
database.

To start you should ALWAYS look at the tables in the database to see what you
can query. Do NOT skip this step.

Then you should query the schema of the most relevant tables.
""".format(
    dialect=db.dialect,
    top_k=5,
)
```
现在，使用模型、工具和提示创建代理：
```python
from langchain.agents import create_agent

# create_agent 会把模型、tools、系统提示词和 middleware 组装成一个可运行的 agent。
agent = create_agent(
    model,
    tools,
    system_prompt=system_prompt,
)
```
## 5. 运行代理

对示例查询运行代理并观察其行为：
```python
question = "Which genre on average has the longest tracks?"

# 这里是实际运行入口：传入 messages 或 state 后，系统会执行推理、工具调用和状态更新。
for step in agent.stream(
    {"messages": [{"role": "user", "content": question}]},
    stream_mode="values",
):
    step["messages"][-1].pretty_print()
```

```
================================ Human Message =================================

Which genre on average has the longest tracks?
================================== Ai Message ==================================
Tool Calls:
  sql_db_list_tables (call_BQsWg8P65apHc8BTJ1NPDvnM)
 Call ID: call_BQsWg8P65apHc8BTJ1NPDvnM
  Args:
================================= Tool Message =================================
Name: sql_db_list_tables

Album, Artist, Customer, Employee, Genre, Invoice, InvoiceLine, MediaType, Playlist, PlaylistTrack, Track
================================== Ai Message ==================================
Tool Calls:
  sql_db_schema (call_i89tjKECFSeERbuACYm4w0cU)
 Call ID: call_i89tjKECFSeERbuACYm4w0cU
  Args:
    table_names: Track, Genre
================================= Tool Message =================================
Name: sql_db_schema

CREATE TABLE "Genre" (
	"GenreId" INTEGER NOT NULL,
	"Name" NVARCHAR(120),
	PRIMARY KEY ("GenreId")
)

/*
3 rows from Genre table:
GenreId	Name
1	Rock
2	Jazz
3	Metal
*/

CREATE TABLE "Track" (
	"TrackId" INTEGER NOT NULL,
	"Name" NVARCHAR(200) NOT NULL,
	"AlbumId" INTEGER,
	"MediaTypeId" INTEGER NOT NULL,
	"GenreId" INTEGER,
	"Composer" NVARCHAR(220),
	"Milliseconds" INTEGER NOT NULL,
	"Bytes" INTEGER,
	"UnitPrice" NUMERIC(10, 2) NOT NULL,
	PRIMARY KEY ("TrackId"),
	FOREIGN KEY("MediaTypeId") REFERENCES "MediaType" ("MediaTypeId"),
	FOREIGN KEY("GenreId") REFERENCES "Genre" ("GenreId"),
	FOREIGN KEY("AlbumId") REFERENCES "Album" ("AlbumId")
)

/*
3 rows from Track table:
TrackId	Name	AlbumId	MediaTypeId	GenreId	Composer	Milliseconds	Bytes	UnitPrice
1	For Those About To Rock (We Salute You)	1	1	1	Angus Young, Malcolm Young, Brian Johnson	343719	11170334	0.99
2	Balls to the Wall	2	2	1	U. Dirkschneider, W. Hoffmann, H. Frank, P. Baltes, S. Kaufmann, G. Hoffmann	342562	5510424	0.99
3	Fast As a Shark	3	2	1	F. Baltes, S. Kaufman, U. Dirkscneider & W. Hoffman	230619	3990994	0.99
*/
================================== Ai Message ==================================
Tool Calls:
  sql_db_query_checker (call_G64yYm6R6UauiVPCXJZMA49b)
 Call ID: call_G64yYm6R6UauiVPCXJZMA49b
  Args:
    query: SELECT Genre.Name, AVG(Track.Milliseconds) AS AverageLength FROM Track INNER JOIN Genre ON Track.GenreId = Genre.GenreId GROUP BY Genre.Name ORDER BY AverageLength DESC LIMIT 5;
================================= Tool Message =================================
Name: sql_db_query_checker

SELECT Genre.Name, AVG(Track.Milliseconds) AS AverageLength FROM Track INNER JOIN Genre ON Track.GenreId = Genre.GenreId GROUP BY Genre.Name ORDER BY AverageLength DESC LIMIT 5;
================================== Ai Message ==================================
Tool Calls:
  sql_db_query (call_AnO3SrhD0ODJBxh6dHMwvHwZ)
 Call ID: call_AnO3SrhD0ODJBxh6dHMwvHwZ
  Args:
    query: SELECT Genre.Name, AVG(Track.Milliseconds) AS AverageLength FROM Track INNER JOIN Genre ON Track.GenreId = Genre.GenreId GROUP BY Genre.Name ORDER BY AverageLength DESC LIMIT 5;
================================= Tool Message =================================
Name: sql_db_query

[('Sci Fi & Fantasy', 2911783.0384615385), ('Science Fiction', 2625549.076923077), ('Drama', 2575283.78125), ('TV Shows', 2145041.0215053763), ('Comedy', 1585263.705882353)]
================================== Ai Message ==================================

On average, the genre with the longest tracks is "Sci Fi & Fantasy" with an average track length of approximately 2,911,783 milliseconds. This is followed by "Science Fiction," "Drama," "TV Shows," and "Comedy."
```
代理正确地编写了一个查询，检查了该查询，然后运行它以告知其最终响应。

> [!note]
您可以检查上述运行的各个方面，包括采取的步骤、调用的工具、LLM 看到的提示以及 [LangSmith 跟踪](https://smith.langchain.com/public/cd2ce887-388a-4bb1-a29d-48208ce50d15/r) 中的更多信息。

### （可选）使用 Studio

[Studio](https://docs.langchain.com/langsmith/studio) 提供“客户端”循环和内存，因此您可以将其作为聊天界面运行并查询数据库。您可以提出诸如“告诉我数据库 schema”或“显示前 5 位客户的发票”之类的问题。您将看到生成的 SQL 命令和结果输出。下面详细介绍了如何开始。

### 在 Studio 中运行您的代理
除了前面提到的包之外，您还需要：
```shell
# 安装依赖：先把示例需要的包安装到当前 Python 环境。
pip install -U langgraph-cli[inmem]>=0.4.0
```
在您将运行的目录中，您将需要一个包含以下内容的 `langgraph.json` 文件：
```json
{
  "dependencies": ["."],
  "graphs": {
      "agent": "./sql_agent.py:agent",
      "graph": "./sql_agent_langgraph.py:graph"
  },
  "env": ".env"
}
```
创建一个文件 `sql_agent.py` 并插入以下内容：
```python
# 供 Studio 使用的 sql_agent.py。
import pathlib

from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_community.utilities import SQLDatabase
import requests

# 初始化 LLM。
model = init_chat_model("gpt-5.4")

# 下载数据库并保存到本地。
url = "https://storage.googleapis.com/benchmarks-artifacts/chinook/Chinook.db"
local_path = pathlib.Path("Chinook.db")

if local_path.exists():
    print(f"{local_path} already exists, skipping download.")
else:
    response = requests.get(url)
    if response.status_code == 200:
        local_path.write_bytes(response.content)
        print(f"File downloaded and saved as {local_path}")
    else:
        print(f"Failed to download the file. Status code: {response.status_code}")

# SQLDatabase 连接示例数据库，后续 SQL agent 会通过 tools 查看 schema 并执行查询。
db = SQLDatabase.from_uri("sqlite:///Chinook.db")

# 创建 tools。
toolkit = SQLDatabaseToolkit(db=db, llm=model)

tools = toolkit.get_tools()

for tool in tools:
    print(f"{tool.name}: {tool.description}\n")

# 使用 create_agent 创建 agent。
system_prompt = """
You are an agent designed to interact with a SQL database.
Given an input question, create a syntactically correct {dialect} query to run,
then look at the results of the query and return the answer. Unless the user
specifies a specific number of examples they wish to obtain, always limit your
query to at most {top_k} results.

You can order the results by a relevant column to return the most interesting
examples in the database. Never query for all the columns from a specific table,
only ask for the relevant columns given the question.

You MUST double check your query before executing it. If you get an error while
executing a query, rewrite the query and try again.

DO NOT make any DML statements (INSERT, UPDATE, DELETE, DROP etc.) to the
database.

To start you should ALWAYS look at the tables in the database to see what you
can query. Do NOT skip this step.

Then you should query the schema of the most relevant tables.
""".format(
    dialect=db.dialect,
    top_k=5,
)

# create_agent 会把模型、tools、系统提示词和 middleware 组装成一个可运行的 agent。
agent = create_agent(
    model,
    tools,
    system_prompt=system_prompt,
)
```
## 6. 实施人在回路审核

在执行代理的 SQL 查询之前检查是否存在任何意外操作或效率低下，这可能是谨慎的做法。

LangChain代理支持内置的[人在回路中间件](https://docs.langchain.com/oss/python/langchain/human-in-the-loop)，以增加对代理工具调用的监督。让我们将代理配置为在调用 `sql_db_query` 工具时暂停以供人工审核：
```python
from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware # [!code highlight]
from langgraph.checkpoint.memory import InMemorySaver # [!code highlight]

# create_agent 会把模型、tools、系统提示词和 middleware 组装成一个可运行的 agent。
agent = create_agent(
    model,
    tools,
    system_prompt=system_prompt,
    middleware=[ # [!code highlight]
        # HumanInTheLoopMiddleware 会在敏感 tool 执行前暂停，让人类审批后再继续。
        HumanInTheLoopMiddleware( # [!code highlight]
            interrupt_on={"sql_db_query": True}, # [!code highlight]
            description_prefix="Tool execution pending approval", # [!code highlight]
        ), # [!code highlight]
    ], # [!code highlight]
    # checkpointer 保存线程内的执行状态，用于多轮对话、暂停恢复和 human-in-the-loop。
    checkpointer=InMemorySaver(), # [!code highlight]
)
```
> [!note]
我们向代理添加了一个 [checkpointer](https://docs.langchain.com/oss/python/langchain/short-term-memory)，以允许暂停和恢复执行。有关此内容以及可用中间件配置的详细信息，请参阅[人在回路指南](https://docs.langchain.com/oss/python/langchain/human-in-the-loop)。

在运行代理时，它现在将在执行 `sql_db_query` 工具之前暂停以进行审查：
```python
question = "Which genre on average has the longest tracks?"
config = {"configurable": {"thread_id": "1"}} # [!code highlight]

# 这里是实际运行入口：传入 messages 或 state 后，系统会执行推理、工具调用和状态更新。
for step in agent.stream(
    {"messages": [{"role": "user", "content": question}]},
    config, # [!code highlight]
    stream_mode="values",
):
    if "__interrupt__" in step: # [!code highlight]
        print("INTERRUPTED:") # [!code highlight]
        interrupt = step["__interrupt__"][0] # [!code highlight]
        for request in interrupt.value["action_requests"]: # [!code highlight]
            print(request["description"]) # [!code highlight]
    elif "messages" in step:
        step["messages"][-1].pretty_print()
    else:
        pass
```

```
...

INTERRUPTED:
Tool execution pending approval

Tool: sql_db_query
Args: {'query': 'SELECT g.Name AS Genre, AVG(t.Milliseconds) AS AvgTrackLength FROM Track t JOIN Genre g ON t.GenreId = g.GenreId GROUP BY g.Name ORDER BY AvgTrackLength DESC LIMIT 1;'}
```
我们可以使用 [Command](https://docs.langchain.com/oss/python/langgraph/use-graph-api#combine-control-flow-and-state-updates-with-command) 恢复执行，在本例中接受查询：
```python
from langgraph.types import Command # [!code highlight]

# 这里是实际运行入口：传入 messages 或 state 后，系统会执行推理、工具调用和状态更新。
for step in agent.stream(
    # Command 可以同时表达 state 更新和下一步跳转，适合工具返回后改变流程的场景。
    Command(resume={"decisions": [{"type": "approve"}]}), # [!code highlight]
    config,
    stream_mode="values",
):
    if "messages" in step:
        step["messages"][-1].pretty_print()
    if "__interrupt__" in step:
        print("INTERRUPTED:")
        interrupt = step["__interrupt__"][0]
        for request in interrupt.value["action_requests"]:
            print(request["description"])
    else:
        pass
```

```
================================== Ai Message ==================================
Tool Calls:
  sql_db_query (call_7oz86Epg7lYRqi9rQHbZPS1U)
 Call ID: call_7oz86Epg7lYRqi9rQHbZPS1U
  Args:
    query: SELECT Genre.Name, AVG(Track.Milliseconds) AS AvgDuration FROM Track JOIN Genre ON Track.GenreId = Genre.GenreId GROUP BY Genre.Name ORDER BY AvgDuration DESC LIMIT 5;
================================= Tool Message =================================
Name: sql_db_query

[('Sci Fi & Fantasy', 2911783.0384615385), ('Science Fiction', 2625549.076923077), ('Drama', 2575283.78125), ('TV Shows', 2145041.0215053763), ('Comedy', 1585263.705882353)]
================================== Ai Message ==================================

The genre with the longest average track length is "Sci Fi & Fantasy" with an average duration of about 2,911,783 milliseconds, followed by "Science Fiction" and "Drama."
```
有关详细信息，请参阅[人在回路指南](https://docs.langchain.com/oss/python/langchain/human-in-the-loop)。

## 后续步骤

如需更深入的自定义，请查看[[02-Custom SQL Agent|本教程]]，以直接使用 LangGraph 原语实现 SQL 代理。
