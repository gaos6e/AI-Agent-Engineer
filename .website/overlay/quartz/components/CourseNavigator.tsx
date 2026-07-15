import { QuartzComponent, QuartzComponentConstructor, QuartzComponentProps } from "./types"
import { resolveRelative } from "../util/path"
import styles from "./styles/course-navigator.scss"

function normalizedRelativePath(file: QuartzComponentProps["fileData"]) {
  return file.relativePath?.replaceAll("\\", "/") ?? ""
}

function displayTitle(file: QuartzComponentProps["fileData"]) {
  const title = file.frontmatter?.title
  if (typeof title === "string" && title.trim()) return title
  const name = normalizedRelativePath(file).split("/").at(-1) ?? "文档"
  return name.replace(/\.md$/i, "")
}

const CourseNavigator: QuartzComponent = ({ fileData, allFiles }: QuartzComponentProps) => {
  const currentPath = normalizedRelativePath(fileData)
  const activeCourse = currentPath.includes("/") ? currentPath.split("/")[0] : ""
  const courses = allFiles
    .filter((file) => file.frontmatter?.ai_learning_stage && file.frontmatter?.ai_learning_order)
    .map((file) => ({
      file,
      name: normalizedRelativePath(file).split("/")[0],
      stage: String(file.frontmatter!.ai_learning_stage),
      order: Number(file.frontmatter!.ai_learning_order),
    }))
    .sort((left, right) => left.order - right.order)
  const stages = [...new Set(courses.map((course) => course.stage))]
  const activeStage = courses.find((course) => course.name === activeCourse)?.stage
  const activePages = activeCourse
    ? allFiles
        .filter((file) => {
          const path = normalizedRelativePath(file)
          return path.startsWith(`${activeCourse}/`) &&
            path.endsWith(".md") &&
            !path.endsWith("/00-目录.md") &&
            file.frontmatter?.third_party_stub !== true
        })
        .sort((left, right) =>
          normalizedRelativePath(left).localeCompare(normalizedRelativePath(right), "zh-CN", {
            numeric: true,
          }),
        )
    : []

  return (
    <nav class="aae-course-nav" aria-label="八阶段课程导航">
      <div class="aae-course-nav__heading">
        <span>ROADMAP</span>
        <strong>8 阶段 · 53 知识库</strong>
      </div>
      <div class="aae-course-nav__stages">
        {stages.map((stage, index) => (
          <details open={activeStage ? activeStage === stage : index === 0}>
            <summary>
              <span>{String(index + 1).padStart(2, "0")}</span>
              <strong>{stage.replace(/^\d+\.\s*/, "")}</strong>
            </summary>
            <ol>
              {courses.filter((course) => course.stage === stage).map((course) => {
                const active = course.name === activeCourse
                return (
                  <li class={active ? "is-active" : undefined}>
                    <a
                      href={resolveRelative(fileData.slug!, course.file.slug!)}
                      aria-current={course.file.slug === fileData.slug ? "page" : undefined}
                    >
                      <span>{String(course.order).padStart(2, "0")}</span>
                      <strong>{course.name}</strong>
                    </a>
                    {active && activePages.length > 0 && (
                      <ol class="aae-course-nav__pages" aria-label={`${course.name}文档`}>
                        {activePages.map((page) => (
                          <li>
                            <a
                              href={resolveRelative(fileData.slug!, page.slug!)}
                              aria-current={page.slug === fileData.slug ? "page" : undefined}
                            >
                              {displayTitle(page)}
                            </a>
                          </li>
                        ))}
                      </ol>
                    )}
                  </li>
                )
              })}
            </ol>
          </details>
        ))}
      </div>
    </nav>
  )
}

CourseNavigator.css = styles

export default (() => CourseNavigator) satisfies QuartzComponentConstructor
