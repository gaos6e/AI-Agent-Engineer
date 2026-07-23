import { QuartzComponent, QuartzComponentConstructor, QuartzComponentProps } from "./types"
import { resolveRelative } from "../util/path"
import styles from "./styles/course-navigator.scss"
import { localeCopy, uiLocale } from "./locale-copy"

type PageFile = QuartzComponentProps["allFiles"][number]
type CourseTrackRole = "agent_app" | "rag" | "agent_platform" | "multimodal_realtime"
type CourseTrackKind = "core" | "recommended" | "optional"
type CourseTrack = { order: number; kind: CourseTrackKind }
type DirectoryNode = {
  name: string
  path: string
  count: number
  directories: Map<string, DirectoryNode>
  files: PageFile[]
}
type CourseRecord = {
  file: PageFile
  id: string
  name: string
  title: string
  domain: string
  catalogOrder: number
  tracks: Partial<Record<CourseTrackRole, CourseTrack>>
  tree: DirectoryNode
}

const trackRoles: CourseTrackRole[] = ["agent_app", "rag", "agent_platform", "multimodal_realtime"]

function normalizedRelativePath(file: QuartzComponentProps["fileData"]) {
  const relativePath = file.relativePath?.replaceAll("\\", "/")
  return relativePath || (file.slug ? `${file.slug}.md` : "")
}

function displayTitle(file: QuartzComponentProps["fileData"]) {
  const title = file.frontmatter?.title
  if (typeof title === "string" && title.trim()) return title
  return (normalizedRelativePath(file).split("/").at(-1) ?? "Document").replace(/\.md$/i, "")
}

function courseIndexName(file: QuartzComponentProps["fileData"]) {
  const segments = normalizedRelativePath(file).split("/")
  if (segments.length !== 2 || !segments[1].endsWith(".md")) return undefined
  return typeof file.frontmatter?.ai_learning_id === "string" ? segments[0] : undefined
}

function formatCatalogOrder(order: number) {
  const display = order / 100
  return Number.isInteger(display) ? String(display).padStart(2, "0") : String(display)
}

function courseTracks(file: PageFile) {
  const tracks: Partial<Record<CourseTrackRole, CourseTrack>> = {}
  for (const role of trackRoles) {
    const order = Number(file.frontmatter?.[`ai_learning_track_${role}_order`])
    const kind = String(file.frontmatter?.[`ai_learning_track_${role}_kind`] ?? "") as CourseTrackKind
    if (Number.isSafeInteger(order) && order > 0 && ["core", "recommended", "optional"].includes(kind)) {
      tracks[role] = { order, kind }
    }
  }
  return tracks
}

function cleanFolderName(name: string, locale: "zh-CN" | "en") {
  const stripped = name.replace(/^\d{1,2}[-._、\s]+/, "") || name
  if (locale !== "en") return stripped
  return stripped.replace(/[-_]+/g, " ").replace(/\b[a-z]/g, (letter) => letter.toUpperCase())
}

function createDirectory(name = "", path = ""): DirectoryNode {
  return { name, path, count: 0, directories: new Map(), files: [] }
}

function buildCourseTree(courseName: string, files: PageFile[]) {
  const root = createDirectory()
  for (const file of files) {
    const relativePath = normalizedRelativePath(file)
    if (!relativePath.startsWith(`${courseName}/`) || !relativePath.endsWith(".md")) continue
    if (courseIndexName(file)) continue
    if (file.frontmatter?.third_party_stub === true) continue
    if (String(file.frontmatter?.title ?? "").startsWith("Folder:")) continue

    const segments = relativePath.slice(courseName.length + 1).split("/")
    segments.pop()
    root.count += 1
    let node = root
    for (const segment of segments) {
      const directoryPath = node.path ? `${node.path}/${segment}` : segment
      if (!node.directories.has(segment)) node.directories.set(segment, createDirectory(segment, directoryPath))
      node = node.directories.get(segment)!
      node.count += 1
    }
    node.files.push(file)
  }
  return root
}

function renderTreeEntries(
  node: DirectoryNode,
  courseName: string,
  currentPath: string,
  currentSlug: QuartzComponentProps["fileData"]["slug"],
  sourceSlug: NonNullable<QuartzComponentProps["fileData"]["slug"]>,
  sectionIndex: string,
  collator: Intl.Collator,
  locale: "zh-CN" | "en",
  depth = 0,
) {
  const entries = [
    ...[...node.directories.values()].map((directory) => ({ kind: "directory" as const, name: directory.name, directory })),
    ...node.files.map((file) => ({ kind: "file" as const, name: normalizedRelativePath(file).split("/").at(-1) ?? displayTitle(file), file })),
  ].sort((left, right) => collator.compare(left.name, right.name))

  return entries.map((entry) => {
    if (entry.kind === "file") {
      return (
        <li class="aae-course-nav__page">
          <a href={resolveRelative(sourceSlug, entry.file.slug!)} aria-current={entry.file.slug === currentSlug ? "page" : undefined}>
            <span aria-hidden="true" class="aae-course-nav__page-mark" />
            <span>{courseIndexName(entry.file) ? sectionIndex : displayTitle(entry.file)}</span>
          </a>
        </li>
      )
    }
    const active = currentPath.startsWith(`${courseName}/${entry.directory.path}/`)
    return (
      <li class="aae-course-nav__folder">
        <details open={active} data-nav-folder={entry.directory.path}>
          <summary><span class="aae-course-nav__chevron" aria-hidden="true" /><strong>{cleanFolderName(entry.directory.name, locale)}</strong><span class="aae-course-nav__count">{entry.directory.count}</span></summary>
          <ol data-nav-depth={String(depth + 1)}>
            {renderTreeEntries(entry.directory, courseName, currentPath, currentSlug, sourceSlug, sectionIndex, collator, locale, depth + 1)}
          </ol>
        </details>
      </li>
    )
  })
}

const CourseNavigator: QuartzComponent = ({ cfg, fileData, allFiles }: QuartzComponentProps) => {
  if (fileData.slug === "index") return null

  const locale = uiLocale(cfg.locale)
  const copy = localeCopy[locale]
  const collator = new Intl.Collator(locale === "en" ? "en" : "zh-CN", { numeric: true, sensitivity: "base" })
  const currentPath = normalizedRelativePath(fileData)
  const activeCourse = currentPath.includes("/") ? currentPath.split("/")[0] : ""
  const pagesByCourse = new Map<string, PageFile[]>()
  for (const file of allFiles) {
    const relativePath = file.relativePath?.replaceAll("\\", "/")
    if (!relativePath?.endsWith(".md") || !relativePath.includes("/")) continue
    const courseName = relativePath.split("/")[0]
    const pages = pagesByCourse.get(courseName) ?? []
    pages.push(file)
    pagesByCourse.set(courseName, pages)
  }

  const courses: CourseRecord[] = allFiles.flatMap((file) => {
    const name = courseIndexName(file)
    const schema = Number(file.frontmatter?.ai_learning_schema)
    const id = String(file.frontmatter?.ai_learning_id ?? "").trim()
    const domain = String(file.frontmatter?.ai_learning_domain ?? "").trim()
    const catalogOrder = Number(file.frontmatter?.ai_learning_catalog_order)
    if (!name || schema !== 2 || !id || !domain || !Number.isSafeInteger(catalogOrder)) return []
    return [{ file, id, name, title: displayTitle(file), domain, catalogOrder, tracks: courseTracks(file), tree: buildCourseTree(name, pagesByCourse.get(name) ?? []) }]
  }).sort((left, right) => left.catalogOrder - right.catalogOrder)

  const domains = copy.domains
    .map(([id, label]) => ({ id, label }))
    .filter((domain) => courses.some((course) => course.domain === domain.id))
  const tracks = copy.roles.map(([id, label]) => ({ id: id as CourseTrackRole, label }))
  const activeDomain = courses.find((course) => course.name === activeCourse)?.domain
  const headingSummary = copy.navigator.headingSummary
    .replace("{domains}", String(domains.length))
    .replace("{courses}", String(courses.length))
    .replace("{tracks}", String(tracks.length))

  return (
    <nav id="aae-course-nav" class="aae-course-nav" aria-label={copy.navigator.aria}>
      <button class="aae-course-nav__scrim" type="button" data-aae-action="close-courses" aria-label={copy.navigator.close} tabIndex={-1} />
      <div class="aae-course-nav__panel" data-aae-course-panel tabIndex={-1}>
        <div class="aae-course-nav__heading">
          <div><span>{copy.navigator.heading}</span><strong>{headingSummary}</strong></div>
          <button type="button" data-aae-action="close-courses" aria-label={copy.navigator.close}><span aria-hidden="true">×</span></button>
        </div>
        <div class="aae-course-nav__stages">
          <section class="aae-course-nav__tracks" aria-labelledby="aae-course-nav-tracks">
            <h2 id="aae-course-nav-tracks">{copy.navigator.tracks}</h2>
            {tracks.map((track) => {
              const trackCourses = courses
                .filter((course) => course.tracks[track.id])
                .sort((left, right) => left.tracks[track.id]!.order - right.tracks[track.id]!.order)
              return (
                <details class="aae-course-nav__track" data-nav-track={track.id}>
                  <summary><span class="aae-course-nav__chevron" aria-hidden="true" /><strong>{track.label}</strong><span class="aae-course-nav__count">{trackCourses.length}</span></summary>
                  <ol>
                    {trackCourses.map((course) => {
                      const courseTrack = course.tracks[track.id]!
                      return (
                        <li>
                          <a href={resolveRelative(fileData.slug!, course.file.slug!)} aria-current={course.name === activeCourse ? "page" : undefined}>
                            <strong>{course.title}</strong><span data-track-kind={courseTrack.kind}>{copy.trackKinds[courseTrack.kind]}</span>
                          </a>
                        </li>
                      )
                    })}
                  </ol>
                </details>
              )
            })}
          </section>
          <h2 class="aae-course-nav__catalog-label">{copy.navigator.domains}</h2>
          {domains.map((domain, domainIndex) => {
            const domainCourses = courses.filter((course) => course.domain === domain.id)
            return (
              <details class="aae-course-nav__stage" open={activeDomain ? activeDomain === domain.id : domainIndex === 0} data-nav-domain={domain.id}>
                <summary><span class="aae-course-nav__chevron" aria-hidden="true" /><span class="aae-course-nav__stage-number">{String(domainIndex + 1).padStart(2, "0")}</span><strong>{domain.label}</strong><span class="aae-course-nav__count">{domainCourses.length}</span></summary>
                <ol class="aae-course-nav__courses">
                  {domainCourses.map((course) => {
                    const active = course.name === activeCourse
                    return (
                      <li class={active ? "is-active" : undefined}>
                        <details class="aae-course-nav__course" open={active} data-nav-course={course.name}>
                          <summary><span class="aae-course-nav__chevron" aria-hidden="true" /><span class="aae-course-nav__course-number">{formatCatalogOrder(course.catalogOrder)}</span><strong>{course.title}</strong></summary>
                          <div class="aae-course-nav__course-content">
                            <a class="aae-course-nav__overview" href={resolveRelative(fileData.slug!, course.file.slug!)} aria-current={course.file.slug === fileData.slug ? "page" : undefined}>
                              <span aria-hidden="true">↳</span><strong>{copy.navigator.overview}</strong>
                            </a>
                            {course.tree.count > 0 && (
                              <ol class="aae-course-nav__tree" data-nav-depth="0">
                                {renderTreeEntries(course.tree, course.name, currentPath, fileData.slug, fileData.slug!, copy.navigator.sectionIndex, collator, locale)}
                              </ol>
                            )}
                          </div>
                        </details>
                      </li>
                    )
                  })}
                </ol>
              </details>
            )
          })}
        </div>
      </div>
    </nav>
  )
}

CourseNavigator.css = styles

export default (() => CourseNavigator) satisfies QuartzComponentConstructor
