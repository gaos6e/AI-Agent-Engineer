import { createHash } from "node:crypto"
import {
  copyFile,
  mkdir,
  readFile,
  readdir,
  rm,
  stat,
  utimes,
  writeFile,
} from "node:fs/promises"
import path from "node:path"
import { fileURLToPath, pathToFileURL } from "node:url"
import { HIGH_CONFIDENCE_SECRET_PATTERNS } from "./scan-public-repository.mjs"

export const WEBSITE_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..")
export const DOCS_ROOT = path.resolve(WEBSITE_ROOT, "..", "docs")
export const GENERATED_ROOT = path.join(WEBSITE_ROOT, ".generated")
export const CONTENT_ROOT = path.join(GENERATED_ROOT, "content")
export const MANIFEST_PATH = path.join(GENERATED_ROOT, "publish-manifest.json")
const LOCAL_VAULT_ROOT = path.resolve(DOCS_ROOT, "..", "..", "..")

const VAULT_PREFIX = "Knowledge/AI Agent Engineer/docs/"
const MAX_CODE_BYTES = 2_000_000
const MAX_IMAGE_BYTES = 8_000_000
const CODE_EXTENSIONS = new Set([".py", ".json", ".csv", ".ipynb", ".jsonl", ".sh", ".txt"])
const IMAGE_EXTENSIONS = new Set([".png", ".jpg", ".jpeg", ".webp", ".gif"])
const PYTHON_PUBLIC_FILES = new Set([
  "Python基础/00-目录.md",
  "Python基础/00-Agent工程实践.md",
])
const PYTHON_PUBLIC_PREFIXES = ["Python基础/Agent工程路线/", "Python基础/examples/"]
const AGENTIC_PUBLIC_FILES = new Set(["Agentic Design Patterns/00-目录.md"])
const AGENTIC_PUBLIC_PREFIXES = ["Agentic Design Patterns/00-初学者路线/"]

function toPosix(value) {
  return value.split(path.sep).join("/")
}

function assertInside(parent, child, label) {
  const relative = path.relative(parent, child)
  if (relative.startsWith("..") || path.isAbsolute(relative)) {
    throw new Error(`${label} escaped its allowed root: ${child}`)
  }
}

async function walk(root) {
  const result = []
  async function visit(directory) {
    const entries = await readdir(directory, { withFileTypes: true })
    for (const entry of entries) {
      const absolute = path.join(directory, entry.name)
      if (entry.isDirectory()) await visit(absolute)
      else if (entry.isFile()) result.push(absolute)
    }
  }
  await visit(root)
  return result.sort((left, right) => left.localeCompare(right, "zh-CN", { numeric: true }))
}

function isAllowedByPrefix(relativePath, files, prefixes) {
  return files.has(relativePath) || prefixes.some((prefix) => relativePath.startsWith(prefix))
}

export function classifyPath(relativePath, size = 0) {
  const normalized = relativePath.replaceAll("\\", "/")
  const extension = path.posix.extname(normalized).toLowerCase()

  if (normalized.startsWith("Python基础/") &&
      !isAllowedByPrefix(normalized, PYTHON_PUBLIC_FILES, PYTHON_PUBLIC_PREFIXES)) {
    return extension === ".md"
      ? { action: "stub", reason: "python-complete-replica" }
      : { action: "exclude", reason: "python-complete-replica" }
  }

  if (normalized.startsWith("Agentic Design Patterns/") &&
      !isAllowedByPrefix(normalized, AGENTIC_PUBLIC_FILES, AGENTIC_PUBLIC_PREFIXES)) {
    return extension === ".md"
      ? { action: "stub", reason: "agentic-unlicensed-translation" }
      : { action: "exclude", reason: "agentic-unlicensed-translation" }
  }

  if (normalized === "深度学习/00-manifest.json") {
    return { action: "exclude", reason: "local-absolute-path-manifest" }
  }

  if (extension === ".md") return { action: "publish", reason: "markdown" }
  if (CODE_EXTENSIONS.has(extension)) {
    if (!/(?:^|\/)examples\//.test(normalized)) {
      return { action: "exclude", reason: "code-or-data-outside-examples" }
    }
    return size <= MAX_CODE_BYTES
      ? { action: "asset", reason: "code-or-data" }
      : { action: "exclude", reason: "code-or-data-too-large" }
  }
  if (IMAGE_EXTENSIONS.has(extension)) {
    if (!/(?:^|\/)(?:attachments|res)\//.test(normalized)) {
      return { action: "exclude", reason: "image-outside-public-asset-directory" }
    }
    return size <= MAX_IMAGE_BYTES
      ? { action: "asset", reason: "image" }
      : { action: "exclude", reason: "image-too-large" }
  }
  if (normalized.endsWith("/.env.example") || normalized.endsWith(".env.example")) {
    if (!/(?:^|\/)examples\//.test(normalized)) {
      return { action: "exclude", reason: "environment-template-outside-examples" }
    }
    return size <= 64_000
      ? { action: "asset", reason: "environment-template" }
      : { action: "exclude", reason: "environment-template-too-large" }
  }
  return { action: "exclude", reason: "extension-not-allowlisted" }
}

function splitFrontmatter(markdown) {
  const match = markdown.match(/^\uFEFF?---\r?\n([\s\S]*?)\r?\n---(?:\r?\n|$)/)
  if (!match) return { frontmatter: "", body: markdown, full: "" }
  return {
    frontmatter: match[1],
    body: markdown.slice(match[0].length),
    full: match[0],
  }
}

export function frontmatterValue(markdown, key) {
  const { frontmatter } = splitFrontmatter(markdown)
  if (!frontmatter) return undefined
  const escaped = key.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")
  const match = frontmatter.match(new RegExp(`^${escaped}:\\s*(.*?)\\s*$`, "m"))
  if (!match) return undefined
  const value = match[1].trim()
  if ((value.startsWith('"') && value.endsWith('"')) || (value.startsWith("'") && value.endsWith("'"))) {
    return value.slice(1, -1)
  }
  return value
}

function firstHeading(markdown) {
  const body = splitFrontmatter(markdown).body
  return body.match(/^#\s+(.+?)\s*$/m)?.[1]?.replace(/\s+#+\s*$/, "").trim()
}

function yamlString(value) {
  return JSON.stringify(String(value))
}

export function ensureTitleAndStripProgress(markdown, fallbackTitle) {
  const title = frontmatterValue(markdown, "title") || firstHeading(markdown) || fallbackTitle
  const parts = splitFrontmatter(markdown)
  if (!parts.full) {
    return `---\ntitle: ${yamlString(title)}\n---\n\n${markdown.replace(/^\uFEFF/, "")}`
  }

  const lines = parts.frontmatter
    .split(/\r?\n/)
    .filter((line) => !/^\s*(?:["']ai_learning_completed["']|ai_learning_completed)\s*:/i.test(line))
  if (!lines.some((line) => /^title\s*:/.test(line))) lines.unshift(`title: ${yamlString(title)}`)
  return `---\n${lines.join("\n")}\n---\n${parts.body}`
}

export function redactMachineSpecificPaths(markdown) {
  return redactVaultRoot(markdown, LOCAL_VAULT_ROOT)
}

export function redactVaultRoot(markdown, vaultRoot) {
  const escapePattern = (value) => value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")
  const windowsRoot = path.resolve(vaultRoot)
  const posixRoot = windowsRoot.replaceAll("\\", "/")
  return markdown
    .replace(new RegExp(escapePattern(windowsRoot), "gi"), "X:\\path\\to\\your-vault")
    .replace(new RegExp(escapePattern(posixRoot), "gi"), "X:/path/to/your-vault")
}

function transformOutsideInlineCode(line, transform) {
  let output = ""
  let cursor = 0
  let delimiter = 0
  const matches = [...line.matchAll(/`+/g)]
  for (const match of matches) {
    const index = match.index ?? 0
    const run = match[0].length
    const segment = line.slice(cursor, index)
    output += delimiter === 0 ? transform(segment) : segment
    output += match[0]
    if (delimiter === 0) delimiter = run
    else if (delimiter === run) delimiter = 0
    cursor = index + run
  }
  const tail = line.slice(cursor)
  return output + (delimiter === 0 ? transform(tail) : tail)
}

export function transformOutsideCode(markdown, transform) {
  const lines = markdown.split(/(?<=\n)/)
  let fence = null
  return lines
    .map((line) => {
      const marker = line.match(/^\s*(`{3,}|~{3,})/)
      if (marker) {
        const token = marker[1][0]
        if (fence === null) fence = token
        else if (fence === token) fence = null
        return line
      }
      return fence === null ? transformOutsideInlineCode(line, transform) : line
    })
    .join("")
}

function countUnescapedPipes(value) {
  let count = 0
  for (let index = 0; index < value.length; index += 1) {
    if (value[index] !== "|") continue
    let slashes = 0
    for (let cursor = index - 1; cursor >= 0 && value[cursor] === "\\"; cursor -= 1) slashes += 1
    if (slashes % 2 === 0) count += 1
  }
  return count
}

function escapeWikilinkPipes(wikilink) {
  return wikilink.replace(/\|/g, (match, offset, value) => {
    let slashes = 0
    for (let cursor = offset - 1; cursor >= 0 && value[cursor] === "\\"; cursor -= 1) slashes += 1
    return slashes % 2 === 0 ? "\\|" : match
  })
}

/**
 * Markdown tables treat the alias separator in `[[target|alias]]` as a cell
 * delimiter. Obsidian accepts `[[target\|alias]]`, while the escaped form is
 * also understood by the Quartz Obsidian parser. Normalize only table rows in
 * the generated publication layer so the source vault remains untouched.
 */
function wikilinkTargetExists(wikilink, relativePath, sourcePaths) {
  if (!(sourcePaths instanceof Set)) return false
  const raw = wikilink.replace(/^!?\[\[/, "").replace(/\]\]$/, "")
  const target = raw.split(/\\?\|/, 1)[0].split("#", 1)[0].replaceAll("\\", "/").trim()
  if (!target) return false
  const sourceDirectory = path.posix.dirname(relativePath || "")
  const candidates = target.startsWith(VAULT_PREFIX)
    ? [target.slice(VAULT_PREFIX.length)]
    : [target, path.posix.normalize(path.posix.join(sourceDirectory, target))]
  return candidates.some((candidate) =>
    sourcePaths.has(candidate) || (!path.posix.extname(candidate) && sourcePaths.has(`${candidate}.md`)),
  )
}

export function normalizeTableWikilinks(markdown, relativePath = "", sourcePaths) {
  const lines = markdown.split(/(?<=\n)/)
  let fence = null
  return lines.map((line) => {
    const marker = line.match(/^\s*(`{3,}|~{3,})/)
    if (marker) {
      const token = marker[1][0]
      if (fence === null) fence = token
      else if (fence === token) fence = null
      return line
    }
    if (fence !== null || !line.includes("[[") || !line.includes("|")) return line

    const probe = line.replace(/(`+)?!?\[\[[^\]\r\n]+\]\]\1?/g, "WIKILINK")
    if (countUnescapedPipes(probe) < 2) return line

    // Some source notes wrapped a wikilink in code ticks to keep the table
    // intact. In the web staging layer it should be an actual link.
    const unwrapped = line.replace(
      /(`+)(!?\[\[[^\]\r\n]+\]\])\1/g,
      (full, _ticks, wikilink) => wikilinkTargetExists(wikilink, relativePath, sourcePaths) ? wikilink : full,
    )
    return unwrapped.replace(/!?\[\[[^\]\r\n]+\]\]/g, escapeWikilinkPipes)
  }).join("")
}

function decodedPath(value) {
  try {
    return decodeURIComponent(value)
  } catch {
    return value
  }
}

function encodedPath(value) {
  return value.split("/").map((segment) => encodeURIComponent(segment)).join("/")
}

export function normalizeRelativeMarkdownLinks(markdown, relativePath, sourcePaths) {
  const sourceDirectory = path.posix.dirname(relativePath)
  const normalizeTarget = (target) => {
    if (!target || target.startsWith("#") || target.startsWith("/") ||
        /^(?:https?:|mailto:|tel:|data:|blob:|javascript:|\/\/)/i.test(target)) return undefined
    const match = target.match(/^([^?#]*)([?#].*)?$/)
    const targetPath = decodedPath((match?.[1] ?? target).replaceAll("\\", "/"))
    const suffix = match?.[2] ?? ""
    const resolved = targetPath.startsWith(VAULT_PREFIX)
      ? targetPath.slice(VAULT_PREFIX.length)
      : path.posix.normalize(path.posix.join(sourceDirectory, targetPath)).replace(/^\.\//, "")
    const knownTarget = sourcePaths.has(resolved) ||
      (!path.posix.extname(resolved) && sourcePaths.has(`${resolved}.md`))
    if (!knownTarget || resolved.startsWith("../")) return undefined
    return `${encodedPath(resolved)}${suffix}`
  }

  return transformOutsideCode(markdown, (segment) => {
    const markdownLinks = segment.replace(
      /(!?\[[^\]\r\n]*\]\()(<[^>\r\n]+>|[^)\s\r\n]+)([^)\r\n]*\))/g,
      (full, opening, rawTarget, closing) => {
        const wrapped = rawTarget.startsWith("<") && rawTarget.endsWith(">")
        const target = wrapped ? rawTarget.slice(1, -1) : rawTarget
        const normalized = normalizeTarget(target)
        return normalized ? `${opening}${normalized}${closing}` : full
      },
    )
    return markdownLinks.replace(
      /\b(src|href)=(['"])([^'"]+)\2/gi,
      (full, attribute, quote, target) => {
        const normalized = normalizeTarget(target)
        return normalized ? `${attribute}=${quote}${normalized}${quote}` : full
      },
    )
  })
}

function sourceUrlFor(relativePath, markdown = "") {
  const explicit = frontmatterValue(markdown, "source_url")
  if (explicit) return explicit
  if (relativePath.startsWith("Python基础/")) {
    const upstream = relativePath.slice("Python基础/".length)
    const encoded = upstream.split("/").map(encodeURIComponent).join("/")
    return `https://github.com/jackfrued/Python-100-Days/blob/master/${encoded}`
  }
  if (relativePath.startsWith("Agentic Design Patterns/")) {
    return "https://github.com/xindoo/agentic-design-patterns/tree/effb52f1730913be650a04e5ffb251c093096894/chapters"
  }
  return undefined
}

function rewriteDeniedEmbeds(segment) {
  return segment.replace(/!\[\[([^\]]+)\]\]/g, (full, rawTarget) => {
    const target = String(rawTarget).split("|")[0].split("#")[0].replaceAll("\\", "/")
    const normalized = target.startsWith(VAULT_PREFIX) ? target.slice(VAULT_PREFIX.length) : target
    if (normalized.startsWith("Agentic Design Patterns/attachments/")) {
      return "[第三方附件未随公开站点再分发](https://github.com/xindoo/agentic-design-patterns)"
    }
    if (normalized.startsWith("Python基础/") &&
        !isAllowedByPrefix(normalized, PYTHON_PUBLIC_FILES, PYTHON_PUBLIC_PREFIXES)) {
      return "[原课程附件请前往上游仓库查看](https://github.com/jackfrued/Python-100-Days)"
    }
    return full
  })
}

export function transformVaultPaths(markdown) {
  return transformOutsideCode(markdown, (segment) =>
    rewriteDeniedEmbeds(segment)
      .replace(/\[\[Obsidian\/附件整理规则(?:#[^|\]]*)?(?:\|([^\]]+))?\]\]/g, (_full, alias) =>
        `${alias || "附件整理规则"}（仅在本机 Obsidian Vault 中提供）`,
      )
      .replaceAll(VAULT_PREFIX, ""),
  )
}

function courseRecordsFromSources(markdownSources) {
  return markdownSources
    .filter(({ relativePath }) => relativePath.split("/").length === 2 && relativePath.endsWith("/00-目录.md"))
    .map(({ relativePath, markdown }) => ({
      name: relativePath.split("/")[0],
      stage: frontmatterValue(markdown, "ai_learning_stage"),
      order: Number(frontmatterValue(markdown, "ai_learning_order")),
    }))
    .filter((course) => course.stage && Number.isFinite(course.order))
    .sort((left, right) => left.order - right.order)
}

export function buildRoadmapTable(courses) {
  const stages = [...new Set(courses.map((course) => course.stage))]
  const lines = ["| 阶段 | 学习重点 |", "| --- | --- |"]
  for (const stage of stages) {
    const links = courses
      .filter((course) => course.stage === stage)
      .map((course) => `[[${course.name}/00-目录|${course.name}]]`)
      .join(" · ")
    lines.push(`| ${stage} | ${links} |`)
  }
  return lines.join("\n")
}

function replaceDataviewRoadmap(markdown, courses) {
  const table = buildRoadmapTable(courses)
  return markdown.replace(/```dataviewjs\s*[\s\S]*?```/, table)
}

function buildStub(relativePath, markdown) {
  const title = frontmatterValue(markdown, "title") || firstHeading(markdown) || path.posix.basename(relativePath, ".md")
  const sourceUrl = sourceUrlFor(relativePath, markdown)
  const course = relativePath.split("/")[0]
  const reason = relativePath.startsWith("Python基础/")
    ? "原 Python-100-Days 课程未在固定来源中提供明确的再分发许可证。"
    : "该固定 commit 的中文译文层未提供明确的再分发许可证。"
  return `---
title: ${yamlString(title)}
tags:
  - third-party-reference
third_party_stub: true
---

# ${title}

> [!info] 本页未复制第三方原文
> ${reason} 公开网站仅保留来源跳转页；你仍可在本机 Obsidian 中阅读已有参考资料。

${sourceUrl ? `[前往上游来源查看本节](${sourceUrl})` : "请从上游项目主页查看原始材料。"}

返回 [[${course}/00-目录|${course} 学习入口]]。
`
}

function encodedMarkdownTarget(relativePath) {
  return relativePath.split("/").map((segment) => encodeURIComponent(segment)).join("/")
}

function buildResourceIndex(assets) {
  const codeAssets = assets.filter((asset) => CODE_EXTENSIONS.has(path.posix.extname(asset).toLowerCase()))
  const byCourse = new Map()
  for (const asset of codeAssets) {
    const course = asset.split("/")[0]
    if (!byCourse.has(course)) byCourse.set(course, [])
    byCourse.get(course).push(asset)
  }
  const sections = [...byCourse.entries()]
    .sort(([left], [right]) => left.localeCompare(right, "zh-CN"))
    .map(([course, files]) => {
      const links = files
        .sort((left, right) => left.localeCompare(right, "zh-CN", { numeric: true }))
        .map((file) => `- [${file.slice(course.length + 1)}](./${encodedMarkdownTarget(file)})`)
        .join("\n")
      return `## ${course}\n\n${links}`
    })
    .join("\n\n")

  return `---
title: 示例资源索引
tags:
  - ai-agent-engineer
  - examples
---

# 示例资源索引

下列文件以只读资源发布，不生成独立文档页面。点击链接会打开站内预览，可继续下载原文件；所有示例都不得包含真实密钥或凭据。

${sections || "> [!info]\n> 当前没有符合公开规则的代码或数据资源。"}
`
}

function buildThirdPartyNotices() {
  return `---
title: 第三方材料与许可声明
tags:
  - legal
  - third-party
---

# 第三方材料与许可声明

本页记录公开网站使用或再发布的第三方材料。获取与核对日期：**2026-07-16**。

## 网站运行时

- [Quartz 5](https://github.com/jackyzha0/quartz/releases/tag/v5.0.0)：MIT License；项目锁定正式版 v5.0.0 的 commit \`ab346fa66a895e12d63a308e70ce330ba795822a\`；[查看 Quartz MIT 全文](_licenses/Quartz-MIT.txt)。
- [Quartz Community 插件](https://github.com/quartz-community)：本站锁定 28 个插件的精确 commit，统一保留上游 MIT 声明；[查看插件 MIT 全文](_licenses/Quartz-Community-MIT.txt)。
- [GSAP 3.15.0](https://gsap.com/docs/v3/)：按 [GSAP Standard “No Charge” License](https://gsap.com/standard-license/) 使用，仅用于界面动效。

## 公开参考材料

- [D2L 中文版](https://github.com/d2l-ai/d2l-zh)：Apache License 2.0。本站保留各页来源和许可说明；[查看 Apache-2.0 全文](_licenses/Apache-2.0.txt)。
- [LangChain 文档](https://github.com/langchain-ai/docs)：MIT License。许可副本同时保留在 [[LangChain/LICENSE-LangChain-docs|LangChain 许可页]]；[查看 LangChain MIT 全文](_licenses/LangChain-MIT.txt)。
- [Model Context Protocol 文档](https://github.com/modelcontextprotocol/docs)：MIT License；[查看 MCP MIT 全文](_licenses/MCP-MIT.txt)。
- [Agent Skills](https://github.com/agentskills/agentskills/tree/38a2ff82958afee88dadf4831509e6f7e9d8ef4e)：Apache License 2.0，版权归 Anthropic, PBC（2025）；其中明确声明 CC0-1.0 的示例按该声明处理；[查看完整上游许可文本](_licenses/Agent-Skills-Apache-2.0.txt)。
- Requests Quickstart 等零散官方参考页按其页面来源和上游 Apache-2.0 许可说明使用。

## 未在本站复制的完整参考层

- [Python-100-Days](https://github.com/jackfrued/Python-100-Days)：固定来源未提供明确 LICENSE，本站仅发布原创 Agent 工程层和来源跳转页。
- [xindoo/agentic-design-patterns](https://github.com/xindoo/agentic-design-patterns)：所用固定 commit 未提供明确 LICENSE，本站仅发布原创初学者路线和来源跳转页。

来源跳转页不包含被排除文档的正文或附件。本声明不替代原作者的版权和许可文件，也不构成法律意见。
`
}

function buildHomepageFrontmatter(stats) {
  return `---
title: AI Agent Engineer
description: 从零构建、评测与部署 AI Agent 的中文工程学习路线。
aliases:
  - AI Agent Engineer 首页
site_page: home
site_source_document_count: ${stats.sourceMarkdown}
site_full_document_count: ${stats.fullMarkdown}
site_stub_count: ${stats.stubs}
site_asset_count: ${stats.assets}
---
`
}

async function writeText(relativePath, text, timestamps) {
  const destination = path.join(CONTENT_ROOT, ...relativePath.split("/"))
  assertInside(CONTENT_ROOT, destination, "generated content")
  await mkdir(path.dirname(destination), { recursive: true })
  await writeFile(destination, text, "utf8")
  if (timestamps) await utimes(destination, timestamps.atime, timestamps.mtime)
}

async function copyAsset(source, relativePath, timestamps) {
  const destination = path.join(CONTENT_ROOT, ...relativePath.split("/"))
  assertInside(CONTENT_ROOT, destination, "generated asset")
  await mkdir(path.dirname(destination), { recursive: true })
  await copyFile(source, destination)
  if (timestamps) await utimes(destination, timestamps.atime, timestamps.mtime)
}

export async function prepareContent() {
  assertInside(WEBSITE_ROOT, GENERATED_ROOT, "generated root")
  await rm(GENERATED_ROOT, { recursive: true, force: true })
  await mkdir(CONTENT_ROOT, { recursive: true })

  const sourceFiles = await walk(DOCS_ROOT)
  const sourcePaths = new Set(sourceFiles.map((source) => toPosix(path.relative(DOCS_ROOT, source))))
  const markdownSources = []
  for (const source of sourceFiles) {
    const relativePath = toPosix(path.relative(DOCS_ROOT, source))
    if (relativePath.toLowerCase().endsWith(".md")) {
      markdownSources.push({ relativePath, markdown: await readFile(source, "utf8") })
    }
  }
  const courses = courseRecordsFromSources(markdownSources)
  if (courses.length !== 53) throw new Error(`Expected 53 course indexes, found ${courses.length}`)
  const orders = courses.map((course) => course.order)
  if (new Set(orders).size !== 53 || Math.min(...orders) !== 1 || Math.max(...orders) !== 53) {
    throw new Error("Course order must be unique and cover 1 through 53")
  }
  const courseNames = new Set(courses.map((course) => course.name))
  const unknownTopLevel = [...sourcePaths].filter((relativePath) => {
    if (relativePath === "All of AI.md") return false
    return !courseNames.has(relativePath.split("/")[0])
  })
  if (unknownTopLevel.length > 0) {
    throw new Error(`Source files outside the 53-course publishing scope: ${unknownTopLevel.slice(0, 10).join(", ")}`)
  }
  const markdownByPath = new Map(markdownSources.map((entry) => [entry.relativePath, entry.markdown]))

  const manifest = {
    generatedAt: new Date().toISOString(),
    sourceRoot: toPosix(path.relative(WEBSITE_ROOT, DOCS_ROOT)),
    publishedMarkdown: [],
    stubMarkdown: [],
    assets: [],
    excluded: [],
    courses,
    sourceDigest: "",
  }
  const sourceHash = createHash("sha256")

  for (const source of sourceFiles) {
    const relativePath = toPosix(path.relative(DOCS_ROOT, source))
    const fileStat = await stat(source)
    const classification = classifyPath(relativePath, fileStat.size)
    const sourceBytes = markdownByPath.has(relativePath)
      ? Buffer.from(markdownByPath.get(relativePath), "utf8")
      : await readFile(source)
    sourceHash.update(relativePath)
    sourceHash.update("\0")
    sourceHash.update(sourceBytes)
    sourceHash.update("\0")

    if (classification.action === "exclude") {
      manifest.excluded.push({ path: relativePath, reason: classification.reason, bytes: fileStat.size })
      continue
    }
    if (classification.action === "asset") {
      await copyAsset(source, relativePath, fileStat)
      manifest.assets.push(relativePath)
      continue
    }

    const original = sourceBytes.toString("utf8")
    if (classification.action === "stub") {
      await writeText(relativePath, buildStub(relativePath, original), fileStat)
      manifest.stubMarkdown.push(relativePath)
      continue
    }

    const fallbackTitle = path.posix.basename(relativePath, ".md")
    let transformed = relativePath === "All of AI.md"
      ? replaceDataviewRoadmap(original, courses)
      : original
    transformed = normalizeTableWikilinks(transformed, relativePath, sourcePaths)
    transformed = normalizeRelativeMarkdownLinks(transformed, relativePath, sourcePaths)
    transformed = transformVaultPaths(transformed)
    transformed = redactMachineSpecificPaths(transformed)
    transformed = ensureTitleAndStripProgress(transformed, fallbackTitle)
    await writeText(relativePath, transformed, fileStat)
    manifest.publishedMarkdown.push(relativePath)
  }

  const stats = {
    sourceMarkdown: markdownSources.length,
    fullMarkdown: manifest.publishedMarkdown.length,
    stubs: manifest.stubMarkdown.length,
    assets: manifest.assets.length,
  }
  await writeText("index.md", buildHomepageFrontmatter(stats))
  await writeText("资源索引.md", buildResourceIndex(manifest.assets))
  await writeText("THIRD_PARTY_NOTICES.md", buildThirdPartyNotices())

  const legalRoot = path.join(WEBSITE_ROOT, "legal")
  for (const filename of [
    "Agent-Skills-Apache-2.0.txt",
    "Apache-2.0.txt",
    "LangChain-MIT.txt",
    "MCP-MIT.txt",
    "Quartz-Community-MIT.txt",
    "Quartz-MIT.txt",
  ]) {
    const source = path.join(legalRoot, filename)
    const destination = path.join(CONTENT_ROOT, "_licenses", filename)
    assertInside(CONTENT_ROOT, destination, "license destination")
    await mkdir(path.dirname(destination), { recursive: true })
    await copyFile(source, destination)
  }

  manifest.generatedPages = ["index.md", "资源索引.md", "THIRD_PARTY_NOTICES.md"]
  manifest.sourceDigest = sourceHash.digest("hex")
  manifest.summary = {
    ...stats,
    generatedPages: manifest.generatedPages.length,
    excludedFiles: manifest.excluded.length,
    stagedMarkdown: stats.fullMarkdown + stats.stubs + manifest.generatedPages.length,
  }
  await writeFile(MANIFEST_PATH, `${JSON.stringify(manifest, null, 2)}\n`, "utf8")

  const stagedTextFiles = await walk(CONTENT_ROOT)
  const publicTextExtensions = new Set([".md", ".json", ".csv", ".ipynb", ".jsonl", ".py", ".sh", ".txt"])
  const progressPattern = /(?:["']ai_learning_completed["']|ai_learning_completed)\s*:/i
  for (const file of stagedTextFiles.filter((item) =>
    publicTextExtensions.has(path.extname(item).toLowerCase()) || item.toLowerCase().endsWith(".env.example"),
  )) {
    const text = await readFile(file, "utf8")
    if (progressPattern.test(text)) {
      throw new Error(`Progress metadata leaked into staging: ${file}`)
    }
    const secret = HIGH_CONFIDENCE_SECRET_PATTERNS.find(([, pattern]) => pattern.test(text))
    if (secret) {
      throw new Error(`Possible ${secret[0]} leaked into public staging: ${file}`)
    }
  }

  console.log(JSON.stringify(manifest.summary))
  return manifest
}

if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) {
  await prepareContent()
}
