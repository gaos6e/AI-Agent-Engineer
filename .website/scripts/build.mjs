import { mkdir, writeFile } from "node:fs/promises"
import path from "node:path"
import {
  bootstrapRuntime,
  copyContentToRuntime,
  runPackageManager,
  RUNTIME_ROOT,
  runtimeEnvironment,
  WEBSITE_ROOT,
} from "./bootstrap-runtime.mjs"
import { prepareContent, CONTENT_ROOT } from "./prepare-content.mjs"
import { SITE_BASE_PATH, SITE_URL } from "./site-config.mjs"
import { validateSite } from "./validate-site.mjs"

await bootstrapRuntime()
await prepareContent()
const runtimeContent = await copyContentToRuntime(CONTENT_ROOT)

const publicRoot = path.join(WEBSITE_ROOT, "public")
await runPackageManager(
  "npx",
  [
    "quartz",
    "build",
    "-d",
    runtimeContent,
    "-o",
    publicRoot,
    "--concurrency",
    "2",
    "--baseDir",
    SITE_BASE_PATH,
  ],
  { cwd: RUNTIME_ROOT, env: runtimeEnvironment() },
)

await mkdir(publicRoot, { recursive: true })
await writeFile(path.join(publicRoot, ".nojekyll"), "", "utf8")
await writeFile(
  path.join(publicRoot, "robots.txt"),
  `User-agent: *\nAllow: /\nSitemap: ${SITE_URL}/sitemap.xml\n`,
  "utf8",
)

await validateSite()
