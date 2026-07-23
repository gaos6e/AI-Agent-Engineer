import { createHash } from "node:crypto"
import { readFile, readdir, stat } from "node:fs/promises"
import os from "node:os"
import path from "node:path"
import { pathToFileURL } from "node:url"
import {
  DEFAULT_LOCALE,
  SITE_LOCALE_IDS,
  contentRootFor,
  getSiteLocale,
  manifestPathFor,
  slugifyPublishedPath,
  sourceRootFor,
} from "../config/site-locales.mjs"
import { GENERATED_ROOT, WEBSITE_ROOT } from "./prepare-content.mjs"
import { HIGH_CONFIDENCE_SECRET_PATTERNS } from "./scan-public-repository.mjs"
import { localeSiteUrl, SITE_BASE_PATH, SITE_ORIGIN } from "./site-config.mjs"

export { slugifyPublishedPath }

const PUBLIC_ROOT = path.join(WEBSITE_ROOT, "public")
const FORBIDDEN_EXTENSIONS = new Set([
  ".key", ".pptx", ".xlsx", ".ttf", ".class", ".iml", ".log", ".lprof", ".sql", ".pdf", ".env",
  ".pem", ".p12", ".pfx", ".sqlite", ".db", ".pt", ".pth", ".ckpt", ".onnx", ".safetensors",
  ".zip", ".tar", ".gz", ".7z", ".rar", ".exe", ".dll", ".pyc",
])
const TEXT_EXTENSIONS = new Set([".html", ".css", ".js", ".mjs", ".json", ".xml", ".txt", ".py", ".csv", ".jsonl", ".sh"])
const escapePattern = (value) => value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")
const vaultRoot = path.resolve(sourceRootFor(WEBSITE_ROOT, DEFAULT_LOCALE), "..", "..", "..")
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
  return value.replaceAll("&amp;", "&").replaceAll("&quot;", '"').replaceAll("&#39;", "'")
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
  const base = SITE_BASE_PATH.replace(/\/+$/, "") || "/"
  let target
  if (withoutFragment === base || withoutFragment === `${base}/`) {
    target = ""
  } else if (base !== "/" && withoutFragment.startsWith(`${base}/`)) {
    target = withoutFragment.slice(base.length + 1)
  } else if (base === "/" && withoutFragment.startsWith("/")) {
    target = withoutFragment.slice(1)
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
  const candidates = cleaned ? [cleaned, `${cleaned}.html`, `${cleaned}/index.html`] : ["index.html"]
  return candidates.some((candidate) => files.has(candidate))
}

export function countKatexErrorSpans(html) {
  let count = 0
  for (const match of html.matchAll(/<span\b[^>]*>/gi)) {
    const classAttribute = match[0].match(/\bclass\s*=\s*(?:"([^"]*)"|'([^']*)')/i)
    if ((classAttribute?.[1] ?? classAttribute?.[2] ?? "").split(/\s+/).includes("katex-error")) count += 1
  }
  return count
}

function absoluteRoute(route) {
  const base = SITE_BASE_PATH.replace(/\/+$/, "")
  const normalized = String(route).replace(/^\/+/, "")
  const trailingSlash = SITE_LOCALE_IDS.some((locale) => normalized === getSiteLocale(locale).routePrefix)
  return new URL(`${base}/${normalized}${trailingSlash ? "/" : ""}`, SITE_ORIGIN).href
}

function htmlAttribute(tag, name) {
  const match = tag.match(new RegExp(`\\b${escapePattern(name)}\\s*=\\s*(?:"([^"]*)"|'([^']*)')`, "i"))
  return match?.[1] ?? match?.[2]
}

function expectedPagePath(locale, relativePath) {
  return `${getSiteLocale(locale).routePrefix}/${markdownToHtmlPath(relativePath)}`
}

async function validatePageHead(locale, manifest, fileSet, errors) {
  const expectedLanguage = locale === "en" ? "en" : "zh-CN"
  for (const page of manifest.pageTranslations) {
    const relativeHtml = expectedPagePath(locale, page.relativePath)
    if (!fileSet.has(relativeHtml)) continue
    const html = await readFile(path.join(PUBLIC_ROOT, ...relativeHtml.split("/")), "utf8")
    const htmlLanguage = html.match(/<html\b[^>]*\blang=(?:"([^"]*)"|'([^']*)')/i)
    if ((htmlLanguage?.[1] ?? htmlLanguage?.[2]) !== expectedLanguage) {
      errors.push(`Invalid HTML language on ${relativeHtml}`)
    }
    const links = [...html.matchAll(/<link\b[^>]*>/gi)].map((match) => match[0])
    const canonical = links.find((tag) => htmlAttribute(tag, "rel") === "canonical")
    if (htmlAttribute(canonical ?? "", "href") !== absoluteRoute(page.route)) {
      errors.push(`Invalid canonical URL on ${relativeHtml}`)
    }
    const alternate = new Map(
      links
        .filter((tag) => htmlAttribute(tag, "rel") === "alternate")
        .map((tag) => [htmlAttribute(tag, "hreflang"), htmlAttribute(tag, "href")]),
    )
    if (alternate.get(expectedLanguage) !== absoluteRoute(page.route) ||
        alternate.get(locale === "en" ? "zh-CN" : "en") !== absoluteRoute(page.alternateRoute) ||
        alternate.get("x-default") !== absoluteRoute(page.defaultRoute)) {
      errors.push(`Missing or incorrect hreflang links on ${relativeHtml}`)
    }
  }
}

async function validateLocale(locale, manifest, relativeFiles, fileSet, errors) {
  const definition = getSiteLocale(locale)
  const prefix = definition.routePrefix
  const localeFiles = relativeFiles.filter((file) => file === `${prefix}.html` || file.startsWith(`${prefix}/`))
  const localeSet = new Set(localeFiles)
  const htmlFiles = localeFiles.filter((file) => file.endsWith(".html"))
  const required = [
    `${prefix}/index.html`,
    `${prefix}/static/contentIndex.json`,
    `${prefix}/static/mermaid.esm.min.mjs`,
  ]
  for (const artifact of required) if (!localeSet.has(artifact)) errors.push(`Missing ${locale} build artifact: ${artifact}`)

  const expectedMinimum = Number(manifest.summary.stagedMarkdown)
  if (htmlFiles.length < expectedMinimum) errors.push(`Expected at least ${expectedMinimum} ${locale} HTML pages, found ${htmlFiles.length}`)

  const expectedCourseIndexes = manifest.courses.map((course) =>
    `${prefix}/${markdownToHtmlPath(`${course.name}/${definition.courseIndexFilename}`)}`)
  const courseIndexes = htmlFiles.filter((file) => expectedCourseIndexes.includes(file))
  if (courseIndexes.length !== manifest.courses.length || expectedCourseIndexes.some((file) => !fileSet.has(file))) {
    errors.push(`Missing or colliding ${locale} course indexes`)
  }

  const expectedDomainCount = new Set(manifest.courses.map((course) => course.domain)).size
  const expectedRoleTrackCount = new Set(manifest.courses.flatMap((course) => Object.keys(course.tracks ?? {}))).size
  const navigationProbe = expectedCourseIndexes[0]
  let navigationFolders = 0
  if (navigationProbe && fileSet.has(navigationProbe)) {
    const html = await readFile(path.join(PUBLIC_ROOT, ...navigationProbe.split("/")), "utf8")
    const navigationDomains = (html.match(/data-nav-domain=/g) ?? []).length
    const navigationRoleTracks = (html.match(/data-nav-track=/g) ?? []).length
    const navigationCourses = (html.match(/data-nav-course=/g) ?? []).length
    navigationFolders = (html.match(/data-nav-folder=/g) ?? []).length
    if (navigationDomains !== expectedDomainCount || navigationRoleTracks !== expectedRoleTrackCount ||
        navigationCourses !== manifest.courses.length || navigationFolders === 0) {
      errors.push(`Invalid ${locale} learning navigation`)
    }
    if (html.includes("Folder:")) errors.push(`Virtual folder titles leaked into ${locale} navigation`)
  } else {
    errors.push(`Missing ${locale} navigation probe page`)
  }

  const homeHtml = `${prefix}/index.html`
  if (fileSet.has(homeHtml)) {
    const home = await readFile(path.join(PUBLIC_ROOT, ...homeHtml.split("/")), "utf8")
    if (home.includes('id="aae-course-nav"')) errors.push(`${locale} homepage embeds the full article navigation tree`)
  }

  const stagedMarkdown = [...manifest.publishedMarkdown, ...manifest.stubMarkdown, ...manifest.generatedPages]
  const expectedPublishedPages = stagedMarkdown.map((relativePath) => expectedPagePath(locale, relativePath))
  const missingPublishedPages = expectedPublishedPages.filter((file) => !fileSet.has(file))
  if (new Set(expectedPublishedPages).size !== expectedPublishedPages.length || missingPublishedPages.length > 0) {
    errors.push(`Missing or colliding ${locale} published pages: ${missingPublishedPages.slice(0, 20).join(", ")}`)
  }

  const expectedAssets = new Map(manifest.assets.map((asset) => [`${prefix}/${slugifyPublishedPath(asset)}`, asset]))
  if (expectedAssets.size !== manifest.assets.length) errors.push(`Published ${locale} asset routes collide after slugification`)
  const missingAssets = [...expectedAssets.keys()].filter((file) => !fileSet.has(file))
  if (missingAssets.length > 0) errors.push(`Missing ${locale} assets: ${missingAssets.slice(0, 20).join(", ")}`)
  const courseRoots = new Set(manifest.courses.map((course) => `${prefix}/${slugifyPublishedPath(course.name)}`))
  const unexpectedCourseAssets = localeFiles.filter((file) =>
    courseRoots.has(file.split("/").slice(0, 2).join("/")) && !file.endsWith(".html") && !expectedAssets.has(file))
  if (unexpectedCourseAssets.length > 0) errors.push(`Unexpected ${locale} course assets: ${unexpectedCourseAssets.slice(0, 20).join(", ")}`)

  for (const [publicPath, stagedPath] of expectedAssets) {
    if (!fileSet.has(publicPath)) continue
    const [stagedBytes, publicBytes] = await Promise.all([
      readFile(path.join(contentRootFor(GENERATED_ROOT, locale), ...stagedPath.split("/"))),
      readFile(path.join(PUBLIC_ROOT, ...publicPath.split("/"))),
    ])
    if (sha256(stagedBytes) !== sha256(publicBytes)) errors.push(`Published ${locale} asset changed during build: ${publicPath}`)
  }

  const packageMermaidRoot = path.join(WEBSITE_ROOT, "node_modules", "mermaid", "dist")
  const packageMermaidChunks = path.join(packageMermaidRoot, "chunks", "mermaid.esm.min")
  const chunkNames = (await readdir(packageMermaidChunks, { withFileTypes: true }))
    .filter((entry) => entry.isFile() && entry.name.endsWith(".mjs")).map((entry) => entry.name).sort()
  const mermaidModules = [
    { source: path.join(packageMermaidRoot, "mermaid.esm.min.mjs"), publicPath: `${prefix}/static/mermaid.esm.min.mjs` },
    ...chunkNames.map((name) => ({ source: path.join(packageMermaidChunks, name), publicPath: `${prefix}/static/chunks/mermaid.esm.min/${name}` })),
  ]
  const expectedMermaidFiles = new Set(mermaidModules.map(({ publicPath }) => publicPath))
  const actualMermaidFiles = localeFiles.filter((file) => file === `${prefix}/static/mermaid.esm.min.mjs` || file.startsWith(`${prefix}/static/chunks/mermaid.esm.min/`))
  if ([...expectedMermaidFiles].some((file) => !fileSet.has(file)) || actualMermaidFiles.some((file) => !expectedMermaidFiles.has(file))) {
    errors.push(`Invalid ${locale} Mermaid module graph`)
  }
  for (const module of mermaidModules) {
    if (!fileSet.has(module.publicPath)) continue
    const [packageBytes, publicBytes] = await Promise.all([readFile(module.source), readFile(path.join(PUBLIC_ROOT, ...module.publicPath.split("/")))])
    if (sha256(packageBytes) !== sha256(publicBytes)) errors.push(`Published ${locale} Mermaid module changed: ${module.publicPath}`)
  }

  const broken = new Set()
  const unsupportedSchemes = new Set()
  const outsideBase = new Set()
  const selfRedirects = new Set()
  const tableWikilinkLeaks = new Set()
  const interactiveCheckboxes = new Set()
  const katexErrorPages = new Map()
  const remoteMermaidLoaders = new Set()
  for (const relativeHtml of htmlFiles) {
    const html = await readFile(path.join(PUBLIC_ROOT, ...relativeHtml.split("/")), "utf8")
    if (/https:\/\/cdnjs\.cloudflare\.com/i.test(html)) remoteMermaidLoaders.add(relativeHtml)
    const katexErrors = countKatexErrorSpans(html)
    if (katexErrors > 0) katexErrorPages.set(relativeHtml, katexErrors)
    for (const match of html.matchAll(/<t[dh]\b[^>]*>[\s\S]*?<\/t[dh]>/gi)) {
      if (/\[\[[\s\S]*?\]\]/.test(match[0].replace(/<code\b[^>]*>[\s\S]*?<\/code>/gi, ""))) tableWikilinkLeaks.add(relativeHtml)
    }
    for (const match of html.matchAll(/<input\b[^>]*\bcheckbox-toggle\b[^>]*>/gi)) {
      if (!/\bdisabled(?:\s*=|\s|\/?>)/i.test(match[0])) interactiveCheckboxes.add(relativeHtml)
    }
    for (const tag of html.match(/<meta\b[^>]*>/gi) ?? []) {
      if (!/\bhttp-equiv=(?:"refresh"|'refresh')/i.test(tag)) continue
      const content = htmlAttribute(tag, "content") ?? ""
      const target = content.replace(/^.*?\burl\s*=\s*/i, "").trim()
      const resolved = localTarget(relativeHtml, target)
      if (resolved?.target !== undefined && htmlRoute(resolved.target) === htmlRoute(relativeHtml)) selfRedirects.add(`${relativeHtml} -> ${target}`)
    }
    for (const match of html.matchAll(/\b(?:href|src)=(?:"([^"]*)"|'([^']*)')/gi)) {
      const raw = match[1] ?? match[2] ?? ""
      const resolved = localTarget(relativeHtml, raw)
      if (!resolved) continue
      if (resolved.unsupportedScheme) unsupportedSchemes.add(`${relativeHtml} -> ${resolved.unsupportedScheme}`)
      else if (resolved.outsideBase) outsideBase.add(`${relativeHtml} -> ${resolved.outsideBase}`)
      else if (!targetExists(resolved.target, fileSet)) broken.add(`${relativeHtml} -> ${raw}`)
    }
  }
  if (remoteMermaidLoaders.size > 0) errors.push(`Remote cdnjs references remain in ${locale} HTML`)
  if (unsupportedSchemes.size > 0) errors.push(`Unsupported ${locale} public URL schemes:\n${[...unsupportedSchemes].slice(0, 20).join("\n")}`)
  if (broken.size > 0) errors.push(`Broken ${locale} local links (${broken.size}):\n${[...broken].slice(0, 100).join("\n")}`)
  if (outsideBase.size > 0) errors.push(`URLs escape ${SITE_BASE_PATH} in ${locale}:\n${[...outsideBase].slice(0, 20).join("\n")}`)
  if (selfRedirects.size > 0) errors.push(`Self-referential ${locale} redirects:\n${[...selfRedirects].slice(0, 20).join("\n")}`)
  if (tableWikilinkLeaks.size > 0) errors.push(`Unparsed ${locale} table wikilinks`)
  if (interactiveCheckboxes.size > 0) errors.push(`Interactive ${locale} learning checkboxes are present`)
  if (katexErrorPages.size > 0) errors.push(`KaTeX render errors in ${locale}`)
  await validatePageHead(locale, manifest, fileSet, errors)

  return { htmlPages: htmlFiles.length, courseIndexes: courseIndexes.length, navigationFolders }
}

export async function validateSite() {
  const publicStat = await stat(PUBLIC_ROOT)
  if (!publicStat.isDirectory()) throw new Error("Public build directory does not exist")
  const manifests = new Map(await Promise.all(SITE_LOCALE_IDS.map(async (locale) => [
    locale,
    JSON.parse(await readFile(manifestPathFor(GENERATED_ROOT, locale), "utf8")),
  ])))
  const publicFiles = await walk(PUBLIC_ROOT)
  const relativeFiles = publicFiles.map((file) => toPosix(path.relative(PUBLIC_ROOT, file)))
  const fileSet = new Set(relativeFiles)
  const errors = []

  for (const required of ["index.html", "404.html", ".nojekyll", "robots.txt"]) {
    if (!fileSet.has(required)) errors.push(`Missing required build artifact: ${required}`)
  }
  const rootIndex = fileSet.has("index.html") ? await readFile(path.join(PUBLIC_ROOT, "index.html"), "utf8") : ""
  if (!rootIndex.includes(`url=${SITE_BASE_PATH.replace(/\/+$/, "")}/${getSiteLocale(DEFAULT_LOCALE).routePrefix}`)) {
    errors.push("Root page does not default to Chinese")
  }
  const robots = fileSet.has("robots.txt") ? await readFile(path.join(PUBLIC_ROOT, "robots.txt"), "utf8") : ""
  for (const locale of SITE_LOCALE_IDS) {
    if (!robots.includes(`Sitemap: ${localeSiteUrl(locale)}/sitemap.xml`)) errors.push(`robots.txt lacks the ${locale} sitemap`)
  }
  const forbidden = relativeFiles.filter((file) => FORBIDDEN_EXTENSIONS.has(path.posix.extname(file).toLowerCase()))
  if (forbidden.length > 0) errors.push(`Forbidden public file types: ${forbidden.slice(0, 10).join(", ")}`)

  const localeSummaries = {}
  for (const locale of SITE_LOCALE_IDS) {
    localeSummaries[locale] = await validateLocale(locale, manifests.get(locale), relativeFiles, fileSet, errors)
  }
  const chineseManifest = manifests.get(DEFAULT_LOCALE)
  for (const { route, targetRoute } of chineseManifest.legacyRoutes) {
    const file = `${route}.html`
    if (!fileSet.has(file)) {
      errors.push(`Missing legacy redirect: ${file}`)
      continue
    }
    const html = await readFile(path.join(PUBLIC_ROOT, ...file.split("/")), "utf8")
    if (!html.includes(siteHref(targetRoute))) errors.push(`Legacy redirect has the wrong target: ${file}`)
  }

  const sensitiveLeaks = []
  const checkboxProgressRuntimeLeaks = []
  for (const relative of relativeFiles.filter((file) => TEXT_EXTENSIONS.has(path.posix.extname(file).toLowerCase()))) {
    const text = await readFile(path.join(PUBLIC_ROOT, ...relative.split("/")), "utf8")
    if (/ai_learning_completed/i.test(text)) sensitiveLeaks.push(`${relative}: learning-progress metadata`)
    if (text.includes("-checkbox-") && /localStorage\.(?:getItem|setItem)/.test(text)) checkboxProgressRuntimeLeaks.push(relative)
    if (MACHINE_PATH_PATTERNS.some((pattern) => pattern.test(text))) sensitiveLeaks.push(`${relative}: machine-specific local path`)
    for (const [label, pattern] of HIGH_CONFIDENCE_SECRET_PATTERNS) {
      if (pattern.test(text)) sensitiveLeaks.push(`${relative}: ${label}`)
    }
  }
  if (sensitiveLeaks.length > 0) errors.push(`Sensitive public content (${sensitiveLeaks.length}):\n${sensitiveLeaks.slice(0, 30).join("\n")}`)
  if (checkboxProgressRuntimeLeaks.length > 0) errors.push(`Checkbox progress persistence is present`)
  if (errors.length > 0) throw new Error(errors.join("\n\n"))

  const summary = {
    locales: localeSummaries,
    publicFiles: relativeFiles.length,
    brokenLocalLinks: 0,
    forbiddenFiles: 0,
    progressMetadataLeaks: 0,
    sensitiveLeaks: 0,
    hreflangErrors: 0,
  }
  console.log(JSON.stringify(summary))
  return summary
}

function siteHref(route) {
  return `${SITE_BASE_PATH.replace(/\/+$/, "")}/${String(route).replace(/^\/+/, "")}`
}

if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) {
  await validateSite()
}
