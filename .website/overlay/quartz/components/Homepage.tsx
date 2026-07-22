import { QuartzComponent, QuartzComponentConstructor, QuartzComponentProps } from "./types"
import { resolveRelative } from "../util/path"
import styles from "./styles/homepage.scss"

type Course = {
  name: string
  domain: string
  catalogOrder: number
  tracks: Partial<Record<CourseTrackRole, CourseTrackKind>>
  slug: NonNullable<QuartzComponentProps["fileData"]["slug"]>
}

type CourseTrackRole = "agent_app" | "rag" | "agent_platform" | "multimodal_realtime"
type CourseTrackKind = "core" | "recommended" | "optional"

const domainCopy = [
  { id: "foundations", label: "工程与数学基础", description: "建立编程、数据表示、协作与定量判断的可靠底座。" },
  { id: "model-and-context", label: "模型与上下文", description: "选择模型，并控制提示、上下文预算与 API 边界。" },
  { id: "retrieval-and-data", label: "检索与数据", description: "完成清洗、解析、切分、检索、重排与引用链路。" },
  { id: "multimodal", label: "多模态", description: "处理文档视觉、语音、实时交互与生成媒体。" },
  { id: "agent-runtime", label: "Agent 运行时", description: "约束工具、状态、权限、恢复、协作与停止条件。" },
  { id: "framework-practice", label: "框架实践", description: "在理解底层合同后选择可替换的装配框架。" },
  { id: "evaluation-reliability", label: "评测与可靠性", description: "用数据集、grader、可视化和压力样本建立质量证据。" },
  { id: "safety-governance", label: "安全与治理", description: "把威胁、隐私、责任与合规放进生命周期。" },
  { id: "production-ops", label: "生产运维", description: "管理发布、回滚、监控和模型或应用制品。" },
  { id: "frontier-reference", label: "前沿与参考", description: "按观察状态学习快速变化的协议与研究方向。" },
] as const

const roleCopy: ReadonlyArray<{ id: CourseTrackRole; label: string; description: string }> = [
  { id: "agent_app", label: "Agent 应用开发", description: "交付有状态、可审批、可恢复的单 Agent。" },
  { id: "rag", label: "RAG 与知识库", description: "交付有 ACL、引用和分层评测的双管线 RAG。" },
  { id: "agent_platform", label: "Agent 平台与可靠性", description: "交付带发布门、trace、回滚与治理的运行平台。" },
  { id: "multimodal_realtime", label: "多模态与实时交互", description: "交付可打断、可调用工具的实时多模态原型。" },
]

function courseIndexName(file: QuartzComponentProps["fileData"]) {
  const relativePath = file.relativePath?.replaceAll("\\", "/")
  return relativePath?.match(/^([^/]+)\/00-目录\.md$/)?.[1]
}

function getCourses(allFiles: QuartzComponentProps["allFiles"]): Course[] {
  return allFiles.flatMap((file) => {
    const name = courseIndexName(file)
    const schema = Number(file.frontmatter?.ai_learning_schema)
    const domain = String(file.frontmatter?.ai_learning_domain ?? "").trim()
    const catalogOrder = Number(file.frontmatter?.ai_learning_catalog_order)
    if (!name || schema !== 2 || !domain || !Number.isSafeInteger(catalogOrder) || !file.slug) return []
    const tracks: Partial<Record<CourseTrackRole, CourseTrackKind>> = {}
    for (const role of roleCopy) {
      const order = Number(file.frontmatter?.[`ai_learning_track_${role.id}_order`])
      const kind = String(file.frontmatter?.[`ai_learning_track_${role.id}_kind`] ?? "") as CourseTrackKind
      if (Number.isSafeInteger(order) && order > 0 && ["core", "recommended", "optional"].includes(kind)) {
        tracks[role.id] = kind
      }
    }
    return [{ name, domain, catalogOrder, tracks, slug: file.slug }]
  })
    .sort((left, right) => left.catalogOrder - right.catalogOrder)
}

function formatCatalogOrder(order: number) {
  const display = order / 100
  return Number.isInteger(display) ? String(display).padStart(2, "0") : String(display)
}

function numericStat(value: unknown, fallback: number) {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : fallback
}

const Homepage: QuartzComponent = ({ fileData, allFiles }: QuartzComponentProps) => {
  if (fileData.slug !== "index") return null
  const current = fileData.slug

  const courses = getCourses(allFiles)
  const domains = domainCopy.filter((domain) => courses.some((course) => course.domain === domain.id))
  const roadmap = allFiles.find(
    (file) => file.relativePath?.replaceAll("\\", "/") === "All of AI.md",
  )
  const notices = allFiles.find(
    (file) => file.relativePath?.replaceAll("\\", "/") === "THIRD_PARTY_NOTICES.md",
  )
  const discoveredDocuments = allFiles.filter((file) => file.relativePath?.endsWith(".md")).length
  const sourceDocuments = numericStat(fileData.frontmatter?.site_source_document_count, discoveredDocuments)
  const fullDocuments = numericStat(fileData.frontmatter?.site_full_document_count, sourceDocuments)
  const sourceStubs = numericStat(fileData.frontmatter?.site_stub_count, 0)
  const assets = numericStat(fileData.frontmatter?.site_asset_count, 0)

  return (
    <main class="aae-home">
      <section class="aae-hero" aria-labelledby="aae-home-title">
        <div class="aae-hero__content">
          <p class="aae-eyebrow" data-aae-hero="eyebrow">OPEN ENGINEERING ROADMAP · 2026</p>
          <h1 id="aae-home-title" data-aae-hero="title">
            从零构建、评测与部署 <span>AI Agent</span>
          </h1>
          <p class="aae-hero__lead" data-aae-hero="lead">
            一套面向真实工程交付的中文学习知识库。按角色路径和能力缺口选择 {courses.length} 个学习重点，
            覆盖从 Python、API 与数据底座，到 RAG、Agent、评测、治理和复杂协作的 {domains.length} 个知识域。
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

        <div class="aae-hero__board" data-aae-hero="board" aria-hidden="true">
          <div class="aae-sticky aae-sticky--lilac"><span>01 · BUILD</span><strong>工具契约</strong></div>
          <div class="aae-sticky aae-sticky--lime"><span>02 · GROUND</span><strong>可靠检索</strong></div>
          <div class="aae-sticky aae-sticky--coral"><span>03 · EVALUATE</span><strong>分层评测</strong></div>
          <div class="aae-sticky aae-sticky--navy"><span>04 · SHIP</span><strong>生产治理</strong></div>
        </div>
      </section>

      <aside class="aae-marquee" aria-label="知识库规模">
        <dl>
          <div><dt>{String(domains.length).padStart(2, "0")}</dt><dd>DOMAINS</dd></div>
          <div><dt>{String(courses.length).padStart(2, "0")}</dt><dd>KNOWLEDGE BASES</dd></div>
          <div><dt>{sourceDocuments}</dt><dd>SOURCE DOCUMENTS</dd></div>
          <div><dt>{fullDocuments}</dt><dd>PUBLIC ARTICLES</dd></div>
        </dl>
        <p aria-hidden="true">BUILD · OBSERVE · EVALUATE · SHIP · ITERATE</p>
      </aside>

      <section class="aae-home-section aae-role-system" aria-labelledby="aae-role-title">
        <div class="aae-section-heading">
          <div>
            <p class="aae-eyebrow">ROLE TRACKS</p>
            <h2 id="aae-role-title">先选交付目标，再补能力</h2>
          </div>
          <p>四条路径直接读取课程 v2 元数据；核心、推荐与可选课程各自保留边界，不把建议顺序伪装成硬依赖。</p>
        </div>
        <div class="aae-role-grid">
          {roleCopy.map((role, index) => {
            const roleCourses = courses.filter((course) => course.tracks[role.id])
            const core = roleCourses.filter((course) => course.tracks[role.id] === "core").length
            const recommended = roleCourses.filter((course) => course.tracks[role.id] === "recommended").length
            const optional = roleCourses.filter((course) => course.tracks[role.id] === "optional").length
            return roadmap?.slug ? (
              <a href={resolveRelative(current, roadmap.slug)} data-aae-reveal="role">
                <span>{String(index + 1).padStart(2, "0")}</span>
                <strong>{role.label}</strong>
                <p>{role.description}</p>
                <small>{core} 核心 · {recommended} 推荐 · {optional} 可选</small>
                <i aria-hidden="true">↗</i>
              </a>
            ) : null
          })}
        </div>
      </section>

      <section class="aae-home-section aae-stage-system" aria-labelledby="aae-stage-title">
        <div class="aae-section-heading">
          <div>
            <p class="aae-eyebrow">LEARNING SYSTEM</p>
            <h2 id="aae-stage-title">{domains.length} 个知识域</h2>
          </div>
          <p>知识域负责稳定归类，角色路径负责学习顺序，硬前置只保留真正无法绕过的完整课程依赖。</p>
        </div>
        <div class="aae-stage-grid">
          {domains.map((domain, index) => {
            const domainCourses = courses.filter((course) => course.domain === domain.id)
            const first = domainCourses[0]
            return (
              <a
                class="aae-stage-card"
                data-aae-reveal="stage"
                data-stage={String(index + 1)}
                href={resolveRelative(current, first.slug)}
              >
                <span class="aae-stage-card__number">{String(index + 1).padStart(2, "0")}</span>
                <span class="aae-stage-card__body">
                  <strong>{domain.label}</strong>
                  <span>{domain.description}</span>
                </span>
                <span class="aae-stage-card__count">{domainCourses.length} 个学习重点</span>
                <span class="aae-stage-card__arrow" aria-hidden="true">↗</span>
              </a>
            )
          })}
        </div>
      </section>

      <section class="aae-home-section aae-course-map" aria-labelledby="aae-course-title">
        <div class="aae-section-heading">
          <div>
            <p class="aae-eyebrow">{courses.length} KNOWLEDGE BASES</p>
            <h2 id="aae-course-title">全部学习重点</h2>
          </div>
          <p>每个入口都进入统一课程目录；阅读页左栏会保留阶段、课程与真实子目录层级。</p>
        </div>
        <div class="aae-course-map__stages">
          {domains.map((domain, domainIndex) => {
            return (
              <section class="aae-course-stage" data-aae-reveal="course-stage">
                <header>
                  <span>{String(domainIndex + 1).padStart(2, "0")}</span>
                  <h3>{domain.label}</h3>
                </header>
                <div class="aae-course-stage__links">
                  {courses.filter((course) => course.domain === domain.id).map((course) => (
                    <a href={resolveRelative(current, course.slug)}>
                      <span>{formatCatalogOrder(course.catalogOrder)}</span>
                      <strong>{course.name}</strong>
                      <i aria-hidden="true">↗</i>
                    </a>
                  ))}
                </div>
              </section>
            )
          })}
        </div>
      </section>

      <aside class="aae-publishing-note" data-aae-reveal="note">
        <div>
          <span class="aae-publishing-note__label">PUBLICATION BOUNDARY</span>
          <h2>公开，保持边界清晰。</h2>
        </div>
        <div>
          <p>
            网站不包含登录或学习进度。{sourceStubs} 篇许可不明确的第三方完整复刻已替换为来源跳转页；
            {assets} 个允许公开的示例和图片以只读方式提供。
          </p>
          {notices?.slug && (
            <a class="aae-button aae-button--inverse" href={resolveRelative(current, notices.slug)}>
              查看第三方与许可说明
            </a>
          )}
        </div>
      </aside>
    </main>
  )
}

Homepage.css = styles

export default (() => Homepage) satisfies QuartzComponentConstructor
