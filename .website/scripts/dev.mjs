import {
  bootstrapRuntime,
  copyContentToRuntime,
  runPackageManager,
  RUNTIME_ROOT,
  runtimeEnvironment,
} from "./bootstrap-runtime.mjs"
import { DEFAULT_LOCALE, contentRootFor, getSiteLocale } from "../config/site-locales.mjs"
import { GENERATED_ROOT, prepareContent, WEBSITE_ROOT } from "./prepare-content.mjs"
import { localeSiteBasePath } from "./site-config.mjs"
import path from "node:path"

const localeFlag = process.argv.indexOf("--locale")
const locale = localeFlag >= 0 ? process.argv[localeFlag + 1] : DEFAULT_LOCALE
const definition = getSiteLocale(locale)

await prepareContent()
await bootstrapRuntime(locale)
const runtimeContent = await copyContentToRuntime(contentRootFor(GENERATED_ROOT, locale))

await runPackageManager(
  "npx",
  [
    "quartz",
    "build",
    "--serve",
    "-d",
    runtimeContent,
    "-o",
    path.join(WEBSITE_ROOT, "public", definition.routePrefix),
    "--concurrency",
    "2",
    "--baseDir",
    localeSiteBasePath(locale),
  ],
  { cwd: RUNTIME_ROOT, env: runtimeEnvironment() },
)
