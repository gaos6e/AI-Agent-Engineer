# AI Agent Engineer

从零构建、评测与部署 AI Agent 的中文工程学习站点。内容按 8 个阶段组织为 53 个知识库，同时支持 Obsidian 阅读与公开网页阅读。

- 公开网站：[gaos6e.github.io/AI-Agent-Engineer](https://gaos6e.github.io/AI-Agent-Engineer/)
- 完整路线：`docs/All of AI.md`
- 网站工程：`.website/`
- 部署方式：GitHub Actions + GitHub Pages

## 内容与公开边界

本地 vault 的 `docs/` 是唯一可编辑正文源。发布前，`.website/scripts/prepare-content.mjs` 会生成经过校验的公开快照：

- 发布原创、整理内容及许可证允许公开的参考层；
- 将许可证不明确的完整复刻替换为来源说明页，不上传其正文与附件；
- 移除学习进度字段、本机路径和潜在凭据；
- 只允许白名单内的小型代码、数据与图片资源。

公开仓库中的 `docs/` 是这一流程生成的安全快照；不要把本地完整资料直接复制到公开仓库。

## 本地预览

需要 Node.js 22 或更高版本（本机已验证 Node.js 24）。在 PowerShell 7 中运行：

```powershell
Set-Location ".website"
npm ci
npm run test
npm run build
npm run preview
```

预览地址为 `http://127.0.0.1:8080/AI-Agent-Engineer/`。

首次执行 `npm run build` 会下载固定版本的 Quartz、依赖与插件；网络正常时需要数分钟。只有看到 `Done processing 847 files`，以及最后一行校验中的 `brokenLocalLinks`、`sensitiveLeaks` 等均为 `0`，才表示构建完成。KaTeX 的 Unicode 警告来自已有笔记中的公式写法，不会阻止构建。

需要编辑后自动重建和刷新时，再运行：

```powershell
npm run dev
```

## 设计与技术

网站基于固定提交的 Quartz 5 构建，使用 Obsidian wikilink、全文搜索、深浅主题、响应式课程导航和只读代码资源预览。GSAP 只承担有意义的入场与滚动节奏，并尊重 `prefers-reduced-motion`。网站不包含登录、学习进度或任何写回功能。

设计约束见 `.website/DESIGN.md`，公开内容策略与第三方来源见 `.website/PUBLISHING.md` 和站内 `THIRD_PARTY_NOTICES`。
