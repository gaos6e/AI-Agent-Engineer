---
title: 构建 Content Builder 代理
aliases:
  - Content Builder
  - Build a content builder agent
  - 内容构建器
source: https://docs.langchain.com/oss/python/deepagents/content-builder
source_md: https://docs.langchain.com/oss/python/deepagents/content-builder.md
retrieved: 2026-05-07
tags:
  - langchain
  - python
  - docs/learn
license: MIT
---
# 构建 Content Builder 代理

> 构建一个带品牌记忆、技能、子代理和图像生成能力的内容写作代理。

## 概述

本指南演示如何使用 [Deep Agents](https://docs.langchain.com/oss/python/deepagents) 从零构建一个内容写作代理。

你将构建的代理会：

1. 从 `AGENTS.md` 和 skill 文件夹加载语气与工作流规则
2. 使用 `web_search` 将网络研究委派给专门的 subagent
3. 按已加载的 skill 起草博客或社交媒体内容
4. 使用 Gemini 生成封面或社交图片，并将文件保存到项目目录下

本教程中的代码接入了图像生成工具和文件系统后端，使代理能够在项目目录下读取和写入文章、研究笔记与图片。完整可运行项目见 [content-builder-agent](https://github.com/langchain-ai/deepagents/tree/main/examples/content-builder-agent) 示例。

### 关键概念

本教程涵盖：

* [Long-term memory](https://docs.langchain.com/oss/python/deepagents/long-term-memory)：用于跨会话保存品牌规范、受众信息和用户偏好，让后续内容任务复用经过确认的长期上下文
* [Skills](https://docs.langchain.com/oss/python/deepagents/skills)：用于按需加载写作与发布流程的专门说明，减少主提示词体积并统一执行方式
* [Subagents](https://docs.langchain.com/oss/python/deepagents/subagents)：用于委派研究、编辑等子任务
* [Filesystem backends](https://docs.langchain.com/oss/python/deepagents/backends)：用于文件读写
* 用于搜索和图像生成的自定义 [tools](https://docs.langchain.com/oss/python/langchain/tools)

## 前提条件

需要以下 API 密钥：

* Anthropic（Claude）或其他提供商的 API 密钥
* Google（Gemini），用于通过 `gemini-2.5-flash-image` 生成图像
* [Tavily](https://www.tavily.com/) 用于网络搜索（免费套餐即可）
* [LangSmith](https://smith.langchain.com?utm_source=docs\&utm_medium=cta\&utm_campaign=langsmith-signup\&utm_content=oss-deepagents-content-builder) 用于 tracing（可选）

Python 3.11 或更高版本。

## 设置

### 创建项目目录
```bash
mkdir content-builder-agent
cd content-builder-agent
```

### 安装依赖项
```bash
# 安装依赖：先把示例需要的包安装到当前 Python 环境。
pip install deepagents google-genai pillow pyyaml rich tavily-python langchain
```

```bash
uv init
# 安装依赖：先把示例需要的包安装到当前 Python 环境。
uv add deepagents google-genai pillow pyyaml rich tavily-python langchain
uv sync
```

在你自己的项目中，将 `deepagents` 固定到受支持的版本范围（例如 `>=0.3.5,<0.4.0`），以匹配上游示例。

### 设置 API 密钥
```bash
# 配置环境变量：示例会从环境变量读取 API key、模型名或服务地址。
export ANTHROPIC_API_KEY="your_anthropic_api_key"
export GOOGLE_API_KEY="your_google_api_key"
export TAVILY_API_KEY="your_tavily_api_key"           # Optional
export LANGSMITH_API_KEY="your_langsmith_api_key"     # Optional
```

## 添加配置文件

该示例把行为配置放在三类文件中：memory、skills 和 subagent 定义。

### 添加 AGENTS.md
在项目根目录创建 `AGENTS.md`。
稍后创建代理并把该文件作为 [memory](https://docs.langchain.com/oss/python/deepagents/long-term-memory) 参数的一部分传入时，它会被加载到 system prompt 中，使品牌语气和研究要求应用到每次运行。

```markdown
# Content Writer Agent

You are a content writer for a technology company. Your job is to create engaging, informative content that educates readers about AI, software development, and emerging technologies.

## Brand Voice

- **Professional but approachable**: Write like a knowledgeable colleague, not a textbook
- **Clear and direct**: Avoid jargon unless necessary; explain technical concepts simply
- **Confident but not arrogant**: Share expertise without being condescending
- **Engaging**: Use concrete examples, analogies, and stories to illustrate points

## Writing Standards

1. **Use active voice**: "The agent processes requests" not "Requests are processed by the agent"
2. **Lead with value**: Start with what matters to the reader, not background
3. **One idea per paragraph**: Keep paragraphs focused and scannable
4. **Concrete over abstract**: Use specific examples, numbers, and case studies
5. **End with action**: Every piece should leave the reader knowing what to do next

## Content Pillars

Our content focuses on:
- AI agents and automation
- Developer tools and productivity
- Software architecture and best practices
- Emerging technologies and trends

## Formatting Guidelines

- Use headers (H2, H3) to break up long content
- Include code examples where relevant (with syntax highlighting)
- Add bullet points for lists of 3+ items
- Keep sentences under 25 words when possible
- Include a clear call-to-action at the end

## Research Requirements

Before writing on any topic:
1. Use the `researcher` subagent for in-depth topic research
2. Gather at least 3 credible sources
3. Identify the key points readers need to understand
4. Find concrete examples or case studies to illustrate concepts
```

若要让代理遵循你自己的语气、内容支柱和格式规则，请更新 `AGENTS.md` 中的文本。

### 添加 subagents.yaml
创建一个名为 `subagents.yaml` 的文件。
然后添加以下内容。它定义了一个 `researcher` subagent，配有基于 Tavily 的 `web_search` 工具、一个 Haiku 模型 ID，并要求在主代理委派任务时，把研究结果保存到你指定的路径：

```yaml
# subagent 定义。
# 这些配置会由 content_writer.py 加载，并和 tools 连接起来。

researcher:
  description: >
    ALWAYS use this first to research any topic before writing content.
    Searches the web for current information, statistics, and sources.
    When delegating, tell it the topic AND the file path to save results
    (e.g., 'Research renewable energy and save to research/renewable-energy.md').
  model: anthropic:claude-haiku-4-5-20251001
  system_prompt: |
    You are a research assistant. You have access to web_search and write_file tools.

    ## Your Tools
    - web_search(query, max_results=5, topic="general") - Search the web
    - write_file(file_path, content) - Save your findings

    ## Your Process
    1. Use web_search to find information on the topic
    2. Make 2-3 targeted searches with specific queries
    3. Gather key statistics, quotes, and examples
    4. Save findings to the file path specified in your task

    ## Important
    - The user will tell you WHERE to save the file - use that exact path
    - Always include source URLs in your findings
    - Keep findings concise but informative
  tools:
    - web_search
```

稍后创建 deep agent 时会把这个文件作为参数传入。

### 添加 skills
创建 `skills/` 目录。每个 skill 都是一个文件夹，里面包含带 YAML frontmatter（`name`、`description`）和 skill 指令的 `SKILL.md` 文件。

创建 `skills/blog-post/SKILL.md`，并复制以下内容。它说明如何创建长文、优化 SEO 内容，以及生成封面图片。

````md
---
name: blog-post
description: Writes and structures long-form blog posts, creates tutorial outlines, and optimizes content for SEO with cover image generation. Use when the user asks to write a blog post, article, how-to guide, tutorial, technical writeup, thought leadership piece, or long-form content.
---

# Blog Post Writing Skill

## Research First (Required)

**Before writing any blog post, you MUST delegate research:**

1. Use the `task` tool with `subagent_type: "researcher"`
2. In the description, specify BOTH the topic AND where to save:

```
task(
    subagent_type="researcher",
    description="Research [TOPIC]. Save findings to research/[slug].md"
)
```

Example:
```
task(
    subagent_type="researcher",
    description="Research the current state of AI agents in 2025. Save findings to research/ai-agents-2025.md"
)
```

3. After research completes, read the findings file before writing

## Output Structure (Required)

**Every blog post MUST have both a post AND a cover image:**

```
blogs/
└── <slug>/
    ├── post.md        # The blog post content
    └── hero.png       # REQUIRED: Generated cover image
```

Example: A post about "AI Agents in 2025" → `blogs/ai-agents-2025/`

**You MUST complete both steps:**
1. Write the post to `blogs/<slug>/post.md`
2. Generate a cover image using `generate_image` and save to `blogs/<slug>/hero.png`

**A blog post is NOT complete without its cover image.**

## Blog Post Structure

Every blog post should follow this structure:

### 1. Hook (Opening)
- Start with a compelling question, statistic, or statement
- Make the reader want to continue
- Keep it to 2-3 sentences

### 2. Context (The Problem)
- Explain why this topic matters
- Describe the problem or opportunity
- Connect to the reader's experience

### 3. Main Content (The Solution)
- Break into 3-5 main sections with H2 headers
- Each section covers one key point
- Include code examples, diagrams, or screenshots where helpful
- Use bullet points for lists

### 4. Practical Application
- Show how to apply the concepts
- Include step-by-step instructions if applicable
- Provide code snippets or templates

### 5. Conclusion & CTA
- Summarize key takeaways (3 bullets max)
- End with a clear call-to-action
- Link to related resources

## Cover Image Generation

After writing the post, generate a cover image using the `generate_cover` tool:

```
generate_cover(prompt="A detailed description of the image...", slug="your-blog-slug")
```

The tool saves the image to `blogs/<slug>/hero.png`.

### Writing Effective Image Prompts

Structure your prompt with these elements:

1. **Subject**: What is the main focus? Be specific and concrete.
2. **Style**: Art direction (minimalist, isometric, flat design, 3D render, watercolor, etc.)
3. **Composition**: How elements are arranged (centered, rule of thirds, symmetrical)
4. **Color palette**: Specific colors or mood (warm earth tones, cool blues and purples, high contrast)
5. **Lighting/Atmosphere**: Soft diffused light, dramatic shadows, golden hour, neon glow
6. **Technical details**: Aspect ratio considerations, negative space for text overlay

### Example Prompts

**For a technical blog post:**
```
Isometric 3D illustration of interconnected glowing cubes representing AI agents, each cube has subtle circuit patterns. Cubes connected by luminous data streams. Deep navy background (#0a192f) with electric blue (#64ffda) and soft purple (#c792ea) accents. Clean minimal style, lots of negative space at top for title. Professional tech aesthetic.
```

**For a tutorial/how-to:**
```
Clean flat illustration of hands typing on a keyboard with abstract code symbols floating upward, transforming into lightbulbs and gears. Warm gradient background from soft coral to light peach. Friendly, approachable style. Centered composition with space for text overlay.
```

**For thought leadership:**
```
Abstract visualization of a human silhouette profile merging with geometric neural network patterns. Split composition - organic watercolor texture on left transitioning to clean vector lines on right. Muted sage green and warm terracotta color scheme. Contemplative, forward-thinking mood.
```

## SEO Considerations

- Include the main keyword in the title and first paragraph
- Use the keyword naturally 3-5 times throughout
- Keep the title under 60 characters
- Write a meta description (150-160 characters)

## Quality Checklist

Before finishing:
- [ ] Post saved to `blogs/<slug>/post.md`
- [ ] Hero image generated at `blogs/<slug>/hero.png`
- [ ] Hook grabs attention in first 2 sentences
- [ ] Each section has a clear purpose
- [ ] Conclusion summarizes key points
- [ ] CTA tells reader what to do next
````

接下来创建 `skills/social-media/SKILL.md`，并复制以下内容。它说明如何起草社交媒体帖子并生成配套图片：

````md
---
name: social-media
description: Drafts engaging social media posts, writes hooks, suggests hashtags, creates thread structures, and generates companion images. Use when the user asks to write a LinkedIn post, tweet, Twitter/X thread, social media caption, social post, or repurpose content for social platforms.
---

# Social Media Content Skill

## Research First (Required)

**Before writing any social media content, you MUST delegate research:**

1. Use the `task` tool with `subagent_type: "researcher"`
2. In the description, specify BOTH the topic AND where to save:

```
task(
    subagent_type="researcher",
    description="Research [TOPIC]. Save findings to research/[slug].md"
)
```

Example:
```
task(
    subagent_type="researcher",
    description="Research renewable energy trends in 2025. Save findings to research/renewable-energy.md"
)
```

3. After research completes, read the findings file before writing

## Output Structure (Required)

**Every social media post MUST have both content AND an image:**

**LinkedIn posts:**
```
linkedin/
└── <slug>/
    ├── post.md        # The post content
    └── image.png      # REQUIRED: Generated visual
```

**Twitter/X threads:**
```
tweets/
└── <slug>/
    ├── thread.md      # The thread content
    └── image.png      # REQUIRED: Generated visual
```

Example: A LinkedIn post about "prompt engineering" → `linkedin/prompt-engineering/`

**You MUST complete both steps:**
1. Write the content to the appropriate path
2. Generate an image using `generate_image` and save alongside the post

**A social media post is NOT complete without its image.**

## Platform Guidelines

### LinkedIn

**Format:**
- 1,300 character limit (show more after ~210 chars)
- First line is crucial - make it hook
- Use line breaks for readability
- 3-5 hashtags at the end

**Tone:**
- Professional but personal
- Share insights and learnings
- Ask questions to drive engagement
- Use "I" and share experiences

**Structure:**
```
[Hook - 1 compelling line]

[Empty line]

[Context - why this matters]

[Empty line]

[Main insight - 2-3 short paragraphs]

[Empty line]

[Call to action or question]

#hashtag1 #hashtag2 #hashtag3
```

### Twitter/X

**Format:**
- 280 character limit per tweet
- Threads for longer content (use 1/🧵 format)
- No more than 2 hashtags per tweet

**Thread Structure:**
```
1/🧵 [Hook - the main insight]

2/ [Supporting point 1]

3/ [Supporting point 2]

4/ [Example or evidence]

5/ [Conclusion + CTA]
```

## Image Generation

Every social media post needs an eye-catching image. Use the `generate_social_image` tool:

```
generate_social_image(prompt="A detailed description...", platform="linkedin", slug="your-post-slug")
```

The tool saves the image to `<platform>/<slug>/image.png`.

### Social Image Best Practices

Social images need to work at small sizes in crowded feeds:
- **Bold, simple compositions** - one clear focal point
- **High contrast** - stands out when scrolling
- **No text in image** - too small to read, platforms add their own
- **Square or 4:5 ratio** - works across platforms

### Writing Effective Prompts

Include these elements:

1. **Single focal point**: One clear subject, not a busy scene
2. **Bold style**: Vibrant colors, strong shapes, high contrast
3. **Simple background**: Solid color, gradient, or subtle texture
4. **Mood/energy**: Match the post tone (inspiring, urgent, thoughtful)

### Example Prompts

**For an insight/tip post:**
```
Single glowing lightbulb floating against a deep purple gradient background, lightbulb made of interconnected golden geometric lines, rays of soft light emanating outward. Minimal, striking, high contrast. Square composition.
```

**For announcements/news:**
```
Abstract rocket ship made of colorful geometric shapes launching upward with a trail of particles. Bright coral and teal color scheme against clean white background. Energetic, celebratory mood. Bold flat illustration style.
```

**For thought-provoking content:**
```
Two overlapping translucent circles, one blue one orange, creating a glowing intersection in the center. Represents collaboration or intersection of ideas. Dark charcoal background, soft ethereal glow. Minimalist and contemplative.
```

## Content Types

### Announcement Posts
- Lead with the news
- Explain the impact
- Include link or next step

### Insight Posts
- Share one specific learning
- Explain the context briefly
- Make it actionable

### Question Posts
- Ask a genuine question
- Provide your take first
- Keep it focused on one topic

## Quality Checklist

Before finishing:
- [ ] Post saved to `linkedin/<slug>/post.md` or `tweets/<slug>/thread.md`
- [ ] Image generated alongside the post
- [ ] First line hooks attention
- [ ] Content fits platform limits
- [ ] Tone matches platform norms
- [ ] Has clear CTA or question
- [ ] Hashtags are relevant (not generic)
````

这些 skill 会指示代理先调用 `researcher` subagent，再把 Markdown 写入 `blogs/`、`linkedin/` 或 `tweets/`，并调用 `generate_cover` 或 `generate_social_image` 生成图片。

稍后创建代理并指定 skills 文件夹时，这些 skill 文件夹内 `SKILL.md` 的 frontmatter 会被加载进 system prompt，使代理能够在任务匹配 skill 描述时使用对应 skill。

## 构建脚本

在项目根目录创建 `content_writer.py`。下面几个部分应按顺序放在同一个文件中。

### 添加工具
`researcher` subagent 使用 Tavily 搜索。
博客和社交媒体工作流使用 Gemini 图像生成。
稍后创建代理时，`load_subagents` 函数会读取 `subagents.yaml`，并把工具名称解析为这些带装饰器的函数。

```python
import os
from pathlib import Path
from typing import Literal

import yaml
from langchain.tools import tool

EXAMPLE_DIR = Path(__file__).parent


# 使用 @tool 可以把普通 Python 函数暴露给 agent，模型会根据函数名、参数和 docstring 判断何时调用。
@tool
def web_search(
    query: str,
    max_results: int = 5,
    topic: Literal["general", "news"] = "general",
) -> dict:
    """Search the web for current information.

    Args:
        query: The search query (be specific and detailed)
        max_results: Number of results to return (default: 5)
        topic: "general" for most queries, "news" for current events

    Returns:
        Search results with titles, URLs, and content excerpts.
    """
    try:
        from tavily import TavilyClient

        api_key = os.environ.get("TAVILY_API_KEY")
        if not api_key:
            return {"error": "TAVILY_API_KEY not set"}

        client = TavilyClient(api_key=api_key)
        return client.search(query, max_results=max_results, topic=topic)
    except Exception as e:
        return {"error": f"Search failed: {e}"}


@tool
def generate_cover(prompt: str, slug: str) -> str:
    """Generate a cover image for a blog post.

    Args:
        prompt: Detailed description of the image to generate.
        slug: Blog post slug. Image saves to blogs/<slug>/hero.png
    """
    try:
        from google import genai

        client = genai.Client()
        response = client.models.generate_content(
            model="gemini-2.5-flash-image",
            contents=[prompt],
        )

        for part in response.parts:
            if part.inline_data is not None:
                image = part.as_image()
                output_path = EXAMPLE_DIR / "blogs" / slug / "hero.png"
                output_path.parent.mkdir(parents=True, exist_ok=True)
                image.save(str(output_path))
                return f"Image saved to {output_path}"

        return "No image generated"
    except Exception as e:
        return f"Error: {e}"


@tool
def generate_social_image(prompt: str, platform: str, slug: str) -> str:
    """Generate an image for a social media post.

    Args:
        prompt: Detailed description of the image to generate.
        platform: Either "linkedin" or "tweets"
        slug: Post slug. Image saves to <platform>/<slug>/image.png
    """
    try:
        from google import genai

        client = genai.Client()
        response = client.models.generate_content(
            model="gemini-2.5-flash-image",
            contents=[prompt],
        )

        for part in response.parts:
            if part.inline_data is not None:
                image = part.as_image()
                output_path = EXAMPLE_DIR / platform / slug / "image.png"
                output_path.parent.mkdir(parents=True, exist_ok=True)
                image.save(str(output_path))
                return f"Image saved to {output_path}"

        return "No image generated"
    except Exception as e:
        return f"Error: {e}"


def load_subagents(config_path: Path) -> list:
    """Load subagent definitions from YAML and wire up tools.

    Unlike `memory` and `skills`, deep agents do not load subagents from files by default.
    This helper externalizes configuration so you can edit YAML without changing Python code.
    """
    available_tools = {
        "web_search": web_search,
    }

    with open(config_path) as f:
        config = yaml.safe_load(f)

    # subagents 用来把专门任务委托给独立提示词和工具集合，减轻主 agent 的负担。
    subagents = []
    for name, spec in config.items():
        subagent = {
            "name": name,
            "description": spec["description"],
            "system_prompt": spec["system_prompt"],
        }
        if "model" in spec:
            subagent["model"] = spec["model"]
        if "tools" in spec:
            subagent["tools"] = [available_tools[t] for t in spec["tools"]]
        subagents.append(subagent)

    return subagents
```

### 创建代理
用 [create\_deep\_agent](https://reference.langchain.com/python/deepagents/graph/create_deep_agent) 创建 deep agent 时，传入 memory 路径、skills 目录、图像工具、来自 YAML 的 subagents，以及以示例目录为根的 [FilesystemBackend](https://docs.langchain.com/oss/python/deepagents/backends)，这样 `./AGENTS.md` 和 `./skills/` 之类路径才能正确解析。

```python
from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend


def create_content_writer():
    """Create a content writer agent configured by filesystem files."""
    # create_deep_agent 会创建具备规划、文件系统和 subagents 能力的 Deep Agent。
    return create_deep_agent(
        model="google_genai:gemini-3.1-pro-preview",
        memory=["./AGENTS.md"],
        skills=["./skills/"],
        tools=[generate_cover, generate_social_image],
        # subagents 用来把专门任务委托给独立提示词和工具集合，减轻主 agent 的负担。
        subagents=load_subagents(EXAMPLE_DIR / "subagents.yaml"),
        backend=FilesystemBackend(root_dir=EXAMPLE_DIR),
    )
```

```python
from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend


def create_content_writer():
    """Create a content writer agent configured by filesystem files."""
    # create_deep_agent 会创建具备规划、文件系统和 subagents 能力的 Deep Agent。
    return create_deep_agent(
        model="openai:gpt-5.4",
        memory=["./AGENTS.md"],
        skills=["./skills/"],
        tools=[generate_cover, generate_social_image],
        # subagents 用来把专门任务委托给独立提示词和工具集合，减轻主 agent 的负担。
        subagents=load_subagents(EXAMPLE_DIR / "subagents.yaml"),
        backend=FilesystemBackend(root_dir=EXAMPLE_DIR),
    )
```

```python
from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend


def create_content_writer():
    """Create a content writer agent configured by filesystem files."""
    # create_deep_agent 会创建具备规划、文件系统和 subagents 能力的 Deep Agent。
    return create_deep_agent(
        model="anthropic:claude-sonnet-4-6",
        memory=["./AGENTS.md"],
        skills=["./skills/"],
        tools=[generate_cover, generate_social_image],
        # subagents 用来把专门任务委托给独立提示词和工具集合，减轻主 agent 的负担。
        subagents=load_subagents(EXAMPLE_DIR / "subagents.yaml"),
        backend=FilesystemBackend(root_dir=EXAMPLE_DIR),
    )
```

```python
from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend


def create_content_writer():
    """Create a content writer agent configured by filesystem files."""
    # create_deep_agent 会创建具备规划、文件系统和 subagents 能力的 Deep Agent。
    return create_deep_agent(
        model="openrouter:anthropic/claude-sonnet-4-6",
        memory=["./AGENTS.md"],
        skills=["./skills/"],
        tools=[generate_cover, generate_social_image],
        # subagents 用来把专门任务委托给独立提示词和工具集合，减轻主 agent 的负担。
        subagents=load_subagents(EXAMPLE_DIR / "subagents.yaml"),
        backend=FilesystemBackend(root_dir=EXAMPLE_DIR),
    )
```

```python
from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend


def create_content_writer():
    """Create a content writer agent configured by filesystem files."""
    # create_deep_agent 会创建具备规划、文件系统和 subagents 能力的 Deep Agent。
    return create_deep_agent(
        model="fireworks:accounts/fireworks/models/qwen3p5-397b-a17b",
        memory=["./AGENTS.md"],
        skills=["./skills/"],
        tools=[generate_cover, generate_social_image],
        # subagents 用来把专门任务委托给独立提示词和工具集合，减轻主 agent 的负担。
        subagents=load_subagents(EXAMPLE_DIR / "subagents.yaml"),
        backend=FilesystemBackend(root_dir=EXAMPLE_DIR),
    )
```

```python
from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend


def create_content_writer():
    """Create a content writer agent configured by filesystem files."""
    # create_deep_agent 会创建具备规划、文件系统和 subagents 能力的 Deep Agent。
    return create_deep_agent(
        model="baseten:zai-org/GLM-5",
        memory=["./AGENTS.md"],
        skills=["./skills/"],
        tools=[generate_cover, generate_social_image],
        # subagents 用来把专门任务委托给独立提示词和工具集合，减轻主 agent 的负担。
        subagents=load_subagents(EXAMPLE_DIR / "subagents.yaml"),
        backend=FilesystemBackend(root_dir=EXAMPLE_DIR),
    )
```

```python
from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend


def create_content_writer():
    """Create a content writer agent configured by filesystem files."""
    # create_deep_agent 会创建具备规划、文件系统和 subagents 能力的 Deep Agent。
    return create_deep_agent(
        model="ollama:devstral-2",
        memory=["./AGENTS.md"],
        skills=["./skills/"],
        tools=[generate_cover, generate_social_image],
        # subagents 用来把专门任务委托给独立提示词和工具集合，减轻主 agent 的负担。
        subagents=load_subagents(EXAMPLE_DIR / "subagents.yaml"),
        backend=FilesystemBackend(root_dir=EXAMPLE_DIR),
    )
```

### 添加入口点
用一条用户消息调用代理，验证它能够正常工作：

```python
import sys

from langchain.messages import HumanMessage

if __name__ == "__main__":
    task = (
        " ".join(sys.argv[1:])
        if len(sys.argv) > 1
        else "Write a blog post about how AI agents are transforming software development"
    )

    agent = create_content_writer()
    # 这里是实际运行入口：传入 messages 或 state 后，系统会执行推理、工具调用和状态更新。
    result = agent.invoke(
        {"messages": [HumanMessage(content=task)]},
        config={"configurable": {"thread_id": "content-builder-demo"}},
    )

    for msg in result.get("messages", []):
        if hasattr(msg, "content") and msg.content:
            print(msg.content)
```

## 运行代理

> [!warning]
>   The filesystem backend can read, write, and delete files under `root_dir`. Run only in a dedicated directory and review generated content before publishing.

在项目目录中，你可以不传参数直接调用代理，也可以把 prompt 作为参数传入：

```bash
# 运行示例脚本：执行前请确认依赖、环境变量和当前工作目录都已准备好。
python content_writer.py
```

```bash
# 运行示例脚本：执行前请确认依赖、环境变量和当前工作目录都已准备好。
python content_writer.py Write a blog post about prompt engineering
```

设置 `LANGSMITH_API_KEY` 后，可以在 [LangSmith](https://docs.langchain.com/langsmith/home) 中检查运行记录。

## 输出

成功运行后，生成产物会写入系统临时目录（在 macOS 和 Linux 上通常位于 `/tmp/`），而不是写在项目文件旁边。

```text
blogs/
└── prompt-engineering/
    ├── post.md
    └── hero.png
research/
└── prompt-engineering.md
```

路径遵循 `SKILL.md` 中的 skill 指令。

## 完整代码

可在 GitHub 浏览完整的 [content-builder-agent example](https://github.com/langchain-ai/deepagents/tree/main/examples/content-builder-agent)，其中包括基于 Rich 的 streaming UI。

## 后续步骤

* 编辑 `AGENTS.md` 以修改品牌语气和研究要求
* 在 `skills/<name>/SKILL.md` 下为新的内容类型添加 skills
* 在 `subagents.yaml` 中添加 subagents，并在 `load_subagents` 中注册工具
* 阅读 [Subagents](https://docs.langchain.com/oss/python/deepagents/subagents)、[Skills](https://docs.langchain.com/oss/python/deepagents/skills) 和 [Customization](https://docs.langchain.com/oss/python/deepagents/customization)，了解更深入的配置方式

***
