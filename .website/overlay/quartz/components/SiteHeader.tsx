import { QuartzComponent, QuartzComponentConstructor, QuartzComponentProps } from "./types"
import { resolveRelative } from "../util/path"
import styles from "./styles/site-header.scss"
// @ts-ignore Quartz's esbuild loader imports `.inline.ts` files as source text.
import script from "./scripts/site-enhancements.inline"

function pageByRelativePath(allFiles: QuartzComponentProps["allFiles"], target: string) {
  return allFiles.find((file) => file.relativePath?.replaceAll("\\", "/") === target)
}

const SiteHeader: QuartzComponent = ({ fileData, allFiles }: QuartzComponentProps) => {
  const home = pageByRelativePath(allFiles, "index.md")
  const roadmap = pageByRelativePath(allFiles, "All of AI.md")
  const resources = pageByRelativePath(allFiles, "资源索引.md")
  const current = fileData.slug!

  return (
    <div class="aae-site-header" data-aae-animate="site-header">
      <a
        class="aae-site-header__brand"
        href={home?.slug ? resolveRelative(current, home.slug) : "."}
        aria-label="AI Agent Engineer 首页"
      >
        <span class="aae-site-header__mark" aria-hidden="true">AAE</span>
        <span class="aae-site-header__wordmark">AI Agent Engineer</span>
      </a>
      <nav class="aae-site-header__nav" aria-label="网站主导航">
        {roadmap?.slug && (
          <a href={resolveRelative(current, roadmap.slug)} class="aae-site-header__link">
            完整路线
          </a>
        )}
        {resources?.slug && (
          <a href={resolveRelative(current, resources.slug)} class="aae-site-header__link">
            示例资源
          </a>
        )}
        <button type="button" class="aae-site-header__button" data-aae-action="search">
          <span>搜索</span>
          <kbd>Ctrl K</kbd>
        </button>
        <button
          type="button"
          class="aae-site-header__button aae-site-header__button--compact"
          data-aae-action="theme"
          aria-label="切换明暗主题"
        >
          主题
        </button>
      </nav>
    </div>
  )
}

SiteHeader.css = styles
SiteHeader.afterDOMLoaded = script

export default (() => SiteHeader) satisfies QuartzComponentConstructor
