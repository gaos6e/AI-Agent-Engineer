import { gsap } from "gsap"
import { ScrollTrigger } from "gsap/ScrollTrigger"

gsap.registerPlugin(ScrollTrigger)

let motionContext: gsap.Context | undefined
let refreshFrame: number | undefined
let routeScrollFrame: number | undefined
let previousPath = window.location.pathname

function teardownMotion() {
  if (refreshFrame !== undefined) cancelAnimationFrame(refreshFrame)
  if (routeScrollFrame !== undefined) cancelAnimationFrame(routeScrollFrame)
  refreshFrame = undefined
  routeScrollFrame = undefined
  motionContext?.revert()
  motionContext = undefined
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
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return

  motionContext = gsap.context(() => {
    const siteHeader = document.querySelector("[data-aae-animate='site-header']")
    if (siteHeader) {
      gsap.from(siteHeader, {
        x: -12,
        autoAlpha: 0,
        duration: 0.34,
        delay: 0.12,
        ease: "power3.out",
      })
    }

    const hero = document.querySelector(".aae-home")
    if (hero) {
      const timeline = gsap.timeline({ defaults: { overwrite: "auto" } })
      timeline
        .from("[data-aae-hero='eyebrow']", {
          x: -22,
          autoAlpha: 0,
          duration: 0.36,
          ease: "expo.out",
        }, 0.18)
        .from("[data-aae-hero='title']", {
          y: 30,
          autoAlpha: 0,
          duration: 0.68,
          ease: "power4.out",
        }, 0.28)
        .from("[data-aae-hero='lead']", {
          autoAlpha: 0,
          duration: 0.5,
          ease: "sine.out",
        }, 0.5)
        .from("[data-aae-hero='actions']", {
          x: 16,
          autoAlpha: 0,
          duration: 0.42,
          ease: "back.out(1.25)",
        }, 0.62)
        .from("[data-aae-hero='stats'] > div", {
          y: 16,
          autoAlpha: 0,
          duration: 0.4,
          stagger: 0.07,
          ease: "circ.out",
        }, 0.56)

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
  document.querySelectorAll<HTMLAnchorElement>("a[href]").forEach((anchor) => {
    if (previewable.test(anchor.href)) anchor.dataset.routerIgnore = ""
  })
  const onClick = (event: MouseEvent) => {
    const target = event.target as Element | null
    const action = target?.closest<HTMLElement>("[data-aae-action]")?.dataset.aaeAction
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
    document.querySelector<HTMLDialogElement>(".aae-asset-dialog")?.close()
  })
}

document.addEventListener("prenav", teardownMotion)
document.addEventListener("nav", () => {
  initMotion()
  resetScrollOnRouteChange()
  initInteractions()
})
