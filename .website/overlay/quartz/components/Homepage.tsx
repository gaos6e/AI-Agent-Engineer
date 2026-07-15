import { QuartzComponent, QuartzComponentConstructor, QuartzComponentProps } from "./types"
import { resolveRelative } from "../util/path"
import styles from "./styles/homepage.scss"

type Course = {
  name: string
  stage: string
  order: number
  slug: NonNullable<QuartzComponentProps["fileData"]["slug"]>
}

const stageCopy: Record<string, { label: string; description: string }> = {
  "1. 工程基础": {
    label: "工程基础",
    description: "建立编程、命令行、版本控制与数据交换的可靠底座。",
  },
  "2. 数学与数据基础": {
    label: "数学与数据基础",
    description: "用最小数学直觉理解训练、向量、指标和数据质量。",
  },
  "3. LLM 应用基础": {
    label: "LLM 应用基础",
    description: "从提示词、上下文预算到可维护的模型 API 集成。",
  },
  "4. RAG 与知识库": {
    label: "RAG 与知识库",
    description: "完成解析、切分、检索、重排与可验证的生成链路。",
  },
  "5. 单 Agent 与工具": {
    label: "单 Agent 与工具",
    description: "让模型在权限、状态、停止条件和工具契约内可靠行动。",
  },
  "6. 框架实践": {
    label: "框架实践",
    description: "在理解底层模式后，用框架交付可测试的工程实现。",
  },
  "7. 生产化、评测与治理": {
    label: "生产化、评测与治理",
    description: "把质量、成本、安全、监控和组织责任放进生命周期。",
  },
  "8. 扩展应用与复杂协作": {
    label: "扩展应用与复杂协作",
    description: "进入多 Agent、多模态与生成媒体的复杂系统边界。",
  },
}

function getCourses(allFiles: QuartzComponentProps["allFiles"]): Course[] {
  return allFiles
    .filter((file) => file.frontmatter?.ai_learning_stage && file.frontmatter?.ai_learning_order)
    .map((file) => ({
      name: file.relativePath?.replaceAll("\\", "/").split("/")[0] ?? file.frontmatter!.title,
      stage: String(file.frontmatter!.ai_learning_stage),
      order: Number(file.frontmatter!.ai_learning_order),
      slug: file.slug!,
    }))
    .filter((course) => course.slug)
    .sort((left, right) => left.order - right.order)
}

const Homepage: QuartzComponent = ({ fileData, allFiles }: QuartzComponentProps) => {
  if (fileData.slug !== "index") return null
  const current = fileData.slug

  const courses = getCourses(allFiles)
  const stages = [...new Set(courses.map((course) => course.stage))]
  const roadmap = allFiles.find(
    (file) => file.relativePath?.replaceAll("\\", "/") === "All of AI.md",
  )
  const sourceDocuments = Number(fileData.frontmatter?.site_source_document_count ?? 844)
  const fullDocuments = Number(fileData.frontmatter?.site_full_document_count ?? sourceDocuments)
  const sourceStubs = Number(fileData.frontmatter?.site_stub_count ?? 0)
  const assets = Number(fileData.frontmatter?.site_asset_count ?? 0)

  return (
    <main class="aae-home">
      <section class="aae-hero" aria-labelledby="aae-home-title">
        <div class="aae-hero__signal" aria-hidden="true">
          <span>01</span><span>BUILD</span><span>OBSERVE</span><span>SHIP</span>
        </div>
        <div class="aae-hero__content">
          <p class="aae-eyebrow" data-aae-hero="eyebrow">OPEN ENGINEERING ROADMAP · 2026</p>
          <h1 id="aae-home-title" data-aae-hero="title">
            从零构建、评测与部署 <span>AI Agent</span>
          </h1>
          <p class="aae-hero__lead" data-aae-hero="lead">
            一套面向真实工程交付的中文学习知识库。沿 8 个阶段完成 53 个知识库，
            从 Python、API 与数据底座，走到 RAG、Agent、评测、治理和复杂协作。
          </p>
          <div class="aae-hero__actions" data-aae-hero="actions">
            {roadmap?.slug && (
              <a class="aae-button aae-button--primary" href={resolveRelative(current, roadmap.slug)}>
                查看完整学习路线
              </a>
            )}
            <button class="aae-button aae-button--secondary" type="button" data-aae-action="search">
              搜索全部文档
            </button>
          </div>
        </div>
        <dl class="aae-hero__stats" data-aae-hero="stats">
          <div><dt>阶段</dt><dd>08</dd></div>
          <div><dt>知识库</dt><dd>{String(courses.length).padStart(2, "0")}</dd></div>
          <div><dt>源文档</dt><dd>{sourceDocuments}</dd></div>
          <div><dt>公开正文</dt><dd>{fullDocuments}</dd></div>
        </dl>
      </section>

      <section class="aae-home-section" aria-labelledby="aae-stage-title">
        <div class="aae-section-heading">
          <div><p class="aae-eyebrow">LEARNING SYSTEM</p><h2 id="aae-stage-title">八阶段能力路径</h2></div>
          <p>按顺序推进，也可以从当前项目的缺口进入。每一阶段都以可完成的实践和掌握检查收束。</p>
        </div>
        <div class="aae-stage-grid">
          {stages.map((stage, index) => {
            const stageCourses = courses.filter((course) => course.stage === stage)
            const first = stageCourses[0]
            const copy = stageCopy[stage] ?? { label: stage, description: "建立这一阶段的核心工程能力。" }
            return (
              <a
                class="aae-stage-card"
                data-aae-reveal="stage"
                data-stage={String(index + 1)}
                href={resolveRelative(current, first.slug)}
              >
                <span class="aae-stage-card__number">{String(index + 1).padStart(2, "0")}</span>
                <span class="aae-stage-card__body">
                  <strong>{copy.label}</strong>
                  <span>{copy.description}</span>
                </span>
                <span class="aae-stage-card__count">{stageCourses.length} 个知识库</span>
              </a>
            )
          })}
        </div>
      </section>

      <section class="aae-home-section aae-course-map" aria-labelledby="aae-course-title">
        <div class="aae-section-heading">
          <div><p class="aae-eyebrow">53 KNOWLEDGE BASES</p><h2 id="aae-course-title">全部知识库</h2></div>
          <p>每个入口都指向该知识库的统一目录页；左侧课程导航会在阅读时展开当前知识库。</p>
        </div>
        <div class="aae-course-map__stages">
          {stages.map((stage, stageIndex) => {
            const copy = stageCopy[stage] ?? { label: stage, description: "" }
            return (
              <section class="aae-course-stage" data-aae-reveal="course-stage">
                <header>
                  <span>{String(stageIndex + 1).padStart(2, "0")}</span>
                  <h3>{copy.label}</h3>
                </header>
                <div class="aae-course-stage__links">
                  {courses.filter((course) => course.stage === stage).map((course) => (
                    <a href={resolveRelative(current, course.slug)}>
                      <span>{String(course.order).padStart(2, "0")}</span>
                      <strong>{course.name}</strong>
                    </a>
                  ))}
                </div>
              </section>
            )
          })}
        </div>
      </section>

      <aside class="aae-publishing-note" data-aae-reveal="note">
        <span class="aae-publishing-note__label">PUBLICATION BOUNDARY</span>
        <p>
          网站不包含登录或学习进度。{sourceStubs} 篇许可不明确的完整第三方复刻已替换为来源跳转页；
          {assets} 个允许公开的示例和图片以只读方式提供。
        </p>
      </aside>
    </main>
  )
}

Homepage.css = styles

export default (() => Homepage) satisfies QuartzComponentConstructor
