import { execFile } from "node:child_process"
import { cp, lstat, mkdir, readFile, readdir, realpath, rm, stat } from "node:fs/promises"
import path from "node:path"
import { promisify } from "node:util"
import { pathToFileURL } from "node:url"
import {
  GENERATED_ROOT,
  WEBSITE_ROOT,
  prepareContent,
} from "./prepare-content.mjs"
import {
  DEFAULT_LOCALE,
  SITE_LOCALE_IDS,
  contentRootFor,
  getSiteLocale,
  manifestPathFor,
} from "../config/site-locales.mjs"
import { scanPublicRepository } from "./scan-public-repository.mjs"

const execFileAsync = promisify(execFile)
const PROJECT_ROOT = path.resolve(WEBSITE_ROOT, "..")
const EXPORT_ROOT = path.join(WEBSITE_ROOT, ".cache")
const EXPECTED_REMOTE = /(?:github\.com[/:])gaos6e\/AI-Agent-Engineer(?:\.git)?$/i
const WEBSITE_EXPORT_PATHS = [
  "config",
  "legal",
  "overlay",
  "scripts",
  "tests",
  ".gitignore",
  "DESIGN.md",
  "package-lock.json",
  "package.json",
  "PUBLISHING.md",
  "quartz.version.json",
]

function assertInside(parent, child, label) {
  const relative = path.relative(parent, child)
  if (!relative || relative.startsWith("..") || path.isAbsolute(relative)) {
    throw new Error(`${label} must be a child of ${parent}`)
  }
}

async function exists(target) {
  try {
    await stat(target)
    return true
  } catch {
    return false
  }
}

async function assertPublicationClone(destination) {
  assertInside(EXPORT_ROOT, destination, "Export destination")
  const exportRootMetadata = await lstat(EXPORT_ROOT)
  const destinationMetadata = await lstat(destination)
  if (exportRootMetadata.isSymbolicLink() || destinationMetadata.isSymbolicLink()) {
    throw new Error("Export root and destination must not be symbolic links or junctions")
  }
  if (!exportRootMetadata.isDirectory() || !destinationMetadata.isDirectory()) {
    throw new Error("Export root and destination must be directories")
  }
  const exportRootReal = await realpath(EXPORT_ROOT)
  const destinationReal = await realpath(destination)
  assertInside(exportRootReal, destinationReal, "Real export destination")
  if (!await exists(path.join(destination, ".git"))) {
    throw new Error("Export destination must already be a Git clone")
  }
  const { stdout } = await execFileAsync(
    "git",
    ["config", "--get", "remote.origin.url"],
    { cwd: destination, encoding: "utf8" },
  )
  if (!EXPECTED_REMOTE.test(stdout.trim())) {
    throw new Error("Refusing to export into a clone with an unexpected origin remote")
  }
  const { stdout: topLevelOutput } = await execFileAsync(
    "git",
    ["rev-parse", "--show-toplevel"],
    { cwd: destination, encoding: "utf8" },
  )
  if (path.resolve(topLevelOutput.trim()) !== destination) {
    throw new Error("Export destination is not the root of the publication clone")
  }
  const { stdout: statusOutput } = await execFileAsync(
    "git",
    ["status", "--porcelain=v1", "--untracked-files=all"],
    { cwd: destination, encoding: "utf8" },
  )
  if (statusOutput.trim()) {
    throw new Error("Publication clone has uncommitted changes; refusing to overwrite them")
  }
}

async function resetExportWorktree(destination) {
  for (const entry of await readdir(destination, { withFileTypes: true })) {
    if (entry.name === ".git") continue
    const target = path.resolve(destination, entry.name)
    assertInside(destination, target, "Exported worktree path")
    await rm(target, { recursive: true, force: true })
  }
}

async function copyWebsiteSource(destination) {
  const target = path.join(destination, ".website")
  await mkdir(target, { recursive: true })
  for (const relative of WEBSITE_EXPORT_PATHS) {
    const source = path.join(WEBSITE_ROOT, relative)
    const output = path.join(target, relative)
    assertInside(WEBSITE_ROOT, source, "Website source path")
    assertInside(target, output, "Website export path")
    await cp(source, output, { recursive: true, force: true })
  }
}

async function copyPublicSnapshot(destination, locale, generatedPages) {
  const target = path.join(destination, getSiteLocale(locale).sourceDirectory)
  const contentRoot = contentRootFor(GENERATED_ROOT, locale)
  await cp(contentRoot, target, { recursive: true, force: true })
  for (const relative of generatedPages) {
    const generated = path.join(target, ...relative.split("/"))
    assertInside(target, generated, "Generated page")
    await rm(generated, { force: true })
  }
  const generatedLicenses = path.join(target, "_licenses")
  assertInside(target, generatedLicenses, "Generated license directory")
  await rm(generatedLicenses, { recursive: true, force: true })
}

async function copyRepositoryFiles(destination) {
  const workflowTarget = path.join(destination, ".github", "workflows", "deploy-pages.yml")
  await mkdir(path.dirname(workflowTarget), { recursive: true })
  await cp(
    path.join(PROJECT_ROOT, ".github", "workflows", "deploy-pages.yml"),
    workflowTarget,
    { force: true },
  )
  for (const relative of ["README.md", ".gitignore"]) {
    await cp(path.join(PROJECT_ROOT, relative), path.join(destination, relative), { force: true })
  }
}

async function countFiles(root) {
  let count = 0
  async function visit(directory) {
    for (const entry of await readdir(directory, { withFileTypes: true })) {
      if (entry.name === ".git") continue
      const absolute = path.join(directory, entry.name)
      if (entry.isDirectory()) await visit(absolute)
      else if (entry.isFile()) count += 1
    }
  }
  await visit(root)
  return count
}

export async function exportPublicRepository(destinationArgument) {
  if (!destinationArgument) throw new Error("Usage: npm run export:repo -- <clone-directory>")
  const destination = path.resolve(destinationArgument)
  await assertPublicationClone(destination)
  await prepareContent()
  const manifests = new Map(await Promise.all(SITE_LOCALE_IDS.map(async (locale) => [
    locale,
    JSON.parse(await readFile(manifestPathFor(GENERATED_ROOT, locale), "utf8")),
  ])))
  await resetExportWorktree(destination)
  await mkdir(destination, { recursive: true })
  await Promise.all([
    copyWebsiteSource(destination),
    ...SITE_LOCALE_IDS.map((locale) =>
      copyPublicSnapshot(destination, locale, manifests.get(locale).generatedPages)),
    copyRepositoryFiles(destination),
  ])

  const scan = await scanPublicRepository(destination, {
    disallowedRoots: [path.resolve(PROJECT_ROOT, "..", "..")],
  })

  const result = {
    destination,
    publicMarkdown: [...manifests.values()].reduce(
      (sum, manifest) => sum + manifest.publishedMarkdown.length + manifest.stubMarkdown.length,
      0,
    ),
    publicAssets: [...manifests.values()].reduce((sum, manifest) => sum + manifest.assets.length, 0),
    excludedSourceFiles: [...manifests.values()].reduce((sum, manifest) => sum + manifest.excluded.length, 0),
    repositoryFiles: await countFiles(destination),
    sourceDigest: manifests.get(DEFAULT_LOCALE).sourceDigest,
    scan,
  }
  console.log(JSON.stringify(result))
  return result
}

if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) {
  await exportPublicRepository(process.argv[2])
}
