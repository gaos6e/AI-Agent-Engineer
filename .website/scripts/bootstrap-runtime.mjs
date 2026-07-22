import { createHash } from "node:crypto"
import { cp, mkdir, readFile, readdir, rm, stat, writeFile } from "node:fs/promises"
import path from "node:path"
import { spawn } from "node:child_process"
import { fileURLToPath, pathToFileURL } from "node:url"

export const WEBSITE_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..")
export const RUNTIME_ROOT = path.join(WEBSITE_ROOT, ".runtime")
export const CACHE_ROOT = path.join(WEBSITE_ROOT, ".cache")
const REQUIRED_PLUGINS = [
  "alias-redirects",
  "article-title",
  "backlinks",
  "breadcrumbs",
  "content-index",
  "content-meta",
  "content-page",
  "crawl-links",
  "created-modified-date",
  "darkmode",
  "description",
  "favicon",
  "folder-page",
  "footer",
  "github-flavored-markdown",
  "hard-line-breaks",
  "latex",
  "note-properties",
  "obsidian-flavored-markdown",
  "og-image",
  "page-title",
  "reader-mode",
  "remove-draft",
  "search",
  "spacer",
  "syntax-highlighting",
  "table-of-contents",
  "tag-page",
]

export function runtimeEnvironment() {
  const npmCache = path.join(CACHE_ROOT, "npm")
  const temporary = path.join(CACHE_ROOT, "tmp")
  return {
    ...process.env,
    // Quartz v5.0.0 pins two GitHub dependencies with ssh:// URLs. Keep the
    // commits locked while allowing clean CI runners without an SSH identity
    // to fetch the public repositories over HTTPS. These settings affect only
    // child processes spawned by this build.
    GIT_CONFIG_COUNT: "2",
    GIT_CONFIG_KEY_0: "url.https://github.com/.insteadOf",
    GIT_CONFIG_VALUE_0: "ssh://git@github.com/",
    GIT_CONFIG_KEY_1: "url.https://github.com/.insteadOf",
    GIT_CONFIG_VALUE_1: "git@github.com:",
    NPM_CONFIG_CACHE: npmCache,
    npm_config_cache: npmCache,
    TEMP: temporary,
    TMP: temporary,
  }
}

export async function copyContentToRuntime(sourceDirectory) {
  const destination = path.join(RUNTIME_ROOT, "content")
  assertRuntimePath(destination)
  await rm(destination, { recursive: true, force: true })
  await cp(sourceDirectory, destination, { recursive: true, force: true, preserveTimestamps: true })
  return destination
}

export function run(command, args, options = {}) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, { stdio: "inherit", shell: false, ...options })
    child.once("error", reject)
    child.once("exit", (code) => {
      if (code === 0) resolve()
      else reject(new Error(`${command} ${args.join(" ")} exited with code ${code}`))
    })
  })
}

export function runPackageManager(tool, args, options = {}) {
  const npmCli = process.env.npm_execpath
  if (npmCli && npmCli.endsWith(".js")) {
    const cli = tool === "npm" ? npmCli : path.join(path.dirname(npmCli), "npx-cli.js")
    return run(process.execPath, [cli, ...args], options)
  }
  if (process.platform === "win32") {
    return run(process.env.ComSpec || "cmd.exe", ["/d", "/s", "/c", `${tool}.cmd`, ...args], options)
  }
  return run(tool, args, options)
}

async function exists(target) {
  try {
    await stat(target)
    return true
  } catch {
    return false
  }
}

function assertRuntimePath(target) {
  const relative = path.relative(WEBSITE_ROOT, target)
  if (!relative || relative.startsWith("..") || path.isAbsolute(relative) || relative.split(path.sep)[0] !== ".runtime") {
    throw new Error(`Unsafe runtime path: ${target}`)
  }
}

async function output(command, args, cwd) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, { cwd, shell: false, stdio: ["ignore", "pipe", "pipe"] })
    let stdout = ""
    let stderr = ""
    child.stdout.on("data", (chunk) => { stdout += chunk })
    child.stderr.on("data", (chunk) => { stderr += chunk })
    child.once("error", reject)
    child.once("exit", (code) => code === 0 ? resolve(stdout.trim()) : reject(new Error(stderr.trim())))
  })
}

async function fileHash(target) {
  const bytes = await readFile(target)
  return createHash("sha256").update(bytes).digest("hex")
}

async function preparePluginLock(commit) {
  const lockPath = path.join(RUNTIME_ROOT, "quartz.lock.json")
  const lock = JSON.parse(await output("git", ["show", `${commit}:quartz.lock.json`], RUNTIME_ROOT))
  const missing = REQUIRED_PLUGINS.filter((name) => !lock.plugins?.[name])
  if (missing.length > 0) throw new Error(`Quartz lockfile is missing plugins: ${missing.join(", ")}`)
  lock.plugins = Object.fromEntries(REQUIRED_PLUGINS.map((name) => [name, lock.plugins[name]]))
  await writeFile(lockPath, `${JSON.stringify(lock, null, 2)}\n`, "utf8")
  return lock
}

async function pluginMatchesLock(pluginsDirectory, name, lock) {
  const pluginDirectory = path.join(pluginsDirectory, name)
  if (!await exists(path.join(pluginDirectory, "package.json")) ||
      !await exists(path.join(pluginDirectory, "dist")) ||
      !await exists(path.join(pluginDirectory, ".git"))) return false
  try {
    const commit = await output("git", ["rev-parse", "HEAD"], pluginDirectory)
    return commit === lock.plugins[name].commit
  } catch {
    return false
  }
}

async function pluginTreeMatchesLock(pluginsDirectory, lock) {
  for (const name of REQUIRED_PLUGINS) {
    if (!await pluginMatchesLock(pluginsDirectory, name, lock)) return false
  }
  return true
}

async function patchWindowsPluginRestore() {
  if (process.platform !== "win32") return
  const target = path.join(RUNTIME_ROOT, "quartz", "cli", "plugin-git-handlers.js")
  let source = await readFile(target, "utf8")
  const originalSource = source
  const oldImport = 'import { execSync } from "child_process"'
  const oldClone = '      execSync(`git clone${branchArg} ${entry.resolved} ${pluginDir}`, { stdio: "ignore" })\n      execSync(`git checkout ${entry.commit}`, { cwd: pluginDir, stdio: "ignore" })'
  if (source.includes(oldClone)) {
    source = source.replace(oldImport, 'import { execFileSync, execSync } from "child_process"')
    source = source.replace(
      oldClone,
      '      const cloneArgs = ["clone", ...(entry.ref ? ["--branch", entry.ref] : []), entry.resolved, pluginDir]\n      execFileSync("git", cloneArgs, { stdio: "ignore" })\n      execFileSync("git", ["checkout", entry.commit], { cwd: pluginDir, stdio: "ignore" })',
    )
  }
  if (source !== originalSource) await writeFile(target, source, "utf8")
  if (!source.includes('execFileSync("git", cloneArgs')) {
    throw new Error("Unable to apply Quartz v5.0.0 Windows path compatibility patch")
  }
}

async function patchTagPageRootLinks(pluginLock) {
  const pluginDirectory = path.join(RUNTIME_ROOT, ".quartz", "plugins", "tag-page")
  const target = path.join(pluginDirectory, "src", "components", "TagContent.tsx")
  const marker = path.join(RUNTIME_ROOT, ".aae-tag-page-root-links-ready")
  const patchVersion = `${pluginLock.plugins["tag-page"].commit}:root-links-v4`
  let source = await readFile(target, "utf8")
  const originalSource = source
  const patchedList = 'fileData: { ...props.fileData, slug: "tags/index" as FullSlug },'
  const patchedHref = 'resolveRelative("tags/index" as FullSlug, tagListingPage)'
  const patchedDescription = "const tagDesc: ComponentChildren | undefined = undefined;"
  source = source
    .replace('fileData: { ...props.fileData, slug: "tags" as FullSlug },', patchedList)
    .replace('resolveRelative("tags" as FullSlug, tagListingPage)', patchedHref)
    .replace(
      /\s+const contentPage = \(allFiles as PageFileData\[\]\)\.find\([\s\S]*?const tagDesc =\s+!root \|\| root\.children\.length === 0 \? contentPage\?\.description : htmlToJsx\(root\);/,
      `\n\n              // Virtual tag pages already contain TagContent; nesting them breaks root-relative links.\n              ${patchedDescription}`,
    )
  const alreadyPatched = source.includes(patchedList) &&
    source.includes(patchedHref) &&
    source.includes(patchedDescription)
  const markerMatches = await exists(marker) && (await readFile(marker, "utf8")).trim() === patchVersion
  const compiledTargets = [
    path.join(pluginDirectory, "dist", "index.js"),
    path.join(pluginDirectory, "dist", "components", "index.js"),
  ]
  const compiledReady = (await Promise.all(compiledTargets.map((compiled) => exists(compiled)))).every(Boolean)
  if (alreadyPatched && source === originalSource && markerMatches && compiledReady) return

  if (!alreadyPatched) {
    source = source.replace(
      /const listProps = \{\r?\n\s+\.\.\.props,\r?\n\s+allFiles: pages,\r?\n\s+\};/,
      `const listProps = {\n                ...props,\n                ${patchedList}\n                allFiles: pages,\n              };`,
    )
    source = source.replace(
      "resolveRelative(slug as FullSlug, tagListingPage)",
      patchedHref,
    )
    if (!source.includes(patchedList) ||
        !source.includes(patchedHref) ||
        !source.includes(patchedDescription)) {
      throw new Error("Unable to apply Quartz v5.0.0 tag index link compatibility patch")
    }
  }
  if (source !== originalSource) await writeFile(target, source, "utf8")

  for (const compiledTarget of compiledTargets) {
    let compiled = await readFile(compiledTarget, "utf8")
    compiled = compiled
      .replace('fileData: { ...props.fileData, slug: "tags" }', 'fileData: { ...props.fileData, slug: "tags/index" }')
      .replace('resolveRelative("tags", tagListingPage)', 'resolveRelative("tags/index", tagListingPage)')
    if (!compiled.includes('fileData: { ...props.fileData, slug: "tags/index" }')) {
      compiled = compiled.replace(
        /const listProps = \{\r?\n(\s+)\.\.\.props,\r?\n\1allFiles: pages\r?\n(\s+)\};/,
        (_full, propertyIndent, closingIndent) =>
          `const listProps = {\n${propertyIndent}...props,\n${propertyIndent}fileData: { ...props.fileData, slug: "tags/index" },\n${propertyIndent}allFiles: pages\n${closingIndent}};`,
      )
    }
    compiled = compiled.replace(
      "resolveRelative(slug, tagListingPage)",
      'resolveRelative("tags/index", tagListingPage)',
    )
    compiled = compiled.replace(
      /\s+const contentPage = allFiles\.find\([\s\S]*?const tagDesc = !root \|\| root\.children\.length === 0 \? contentPage\?\.description : htmlToJsx\(root\);/,
      "\n          const tagDesc = void 0;",
    )
    if (!compiled.includes('fileData: { ...props.fileData, slug: "tags/index" }') ||
        !compiled.includes('resolveRelative("tags/index", tagListingPage)') ||
        !compiled.includes("const tagDesc = void 0;")) {
      throw new Error("Unable to patch compiled Quartz tag index links")
    }
    await writeFile(compiledTarget, compiled, "utf8")
  }
  await writeFile(marker, `${patchVersion}\n`, "utf8")
}

async function patchSearchBasePath(pluginLock) {
  const pluginDirectory = path.join(RUNTIME_ROOT, ".quartz", "plugins", "search")
  const target = path.join(pluginDirectory, "src", "components", "scripts", "search.inline.ts")
  const marker = path.join(RUNTIME_ROOT, ".aae-search-base-path-ready")
  const patchVersion = `${pluginLock.plugins.search.commit}:base-path-v2`
  let source = await readFile(target, "utf8")
  const originalSource = source
  const helper = `function siteUrl(slug: string): string {
  const postscript = document.querySelector<HTMLScriptElement>('script[src$="/postscript.js"]')?.src;
  const base = new URL(".", postscript ?? window.location.origin + "/");
  return new URL(slug.replace(/^\\/+/, ""), base).toString();
}`
  if (!source.includes("function siteUrl(slug: string)")) {
    source = source.replace("const parser = new DOMParser();", `const parser = new DOMParser();\n\n${helper}`)
  }
  source = source
    .replace('const targetUrl = new URL("/" + slug, window.location.origin).toString();', "const targetUrl = siteUrl(slug);")
    .replace('itemTile.href = "/" + item.slug;', "itemTile.href = siteUrl(item.slug);")
    .replace(
      /  const response = await fetch\("\/static\/contentIndex\.json"\);\r?\n  const data = await response\.json\(\);/,
      "  const data = await fetchData;",
    )
    .replace(/^\s*console\.log\("\[Search\] hideSearch called, stack:", new Error\(\)\.stack\);\r?\n/m, "")
    .replace(/^\s*console\.log\("\[Search\] showSearch called, type:", type\);\r?\n/m, "")
    .replace(/^\s*console\.log\("\[Search\] container\.classList after add:", container\.classList\.toString\(\)\);\r?\n/m, "")
    .replace(
      /\s+console\.log\(\r?\n\s+"\[Search\] focus called, container active:",\r?\n\s+container\.classList\.contains\("active"\),\r?\n\s+\);/,
      "",
    )
    .replace(
      /\s+console\.log\(\r?\n\s+"\[Search\] Button click event, target:",\r?\n\s+e\.target,\r?\n\s+"currentTarget:",\r?\n\s+e\.currentTarget,\r?\n\s+\);/,
      "",
    )
  const sourceReady = source.includes("function siteUrl(slug: string)") &&
    source.includes("const targetUrl = siteUrl(slug);") &&
    source.includes("itemTile.href = siteUrl(item.slug);") &&
    source.includes("const data = await fetchData;") &&
    !source.includes("[Search]")
  if (!sourceReady) throw new Error("Unable to apply Quartz v5.0.0 search base-path patch")
  if (source !== originalSource) await writeFile(target, source, "utf8")

  const compiledTargets = [
    path.join(pluginDirectory, "dist", "index.js"),
    path.join(pluginDirectory, "dist", "components", "index.js"),
  ]
  const compiledHelper = `function aaeSiteUrl(t){let e=document.querySelector('script[src$="/postscript.js"]')?.src??window.location.origin+"/";return new URL(t.replace(/^\\\\/+/,""),new URL(".",e)).toString()}`
  for (const compiledTarget of compiledTargets) {
    let compiled = await readFile(compiledTarget, "utf8")
    if (compiled.includes("function aaeSiteUrl(t)")) {
      compiled = compiled.replace(/function aaeSiteUrl\(t\)\{[^}]+\}/, compiledHelper)
    } else {
      compiled = compiled.replace('var ut="basic"', `${compiledHelper}var ut="basic"`)
    }
    compiled = compiled
      .replace('new URL("/"+t,window.location.origin).toString()', "aaeSiteUrl(t)")
      .replace('M.href="/"+y.slug', "M.href=aaeSiteUrl(y.slug)")
      .replace('await(await fetch("/static/contentIndex.json")).json()', "await fetchData")
      .replace('console.log("[Search] hideSearch called, stack:",new Error().stack),', "")
      .replace('console.log("[Search] showSearch called, type:",_),', "")
      .replace('console.log("[Search] container.classList after add:",n.classList.toString()),', "")
      .replace('console.log("[Search] focus called, container active:",n.classList.contains("active"))', "")
      .replace('console.log("[Search] Button click event, target:",_.target,"currentTarget:",_.currentTarget),', "")
      .replace(/\.focus\(\),\}/g, ".focus()}")
    const compiledReady = compiled.includes("function aaeSiteUrl(t)") &&
      compiled.includes("t.replace(/^\\\\/+/,") &&
      compiled.includes("aaeSiteUrl(t)") &&
      compiled.includes("M.href=aaeSiteUrl(y.slug)") &&
      compiled.includes("await fetchData") &&
      !compiled.includes('fetch("/static/contentIndex.json")') &&
      !compiled.includes("[Search]")
    if (!compiledReady) throw new Error("Unable to patch compiled Quartz search base paths")
    await writeFile(compiledTarget, compiled, "utf8")
  }
  await writeFile(marker, `${patchVersion}\n`, "utf8")
}

async function patchReadOnlyCheckboxes(pluginLock) {
  const pluginDirectory = path.join(RUNTIME_ROOT, ".quartz", "plugins", "obsidian-flavored-markdown")
  const sourceTarget = path.join(pluginDirectory, "src", "scripts", "checkbox.inline.ts")
  const compiledTarget = path.join(pluginDirectory, "dist", "index.js")
  const readOnlySource = `const setupReadOnlyCheckboxes = () => {
  const checkboxes = document.querySelectorAll(
    "input.checkbox-toggle",
  ) as NodeListOf<HTMLInputElement>;
  checkboxes.forEach((checkbox) => {
    checkbox.disabled = true;
    checkbox.setAttribute("aria-disabled", "true");
  });
};

document.addEventListener("nav", setupReadOnlyCheckboxes);
document.addEventListener("render", setupReadOnlyCheckboxes);
`
  await writeFile(sourceTarget, readOnlySource, "utf8")

  let compiled = await readFile(compiledTarget, "utf8")
  const scriptMarker = "// src/scripts/checkbox.inline.ts"
  const nextMarker = "// src/scripts/mermaid.inline.ts"
  const markerIndex = compiled.indexOf(scriptMarker)
  const declarationIndex = compiled.indexOf("var checkbox_inline_default =", markerIndex)
  const nextMarkerIndex = compiled.indexOf(nextMarker, declarationIndex)
  if (markerIndex < 0 || declarationIndex < 0 || nextMarkerIndex < 0) {
    throw new Error("Unable to locate the Quartz checkbox runtime for the read-only patch")
  }
  const browserScript = `const setupReadOnlyCheckboxes = () => {
  document.querySelectorAll("input.checkbox-toggle").forEach((checkbox) => {
    checkbox.disabled = true;
    checkbox.setAttribute("aria-disabled", "true");
  });
};
document.addEventListener("nav", setupReadOnlyCheckboxes);
document.addEventListener("render", setupReadOnlyCheckboxes);
`
  compiled = `${compiled.slice(0, declarationIndex)}var checkbox_inline_default = ${JSON.stringify(browserScript)};\n\n${compiled.slice(nextMarkerIndex)}`
  const checkboxNode = `      disabled: false,
      className: "checkbox-toggle"`
  const readOnlyCheckboxNode = `      disabled: true,
      ariaDisabled: "true",
      className: "checkbox-toggle"`
  if (compiled.includes(checkboxNode)) compiled = compiled.replace(checkboxNode, readOnlyCheckboxNode)
  await writeFile(compiledTarget, compiled, "utf8")

  const sourceReady = !readOnlySource.includes("localStorage") && readOnlySource.includes("checkbox.disabled = true")
  const compiledReady = !compiled.slice(markerIndex, nextMarkerIndex).includes("localStorage") &&
    compiled.includes("aria-disabled") &&
    compiled.includes('disabled: true,\n      ariaDisabled: "true"') &&
    compiled.includes("var checkbox_inline_default =")
  if (!sourceReady || !compiledReady) {
    throw new Error(`Unable to disable checkbox progress persistence for plugin ${pluginLock.plugins["obsidian-flavored-markdown"].commit}`)
  }
}

export function secureMermaidSource(source) {
  const patched = source
    // Mermaid re-renders the original source before parsing it.  textContent
    // keeps hostile HTML/event-handler text inert until Mermaid parses the
    // diagram under its strict security policy.
    .replace("node.innerHTML = oldText;", "node.textContent = oldText;")
    .replace('securityLevel: "loose"', 'securityLevel: "strict"')
  if (!patched.includes("node.textContent = oldText;") ||
      !patched.includes('securityLevel: "strict"') ||
      patched.includes("node.innerHTML = oldText;")) {
    throw new Error("Unable to apply Mermaid source security patch")
  }
  return patched
}

// Quartz's locked plugin currently embeds this legacy CDN URL. It is only the
// patch target; the browser receives the separately pinned Mermaid dependency
// from this website's own node_modules tree.
const QUARTZ_MERMAID_REMOTE_URL = "https://cdnjs.cloudflare.com/ajax/libs/mermaid/11.4.0/mermaid.esm.min.mjs"

const MERMAID_SOURCE_URL_HELPER = `const getMermaidAssetUrl = () => {
  const postscript = [...document.scripts].find((script) =>
    script.src.split("?")[0].endsWith("/postscript.js"),
  )?.src;
  if (!postscript) throw new Error("Unable to resolve the same-origin Mermaid asset");
  return new URL("static/mermaid.esm.min.mjs", new URL(".", postscript)).href;
};`

export function localMermaidSource(source) {
  let patched = source
  const existingHelper = /const getMermaidAssetUrl = \(\) => \{[\s\S]*?\n\};/
  if (existingHelper.test(patched)) {
    patched = patched.replace(existingHelper, MERMAID_SOURCE_URL_HELPER)
  } else {
    const declaration = "let mermaidImport = undefined;"
    if (!patched.includes(declaration)) {
      throw new Error("Unable to locate the Mermaid import declaration")
    }
    patched = patched.replace(declaration, `${declaration}\n${MERMAID_SOURCE_URL_HELPER}`)
  }
  patched = patched.replace(
    /mermaidImport\s*\|\|=\s*await import\(\s*\/\/ @ts-expect-error -- remote ESM import\s*"https:\/\/cdnjs\.cloudflare\.com\/ajax\/libs\/mermaid\/11\.4\.0\/mermaid\.esm\.min\.mjs"\s*\);/s,
    "mermaidImport ||= await import(getMermaidAssetUrl());",
  )
  if (!patched.includes("getMermaidAssetUrl()") || patched.includes(QUARTZ_MERMAID_REMOTE_URL)) {
    throw new Error("Unable to switch Mermaid to the same-origin asset")
  }
  return patched
}

export function removeMermaidCdnPreconnect(source) {
  const patched = source.replace(
    /\s*<link\s+rel="preconnect"\s+href="https:\/\/cdnjs\.cloudflare\.com"\s+crossOrigin="anonymous"\s*\/>/g,
    "",
  )
  if (patched.includes("https://cdnjs.cloudflare.com")) {
    throw new Error("Unable to remove the obsolete cdnjs preconnect from Quartz Head")
  }
  return patched
}

export function secureMermaidCompiled(compiled) {
  const scriptMarker = "// src/scripts/mermaid.inline.ts"
  const styleMarker = "// src/styles/mermaid.inline.scss"
  const markerIndex = compiled.indexOf(scriptMarker)
  const nextMarkerIndex = compiled.indexOf(styleMarker, markerIndex)
  if (markerIndex < 0 || nextMarkerIndex < 0) {
    throw new Error("Unable to locate the Quartz Mermaid runtime for the security patch")
  }
  const before = compiled.slice(0, nextMarkerIndex)
  const after = compiled.slice(nextMarkerIndex)
  const patchedBefore = before
    .replace("i.innerHTML=c", "i.textContent=c")
    .replace('securityLevel:"loose"', 'securityLevel:"strict"')
  if (!patchedBefore.includes("i.textContent=c") ||
      !patchedBefore.includes('securityLevel:"strict"') ||
      patchedBefore.includes("i.innerHTML=c")) {
    throw new Error("Unable to apply compiled Mermaid security patch")
  }
  return `${patchedBefore}${after}`
}

const MERMAID_COMPILED_URL_HELPER =
  'function aaeMermaidAssetUrl(){let e=[...document.scripts].find(e=>e.src.split("?")[0].endsWith("/postscript.js"))?.src;if(!e)throw new Error("Unable to resolve the same-origin Mermaid asset");return new URL("static/mermaid.esm.min.mjs",new URL(".",e)).href}'

export function localMermaidCompiled(compiled) {
  const scriptMarker = "// src/scripts/mermaid.inline.ts"
  const styleMarker = "// src/styles/mermaid.inline.scss"
  const markerIndex = compiled.indexOf(scriptMarker)
  const nextMarkerIndex = compiled.indexOf(styleMarker, markerIndex)
  if (markerIndex < 0 || nextMarkerIndex < 0) {
    throw new Error("Unable to locate the Quartz Mermaid runtime for the local asset patch")
  }
  const before = compiled.slice(0, nextMarkerIndex)
  const after = compiled.slice(nextMarkerIndex)
  let patchedBefore = before.replace(
    `L||(L=await import("${QUARTZ_MERMAID_REMOTE_URL}"))`,
    "L||(L=await import(aaeMermaidAssetUrl()))",
  )
  const existingHelper = /function aaeMermaidAssetUrl\(\)\{[\s\S]*?\}(?=async function M\(\)\{)/
  if (existingHelper.test(patchedBefore)) {
    patchedBefore = patchedBefore.replace(existingHelper, MERMAID_COMPILED_URL_HELPER)
  } else {
    const functionMarker = "async function M(){"
    if (!patchedBefore.includes(functionMarker)) {
      throw new Error("Unable to locate the compiled Mermaid loader")
    }
    patchedBefore = patchedBefore.replace(functionMarker, `${MERMAID_COMPILED_URL_HELPER}${functionMarker}`)
  }
  if (!patchedBefore.includes("function aaeMermaidAssetUrl(){") ||
      !patchedBefore.includes("await import(aaeMermaidAssetUrl())") ||
      patchedBefore.includes(QUARTZ_MERMAID_REMOTE_URL)) {
    throw new Error("Unable to switch compiled Mermaid to the same-origin asset")
  }
  return `${patchedBefore}${after}`
}

async function patchMermaidSecurity(pluginLock) {
  const pluginDirectory = path.join(RUNTIME_ROOT, ".quartz", "plugins", "obsidian-flavored-markdown")
  const sourceTarget = path.join(pluginDirectory, "src", "scripts", "mermaid.inline.ts")
  const compiledTarget = path.join(pluginDirectory, "dist", "index.js")
  const marker = path.join(RUNTIME_ROOT, ".aae-mermaid-security-ready")
  const patchVersion = `${pluginLock.plugins["obsidian-flavored-markdown"].commit}:security-v2-local-mermaid`

  let source = await readFile(sourceTarget, "utf8")
  const originalSource = source
  source = localMermaidSource(secureMermaidSource(source))
  if (source !== originalSource) await writeFile(sourceTarget, source, "utf8")

  const compiled = localMermaidCompiled(secureMermaidCompiled(await readFile(compiledTarget, "utf8")))
  await writeFile(compiledTarget, compiled, "utf8")
  await writeFile(marker, `${patchVersion}\n`, "utf8")
}

async function patchQuartzHead() {
  const target = path.join(RUNTIME_ROOT, "quartz", "components", "Head.tsx")
  const source = await readFile(target, "utf8")
  const patched = removeMermaidCdnPreconnect(source)
  if (patched !== source) await writeFile(target, patched, "utf8")
}

async function stageMermaidAssets() {
  const packageRoot = path.join(WEBSITE_ROOT, "node_modules", "mermaid", "dist")
  const packageChunks = path.join(packageRoot, "chunks", "mermaid.esm.min")
  const staticRoot = path.join(RUNTIME_ROOT, "quartz", "static")
  const entryTarget = path.join(staticRoot, "mermaid.esm.min.mjs")
  const chunkTarget = path.join(staticRoot, "chunks", "mermaid.esm.min")
  assertRuntimePath(entryTarget)
  assertRuntimePath(chunkTarget)

  const chunks = (await readdir(packageChunks, { withFileTypes: true }))
    .filter((entry) => entry.isFile() && entry.name.endsWith(".mjs"))
  if (chunks.length === 0) throw new Error("The installed Mermaid package has no browser ESM chunks")

  await rm(chunkTarget, { recursive: true, force: true })
  await mkdir(chunkTarget, { recursive: true })
  await cp(path.join(packageRoot, "mermaid.esm.min.mjs"), entryTarget, { force: true })
  for (const chunk of chunks) {
    await cp(path.join(packageChunks, chunk.name), path.join(chunkTarget, chunk.name), { force: true })
  }
}

export async function bootstrapRuntime() {
  const version = JSON.parse(await readFile(path.join(WEBSITE_ROOT, "quartz.version.json"), "utf8"))
  assertRuntimePath(RUNTIME_ROOT)
  await mkdir(path.join(CACHE_ROOT, "npm"), { recursive: true })
  await mkdir(path.join(CACHE_ROOT, "tmp"), { recursive: true })
  const commandEnv = runtimeEnvironment()

  let currentCommit = ""
  if (await exists(path.join(RUNTIME_ROOT, ".git"))) {
    try {
      currentCommit = await output("git", ["rev-parse", "HEAD"], RUNTIME_ROOT)
    } catch {
      currentCommit = ""
    }
  }

  if (currentCommit !== version.commit) {
    if (await exists(RUNTIME_ROOT)) await rm(RUNTIME_ROOT, { recursive: true, force: true })
    await mkdir(path.dirname(RUNTIME_ROOT), { recursive: true })
    await run("git", ["clone", "--depth", "1", "--branch", version.tag, version.repository, RUNTIME_ROOT], {
      cwd: WEBSITE_ROOT,
    })
    currentCommit = await output("git", ["rev-parse", "HEAD"], RUNTIME_ROOT)
    if (currentCommit !== version.commit) {
      throw new Error(`Quartz commit mismatch: expected ${version.commit}, got ${currentCommit}`)
    }
  }

  const pluginLock = await preparePluginLock(version.commit)
  await patchWindowsPluginRestore()
  await cp(
    path.join(WEBSITE_ROOT, "config", "quartz.config.yaml"),
    path.join(RUNTIME_ROOT, "quartz.config.yaml"),
    { force: true },
  )

  const npmMarker = path.join(RUNTIME_ROOT, ".aae-npm-ready")
  const packageLockHash = await fileHash(path.join(RUNTIME_ROOT, "package-lock.json"))
  const npmReady = await exists(path.join(RUNTIME_ROOT, "node_modules")) &&
    await exists(npmMarker) &&
    (await readFile(npmMarker, "utf8")).trim() === packageLockHash
  if (!npmReady) {
    await runPackageManager("npm", ["ci"], { cwd: RUNTIME_ROOT, env: commandEnv })
    await writeFile(npmMarker, `${packageLockHash}\n`, "utf8")
  }

  const pluginMarker = path.join(RUNTIME_ROOT, ".aae-plugins-ready")
  const pluginLockHash = await fileHash(path.join(RUNTIME_ROOT, "quartz.lock.json"))
  const pluginsDirectory = path.join(RUNTIME_ROOT, ".quartz", "plugins")
  const markerMatches = await exists(pluginMarker) &&
    (await readFile(pluginMarker, "utf8")).trim() === pluginLockHash
  const pluginsReady = await exists(pluginsDirectory) &&
    await pluginTreeMatchesLock(pluginsDirectory, pluginLock)
  if (pluginsReady && !markerMatches) {
    await writeFile(pluginMarker, `${pluginLockHash}\n`, "utf8")
  }
  if (!pluginsReady) {
    assertRuntimePath(pluginsDirectory)
    await mkdir(pluginsDirectory, { recursive: true })
    for (const entry of await readdir(pluginsDirectory, { withFileTypes: true })) {
      if (!entry.isDirectory()) continue
      const pluginDirectory = path.join(pluginsDirectory, entry.name)
      assertRuntimePath(pluginDirectory)
      if (!REQUIRED_PLUGINS.includes(entry.name) ||
          !await pluginMatchesLock(pluginsDirectory, entry.name, pluginLock)) {
        await rm(pluginDirectory, { recursive: true, force: true })
      }
    }
    await runPackageManager("npx", ["quartz", "plugin", version.pluginCommand], {
      cwd: RUNTIME_ROOT,
      env: commandEnv,
    })
    if (!await pluginTreeMatchesLock(pluginsDirectory, pluginLock)) {
      throw new Error("Quartz plugins failed lockfile integrity verification after restore")
    }
    await writeFile(pluginMarker, `${pluginLockHash}\n`, "utf8")
  }
  await patchTagPageRootLinks(pluginLock)
  await patchSearchBasePath(pluginLock)
  await patchReadOnlyCheckboxes(pluginLock)
  await patchMermaidSecurity(pluginLock)
  await patchQuartzHead()
  await cp(path.join(WEBSITE_ROOT, "overlay"), RUNTIME_ROOT, { recursive: true, force: true })
  await stageMermaidAssets()

  return { runtimeRoot: RUNTIME_ROOT, commit: currentCommit }
}

if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) {
  await bootstrapRuntime()
}
