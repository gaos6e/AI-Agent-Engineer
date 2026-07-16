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
  name: string
  stage: string
  order: number
  tree: DirectoryNode
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

  const courses: CourseRecord[] = allFiles
    .filter((file) => file.frontmatter?.ai_learning_stage && file.frontmatter?.ai_learning_order)
    .map((file) => {
      const name = normalizedRelativePath(file).split("/")[0]
      return {
        file,
        name,
        stage: String(file.frontmatter!.ai_learning_stage),
        order: Number(file.frontmatter!.ai_learning_order),
        tree: buildCourseTree(name, pagesByCourse.get(name) ?? []),
      }
    })
    .sort((left, right) => left.order - right.order)

  const stages = [...new Set(courses.map((course) => course.stage))]
  const activeStage = courses.find((course) => course.name === activeCourse)?.stage

  return (
    <nav id="aae-course-nav" class="aae-course-nav" aria-label="AI Agent Engineer 学习路线">
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
            <span>LEARNING ROADMAP</span>
            <strong>8 阶段 · 53 个学习重点</strong>
          </div>
          <button type="button" data-aae-action="close-courses" aria-label="关闭课程目录">
            <span aria-hidden="true">×</span>
          </button>
        </div>
        <div class="aae-course-nav__stages">
          {stages.map((stage, stageIndex) => {
            const stageCourses = courses.filter((course) => course.stage === stage)
            return (
              <details
                class="aae-course-nav__stage"
                open={activeStage ? activeStage === stage : stageIndex === 0}
                data-nav-stage={String(stageIndex + 1)}
              >
                <summary>
                  <span class="aae-course-nav__chevron" aria-hidden="true" />
                  <span class="aae-course-nav__stage-number">
                    {String(stageIndex + 1).padStart(2, "0")}
                  </span>
                  <strong>{stage.replace(/^\d+\.\s*/, "")}</strong>
                  <span class="aae-course-nav__count">{stageCourses.length}</span>
                </summary>
                <ol class="aae-course-nav__courses">
                  {stageCourses.map((course) => {
                    const active = course.name === activeCourse
                    return (
                      <li class={active ? "is-active" : undefined}>
                        <details class="aae-course-nav__course" open={active} data-nav-course={course.name}>
                          <summary>
                            <span class="aae-course-nav__chevron" aria-hidden="true" />
                            <span class="aae-course-nav__course-number">
                              {String(course.order).padStart(2, "0")}
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
