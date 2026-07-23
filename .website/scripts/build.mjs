import { copyFile, mkdir, readFile, rm, writeFile } from "node:fs/promises"
import path from "node:path"
import {
  DEFAULT_LOCALE,
  SITE_LOCALE_IDS,
  contentRootFor,
  getSiteLocale,
  manifestPathFor,
} from "../config/site-locales.mjs"
import {
  localeSiteBasePath,
  localeSiteUrl,
  SITE_BASE_PATH,
  SITE_ORIGIN,
} from "./site-config.mjs"
import {
  bootstrapRuntime,
  copyContentToRuntime,
  runPackageManager,
  RUNTIME_ROOT,
  runtimeEnvironment,
  WEBSITE_ROOT,
} from "./bootstrap-runtime.mjs"
import { GENERATED_ROOT, prepareContent } from "./prepare-content.mjs"
import { validateSite } from "./validate-site.mjs"

function assertInside(parent, child, label) {
  const relative = path.relative(parent, child)
  if (relative.startsWith("..") || path.isAbsolute(relative)) {
    throw new Error(`${label} escaped its allowed root: ${child}`)
  }
}

function siteHref(route) {
  return `${SITE_BASE_PATH.replace(/\/+$/, "")}/${String(route).replace(/^\/+/, "")}`
}

function redirectDocument(target) {
  const href = siteHref(target)
  const canonical = new URL(href, SITE_ORIGIN).href
  const escapedHref = href.replaceAll("&", "&amp;").replaceAll('"', "&quot;")
  return `<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="robots" content="noindex">
  <link rel="canonical" href="${canonical}">
  <meta http-equiv="refresh" content="0; url=${escapedHref}">
  <script>location.replace(${JSON.stringify(href)})</script>
</head>
<body><a href="${escapedHref}">继续前往 AI Agent Engineer</a></body>
</html>
`
}

async function writeRedirect(publicRoot, route, targetRoute) {
  const normalized = String(route).replaceAll("\\", "/").replace(/^\/+|\/+$/g, "")
  const destination = path.resolve(publicRoot, ...`${normalized}.html`.split("/"))
  assertInside(publicRoot, destination, "Legacy redirect")
  await mkdir(path.dirname(destination), { recursive: true })
  await writeFile(destination, redirectDocument(targetRoute), "utf8")
}

await prepareContent()

const publicRoot = path.join(WEBSITE_ROOT, "public")
await rm(publicRoot, { recursive: true, force: true })
await mkdir(publicRoot, { recursive: true })

for (const locale of SITE_LOCALE_IDS) {
  const definition = getSiteLocale(locale)
  await bootstrapRuntime(locale)
  const runtimeContent = await copyContentToRuntime(contentRootFor(GENERATED_ROOT, locale))
  await runPackageManager(
    "npx",
    [
      "quartz",
      "build",
      "-d",
      runtimeContent,
      "-o",
      path.join(publicRoot, definition.routePrefix),
      "--concurrency",
      "2",
      "--baseDir",
      localeSiteBasePath(locale),
    ],
    { cwd: RUNTIME_ROOT, env: runtimeEnvironment() },
  )
}

const chineseManifest = JSON.parse(await readFile(manifestPathFor(GENERATED_ROOT, DEFAULT_LOCALE), "utf8"))
await writeFile(path.join(publicRoot, "index.html"), redirectDocument(getSiteLocale(DEFAULT_LOCALE).routePrefix), "utf8")
for (const { route, targetRoute } of chineseManifest.legacyRoutes) {
  if (route === "index") continue
  await writeRedirect(publicRoot, route, targetRoute)
}

const chinese404 = path.join(publicRoot, getSiteLocale(DEFAULT_LOCALE).routePrefix, "404.html")
await copyFile(chinese404, path.join(publicRoot, "404.html"))
await writeFile(path.join(publicRoot, ".nojekyll"), "", "utf8")
await writeFile(
  path.join(publicRoot, "robots.txt"),
  [
    "User-agent: *",
    "Allow: /",
    ...SITE_LOCALE_IDS.map((locale) => `Sitemap: ${localeSiteUrl(locale)}/sitemap.xml`),
    "",
  ].join("\n"),
  "utf8",
)

await validateSite()
