# 公开发布策略

本项目以 `../docs-CN/` 作为权威中文 Obsidian 内容源，并以 `../docs-EN/` 保存一一对应的英文内容。构建只读扫描两个源目录，并将允许公开的副本分别写入 `.generated/content/zh-CN/` 与 `.generated/content/en/`；任何转换都不能回写任一源目录。

公开仓库为 `gaos6e/AI-Agent-Engineer`。仓库中的 `docs-CN/` 与 `docs-EN/` 由 `npm run export:repo -- <clone-directory>` 生成，是经过许可、进度、本机路径、凭据和资源白名单检查的发布快照；它们不是第二份手工维护的正文。GitHub Actions 只从这些安全快照构建 GitHub Pages，因而许可边界不清晰的本地参考层既不会进入网站，也不会进入公开 Git 历史。

## 双语发布门禁

- 每个中文 Markdown 必须恰好对应一个英文 Markdown。英文源以根级 `translation_key` 指向其中文相对路径，以 `translation_source_hash` 记录当前中文源的 SHA-256，并声明 `lang: en`。缺页、重复映射、哈希过期或课程元数据不一致时，`npm run build` 必须失败，不得只发布单语站点。
- 中文路径保持旧 URL 所需的稳定性；英文路径使用自然的英文目录和文件名。构建分别输出 `/zh-CN/` 与 `/en/`，根路径默认跳转到 `/zh-CN/`，旧无语言前缀页面和 aliases 永久跳转到对应中文页面。
- 每个已发布页面都生成自己的 canonical URL，并声明中英文 `hreflang` 与 `x-default`。两个语言站点各自生成 sitemap、RSS、搜索索引和运行时静态资源。
- 英文不得以未核验的逐句机器直译替代技术写作。翻译须保留事实、引用、许可证、API/协议名和产品名；术语遵循 `.website/config/translation-glossary.yaml`。真正存在歧义时暂停该页并向维护者确认，不以猜测绕过门禁。
- 第三方材料的英文版默认生成来源跳转页，而非再分发或翻译其完整正文；只有完成独立的逐页许可核验后才可收紧该规则。

## 默认规则

- 每个允许公开的 Markdown 文档生成一个页面。
- `.py`、`.json`、`.csv`、`.ipynb` 及被允许正文引用的图片作为只读预览/下载资源。
- 进度字段在暂存副本中删除；网站不读取、不显示、不保存学习进度。
- 缓存、凭据、模型、大型数据、Office 文件、字体、编译产物和本机工程状态默认拒绝发布。
- 构建范围默认为拒绝；只有脚本中的明确类型与大小规则可以进入产物。
- 导出完成后会在首次提交前扫描公开克隆中的全部文本、禁止目录、文件大小、符号链接、高置信凭据、本机路径与进度字段；CI 在构建前重复运行同一门禁。

## 学习路线元数据门禁

57 门顶层课程必须全部声明 `ai_learning_schema: 2`，并提供唯一稳定 ID、受控 domain、唯一 catalog order 和显式硬前置列表；角色路径中的 order/kind 必须成对出现且在角色内唯一。构建会校验未知字段、类型、依赖存在性、自环/全图环、同角色前置可见且更早，以及 core 课程的 core 前置闭包。任何入口退回 legacy、拼错字段或破坏闭包都会失败关闭。

`docs-CN/All of AI.md` 在 Obsidian 中保留唯一的可勾选 Dataview 课程地图，并直接保存四条角色清单；`docs-EN/all-of-ai.md` 保留对应的英文静态快照。构建会由同一 YAML AST 解析结果生成并校验两个语言的静态知识域表与角色清单；元数据变化而任一语言路线未同步时不会静默发布旧路线。Homepage 和 CourseNavigator 只消费 v2 domain、catalog order 与 track；旧 `ai_learning_stage/order` 只为本地交互地图保留，不驱动公开导航，`ai_learning_completed` 也会在发布时移除。

## 内容来源元数据门禁

`content_origin` 与 `content_status` 的定义见 `docs-CN/维护记录/内容质量与来源标记规范.md`。普通历史页面可以暂不填写，缺失只表示“尚未分类”，不能据此推断为原创或已验证；但已登记的冻结上游参考树（当前包括 `深度学习`、LangChain 官方参考层、MCP 官方参考层和 Agent Skills 官方参考层）实行更严格的 fail-closed 规则：逐页必须为 `content_origin: third-party` 与 `content_status: frozen-reference`，仅把 frontmatter 改成 `original`、`curated` 或 `mixed` 不能释放镜像正文；真正独立重写的内容通常必须移出冻结树。留在冻结树中的罕见例外，必须同时经过逐文件原创来源审阅、使用 `content_origin: original` 与 `content_status: validated`，并由脚本的精确路径和测试放行，不能以目录前缀或仅改 frontmatter 放宽。深度学习树既有的精确本地入口例外是 `00-目录.md` 与 `00-来源与目录.md`；本轮新增例外仅为 `00-工程实践与现代化路线.md` 及其两份零依赖训练合同示例。它们不是 D2L 镜像，其他深度学习页面继续失败关闭。明确标为 `needs-review` 的第三方参考页会生成说明已知质量问题的专用 stub，不会退化成含混的“元数据缺失”提示。后续应逐个知识库、逐个章节补齐来源和许可证，再恢复完整发布。一旦填写，构建会校验受控枚举，空值、重复字段和未知值都会令构建失败。构建使用固定版本的 YAML AST 解析器核对 frontmatter 语义；解析错误、重复键、merge key，以及作为映射键的 alias/复杂节点会失败关闭。`content_origin`、`content_status`、`reference_layer_status`、`license`、`source_url`、`attribution` 与 `local_changes` 必须写成根级、非缩进的块式 `key: value`；flow mapping、缩进/序列映射、治理键上的 tag/anchor、转义或折叠显式键，以及解码后包含控制字符的值都会失败。无关字段的普通 alias value 不属于治理字段门禁范围。

通用规则只在页面明确标为 `content_origin: third-party` 时生效。第三方页必须提供绝对的 HTTP(S) `source_url`，且 URL 不能嵌入 username/password；stub 只输出解析器规范化并做 Markdown 安全编码后的 URL。公开正文必须同时匹配脚本中已登记的本地页与规范化上游 origin/path、该项目允许的许可证，以及构建时复制的本地许可声明；任意 URL 加 `license: MIT` 不会放行。`MIT`、`Apache-2.0`、`CC-BY-4.0`、`CC0-1.0` 许可白名单只是必要条件，不是充分条件；未登记来源、来源与许可证错配、许可证缺失/未知/专有/拼写错误或未进入白名单时，公开层都会把正文替换为来源跳转页。CC BY 4.0 页面还必须用根级单行 `attribution` 保留上游署名，并用 `local_changes` 明确翻译、整理或格式变更；生成期会把来源、许可、署名和改动说明作为可见 callout 注入正文，而不是依赖被隐藏的 properties。Agent Skills 当前进一步要求 8 个本地页各自绑定精确官网路径、无 query/fragment、固定项目署名与固定中文翻译改动声明；许可全文按固定 SHA256 验证。缺少任一项继续生成 stub。新增来源或许可证必须先核对再分发条件、署名/NOTICE 要求与许可副本，再更新显式注册表，不能只填任意非空字符串绕过门禁。`mixed` 入口不会被整页拦截，因为页面级许可证不能代表其所有组成部分；其中的第三方材料仍应拆分为独立页面或逐段注明边界。

当前来源注册表只覆盖下文已经列入第三方声明的 D2L 中文版、LangChain 文档、MCP 已归档旧文档仓库、Agent Skills 精确页面与 Requests 文档；域名相同但仓库路径不同的内容不会继承登记。注册表是发布许可门禁，不是来源真实性证明，页面内容与所填来源是否一致仍需逐页人工核验。

许可证字段只是维护声明，不是许可证真实性证明，也不替代上游许可文件、署名/NOTICE 等条件和人工核验。若通用来源跳转页所在的顶层课程仍有按资源白名单会公开的附件、图片、示例代码或数据，构建会失败，而不会静默发布这些资源；维护者必须先把参考层隔离到独立顶层目录，或为该范围增加经过核验的显式发布策略。

## 完整第三方复刻

以下参考层没有足够的本地再分发许可证据，公开站点不复制其正文或附件：

- `Python基础` 中原 Python-100-Days 完整课程层。
- `Agentic Design Patterns` 中固定 commit 的中文译文、附录、参考资料和附件。

为了不让原创入口页产生断链，构建会为这些 Markdown 生成简短的“未再发布”来源跳转页；跳转页不包含原文。

## 可公开的许可材料

- D2L 中文材料：Apache-2.0，保留来源、许可和改动说明。
- LangChain 官方文档参考层：MIT，保留 `LICENSE-LangChain-docs.md`。
- MCP 已归档旧文档仓库：MIT；2026-01-05 许可切换后的新单仓库文档通常涉及 CC BY 4.0，而跨切换历史的页面可能同时包含旧 MIT 与新许可贡献。当前官网 URL 不继承旧仓库 MIT 登记；没有逐页提交历史和许可证明时继续生成 stub。
- Agent Skills 官方**文档**参考层：CC BY 4.0，保留 Agent Skills 项目署名、原始页面链接、许可副本和本地改动说明；仓库代码的 Apache-2.0 不能替代文档许可证。示例 Skill 中明确声明为 CC0-1.0 的内容按其声明处理。

`Agent Skills/examples/` 不是整目录白名单；只有当前已经审阅的五个教学文件可进入公开层，新增 Markdown、代码或数据默认排除，必须逐项核验后再登记。未再复制的 `.website/legal/Agent-Skills-Apache-2.0.txt` 仅保留为上游代码许可证对照，不代表网站文档许可。

Quartz、Quartz Community 插件、LangChain 与 MCP 已归档旧文档仓库分别保留带各自版权声明的 MIT 文件，不以一份带特定版权人的文本代替其他项目许可；构建期 `yaml@2.9.0` 依赖按其 ISC License 记录在第三方声明页。

完整清单和来源会在构建期生成到 `THIRD_PARTY_NOTICES.md`。浏览器运行时的 Mermaid 固定为 lockfile 中的 11.16.0，并由构建脚本复制成同源 `static/mermaid.esm.min.mjs` 及其 ESM chunks；校验器同时核对完整模块集合与文件摘要，并禁止 HTML 回退到 cdnjs Mermaid 加载器。此策略是保守的工程发布边界，不替代正式法律意见。
