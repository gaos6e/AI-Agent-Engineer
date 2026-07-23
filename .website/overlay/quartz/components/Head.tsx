import { i18n } from "../i18n"
import { FullSlug, getFileExtension, joinSegments, pathToRoot } from "../util/path"
import { CSSResourceToStyleElement, JSResourceToScriptElement } from "../util/resources"
import { googleFontHref, googleFontSubsetHref } from "../util/theme"
import { QuartzComponent, QuartzComponentConstructor, QuartzComponentProps } from "./types"
import { unescapeHTML } from "../util/escape"
import { CustomOgImagesEmitterName } from "../../.quartz/plugins"

function languageTag(value: unknown) {
  return String(value ?? "").toLowerCase().startsWith("en") ? "en" : "zh-CN"
}

function localizedUrl(baseUrl: URL, route: unknown) {
  if (typeof route !== "string" || !route.trim()) return undefined
  const root = baseUrl.pathname.replace(/\/(?:zh-CN|en)\/?$/, "").replace(/\/$/, "")
  const normalizedRoute = route.replace(/^\/+/, "")
  const homepageRoute = /^(?:zh-CN|en)$/.test(normalizedRoute)
    ? `${normalizedRoute}/`
    : normalizedRoute
  return new URL(`${root}/${homepageRoute}`, baseUrl).toString()
}

export default (() => {
  const Head: QuartzComponent = ({ cfg, fileData, externalResources, ctx }: QuartzComponentProps) => {
    const titleSuffix = cfg.pageTitleSuffix ?? ""
    const title = (fileData.frontmatter?.title ?? i18n(cfg.locale).propertyDefaults.title) + titleSuffix
    const description =
      fileData.frontmatter?.socialDescription ??
      fileData.frontmatter?.description ??
      unescapeHTML(fileData.description?.trim() ?? i18n(cfg.locale).propertyDefaults.description)
    const { css, js, additionalHead } = externalResources
    const url = new URL(`https://${cfg.baseUrl ?? "example.com"}`)
    const path = url.pathname as FullSlug
    const baseDir = fileData.slug === "404" ? path : pathToRoot(fileData.slug!)
    const iconPath = joinSegments(baseDir, "static/icon.png")
    const localePath = url.pathname.replace(/\/$/, "")
    const canonicalPath = fileData.slug === "404" || fileData.slug === "index"
      ? `${localePath}/`
      : `${localePath}/${fileData.slug}`
    const canonicalUrl = new URL(canonicalPath, url).toString()
    const locale = languageTag(fileData.frontmatter?.lang ?? cfg.locale)
    const alternateLocale = locale === "en" ? "zh-CN" : "en"
    const alternateUrl = localizedUrl(url, fileData.frontmatter?.translation_route)
    const defaultUrl = localizedUrl(url, fileData.frontmatter?.translation_default_route) ?? canonicalUrl
    const usesCustomOgImage = ctx.cfg.plugins.emitters.some((emitter) => emitter.name === CustomOgImagesEmitterName)
    const ogImageDefaultPath = `https://${cfg.baseUrl}/static/og-image.png`

    return (
      <head>
        <title>{title}</title>
        <meta charSet="utf-8" />
        {cfg.theme.cdnCaching && cfg.theme.fontOrigin === "googleFonts" && (
          <>
            <link rel="preconnect" href="https://fonts.googleapis.com" />
            <link rel="preconnect" href="https://fonts.gstatic.com" />
            <link rel="stylesheet" href={googleFontHref(cfg.theme)} />
            {cfg.theme.typography.title && <link rel="stylesheet" href={googleFontSubsetHref(cfg.theme, cfg.pageTitle)} />}
          </>
        )}
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
        <meta name="og:site_name" content={cfg.pageTitle} />
        <meta property="og:title" content={title} />
        <meta property="og:type" content="website" />
        <meta name="twitter:card" content="summary_large_image" />
        <meta name="twitter:title" content={title} />
        <meta name="twitter:description" content={description} />
        <meta property="og:description" content={description} />
        <meta property="og:image:alt" content={description} />
        {!usesCustomOgImage && (
          <>
            <meta property="og:image" content={ogImageDefaultPath} />
            <meta property="og:image:url" content={ogImageDefaultPath} />
            <meta name="twitter:image" content={ogImageDefaultPath} />
            <meta property="og:image:type" content={`image/${getFileExtension(ogImageDefaultPath) ?? "png"}`} />
          </>
        )}
        {cfg.baseUrl && (
          <>
            <meta property="twitter:domain" content={cfg.baseUrl} />
            <meta property="og:url" content={canonicalUrl} />
            <meta property="twitter:url" content={canonicalUrl} />
          </>
        )}
        <link rel="canonical" href={canonicalUrl} />
        <link rel="alternate" hrefLang={locale} href={canonicalUrl} />
        {alternateUrl && <link rel="alternate" hrefLang={alternateLocale} href={alternateUrl} />}
        <link rel="alternate" hrefLang="x-default" href={defaultUrl} />
        <link rel="icon" href={iconPath} />
        <meta name="description" content={description} />
        <meta name="generator" content="Quartz" />
        {css.map((resource) => CSSResourceToStyleElement(resource, true))}
        {js.filter((resource) => resource.loadTime === "beforeDOMReady").map((resource) => JSResourceToScriptElement(resource, true))}
        {additionalHead.map((resource) => typeof resource === "function" ? resource(fileData) : resource)}
      </head>
    )
  }
  return Head
}) satisfies QuartzComponentConstructor
