import test from "node:test"
import assert from "node:assert/strict"
import {
  buildRoadmapTable,
  classifyPath,
  ensureTitleAndStripProgress,
  normalizeTableWikilinks,
  normalizeRelativeMarkdownLinks,
  redactMachineSpecificPaths,
  redactVaultRoot,
  transformVaultPaths,
} from "../scripts/prepare-content.mjs"
import {
  localTarget,
  markdownToHtmlPath,
  slugifyPublishedPath,
} from "../scripts/validate-site.mjs"

test("publication policy keeps original layers out and preserves authored layers", () => {
  assert.equal(classifyPath("Python基础/Day01-20/01.初识Python.md", 100).action, "stub")
  assert.equal(classifyPath("Python基础/res/logo.png", 100).action, "exclude")
  assert.equal(classifyPath("Python基础/Agent工程路线/01-基础.md", 100).action, "publish")
  assert.equal(classifyPath("Agentic Design Patterns/01-核心模式/01-提示链.md", 100).action, "stub")
  assert.equal(classifyPath("Agentic Design Patterns/00-初学者路线/01-选择模式.md", 100).action, "publish")
})

test("only allowlisted code, data, and image assets enter staging", () => {
  assert.equal(classifyPath("RAG/examples/demo.py", 100).action, "asset")
  assert.equal(classifyPath("RAG/examples/input.json", 100).action, "asset")
  assert.equal(classifyPath("RAG/examples/data.csv", 100).action, "asset")
  assert.equal(classifyPath("RAG/examples/lab.ipynb", 100).action, "asset")
  assert.equal(classifyPath("RAG/examples/run.sh", 100).action, "asset")
  assert.equal(classifyPath("RAG/examples/events.jsonl", 100).action, "asset")
  assert.equal(classifyPath("RAG/examples/requirements.txt", 100).action, "asset")
  assert.equal(classifyPath("RAG/attachments/diagram.png", 100).action, "asset")
  assert.equal(classifyPath("RAG/credentials.json", 100).action, "exclude")
  assert.equal(classifyPath("RAG/diagram.png", 100).action, "exclude")
  assert.equal(classifyPath("RAG/model.pt", 100).action, "exclude")
  assert.equal(classifyPath("RAG/examples/huge.csv", 2_000_001).action, "exclude")
})

test("vault path transformation skips fenced and inline code", () => {
  const source = [
    "[[Knowledge/AI Agent Engineer/docs/RAG/00-目录|RAG]]",
    "`[[Knowledge/AI Agent Engineer/docs/API/00-目录]]`",
    "```markdown",
    "[[Knowledge/AI Agent Engineer/docs/Git/00-目录]]",
    "```",
  ].join("\n")
  const result = transformVaultPaths(source)
  assert.match(result, /^\[\[RAG\/00-目录\|RAG\]\]/)
  assert.match(result, /`\[\[Knowledge\/AI Agent Engineer\/docs\/API\/00-目录\]\]`/)
  assert.match(result, /```markdown\n\[\[Knowledge\/AI Agent Engineer\/docs\/Git\/00-目录\]\]/)
})

test("staging removes progress metadata and injects a title without touching body text", () => {
  const source = "---\ntags: [demo]\n  \"AI_LEARNING_COMPLETED\": true\n---\n\n# 示例标题\n\n正文"
  const result = ensureTitleAndStripProgress(source, "fallback")
  assert.match(result, /^---\ntitle: "示例标题"/)
  assert.doesNotMatch(result, /ai_learning_completed/)
  assert.match(result, /# 示例标题\n\n正文$/)
})

test("relative Markdown and HTML assets become vault-root paths outside code", () => {
  const source = [
    "[demo](../examples/demo.py)",
    '<img src="../attachments/diagram.png" alt="diagram">',
    "`[keep](../examples/demo.py)`",
  ].join("\n")
  const paths = new Set([
    "RAG/examples/demo.py",
    "RAG/attachments/diagram.png",
  ])
  const result = normalizeRelativeMarkdownLinks(source, "RAG/课程/项目.md", paths)
  assert.match(result, /\(RAG\/examples\/demo\.py\)/)
  assert.match(result, /src="RAG\/attachments\/diagram\.png"/)
  assert.match(result, /`\[keep\]\(\.\.\/examples\/demo\.py\)`/)
})

test("roadmap table preserves all ordered courses", () => {
  const courses = Array.from({ length: 53 }, (_, index) => ({
    name: `课程${index + 1}`,
    stage: `${Math.floor(index / 7) + 1}. 阶段`,
    order: index + 1,
  }))
  const table = buildRoadmapTable(courses)
  assert.equal((table.match(/\[\[/g) ?? []).length, 53)
  assert.match(table, /课程1\/00-目录/)
  assert.match(table, /课程53\/00-目录/)
})

test("table wikilinks escape alias pipes and unwrap link-only code spans", () => {
  const source = [
    "| 顺序 | 课程 |",
    "| --- | --- |",
    "| 1 | [[RAG/01-系统边界|系统边界]] |",
    "| 2 | `[[RAG/02-查询路由|查询路由]]` |",
    "| 3 | [[RAG/03-已转义\\|已转义]] |",
    "正文 [[RAG/04-正文|正文链接]] 不应改写。",
    "```markdown",
    "| 5 | [[RAG/05-代码|代码示例]] |",
    "```",
  ].join("\n")
  const result = normalizeTableWikilinks(source, "RAG/00-目录.md", new Set([
    "RAG/01-系统边界.md",
    "RAG/02-查询路由.md",
    "RAG/03-已转义.md",
  ]))
  assert.match(result, /\[\[RAG\/01-系统边界\\\|系统边界\]\]/)
  assert.match(result, /\[\[RAG\/02-查询路由\\\|查询路由\]\]/)
  assert.doesNotMatch(result, /`\[\[RAG\/02/)
  assert.match(result, /\[\[RAG\/03-已转义\\\|已转义\]\]/)
  assert.match(result, /正文 \[\[RAG\/04-正文\|正文链接\]\] 不应改写/)
  assert.match(result, /```markdown\n\| 5 \| \[\[RAG\/05-代码\|代码示例\]\] \|/)
})

test("table syntax examples stay code when their wikilink targets do not exist", () => {
  const source = "| 语法 | 说明 |\n| --- | --- |\n| `[[路径/笔记|别名]]` | 教学示例 |"
  const result = normalizeTableWikilinks(source, "Markdown/语法.md", new Set(["Markdown/语法.md"]))
  assert.match(result, /`\[\[路径\/笔记\\\|别名\]\]`/)
})

test("public staging redacts the configured vault path without changing generic examples", () => {
  const vaultRoot = "D:\\vaults\\Gao"
  const source = [
    'Set-Location "D:\\vaults\\Gao\\Knowledge\\AI Agent Engineer"',
    "source: D:/vaults/Gao/Knowledge/AI Agent Engineer",
    "example: C:\\Users\\<用户名>",
  ].join("\n")
  const result = redactVaultRoot(source, vaultRoot)
  assert.doesNotMatch(result, /D:[\\/]vaults/i)
  assert.match(result, /X:\\path\\to\\your-vault/)
  assert.match(result, /X:\/path\/to\/your-vault/)
  assert.match(result, /C:\\Users\\<用户名>/)
})

test("default machine-path redaction remains callable for production staging", () => {
  assert.equal(redactMachineSpecificPaths("generic path"), "generic path")
})

test("publication routes match Quartz slugification", () => {
  assert.equal(slugifyPublishedPath("Agent 核心/examples/demo.py"), "Agent-核心/examples/demo.py")
  assert.equal(slugifyPublishedPath("Tool & API/100% ready?.json"), "Tool--and--API/100-percent-ready.json")
  assert.equal(markdownToHtmlPath("Agent Skills/00-目录.md"), "Agent-Skills/00-目录.html")
})

test("site links stay inside the GitHub Pages base path and reject unsafe schemes", () => {
  assert.equal(localTarget("RAG/00-目录.html", "https://example.com"), null)
  assert.deepEqual(localTarget("RAG/00-目录.html", "/AI-Agent-Engineer/API/00-目录"), { target: "API/00-目录" })
  assert.deepEqual(localTarget("RAG/00-目录.html", "../API/00-目录"), { target: "API/00-目录" })
  assert.deepEqual(localTarget("RAG/00-目录.html", "/outside"), { outsideBase: "/outside" })
  assert.deepEqual(localTarget("RAG/00-目录.html", "../../outside"), { outsideBase: "../../outside" })
  assert.deepEqual(localTarget("RAG/00-目录.html", "javascript:alert(1)"), {
    unsupportedScheme: "javascript:alert(1)",
  })
  assert.deepEqual(localTarget("RAG/00-目录.html", "data:text/html,unsafe"), {
    unsupportedScheme: "data:text/html,unsafe",
  })
})
