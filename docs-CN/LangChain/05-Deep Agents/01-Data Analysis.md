---
title: "数据分析"
aliases:
  - Data Analysis
  - 数据分析
source: https://docs.langchain.com/oss/python/deepagents/data-analysis
source_md: https://docs.langchain.com/oss/python/deepagents/data-analysis.md
source_url: https://docs.langchain.com/oss/python/deepagents/data-analysis
retrieved: 2026-05-07
source_checked: 2026-07-21
content_origin: third-party
content_status: frozen-reference
attribution: LangChain project documentation contributors
tags:
  - langchain
  - python
  - docs/learn
license: MIT
lang: zh-CN
translation_key: LangChain/05-Deep Agents/01-Data Analysis.md
translation_route: en/langchain/upstream-references/deep-agents/data-analysis
translation_default_route: zh-CN/LangChain/05-Deep-Agents/01-Data-Analysis
---

# 数据分析

> [!warning] 冻结参考：代码执行、文件和 Slack 都是外部能力
> 本页是 2026-05-07 的译文快照，不能作为当前 Deep Agents API 或部署配置的保证。任何可执行代码、上传文件、网络访问、artifact 下载和 Slack 发送都必须有隔离 sandbox、最小权限凭据、输出审查、资源预算和审计；本地 shell 不应因示例存在而默认对不可信输入开放。需要实现时先核对本页 `source` 的当前版本，并把真实服务集成放在受控项目环境而非此知识库示例中。

> 构建一个代理来分析数据文件、生成可视化并共享结果

## 概述

本指南演示如何使用[Deep Agents](https://docs.langchain.com/oss/python/deepagents)构建数据分析代理。数据分析任务通常需要规划、代码执行以及处理脚本、报告和绘图等 artifact，而Deep Agents旨在处理这些功能。

我们将构建的代理将：

1. 接受 CSV 文件进行分析
2. 执行探索性数据分析并生成可视化
3. 将结果分享到 Slack 频道

> [!tip]
Slack 集成是可选的。可以修改代理以在本地保存 artifact 或通过其他渠道共享结果。

### 关键概念

本教程涵盖：

* [后端](https://docs.langchain.com/oss/python/deepagents/backends) 用于沙盒代码执行
* 用于外部集成的自定义[工具](https://docs.langchain.com/oss/python/langchain/tools)

## 设置

### 安装

安装核心依赖项：
```bash
# 安装依赖：先把示例需要的包安装到当前 Python 环境。
pip install deepagents
```
### 可选依赖项

对于本教程，我们将使用：

* [Slack Python SDK](https://docs.slack.dev/tools/python-slack-sdk/) 用于共享结果（[令牌设置](https://docs.slack.dev/authentication/tokens/)）
* 用于代码执行的[沙箱](https://docs.langchain.com/oss/python/deepagents/sandboxes)环境。有关设置详细信息，请参阅[可用提供商](https://docs.langchain.com/oss/python/deepagents/sandboxes#available-providers)
```bash
# 安装依赖：先把示例需要的包安装到当前 Python 环境。
pip install slack-sdk
```
> [!note]
这些服务是可选的，但强烈建议将沙盒环境用于任何生产用途。您也可以使用本地 shell 后端（考虑到重要的[安全考虑](https://docs.langchain.com/oss/python/deepagents/backends#localshellbackend-local-shell)）或直接从后端下载 artifact。

### LangSmith

您使用 LangChain 构建的许多应用程序将包含多个步骤以及多次调用 LLM 调用。随着这些应用程序变得越来越复杂，能够检查链或代理内部到底发生了什么变得至关重要。最好的方法是使用 [LangSmith](https://smith.langchain.com?utm_source=docs\&utm_medium=cta\&utm_campaign=langsmith-signup\&utm_content=oss-deepagents-data-analysis)。

在上面的链接注册后，请确保设置环境变量以开始记录跟踪：
```shell
# 配置环境变量：示例会从环境变量读取 API key、模型名或服务地址。
export LANGSMITH_TRACING="true"
export LANGSMITH_API_KEY="..."
```
或者，在 Python 中设置它们：
```python
import getpass
import os

os.environ["LANGSMITH_TRACING"] = "true"
os.environ["LANGSMITH_API_KEY"] = getpass.getpass()
```
## 设置后端

Deep Agents使用 [后端](https://docs.langchain.com/oss/python/deepagents/backends) 在沙盒环境中执行代码。

有关设置详细信息，请参阅[可用提供商](https://docs.langchain.com/oss/python/deepagents/sandboxes#available-providers)。

#### daytona
```bash
# 安装依赖：先把示例需要的包安装到当前 Python 环境。
pip install langchain-daytona
```

```bash
# 安装依赖：先把示例需要的包安装到当前 Python 环境。
uv add langchain-daytona
```

```python
from daytona import Daytona

from langchain_daytona import DaytonaSandbox

sandbox = Daytona().create()
backend = DaytonaSandbox(sandbox=sandbox)
```
验证沙箱是否准备就绪：
```python
result = backend.execute("echo ready")
print(result)
# 示例执行结果：ExecuteResponse(output='ready', exit_code=0, ...)。
```
#### model
```python
import modal

from langchain_modal import ModalSandbox

app = modal.App.lookup("your-app")
modal_sandbox = modal.Sandbox.create(app=app)
backend = ModalSandbox(sandbox=modal_sandbox)
```
#### 运行循环
```bash
# 安装依赖：先把示例需要的包安装到当前 Python 环境。
pip install langchain-runloop
```

```bash
# 安装依赖：先把示例需要的包安装到当前 Python 环境。
uv add langchain-runloop
```

```python
from runloop_api_client import RunloopSDK

from langchain_runloop import RunloopSandbox

api_key = "..."
client = RunloopSDK(bearer_token=api_key)

devbox = client.devbox.create()
backend = RunloopSandbox(devbox=devbox)
```
#### 代理核心
```bash
# 安装依赖：先把示例需要的包安装到当前 Python 环境。
pip install langchain-agentcore-codeinterpreter
```

```bash
# 安装依赖：先把示例需要的包安装到当前 Python 环境。
uv add langchain-agentcore-codeinterpreter
```

```python
from bedrock_agentcore.tools.code_interpreter_client import CodeInterpreter
from langchain_agentcore_codeinterpreter import AgentCoreSandbox

interpreter = CodeInterpreter(region="us-west-2")
interpreter.start()
backend = AgentCoreSandbox(interpreter=interpreter)
```
#### 本地外壳
> [!warning]
该后端提供不受限制的文件系统和 shell 访问。仅在受控环境中使用以进行开发和测试。有关更多详细信息，请参阅[安全注意事项](https://docs.langchain.com/oss/python/deepagents/backends#localshellbackend-local-shell)。
```python
from deepagents.backends import LocalShellBackend

backend = LocalShellBackend(root_dir=".", env={"PATH": "/usr/bin:/bin"})
```
### 上传样本数据

创建示例销售数据并将其上传到后端：
```python
import csv
import io

# 创建示例销售数据。
data = [
    ["Date", "Product", "Units Sold", "Revenue"],
    ["2025-08-01", "Widget A", 10, 250],
    ["2025-08-02", "Widget B", 5, 125],
    ["2025-08-03", "Widget A", 7, 175],
    ["2025-08-04", "Widget C", 3, 90],
    ["2025-08-05", "Widget B", 8, 200],
]

# 转换成 CSV 字节数据。
text_buf = io.StringIO()
writer = csv.writer(text_buf)
writer.writerows(data)
csv_bytes = text_buf.getvalue().encode("utf-8")
text_buf.close()

# 上传到后端。
backend.upload_files([("/home/daytona/data/sales_data.csv", csv_bytes)])
```
## 实施自定义工具

数据分析任务可能会产生 artifact，例如报告或图。
以下简单的[工具](https://docs.langchain.com/oss/python/langchain/tools) 使用 `backend.download_files` 下载它们，然后使用 Slack SDK 上传它们。
我们还可以要求我们的代理列出相关文件路径而不是上传它们，以便感兴趣的各方可以根据需要单独获取它们。
```python
from langchain.tools import tool
from slack_sdk import WebClient

slack_token = os.environ["SLACK_USER_TOKEN"]
slack_client = WebClient(token=slack_token)

# 使用 @tool 可以把普通 Python 函数暴露给 agent，模型会根据函数名、参数和 docstring 判断何时调用。
@tool(parse_docstring=True)
def slack_send_message(text: str, file_path: str | None = None) -> str:
    """Send message, optionally including attachments such as images.

    Args:
        text: (str) text content of the message
        file_path: (str) file path of attachment in the filesystem.
    """
    if not file_path:
        slack_client.chat_postMessage(channel=channel, text=text)
    else:
        fp = backend.download_files([file_path])
        slack_client.files_upload_v2(
            channel="C0123456ABC",  # 在这里指定你自己的 channel。
            content=fp[0].content,
            initial_comment=text,
        )

    return "Message sent."
```
> [!note]
通常，避免向沙箱添加凭据和其他机密是一种好的做法。在这里，我们在工具中管理沙箱之外的 Slack 令牌。

## 运行代理

让我们实例化一个代理：
```python
from langchain_core.utils.uuid import uuid7

from langgraph.checkpoint.memory import InMemorySaver
from deepagents import create_deep_agent

# checkpointer 保存线程内的执行状态，用于多轮对话、暂停恢复和 human-in-the-loop。
checkpointer = InMemorySaver()

# create_deep_agent 会创建具备规划、文件系统和 subagents 能力的 Deep Agent。
agent = create_deep_agent(
    model="google_genai:gemini-3.1-pro-preview",
    tools=[slack_send_message],
    backend=backend,
    checkpointer=checkpointer,
)

thread_id = str(uuid7())
config={"configurable": {"thread_id": thread_id}}
```
我们包括：

* [模型](https://docs.langchain.com/oss/python/deepagents/customization#model) 的选择
* 我们的定制[工具](https://docs.langchain.com/oss/python/deepagents/customization#tools)
* [后端](https://docs.langchain.com/oss/python/deepagents/backends)
* 支持多轮对话的 [checkpointer](https://docs.langchain.com/oss/python/langchain/short-term-memory)

现在让我们调用我们的代理。
```python
input_message = {
    "role": "user",
    "content": (
        "Analyze ./data/sales_data.csv in the current dir and generate a beautiful plot. "
        "When finished, send your analysis and the plot to Slack using the tool."
    ),
}
# 这里是实际运行入口：传入 messages 或 state 后，系统会执行推理、工具调用和状态更新。
for step in agent.stream(
    {"messages": [input_message]},
    config,
    stream_mode="updates",
):
    for _, update in step.items():
        if update and (messages := update.get("messages")) and isinstance(messages, list):
            for message in messages:
                message.pretty_print()
```

```Result
================================== Ai Message ==================================

[{'text': "I'll help you analyze the sales data and create a beautiful plot, then send the results to Slack. Let me start by exploring the data.", 'type': 'text'}, {'id': 'toolu_01LRot5h6WkhdpDQ1SG6EQGQ', 'input': {'file_path': './data/sales_data.csv'}, 'name': 'read_file', 'type': 'tool_use'}]
Tool Calls:
  read_file (toolu_01LRot5h6WkhdpDQ1SG6EQGQ)
 Call ID: toolu_01LRot5h6WkhdpDQ1SG6EQGQ
  Args:
    file_path: ./data/sales_data.csv
================================= Tool Message =================================
Name: read_file

Error: File '/data/sales_data.csv' not found
================================== Ai Message ==================================

[{'text': 'Let me check the current directory structure first:', 'type': 'text'}, {'id': 'toolu_018DSeF8Dx714Dh2M5vJ1JuK', 'input': {'command': 'pwd'}, 'name': 'execute', 'type': 'tool_use'}, {'id': 'toolu_01As782aRsVB3mJpKPKNwg9c', 'input': {'path': '/'}, 'name': 'ls', 'type': 'tool_use'}]
Tool Calls:
  execute (toolu_018DSeF8Dx714Dh2M5vJ1JuK)
 Call ID: toolu_018DSeF8Dx714Dh2M5vJ1JuK
  Args:
    command: pwd
  ls (toolu_01As782aRsVB3mJpKPKNwg9c)
 Call ID: toolu_01As782aRsVB3mJpKPKNwg9c
  Args:
    path: /
================================= Tool Message =================================
Name: execute

/home/daytona
[Command succeeded with exit code 0]
================================= Tool Message =================================
Name: ls

['/bin', '/boot', '/dev', '/etc', '/home', '/lib', '/lib64', '/media', '/mnt', '/opt', '/proc', '/root', '/run', '/sbin', '/srv', '/sys', '/tmp', '/usr', '/var', '/.dockerenv']
================================== Ai Message ==================================

[{'id': 'toolu_01Sv4ut1P2XFsjrzVmQbJLpr', 'input': {'path': '/home/daytona'}, 'name': 'ls', 'type': 'tool_use'}]
Tool Calls:
  ls (toolu_01Sv4ut1P2XFsjrzVmQbJLpr)
 Call ID: toolu_01Sv4ut1P2XFsjrzVmQbJLpr
  Args:
    path: /home/daytona
================================= Tool Message =================================
Name: ls

['/home/daytona/.bash_logout', '/home/daytona/.bashrc', '/home/daytona/.face', '/home/daytona/.face.icon', '/home/daytona/.profile', '/home/daytona/.daytona', '/home/daytona/data', '/home/daytona/.zshrc']
================================== Ai Message ==================================

[{'text': "Great! I can see there's a data directory. Let me check its contents:", 'type': 'text'}, {'id': 'toolu_01WN6V9RZjGGoDXzuWdEgB1z', 'input': {'path': '/home/daytona/data'}, 'name': 'ls', 'type': 'tool_use'}]
Tool Calls:
  ls (toolu_01WN6V9RZjGGoDXzuWdEgB1z)
 Call ID: toolu_01WN6V9RZjGGoDXzuWdEgB1z
  Args:
    path: /home/daytona/data
================================= Tool Message =================================
Name: ls

['/home/daytona/data/sales_data.csv']
================================== Ai Message ==================================

[{'text': 'Perfect! Now let me read the sales data:', 'type': 'text'}, {'id': 'toolu_01RFmneg7mua1G5csH3rH2Zq', 'input': {'file_path': '/home/daytona/data/sales_data.csv'}, 'name': 'read_file', 'type': 'tool_use'}]
Tool Calls:
  read_file (toolu_01RFmneg7mua1G5csH3rH2Zq)
 Call ID: toolu_01RFmneg7mua1G5csH3rH2Zq
  Args:
    file_path: /home/daytona/data/sales_data.csv
================================= Tool Message =================================
Name: read_file

     1	Date,Product,Units Sold,Revenue
     2	2025-08-01,Widget A,10,250
     3	2025-08-02,Widget B,5,125
     4	2025-08-03,Widget A,7,175
     5	2025-08-04,Widget C,3,90
     6	2025-08-05,Widget B,8,200
================================== Ai Message ==================================

[{'text': "Excellent! I can see the sales data. Now I'll create a Python script to analyze the data and generate a beautiful plot. Let me create a comprehensive analysis with visualizations:", 'type': 'text'}, {'id': 'toolu_01JcBjEXgPpCPuaGxn9ALwMg', 'input': {'file_path': '/home/daytona/analyze_sales.py', 'content': 'import pandas as pd\nimport matplotlib.pyplot as plt\nimport seaborn as sns\nfrom datetime import datetime\n\n# Set style for beautiful plots\nsns.set_style("whitegrid")\nplt.rcParams[\'figure.figsize\'] = (14, 10)\nplt.rcParams[\'font.size\'] = 11\n\n# Read the data\ndf = pd.read_csv(\'/home/daytona/data/sales_data.csv\')\ndf[\'Date\'] = pd.to_datetime(df[\'Date\'])\n\n# Analysis\nprint("=" * 60)\nprint("SALES DATA ANALYSIS REPORT")\nprint("=" * 60)\nprint("\\n1. DATA OVERVIEW")\nprint("-" * 60)\nprint(f"Date Range: {df[\'Date\'].min().strftime(\'%Y-%m-%d\')} to {df[\'Date\'].max().strftime(\'%Y-%m-%d\')}")\nprint(f"Total Records: {len(df)}")\nprint(f"Products: {\', \'.join(df[\'Product\'].unique())}")\n\nprint("\\n2. SUMMARY STATISTICS")\nprint("-" * 60)\nprint(f"Total Revenue: ${df[\'Revenue\'].sum():,.2f}")\nprint(f"Total Units Sold: {df[\'Units Sold\'].sum()}")\nprint(f"Average Daily Revenue: ${df[\'Revenue\'].mean():.2f}")\nprint(f"Average Units per Sale: {df[\'Units Sold\'].mean():.2f}")\n\nprint("\\n3. PRODUCT PERFORMANCE")\nprint("-" * 60)\nproduct_stats = df.groupby(\'Product\').agg({\n    \'Revenue\': [\'sum\', \'mean\'],\n    \'Units Sold\': [\'sum\', \'mean\']\n}).round(2)\nprint(product_stats)\n\nprint("\\n4. BEST PERFORMING DAY")\nprint("-" * 60)\nbest_day = df.loc[df[\'Revenue\'].idxmax()]\nprint(f"Date: {best_day[\'Date\'].strftime(\'%Y-%m-%d\')}")\nprint(f"Product: {best_day[\'Product\']}")\nprint(f"Revenue: ${best_day[\'Revenue\']:.2f}")\nprint(f"Units Sold: {best_day[\'Units Sold\']}")\n\n# Create visualizations\nfig = plt.figure(figsize=(16, 12))\nfig.suptitle(\'Sales Data Analysis Dashboard\', fontsize=20, fontweight=\'bold\', y=0.995)\n\n# 1. Revenue by Date\nax1 = plt.subplot(2, 3, 1)\ncolors = sns.color_palette("husl", len(df))\nbars = ax1.bar(df[\'Date\'].dt.strftime(\'%m-%d\'), df[\'Revenue\'], color=colors, edgecolor=\'black\', linewidth=1.5)\nax1.set_title(\'Daily Revenue\', fontsize=14, fontweight=\'bold\', pad=10)\nax1.set_xlabel(\'Date\', fontsize=12, fontweight=\'bold\')\nax1.set_ylabel(\'Revenue ($)\', fontsize=12, fontweight=\'bold\')\nax1.grid(axis=\'y\', alpha=0.3)\nfor bar in bars:\n    height = bar.get_height()\n    ax1.text(bar.get_x() + bar.get_width()/2., height,\n            f\'${int(height)}\',\n            ha=\'center\', va=\'bottom\', fontsize=9, fontweight=\'bold\')\nplt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)\n\n# 2. Units Sold by Date\nax2 = plt.subplot(2, 3, 2)\nbars = ax2.bar(df[\'Date\'].dt.strftime(\'%m-%d\'), df[\'Units Sold\'], color=colors, edgecolor=\'black\', linewidth=1.5)\nax2.set_title(\'Daily Units Sold\', fontsize=14, fontweight=\'bold\', pad=10)\nax2.set_xlabel(\'Date\', fontsize=12, fontweight=\'bold\')\nax2.set_ylabel(\'Units\', fontsize=12, fontweight=\'bold\')\nax2.grid(axis=\'y\', alpha=0.3)\nfor bar in bars:\n    height = bar.get_height()\n    ax2.text(bar.get_x() + bar.get_width()/2., height,\n            f\'{int(height)}\',\n            ha=\'center\', va=\'bottom\', fontsize=9, fontweight=\'bold\')\nplt.setp(ax2.xaxis.get_majorticklabels(), rotation=45)\n\n# 3. Revenue by Product (Pie Chart)\nax3 = plt.subplot(2, 3, 3)\nproduct_revenue = df.groupby(\'Product\')[\'Revenue\'].sum()\ncolors_pie = sns.color_palette("Set2", len(product_revenue))\nwedges, texts, autotexts = ax3.pie(product_revenue, labels=product_revenue.index, autopct=\'%1.1f%%\',\n                                     colors=colors_pie, startangle=90, textprops={\'fontsize\': 11, \'fontweight\': \'bold\'},\n                                     explode=[0.05] * len(product_revenue))\nax3.set_title(\'Revenue Distribution by Product\', fontsize=14, fontweight=\'bold\', pad=10)\nfor autotext in autotexts:\n    autotext.set_color(\'white\')\n    autotext.set_fontsize(12)\n\n# 4. Total Revenue by Product (Bar Chart)\nax4 = plt.subplot(2, 3, 4)\nproduct_revenue_sorted = product_revenue.sort_values(ascending=False)\ncolors_product = sns.color_palette("coolwarm", len(product_revenue_sorted))\nbars = ax4.barh(product_revenue_sorted.index, product_revenue_sorted.values, color=colors_product, edgecolor=\'black\', linewidth=1.5)\nax4.set_title(\'Total Revenue by Product\', fontsize=14, fontweight=\'bold\', pad=10)\nax4.set_xlabel(\'Revenue ($)\', fontsize=12, fontweight=\'bold\')\nax4.set_ylabel(\'Product\', fontsize=12, fontweight=\'bold\')\nax4.grid(axis=\'x\', alpha=0.3)\nfor i, (product, revenue) in enumerate(product_revenue_sorted.items()):\n    ax4.text(revenue, i, f\' ${int(revenue)}\', va=\'center\', fontsize=10, fontweight=\'bold\')\n\n# 5. Total Units Sold by Product\nax5 = plt.subplot(2, 3, 5)\nproduct_units = df.groupby(\'Product\')[\'Units Sold\'].sum().sort_values(ascending=False)\ncolors_units = sns.color_palette("viridis", len(product_units))\nbars = ax5.barh(product_units.index, product_units.values, color=colors_units, edgecolor=\'black\', linewidth=1.5)\nax5.set_title(\'Total Units Sold by Product\', fontsize=14, fontweight=\'bold\', pad=10)\nax5.set_xlabel(\'Units\', fontsize=12, fontweight=\'bold\')\nax5.set_ylabel(\'Product\', fontsize=12, fontweight=\'bold\')\nax5.grid(axis=\'x\', alpha=0.3)\nfor i, (product, units) in enumerate(product_units.items()):\n    ax5.text(units, i, f\' {int(units)}\', va=\'center\', fontsize=10, fontweight=\'bold\')\n\n# 6. Product Distribution\nax6 = plt.subplot(2, 3, 6)\nproduct_counts = df[\'Product\'].value_counts()\ncolors_count = sns.color_palette("muted", len(product_counts))\nwedges, texts, autotexts = ax6.pie(product_counts, labels=product_counts.index, autopct=\'%1.1f%%\',\n                                     colors=colors_count, startangle=45, textprops={\'fontsize\': 11, \'fontweight\': \'bold\'},\n                                     explode=[0.05] * len(product_counts))\nax6.set_title(\'Sales Transactions by Product\', fontsize=14, fontweight=\'bold\', pad=10)\nfor autotext in autotexts:\n    autotext.set_color(\'white\')\n    autotext.set_fontsize(12)\n\nplt.tight_layout()\nplt.savefig(\'/home/daytona/sales_analysis_plot.png\', dpi=300, bbox_inches=\'tight\', facecolor=\'white\')\nprint("\\n" + "=" * 60)\nprint("Plot saved as: sales_analysis_plot.png")\nprint("=" * 60)\n'}, 'name': 'write_file', 'type': 'tool_use'}]
Tool Calls:
  write_file (toolu_01JcBjEXgPpCPuaGxn9ALwMg)
 Call ID: toolu_01JcBjEXgPpCPuaGxn9ALwMg
  Args:
    file_path: /home/daytona/analyze_sales.py
    content: import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime

# Set style for beautiful plots
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (14, 10)
plt.rcParams['font.size'] = 11

# Read the data
df = pd.read_csv('/home/daytona/data/sales_data.csv')
df['Date'] = pd.to_datetime(df['Date'])

# Analysis
print("=" * 60)
print("SALES DATA ANALYSIS REPORT")
print("=" * 60)
print("\n1. DATA OVERVIEW")
print("-" * 60)
print(f"Date Range: {df['Date'].min().strftime('%Y-%m-%d')} to {df['Date'].max().strftime('%Y-%m-%d')}")
print(f"Total Records: {len(df)}")
print(f"Products: {', '.join(df['Product'].unique())}")

print("\n2. SUMMARY STATISTICS")
print("-" * 60)
print(f"Total Revenue: ${df['Revenue'].sum():,.2f}")
print(f"Total Units Sold: {df['Units Sold'].sum()}")
print(f"Average Daily Revenue: ${df['Revenue'].mean():.2f}")
print(f"Average Units per Sale: {df['Units Sold'].mean():.2f}")

print("\n3. PRODUCT PERFORMANCE")
print("-" * 60)
product_stats = df.groupby('Product').agg({
    'Revenue': ['sum', 'mean'],
    'Units Sold': ['sum', 'mean']
}).round(2)
print(product_stats)

print("\n4. BEST PERFORMING DAY")
print("-" * 60)
best_day = df.loc[df['Revenue'].idxmax()]
print(f"Date: {best_day['Date'].strftime('%Y-%m-%d')}")
print(f"Product: {best_day['Product']}")
print(f"Revenue: ${best_day['Revenue']:.2f}")
print(f"Units Sold: {best_day['Units Sold']}")

# Create visualizations
fig = plt.figure(figsize=(16, 12))
fig.suptitle('Sales Data Analysis Dashboard', fontsize=20, fontweight='bold', y=0.995)

# 1. Revenue by Date
ax1 = plt.subplot(2, 3, 1)
colors = sns.color_palette("husl", len(df))
bars = ax1.bar(df['Date'].dt.strftime('%m-%d'), df['Revenue'], color=colors, edgecolor='black', linewidth=1.5)
ax1.set_title('Daily Revenue', fontsize=14, fontweight='bold', pad=10)
ax1.set_xlabel('Date', fontsize=12, fontweight='bold')
ax1.set_ylabel('Revenue ($)', fontsize=12, fontweight='bold')
ax1.grid(axis='y', alpha=0.3)
for bar in bars:
    height = bar.get_height()
    ax1.text(bar.get_x() + bar.get_width()/2., height,
            f'${int(height)}',
            ha='center', va='bottom', fontsize=9, fontweight='bold')
plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)

# 2. Units Sold by Date
ax2 = plt.subplot(2, 3, 2)
bars = ax2.bar(df['Date'].dt.strftime('%m-%d'), df['Units Sold'], color=colors, edgecolor='black', linewidth=1.5)
ax2.set_title('Daily Units Sold', fontsize=14, fontweight='bold', pad=10)
ax2.set_xlabel('Date', fontsize=12, fontweight='bold')
ax2.set_ylabel('Units', fontsize=12, fontweight='bold')
ax2.grid(axis='y', alpha=0.3)
for bar in bars:
    height = bar.get_height()
    ax2.text(bar.get_x() + bar.get_width()/2., height,
            f'{int(height)}',
            ha='center', va='bottom', fontsize=9, fontweight='bold')
plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45)

# 3. Revenue by Product (Pie Chart)
ax3 = plt.subplot(2, 3, 3)
product_revenue = df.groupby('Product')['Revenue'].sum()
colors_pie = sns.color_palette("Set2", len(product_revenue))
wedges, texts, autotexts = ax3.pie(product_revenue, labels=product_revenue.index, autopct='%1.1f%%',
                                     colors=colors_pie, startangle=90, textprops={'fontsize': 11, 'fontweight': 'bold'},
                                     explode=[0.05] * len(product_revenue))
ax3.set_title('Revenue Distribution by Product', fontsize=14, fontweight='bold', pad=10)
for autotext in autotexts:
    autotext.set_color('white')
    autotext.set_fontsize(12)

# 4. Total Revenue by Product (Bar Chart)
ax4 = plt.subplot(2, 3, 4)
product_revenue_sorted = product_revenue.sort_values(ascending=False)
colors_product = sns.color_palette("coolwarm", len(product_revenue_sorted))
bars = ax4.barh(product_revenue_sorted.index, product_revenue_sorted.values, color=colors_product, edgecolor='black', linewidth=1.5)
ax4.set_title('Total Revenue by Product', fontsize=14, fontweight='bold', pad=10)
ax4.set_xlabel('Revenue ($)', fontsize=12, fontweight='bold')
ax4.set_ylabel('Product', fontsize=12, fontweight='bold')
ax4.grid(axis='x', alpha=0.3)
for i, (product, revenue) in enumerate(product_revenue_sorted.items()):
    ax4.text(revenue, i, f' ${int(revenue)}', va='center', fontsize=10, fontweight='bold')

# 5. Total Units Sold by Product
ax5 = plt.subplot(2, 3, 5)
product_units = df.groupby('Product')['Units Sold'].sum().sort_values(ascending=False)
colors_units = sns.color_palette("viridis", len(product_units))
bars = ax5.barh(product_units.index, product_units.values, color=colors_units, edgecolor='black', linewidth=1.5)
ax5.set_title('Total Units Sold by Product', fontsize=14, fontweight='bold', pad=10)
ax5.set_xlabel('Units', fontsize=12, fontweight='bold')
ax5.set_ylabel('Product', fontsize=12, fontweight='bold')
ax5.grid(axis='x', alpha=0.3)
for i, (product, units) in enumerate(product_units.items()):
    ax5.text(units, i, f' {int(units)}', va='center', fontsize=10, fontweight='bold')

# 6. Product Distribution
ax6 = plt.subplot(2, 3, 6)
product_counts = df['Product'].value_counts()
colors_count = sns.color_palette("muted", len(product_counts))
wedges, texts, autotexts = ax6.pie(product_counts, labels=product_counts.index, autopct='%1.1f%%',
                                     colors=colors_count, startangle=45, textprops={'fontsize': 11, 'fontweight': 'bold'},
                                     explode=[0.05] * len(product_counts))
ax6.set_title('Sales Transactions by Product', fontsize=14, fontweight='bold', pad=10)
for autotext in autotexts:
    autotext.set_color('white')
    autotext.set_fontsize(12)

plt.tight_layout()
plt.savefig('/home/daytona/sales_analysis_plot.png', dpi=300, bbox_inches='tight', facecolor='white')
print("\n" + "=" * 60)
print("Plot saved as: sales_analysis_plot.png")
print("=" * 60)
================================= Tool Message =================================
Name: write_file

Updated file /home/daytona/analyze_sales.py
================================== Ai Message ==================================

[{'text': 'Now let me run the analysis script:', 'type': 'text'}, {'id': 'toolu_015xkZr21TuzCTEKGzSqgnbp', 'input': {'command': 'cd /home/daytona && python analyze_sales.py'}, 'name': 'execute', 'type': 'tool_use'}]
Tool Calls:
  execute (toolu_015xkZr21TuzCTEKGzSqgnbp)
 Call ID: toolu_015xkZr21TuzCTEKGzSqgnbp
  Args:
    command: cd /home/daytona && python analyze_sales.py
================================= Tool Message =================================
Name: execute

============================================================
SALES DATA ANALYSIS REPORT
============================================================

1. DATA OVERVIEW
------------------------------------------------------------
Date Range: 2025-08-01 to 2025-08-05
Total Records: 5
Products: Widget A, Widget B, Widget C

2. SUMMARY STATISTICS
------------------------------------------------------------
Total Revenue: $840.00
Total Units Sold: 33
Average Daily Revenue: $168.00
Average Units per Sale: 6.60

3. PRODUCT PERFORMANCE
------------------------------------------------------------
         Revenue        Units Sold
             sum   mean        sum mean
Product
Widget A     425  212.5         17  8.5
Widget B     325  162.5         13  6.5
Widget C      90   90.0          3  3.0

4. BEST PERFORMING DAY
------------------------------------------------------------
Date: 2025-08-01
Product: Widget A
Revenue: $250.00
Units Sold: 10

============================================================
Plot saved as: sales_analysis_plot.png
============================================================
[Command succeeded with exit code 0]
================================== Ai Message ==================================

[{'text': 'Perfect! The analysis is complete and the plot has been generated. Now let me send both the analysis and the plot to Slack:', 'type': 'text'}, {'id': 'toolu_01Qust5a8DECKPZuU9pBBvkz', 'input': {'text': '📊 **SALES DATA ANALYSIS REPORT** 📊\n\n**1. DATA OVERVIEW**\n• Date Range: August 1-5, 2025 (5 days)\n• Products Analyzed: Widget A, Widget B, Widget C\n\n**2. KEY METRICS**\n💰 Total Revenue: $840.00\n📦 Total Units Sold: 33 units\n📈 Average Daily Revenue: $168.00\n📊 Average Units per Sale: 6.60\n\n**3. PRODUCT PERFORMANCE**\n🏆 Widget A (Top Performer)\n   - Total Revenue: $425 (50.6% of total)\n   - Total Units Sold: 17 (avg 8.5 per transaction)\n\n🥈 Widget B\n   - Total Revenue: $325 (38.7% of total)\n   - Total Units Sold: 13 (avg 6.5 per transaction)\n\n🥉 Widget C\n   - Total Revenue: $90 (10.7% of total)\n   - Total Units Sold: 3 (avg 3.0 per transaction)\n\n**4. BEST PERFORMING DAY**\n🌟 August 1, 2025\n   - Product: Widget A\n   - Revenue: $250.00\n   - Units Sold: 10\n\n**KEY INSIGHTS:**\n✅ Widget A is the clear leader, generating over 50% of total revenue\n✅ Widget B shows strong performance with consistent sales\n⚠️ Widget C has potential for improvement - lowest sales and revenue\n📊 Daily revenue ranges from $90 to $250\n\nSee attached visualization dashboard for detailed charts! 📈', 'file_path': '/home/daytona/sales_analysis_plot.png'}, 'name': 'slack_send_message', 'type': 'tool_use'}]
Tool Calls:
  slack_send_message (toolu_01Qust5a8DECKPZuU9pBBvkz)
 Call ID: toolu_01Qust5a8DECKPZuU9pBBvkz
  Args:
    text: 📊 **SALES DATA ANALYSIS REPORT** 📊

**1. DATA OVERVIEW**
• Date Range: August 1-5, 2025 (5 days)
• Products Analyzed: Widget A, Widget B, Widget C

**2. KEY METRICS**
💰 Total Revenue: $840.00
📦 Total Units Sold: 33 units
📈 Average Daily Revenue: $168.00
📊 Average Units per Sale: 6.60

**3. PRODUCT PERFORMANCE**
🏆 Widget A (Top Performer)
   - Total Revenue: $425 (50.6% of total)
   - Total Units Sold: 17 (avg 8.5 per transaction)

🥈 Widget B
   - Total Revenue: $325 (38.7% of total)
   - Total Units Sold: 13 (avg 6.5 per transaction)

🥉 Widget C
   - Total Revenue: $90 (10.7% of total)
   - Total Units Sold: 3 (avg 3.0 per transaction)

**4. BEST PERFORMING DAY**
🌟 August 1, 2025
   - Product: Widget A
   - Revenue: $250.00
   - Units Sold: 10

**KEY INSIGHTS:**
✅ Widget A is the clear leader, generating over 50% of total revenue
✅ Widget B shows strong performance with consistent sales
⚠️ Widget C has potential for improvement - lowest sales and revenue
📊 Daily revenue ranges from $90 to $250

See attached visualization dashboard for detailed charts! 📈
    file_path: /home/daytona/sales_analysis_plot.png
================================= Tool Message =================================
Name: slack_send_message

Message sent.
================================== Ai Message ==================================

Excellent! I've successfully completed the analysis and sent everything to Slack. Here's what I did:

## Summary

**Analysis Completed:**
- Analyzed the sales data from August 1-5, 2025
- Processed data for 3 products (Widget A, B, and C)
- Generated comprehensive statistics and insights

**Key Findings:**
1. **Total Revenue:** $840 across 5 days
2. **Best Product:** Widget A ($425 revenue, 50.6% of total)
3. **Best Day:** August 1st with $250 in revenue
4. **Total Units Sold:** 33 units

**Visualization Created:**
A beautiful 6-panel dashboard featuring:
- Daily revenue trends
- Daily units sold
- Revenue distribution by product (pie chart)
- Total revenue by product (horizontal bar chart)
- Total units sold by product (horizontal bar chart)
- Sales transactions distribution (pie chart)

**Delivered to Slack:**
✅ Comprehensive analysis report with key metrics and insights
✅ High-resolution visualization dashboard (saved as PNG)

The analysis reveals that Widget A is the top performer, while Widget C shows room for improvement. All results have been sent to your Slack workspace!
```
查看此执行的完整 [LangSmith 跟踪](https://smith.langchain.com/public/ac2443a8-16ad-4e00-8f02-afde6a737534/r)。

## 结果

代理成功分析数据并向 Slack 共享包含可视化内容的综合报告：

> 框架说明：Agent生成的分析报告和可视化仪表板交付给Slack
<img src="LangChain/attachments/images/data_analysis_slack_response.png" alt="Sales analysis results in Slack" width="514" height="961" data-path="images/data_analysis_slack_response.png" data-source="https://docs.langchain.com/images/data_analysis_slack_response.png" />

> [!tip]
您可以直接从后端下载 artifact，无需使用外部工具：
```python
backend.download_files(list_of_filepaths)
```
> [!note]
请参阅[提供商指南](https://docs.langchain.com/oss/python/deepagents/sandboxes#available-providers) 了解如何在完成后清理沙箱。

## 后续步骤

现在您已经构建了数据分析代理，请探索以下资源来扩展其功能：

* [后端](https://docs.langchain.com/oss/python/deepagents/backends)：了解 Deep Agents 后端系统
* [沙箱](https://docs.langchain.com/oss/python/deepagents/sandboxes)：检查沙箱代码执行的后端，包括安全注意事项和高级配置
* [定制](https://docs.langchain.com/oss/python/deepagents/customization)：了解如何使用不同的模型、工具、提示和规划策略定制您的代理
* [CLI](https://docs.langchain.com/oss/python/deepagents/cli/overview)：尝试使用 Deep Agents CLI 作为终端编码代理，以协助本地数据分析和其他代理任务
* [技能](https://docs.langchain.com/oss/python/deepagents/skills)：为您的代理配备可重复使用的常见工作流技能
* [人在回路](https://docs.langchain.com/oss/python/deepagents/human-in-the-loop)：为数据分析工作流中的关键操作添加交互式审批步骤
