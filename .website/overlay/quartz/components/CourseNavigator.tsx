import { QuartzComponent, QuartzComponentConstructor, QuartzComponentProps } from "./types"
import { resolveRelative } from "../util/path"
import styles from "./styles/course-navigator.scss"

type PageFile = QuartzComponentProps["allFiles"][number]

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
  domain: string
  catalogOrder: number
  tracks: Partial<Record<CourseTrackRole, CourseTrack>>
  tree: DirectoryNode
}

type CourseTrackRole = "agent_app" | "rag" | "agent_platform" | "multimodal_realtime"
type CourseTrackKind = "core" | "recommended" | "optional"
type CourseTrack = { order: number; kind: CourseTrackKind }

const domainDefinitions = [
  ["foundations", "工程与数学基础"],
  ["model-and-context", "模型与上下文"],
  ["retrieval-and-data", "检索与数据"],
  ["multimodal", "多模态"],
  ["agent-runtime", "Agent 运行时"],
  ["framework-practice", "框架实践"],
  ["evaluation-reliability", "评测与可靠性"],
  ["safety-governance", "安全与治理"],
  ["production-ops", "生产运维"],
  ["frontier-reference", "前沿与参考"],
] as const

const trackDefinitions: ReadonlyArray<{ id: CourseTrackRole; label: string }> = [
  { id: "agent_app", label: "Agent 应用开发" },
  { id: "rag", label: "RAG 与知识库" },
  { id: "agent_platform", label: "Agent 平台与可靠性" },
  { id: "multimodal_realtime", label: "多模态与实时交互" },
]

const trackKindLabels: Record<CourseTrackKind, string> = {
  core: "核心",
  recommended: "推荐",
  optional: "可选",
}

const collator = new Intl.Collator("zh-CN", { numeric: true, sensitivity: "base" })

function normalizedRelativePath(file: QuartzComponentProps["fileData"]) {
  const relativePath = file.relativePath?.replaceAll("\\", "/")
  if (relativePath) return relativePath
  return file.slug ? `${file.slug}.md` : ""
}

function displayTitle(file: QuartzComponentProps["fileData"]) {
  const title = file.frontmatter?.title
  if (typeof title === "string" && title.trim()) return title
  const name = normalizedRelativePath(file).split("/").at(-1) ?? "文档"
  return name.replace(/\.md$/i, "")
}

function courseIndexName(file: QuartzComponentProps["fileData"]) {
  return normalizedRelativePath(file).match(/^([^/]+)\/00-目录\.md$/)?.[1]
}

function formatCatalogOrder(order: number) {
  const display = order / 100
  return Number.isInteger(display) ? String(display).padStart(2, "0") : String(display)
}

function courseTracks(file: PageFile) {
  const tracks: Partial<Record<CourseTrackRole, CourseTrack>> = {}
  for (const track of trackDefinitions) {
    const rawOrder = file.frontmatter?.[`ai_learning_track_${track.id}_order`]
    const rawKind = file.frontmatter?.[`ai_learning_track_${track.id}_kind`]
    const order = Number(rawOrder)
    const kind = String(rawKind ?? "") as CourseTrackKind
    if (Number.isSafeInteger(order) && order > 0 && kind in trackKindLabels) {
      tracks[track.id] = { order, kind }
    }
  }
  return tracks
}

function cleanFolderName(name: string) {
  return name.replace(/^\d{1,2}[-._、\s]+/, "") || name
}

function createDirectory(name = "", path = ""): DirectoryNode {
  return { name, path, count: 0, directories: new Map(), files: [] }
}

function buildCourseTree(courseName: string, files: PageFile[]) {
  const root = createDirectory()
  for (const file of files) {
    const relativePath = normalizedRelativePath(file)
    if (!relativePath.startsWith(`${courseName}/`) || !relativePath.endsWith(".md")) continue
    if (relativePath === `${courseName}/00-目录.md`) continue
    if (file.frontmatter?.third_party_stub === true) continue
    if (String(file.frontmatter?.title ?? "").startsWith("Folder:")) continue

    const segments = relativePath.slice(courseName.length + 1).split("/")
    segments.pop()
    root.count += 1
    let node = root
    for (const segment of segments) {
      const directoryPath = node.path ? `${node.path}/${segment}` : segment
      if (!node.directories.has(segment)) {
        node.directories.set(segment, createDirectory(segment, directoryPath))
      }
      node = node.directories.get(segment)!
      node.count += 1
    }
    node.files.push(file)
  }
  return root
}

function pageLabel(file: PageFile) {
  return normalizedRelativePath(file).endsWith("/00-目录.md") ? "本节目录" : displayTitle(file)
}

function renderTreeEntries(
  node: DirectoryNode,
  courseName: string,
  currentPath: string,
  currentSlug: QuartzComponentProps["fileData"]["slug"],
  sourceSlug: NonNullable<QuartzComponentProps["fileData"]["slug"]>,
  depth = 0,
) {
  const entries = [
    ...[...node.directories.values()].map((directory) => ({
      kind: "directory" as const,
      name: directory.name,
      directory,
    })),
    ...node.files.map((file) => ({
      kind: "file" as const,
      name: normalizedRelativePath(file).split("/").at(-1) ?? displayTitle(file),
      file,
    })),
  ].sort((left, right) => collator.compare(left.name, right.name))

  return entries.map((entry) => {
    if (entry.kind === "file") {
      return (
        <li class="aae-course-nav__page">
          <a
            href={resolveRelative(sourceSlug, entry.file.slug!)}
            aria-current={entry.file.slug === currentSlug ? "page" : undefined}
          >
            <span aria-hidden="true" class="aae-course-nav__page-mark" />
            <span>{pageLabel(entry.file)}</span>
          </a>
        </li>
      )
    }

    const active = currentPath.startsWith(`${courseName}/${entry.directory.path}/`)
    return (
      <li class="aae-course-nav__folder">
        <details open={active} data-nav-folder={entry.directory.path}>
          <summary>
            <span class="aae-course-nav__chevron" aria-hidden="true" />
            <strong>{cleanFolderName(entry.directory.name)}</strong>
            <span class="aae-course-nav__count">{entry.directory.count}</span>
          </summary>
          <ol data-nav-depth={String(depth + 1)}>
            {renderTreeEntries(
              entry.directory,
              courseName,
              currentPath,
              currentSlug,
              sourceSlug,
              depth + 1,
            )}
          </ol>
        </details>
      </li>
    )
  })
}

const CourseNavigator: QuartzComponent = ({ fileData, allFiles }: QuartzComponentProps) => {
  if (fileData.slug === "index") return null

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
    return [{
      file,
      id,
      name,
      domain,
      catalogOrder,
      tracks: courseTracks(file),
      tree: buildCourseTree(name, pagesByCourse.get(name) ?? []),
    }]
  })
    .sort((left, right) => left.catalogOrder - right.catalogOrder)

  const domains = domainDefinitions.filter(([domain]) =>
    courses.some((course) => course.domain === domain),
  )
  const activeDomain = courses.find((course) => course.name === activeCourse)?.domain

  return (
    <nav id="aae-course-nav" class="aae-course-nav" aria-label="AI Agent Engineer v2 课程目录与角色路径">
      <button
        class="aae-course-nav__scrim"
        type="button"
        data-aae-action="close-courses"
        aria-label="关闭课程目录"
        tabIndex={-1}
      />
      <div class="aae-course-nav__panel" data-aae-course-panel tabIndex={-1}>
        <div class="aae-course-nav__heading">
          <div>
            <span>COURSE CATALOG</span>
            <strong>{domains.length} 个知识域 · {courses.length} 个课程入口 · {trackDefinitions.length} 条角色路径</strong>
          </div>
          <button type="button" data-aae-action="close-courses" aria-label="关闭课程目录">
            <span aria-hidden="true">×</span>
          </button>
        </div>
        <div class="aae-course-nav__stages">
          <section class="aae-course-nav__tracks" aria-labelledby="aae-course-nav-tracks">
            <h2 id="aae-course-nav-tracks">ROLE PATHS</h2>
            {trackDefinitions.map((track) => {
              const trackCourses = courses
                .filter((course) => course.tracks[track.id])
                .sort((left, right) => left.tracks[track.id]!.order - right.tracks[track.id]!.order)
              return (
                <details class="aae-course-nav__track" data-nav-track={track.id}>
                  <summary>
                    <span class="aae-course-nav__chevron" aria-hidden="true" />
                    <strong>{track.label}</strong>
                    <span class="aae-course-nav__count">{trackCourses.length}</span>
                  </summary>
                  <ol>
                    {trackCourses.map((course) => {
                      const courseTrack = course.tracks[track.id]!
                      return (
                        <li>
                          <a
                            href={resolveRelative(fileData.slug!, course.file.slug!)}
                            aria-current={course.name === activeCourse ? "page" : undefined}
                          >
                            <strong>{course.name}</strong>
                            <span data-track-kind={courseTrack.kind}>
                              {trackKindLabels[courseTrack.kind]}
                            </span>
                          </a>
                        </li>
                      )
                    })}
                  </ol>
                </details>
              )
            })}
          </section>
          <h2 class="aae-course-nav__catalog-label">KNOWLEDGE DOMAINS</h2>
          {domains.map(([domain, domainLabel], domainIndex) => {
            const domainCourses = courses.filter((course) => course.domain === domain)
            return (
              <details
                class="aae-course-nav__stage"
                open={activeDomain ? activeDomain === domain : domainIndex === 0}
                data-nav-domain={domain}
              >
                <summary>
                  <span class="aae-course-nav__chevron" aria-hidden="true" />
                  <span class="aae-course-nav__stage-number">
                    {String(domainIndex + 1).padStart(2, "0")}
                  </span>
                  <strong>{domainLabel}</strong>
                  <span class="aae-course-nav__count">{domainCourses.length}</span>
                </summary>
                <ol class="aae-course-nav__courses">
                  {domainCourses.map((course) => {
                    const active = course.name === activeCourse
                    return (
                      <li class={active ? "is-active" : undefined}>
                        <details class="aae-course-nav__course" open={active} data-nav-course={course.name}>
                          <summary>
                            <span class="aae-course-nav__chevron" aria-hidden="true" />
                            <span class="aae-course-nav__course-number">
                              {formatCatalogOrder(course.catalogOrder)}
                            </span>
                            <strong>{course.name}</strong>
                          </summary>
                          <div class="aae-course-nav__course-content">
                            <a
                              class="aae-course-nav__overview"
                              href={resolveRelative(fileData.slug!, course.file.slug!)}
                              aria-current={course.file.slug === fileData.slug ? "page" : undefined}
                            >
                              <span aria-hidden="true">↳</span>
                              <strong>课程总览</strong>
                            </a>
                            {course.tree.count > 0 && (
                              <ol class="aae-course-nav__tree" data-nav-depth="0">
                                {renderTreeEntries(
                                  course.tree,
                                  course.name,
                                  currentPath,
                                  fileData.slug,
                                  fileData.slug!,
                                )}
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
