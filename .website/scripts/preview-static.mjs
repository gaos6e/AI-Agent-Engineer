import { createReadStream, existsSync, statSync } from "node:fs"
import { createServer } from "node:http"
import path from "node:path"
import { fileURLToPath, pathToFileURL } from "node:url"
import { SITE_BASE_PATH } from "./site-config.mjs"

const WEBSITE_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..")
const DEFAULT_PUBLIC_ROOT = path.join(WEBSITE_ROOT, "public")
const DEFAULT_HOST = "127.0.0.1"
const DEFAULT_PORT = 8080

const MIME_TYPES = new Map([
  [".css", "text/css; charset=utf-8"],
  [".csv", "text/csv; charset=utf-8"],
  [".gif", "image/gif"],
  [".html", "text/html; charset=utf-8"],
  [".ico", "image/x-icon"],
  [".jpeg", "image/jpeg"],
  [".jpg", "image/jpeg"],
  [".js", "text/javascript; charset=utf-8"],
  [".json", "application/json; charset=utf-8"],
  [".jsonl", "application/x-ndjson; charset=utf-8"],
  [".map", "application/json; charset=utf-8"],
  [".md", "text/markdown; charset=utf-8"],
  [".mjs", "text/javascript; charset=utf-8"],
  [".png", "image/png"],
  [".py", "text/plain; charset=utf-8"],
  [".sh", "text/plain; charset=utf-8"],
  [".svg", "image/svg+xml; charset=utf-8"],
  [".txt", "text/plain; charset=utf-8"],
  [".webp", "image/webp"],
  [".xml", "application/xml; charset=utf-8"],
])

function normalizeBasePath(basePath) {
  const value = `/${String(basePath || "").replace(/^\/+|\/+$/g, "")}`
  return value === "/" ? "" : value
}

function isFile(candidate) {
  return existsSync(candidate) && statSync(candidate).isFile()
}

export function resolvePreviewPath(publicRoot, basePath, pathname) {
  const root = path.resolve(publicRoot)
  const base = normalizeBasePath(basePath)
  let decoded

  try {
    decoded = decodeURIComponent(pathname)
  } catch {
    return null
  }

  if (decoded.includes("\0") || decoded.includes("\\")) return null
  if (base && decoded !== base && !decoded.startsWith(`${base}/`)) return null

  const relativeUrl = base ? decoded.slice(base.length) : decoded
  const segments = relativeUrl.split("/").filter(Boolean)
  if (segments.some((segment) => segment === "." || segment === "..")) return null

  const relativePath = segments.join(path.sep)
  const candidate = path.resolve(root, relativePath)
  const relationship = path.relative(root, candidate)
  if (relationship.startsWith("..") || path.isAbsolute(relationship)) return null

  const candidates = []
  if (!relativePath || decoded.endsWith("/")) {
    candidates.push(path.join(candidate, "index.html"))
  } else {
    candidates.push(candidate)
    if (!path.extname(candidate)) {
      candidates.push(`${candidate}.html`, path.join(candidate, "index.html"))
    } else if (existsSync(candidate) && statSync(candidate).isDirectory()) {
      candidates.push(path.join(candidate, "index.html"))
    }
  }

  return candidates.find(isFile) || null
}

function sendFile(response, filePath, method, statusCode = 200) {
  const extension = path.extname(filePath).toLowerCase()
  const contentType = MIME_TYPES.get(extension) || "application/octet-stream"
  const { size } = statSync(filePath)
  response.writeHead(statusCode, {
    "Cache-Control": "no-store",
    "Content-Length": size,
    "Content-Type": contentType,
    "X-Content-Type-Options": "nosniff",
  })
  if (method === "HEAD") {
    response.end()
    return
  }
  createReadStream(filePath).pipe(response)
}

export function createPreviewServer({
  publicRoot = DEFAULT_PUBLIC_ROOT,
  basePath = SITE_BASE_PATH,
} = {}) {
  const root = path.resolve(publicRoot)
  const base = normalizeBasePath(basePath)

  return createServer((request, response) => {
    const method = request.method || "GET"
    if (method !== "GET" && method !== "HEAD") {
      response.writeHead(405, { Allow: "GET, HEAD" })
      response.end("Method Not Allowed")
      return
    }

    let url
    try {
      url = new URL(request.url || "/", "http://localhost")
    } catch {
      response.writeHead(400)
      response.end("Bad Request")
      return
    }

    if (url.pathname === "/" && base) {
      response.writeHead(302, { Location: `${base}/` })
      response.end()
      return
    }

    const resolved = resolvePreviewPath(root, base, url.pathname)
    if (resolved) {
      sendFile(response, resolved, method)
      return
    }

    const notFound = path.join(root, "404.html")
    if (isFile(notFound)) {
      sendFile(response, notFound, method, 404)
      return
    }
    response.writeHead(404, { "Content-Type": "text/plain; charset=utf-8" })
    response.end("Not Found")
  })
}

function parsePort(value) {
  const port = Number.parseInt(value || String(DEFAULT_PORT), 10)
  if (!Number.isInteger(port) || port < 1 || port > 65535) {
    throw new Error(`Invalid PORT: ${value}`)
  }
  return port
}

const invokedDirectly = process.argv[1]
  && pathToFileURL(path.resolve(process.argv[1])).href === import.meta.url

if (invokedDirectly) {
  if (!existsSync(DEFAULT_PUBLIC_ROOT)) {
    throw new Error(`Build output not found: ${DEFAULT_PUBLIC_ROOT}. Run npm run build first.`)
  }
  const host = process.env.HOST || DEFAULT_HOST
  const port = parsePort(process.env.PORT)
  const server = createPreviewServer()
  server.listen(port, host, () => {
    console.log(`Previewing ${DEFAULT_PUBLIC_ROOT}`)
    console.log(`Local URL: http://${host}:${port}${normalizeBasePath(SITE_BASE_PATH)}/`)
  })
}
