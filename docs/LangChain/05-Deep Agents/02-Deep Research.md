---
title: 深度研究
aliases:
  - Deep Research
  - 深度研究
source: https://docs.langchain.com/oss/python/deepagents/deep-research
source_md: https://docs.langchain.com/oss/python/deepagents/deep-research.md
retrieved: 2026-05-07
tags:
  - langchain
  - python
  - docs/learn
license: MIT
---

# 深度研究

> 使用子代理委托构建多步骤网络研究代理

## 概述

本指南演示了如何使用 [Deep Agents](https://docs.langchain.com/oss/python/deepagents) 从头开始​​构建多步骤网络研究代理。该代理将研究问题分解为重点任务，将其委托给专门的子代理，并将研究结果综合成一份综合报告。

您构建的代理将：

1. 使用待办事项列表计划研究
2. 将重点研究任务委托给具有孤立上下文的子代理
3. 收集信息时评估搜索结果并计划后续步骤
4. 将研究结果与适当的引用综合成最终报告

生成的子代理将使用 Tavily 进行网络搜索，获取完整的网页内容进行分析。

### 关键概念

本教程涵盖：

* [子代理](https://docs.langchain.com/oss/python/deepagents/subagents) 用于并行、上下文隔离的研究
* 用于网络搜索的自定义[工具](https://docs.langchain.com/oss/python/langchain/tools)
* 使用[内置规划工具](https://docs.langchain.com/oss/python/deepagents/harness#planning-capabilities)进行多步骤规划

## 先决条件

API 密钥用于：

* Anthropic（Claude）或谷歌（Gemini）
* [Tavily](https://www.tavily.com/) 用于网络搜索（可选 - 免费套餐足够）
* [LangSmith](https://smith.langchain.com?utm_source=docs\&utm_medium=cta\&utm_campaign=langsmith-signup\&utm_content=oss-deepagents-deep-research) 用于跟踪（可选）

## 设置

### 创建项目目录
```bash
mkdir deep-research-agent
cd deep-research-agent
```
### 安装依赖项

#### 克洛德
```bash
# 安装依赖：先把示例需要的包安装到当前 Python 环境。
pip install deepagents tavily-python httpx markdownify langchain-anthropic langchain-core
```

```bash
uv init
# 安装依赖：先把示例需要的包安装到当前 Python 环境。
uv add deepagents tavily-python httpx markdownify langchain-anthropic langchain-core
uv sync
```
#### Gemini
```bash
# 安装依赖：先把示例需要的包安装到当前 Python 环境。
pip install deepagents tavily-python httpx markdownify langchain-google-genai langchain-core
```

```bash
uv init
# 安装依赖：先把示例需要的包安装到当前 Python 环境。
uv add deepagents tavily-python httpx markdownify langchain-google-genai langchain-core
uv sync
```
### 设置 API 密钥

#### 克洛德
```bash
# 配置环境变量：示例会从环境变量读取 API key、模型名或服务地址。
export ANTHROPIC_API_KEY="your_anthropic_api_key"
export TAVILY_API_KEY="your_tavily_api_key"
export LANGSMITH_API_KEY="your_langsmith_api_key"   # Optional
```
#### Gemini
```bash
# 配置环境变量：示例会从环境变量读取 API key、模型名或服务地址。
export GOOGLE_API_KEY="your_google_api_key"
export TAVILY_API_KEY="your_tavily_api_key"
export LANGSMITH_API_KEY="your_langsmith_api_key"   # Optional
```
## 构建代理

在项目目录中创建 `agent.py`：

### 添加工具
添加自定义搜索工具。 `tavily_search` 工具使用 Tavily 进行 URL 发现，然后获取完整的网页内容，以便代理可以分析完整的源而不是摘要。
```python
import os
from typing import Annotated, Literal

import httpx
from langchain.tools import InjectedToolArg, tool
from markdownify import markdownify
from tavily import TavilyClient

tavily_client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])

def fetch_webpage_content(url: str, timeout: float = 10.0) -> str:
    """Fetch webpage and convert HTML to markdown."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    try:
        response = httpx.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        return markdownify(response.text)
    except Exception as e:
        return f"Error fetching {url}: {e!s}"

# 使用 @tool 可以把普通 Python 函数暴露给 agent，模型会根据函数名、参数和 docstring 判断何时调用。
@tool(parse_docstring=True)
def tavily_search(
    query: str,
    max_results: Annotated[int, InjectedToolArg] = 1,
    topic: Annotated[
        Literal["general", "news", "finance"], InjectedToolArg
    ] = "general",
) -> str:
    """Search the web for information on a given query.

    Uses Tavily to discover relevant URLs, then fetches and returns full webpage content as markdown.

    Args:
        query: Search query to execute
        max_results: Maximum number of results to return (default: 1)
        topic: Topic filter - 'general', 'news', or 'finance' (default: 'general')

    Returns:
        Formatted search results with full webpage content
    """
    search_results = tavily_client.search(
        query,
        max_results=max_results,
        topic=topic,
    )
    result_texts = []
    for result in search_results.get("results", []):
        url = result["url"]
        title = result["title"]
        content = fetch_webpage_content(url)
        result_texts.append(f"## {title}\n**URL:** {url}\n\n{content}\n---")

    return f"Found {len(result_texts)} result(s) for '{query}':\n\n" + "\n".join(
        result_texts
    )
```
### 添加提示
将 Orchestrator 工作流和子代理提示模板添加到 `agent.py`：
```python
RESEARCH_WORKFLOW_INSTRUCTIONS = """# Research Workflow

Follow this workflow for all research requests:

1. **Plan**: Create a todo list with write_todos to break down the research into focused tasks
2. **Save the request**: Use write_file() to save the user's research question to `/research_request.md`
3. **Research**: Delegate research tasks to sub-agents using the task() tool - ALWAYS use sub-agents for research, never conduct research yourself
4. **Synthesize**: Review all sub-agent findings and consolidate citations (each unique URL gets one number across all findings)
5. **Write Report**: Write a comprehensive final report to `/final_report.md` (see Report Writing Guidelines below)
6. **Verify**: Read `/research_request.md` and confirm you've addressed all aspects with proper citations and structure

## Research Planning Guidelines
- Batch similar research tasks into a single TODO to minimize overhead
- For simple fact-finding questions, use 1 sub-agent
- For comparisons or multi-faceted topics, delegate to multiple parallel sub-agents
- Each sub-agent should research one specific aspect and return findings

## Report Writing Guidelines

When writing the final report to `/final_report.md`, follow these structure patterns:

**For comparisons:**
1. Introduction
2. Overview of topic A
3. Overview of topic B
4. Detailed comparison
5. Conclusion

**For lists/rankings:**
Simply list items with details - no introduction needed:
1. Item 1 with explanation
2. Item 2 with explanation
3. Item 3 with explanation

**For summaries/overviews:**
1. Overview of topic
2. Key concept 1
3. Key concept 2
4. Key concept 3
5. Conclusion

**General guidelines:**
- Use clear section headings (## for sections, ### for subsections)
- Write in paragraph form by default - be text-heavy, not just bullet points
- Do NOT use self-referential language ("I found...", "I researched...")
- Write as a professional report without meta-commentary
- Each section should be comprehensive and detailed
- Use bullet points only when listing is more appropriate than prose

**Citation format:**
- Cite sources inline using [1], [2], [3] format
- Assign each unique URL a single citation number across ALL sub-agent findings
- End report with ### Sources section listing each numbered source
- Number sources sequentially without gaps (1,2,3,4...)
- Format: [1] Source Title: URL (each on separate line for proper list rendering)
- Example:

 Some important finding [1]. Another key insight [2].

 ### Sources
 [1] AI Research Paper: https://example.com/paper
 [2] Industry Analysis: https://example.com/analysis
"""
```

```python
RESEARCHER_INSTRUCTIONS = """You are a research assistant conducting research on the user's input topic. For context, today's date is {date}.

Your job is to use tools to gather information about the user's input topic.
You can use the tavily_search tool to find resources that can help answer the research question.
You can call it in series or in parallel, your research is conducted in a tool-calling loop.

You have access to the tavily_search tool for conducting web searches.

Think like a human researcher with limited time. Follow these steps:

1. **Read the question carefully** - What specific information does the user need?
2. **Start with broader searches** - Use broad, comprehensive queries first
3. **After each search, pause and assess** - Do I have enough to answer? What's still missing?
4. **Execute narrower searches as you gather information** - Fill in the gaps
5. **Stop when you can answer confidently** - Don't keep searching for perfection

**Tool Call Budgets** (Prevent excessive searching):
- **Simple queries**: Use 2-3 search tool calls maximum
- **Complex queries**: Use up to 5 search tool calls maximum
- **Always stop**: After 5 search tool calls if you cannot find the right sources

**Stop Immediately When**:
- You can answer the user's question comprehensively
- You have 3+ relevant examples/sources for the question
- Your last 2 searches returned similar information

After each search, assess results before continuing: What key information did I find? What's missing? Do I have enough to answer? Should I search more or provide my answer?

When providing your findings back to the orchestrator:

1. **Structure your response**: Organize findings with clear headings and detailed explanations
2. **Cite sources inline**: Use [1], [2], [3] format when referencing information from your searches
3. **Include Sources section**: End with ### Sources listing each numbered source with title and URL

Example:
## Key Findings

Context engineering is a critical technique for AI agents [1]. Studies show that proper context management can improve performance by 40% [2].

### Sources
[1] Context Engineering Guide: https://example.com/context-guide
[2] AI Performance Study: https://example.com/study

The orchestrator will consolidate citations from all sub-agents into the final report.
"""
```

```python
SUBAGENT_DELEGATION_INSTRUCTIONS = """# Sub-Agent Research Coordination

Your role is to coordinate research by delegating tasks from your TODO list to specialized research sub-agents.

## Delegation Strategy

**DEFAULT: Start with 1 sub-agent** for most queries:
- "What is quantum computing?" -> 1 sub-agent (general overview)
- "List the top 10 coffee shops in San Francisco" -> 1 sub-agent
- "Summarize the history of the internet" -> 1 sub-agent
- "Research context engineering for AI agents" -> 1 sub-agent (covers all aspects)

**ONLY parallelize when the query EXPLICITLY requires comparison or has clearly independent aspects:**

**Explicit comparisons** -> 1 sub-agent per element:
- "Compare OpenAI vs Anthropic vs DeepMind AI safety approaches" -> 3 parallel sub-agents
- "Compare Python vs JavaScript for web development" -> 2 parallel sub-agents

**Clearly separated aspects** -> 1 sub-agent per aspect (use sparingly):
- "Research renewable energy adoption in Europe, Asia, and North America" -> 3 parallel sub-agents (geographic separation)
- Only use this pattern when aspects cannot be covered efficiently by a single comprehensive search

## Key Principles
- **Bias towards single sub-agent**: One comprehensive research task is more token-efficient than multiple narrow ones
- **Avoid premature decomposition**: Don't break "research X" into "research X overview", "research X techniques", "research X applications" - just use 1 sub-agent for all of X
- **Parallelize only for clear comparisons**: Use multiple sub-agents when comparing distinct entities or geographically separated data

## Parallel Execution Limits
- Use at most {max_concurrent_research_units} parallel sub-agents per iteration
- Make multiple task() calls in a single response to enable parallel execution
- Each sub-agent returns findings independently

## Research Limits
- Stop after {max_researcher_iterations} delegation rounds if you haven't found adequate sources
- Stop when you have sufficient information to answer comprehensively
- Bias towards focused research over exhaustive exploration"""
```
### 创建代理
将模型初始化和代理创建添加到 `agent.py`。选择您的提供商：

#### 克洛德
```python
from datetime import datetime

from deepagents import create_deep_agent
from langchain.chat_models import init_chat_model

max_concurrent_research_units = 3
max_researcher_iterations = 3

current_date = datetime.now().strftime("%Y-%m-%d")

INSTRUCTIONS = (
    RESEARCH_WORKFLOW_INSTRUCTIONS
    + "\n\n"
    + "=" * 80
    + "\n\n"
    + SUBAGENT_DELEGATION_INSTRUCTIONS.format(
        max_concurrent_research_units=max_concurrent_research_units,
        max_researcher_iterations=max_researcher_iterations,
    )
)

research_sub_agent = {
    "name": "research-agent",
    "description": "Delegate research to the sub-agent. Give one topic at a time.",
    "system_prompt": RESEARCHER_INSTRUCTIONS.format(date=current_date),
    "tools": [tavily_search],
}

# 初始化 chat model：后续 agent、chain 或 graph 都会通过这个模型向 LLM 发请求。
model = init_chat_model(model="google_genai:gemini-3.1-pro-preview", temperature=0.0)

# create_deep_agent 会创建具备规划、文件系统和 subagents 能力的 Deep Agent。
agent = create_deep_agent(
    model=model,
    tools=[tavily_search],
    system_prompt=INSTRUCTIONS,
    # subagents 用来把专门任务委托给独立提示词和工具集合，减轻主 agent 的负担。
    subagents=[research_sub_agent],
)
```

```python
from datetime import datetime

from deepagents import create_deep_agent
from langchain.chat_models import init_chat_model

max_concurrent_research_units = 3
max_researcher_iterations = 3

current_date = datetime.now().strftime("%Y-%m-%d")

INSTRUCTIONS = (
    RESEARCH_WORKFLOW_INSTRUCTIONS
    + "\n\n"
    + "=" * 80
    + "\n\n"
    + SUBAGENT_DELEGATION_INSTRUCTIONS.format(
        max_concurrent_research_units=max_concurrent_research_units,
        max_researcher_iterations=max_researcher_iterations,
    )
)

research_sub_agent = {
    "name": "research-agent",
    "description": "Delegate research to the sub-agent. Give one topic at a time.",
    "system_prompt": RESEARCHER_INSTRUCTIONS.format(date=current_date),
    "tools": [tavily_search],
}

# 初始化 chat model：后续 agent、chain 或 graph 都会通过这个模型向 LLM 发请求。
model = init_chat_model(model="openai:gpt-5.4", temperature=0.0)

# create_deep_agent 会创建具备规划、文件系统和 subagents 能力的 Deep Agent。
agent = create_deep_agent(
    model=model,
    tools=[tavily_search],
    system_prompt=INSTRUCTIONS,
    # subagents 用来把专门任务委托给独立提示词和工具集合，减轻主 agent 的负担。
    subagents=[research_sub_agent],
)
```

```python
from datetime import datetime

from deepagents import create_deep_agent
from langchain.chat_models import init_chat_model

max_concurrent_research_units = 3
max_researcher_iterations = 3

current_date = datetime.now().strftime("%Y-%m-%d")

INSTRUCTIONS = (
    RESEARCH_WORKFLOW_INSTRUCTIONS
    + "\n\n"
    + "=" * 80
    + "\n\n"
    + SUBAGENT_DELEGATION_INSTRUCTIONS.format(
        max_concurrent_research_units=max_concurrent_research_units,
        max_researcher_iterations=max_researcher_iterations,
    )
)

research_sub_agent = {
    "name": "research-agent",
    "description": "Delegate research to the sub-agent. Give one topic at a time.",
    "system_prompt": RESEARCHER_INSTRUCTIONS.format(date=current_date),
    "tools": [tavily_search],
}

# 初始化 chat model：后续 agent、chain 或 graph 都会通过这个模型向 LLM 发请求。
model = init_chat_model(model="anthropic:claude-sonnet-4-6", temperature=0.0)

# create_deep_agent 会创建具备规划、文件系统和 subagents 能力的 Deep Agent。
agent = create_deep_agent(
    model=model,
    tools=[tavily_search],
    system_prompt=INSTRUCTIONS,
    # subagents 用来把专门任务委托给独立提示词和工具集合，减轻主 agent 的负担。
    subagents=[research_sub_agent],
)
```

```python
from datetime import datetime

from deepagents import create_deep_agent
from langchain.chat_models import init_chat_model

max_concurrent_research_units = 3
max_researcher_iterations = 3

current_date = datetime.now().strftime("%Y-%m-%d")

INSTRUCTIONS = (
    RESEARCH_WORKFLOW_INSTRUCTIONS
    + "\n\n"
    + "=" * 80
    + "\n\n"
    + SUBAGENT_DELEGATION_INSTRUCTIONS.format(
        max_concurrent_research_units=max_concurrent_research_units,
        max_researcher_iterations=max_researcher_iterations,
    )
)

research_sub_agent = {
    "name": "research-agent",
    "description": "Delegate research to the sub-agent. Give one topic at a time.",
    "system_prompt": RESEARCHER_INSTRUCTIONS.format(date=current_date),
    "tools": [tavily_search],
}

# 初始化 chat model：后续 agent、chain 或 graph 都会通过这个模型向 LLM 发请求。
model = init_chat_model(model="openrouter:anthropic/claude-sonnet-4-6", temperature=0.0)

# create_deep_agent 会创建具备规划、文件系统和 subagents 能力的 Deep Agent。
agent = create_deep_agent(
    model=model,
    tools=[tavily_search],
    system_prompt=INSTRUCTIONS,
    # subagents 用来把专门任务委托给独立提示词和工具集合，减轻主 agent 的负担。
    subagents=[research_sub_agent],
)
```

```python
from datetime import datetime

from deepagents import create_deep_agent
from langchain.chat_models import init_chat_model

max_concurrent_research_units = 3
max_researcher_iterations = 3

current_date = datetime.now().strftime("%Y-%m-%d")

INSTRUCTIONS = (
    RESEARCH_WORKFLOW_INSTRUCTIONS
    + "\n\n"
    + "=" * 80
    + "\n\n"
    + SUBAGENT_DELEGATION_INSTRUCTIONS.format(
        max_concurrent_research_units=max_concurrent_research_units,
        max_researcher_iterations=max_researcher_iterations,
    )
)

research_sub_agent = {
    "name": "research-agent",
    "description": "Delegate research to the sub-agent. Give one topic at a time.",
    "system_prompt": RESEARCHER_INSTRUCTIONS.format(date=current_date),
    "tools": [tavily_search],
}

# 初始化 chat model：后续 agent、chain 或 graph 都会通过这个模型向 LLM 发请求。
model = init_chat_model(model="fireworks:accounts/fireworks/models/qwen3p5-397b-a17b", temperature=0.0)

# create_deep_agent 会创建具备规划、文件系统和 subagents 能力的 Deep Agent。
agent = create_deep_agent(
    model=model,
    tools=[tavily_search],
    system_prompt=INSTRUCTIONS,
    # subagents 用来把专门任务委托给独立提示词和工具集合，减轻主 agent 的负担。
    subagents=[research_sub_agent],
)
```

```python
from datetime import datetime

from deepagents import create_deep_agent
from langchain.chat_models import init_chat_model

max_concurrent_research_units = 3
max_researcher_iterations = 3

current_date = datetime.now().strftime("%Y-%m-%d")

INSTRUCTIONS = (
    RESEARCH_WORKFLOW_INSTRUCTIONS
    + "\n\n"
    + "=" * 80
    + "\n\n"
    + SUBAGENT_DELEGATION_INSTRUCTIONS.format(
        max_concurrent_research_units=max_concurrent_research_units,
        max_researcher_iterations=max_researcher_iterations,
    )
)

research_sub_agent = {
    "name": "research-agent",
    "description": "Delegate research to the sub-agent. Give one topic at a time.",
    "system_prompt": RESEARCHER_INSTRUCTIONS.format(date=current_date),
    "tools": [tavily_search],
}

# 初始化 chat model：后续 agent、chain 或 graph 都会通过这个模型向 LLM 发请求。
model = init_chat_model(model="baseten:zai-org/GLM-5", temperature=0.0)

# create_deep_agent 会创建具备规划、文件系统和 subagents 能力的 Deep Agent。
agent = create_deep_agent(
    model=model,
    tools=[tavily_search],
    system_prompt=INSTRUCTIONS,
    # subagents 用来把专门任务委托给独立提示词和工具集合，减轻主 agent 的负担。
    subagents=[research_sub_agent],
)
```

```python
from datetime import datetime

from deepagents import create_deep_agent
from langchain.chat_models import init_chat_model

max_concurrent_research_units = 3
max_researcher_iterations = 3

current_date = datetime.now().strftime("%Y-%m-%d")

INSTRUCTIONS = (
    RESEARCH_WORKFLOW_INSTRUCTIONS
    + "\n\n"
    + "=" * 80
    + "\n\n"
    + SUBAGENT_DELEGATION_INSTRUCTIONS.format(
        max_concurrent_research_units=max_concurrent_research_units,
        max_researcher_iterations=max_researcher_iterations,
    )
)

research_sub_agent = {
    "name": "research-agent",
    "description": "Delegate research to the sub-agent. Give one topic at a time.",
    "system_prompt": RESEARCHER_INSTRUCTIONS.format(date=current_date),
    "tools": [tavily_search],
}

# 初始化 chat model：后续 agent、chain 或 graph 都会通过这个模型向 LLM 发请求。
model = init_chat_model(model="ollama:devstral-2", temperature=0.0)

# create_deep_agent 会创建具备规划、文件系统和 subagents 能力的 Deep Agent。
agent = create_deep_agent(
    model=model,
    tools=[tavily_search],
    system_prompt=INSTRUCTIONS,
    # subagents 用来把专门任务委托给独立提示词和工具集合，减轻主 agent 的负担。
    subagents=[research_sub_agent],
)
```
#### Gemini
```python
from datetime import datetime

from langchain_google_genai import ChatGoogleGenerativeAI
from deepagents import create_deep_agent

max_concurrent_research_units = 3
max_researcher_iterations = 3

current_date = datetime.now().strftime("%Y-%m-%d")

INSTRUCTIONS = (
    RESEARCH_WORKFLOW_INSTRUCTIONS
    + "\n\n"
    + "=" * 80
    + "\n\n"
    + SUBAGENT_DELEGATION_INSTRUCTIONS.format(
        max_concurrent_research_units=max_concurrent_research_units,
        max_researcher_iterations=max_researcher_iterations,
    )
)

research_sub_agent = {
    "name": "research-agent",
    "description": "Delegate research to the sub-agent. Give one topic at a time.",
    "system_prompt": RESEARCHER_INSTRUCTIONS.format(date=current_date),
    "tools": [tavily_search],
}

model = ChatGoogleGenerativeAI(model="gemini-3-pro-preview", temperature=0.0)

# create_deep_agent 会创建具备规划、文件系统和 subagents 能力的 Deep Agent。
agent = create_deep_agent(
    model=model,
    tools=[tavily_search],
    system_prompt=INSTRUCTIONS,
    # subagents 用来把专门任务委托给独立提示词和工具集合，减轻主 agent 的负担。
    subagents=[research_sub_agent],
)
```
## 运行代理

您可以同步运行代理，这意味着它将等待完整结果然后打印它，或者您可以在更新到来时流式传输它们。

从 `agent.py` 底部的相应选项卡添加代码：

#### 同步运行
```python
from langchain.messages import HumanMessage

if __name__ == "__main__":
    # 这里是实际运行入口：传入 messages 或 state 后，系统会执行推理、工具调用和状态更新。
    result = agent.invoke(
        {
            "messages": [
                HumanMessage(
                    content="What are the main differences between RAG and fine-tuning for LLM applications?"
                )
            ]
        }
    )

    for msg in result.get("messages", []):
        if hasattr(msg, "content") and msg.content:
            print(msg.content)
```
#### 串流更新
```python
from langchain.messages import HumanMessage
from langgraph.types import Overwrite

if __name__ == "__main__":
    # 这里是实际运行入口：传入 messages 或 state 后，系统会执行推理、工具调用和状态更新。
    for chunk in agent.stream(
        {
            "messages": [
                HumanMessage(content="Compare Python vs JavaScript for web development")
            ]
        },
        stream_mode="updates",
    ):
        for node, update in chunk.items():
            if not update or not (messages := update.get("messages")):
                continue
            msg_list = messages.value if isinstance(messages, Overwrite) else messages
            for msg in msg_list:
                if hasattr(msg, "content") and msg.content:
                    print(msg.content)
```
从项目根目录运行代理：
```sh
# 运行示例脚本：执行前请确认依赖、环境变量和当前工作目录都已准备好。
python agent.py
```
如果在运行之前设置 `LANGSMITH_API_KEY` 环境变量，则可以在 [LangSmith](https://docs.langchain.com/langsmith/home) 中查看代理的跟踪来调试和监视多步行为。

## 完整代码

在 GitHub 上查看完整的[深度研究示例](https://github.com/langchain-ai/deepagents/tree/main/examples/deep_research)。

## 后续步骤

现在您已经构建了代理，可以通过更改代理文件中的提示常量来自定义它，以调整工作流、委派策略或研究人员行为。
您还可以调整委派限制以允许更多并行子代理或委派轮次。

有关本教程中的概念的更多信息，请查看以下资源：

* [子代理](https://docs.langchain.com/oss/python/deepagents/subagents)：了解如何使用不同的工具和提示配置子代理
* [自定义](https://docs.langchain.com/oss/python/deepagents/customization)：自定义模型、工具、系统提示和规划行为
* [LangSmith](https://docs.langchain.com/langsmith/home)：跟踪研究运行并调试多步骤行为
* [深度研究课程](https://academy.langchain.com/courses/deep-research-with-langgraph)：LangGraph深度研究完整课程
