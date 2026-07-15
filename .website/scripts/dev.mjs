import {
  bootstrapRuntime,
  copyContentToRuntime,
  runPackageManager,
  RUNTIME_ROOT,
  runtimeEnvironment,
} from "./bootstrap-runtime.mjs"
import { prepareContent, CONTENT_ROOT, WEBSITE_ROOT } from "./prepare-content.mjs"
import { SITE_BASE_PATH } from "./site-config.mjs"
import path from "node:path"

await bootstrapRuntime()
await prepareContent()
const runtimeContent = await copyContentToRuntime(CONTENT_ROOT)

await runPackageManager(
  "npx",
  [
    "quartz",
    "build",
    "--serve",
    "-d",
    runtimeContent,
    "-o",
    path.join(WEBSITE_ROOT, "public"),
    "--concurrency",
    "2",
    "--baseDir",
    SITE_BASE_PATH,
  ],
  { cwd: RUNTIME_ROOT, env: runtimeEnvironment() },
)
