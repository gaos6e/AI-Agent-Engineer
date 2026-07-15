---
title: 语义搜索
aliases:
  - Semantic Search
  - 语义搜索
source: https://docs.langchain.com/oss/python/langchain/knowledge-base
source_md: https://docs.langchain.com/oss/python/langchain/knowledge-base.md
retrieved: 2026-05-07
tags:
  - langchain
  - python
  - docs/learn
license: MIT
---

# 语义搜索

## 概述

本教程将让您熟悉 LangChain 的[文档加载器](https://docs.langchain.com/oss/python/integrations/document_loaders)、[嵌入](https://docs.langchain.com/oss/python/integrations/embeddings)和[向量存储](https://docs.langchain.com/oss/python/integrations/vectorstores)抽象。这些抽象用于从（向量）数据库和其他来源检索数据，并将检索结果接入 LLM 工作流。对于需要在模型推理时取用外部数据的应用来说，它们非常重要，例如检索增强生成 [RAG](https://docs.langchain.com/oss/python/langchain/retrieval)。

在这里，我们将在 PDF 文档上构建一个搜索引擎。这将使我们能够检索 PDF 中类似于输入查询的段落。该指南还包括搜索引擎之上的最小 RAG 实现。

### 概念

本指南重点介绍文本数据的检索。我们将涵盖以下概念：

* [文档和文档加载器](https://docs.langchain.com/oss/python/integrations/document_loaders);
* [文本分割器](https://docs.langchain.com/oss/python/integrations/splitters);
* [嵌入](https://docs.langchain.com/oss/python/integrations/embeddings);
* [向量存储](https://docs.langchain.com/oss/python/integrations/vectorstores) 和[检索器](https://docs.langchain.com/oss/python/integrations/retrievers)。

## 设置

### 安装

本教程需要 `langchain-community` 和 `pypdf` 包：
```bash
# 安装依赖：先把示例需要的包安装到当前 Python 环境。
pip install langchain-community pypdf
```

```bash
conda install langchain-community pypdf -c conda-forge
```

```bash
# 安装依赖：先把示例需要的包安装到当前 Python 环境。
uv add langchain-community pypdf
```
有关更多详细信息，请参阅[安装指南](https://docs.langchain.com/oss/python/langchain/install)。

### LangSmith

您使用 LangChain 构建的许多应用程序将包含多个步骤以及多次调用 LLM 调用。
随着这些应用程序变得越来越复杂，能够检查链或代理内部到底发生了什么变得至关重要。
最好的方法是使用 [LangSmith](https://smith.langchain.com?utm_source=docs\&utm_medium=cta\&utm_campaign=langsmith-signup\&utm_content=oss-langchain-knowledge-base)。

在上面的链接注册后，请确保设置环境变量以开始记录跟踪：
```shell
# 配置环境变量：示例会从环境变量读取 API key、模型名或服务地址。
export LANGSMITH_TRACING="true"
export LANGSMITH_API_KEY="..."
```
或者，如果在笔记本中，您可以使用以下命令设置它们：
```python
import getpass
import os

os.environ["LANGSMITH_TRACING"] = "true"
os.environ["LANGSMITH_API_KEY"] = getpass.getpass()
```
## 1. 文档和文档加载器

LangChain 实现了一个 [Document](https://reference.langchain.com/python/langchain-core/documents/base/Document) 抽象，旨在表示文本单元和相关元数据。它具有三个属性：

* `page_content`：代表内容的字符串；
* `metadata`：包含任意元数据的字典；
* `id`：（可选）文档的字符串标识符。

`metadata` 属性可以捕获有关文档来源、其与其他文档的关系以及其他信息的信息。请注意，单个 [`Document`](https://reference.langchain.com/python/langchain-core/documents/base/Document) 对象通常代表较大文档的一块。

我们可以在需要时生成示例文档：
```python
from langchain_core.documents import Document

documents = [
    Document(
        page_content="Dogs are great companions, known for their loyalty and friendliness.",
        metadata={"source": "mammal-pets-doc"},
    ),
    Document(
        page_content="Cats are independent pets that often enjoy their own space.",
        metadata={"source": "mammal-pets-doc"},
    ),
]
```
然而，LangChain生态系统实现了与数百个常见源集成的[文档加载器](https://docs.langchain.com/oss/python/integrations/document_loaders)。这使得您可以轻松地将这些来源的数据合并到您的人工智能应用程序中。

### 装载文件

让我们将 PDF 加载到 [`Document`](https://reference.langchain.com/python/langchain-core/documents/base/Document) 对象序列中。 [这里是一个 PDF 样本](https://github.com/langchain-ai/langchain/blob/v0.3/docs/docs/example_data/nke-10k-2023.pdf)——Nike 从 2023 年开始的 10-k 文件。我们可以查阅 LangChain 文档以获取[可用的 PDF 文档加载器](https://docs.langchain.com/oss/python/integrations/document_loaders/#pdfs)。
```python
from langchain_community.document_loaders import PyPDFLoader

file_path = "../example_data/nke-10k-2023.pdf"
loader = PyPDFLoader(file_path)

# 加载和切分阶段会把长资料拆成较小 chunk，方便 embedding 和检索。
docs = loader.load()

print(len(docs))
```

```text
107
```
`PyPDFLoader` 为每个 PDF 页面加载一个 [`Document`](https://reference.langchain.com/python/langchain-core/documents/base/Document) 对象。对于每个，我们都可以轻松访问：

* 页面的字符串内容；
* 包含文件名和页码的元数据。
```python
print(f"{docs[0].page_content[:200]}\n")
print(docs[0].metadata)
```

```python
Table of Contents
UNITED STATES
SECURITIES AND EXCHANGE COMMISSION
Washington, D.C. 20549
FORM 10-K
(Mark One)
☑ ANNUAL REPORT PURSUANT TO SECTION 13 OR 15(D) OF THE SECURITIES EXCHANGE ACT OF 1934
FO

{'source': '../example_data/nke-10k-2023.pdf', 'page': 0}
```
### 分裂

对于信息检索和下游问答来说，页面的表示可能过于粗糙。我们的最终目标是检索回答输入查询的 [`Document`](https://reference.langchain.com/python/langchain-core/documents/base/Document) 对象，进一步分割 PDF 将有助于确保文档相关部分的含义不会被周围的文本“冲走”。

我们可以使用[文本分割器](https://docs.langchain.com/oss/python/integrations/splitters)来达到此目的。这里我们将使用一个简单的文本分割器，根据字符进行分区。我们将把文档分成 1000 个字符的块
块之间有 200 个字符的重叠。重叠有助于
减少将声明与重要内容分开的可能性
与其相关的上下文。我们使用
`RecursiveCharacterTextSplitter`，
这将使用常见的分隔符递归地分割文档，例如
新行，直到每个块的大小合适。这是
推荐用于通用文本用例的文本分割器。

我们设置 `add_start_index=True` 以便每个字符的索引
切分后的 `Document` 在原始 `Document` 中的起始位置会保存在
元数据属性“start\_index”。
```python
from langchain_text_splitters import RecursiveCharacterTextSplitter

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000, chunk_overlap=200, add_start_index=True
)
# 加载和切分阶段会把长资料拆成较小 chunk，方便 embedding 和检索。
all_splits = text_splitter.split_documents(docs)

print(len(all_splits))
```

```text
514
```
## 2. 嵌入

矢量搜索是存储和搜索非结构化数据（例如非结构化文本）的常用方法。这个想法是存储与文本关联的数字向量。给定一个查询，我们可以将其[embed](https://docs.langchain.com/oss/python/integrations/embeddings)作为相同维度的向量，并使用向量相似度度量（例如余弦相似度）来识别相关文本。

LangChain 支持来自[数十个提供商](https://docs.langchain.com/oss/python/integrations/embeddings/) 的嵌入。这些模型指定如何将文本转换为数字向量。让我们选择一个模型：

#### OpenAI
```shell
# 安装依赖：先把示例需要的包安装到当前 Python 环境。
pip install -U "langchain-openai"
```

```python
import getpass
import os

if not os.environ.get("OPENAI_API_KEY"):
    os.environ["OPENAI_API_KEY"] = getpass.getpass("Enter API key for OpenAI: ")

from langchain_openai import OpenAIEmbeddings

# embedding 模型会把文本转换成向量，这是 semantic search 和 RAG 检索的基础。
embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
```
#### Azure
```shell
# 安装依赖：先把示例需要的包安装到当前 Python 环境。
pip install -U "langchain-openai"
```

```python
import getpass
import os

if not os.environ.get("AZURE_OPENAI_API_KEY"):
    os.environ["AZURE_OPENAI_API_KEY"] = getpass.getpass("Enter API key for Azure: ")

from langchain_openai import AzureOpenAIEmbeddings

# embedding 模型会把文本转换成向量，这是 semantic search 和 RAG 检索的基础。
embeddings = AzureOpenAIEmbeddings(
    azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
    azure_deployment=os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"],
    openai_api_version=os.environ["AZURE_OPENAI_API_VERSION"],
)
```
#### Google Gemini
```shell
# 安装依赖：先把示例需要的包安装到当前 Python 环境。
pip install -qU langchain-google-genai
```

```python
import getpass
import os

if not os.environ.get("GOOGLE_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = getpass.getpass("Enter API key for Google Gemini: ")

from langchain_google_genai import GoogleGenerativeAIEmbeddings

# embedding 模型会把文本转换成向量，这是 semantic search 和 RAG 检索的基础。
embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
```
#### 谷歌顶点
```shell
# 安装依赖：先把示例需要的包安装到当前 Python 环境。
pip install -qU langchain-google-vertexai
```

```python
from langchain_google_vertexai import VertexAIEmbeddings

# embedding 模型会把文本转换成向量，这是 semantic search 和 RAG 检索的基础。
embeddings = VertexAIEmbeddings(model="text-embedding-005")
```
#### AWS
```shell
# 安装依赖：先把示例需要的包安装到当前 Python 环境。
pip install -qU langchain-aws
```

```python
from langchain_aws import BedrockEmbeddings

# embedding 模型会把文本转换成向量，这是 semantic search 和 RAG 检索的基础。
embeddings = BedrockEmbeddings(model_id="amazon.titan-embed-text-v2:0")
```
#### Hugging Face
```shell
# 安装依赖：先把示例需要的包安装到当前 Python 环境。
pip install -qU langchain-huggingface
```

```python
from langchain_huggingface import HuggingFaceEmbeddings

# embedding 模型会把文本转换成向量，这是 semantic search 和 RAG 检索的基础。
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-mpnet-base-v2")
```
#### 奥拉马
```shell
# 安装依赖：先把示例需要的包安装到当前 Python 环境。
pip install -qU langchain-ollama
```

```python
from langchain_ollama import OllamaEmbeddings

# embedding 模型会把文本转换成向量，这是 semantic search 和 RAG 检索的基础。
embeddings = OllamaEmbeddings(model="llama3")
```
#### 连贯
```shell
# 安装依赖：先把示例需要的包安装到当前 Python 环境。
pip install -qU langchain-cohere
```

```python
import getpass
import os

if not os.environ.get("COHERE_API_KEY"):
    os.environ["COHERE_API_KEY"] = getpass.getpass("Enter API key for Cohere: ")

from langchain_cohere import CohereEmbeddings

# embedding 模型会把文本转换成向量，这是 semantic search 和 RAG 检索的基础。
embeddings = CohereEmbeddings(model="embed-english-v3.0")
```
#### MistralAI
```shell
# 安装依赖：先把示例需要的包安装到当前 Python 环境。
pip install -qU langchain-mistralai
```

```python
import getpass
import os

if not os.environ.get("MISTRALAI_API_KEY"):
    os.environ["MISTRALAI_API_KEY"] = getpass.getpass("Enter API key for MistralAI: ")

from langchain_mistralai import MistralAIEmbeddings

# embedding 模型会把文本转换成向量，这是 semantic search 和 RAG 检索的基础。
embeddings = MistralAIEmbeddings(model="mistral-embed")
```
#### 诺米克
```shell
# 安装依赖：先把示例需要的包安装到当前 Python 环境。
pip install -qU langchain-nomic
```

```python
import getpass
import os

if not os.environ.get("NOMIC_API_KEY"):
    os.environ["NOMIC_API_KEY"] = getpass.getpass("Enter API key for Nomic: ")

from langchain_nomic import NomicEmbeddings

# embedding 模型会把文本转换成向量，这是 semantic search 和 RAG 检索的基础。
embeddings = NomicEmbeddings(model="nomic-embed-text-v1.5")
```
#### 英伟达
```shell
# 安装依赖：先把示例需要的包安装到当前 Python 环境。
pip install -qU langchain-nvidia-ai-endpoints
```

```python
import getpass
import os

if not os.environ.get("NVIDIA_API_KEY"):
    os.environ["NVIDIA_API_KEY"] = getpass.getpass("Enter API key for NVIDIA: ")

from langchain_nvidia_ai_endpoints import NVIDIAEmbeddings

# embedding 模型会把文本转换成向量，这是 semantic search 和 RAG 检索的基础。
embeddings = NVIDIAEmbeddings(model="NV-Embed-QA")
```
#### 航程人工智能
```shell
# 安装依赖：先把示例需要的包安装到当前 Python 环境。
pip install -qU langchain-voyageai
```

```python
import getpass
import os

if not os.environ.get("VOYAGE_API_KEY"):
    os.environ["VOYAGE_API_KEY"] = getpass.getpass("Enter API key for Voyage AI: ")

from langchain-voyageai import VoyageAIEmbeddings

# embedding 模型会把文本转换成向量，这是 semantic search 和 RAG 检索的基础。
embeddings = VoyageAIEmbeddings(model="voyage-3")
```
#### IBM沃森克斯
```shell
# 安装依赖：先把示例需要的包安装到当前 Python 环境。
pip install -qU langchain-ibm
```

```python
import getpass
import os

if not os.environ.get("WATSONX_APIKEY"):
    os.environ["WATSONX_APIKEY"] = getpass.getpass("Enter API key for IBM watsonx: ")

from langchain_ibm import WatsonxEmbeddings

# embedding 模型会把文本转换成向量，这是 semantic search 和 RAG 检索的基础。
embeddings = WatsonxEmbeddings(
    model_id="ibm/slate-125m-english-rtrvr",
    url="https://us-south.ml.cloud.ibm.com",
    project_id="<WATSONX PROJECT_ID>",
)
```
#### 伪造的
```shell
# 安装依赖：先把示例需要的包安装到当前 Python 环境。
pip install -qU langchain-core
```

```python
from langchain_core.embeddings import DeterministicFakeEmbedding

# embedding 模型会把文本转换成向量，这是 semantic search 和 RAG 检索的基础。
embeddings = DeterministicFakeEmbedding(size=4096)
```
#### 以撒
```shell
# 安装依赖：先把示例需要的包安装到当前 Python 环境。
pip install -qU langchain-isaacus
```

```python
import getpass
import os

if not os.environ.get("ISAACUS_API_KEY"):
os.environ["ISAACUS_API_KEY"] = getpass.getpass("Enter API key for Isaacus: ")

from langchain_isaacus import IsaacusEmbeddings

# embedding 模型会把文本转换成向量，这是 semantic search 和 RAG 检索的基础。
embeddings = IsaacusEmbeddings(model="kanon-2-embedder")
```

```python
vector_1 = embeddings.embed_query(all_splits[0].page_content)
vector_2 = embeddings.embed_query(all_splits[1].page_content)

assert len(vector_1) == len(vector_2)
print(f"Generated vectors of length {len(vector_1)}\n")
print(vector_1[:10])
```

```text
Generated vectors of length 1536

[-0.008586574345827103, -0.03341241180896759, -0.008936782367527485, -0.0036674530711025, 0.010564599186182022, 0.009598285891115665, -0.028587326407432556, -0.015824200585484505, 0.0030416189692914486, -0.012899317778646946]
```
有了用于生成文本嵌入的模型，我们接下来可以将它们存储在支持高效相似性搜索的特殊数据结构中。

## 3. 向量存储

LangChain [VectorStore](https://reference.langchain.com/python/langchain-core/vectorstores/base/VectorStore) 对象包含将文本和 [`Document`](https://reference.langchain.com/python/langchain-core/documents/base/Document) 对象添加到存储并使用各种相似性度量查询它们的方法。它们通常使用[嵌入](https://docs.langchain.com/oss/python/integrations/embeddings)模型进行初始化，该模型确定如何将文本数据转换为数字向量。

LangChain 包含一套具有不同向量存储技术的[集成](https://docs.langchain.com/oss/python/integrations/vectorstores)。一些向量存储由提供商（例如，各种云提供商）托管，并且需要特定的凭据才能使用；有些（例如 [Postgres](https://docs.langchain.com/oss/python/integrations/vectorstores/pgvector)）在单独的基础设施中运行，可以在本地或通过第三方运行；其他可以在内存中运行以处理轻量级工作负载。让我们选择一个向量存储：

#### 内存中
```shell
# 安装依赖：先把示例需要的包安装到当前 Python 环境。
pip install -U "langchain-core"
```

```python
from langchain_core.vectorstores import InMemoryVectorStore

# vector store 用来保存文本向量和元数据，查询时按语义相似度找回相关片段。
vector_store = InMemoryVectorStore(embeddings)
```
#### 亚马逊开放搜索
```shell
# 安装依赖：先把示例需要的包安装到当前 Python 环境。
pip install -qU  boto3
```

```python
from opensearchpy import RequestsHttpConnection

service = "es"  # 必须把 service 设置为 'es'。
region = "us-east-2"
credentials = boto3.Session(
    aws_access_key_id="xxxxxx", aws_secret_access_key="xxxxx"
).get_credentials()
awsauth = AWS4Auth("xxxxx", "xxxxxx", region, service, session_token=credentials.token)

# vector store 用来保存文本向量和元数据，查询时按语义相似度找回相关片段。
vector_store = OpenSearchVectorSearch.from_documents(
    docs,
    embeddings,
    opensearch_url="host url",
    http_auth=awsauth,
    timeout=300,
    use_ssl=True,
    verify_certs=True,
    connection_class=RequestsHttpConnection,
    index_name="test-index",
)
```
#### 阿斯特拉数据库
```shell
# 安装依赖：先把示例需要的包安装到当前 Python 环境。
pip install -U "langchain-astradb"
```

```python
from langchain_astradb import AstraDBVectorStore

# vector store 用来保存文本向量和元数据，查询时按语义相似度找回相关片段。
vector_store = AstraDBVectorStore(
    # embedding 模型会把文本转换成向量，这是 semantic search 和 RAG 检索的基础。
    embedding=embeddings,
    api_endpoint=ASTRA_DB_API_ENDPOINT,
    collection_name="astra_vector_langchain",
    token=ASTRA_DB_APPLICATION_TOKEN,
    namespace=ASTRA_DB_NAMESPACE,
)
```
#### Chroma
```shell
# 安装依赖：先把示例需要的包安装到当前 Python 环境。
pip install -qU langchain-chroma
```

```python
from langchain_chroma import Chroma

# vector store 用来保存文本向量和元数据，查询时按语义相似度找回相关片段。
vector_store = Chroma(
    collection_name="example_collection",
    embedding_function=embeddings,
    persist_directory="./chroma_langchain_db",  # 本地保存数据的位置；如果不需要保存可以移除。
)
```
#### FAISS
```shell
# 安装依赖：先把示例需要的包安装到当前 Python 环境。
pip install -qU langchain-community faiss-cpu
```

```python
import faiss
from langchain_community.docstore.in_memory import InMemoryDocstore
from langchain_community.vectorstores import FAISS

embedding_dim = len(embeddings.embed_query("hello world"))
index = faiss.IndexFlatL2(embedding_dim)

# vector store 用来保存文本向量和元数据，查询时按语义相似度找回相关片段。
vector_store = FAISS(
    embedding_function=embeddings,
    index=index,
    docstore=InMemoryDocstore(),
    index_to_docstore_id={},
)
```
#### 米尔乌斯
```shell
# 安装依赖：先把示例需要的包安装到当前 Python 环境。
pip install -qU langchain-milvus
```

```python
from langchain_milvus import Milvus

URI = "./milvus_example.db"

# vector store 用来保存文本向量和元数据，查询时按语义相似度找回相关片段。
vector_store = Milvus(
    embedding_function=embeddings,
    connection_args={"uri": URI},
    index_params={"index_type": "FLAT", "metric_type": "L2"},
)
```
#### MongoDB
```shell
# 安装依赖：先把示例需要的包安装到当前 Python 环境。
pip install -qU langchain-mongodb
```

```python
from langchain_mongodb import MongoDBAtlasVectorSearch

# vector store 用来保存文本向量和元数据，查询时按语义相似度找回相关片段。
vector_store = MongoDBAtlasVectorSearch(
    # embedding 模型会把文本转换成向量，这是 semantic search 和 RAG 检索的基础。
    embedding=embeddings,
    collection=MONGODB_COLLECTION,
    index_name=ATLAS_VECTOR_SEARCH_INDEX_NAME,
    relevance_score_fn="cosine",
)
```
#### PG向量
```shell
# 安装依赖：先把示例需要的包安装到当前 Python 环境。
pip install -qU langchain-postgres
```

```python
from langchain_postgres import PGVector

# vector store 用来保存文本向量和元数据，查询时按语义相似度找回相关片段。
vector_store = PGVector(
    # embedding 模型会把文本转换成向量，这是 semantic search 和 RAG 检索的基础。
    embeddings=embeddings,
    collection_name="my_docs",
    connection="postgresql+psycopg://...",
)
```
#### PGVectorStore
```shell
# 安装依赖：先把示例需要的包安装到当前 Python 环境。
pip install -qU langchain-postgres
```

```python
from langchain_postgres import PGEngine, PGVectorStore

pg_engine = PGEngine.from_connection_string(
    url="postgresql+psycopg://..."
)

# vector store 用来保存文本向量和元数据，查询时按语义相似度找回相关片段。
vector_store = PGVectorStore.create_sync(
    engine=pg_engine,
    table_name='test_table',
    embedding_service=embeddings
)
```
#### Pinecone
```shell
# 安装依赖：先把示例需要的包安装到当前 Python 环境。
pip install -qU langchain-pinecone
```

```python
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone

pc = Pinecone(api_key=...)
index = pc.Index(index_name)

# embedding 模型会把文本转换成向量，这是 semantic search 和 RAG 检索的基础。
vector_store = PineconeVectorStore(embedding=embeddings, index=index)
```
#### Qdrant
```shell
# 安装依赖：先把示例需要的包安装到当前 Python 环境。
pip install -qU langchain-qdrant
```

```python
from qdrant_client.models import Distance, VectorParams
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient

client = QdrantClient(":memory:")

vector_size = len(embeddings.embed_query("sample text"))

if not client.collection_exists("test"):
    client.create_collection(
        collection_name="test",
        vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE)
    )
# vector store 用来保存文本向量和元数据，查询时按语义相似度找回相关片段。
vector_store = QdrantVectorStore(
    client=client,
    collection_name="test",
    # embedding 模型会把文本转换成向量，这是 semantic search 和 RAG 检索的基础。
    embedding=embeddings,
)
```
实例化向量存储后，我们现在可以索引文档。
```python
# vector store 用来保存文本向量和元数据，查询时按语义相似度找回相关片段。
ids = vector_store.add_documents(documents=all_splits)
```
请注意，大多数向量存储实现将允许您连接到现有向量存储 - 例如，通过提供客户端、索引名称或其他信息。有关更多详细信息，请参阅特定[集成](https://docs.langchain.com/oss/python/integrations/vectorstores) 的文档。

一旦我们实例化了包含文档的 [`VectorStore`](https://reference.langchain.com/python/langchain-core/vectorstores/base/VectorStore)，我们就可以查询它。 [VectorStore](https://reference.langchain.com/python/langchain-core/vectorstores/base/VectorStore) 包含查询方法：

* 同步和异步；
* 按字符串查询和按向量查询；
* 有或没有返回相似度分数；
* 通过相似性和[最大边际相关性](https://reference.langchain.com/python/langchain-core/vectorstores/base/VectorStore/max_marginal_relevance_search)（平衡相似性与检索结果中查询的多样性）。

这些方法通常会在其输出中包含 [Document](https://reference.langchain.com/python/langchain-core/documents/base/Document) 对象的列表。

**用法**

嵌入通常将文本表示为“密集”向量，使得具有相似含义的文本在几何上接近。这使我们只需传入问题即可检索相关信息，而无需了解文档中使用的任何特定关键术语。

根据与字符串查询的相似性返回文档：
```python
# similarity_search 根据向量相似度返回最相关的文档片段，是最基础的语义搜索入口。
results = vector_store.similarity_search(
    "How many distribution centers does Nike have in the US?"
)

print(results[0])
```

```python
page_content='direct to consumer operations sell products through the following number of retail stores in the United States:
U.S. RETAIL STORES NUMBER
NIKE Brand factory stores 213
NIKE Brand in-line stores (including employee-only stores) 74
Converse stores (including factory stores) 82
TOTAL 369
In the United States, NIKE has eight significant distribution centers. Refer to Item 2. Properties for further information.
2023 FORM 10-K 2' metadata={'page': 4, 'source': '../example_data/nke-10k-2023.pdf', 'start_index': 3125}
```
异步查询：
```python
results = await vector_store.asimilarity_search("When was Nike incorporated?")

print(results[0])
```

```python
page_content='Table of Contents
PART I
ITEM 1. BUSINESS
GENERAL
NIKE, Inc. was incorporated in 1967 under the laws of the State of Oregon. As used in this Annual Report on Form 10-K (this "Annual Report"), the terms "we," "us," "our,"
"NIKE" and the "Company" refer to NIKE, Inc. and its predecessors, subsidiaries and affiliates, collectively, unless the context indicates otherwise.
Our principal business activity is the design, development and worldwide marketing and selling of athletic footwear, apparel, equipment, accessories and services. NIKE is
the largest seller of athletic footwear and apparel in the world. We sell our products through NIKE Direct operations, which are comprised of both NIKE-owned retail stores
and sales through our digital platforms (also referred to as "NIKE Brand Digital"), to retail accounts and to a mix of independent distributors, licensees and sales' metadata={'page': 3, 'source': '../example_data/nke-10k-2023.pdf', 'start_index': 0}
```
返回分数：
```python
# 注意：不同 provider 对分数的定义不同；这里的分数。
# 是距离度量，数值越小通常表示相似度越高。

results = vector_store.similarity_search_with_score("What was Nike's revenue in 2023?")
doc, score = results[0]
print(f"Score: {score}\n")
print(doc)
```

```python
Score: 0.23699893057346344

page_content='Table of Contents
FISCAL 2023 NIKE BRAND REVENUE HIGHLIGHTS
The following tables present NIKE Brand revenues disaggregated by reportable operating segment, distribution channel and major product line:
FISCAL 2023 COMPARED TO FISCAL 2022
•NIKE, Inc. Revenues were $51.2 billion in fiscal 2023, which increased 10% and 16% compared to fiscal 2022 on a reported and currency-neutral basis, respectively.
The increase was due to higher revenues in North America, Europe, Middle East & Africa ("EMEA"), APLA and Greater China, which contributed approximately 7, 6,
2 and 1 percentage points to NIKE, Inc. Revenues, respectively.
•NIKE Brand revenues, which represented over 90% of NIKE, Inc. Revenues, increased 10% and 16% on a reported and currency-neutral basis, respectively. This
increase was primarily due to higher revenues in Men's, the Jordan Brand, Women's and Kids' which grew 17%, 35%,11% and 10%, respectively, on a wholesale
equivalent basis.' metadata={'page': 35, 'source': '../example_data/nke-10k-2023.pdf', 'start_index': 0}
```
根据与嵌入查询的相似性返回文档：
```python
# embedding 模型会把文本转换成向量，这是 semantic search 和 RAG 检索的基础。
embedding = embeddings.embed_query("How were Nike's margins impacted in 2023?")

results = vector_store.similarity_search_by_vector(embedding)
print(results[0])
```

```python
page_content='Table of Contents
GROSS MARGIN
FISCAL 2023 COMPARED TO FISCAL 2022
For fiscal 2023, our consolidated gross profit increased 4% to $22,292 million compared to $21,479 million for fiscal 2022. Gross margin decreased 250 basis points to
43.5% for fiscal 2023 compared to 46.0% for fiscal 2022 due to the following:
*Wholesale equivalent
The decrease in gross margin for fiscal 2023 was primarily due to:
•Higher NIKE Brand product costs, on a wholesale equivalent basis, primarily due to higher input costs and elevated inbound freight and logistics costs as well as
product mix;
•Lower margin in our NIKE Direct business, driven by higher promotional activity to liquidate inventory in the current period compared to lower promotional activity in
the prior period resulting from lower available inventory supply;
•Unfavorable changes in net foreign currency exchange rates, including hedges; and
•Lower off-price margin, on a wholesale equivalent basis.
This was partially offset by:' metadata={'page': 36, 'source': '../example_data/nke-10k-2023.pdf', 'start_index': 0}
```
了解更多：

* [API参考](https://reference.langchain.com/python/langchain-core/vectorstores/base/VectorStore)
* [特定于集成的文档](https://docs.langchain.com/oss/python/integrations/vectorstores)

## 4.寻回犬

LangChain [`VectorStore`](https://reference.langchain.com/python/langchain-core/vectorstores/base/VectorStore) 对象不会子类化 [Runnable](https://reference.langchain.com/python/langchain-core/runnables/base/Runnable)。 LangChain [Retrievers](https://reference.langchain.com/python/langchain-core/retrievers/BaseRetriever) 是 Runnables，因此它们实现了一组标准方法（例如，同步和异步 `invoke` 和 `batch` 操作）。尽管我们可以从向量存储构建检索器，但检索器也可以与非向量存储数据源（例如外部 API）进行交互。

我们可以自己创建一个简单版本，无需子类化 `Retriever`。如果我们选择希望使用什么方法来检索文档，我们可以轻松创建一个可运行程序。下面我们将围绕 `similarity_search` 方法构建一个：
```python
from typing import List

from langchain_core.documents import Document
from langchain_core.runnables import chain

@chain
def retriever(query: str) -> List[Document]:
    # vector store 用来保存文本向量和元数据，查询时按语义相似度找回相关片段。
    return vector_store.similarity_search(query, k=1)

retriever.batch(
    [
        "How many distribution centers does Nike have in the US?",
        "When was Nike incorporated?",
    ],
)
```

```text
[[Document(metadata={'page': 4, 'source': '../example_data/nke-10k-2023.pdf', 'start_index': 3125}, page_content='direct to consumer operations sell products through the following number of retail stores in the United States:\nU.S. RETAIL STORES NUMBER\nNIKE Brand factory stores 213 \nNIKE Brand in-line stores (including employee-only stores) 74 \nConverse stores (including factory stores) 82 \nTOTAL 369 \nIn the United States, NIKE has eight significant distribution centers. Refer to Item 2. Properties for further information.\n2023 FORM 10-K 2')],
 [Document(metadata={'page': 3, 'source': '../example_data/nke-10k-2023.pdf', 'start_index': 0}, page_content='Table of Contents\nPART I\nITEM 1. BUSINESS\nGENERAL\nNIKE, Inc. was incorporated in 1967 under the laws of the State of Oregon. As used in this Annual Report on Form 10-K (this "Annual Report"), the terms "we," "us," "our,"\n"NIKE" and the "Company" refer to NIKE, Inc. and its predecessors, subsidiaries and affiliates, collectively, unless the context indicates otherwise.\nOur principal business activity is the design, development and worldwide marketing and selling of athletic footwear, apparel, equipment, accessories and services. NIKE is\nthe largest seller of athletic footwear and apparel in the world. We sell our products through NIKE Direct operations, which are comprised of both NIKE-owned retail stores\nand sales through our digital platforms (also referred to as "NIKE Brand Digital"), to retail accounts and to a mix of independent distributors, licensees and sales')]]
```
Vectorstore 实现了一个 `as_retriever` 方法，该方法将生成一个检索器，特别是一个 [`VectorStoreRetriever`](https://reference.langchain.com/python/langchain-core/vectorstores/base/VectorStoreRetriever)。这些检索器包括特定的 `search_type` 和 `search_kwargs` 属性，用于标识要调用的底层向量存储的哪些方法以及如何参数化它们。例如，我们可以用以下内容复制上面的内容：
```python
# retriever 是检索器，负责根据用户问题从资料库中取回候选文档。
retriever = vector_store.as_retriever(
    search_type="similarity",
    search_kwargs={"k": 1},
)

retriever.batch(
    [
        "How many distribution centers does Nike have in the US?",
        "When was Nike incorporated?",
    ],
)
```

```text
[[Document(metadata={'page': 4, 'source': '../example_data/nke-10k-2023.pdf', 'start_index': 3125}, page_content='direct to consumer operations sell products through the following number of retail stores in the United States:\nU.S. RETAIL STORES NUMBER\nNIKE Brand factory stores 213 \nNIKE Brand in-line stores (including employee-only stores) 74 \nConverse stores (including factory stores) 82 \nTOTAL 369 \nIn the United States, NIKE has eight significant distribution centers. Refer to Item 2. Properties for further information.\n2023 FORM 10-K 2')],
 [Document(metadata={'page': 3, 'source': '../example_data/nke-10k-2023.pdf', 'start_index': 0}, page_content='Table of Contents\nPART I\nITEM 1. BUSINESS\nGENERAL\nNIKE, Inc. was incorporated in 1967 under the laws of the State of Oregon. As used in this Annual Report on Form 10-K (this "Annual Report"), the terms "we," "us," "our,"\n"NIKE" and the "Company" refer to NIKE, Inc. and its predecessors, subsidiaries and affiliates, collectively, unless the context indicates otherwise.\nOur principal business activity is the design, development and worldwide marketing and selling of athletic footwear, apparel, equipment, accessories and services. NIKE is\nthe largest seller of athletic footwear and apparel in the world. We sell our products through NIKE Direct operations, which are comprised of both NIKE-owned retail stores\nand sales through our digital platforms (also referred to as "NIKE Brand Digital"), to retail accounts and to a mix of independent distributors, licensees and sales')]]
```
`VectorStoreRetriever` 支持 `"similarity"`（默认）、`"mmr"`（最大边际相关性，如上所述）和 `"similarity_score_threshold"` 的搜索类型。我们可以使用后者通过相似度分数来对检索器输出的文档进行阈值处理。

检索器可以轻松地合并到更复杂的应用程序中，例如[检索增强生成（RAG）](https://docs.langchain.com/oss/python/langchain/retrieval)应用程序，它将给定的问题与检索到的上下文组合成LLM 的提示。要了解有关构建此类应用程序的更多信息，请查看 [[02-RAG Agent|RAG 教程]] 教程。

## 后续步骤

您现在已经了解了如何在 PDF 文档上构建语义搜索引擎。

有关文档加载器的更多信息：

* [概述](https://docs.langchain.com/oss/python/langchain/retrieval)
* [可用集成](https://docs.langchain.com/oss/python/integrations/document_loaders/)

有关嵌入的更多信息：

* [概述](https://docs.langchain.com/oss/python/langchain/retrieval)
* [可用集成](https://docs.langchain.com/oss/python/integrations/embeddings/)

有关向量存储的更多信息：

* [概述](https://docs.langchain.com/oss/python/langchain/retrieval)
* [可用集成](https://docs.langchain.com/oss/python/integrations/vectorstores/)

有关 RAG 的更多信息，请参阅：

* [构建检索增强生成 (RAG) 应用程序](https://docs.langchain.com/oss/python/langchain/rag/)
