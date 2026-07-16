import { createHash } from "node:crypto"
import { readFile, readdir, stat } from "node:fs/promises"
import path from "node:path"
import { pathToFileURL } from "node:url"
import os from "node:os"
import { DOCS_ROOT, MANIFEST_PATH, WEBSITE_ROOT } from "./prepare-content.mjs"
import { HIGH_CONFIDENCE_SECRET_PATTERNS } from "./scan-public-repository.mjs"
import { SITE_BASE_PATH } from "./site-config.mjs"

const PUBLIC_ROOT = path.join(WEBSITE_ROOT, "public")
const BASE_PATH = SITE_BASE_PATH
const FORBIDDEN_EXTENSIONS = new Set([
  ".key",
  ".pptx",
  ".xlsx",
  ".ttf",
  ".class",
  ".iml",
  ".log",
  ".lprof",
  ".sql",
  ".pdf",
  ".env",
  ".pem",
  ".p12",
  ".pfx",
  ".sqlite",
  ".db",
  ".pt",
  ".pth",
  ".ckpt",
  ".onnx",
  ".safetensors",
  ".zip",
  ".tar",
  ".gz",
  ".7z",
  ".rar",
  ".exe",
  ".dll",
  ".pyc",
])
const TEXT_EXTENSIONS = new Set([".html", ".css", ".js", ".json", ".xml", ".txt", ".py", ".csv", ".jsonl", ".sh"])
const SECRET_PATTERNS = HIGH_CONFIDENCE_SECRET_PATTERNS
const escapePattern = (value) => value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")
const vaultRoot = path.resolve(DOCS_ROOT, "..", "..", "..")
const homeRoot = os.homedir()
const MACHINE_PATH_PATTERNS = [
  new RegExp(escapePattern(vaultRoot), "i"),
  new RegExp(escapePattern(vaultRoot.replaceAll("\\", "/")), "i"),
  new RegExp(escapePattern(homeRoot), "i"),
  new RegExp(escapePattern(homeRoot.replaceAll("\\", "/")), "i"),
  /\b[A-Z]:\\Users\\(?!<)[^\\\s<>"']+\\/,
]

function toPosix(value) {
  return value.split(path.sep).join("/")
}

export function slugifyPublishedPath(value) {
  return value
    .split("/")
    .map((segment) => segment
      .replace(/\s/g, "-")
      .replace(/&/g, "-and-")
      .replace(/%/g, "-percent")
      .replace(/[?#]/g, ""))
    .join("/")
    .replace(/\/$/, "")
    .replace(/(^|\/)\_index(?=\.|$)/g, "$1index")
}

export function markdownToHtmlPath(relativePath) {
  return `${slugifyPublishedPath(relativePath.replace(/\.md$/i, ""))}.html`
}

function sha256(buffer) {
  return createHash("sha256").update(buffer).digest("hex")
}

async function walk(root) {
  const result = []
  async function visit(directory) {
    for (const entry of await readdir(directory, { withFileTypes: true })) {
      const absolute = path.join(directory, entry.name)
      if (entry.isDirectory()) await visit(absolute)
      else if (entry.isFile()) result.push(absolute)
    }
  }
  await visit(root)
  return result
}

function decodeHtmlAttribute(value) {
  return value
    .replaceAll("&amp;", "&")
    .replaceAll("&quot;", '"')
    .replaceAll("&#39;", "'")
}

function safeDecode(value) {
  try {
    return decodeURIComponent(value)
  } catch {
    return value
  }
}

function htmlRoute(relativeHtml) {
  const withoutExtension = relativeHtml.replace(/\.html$/i, "")
  if (withoutExtension === "index") return ""
  return withoutExtension.endsWith("/index") ? withoutExtension.slice(0, -"/index".length) : withoutExtension
}

export function localTarget(currentHtml, rawValue) {
  const value = decodeHtmlAttribute(rawValue.trim())
  if (!value || value.startsWith("#")) return null
  if (/^(?:https?:|mailto:|tel:)/i.test(value)) return null
  if (value.startsWith("//")) return { unsupportedScheme: value }
  if (/^[a-z][a-z0-9+.-]*:/i.test(value)) return { unsupportedScheme: value }

  const withoutFragment = value.split("#")[0].split("?")[0]
  if (!withoutFragment) return null
  let target
  if (withoutFragment === BASE_PATH || withoutFragment === `${BASE_PATH}/`) {
    target = ""
  } else if (withoutFragment.startsWith(`${BASE_PATH}/`)) {
    target = withoutFragment.slice(BASE_PATH.length + 1)
  } else if (withoutFragment.startsWith("/")) {
    return { outsideBase: value }
  } else {
    target = path.posix.join(path.posix.dirname(currentHtml), withoutFragment)
  }
  target = path.posix.normalize(safeDecode(target)).replace(/^\.\//, "")
  if (target === ".") target = ""
  if (target === ".." || target.startsWith("../")) return { outsideBase: value }
  return { target }
}

function targetExists(target, files) {
  const cleaned = target.replace(/\/$/, "")
  const candidates = cleaned
    ? [cleaned, `${cleaned}.html`, `${cleaned}/index.html`]
    : ["index.html"]
  return candidates.some((candidate) => files.has(candidate))
}

export async function validateSite() {
  const publicStat = await stat(PUBLIC_ROOT)
  if (!publicStat.isDirectory()) throw new Error("Public build directory does not exist")

  const manifest = JSON.parse(await readFile(MANIFEST_PATH, "utf8"))
  const publicFiles = await walk(PUBLIC_ROOT)
  const relativeFiles = publicFiles.map((file) => toPosix(path.relative(PUBLIC_ROOT, file)))
  const fileSet = new Set(relativeFiles)
  const errors = []

  for (const required of ["index.html", "static/contentIndex.json", ".nojekyll", "robots.txt"]) {
    if (!fileSet.has(required)) errors.push(`Missing required build artifact: ${required}`)
  }

  const forbidden = relativeFiles.filter((file) => FORBIDDEN_EXTENSIONS.has(path.posix.extname(file).toLowerCase()))
  if (forbidden.length > 0) errors.push(`Forbidden public file types: ${forbidden.slice(0, 10).join(", ")}`)

  const htmlFiles = relativeFiles.filter((file) => file.endsWith(".html"))
  const expectedMinimum = Number(manifest.summary.stagedMarkdown)
  if (htmlFiles.length < expectedMinimum) {
    errors.push(`Expected at least ${expectedMinimum} HTML pages, found ${htmlFiles.length}`)
  }

  const courseIndexes = htmlFiles.filter((file) => {
    const segments = file.split("/")
    return segments.length === 2 && segments[1] === "00-目录.html"
  })
  if (courseIndexes.length !== 53) {
    errors.push(`Expected 53 top-level course index pages, found ${courseIndexes.length}`)
  }

  const expectedCourseIndexes = manifest.courses.map((course) =>
    `${slugifyPublishedPath(course.name)}/00-目录.html`)
  const missingCourseIndexes = expectedCourseIndexes.filter((file) => !fileSet.has(file))
  if (new Set(expectedCourseIndexes).size !== 53 || missingCourseIndexes.length > 0) {
    errors.push(`Missing or colliding course indexes: ${missingCourseIndexes.slice(0, 20).join(", ")}`)
  }

  const navigationProbe = "RAG/00-目录.html"
  let navigationStages = 0
  let navigationCourses = 0
  let navigationFolders = 0
  if (fileSet.has(navigationProbe)) {
    const html = await readFile(path.join(PUBLIC_ROOT, ...navigationProbe.split("/")), "utf8")
    navigationStages = (html.match(/data-nav-stage=/g) ?? []).length
    navigationCourses = (html.match(/data-nav-course=/g) ?? []).length
    navigationFolders = (html.match(/data-nav-folder=/g) ?? []).length
    if (navigationStages !== 8 || navigationCourses !== 53 || navigationFolders === 0) {
      errors.push(
        `Invalid learning navigation: ${navigationStages} stages, ${navigationCourses} courses, ${navigationFolders} folders`,
      )
    }
    if (html.includes("Folder:")) errors.push("Virtual folder titles leaked into the learning navigation")
  } else {
    errors.push(`Missing navigation probe page: ${navigationProbe}`)
  }

  if (fileSet.has("index.html")) {
    const homeHtml = await readFile(path.join(PUBLIC_ROOT, "index.html"), "utf8")
    if (homeHtml.includes('id="aae-course-nav"')) {
      errors.push("Homepage unexpectedly embeds the full article navigation tree")
    }
  }

  const stagedMarkdown = [
    ...manifest.publishedMarkdown,
    ...manifest.stubMarkdown,
    ...manifest.generatedPages,
  ]
  const expectedPublishedPages = stagedMarkdown.map(markdownToHtmlPath)
  const missingPublishedPages = expectedPublishedPages.filter((file) => !fileSet.has(file))
  if (new Set(expectedPublishedPages).size !== expectedPublishedPages.length) {
    errors.push("Published Markdown routes collide after Quartz slugification")
  }
  if (missingPublishedPages.length > 0) {
    errors.push(`Missing published pages (${missingPublishedPages.length}): ${missingPublishedPages.slice(0, 20).join(", ")}`)
  }

  const expectedAssets = new Map(manifest.assets.map((asset) => [slugifyPublishedPath(asset), asset]))
  if (expectedAssets.size !== manifest.assets.length) {
    errors.push("Published asset routes collide after Quartz slugification")
  }
  const missingAssets = [...expectedAssets.keys()].filter((file) => !fileSet.has(file))
  if (missingAssets.length > 0) {
    errors.push(`Missing published assets (${missingAssets.length}): ${missingAssets.slice(0, 20).join(", ")}`)
  }

  const courseRoots = new Set(manifest.courses.map((course) => slugifyPublishedPath(course.name)))
  const unexpectedCourseAssets = relativeFiles.filter((file) =>
    courseRoots.has(file.split("/")[0]) && !file.endsWith(".html") && !expectedAssets.has(file))
  if (unexpectedCourseAssets.length > 0) {
    errors.push(`Unexpected course assets: ${unexpectedCourseAssets.slice(0, 20).join(", ")}`)
  }

  const changedAssets = []
  for (const [publicPath, stagedPath] of expectedAssets) {
    if (!fileSet.has(publicPath)) continue
    const [stagedBytes, publicBytes] = await Promise.all([
      readFile(path.join(WEBSITE_ROOT, ".generated", "content", ...stagedPath.split("/"))),
      readFile(path.join(PUBLIC_ROOT, ...publicPath.split("/"))),
    ])
    if (sha256(stagedBytes) !== sha256(publicBytes)) changedAssets.push(publicPath)
  }
  if (changedAssets.length > 0) {
    errors.push(`Published assets changed during build: ${changedAssets.slice(0, 20).join(", ")}`)
  }

  const broken = new Set()
  const unsupportedSchemes = new Set()
  const outsideBase = new Set()
  const selfRedirects = new Set()
  const tableWikilinkLeaks = new Set()
  const interactiveCheckboxes = new Set()
  for (const relativeHtml of htmlFiles) {
    const html = await readFile(path.join(PUBLIC_ROOT, ...relativeHtml.split("/")), "utf8")
    for (const match of html.matchAll(/<t[dh]\b[^>]*>[\s\S]*?<\/t[dh]>/gi)) {
      const nonCodeCell = match[0].replace(/<code\b[^>]*>[\s\S]*?<\/code>/gi, "")
      if (/\[\[[\s\S]*?\]\]/.test(nonCodeCell)) tableWikilinkLeaks.add(relativeHtml)
    }
    for (const match of html.matchAll(/<input\b[^>]*\bcheckbox-toggle\b[^>]*>/gi)) {
      if (!/\bdisabled(?:\s*=|\s|\/?>)/i.test(match[0])) interactiveCheckboxes.add(relativeHtml)
    }
    for (const match of html.matchAll(/<meta\b[^>]*>/gi)) {
      const tag = match[0]
      if (!/\bhttp-equiv=(?:"refresh"|'refresh')/i.test(tag)) continue
      const content = tag.match(/\bcontent=(?:"([^"]*)"|'([^']*)')/i)
      const refreshTarget = (content?.[1] ?? content?.[2] ?? "").replace(/^.*?\burl\s*=\s*/i, "").trim()
      if (!refreshTarget) continue
      const resolved = localTarget(relativeHtml, refreshTarget)
      if (resolved?.target !== undefined && htmlRoute(resolved.target) === htmlRoute(relativeHtml)) {
        selfRedirects.add(`${relativeHtml} -> ${refreshTarget}`)
      }
    }
    for (const match of html.matchAll(/\b(?:href|src)=(?:"([^"]*)"|'([^']*)')/gi)) {
      const raw = match[1] ?? match[2] ?? ""
      const resolved = localTarget(relativeHtml, raw)
      if (!resolved) continue
      if (resolved.unsupportedScheme) {
        unsupportedSchemes.add(`${relativeHtml} -> ${resolved.unsupportedScheme}`)
        continue
      }
      if (resolved.outsideBase) {
        outsideBase.add(`${relativeHtml} -> ${resolved.outsideBase}`)
        continue
      }
      if (!targetExists(resolved.target, fileSet)) broken.add(`${relativeHtml} -> ${raw}`)
    }
  }
  if (unsupportedSchemes.size > 0) {
    errors.push(`Unsupported public URL schemes:\n${[...unsupportedSchemes].slice(0, 20).join("\n")}`)
  }
  if (broken.size > 0) {
    errors.push(`Broken local links (${broken.size}):\n${[...broken].slice(0, 100).join("\n")}`)
  }
  if (outsideBase.size > 0) {
    errors.push(`URLs escape ${BASE_PATH}:\n${[...outsideBase].slice(0, 20).join("\n")}`)
  }
  if (selfRedirects.size > 0) {
    errors.push(`Self-referential redirect pages (${selfRedirects.size}):\n${[...selfRedirects].slice(0, 20).join("\n")}`)
  }
  if (tableWikilinkLeaks.size > 0) {
    errors.push(`Unparsed wikilinks inside tables (${tableWikilinkLeaks.size}):\n${[...tableWikilinkLeaks].slice(0, 20).join("\n")}`)
  }
  if (interactiveCheckboxes.size > 0) {
    errors.push(`Interactive learning checkboxes are present (${interactiveCheckboxes.size}):\n${[...interactiveCheckboxes].slice(0, 20).join("\n")}`)
  }

  const sensitiveLeaks = []
  const checkboxProgressRuntimeLeaks = []
  for (const relative of relativeFiles.filter((file) => TEXT_EXTENSIONS.has(path.posix.extname(file).toLowerCase()))) {
    const text = await readFile(path.join(PUBLIC_ROOT, ...relative.split("/")), "utf8")
    if (/ai_learning_completed/i.test(text)) sensitiveLeaks.push(`${relative}: learning-progress metadata`)
    if (text.includes("-checkbox-") && /localStorage\.(?:getItem|setItem)/.test(text)) {
      checkboxProgressRuntimeLeaks.push(relative)
    }
    if (MACHINE_PATH_PATTERNS.some((pattern) => pattern.test(text))) {
      sensitiveLeaks.push(`${relative}: machine-specific local path`)
    }
    for (const [label, pattern] of SECRET_PATTERNS) {
      if (pattern.test(text)) sensitiveLeaks.push(`${relative}: ${label}`)
    }
  }
  if (sensitiveLeaks.length > 0) {
    errors.push(`Sensitive public content (${sensitiveLeaks.length}):\n${sensitiveLeaks.slice(0, 30).join("\n")}`)
  }
  if (checkboxProgressRuntimeLeaks.length > 0) {
    errors.push(`Checkbox progress persistence is present (${checkboxProgressRuntimeLeaks.length}):\n${checkboxProgressRuntimeLeaks.slice(0, 20).join("\n")}`)
  }

  if (errors.length > 0) throw new Error(errors.join("\n\n"))

  const summary = {
    htmlPages: htmlFiles.length,
    courseIndexes: courseIndexes.length,
    publishedPages: expectedPublishedPages.length,
    publishedAssets: expectedAssets.size,
    publicFiles: relativeFiles.length,
    brokenLocalLinks: 0,
    forbiddenFiles: 0,
    progressMetadataLeaks: 0,
    sensitiveLeaks: 0,
    selfRedirects: 0,
    tableWikilinkLeaks: 0,
    checkboxProgressRuntimeLeaks: 0,
    interactiveCheckboxes: 0,
    navigationStages,
    navigationCourses,
    navigationFolders,
  }
  console.log(JSON.stringify(summary))
  return summary
}

if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) {
  await validateSite()
}
