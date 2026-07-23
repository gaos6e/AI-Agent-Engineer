import { QuartzComponent, QuartzComponentConstructor, QuartzComponentProps } from "./types"
import { resolveRelative } from "../util/path"
import styles from "./styles/homepage.scss"
import { localeCopy, uiLocale } from "./locale-copy"

type CourseTrackRole = "agent_app" | "rag" | "agent_platform" | "multimodal_realtime"
type CourseTrackKind = "core" | "recommended" | "optional"
type Course = {
  name: string
  title: string
  domain: string
  catalogOrder: number
  tracks: Partial<Record<CourseTrackRole, CourseTrackKind>>
  slug: NonNullable<QuartzComponentProps["fileData"]["slug"]>
}

const trackRoles: CourseTrackRole[] = ["agent_app", "rag", "agent_platform", "multimodal_realtime"]

function courseIndexName(file: QuartzComponentProps["fileData"]) {
  const segments = file.relativePath?.replaceAll("\\", "/").split("/")
  return segments?.length === 2 && segments[1].endsWith(".md") ? segments[0] : undefined
}

function getCourses(allFiles: QuartzComponentProps["allFiles"]): Course[] {
  return allFiles.flatMap((file) => {
    const name = courseIndexName(file)
    const schema = Number(file.frontmatter?.ai_learning_schema)
    const domain = String(file.frontmatter?.ai_learning_domain ?? "").trim()
    const catalogOrder = Number(file.frontmatter?.ai_learning_catalog_order)
    if (!name || schema !== 2 || !domain || !Number.isSafeInteger(catalogOrder) || !file.slug) return []
    const tracks: Partial<Record<CourseTrackRole, CourseTrackKind>> = {}
    for (const role of trackRoles) {
      const order = Number(file.frontmatter?.[`ai_learning_track_${role}_order`])
      const kind = String(file.frontmatter?.[`ai_learning_track_${role}_kind`] ?? "") as CourseTrackKind
      if (Number.isSafeInteger(order) && order > 0 && ["core", "recommended", "optional"].includes(kind)) {
        tracks[role] = kind
      }
    }
    const title = typeof file.frontmatter?.title === "string" && file.frontmatter.title.trim()
      ? file.frontmatter.title.trim()
      : name
    return [{ name, title, domain, catalogOrder, tracks, slug: file.slug }]
  }).sort((left, right) => left.catalogOrder - right.catalogOrder)
}

function formatCatalogOrder(order: number) {
  const display = order / 100
  return Number.isInteger(display) ? String(display).padStart(2, "0") : String(display)
}

function numericStat(value: unknown, fallback: number) {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : fallback
}

const Homepage: QuartzComponent = ({ cfg, fileData, allFiles }: QuartzComponentProps) => {
  if (fileData.slug !== "index") return null
  const locale = uiLocale(cfg.locale)
  const copy = localeCopy[locale]
  const domains = copy.domains.map(([id, label, description]) => ({ id, label, description }))
  const roles = copy.roles.map(([id, label, description]) => ({ id: id as CourseTrackRole, label, description }))
  const current = fileData.slug
  const courses = getCourses(allFiles)
  const visibleDomains = domains.filter((domain) => courses.some((course) => course.domain === domain.id))
  const roadmap = allFiles.find((file) => file.frontmatter?.site_page === "roadmap")
  const notices = allFiles.find((file) => file.frontmatter?.site_page === "third-party-notices")
  const discoveredDocuments = allFiles.filter((file) => file.relativePath?.endsWith(".md")).length
  const sourceDocuments = numericStat(fileData.frontmatter?.site_source_document_count, discoveredDocuments)
  const fullDocuments = numericStat(fileData.frontmatter?.site_full_document_count, sourceDocuments)
  const sourceStubs = numericStat(fileData.frontmatter?.site_stub_count, 0)
  const assets = numericStat(fileData.frontmatter?.site_asset_count, 0)

  return (
    <main class="aae-home">
      <section class="aae-hero" aria-labelledby="aae-home-title">
        <div class="aae-hero__content">
          <p class="aae-eyebrow" data-aae-hero="eyebrow">{copy.home.eyebrow}</p>
          <h1 id="aae-home-title" data-aae-hero="title">
            {copy.home.title} <span>AI Agent</span>
          </h1>
          <p class="aae-hero__lead" data-aae-hero="lead">
            {copy.home.lead} {courses.length} {copy.home.leadAfter} {visibleDomains.length} {copy.home.leadEnd}
          </p>
          <div class="aae-hero__actions" data-aae-hero="actions">
            {roadmap?.slug && (
              <a class="aae-button aae-button--primary" href={resolveRelative(current, roadmap.slug)}>
                {copy.home.roadmap}
              </a>
            )}
            <button class="aae-button aae-button--secondary" type="button" data-aae-action="search">
              {copy.home.search}
            </button>
          </div>
        </div>

        <div class="aae-hero__board" data-aae-hero="board" aria-hidden="true">
          <div class="aae-sticky aae-sticky--lilac"><span>01 · BUILD</span><strong>{copy.home.sticky[0]}</strong></div>
          <div class="aae-sticky aae-sticky--lime"><span>02 · GROUND</span><strong>{copy.home.sticky[1]}</strong></div>
          <div class="aae-sticky aae-sticky--coral"><span>03 · EVALUATE</span><strong>{copy.home.sticky[2]}</strong></div>
          <div class="aae-sticky aae-sticky--navy"><span>04 · SHIP</span><strong>{copy.home.sticky[3]}</strong></div>
        </div>
      </section>

      <aside class="aae-marquee" aria-label={copy.home.statsAria}>
        <dl>
          <div><dt>{String(visibleDomains.length).padStart(2, "0")}</dt><dd>{copy.home.stats[0]}</dd></div>
          <div><dt>{String(courses.length).padStart(2, "0")}</dt><dd>{copy.home.stats[1]}</dd></div>
          <div><dt>{sourceDocuments}</dt><dd>{copy.home.stats[2]}</dd></div>
          <div><dt>{fullDocuments}</dt><dd>{copy.home.stats[3]}</dd></div>
        </dl>
        <p aria-hidden="true">BUILD · OBSERVE · EVALUATE · SHIP · ITERATE</p>
      </aside>

      <section class="aae-home-section aae-role-system" aria-labelledby="aae-role-title">
        <div class="aae-section-heading">
          <div>
            <p class="aae-eyebrow">{copy.home.roleEyebrow}</p>
            <h2 id="aae-role-title">{copy.home.roleTitle}</h2>
          </div>
          <p>{copy.home.roleDescription}</p>
        </div>
        <div class="aae-role-grid">
          {roles.map((role, index) => {
            const roleCourses = courses.filter((course) => course.tracks[role.id])
            const core = roleCourses.filter((course) => course.tracks[role.id] === "core").length
            const recommended = roleCourses.filter((course) => course.tracks[role.id] === "recommended").length
            const optional = roleCourses.filter((course) => course.tracks[role.id] === "optional").length
            return roadmap?.slug ? (
              <a href={resolveRelative(current, roadmap.slug)} data-aae-reveal="role">
                <span>{String(index + 1).padStart(2, "0")}</span>
                <strong>{role.label}</strong>
                <p>{role.description}</p>
                <small>{core} {copy.home.core} · {recommended} {copy.home.recommended} · {optional} {copy.home.optional}</small>
                <i aria-hidden="true">↗</i>
              </a>
            ) : null
          })}
        </div>
      </section>

      <section class="aae-home-section aae-stage-system" aria-labelledby="aae-stage-title">
        <div class="aae-section-heading">
          <div>
            <p class="aae-eyebrow">{copy.home.systemEyebrow}</p>
            <h2 id="aae-stage-title">{visibleDomains.length} {copy.home.systemTitleSuffix}</h2>
          </div>
          <p>{copy.home.systemDescription}</p>
        </div>
        <div class="aae-stage-grid">
          {visibleDomains.map((domain, index) => {
            const domainCourses = courses.filter((course) => course.domain === domain.id)
            const first = domainCourses[0]
            return (
              <a class="aae-stage-card" data-aae-reveal="stage" data-stage={String(index + 1)} href={resolveRelative(current, first.slug)}>
                <span class="aae-stage-card__number">{String(index + 1).padStart(2, "0")}</span>
                <span class="aae-stage-card__body"><strong>{domain.label}</strong><span>{domain.description}</span></span>
                <span class="aae-stage-card__count">{domainCourses.length} {copy.home.courseCount}</span>
                <span class="aae-stage-card__arrow" aria-hidden="true">↗</span>
              </a>
            )
          })}
        </div>
      </section>

      <section class="aae-home-section aae-course-map" aria-labelledby="aae-course-title">
        <div class="aae-section-heading">
          <div>
            <p class="aae-eyebrow">{courses.length} {copy.home.coursesEyebrow}</p>
            <h2 id="aae-course-title">{copy.home.coursesTitle}</h2>
          </div>
          <p>{copy.home.coursesDescription}</p>
        </div>
        <div class="aae-course-map__stages">
          {visibleDomains.map((domain, domainIndex) => (
            <section class="aae-course-stage" data-aae-reveal="course-stage">
              <header><span>{String(domainIndex + 1).padStart(2, "0")}</span><h3>{domain.label}</h3></header>
              <div class="aae-course-stage__links">
                {courses.filter((course) => course.domain === domain.id).map((course) => (
                  <a href={resolveRelative(current, course.slug)}><span>{formatCatalogOrder(course.catalogOrder)}</span><strong>{course.title}</strong><i aria-hidden="true">↗</i></a>
                ))}
              </div>
            </section>
          ))}
        </div>
      </section>

      <aside class="aae-publishing-note" data-aae-reveal="note">
        <div><span class="aae-publishing-note__label">{copy.home.publicationEyebrow}</span><h2>{copy.home.publicationTitle}</h2></div>
        <div>
          <p>{copy.home.publicationLead}{sourceStubs}{copy.home.publicationMiddle}{assets}{copy.home.publicationEnd}</p>
          {notices?.slug && (
            <a class="aae-button aae-button--inverse" href={resolveRelative(current, notices.slug)}>{copy.home.notices}</a>
          )}
        </div>
      </aside>
    </main>
  )
}

Homepage.css = styles

export default (() => Homepage) satisfies QuartzComponentConstructor
