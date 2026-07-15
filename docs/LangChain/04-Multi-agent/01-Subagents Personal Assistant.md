---
title: Subagents：个人助手
aliases:
  - Subagents: Personal Assistant
  - Subagents：个人助手
source: https://docs.langchain.com/oss/python/langchain/multi-agent/subagents-personal-assistant
source_md: https://docs.langchain.com/oss/python/langchain/multi-agent/subagents-personal-assistant.md
retrieved: 2026-05-07
tags:
  - langchain
  - python
  - docs/learn
license: MIT
---

# Subagents：个人助手

## 概述

**supervisor 模式**是一种[多代理](https://docs.langchain.com/oss/python/langchain/multi-agent) 架构，其中中央 supervisor 代理协调专门的工作代理。当任务需要不同类型的专业知识时，这种方法非常有用。您无需构建一个跨域管理工具选择的代理，而是创建由了解整体工作流的主管协调的专注专家。

在本教程中，您将构建一个个人助理系统，通过实际的工作流展示这些好处。该系统将协调两名职责截然不同的专家：

* **日历代理**，处理日程安排、可用性检查和事件管理。
* **电子邮件代理**，用于管理通信、起草消息和发送通知。

我们还将纳入[人在回路审核](https://docs.langchain.com/oss/python/langchain/human-in-the-loop)，以允许用户根据需要批准、编辑和拒绝操作（例如出站电子邮件）。

### 为什么要使用主管？

多代理架构允许您在工作人员之间划分[工具](https://docs.langchain.com/oss/python/langchain/tools)，每个工作人员都有自己的提示或说明。考虑一个可以直接访问所有日历和电子邮件 API 的代理：它必须从许多类似的工具中进行选择，了解每个 API 的确切格式，并同时处理多个域。如果性能下降，将相关工具和关联提示分成逻辑组可能会有所帮助（部分是为了管理迭代改进）。

### 概念

我们将涵盖以下概念：

* [多智能体系统](https://docs.langchain.com/oss/python/langchain/multi-agent)
* [人在回路审核](https://docs.langchain.com/oss/python/langchain/human-in-the-loop)

## 设置

### 安装

本教程需要 `langchain` 包：
```bash
# 安装依赖：先把示例需要的包安装到当前 Python 环境。
pip install langchain
```

```bash
conda install langchain -c conda-forge
```
有关更多详细信息，请参阅[安装指南](https://docs.langchain.com/oss/python/langchain/install)。

### LangSmith

设置 [LangSmith](https://smith.langchain.com?utm_source=docs\&utm_medium=cta\&utm_campaign=langsmith-signup\&utm_content=oss-langchain-multi-agent-subagents-personal-assistant) 来检查代理内部发生的情况。然后设置以下环境变量：
```bash
# 配置环境变量：示例会从环境变量读取 API key、模型名或服务地址。
export LANGSMITH_TRACING="true"
export LANGSMITH_API_KEY="..."
```

```python
import getpass
import os

os.environ["LANGSMITH_TRACING"] = "true"
os.environ["LANGSMITH_API_KEY"] = getpass.getpass()
```
### 成分

我们需要从 LangChain 的集成套件中选择一个聊天模型：

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
## 1. 定义工具

首先定义需要结构化输入的工具。在实际应用程序中，这些将调用实际的 API（Google Calendar、SendGrid 等）。在本教程中，您将使用存根来演示该模式。
```python
from langchain.tools import tool

# 使用 @tool 可以把普通 Python 函数暴露给 agent，模型会根据函数名、参数和 docstring 判断何时调用。
@tool
def create_calendar_event(
    title: str,
    start_time: str,       # ISO 格式："2024-01-15T14:00:00"。
    end_time: str,         # ISO 格式："2024-01-15T15:00:00"。
    attendees: list[str],  # 邮箱地址。
    location: str = ""
) -> str:
    """Create a calendar event. Requires exact ISO datetime format."""
    # 占位实现：真实系统中这里会调用 Google Calendar API、Outlook API 等。
    return f"Event created: {title} from {start_time} to {end_time} with {len(attendees)} attendees"

@tool
def send_email(
    to: list[str],  # 邮箱地址。
    subject: str,
    body: str,
    cc: list[str] = []
) -> str:
    """Send an email via email API. Requires properly formatted addresses."""
    # 占位实现：真实系统中这里会调用 SendGrid、Gmail API 等。
    return f"Email sent to {', '.join(to)} - Subject: {subject}"

@tool
def get_available_time_slots(
    attendees: list[str],
    date: str,  # ISO 格式："2024-01-15"。
    duration_minutes: int
) -> list[str]:
    """Check calendar availability for given attendees on a specific date."""
    # 占位实现：真实系统中这里会查询日历 API。
    return ["09:00", "14:00", "16:00"]
```
## 2. 创建专门的子代理

接下来，我们将创建处理每个域的专门子代理。

### 创建日历代理

日历代理理解自然语言调度请求并将其转换为精确的 API 调用。它处理日期解析、可用性检查和事件创建。
```python
from langchain.agents import create_agent

CALENDAR_AGENT_PROMPT = (
    "You are a calendar scheduling assistant. "
    "Parse natural language scheduling requests (e.g., 'next Tuesday at 2pm') "
    "into proper ISO datetime formats. "
    "Use get_available_time_slots to check availability when needed. "
    "If there is no suitable time slot, stop and confirm unavailability in your response. "
    "Use create_calendar_event to schedule events. "
    "Always confirm what was scheduled in your final response."
)

# create_agent 会把模型、tools、系统提示词和 middleware 组装成一个可运行的 agent。
calendar_agent = create_agent(
    model,
    tools=[create_calendar_event, get_available_time_slots],
    system_prompt=CALENDAR_AGENT_PROMPT,
)
```
测试日历代理以查看它如何处理自然语言调度：
```python
query = "Schedule a team meeting next Tuesday at 2pm for 1 hour"

for step in calendar_agent.stream(
    {"messages": [{"role": "user", "content": query}]}
):
    for update in step.values():
        for message in update.get("messages", []):
            message.pretty_print()
```

```
================================== Ai Message ==================================
Tool Calls:
  get_available_time_slots (call_EIeoeIi1hE2VmwZSfHStGmXp)
 Call ID: call_EIeoeIi1hE2VmwZSfHStGmXp
  Args:
    attendees: []
    date: 2024-06-18
    duration_minutes: 60
================================= Tool Message =================================
Name: get_available_time_slots

["09:00", "14:00", "16:00"]
================================== Ai Message ==================================
Tool Calls:
  create_calendar_event (call_zgx3iJA66Ut0W8S3NpT93kEB)
 Call ID: call_zgx3iJA66Ut0W8S3NpT93kEB
  Args:
    title: Team Meeting
    start_time: 2024-06-18T14:00:00
    end_time: 2024-06-18T15:00:00
    attendees: []
================================= Tool Message =================================
Name: create_calendar_event

Event created: Team Meeting from 2024-06-18T14:00:00 to 2024-06-18T15:00:00 with 0 attendees
================================== Ai Message ==================================

The team meeting has been scheduled for next Tuesday, June 18th, at 2:00 PM and will last for 1 hour. If you need to add attendees or a location, please let me know!
```
代理将“下周二下午 2 点”解析为 ISO 格式（“2024-01-16T14:00:00”），计算结束时间，调用 `create_calendar_event`，并返回自然语言确认。

### 创建电子邮件代理

电子邮件代理处理消息撰写和发送。它侧重于提取收件人信息、制作适当的主题行和正文以及管理电子邮件通信。
```python
EMAIL_AGENT_PROMPT = (
    "You are an email assistant. "
    "Compose professional emails based on natural language requests. "
    "Extract recipient information and craft appropriate subject lines and body text. "
    "Use send_email to send the message. "
    "Always confirm what was sent in your final response."
)

# create_agent 会把模型、tools、系统提示词和 middleware 组装成一个可运行的 agent。
email_agent = create_agent(
    model,
    tools=[send_email],
    system_prompt=EMAIL_AGENT_PROMPT,
)
```
使用自然语言请求测试电子邮件代理：
```python
query = "Send the design team a reminder about reviewing the new mockups"

for step in email_agent.stream(
    {"messages": [{"role": "user", "content": query}]}
):
    for update in step.values():
        for message in update.get("messages", []):
            message.pretty_print()
```

```
================================== Ai Message ==================================
Tool Calls:
  send_email (call_OMl51FziTVY6CRZvzYfjYOZr)
 Call ID: call_OMl51FziTVY6CRZvzYfjYOZr
  Args:
    to: ['design-team@example.com']
    subject: Reminder: Please Review the New Mockups
    body: Hi Design Team,

This is a friendly reminder to review the new mockups at your earliest convenience. Your feedback is important to ensure that we stay on track with our project timeline.

Please let me know if you have any questions or need additional information.

Thank you!

Best regards,
================================= Tool Message =================================
Name: send_email

Email sent to design-team@example.com - Subject: Reminder: Please Review the New Mockups
================================== Ai Message ==================================

I've sent a reminder to the design team asking them to review the new mockups. If you need any further communication on this topic, just let me know!
```
代理根据非正式请求推断收件人，制作专业的主题行和正文，致电 `send_email`，并返回确认。每个子代理都有一个特定领域的工具和提示，使其能够在特定任务中表现出色。

## 3. 将子代理包装为工具

现在将每个子代理包装为 supervisor可以调用的工具。这是创建分层系统的关键架构步骤。主管将看到“schedule\_event”等高级工具，而不是“create\_calendar\_event”等低级工具。
```python
# 使用 @tool 可以把普通 Python 函数暴露给 agent，模型会根据函数名、参数和 docstring 判断何时调用。
@tool
def schedule_event(request: str) -> str:
    """Schedule calendar events using natural language.

    Use this when the user wants to create, modify, or check calendar appointments.
    Handles date/time parsing, availability checking, and event creation.

    Input: Natural language scheduling request (e.g., 'meeting with design team
    next Tuesday at 2pm')
    """
    result = calendar_agent.invoke({
        "messages": [{"role": "user", "content": request}]
    })
    return result["messages"][-1].text

@tool
def manage_email(request: str) -> str:
    """Send emails using natural language.

    Use this when the user wants to send notifications, reminders, or any email
    communication. Handles recipient extraction, subject generation, and email
    composition.

    Input: Natural language email request (e.g., 'send them a reminder about
    the meeting')
    """
    result = email_agent.invoke({
        "messages": [{"role": "user", "content": request}]
    })
    return result["messages"][-1].text
```
工具描述可以帮助主管决定何时使用每种工具，因此要使其清晰具体。我们仅返回子代理的最终响应，因为 supervisor不需要查看中间推理或工具调用。

## 4.创建 supervisor 代理

现在创建协调子代理的主管。主管只能看到高级工具并在域级别（而不是单个 API 级别）做出路由决策。
```python
SUPERVISOR_PROMPT = (
    "You are a helpful personal assistant. "
    "You can schedule calendar events and send emails. "
    "Break down user requests into appropriate tool calls and coordinate the results. "
    "When a request involves multiple actions, use multiple tools in sequence."
)

# create_agent 会把模型、tools、系统提示词和 middleware 组装成一个可运行的 agent。
supervisor_agent = create_agent(
    model,
    tools=[schedule_event, manage_email],
    system_prompt=SUPERVISOR_PROMPT,
)
```
## 5. 使用主管

现在使用需要跨多个域协调的复杂请求来测试您的整个系统：

### 示例1：简单的单域请求
```python
query = "Schedule a team standup for tomorrow at 9am"

for step in supervisor_agent.stream(
    {"messages": [{"role": "user", "content": query}]}
):
    for update in step.values():
        for message in update.get("messages", []):
            message.pretty_print()
```

```
================================== Ai Message ==================================
Tool Calls:
  schedule_event (call_mXFJJDU8bKZadNUZPaag8Lct)
 Call ID: call_mXFJJDU8bKZadNUZPaag8Lct
  Args:
    request: Schedule a team standup for tomorrow at 9am with Alice and Bob.
================================= Tool Message =================================
Name: schedule_event

The team standup has been scheduled for tomorrow at 9:00 AM with Alice and Bob. If you need to make any changes or add more details, just let me know!
================================== Ai Message ==================================

The team standup with Alice and Bob is scheduled for tomorrow at 9:00 AM. If you need any further arrangements or adjustments, please let me know!
```
主管将此识别为日历任务，调用 `schedule_event`，日历代理处理日期解析和事件创建。

> [!tip]
要完全了解信息流（包括每个聊天模型调用的提示和响应），请查看上述运行的 [LangSmith 跟踪](https://smith.langchain.com/public/91a9a95f-fba9-4e84-aff0-371861ad2f4a/r)。

### 示例2：复杂的多域请求
```python
query = (
    "Schedule a meeting with the design team next Tuesday at 2pm for 1 hour, "
    "and send them an email reminder about reviewing the new mockups."
)

for step in supervisor_agent.stream(
    {"messages": [{"role": "user", "content": query}]}
):
    for update in step.values():
        for message in update.get("messages", []):
            message.pretty_print()
```

```
================================== Ai Message ==================================
Tool Calls:
  schedule_event (call_YA68mqF0koZItCFPx0kGQfZi)
 Call ID: call_YA68mqF0koZItCFPx0kGQfZi
  Args:
    request: meeting with the design team next Tuesday at 2pm for 1 hour
  manage_email (call_XxqcJBvVIuKuRK794ZIzlLxx)
 Call ID: call_XxqcJBvVIuKuRK794ZIzlLxx
  Args:
    request: send the design team an email reminder about reviewing the new mockups
================================= Tool Message =================================
Name: schedule_event

Your meeting with the design team is scheduled for next Tuesday, June 18th, from 2:00pm to 3:00pm. Let me know if you need to add more details or make any changes!
================================= Tool Message =================================
Name: manage_email

I've sent an email reminder to the design team requesting them to review the new mockups. If you need to include more information or recipients, just let me know!
================================== Ai Message ==================================

Your meeting with the design team is scheduled for next Tuesday, June 18th, from 2:00pm to 3:00pm.

I've also sent an email reminder to the design team, asking them to review the new mockups.

Let me know if you'd like to add more details to the meeting or include additional information in the email!
```
主管认识到这需要日历和电子邮件操作，致电 `schedule_event` 参加会议，然后致电 `manage_email` 进行提醒。每个子代理完成其任务，主管将两个结果合成为连贯的响应。

> [!tip]
参考 [LangSmith Trace](https://smith.langchain.com/public/95cd00a3-d1f9-4dba-9731-7bf733fb6a3c/r) 查看上述运行的详细信息流程，包括各个聊天模型的提示和响应。

### 完整的工作示例

以下是可运行脚本中的所有内容：

### 查看完整代码
```python
"""
Personal Assistant Supervisor Example

This example demonstrates the tool calling pattern for multi-agent systems.
A supervisor agent coordinates specialized sub-agents (calendar and email)
that are wrapped as tools.
"""

from langchain.tools import tool
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model

# ============================================================================
# 步骤 1：定义底层 API tools（这里用 stub 模拟）。
# ============================================================================

# 使用 @tool 可以把普通 Python 函数暴露给 agent，模型会根据函数名、参数和 docstring 判断何时调用。
@tool
def create_calendar_event(
    title: str,
    start_time: str,  # ISO 格式："2024-01-15T14:00:00"。
    end_time: str,    # ISO 格式："2024-01-15T15:00:00"。
    attendees: list[str],  # 邮箱地址。
    location: str = ""
) -> str:
    """Create a calendar event. Requires exact ISO datetime format."""
    return f"Event created: {title} from {start_time} to {end_time} with {len(attendees)} attendees"

@tool
def send_email(
    to: list[str],      # 邮箱地址。
    subject: str,
    body: str,
    cc: list[str] = []
) -> str:
    """Send an email via email API. Requires properly formatted addresses."""
    return f"Email sent to {', '.join(to)} - Subject: {subject}"

@tool
def get_available_time_slots(
    attendees: list[str],
    date: str,  # ISO 格式："2024-01-15"。
    duration_minutes: int
) -> list[str]:
    """Check calendar availability for given attendees on a specific date."""
    return ["09:00", "14:00", "16:00"]

# ============================================================================
# 步骤 2：创建专门负责不同任务的 sub-agents。
# ============================================================================

# 初始化 chat model：后续 agent、chain 或 graph 都会通过这个模型向 LLM 发请求。
model = init_chat_model("gpt-5.4")  # 这里选择 supervisor 和子 agent 共用的聊天模型。

# create_agent 会把模型、tools、系统提示词和 middleware 组装成一个可运行的 agent。
calendar_agent = create_agent(
    model,
    tools=[create_calendar_event, get_available_time_slots],
    system_prompt=(
        "You are a calendar scheduling assistant. "
        "Parse natural language scheduling requests (e.g., 'next Tuesday at 2pm') "
        "into proper ISO datetime formats. "
        "Use get_available_time_slots to check availability when needed. "
        "If there is no suitable time slot, stop and confirm unavailability in your response. "
        "Use create_calendar_event to schedule events. "
        "Always confirm what was scheduled in your final response."
    )
)

email_agent = create_agent(
    model,
    tools=[send_email],
    system_prompt=(
        "You are an email assistant. "
        "Compose professional emails based on natural language requests. "
        "Extract recipient information and craft appropriate subject lines and body text. "
        "Use send_email to send the message. "
        "Always confirm what was sent in your final response."
    )
)

# ============================================================================
# 步骤 3：把 sub-agents 包装成 supervisor 可以调用的 tools。
# ============================================================================

@tool
def schedule_event(request: str) -> str:
    """Schedule calendar events using natural language.

    Use this when the user wants to create, modify, or check calendar appointments.
    Handles date/time parsing, availability checking, and event creation.

    Input: Natural language scheduling request (e.g., 'meeting with design team
    next Tuesday at 2pm')
    """
    result = calendar_agent.invoke({
        "messages": [{"role": "user", "content": request}]
    })
    return result["messages"][-1].text

@tool
def manage_email(request: str) -> str:
    """Send emails using natural language.

    Use this when the user wants to send notifications, reminders, or any email
    communication. Handles recipient extraction, subject generation, and email
    composition.

    Input: Natural language email request (e.g., 'send them a reminder about
    the meeting')
    """
    result = email_agent.invoke({
        "messages": [{"role": "user", "content": request}]
    })
    return result["messages"][-1].text

# ============================================================================
# 步骤 4：创建 supervisor agent。
# ============================================================================

supervisor_agent = create_agent(
    model,
    tools=[schedule_event, manage_email],
    system_prompt=(
        "You are a helpful personal assistant. "
        "You can schedule calendar events and send emails. "
        "Break down user requests into appropriate tool calls and coordinate the results. "
        "When a request involves multiple actions, use multiple tools in sequence."
    )
)

# ============================================================================
# 步骤 5：调用 supervisor。
# ============================================================================

if __name__ == "__main__":
    # 示例：用户请求同时需要日历和邮件协作。
    user_request = (
        "Schedule a meeting with the design team next Tuesday at 2pm for 1 hour, "
        "and send them an email reminder about reviewing the new mockups."
    )

    print("User Request:", user_request)
    print("\n" + "="*80 + "\n")

    for step in supervisor_agent.stream(
        {"messages": [{"role": "user", "content": user_request}]}
    ):
        for update in step.values():
            for message in update.get("messages", []):
                message.pretty_print()
```
### 了解架构

您的系统有三层。底层包含需要精确格式的严格 API 工具。中间层包含接受自然语言、将其转换为结构化 API 调用并返回自然语言确认的子代理。顶层包含管理器，用于路由到高级功能并综合结果。

这种关注点分离提供了几个好处：每个层都有一个集中的职责，您可以添加新域而不影响现有域，并且可以独立测试和迭代每个层。

## 6.添加人工参与审核

谨慎的做法是对敏感行为进行[人在回路审查](https://docs.langchain.com/oss/python/langchain/human-in-the-loop)。 LangChain包含[内置中间件](https://docs.langchain.com/oss/python/langchain/human-in-the-loop#configuring-interrupts)来审查工具调用，在本例中是子代理调用的工具。

让我们为两个子代理添加人在回路审核：

* 我们将 `create_calendar_event` 和 `send_email` 工具配置为中断，允许所有[响应类型](https://docs.langchain.com/oss/python/langchain/human-in-the-loop) (`approve`, `edit`, `reject`)
* 我们添加一个 [checkpointer](https://docs.langchain.com/oss/python/langchain/short-term-memory) **仅到顶级代理**。这是暂停和恢复执行所必需的。
```python
from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware # [!code highlight]
from langgraph.checkpoint.memory import InMemorySaver # [!code highlight]

# create_agent 会把模型、tools、系统提示词和 middleware 组装成一个可运行的 agent。
calendar_agent = create_agent(
    model,
    tools=[create_calendar_event, get_available_time_slots],
    system_prompt=CALENDAR_AGENT_PROMPT,
    middleware=[ # [!code highlight]
        # HumanInTheLoopMiddleware 会在敏感 tool 执行前暂停，让人类审批后再继续。
        HumanInTheLoopMiddleware( # [!code highlight]
            interrupt_on={"create_calendar_event": True}, # [!code highlight]
            description_prefix="Calendar event pending approval", # [!code highlight]
        ), # [!code highlight]
    ], # [!code highlight]
)

email_agent = create_agent(
    model,
    tools=[send_email],
    system_prompt=EMAIL_AGENT_PROMPT,
    middleware=[ # [!code highlight]
        HumanInTheLoopMiddleware( # [!code highlight]
            interrupt_on={"send_email": True}, # [!code highlight]
            description_prefix="Outbound email pending approval", # [!code highlight]
        ), # [!code highlight]
    ], # [!code highlight]
)

supervisor_agent = create_agent(
    model,
    tools=[schedule_event, manage_email],
    system_prompt=SUPERVISOR_PROMPT,
    # checkpointer 保存线程内的执行状态，用于多轮对话、暂停恢复和 human-in-the-loop。
    checkpointer=InMemorySaver(), # [!code highlight]
)
```
让我们重复一下查询。请注意，我们将中断事件收集到一个列表中以访问下游：
```python
query = (
    "Schedule a meeting with the design team next Tuesday at 2pm for 1 hour, "
    "and send them an email reminder about reviewing the new mockups."
)

config = {"configurable": {"thread_id": "6"}}

interrupts = []
for step in supervisor_agent.stream(
    {"messages": [{"role": "user", "content": query}]},
    config,
):
    for update in step.values():
        if isinstance(update, dict):
            for message in update.get("messages", []):
                message.pretty_print()
        else:
            interrupt_ = update[0]
            interrupts.append(interrupt_)
            print(f"\nINTERRUPTED: {interrupt_.id}")
```

```
================================== Ai Message ==================================
Tool Calls:
  schedule_event (call_t4Wyn32ohaShpEZKuzZbl83z)
 Call ID: call_t4Wyn32ohaShpEZKuzZbl83z
  Args:
    request: Schedule a meeting with the design team next Tuesday at 2pm for 1 hour.
  manage_email (call_JWj4vDJ5VMnvkySymhCBm4IR)
 Call ID: call_JWj4vDJ5VMnvkySymhCBm4IR
  Args:
    request: Send an email reminder to the design team about reviewing the new mockups before our meeting next Tuesday at 2pm.

INTERRUPTED: 4f994c9721682a292af303ec1a46abb7

INTERRUPTED: 2b56f299be313ad8bc689eff02973f16
```
这次我们中断了执行。让我们检查一下中断事件：
```python
for interrupt_ in interrupts:
    for request in interrupt_.value["action_requests"]:
        print(f"INTERRUPTED: {interrupt_.id}")
        print(f"{request['description']}\n")
```

```
INTERRUPTED: 4f994c9721682a292af303ec1a46abb7
Calendar event pending approval

Tool: create_calendar_event
Args: {'title': 'Meeting with the Design Team', 'start_time': '2024-06-18T14:00:00', 'end_time': '2024-06-18T15:00:00', 'attendees': ['design team']}

INTERRUPTED: 2b56f299be313ad8bc689eff02973f16
Outbound email pending approval

Tool: send_email
Args: {'to': ['designteam@example.com'], 'subject': 'Reminder: Review New Mockups Before Meeting Next Tuesday at 2pm', 'body': "Hello Team,\n\nThis is a reminder to review the new mockups ahead of our meeting scheduled for next Tuesday at 2pm. Your feedback and insights will be valuable for our discussion and next steps.\n\nPlease ensure you've gone through the designs and are ready to share your thoughts during the meeting.\n\nThank you!\n\nBest regards,\n[Your Name]"}
```
我们可以通过使用 [`Command`](https://reference.langchain.com/python/langgraph/types/Command) 引用每个中断的 ID 来指定每个中断的决策。请参阅[人在回路指南](https://docs.langchain.com/oss/python/langchain/human-in-the-loop) 了解更多详细信息。出于演示目的，这里我们将接受日历事件，但编辑出站电子邮件的主题：
```python
from langgraph.types import Command # [!code highlight]

resume = {}
for interrupt_ in interrupts:
    if interrupt_.id == "2b56f299be313ad8bc689eff02973f16":
        # 编辑邮件。
        edited_action = interrupt_.value["action_requests"][0].copy()
        edited_action["args"]["subject"] = "Mockups reminder"
        resume[interrupt_.id] = {
            "decisions": [{"type": "edit", "edited_action": edited_action}]
        }
    else:
        resume[interrupt_.id] = {"decisions": [{"type": "approve"}]}

interrupts = []
for step in supervisor_agent.stream(
    # Command 可以同时表达 state 更新和下一步跳转，适合工具返回后改变流程的场景。
    Command(resume=resume), # [!code highlight]
    config,
):
    for update in step.values():
        if isinstance(update, dict):
            for message in update.get("messages", []):
                message.pretty_print()
        else:
            interrupt_ = update[0]
            interrupts.append(interrupt_)
            print(f"\nINTERRUPTED: {interrupt_.id}")
```

```
================================= Tool Message =================================
Name: schedule_event

Your meeting with the design team has been scheduled for next Tuesday, June 18th, from 2:00 pm to 3:00 pm.
================================= Tool Message =================================
Name: manage_email

Your email reminder to the design team has been sent. Here’s what was sent:

- Recipient: designteam@example.com
- Subject: Mockups reminder
- Body: A reminder to review the new mockups before the meeting next Tuesday at 2pm, with a request for feedback and readiness for discussion.

Let me know if you need any further assistance!
================================== Ai Message ==================================

- Your meeting with the design team has been scheduled for next Tuesday, June 18th, from 2:00 pm to 3:00 pm.
- An email reminder has been sent to the design team about reviewing the new mockups before the meeting.

Let me know if you need any further assistance!
```
运行根据我们的输入继续进行。

## 7. 高级：控制信息流

默认情况下，子代理仅接收来自主管的请求字符串。您可能想要传递其他上下文，例如对话历史记录或用户首选项。

### 将额外的对话上下文传递给子代理
```python
from langchain.tools import tool, ToolRuntime

# 使用 @tool 可以把普通 Python 函数暴露给 agent，模型会根据函数名、参数和 docstring 判断何时调用。
@tool
def schedule_event(
    request: str,
    runtime: ToolRuntime
) -> str:
    """Schedule calendar events using natural language."""
    # 自定义 sub-agent 接收到的上下文。
    original_user_message = next(
        message for message in runtime.state["messages"]
        if message.type == "human"
    )
    prompt = (
        "You are assisting with the following user inquiry:\n\n"
        f"{original_user_message.text}\n\n"
        "You are tasked with the following sub-request:\n\n"
        f"{request}"
    )
    result = calendar_agent.invoke({
        "messages": [{"role": "user", "content": prompt}],
    })
    return result["messages"][-1].text
```
这允许子代理查看完整的对话上下文，这对于解决诸如“安排在明天同一时间”（引用之前的对话）之类的歧义非常有用。

> [!tip]
您可以在 LangSmith 跟踪的 [聊天模型调用](https://smith.langchain.com/public/c7d54882-afb8-4039-9c5a-4112d0f458b0/r/6803571e-af78-4c68-904a-ecf55771084d) 中看到子代理收到的完整上下文。

### 控制主管收到的内容

您还可以自定义流回主管的信息：
```python
import json

# 使用 @tool 可以把普通 Python 函数暴露给 agent，模型会根据函数名、参数和 docstring 判断何时调用。
@tool
def schedule_event(request: str) -> str:
    """Schedule calendar events using natural language."""
    result = calendar_agent.invoke({
        "messages": [{"role": "user", "content": request}]
    })

    # 选项 1：只返回确认消息。
    return result["messages"][-1].text

    # 选项 2：返回结构化数据。
    # 返回 JSON 字符串。
    #     示例字段：status 表示成功。
    #     示例字段：event_id。
    #     示例字段：summary 使用最后一条消息文本。
    # })
```
**重要提示：** 确保子代理提示强调其最终消息应包含所有相关信息。常见的故障模式是子代理执行工具调用但不将结果包含在其最终响应中。

## 8. 要点

supervisor 模式创建了抽象层，其中每一层都有明确的职责。设计 supervisor 系统时，从清晰的域边界开始，并为每个子代理提供重点工具和提示。为 supervisor 编写清晰的工具描述，在集成之前独立测试每一层，并根据您的具体需求控制信息流。

> [!tip]
**何时使用 supervisor 模式**

当您有多个不同的域（日历、电子邮件、CRM、数据库）、每个域有多个工具或复杂的逻辑、您需要集中式工作流控制并且子代理不需要直接与用户交谈时，请使用 supervisor 模式。

对于仅使用少量工具的简单情况，请使用单个代理。当代理需要与用户对话时，请使用 [handoffs](https://docs.langchain.com/oss/python/langchain/multi-agent/handoffs)。对于代理之间的点对点协作，请考虑其他多代理模式。

## 后续步骤

了解代理间对话的[交接](https://docs.langchain.com/oss/python/langchain/multi-agent/handoffs)，探索[上下文工程](https://docs.langchain.com/oss/python/langchain/context-engineering)以微调信息流，阅读[多代理概述](https://docs.langchain.com/oss/python/langchain/multi-agent)以比较不同的模式，并使用[LangSmith](https://smith.langchain.com?utm_source=docs\&utm_medium=cta\&utm_campaign=langsmith-signup\&utm_content=oss-langchain-multi-agent-subagents-personal-assistant)调试和监控您的多代理系统。
