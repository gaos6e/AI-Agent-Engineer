import { QuartzComponent, QuartzComponentConstructor, QuartzComponentProps } from "./types"
import { resolveRelative } from "../util/path"
import styles from "./styles/site-header.scss"
import { localeCopy, uiLocale } from "./locale-copy"
// @ts-ignore Quartz's esbuild loader imports `.inline.ts` files as source text.
import script from "./scripts/site-enhancements.inline"

function pageByRelativePath(allFiles: QuartzComponentProps["allFiles"], target: string) {
  return allFiles.find((file) => file.relativePath?.replaceAll("\\", "/") === target)
}

function siteHref(cfg: QuartzComponentProps["cfg"], route: string) {
  const configured = new URL(`https://${cfg.baseUrl ?? "example.com"}`)
  const root = configured.pathname.replace(/\/(?:zh-CN|en)\/?$/, "").replace(/\/$/, "")
  const normalizedRoute = route.replace(/^\/+/, "")
  const homepageRoute = /^(?:zh-CN|en)$/.test(normalizedRoute)
    ? `${normalizedRoute}/`
    : normalizedRoute
  return `${root}/${homepageRoute}` || "/"
}

const SiteHeader: QuartzComponent = ({ cfg, fileData, allFiles }: QuartzComponentProps) => {
  const locale = uiLocale(cfg.locale)
  const copy = localeCopy[locale]
  const home = pageByRelativePath(allFiles, "index.md")
  const roadmap = allFiles.find((file) => file.frontmatter?.site_page === "roadmap")
  const resources = allFiles.find((file) => file.frontmatter?.site_page === "resources")
  const current = fileData.slug!
  const showCourseNavigation = Boolean(fileData.relativePath) && fileData.slug !== "index"
  const counterpart = typeof fileData.frontmatter?.translation_route === "string"
    ? fileData.frontmatter.translation_route
    : locale === "en" ? "zh-CN" : "en"

  return (
    <div class="aae-site-header" data-aae-animate="site-header">
      <a
        class="aae-site-header__brand"
        href={home?.slug ? resolveRelative(current, home.slug) : "."}
        aria-label={copy.header.homeAria}
      >
        <span class="aae-site-header__mark" aria-hidden="true">AAE</span>
        <span class="aae-site-header__wordmark">AI Agent Engineer</span>
      </a>
      <nav class="aae-site-header__nav" aria-label={copy.header.navigationAria}>
        {roadmap?.slug && (
          <a href={resolveRelative(current, roadmap.slug)} class="aae-site-header__link">
            {copy.header.roadmap}
          </a>
        )}
        {resources?.slug && (
          <a href={resolveRelative(current, resources.slug)} class="aae-site-header__link">
            {copy.header.resources}
          </a>
        )}
        {showCourseNavigation && (
          <button
            type="button"
            class="aae-site-header__button aae-site-header__button--courses"
            data-aae-action="courses"
            aria-controls="aae-course-nav"
            aria-expanded="false"
          >
            {copy.header.courses}
          </button>
        )}
        <button
          type="button"
          class="aae-site-header__button aae-site-header__button--primary"
          data-aae-action="search"
        >
          <span>{copy.header.search}</span>
          <kbd>Ctrl K</kbd>
        </button>
        <button
          type="button"
          class="aae-site-header__button aae-site-header__button--compact"
          data-aae-action="theme"
          aria-label={copy.header.themeAria}
        >
          <span aria-hidden="true">◐</span>
          <span class="aae-site-header__theme-label">{copy.header.theme}</span>
        </button>
        <a
          class="aae-site-header__link aae-site-header__language"
          href={siteHref(cfg, counterpart)}
          aria-label={copy.header.switchAria}
          data-router-ignore
        >
          {copy.header.switch}
        </a>
      </nav>
    </div>
  )
}

SiteHeader.css = styles
SiteHeader.afterDOMLoaded = script

export default (() => SiteHeader) satisfies QuartzComponentConstructor
