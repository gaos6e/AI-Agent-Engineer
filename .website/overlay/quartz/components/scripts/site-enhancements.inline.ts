import { gsap } from "gsap"
import { ScrollTrigger } from "gsap/ScrollTrigger"

gsap.registerPlugin(ScrollTrigger)

let motionMedia: ReturnType<typeof gsap.matchMedia> | undefined
let refreshFrame: number | undefined
let routeScrollFrame: number | undefined
let previousPath = window.location.pathname

function teardownMotion() {
  if (refreshFrame !== undefined) cancelAnimationFrame(refreshFrame)
  if (routeScrollFrame !== undefined) cancelAnimationFrame(routeScrollFrame)
  refreshFrame = undefined
  routeScrollFrame = undefined
  motionMedia?.revert()
  motionMedia = undefined
}

function resetScrollOnRouteChange() {
  const currentPath = window.location.pathname
  const routeChanged = currentPath !== previousPath
  previousPath = currentPath
  if (!routeChanged || window.location.hash) return

  routeScrollFrame = requestAnimationFrame(() => {
    routeScrollFrame = undefined
    const root = document.documentElement
    const previousBehavior = root.style.scrollBehavior
    root.style.scrollBehavior = "auto"
    window.scrollTo(0, 0)
    if (previousBehavior) root.style.scrollBehavior = previousBehavior
    else root.style.removeProperty("scroll-behavior")
  })
}

function initMotion() {
  teardownMotion()
  motionMedia = gsap.matchMedia()
  motionMedia.add("(prefers-reduced-motion: no-preference)", () => {
    const siteHeader = document.querySelector("[data-aae-animate='site-header']")
    if (siteHeader) {
      gsap.from(siteHeader, {
        y: -8,
        autoAlpha: 0,
        duration: 0.3,
        delay: 0.08,
        ease: "power3.out",
      })
    }

    const hero = document.querySelector(".aae-home")
    if (hero) {
      const timeline = gsap.timeline({ defaults: { overwrite: "auto" } })
      timeline
        .from("[data-aae-hero='eyebrow']", {
          y: 12,
          autoAlpha: 0,
          duration: 0.34,
          ease: "power3.out",
        }, 0.12)
        .from("[data-aae-hero='title']", {
          y: 24,
          autoAlpha: 0,
          duration: 0.58,
          ease: "power4.out",
        }, 0.2)
        .from("[data-aae-hero='lead']", {
          y: 12,
          autoAlpha: 0,
          duration: 0.42,
          ease: "power3.out",
        }, 0.38)
        .from("[data-aae-hero='actions']", {
          y: 10,
          autoAlpha: 0,
          duration: 0.38,
          ease: "power3.out",
        }, 0.48)
        .from("[data-aae-hero='board'] > div", {
          y: 18,
          scale: 0.97,
          autoAlpha: 0,
          duration: 0.44,
          stagger: 0.06,
          ease: "power3.out",
        }, 0.34)

      ScrollTrigger.batch("[data-aae-reveal]", {
        start: "top 88%",
        once: true,
        interval: 0.08,
        batchMax: 6,
        onEnter: (elements) => {
          gsap.from(elements, {
            y: 22,
            autoAlpha: 0,
            duration: 0.48,
            stagger: 0.07,
            ease: "power3.out",
            overwrite: "auto",
          })
        },
      })
    } else {
      const lead = Array.from(document.querySelectorAll(".center article > *")).slice(0, 7)
      if (lead.length > 0) {
        gsap.from(lead, {
          y: 10,
          autoAlpha: 0,
          duration: 0.36,
          stagger: 0.035,
          delay: 0.16,
          ease: "power2.out",
        })
      }
    }
  }, document.body)

  refreshFrame = requestAnimationFrame(() => {
    refreshFrame = undefined
    ScrollTrigger.refresh()
  })
}

const previewable = /\.(?:py|json|csv|ipynb|jsonl|sh|txt)(?:$|[?#])/i

function ensureSearchPortal() {
  const existing = document.querySelector<HTMLElement>(".aae-search-portal")
  const source = document.querySelector<HTMLElement>(".page .search") ?? existing
  if (!source) return undefined
  if (existing && existing !== source) existing.remove()
  source.classList.add("aae-search-portal")
  if (source.parentElement !== document.body) document.body.append(source)
  return source.querySelector<HTMLElement>(".search-button, [data-search-button]") ?? undefined
}

function notebookToText(raw: string) {
  try {
    const notebook = JSON.parse(raw) as { cells?: Array<{ cell_type?: string; source?: string[] | string }> }
    if (!Array.isArray(notebook.cells)) return raw
    return notebook.cells
      .map((cell, index) => {
        const source = Array.isArray(cell.source) ? cell.source.join("") : String(cell.source ?? "")
        return `# Cell ${index + 1} · ${cell.cell_type ?? "unknown"}\n\n${source}`
      })
      .join("\n\n")
  } catch {
    return raw
  }
}

async function openAssetPreview(url: URL, label: string) {
  document.querySelector(".aae-asset-dialog")?.remove()
  const dialog = document.createElement("dialog")
  dialog.className = "aae-asset-dialog"
  dialog.setAttribute("aria-label", `${label} 资源预览`)
  dialog.innerHTML = `
    <div class="aae-asset-dialog__head">
      <div><span>READ-ONLY ASSET</span><strong></strong></div>
      <button type="button" aria-label="关闭资源预览">关闭</button>
    </div>
    <div class="aae-asset-dialog__body"><p>正在加载预览…</p></div>
    <div class="aae-asset-dialog__foot"><a>下载原文件</a></div>
  `
  const title = dialog.querySelector("strong")!
  const body = dialog.querySelector(".aae-asset-dialog__body")!
  const close = dialog.querySelector("button")!
  const download = dialog.querySelector("a")!
  title.textContent = label
  download.setAttribute("href", url.href)
  download.setAttribute("download", "")
  download.dataset.routerIgnore = ""
  close.addEventListener("click", () => dialog.close())
  dialog.addEventListener("close", () => dialog.remove())
  document.body.append(dialog)
  dialog.showModal()

  try {
    const response = await fetch(url)
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    const declaredLength = Number(response.headers.get("content-length") ?? 0)
    if (declaredLength > 1_500_000) {
      body.textContent = "该资源超过在线预览上限，请使用下方按钮下载后查看。"
      return
    }
    let text = await response.text()
    if (url.pathname.toLowerCase().endsWith(".ipynb")) text = notebookToText(text)
    const truncated = text.length > 400_000
    if (truncated) text = `${text.slice(0, 400_000)}\n\n…预览已截断，请下载原文件查看完整内容。`
    const pre = document.createElement("pre")
    const code = document.createElement("code")
    code.textContent = text
    pre.append(code)
    body.replaceChildren(pre)
  } catch (error) {
    body.textContent = `无法加载在线预览：${error instanceof Error ? error.message : String(error)}`
  }
}

function initInteractions() {
  ensureSearchPortal()
  const courseDrawer = document.querySelector<HTMLElement>("#aae-course-nav")
  const coursePanel = courseDrawer?.querySelector<HTMLElement>("[data-aae-course-panel]")
  const courseTrigger = document.querySelector<HTMLButtonElement>("[data-aae-action='courses']")
  const courseMedia = window.matchMedia("(max-width: 960px)")
  let returnFocusTarget: HTMLElement | undefined

  const courseDrawerOpen = () => courseDrawer?.classList.contains("is-mobile-open") ?? false
  const setCourseDrawer = (open: boolean, restoreFocus = true) => {
    if (!courseDrawer || !courseMedia.matches) return
    if (open) {
      returnFocusTarget = courseTrigger ?? undefined
      courseDrawer.inert = false
      courseDrawer.removeAttribute("aria-hidden")
      courseDrawer.classList.add("is-mobile-open")
      courseTrigger?.setAttribute("aria-expanded", "true")
      document.body.classList.add("aae-course-drawer-open")
      requestAnimationFrame(() => {
        courseDrawer.querySelector<HTMLButtonElement>("[data-aae-action='close-courses']")?.focus()
      })
      return
    }

    courseDrawer.classList.remove("is-mobile-open")
    courseTrigger?.setAttribute("aria-expanded", "false")
    courseDrawer.setAttribute("aria-hidden", "true")
    courseDrawer.inert = true
    document.body.classList.remove("aae-course-drawer-open")
    if (restoreFocus) returnFocusTarget?.focus()
  }

  const syncCourseDrawerMode = () => {
    if (!courseDrawer) return
    if (courseMedia.matches) {
      if (!courseDrawerOpen()) {
        courseDrawer.setAttribute("aria-hidden", "true")
        courseDrawer.inert = true
      }
      return
    }
    courseDrawer.classList.remove("is-mobile-open")
    courseDrawer.removeAttribute("aria-hidden")
    courseDrawer.inert = false
    courseTrigger?.setAttribute("aria-expanded", "false")
    document.body.classList.remove("aae-course-drawer-open")
  }

  syncCourseDrawerMode()
  courseMedia.addEventListener("change", syncCourseDrawerMode)
  document.querySelectorAll<HTMLAnchorElement>("a[href]").forEach((anchor) => {
    if (previewable.test(anchor.href)) anchor.dataset.routerIgnore = ""
  })
  const onClick = (event: MouseEvent) => {
    const target = event.target as Element | null
    const action = target?.closest<HTMLElement>("[data-aae-action]")?.dataset.aaeAction
    if (action === "courses") {
      event.preventDefault()
      setCourseDrawer(true)
      return
    }
    if (action === "close-courses") {
      event.preventDefault()
      setCourseDrawer(false)
      return
    }
    if (action === "search") {
      event.preventDefault()
      const search = ensureSearchPortal()
      search?.click()
      return
    }
    if (action === "theme") {
      event.preventDefault()
      const theme = document.querySelector<HTMLElement>(".darkmode, .darkmode button")
      theme?.click()
      return
    }

    const anchor = target?.closest<HTMLAnchorElement>("a[href]")
    if (anchor && courseDrawer?.contains(anchor) && courseMedia.matches) {
      setCourseDrawer(false, false)
    }
    if (!anchor || anchor.hasAttribute("download") || !previewable.test(anchor.href) ||
        event.button !== 0 || event.metaKey || event.ctrlKey) return
    const url = new URL(anchor.href, window.location.href)
    if (url.origin !== window.location.origin) return
    anchor.dataset.routerIgnore = ""
    event.preventDefault()
    event.stopPropagation()
    event.stopImmediatePropagation()
    void openAssetPreview(url, anchor.textContent?.trim() || url.pathname.split("/").at(-1) || "资源")
  }

  const onKeydown = (event: KeyboardEvent) => {
    if (event.key === "Escape" && courseDrawerOpen()) {
      event.preventDefault()
      setCourseDrawer(false)
      return
    }

    if (event.key === "Tab" && courseDrawerOpen() && coursePanel) {
      const focusable = Array.from(
        coursePanel.querySelectorAll<HTMLElement>(
          "a[href], button:not([disabled]), summary, [tabindex]:not([tabindex='-1'])",
        ),
      ).filter((element) => element.offsetParent !== null && !element.inert)
      if (focusable.length > 0) {
        const first = focusable[0]
        const last = focusable.at(-1)!
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault()
          last.focus()
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault()
          first.focus()
        }
      }
      return
    }

    if (!(event.ctrlKey || event.metaKey) || event.key.toLowerCase() !== "k") return
    const active = document.activeElement
    if (active instanceof HTMLInputElement || active instanceof HTMLTextAreaElement || active instanceof HTMLSelectElement) return
    event.preventDefault()
    ensureSearchPortal()?.click()
  }

  document.addEventListener("click", onClick, true)
  document.addEventListener("keydown", onKeydown)
  window.addCleanup(() => {
    document.removeEventListener("click", onClick, true)
    document.removeEventListener("keydown", onKeydown)
    courseMedia.removeEventListener("change", syncCourseDrawerMode)
    document.body.classList.remove("aae-course-drawer-open")
    document.querySelector<HTMLDialogElement>(".aae-asset-dialog")?.close()
  })
}

document.addEventListener("prenav", teardownMotion)
document.addEventListener("nav", () => {
  initMotion()
  resetScrollOnRouteChange()
  initInteractions()
})
