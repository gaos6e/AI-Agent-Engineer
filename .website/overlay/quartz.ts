import { loadQuartzConfig, loadQuartzLayout } from "./quartz/plugins/loader/config-loader"
import { PageTypes } from "./quartz/plugins"
import type { FullPageLayout } from "./quartz/cfg"
import Homepage from "./quartz/components/Homepage"
import SiteHeader from "./quartz/components/SiteHeader"
import CourseNavigator from "./quartz/components/CourseNavigator"

const config = await loadQuartzConfig()
const baseLayout = await loadQuartzLayout()

const homepage = Homepage()
const siteHeader = SiteHeader()
const courseNavigator = CourseNavigator()

function withSiteShell(layout: Partial<FullPageLayout>, includeCourses = true) {
  return {
    ...layout,
    header: [siteHeader],
    beforeBody: [homepage, ...(layout.beforeBody ?? [])],
    left: includeCourses ? [...(layout.left ?? []), courseNavigator] : (layout.left ?? []),
  }
}

const defaults = withSiteShell(baseLayout.defaults)
const byPageType = Object.fromEntries(
  Object.entries(baseLayout.byPageType).map(([pageType, pageLayout]) => [
    pageType,
    withSiteShell(pageLayout, pageType !== "404"),
  ]),
)

const dispatcher = PageTypes.PageTypeDispatcher({ defaults, byPageType })
config.plugins.emitters = config.plugins.emitters.map((emitter) =>
  emitter.name === "PageTypeDispatcher" ? dispatcher : emitter,
)

export default config
export const layout = { defaults, byPageType }
