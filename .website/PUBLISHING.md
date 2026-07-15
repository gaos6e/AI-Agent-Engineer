# 公开发布策略

本项目把 `../docs/` 视为 Obsidian 唯一内容源。构建只读扫描源文件，并将允许公开的副本写入 `.generated/content/`；任何转换都不能回写 `docs/`。

公开仓库为 `gaos6e/AI-Agent-Engineer`。仓库中的 `docs/` 由 `npm run export:repo -- <clone-directory>` 生成，是经过许可、进度、本机路径、凭据和资源白名单检查的发布快照；它不是第二份手工维护的正文。GitHub Actions 只从该快照构建 GitHub Pages，因而许可边界不清晰的本地参考层既不会进入网站，也不会进入公开 Git 历史。

## 默认规则

- 每个允许公开的 Markdown 文档生成一个页面。
- `.py`、`.json`、`.csv`、`.ipynb` 及被允许正文引用的图片作为只读预览/下载资源。
- 进度字段在暂存副本中删除；网站不读取、不显示、不保存学习进度。
- 缓存、凭据、模型、大型数据、Office 文件、字体、编译产物和本机工程状态默认拒绝发布。
- 构建范围默认为拒绝；只有脚本中的明确类型与大小规则可以进入产物。
- 导出完成后会在首次提交前扫描公开克隆中的全部文本、禁止目录、文件大小、符号链接、高置信凭据、本机路径与进度字段；CI 在构建前重复运行同一门禁。

## 完整第三方复刻

以下参考层没有足够的本地再分发许可证据，公开站点不复制其正文或附件：

- `Python基础` 中原 Python-100-Days 完整课程层。
- `Agentic Design Patterns` 中固定 commit 的中文译文、附录、参考资料和附件。

为了不让原创入口页产生断链，构建会为这些 Markdown 生成简短的“未再发布”来源跳转页；跳转页不包含原文。

## 可公开的许可材料

- D2L 中文材料：Apache-2.0，保留来源、许可和改动说明。
- LangChain 官方文档参考层：MIT，保留 `LICENSE-LangChain-docs.md`。
- MCP 官方文档参考层：MIT，保留来源并在第三方声明页记录许可。
- Agent Skills 官方参考层：Apache-2.0，保留 `Copyright 2025 Anthropic, PBC` 与独立上游许可副本；示例 Skill 中声明为 CC0-1.0 的内容按其声明处理。

Quartz、Quartz Community 插件、LangChain 与 MCP 分别保留带各自版权声明的 MIT 文件，不以一份带特定版权人的文本代替其他项目许可。

完整清单和来源会在构建期生成到 `THIRD_PARTY_NOTICES.md`。此策略是保守的工程发布边界，不替代正式法律意见。
