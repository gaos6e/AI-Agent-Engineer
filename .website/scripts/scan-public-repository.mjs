import { lstat, readFile, readdir } from "node:fs/promises"
import os from "node:os"
import path from "node:path"
import { pathToFileURL } from "node:url"

const MAX_REPOSITORY_FILE_BYTES = 8_500_000
const BINARY_EXTENSIONS = new Set([".gif", ".jpeg", ".jpg", ".png", ".webp"])
const FORBIDDEN_DIRECTORY_NAMES = new Set([
  ".cache",
  ".generated",
  ".playwright-cli",
  ".runtime",
  "node_modules",
  "public",
])
const FORBIDDEN_FILE_EXTENSIONS = new Set([
  ".ckpt",
  ".db",
  ".dll",
  ".env",
  ".exe",
  ".key",
  ".onnx",
  ".p12",
  ".pem",
  ".pfx",
  ".pt",
  ".pth",
  ".pyc",
  ".safetensors",
  ".sqlite",
])
const FORBIDDEN_FILE_NAMES = new Set([
  ".git-credentials",
  ".netrc",
  ".npmrc",
  ".pypirc",
  "aws_credentials",
  "credentials",
  "credentials.json",
  "id_ed25519",
  "id_rsa",
])
const ALLOWED_WORKFLOW_FILES = new Set([".github/workflows/deploy-pages.yml"])
const PROGRESS_TOKEN = ["ai", "learning", "completed"].join("_")

export const HIGH_CONFIDENCE_SECRET_PATTERNS = [
  ["private key", /-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----/],
  ["AWS access key", /(?<![A-Z0-9])AKIA[A-Z0-9]{16}(?![A-Z0-9])/],
  ["OpenAI-style API key", /(?<![A-Za-z0-9])sk-(?:proj-)?[A-Za-z0-9_-]{20,}(?![A-Za-z0-9_-])/],
  ["Anthropic API key", /(?<![A-Za-z0-9])sk-ant-[A-Za-z0-9_-]{20,}(?![A-Za-z0-9_-])/],
  ["GitHub token", /(?<![A-Za-z0-9])gh[pousr]_[A-Za-z0-9]{30,}(?![A-Za-z0-9])/],
  ["GitHub fine-grained token", /(?<![A-Za-z0-9])github_pat_[A-Za-z0-9_]{50,}(?![A-Za-z0-9_])/],
  ["Google API key", /(?<![A-Za-z0-9])AIza[A-Za-z0-9_-]{35}(?![A-Za-z0-9_-])/],
  ["Slack token", /(?<![A-Za-z0-9])xox[baprs]-[A-Za-z0-9-]{20,}(?![A-Za-z0-9-])/],
  ["Hugging Face token", /(?<![A-Za-z0-9])hf_[A-Za-z0-9]{30,}(?![A-Za-z0-9])/],
  ["Stripe live key", /(?<![A-Za-z0-9])sk_live_[A-Za-z0-9]{20,}(?![A-Za-z0-9])/],
]

function toPosix(value) {
  return value.split(path.sep).join("/")
}

export function isSensitiveFileName(value) {
  const name = value.toLowerCase()
  if (name === ".env.example") return false
  return name === ".env" || name.startsWith(".env.") || FORBIDDEN_FILE_NAMES.has(name)
}

export function validateWorkflow(relative, text) {
  if (!ALLOWED_WORKFLOW_FILES.has(relative)) {
    throw new Error(`Unexpected workflow entered the public repository: ${relative}`)
  }
  if (!/^permissions:\s*\{\}\s*$/m.test(text)) {
    throw new Error(`Workflow must default to no permissions: ${relative}`)
  }
  if (!/^\s*persist-credentials:\s*false\s*$/m.test(text)) {
    throw new Error(`Workflow checkout must disable persisted credentials: ${relative}`)
  }
  if (/^\s*(?:pull_request_target|workflow_run)\s*:/m.test(text)) {
    throw new Error(`Privileged workflow trigger is not allowed: ${relative}`)
  }
  const actions = [...text.matchAll(/^\s*(?:-\s*)?uses:\s*([^\s#]+)(?:\s+#.*)?$/gm)]
  if (actions.length === 0) throw new Error(`Workflow has no pinned actions: ${relative}`)
  for (const match of actions) {
    if (!/@[0-9a-f]{40}$/i.test(match[1])) {
      throw new Error(`Workflow action is not pinned to a full commit SHA: ${relative}: ${match[1]}`)
    }
  }
}

function machineFragments(disallowedRoots) {
  const roots = [...disallowedRoots, os.homedir()]
  return [...new Set(roots
    .filter(Boolean)
    .flatMap((root) => {
      const resolved = path.resolve(root)
      return [resolved, resolved.replaceAll("\\", "/")]
    }))]
}

async function walkRepository(root) {
  const files = []
  async function visit(directory) {
    for (const entry of await readdir(directory, { withFileTypes: true })) {
      if (entry.name === ".git") continue
      const absolute = path.join(directory, entry.name)
      const relative = toPosix(path.relative(root, absolute))
      const metadata = await lstat(absolute)
      if (metadata.isSymbolicLink()) throw new Error(`Symbolic link is not allowed in the public repository: ${relative}`)
      if (entry.isDirectory()) {
        if (FORBIDDEN_DIRECTORY_NAMES.has(entry.name)) {
          throw new Error(`Generated or dependency directory entered the public repository: ${relative}`)
        }
        await visit(absolute)
      } else if (entry.isFile()) {
        if (metadata.size > MAX_REPOSITORY_FILE_BYTES) {
          throw new Error(`Repository file exceeds the publication size limit: ${relative}`)
        }
        const extension = path.extname(entry.name).toLowerCase()
        if (isSensitiveFileName(entry.name)) {
          throw new Error(`Sensitive configuration filename entered the public repository: ${relative}`)
        }
        if (FORBIDDEN_FILE_EXTENSIONS.has(extension)) {
          throw new Error(`Forbidden file type entered the public repository: ${relative}`)
        }
        if (relative.startsWith(".github/workflows/") && !ALLOWED_WORKFLOW_FILES.has(relative)) {
          throw new Error(`Unexpected workflow entered the public repository: ${relative}`)
        }
        files.push({ absolute, relative, size: metadata.size, extension })
      }
    }
  }
  await visit(root)
  return files
}

export async function scanPublicRepository(rootArgument, options = {}) {
  const root = path.resolve(rootArgument)
  const fragments = machineFragments(options.disallowedRoots ?? [])
  const files = await walkRepository(root)
  let textFiles = 0
  let binaryFiles = 0
  let totalBytes = 0

  for (const file of files) {
    totalBytes += file.size
    const bytes = await readFile(file.absolute)
    if (BINARY_EXTENSIONS.has(file.extension) || bytes.includes(0)) {
      binaryFiles += 1
      continue
    }
    textFiles += 1
    const text = bytes.toString("utf8")
    if (file.relative.startsWith(".github/workflows/")) validateWorkflow(file.relative, text)
    for (const [label, pattern] of HIGH_CONFIDENCE_SECRET_PATTERNS) {
      if (pattern.test(text)) throw new Error(`Possible ${label} in public repository file: ${file.relative}`)
    }
    if (/^docs-(?:CN|EN)\//.test(file.relative) && text.toLowerCase().includes(PROGRESS_TOKEN)) {
      throw new Error(`Learning-progress metadata entered the public snapshot: ${file.relative}`)
    }
    for (const fragment of fragments) {
      if (fragment.length >= 4 && text.toLowerCase().includes(fragment.toLowerCase())) {
        throw new Error(`Machine-specific path entered the public repository: ${file.relative}`)
      }
    }
  }

  return {
    repositoryFiles: files.length,
    textFiles,
    binaryFiles,
    totalBytes,
    secretFindings: 0,
    progressLeaks: 0,
    machinePathLeaks: 0,
  }
}

if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) {
  const result = await scanPublicRepository(process.argv[2] || path.resolve(process.cwd(), ".."))
  console.log(JSON.stringify(result))
}
