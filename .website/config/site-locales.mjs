import path from "node:path"

export const DEFAULT_LOCALE = "zh-CN"

export const SITE_LOCALES = Object.freeze({
  "zh-CN": Object.freeze({
    id: "zh-CN",
    sourceDirectory: "docs-CN",
    routePrefix: "zh-CN",
    quartzLocale: "zh-CN",
    pageTitle: "AI Agent Engineer",
    pageTitleSuffix: " · 从零构建、评测与部署 AI Agent",
    courseIndexFilename: "00-目录.md",
    courseIndexLink: "00-目录",
    roadmapFilename: "All of AI.md",
    resourceIndexFilename: "资源索引.md",
    thirdPartyNoticesFilename: "THIRD_PARTY_NOTICES.md",
    supplementalTopLevel: ["维护记录"],
  }),
  en: Object.freeze({
    id: "en",
    sourceDirectory: "docs-EN",
    routePrefix: "en",
    quartzLocale: "en-US",
    pageTitle: "AI Agent Engineer",
    pageTitleSuffix: " · Build, Evaluate, and Deploy AI Agents",
    courseIndexFilename: "00-index.md",
    courseIndexLink: "00-index",
    roadmapFilename: "all-of-ai.md",
    resourceIndexFilename: "resources.md",
    thirdPartyNoticesFilename: "third-party-notices.md",
    supplementalTopLevel: ["maintenance-records"],
  }),
})

export const SITE_LOCALE_IDS = Object.freeze(Object.keys(SITE_LOCALES))

export function getSiteLocale(locale = DEFAULT_LOCALE) {
  const definition = SITE_LOCALES[locale]
  if (!definition) throw new Error(`Unsupported site locale: ${locale}`)
  return definition
}

export function sourceRootFor(websiteRoot, locale = DEFAULT_LOCALE) {
  return path.resolve(websiteRoot, "..", getSiteLocale(locale).sourceDirectory)
}

export function contentRootFor(generatedRoot, locale = DEFAULT_LOCALE) {
  return path.join(generatedRoot, "content", getSiteLocale(locale).routePrefix)
}

export function manifestPathFor(generatedRoot, locale = DEFAULT_LOCALE) {
  return path.join(generatedRoot, "manifests", `${getSiteLocale(locale).routePrefix}.json`)
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

export function pageRouteFor(locale, relativeMarkdownPath) {
  const definition = getSiteLocale(locale)
  const relative = String(relativeMarkdownPath).replace(/\.md$/i, "")
  const slug = slugifyPublishedPath(relative)
    .replace(/^index$/, "")
    .replace(/\/index$/, "")
  return slug ? `${definition.routePrefix}/${slug}` : definition.routePrefix
}
