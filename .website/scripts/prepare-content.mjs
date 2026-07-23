import { createHash } from "node:crypto"
import {
  copyFile,
  mkdir,
  readFile,
  readdir,
  rm,
  stat,
  utimes,
  writeFile,
} from "node:fs/promises"
import path from "node:path"
import { fileURLToPath, pathToFileURL } from "node:url"
import { isMap, isScalar, isSeq, parseDocument } from "yaml"
import {
  DEFAULT_LOCALE,
  SITE_LOCALE_IDS,
  contentRootFor,
  getSiteLocale,
  manifestPathFor,
  pageRouteFor,
  slugifyPublishedPath,
  sourceRootFor,
} from "../config/site-locales.mjs"
import { HIGH_CONFIDENCE_SECRET_PATTERNS } from "./scan-public-repository.mjs"

export const WEBSITE_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..")
export const GENERATED_ROOT = path.join(WEBSITE_ROOT, ".generated")
export const DOCS_ROOT = sourceRootFor(WEBSITE_ROOT, DEFAULT_LOCALE)
export const CONTENT_ROOT = contentRootFor(GENERATED_ROOT, DEFAULT_LOCALE)
export const MANIFEST_PATH = manifestPathFor(GENERATED_ROOT, DEFAULT_LOCALE)
const LOCAL_VAULT_ROOT = path.resolve(DOCS_ROOT, "..", "..", "..")
const WINDOWS_ABSOLUTE_PROJECT_ROOT_PATTERN =
  /[A-Za-z]:[\\/](?:[^\\/\r\n"'`<>|]+[\\/])*AI Agent Engineer(?=[\\/\s"'`]|$)/i

const VAULT_PREFIXES = [
  "Knowledge/AI Agent Engineer/docs/",
  "Knowledge/AI Agent Engineer/docs-CN/",
  "Knowledge/AI Agent Engineer/docs-EN/",
]

function stripVaultPrefix(value) {
  const prefix = VAULT_PREFIXES.find((candidate) => value.startsWith(candidate))
  return prefix ? value.slice(prefix.length) : undefined
}
const MAX_CODE_BYTES = 2_000_000
const MAX_IMAGE_BYTES = 8_000_000
const CODE_EXTENSIONS = new Set([".py", ".json", ".csv", ".ipynb", ".jsonl", ".sh", ".txt"])
const IMAGE_EXTENSIONS = new Set([".png", ".jpg", ".jpeg", ".webp", ".gif"])
// Frozen legacy reference trees are intentionally listed explicitly. They may
// contain mirrors, translations, or local summaries derived from upstream
// documentation. A source URL or a metadata-only relabel is not proof that a
// body is current or may be redistributed, so every page fails closed until
// its content shape, provenance, license, and quality have all been reviewed.
const LEGACY_REFERENCE_PREFIXES = [
  "深度学习/",
  "LangChain/01-Learn.md",
  "LangChain/LICENSE-LangChain-docs.md",
  "LangChain/01-Conceptual Overviews/",
  "LangChain/02-LangChain/",
  "LangChain/03-LangGraph/",
  "LangChain/04-Multi-agent/",
  "LangChain/05-Deep Agents/",
  "LangChain/06-Additional Resources/",
  "MCP/01-入门/",
  "MCP/02-了解 MCP/",
  "MCP/03-使用 MCP 开发/",
  "MCP/04-客户端/",
  "MCP/05-安全/",
  "MCP/06-开发者工具/",
  "MCP/07-示例/",
  "Agent Skills/01-概览/",
  "Agent Skills/02-技能创建者/",
]
const LEGACY_REFERENCE_LOCAL_FILES = new Set([
  "深度学习/00-目录.md",
  "深度学习/00-来源与目录.md",
  // This is an independently authored engineering overlay, not a D2L mirror.
  // Keep the exception exact so it cannot release neighboring reference pages.
  "深度学习/00-工程实践与现代化路线.md",
])
const LEGACY_REFERENCE_ASSET_EXCLUDE_PREFIXES = ["LangChain/attachments/"]
// These six images are the only frozen LangChain reference assets that have
// been individually checked against the upstream MIT repository.  Keep the
// enclosing attachment tree fail-closed; the phase-17 maintenance record
// records the upstream commit, blob paths, and content digests.
const LANGCHAIN_PUBLIC_REFERENCE_IMAGE_DIGESTS = new Map([
  ["LangChain/attachments/images/rag_indexing.png", "d24e6b3c8631685e5efd85e0cf7714dce7a7f1e3186655b1e00cbeccb894431b"],
  ["LangChain/attachments/images/rag_retrieval_generation.png", "723d38f4c3e9fb1c84eb4fdaa32ff2375b04f2e154692ac117a06028afc610f3"],
  ["LangChain/attachments/images/langgraph-hybrid-rag-tutorial.png", "e8a37e3d1df2e71e724506714acb32da3465a3b6b1c81f3e8ac2283c74b887f4"],
  ["LangChain/attachments/oss/images/agentic-rag-output.png", "23e192104524074fb91cb17d8fca7ef0f6777f6c5910deadd30b9ac98ba51c39"],
  ["LangChain/attachments/oss/images/sql-agent-langgraph.png", "72cb96ea3b2db9054e076197b69b536e081aa6ef3a11965b900c558d4e5a4755"],
  ["LangChain/attachments/images/data_analysis_slack_response.png", "36f3f251bcf8603adc9462b699047f269f5e2f3ff654c386d927668217654092"],
])
const LEGACY_REFERENCE_ASSET_ALLOWED_PREFIXES = [
  "LangChain/00-初学者路线/examples/",
  "MCP/examples/",
]
// Exact, reviewed offline examples that belong to the independently authored
// deep-learning overlay above. Do not widen this to the whole examples folder:
// frozen D2L material must remain unable to expose adjacent assets by default.
const LEGACY_REFERENCE_ASSET_ALLOWED_FILES = new Set([
  "深度学习/examples/training_run_audit.py",
  "深度学习/examples/test_training_run_audit.py",
])
const AGENT_SKILLS_PUBLIC_EXAMPLE_FILES = new Set([
  "Agent Skills/examples/test_validate_skill.py",
  "Agent Skills/examples/validate_skill.py",
  "Agent Skills/examples/text-statistics/SKILL.md",
  "Agent Skills/examples/text-statistics/evals/evals.json",
  "Agent Skills/examples/text-statistics/scripts/text_stats.py",
])
const PYTHON_PUBLIC_FILES = new Set([
  "Python基础/00-目录.md",
  "Python基础/00-Agent工程实践.md",
])
const PYTHON_PUBLIC_PREFIXES = ["Python基础/Agent工程路线/", "Python基础/examples/"]
const AGENTIC_PUBLIC_FILES = new Set(["Agentic Design Patterns/00-目录.md"])
const AGENTIC_PUBLIC_PREFIXES = ["Agentic Design Patterns/00-初学者路线/"]
const CONTENT_ORIGINS = new Set(["original", "curated", "third-party", "mixed"])
const CONTENT_STATUSES = new Set(["validated", "dynamic", "needs-review", "frozen-reference"])
const COURSE_SCHEMA_VERSION = 2
const COURSE_COPY = {
  "zh-CN": {
    domains: new Map([
      ["foundations", "工程与数学基础"],
      ["model-and-context", "模型与上下文"],
      ["retrieval-and-data", "检索与数据"],
      ["multimodal", "多模态"],
      ["agent-runtime", "Agent 运行时"],
      ["framework-practice", "框架实践"],
      ["evaluation-reliability", "评测与可靠性"],
      ["safety-governance", "安全与治理"],
      ["production-ops", "生产运维"],
      ["frontier-reference", "前沿与参考"],
    ]),
    tracks: new Map([
      ["agent_app", "Agent 应用开发"],
      ["rag", "RAG 与知识库"],
      ["agent_platform", "Agent 平台与可靠性"],
      ["multimodal_realtime", "多模态与实时交互"],
    ]),
    trackKinds: new Map([
      ["core", "核心"],
      ["recommended", "推荐"],
      ["optional", "可选"],
    ]),
  },
  en: {
    domains: new Map([
      ["foundations", "Engineering and mathematical foundations"],
      ["model-and-context", "Models and context"],
      ["retrieval-and-data", "Retrieval and data"],
      ["multimodal", "Multimodal systems"],
      ["agent-runtime", "Agent runtime"],
      ["framework-practice", "Framework practice"],
      ["evaluation-reliability", "Evaluation and reliability"],
      ["safety-governance", "Safety and governance"],
      ["production-ops", "Production operations"],
      ["frontier-reference", "Frontier and reference"],
    ]),
    tracks: new Map([
      ["agent_app", "Agent application development"],
      ["rag", "RAG and knowledge bases"],
      ["agent_platform", "Agent platform and reliability"],
      ["multimodal_realtime", "Multimodal and real-time interaction"],
    ]),
    trackKinds: new Map([
      ["core", "Core"],
      ["recommended", "Recommended"],
      ["optional", "Optional"],
    ]),
  },
}
const COURSE_DOMAIN_LABELS = COURSE_COPY[DEFAULT_LOCALE].domains
const COURSE_TRACK_LABELS = COURSE_COPY[DEFAULT_LOCALE].tracks
const COURSE_TRACK_KIND_LABELS = COURSE_COPY[DEFAULT_LOCALE].trackKinds
const COURSE_DOMAINS = new Set(COURSE_DOMAIN_LABELS.keys())
const COURSE_TRACK_ROLES = new Set(COURSE_TRACK_LABELS.keys())
const COURSE_TRACK_KINDS = new Set(["core", "recommended", "optional"])

function courseCopy(locale = DEFAULT_LOCALE) {
  return COURSE_COPY[getSiteLocale(locale).id]
}
const GOVERNANCE_KEYS = new Set([
  "content_origin",
  "content_status",
  "reference_layer_status",
  "license",
  "source_url",
  "attribution",
  "local_changes",
])
const PUBLIC_THIRD_PARTY_LICENSES = new Set(["mit", "apache-2.0", "cc-by-4.0", "cc0-1.0"])
const PUBLIC_SOURCE_PROTOCOLS = new Set(["http:", "https:"])
const LEGAL_LICENSE_FILES = new Set([
  "Agent-Skills-CC-BY-4.0.txt",
  "Apache-2.0.txt",
  "LangChain-MIT.txt",
  "MCP-MIT.txt",
  "Mermaid-MIT.txt",
  "Quartz-Community-MIT.txt",
  "Quartz-MIT.txt",
])
const LEGAL_LICENSE_SHA256 = new Map([
  [
    "Agent-Skills-CC-BY-4.0.txt",
    "9e5f1b3c610b9c2da5c313bf81d577a7d1acec686bdb0384edefa6df0f90cd94",
  ],
])
const PUBLIC_THIRD_PARTY_SOURCE_REGISTRY = [
  {
    id: "d2l-zh",
    routes: [
      { origin: "https://github.com", pathPrefix: "/d2l-ai/d2l-zh" },
      { origin: "https://zh-v2.d2l.ai", pathPrefix: "/" },
    ],
    licenses: new Set(["apache-2.0"]),
    licenseFile: "Apache-2.0.txt",
  },
  {
    id: "langchain-docs",
    routes: [
      { origin: "https://github.com", pathPrefix: "/langchain-ai/docs" },
      { origin: "https://docs.langchain.com", pathPrefix: "/" },
    ],
    licenses: new Set(["mit"]),
    licenseFile: "LangChain-MIT.txt",
  },
  {
    id: "model-context-protocol-archived-docs",
    routes: [
      { origin: "https://github.com", pathPrefix: "/modelcontextprotocol/docs" },
    ],
    licenses: new Set(["mit"]),
    licenseFile: "MCP-MIT.txt",
  },
  {
    id: "agent-skills-docs",
    routes: [
      {
        origin: "https://agentskills.io",
        pathExact: "/home.md",
        localPath: "Agent Skills/01-概览/01-Agent Skills Overview.md",
      },
      {
        origin: "https://agentskills.io",
        pathExact: "/specification.md",
        localPath: "Agent Skills/01-概览/02-Specification.md",
      },
      {
        origin: "https://agentskills.io",
        pathExact: "/clients.md",
        localPath: "Agent Skills/01-概览/03-Client Showcase.md",
      },
      ...[
        ["quickstart.md", "01-Quickstart.md"],
        ["best-practices.md", "02-Best practices.md"],
        ["optimizing-descriptions.md", "03-Optimizing descriptions.md"],
        ["evaluating-skills.md", "04-Evaluating skills.md"],
        ["using-scripts.md", "05-Using scripts.md"],
      ].map(([upstreamName, localName]) => ({
        origin: "https://agentskills.io",
        pathExact: `/skill-creation/${upstreamName}`,
        localPath: `Agent Skills/02-技能创建者/${localName}`,
      })),
    ],
    licenses: new Set(["cc-by-4.0"]),
    licenseFile: "Agent-Skills-CC-BY-4.0.txt",
    requiredAttribution: "Agent Skills project contributors",
    requiredChangeNotice: "Chinese translation, link normalization, and Obsidian formatting",
  },
  {
    id: "requests-docs",
    routes: [
      { origin: "https://github.com", pathPrefix: "/psf/requests" },
      { origin: "https://requests.readthedocs.io", pathPrefix: "/" },
    ],
    licenses: new Set(["apache-2.0"]),
    licenseFile: "Apache-2.0.txt",
  },
]
const UNKNOWN_LICENSES = new Set([
  "unknown",
  "unspecified",
  "not specified",
  "none",
  "unlicensed",
  "n/a",
  "null",
  "~",
  "false",
])

for (const registration of PUBLIC_THIRD_PARTY_SOURCE_REGISTRY) {
  if (!LEGAL_LICENSE_FILES.has(registration.licenseFile)) {
    throw new Error(`Registered third-party source lacks a copied license file: ${registration.id}`)
  }
}

export function assertLegalLicenseDigest(filename, contents) {
  const expected = LEGAL_LICENSE_SHA256.get(filename)
  if (!expected) return
  const actual = createHash("sha256").update(contents).digest("hex")
  if (actual !== expected) {
    throw new Error(`Copied license digest mismatch for ${filename}: ${actual}`)
  }
}

function toPosix(value) {
  return value.split(path.sep).join("/")
}

function assertInside(parent, child, label) {
  const relative = path.relative(parent, child)
  if (relative.startsWith("..") || path.isAbsolute(relative)) {
    throw new Error(`${label} escaped its allowed root: ${child}`)
  }
}

async function walk(root) {
  const result = []
  async function visit(directory) {
    const entries = await readdir(directory, { withFileTypes: true })
    for (const entry of entries) {
      const absolute = path.join(directory, entry.name)
      if (entry.isDirectory()) await visit(absolute)
      else if (entry.isFile()) result.push(absolute)
    }
  }
  await visit(root)
  return result.sort((left, right) => left.localeCompare(right, "zh-CN", { numeric: true }))
}

function isAllowedByPrefix(relativePath, files, prefixes) {
  return files.has(relativePath) || prefixes.some((prefix) => relativePath.startsWith(prefix))
}

function simpleYamlScalar(rawValue) {
  const value = String(rawValue ?? "").trim()
  const doubleQuoted = value.match(/^"((?:\\.|[^"\\])*)"\s*(?:#.*)?$/)
  if (doubleQuoted) {
    try {
      return JSON.parse(`"${doubleQuoted[1]}"`)
    } catch {
      return value
    }
  }
  const singleQuoted = value.match(/^'((?:''|[^'])*)'\s*(?:#.*)?$/)
  if (singleQuoted) return singleQuoted[1].replaceAll("''", "'")
  return value.replace(/\s+#.*$/, "").trim()
}

function frontmatterKeyPattern(key) {
  const escaped = key.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")
  return `(?:${escaped}|"${escaped}"|'${escaped}')`
}

function frontmatterValues(markdown, key) {
  const { frontmatter } = splitFrontmatter(markdown)
  if (!frontmatter) return []
  const keyPattern = frontmatterKeyPattern(key)
  return [...frontmatter.matchAll(new RegExp(`^${keyPattern}[ \\t]*:[ \\t]*(.*?)[ \\t]*$`, "gm"))]
    .map((match) => simpleYamlScalar(match[1]))
}

function parseGovernanceFields(relativePath, markdown) {
  const { frontmatter } = splitFrontmatter(markdown)
  const fields = new Map()
  if (!frontmatter) return fields

  for (const key of GOVERNANCE_KEYS) {
    if (frontmatterValues(markdown, key).length > 1) {
      throw new Error(`Duplicate ${key} in ${relativePath}`)
    }
  }

  const document = parseDocument(frontmatter, {
    uniqueKeys: true,
    merge: false,
    prettyErrors: false,
    logLevel: "silent",
  })
  const yamlIssue = document.errors[0] ?? document.warnings[0]
  if (yamlIssue) {
    throw new Error(`Invalid YAML frontmatter in ${relativePath}: ${yamlIssue.code}`)
  }
  if (!document.contents) return fields
  if (!isMap(document.contents)) {
    throw new Error(`YAML frontmatter must be a root mapping in ${relativePath}`)
  }

  function visit(node, depth) {
    if (isMap(node)) {
      for (const pair of node.items) {
        const keyNode = pair.key
        if (!isScalar(keyNode)) {
          throw new Error(`Unsupported YAML mapping key syntax in ${relativePath}`)
        }
        const semanticKey = keyNode.value == null ? "" : String(keyNode.value)
        if (semanticKey === "<<") {
          throw new Error(`YAML merge keys are not allowed in ${relativePath}`)
        }

        if (GOVERNANCE_KEYS.has(semanticKey)) {
          const canonicalValues = frontmatterValues(markdown, semanticKey)
          if (
            depth !== 0 ||
            canonicalValues.length !== 1 ||
            keyNode.tag ||
            keyNode.anchor ||
            keyNode.range && frontmatter.slice(keyNode.range[0], keyNode.range[1]).includes("\n")
          ) {
            throw new Error(
              `Unsupported ${semanticKey} YAML syntax in ${relativePath}; ` +
              "use one unindented root-level 'key: value' field",
            )
          }
          if (fields.has(semanticKey)) {
            throw new Error(`Duplicate ${semanticKey} in ${relativePath}`)
          }
          if (!isScalar(pair.value) || pair.value.tag || pair.value.anchor) {
            throw new Error(`Unsupported ${semanticKey} value syntax in ${relativePath}`)
          }
          const valueRange = pair.value.range
          if (valueRange && frontmatter.slice(valueRange[0], valueRange[1]).includes("\n")) {
            throw new Error(`Unsupported multiline ${semanticKey} value in ${relativePath}`)
          }
          fields.set(
            semanticKey,
            pair.value.value == null ? "" : String(pair.value.value).trim(),
          )
        }

        visit(pair.value, depth + 1)
      }
    } else if (isSeq(node)) {
      for (const item of node.items) visit(item, depth + 1)
    }
  }

  visit(document.contents, 0)
  return fields
}

function governanceFieldValue(relativePath, fields, key, { allowEmpty = false } = {}) {
  if (!fields.has(key)) return undefined
  const value = fields.get(key)
  if (!allowEmpty && !value) throw new Error(`Empty ${key} in ${relativePath}`)
  if (/[\u0000-\u001f\u007f\u2028\u2029]/u.test(value)) {
    throw new Error(`Decoded control characters are not allowed in ${key} in ${relativePath}`)
  }
  return value
}

function normalizedPublicSourceUrl(value) {
  try {
    const parsed = new URL(value)
    if (!PUBLIC_SOURCE_PROTOCOLS.has(parsed.protocol)) return undefined
    if (parsed.username || parsed.password) return undefined
    return parsed.href
  } catch {
    return undefined
  }
}

function sourcePathMatches(pathname, prefix) {
  if (prefix === "/") return true
  const normalizedPrefix = prefix.endsWith("/") ? prefix.slice(0, -1) : prefix
  return pathname === normalizedPrefix || pathname.startsWith(`${normalizedPrefix}/`)
}

function isPathUnderPrefix(relativePath, prefixes) {
  return prefixes.some((prefix) => relativePath === prefix || relativePath.startsWith(prefix))
}

function hasRootFrontmatterField(markdown, key) {
  return frontmatterValues(markdown, key).length === 1
}

function legacyReferenceStubReason(relativePath, metadata, locale = DEFAULT_LOCALE) {
  if (locale !== DEFAULT_LOCALE) return undefined
  if (!isPathUnderPrefix(relativePath, LEGACY_REFERENCE_PREFIXES)) return undefined
  if (LEGACY_REFERENCE_LOCAL_FILES.has(relativePath)) return undefined
  if (metadata?.status === "needs-review") {
    return "third-party-reference-needs-review"
  }
  // A metadata-only change to original/curated/mixed must never release a body
  // from a frozen legacy tree. A genuinely independent, validated rewrite
  // belongs outside this tree; a reviewed redistribution must satisfy the
  // third-party provenance and license contract below.
  return metadata?.origin !== "third-party" || metadata?.status !== "frozen-reference"
    ? "third-party-metadata-missing"
    : undefined
}

function publicSourceRegistration(relativePath, parsedUrl) {
  // Keep registry matching independent of any upstream/proxy decoding policy.
  // Encoded percent signs, dot segments, or path separators are non-canonical
  // for the registered routes and therefore fail closed.
  if (/%(?:25|2e|2f|5c)/i.test(parsedUrl.pathname)) return undefined
  return PUBLIC_THIRD_PARTY_SOURCE_REGISTRY.find((registration) =>
    registration.routes.some((route) =>
      parsedUrl.origin === route.origin &&
      (!route.localPath || route.localPath === relativePath) &&
      (route.pathExact
        ? parsedUrl.pathname === route.pathExact && !parsedUrl.search && !parsedUrl.hash
        : sourcePathMatches(parsedUrl.pathname, route.pathPrefix)),
    ),
  )
}

const CC_BY_PLACEHOLDER_VALUES = new Set([
  "0",
  "false",
  "n/a",
  "none",
  "null",
  "tbd",
  "unknown",
  "unspecified",
  "~",
])

function meaningfulCcByText(value) {
  const normalized = String(value ?? "").trim()
  return normalized.length >= 8 && !CC_BY_PLACEHOLDER_VALUES.has(normalized.toLowerCase())
}

function validCcByAttribution(value, sourceRegistration) {
  if (!meaningfulCcByText(value)) return false
  const normalized = String(value).toLowerCase()
  if (sourceRegistration?.requiredAttribution) {
    return normalized === sourceRegistration.requiredAttribution.toLowerCase()
  }
  const tokens = sourceRegistration?.attributionTokens ?? []
  return tokens.length === 0 || tokens.some((token) => normalized.includes(token))
}

function validCcByChangeNotice(value, sourceRegistration) {
  if (!meaningfulCcByText(value)) return false
  if (sourceRegistration?.requiredChangeNotice) {
    return String(value) === sourceRegistration.requiredChangeNotice
  }
  if (sourceRegistration?.requiredChangePattern) {
    return sourceRegistration.requiredChangePattern.test(String(value))
  }
  return /(翻译|译文|整理|改写|格式|排版|删节|增补|未作改动|translation|translated|adapt|format|local change|no change)/i
    .test(String(value))
}

function markdownSafeUrl(value) {
  return String(value).replace(/[()[\]<>\\]/g, (character) =>
    `%${character.codePointAt(0).toString(16).toUpperCase()}`,
  )
}

export function validateContentMetadata(relativePath, markdown) {
  const fields = parseGovernanceFields(relativePath, markdown)
  const origin = governanceFieldValue(relativePath, fields, "content_origin")
  const status = governanceFieldValue(relativePath, fields, "content_status")
  const referenceStatus = governanceFieldValue(relativePath, fields, "reference_layer_status")
  const license = governanceFieldValue(relativePath, fields, "license", { allowEmpty: true })
  const sourceUrl = governanceFieldValue(relativePath, fields, "source_url", { allowEmpty: true })
  const attribution = governanceFieldValue(relativePath, fields, "attribution", { allowEmpty: true })
  const localChanges = governanceFieldValue(relativePath, fields, "local_changes", { allowEmpty: true })
  let canonicalSourceUrl = sourceUrl
  let sourceRegistration

  if (origin && !CONTENT_ORIGINS.has(origin)) {
    throw new Error(
      `Invalid content_origin in ${relativePath}: ${origin}. ` +
      `Expected one of ${[...CONTENT_ORIGINS].join(", ")}`,
    )
  }
  if (status && !CONTENT_STATUSES.has(status)) {
    throw new Error(
      `Invalid content_status in ${relativePath}: ${status}. ` +
      `Expected one of ${[...CONTENT_STATUSES].join(", ")}`,
    )
  }
  if (referenceStatus && !CONTENT_STATUSES.has(referenceStatus)) {
    throw new Error(
      `Invalid reference_layer_status in ${relativePath}: ${referenceStatus}. ` +
      `Expected one of ${[...CONTENT_STATUSES].join(", ")}`,
    )
  }
  if (origin === "third-party") {
    if (!sourceUrl) {
      throw new Error(`Third-party page requires an absolute source_url in ${relativePath}`)
    }
    let parsedSourceUrl
    try {
      parsedSourceUrl = new URL(sourceUrl)
    } catch {
      throw new Error(`Third-party page requires a valid absolute source_url in ${relativePath}`)
    }
    if (!PUBLIC_SOURCE_PROTOCOLS.has(parsedSourceUrl.protocol)) {
      throw new Error(`Third-party source_url must use http or https in ${relativePath}`)
    }
    if (parsedSourceUrl.username || parsedSourceUrl.password) {
      throw new Error(`Third-party source_url must not contain credentials in ${relativePath}`)
    }
    canonicalSourceUrl = parsedSourceUrl.href
    sourceRegistration = publicSourceRegistration(relativePath, parsedSourceUrl)
  }

  const normalizedLicense = license?.toLowerCase()
  const licenseIsUnknown = !normalizedLicense || UNKNOWN_LICENSES.has(normalizedLicense)
  const licenseIsAllowlisted = Boolean(
    normalizedLicense && PUBLIC_THIRD_PARTY_LICENSES.has(normalizedLicense),
  )
  const sourceLicenseMatches = Boolean(
    sourceRegistration && normalizedLicense && sourceRegistration.licenses.has(normalizedLicense),
  )
  const requiresCcByAttribution = normalizedLicense === "cc-by-4.0"
  const ccByAttributionIsValid = validCcByAttribution(attribution, sourceRegistration)
  const ccByChangeNoticeIsValid = validCcByChangeNotice(localChanges, sourceRegistration)
  const metadata = {
    origin,
    status,
    referenceStatus,
    license,
    sourceUrl: canonicalSourceUrl,
    attribution,
    localChanges,
    requiresThirdPartyStub: origin === "third-party" && (
      !licenseIsAllowlisted ||
      !sourceRegistration ||
      !sourceLicenseMatches ||
      (requiresCcByAttribution && !ccByAttributionIsValid) ||
      (requiresCcByAttribution && !ccByChangeNoticeIsValid)
    ),
  }
  if (metadata.requiresThirdPartyStub) {
    metadata.thirdPartyStubReason = licenseIsUnknown
      ? "third-party-license-unknown"
      : !licenseIsAllowlisted
        ? "third-party-license-not-allowlisted"
        : !sourceRegistration
          ? "third-party-source-unregistered"
          : !sourceLicenseMatches
            ? "third-party-source-license-mismatch"
            : !ccByAttributionIsValid
              ? "third-party-attribution-missing"
              : "third-party-change-notice-missing"
  }
  return metadata
}

export function classifyPath(relativePath, size = 0, markdown, locale = DEFAULT_LOCALE) {
  getSiteLocale(locale)
  const normalized = relativePath.replaceAll("\\", "/")
  const isChineseSource = locale === DEFAULT_LOCALE
  const extension = path.posix.extname(normalized).toLowerCase()
  const metadata = extension === ".md" && typeof markdown === "string"
    ? validateContentMetadata(normalized, markdown)
    : undefined

  if (isChineseSource && normalized.startsWith("Agent Skills/examples/") &&
      !AGENT_SKILLS_PUBLIC_EXAMPLE_FILES.has(normalized)) {
    return { action: "exclude", reason: "agent-skills-example-not-audited" }
  }

  if (
    isChineseSource &&
    extension !== ".md" &&
    isPathUnderPrefix(normalized, LEGACY_REFERENCE_ASSET_EXCLUDE_PREFIXES) &&
    !LANGCHAIN_PUBLIC_REFERENCE_IMAGE_DIGESTS.has(normalized)
  ) {
    return { action: "exclude", reason: "third-party-metadata-missing" }
  }

  if (isChineseSource && normalized.startsWith("Python基础/") &&
      !isAllowedByPrefix(normalized, PYTHON_PUBLIC_FILES, PYTHON_PUBLIC_PREFIXES)) {
    return extension === ".md"
      ? { action: "stub", reason: "python-complete-replica" }
      : { action: "exclude", reason: "python-complete-replica" }
  }

  if (isChineseSource && normalized.startsWith("Agentic Design Patterns/") &&
      !isAllowedByPrefix(normalized, AGENTIC_PUBLIC_FILES, AGENTIC_PUBLIC_PREFIXES)) {
    return extension === ".md"
      ? { action: "stub", reason: "agentic-unlicensed-translation" }
      : { action: "exclude", reason: "agentic-unlicensed-translation" }
  }

  if (isChineseSource && normalized === "深度学习/00-manifest.json") {
    return { action: "exclude", reason: "local-absolute-path-manifest" }
  }

  const legacyStubReason = extension === ".md"
    ? legacyReferenceStubReason(normalized, metadata, locale)
    : undefined
  if (legacyStubReason) {
    return { action: "stub", reason: legacyStubReason }
  }

  if (extension === ".md" && metadata?.requiresThirdPartyStub) {
    return { action: "stub", reason: metadata.thirdPartyStubReason }
  }

  if (extension === ".md") return { action: "publish", reason: "markdown" }
  if (CODE_EXTENSIONS.has(extension)) {
    if (!/(?:^|\/)examples\//.test(normalized)) {
      return { action: "exclude", reason: "code-or-data-outside-examples" }
    }
    return size <= MAX_CODE_BYTES
      ? { action: "asset", reason: "code-or-data" }
      : { action: "exclude", reason: "code-or-data-too-large" }
  }
  if (IMAGE_EXTENSIONS.has(extension)) {
    if (!/(?:^|\/)(?:attachments|res)\//.test(normalized)) {
      return { action: "exclude", reason: "image-outside-public-asset-directory" }
    }
    return size <= MAX_IMAGE_BYTES
      ? { action: "asset", reason: "image" }
      : { action: "exclude", reason: "image-too-large" }
  }
  if (normalized.endsWith("/.env.example") || normalized.endsWith(".env.example")) {
    if (!/(?:^|\/)examples\//.test(normalized)) {
      return { action: "exclude", reason: "environment-template-outside-examples" }
    }
    return size <= 64_000
      ? { action: "asset", reason: "environment-template" }
      : { action: "exclude", reason: "environment-template-too-large" }
  }
  return { action: "exclude", reason: "extension-not-allowlisted" }
}

export function assertPortablePublishedMarkdown(markdownSources, locale = DEFAULT_LOCALE) {
  const offenders = []
  const supplementalTopLevel = new Set(getSiteLocale(locale).supplementalTopLevel)
  for (const { relativePath, markdown } of markdownSources) {
    const normalized = relativePath.replaceAll("\\", "/")
    const topLevel = normalized.split("/")[0]
    if (supplementalTopLevel.has(topLevel)) continue

    const classification = classifyPath(normalized, Buffer.byteLength(markdown, "utf8"), markdown, locale)
    if (classification.action !== "publish") continue
    if (WINDOWS_ABSOLUTE_PROJECT_ROOT_PATTERN.test(markdown)) {
      offenders.push(normalized)
    }
  }

  if (offenders.length > 0) {
    throw new Error(
      "Published course Markdown must use project-root-relative paths; " +
      `hard-coded local project root found in: ${offenders.join(", ")}`,
    )
  }
}

export function assertThirdPartyAssetBoundaries(markdownSources, publicAssets, locale = DEFAULT_LOCALE) {
  for (const { relativePath, markdown } of markdownSources) {
    const classification = classifyPath(relativePath, Buffer.byteLength(markdown, "utf8"), markdown, locale)
    if (!classification.reason.startsWith("third-party-")) continue

    const course = relativePath.split("/", 1)[0]
    const exposedAssets = publicAssets.filter((asset) => {
      if (!asset.startsWith(`${course}/`)) return false
      // These are independently maintained, offline examples rather than
      // attachments belonging to the frozen reference pages.  Keep them
      // publishable while the upstream prose remains a metadata-free stub.
      if (isPathUnderPrefix(asset, LEGACY_REFERENCE_ASSET_ALLOWED_PREFIXES) ||
          LEGACY_REFERENCE_ASSET_ALLOWED_FILES.has(asset) ||
          LANGCHAIN_PUBLIC_REFERENCE_IMAGE_DIGESTS.has(asset) ||
          AGENT_SKILLS_PUBLIC_EXAMPLE_FILES.has(asset)) {
        return false
      }
      return true
    })
    if (exposedAssets.length === 0) continue

    throw new Error(
      `Non-publishable third-party page has assets that would still be published: ${relativePath} -> ` +
      `${exposedAssets.slice(0, 5).join(", ")}. ` +
      "Move the reference into an isolated top-level course or add an explicit, verified publication policy.",
    )
  }
}

function splitFrontmatter(markdown) {
  const match = markdown.match(/^\uFEFF?---\r?\n([\s\S]*?)\r?\n---(?:\r?\n|$)/)
  if (!match) return { frontmatter: "", body: markdown, full: "" }
  return {
    frontmatter: match[1],
    body: markdown.slice(match[0].length),
    full: match[0],
  }
}

export function frontmatterValue(markdown, key) {
  const { frontmatter } = splitFrontmatter(markdown)
  if (!frontmatter) return undefined
  const keyPattern = frontmatterKeyPattern(key)
  const match = frontmatter.match(new RegExp(`^${keyPattern}[ \\t]*:[ \\t]*(.*?)[ \\t]*$`, "m"))
  if (!match) return undefined
  return simpleYamlScalar(match[1])
}

function normalizedTranslationKey(value) {
  const key = String(value ?? "").replaceAll("\\", "/").trim()
  if (!key || key.startsWith("/") || key.includes("\0") || key.split("/").some((part) =>
    !part || part === "." || part === "..")) {
    return undefined
  }
  return key
}

export function translationSourceHash(markdown) {
  // Translation metadata is checked in Windows and Linux worktrees. Normalize
  // line endings so a checkout conversion cannot make a current translation
  // look stale.
  const normalized = String(markdown).replace(/\r\n?/g, "\n")
  return createHash("sha256").update(Buffer.from(normalized, "utf8")).digest("hex")
}

const HAN_CHARACTER = /\p{Script=Han}/u
const UNFINISHED_TRANSLATION_MARKER = /(?:\btranslation[_ -]?(?:needed|todo|pending)\b|\b(?:todo|tbd)\b|待翻译)/i

function englishProseForValidation(markdown) {
  const { frontmatter, body } = splitFrontmatter(markdown)
  // Translation metadata deliberately records Chinese paths. It is provenance
  // and navigation state, not reader-visible English prose.
  const visibleFrontmatter = frontmatter.replace(
    /^(?:translation_key|translation_route|translation_default_route)\s*:[^\r\n]*(?:\r?\n|$)/gm,
    "",
  )
  const visibleBody = body
    // Code, fixture payloads, and shell paths may intentionally preserve a
    // Chinese literal that is part of the teaching example.
    .replace(/```[\s\S]*?```/g, "")
    .replace(/`[^`]*`/g, "")
    // Keep link labels and image alt text in the check while ignoring URLs.
    .replace(/(!?\[[^\]]*\])\([^\r\n)]*\)/g, "$1")
    .replace(/https?:\/\/[^\s)>]+/g, "")
  return `${visibleFrontmatter}\n${visibleBody}`
}

export function assertEnglishSourceLanguage(englishSources) {
  for (const english of englishSources) {
    if (HAN_CHARACTER.test(english.relativePath)) {
      throw new Error(`English translation path must use semantic English names: ${english.relativePath}`)
    }
    const prose = englishProseForValidation(english.markdown)
    if (UNFINISHED_TRANSLATION_MARKER.test(prose)) {
      throw new Error(`English translation contains an unfinished-work marker: ${english.relativePath}`)
    }
    if (HAN_CHARACTER.test(prose)) {
      throw new Error(
        `English translation contains unlocalized Chinese prose outside code or translation_key: ${english.relativePath}`,
      )
    }
  }
}

export function assertTranslationPairs(chineseSources, englishSources) {
  const chineseByPath = new Map(chineseSources.map((source) => [source.relativePath, source]))
  const englishToChinese = new Map()
  const chineseToEnglish = new Map()

  for (const english of englishSources) {
    const key = normalizedTranslationKey(frontmatterValue(english.markdown, "translation_key"))
    if (!key || !key.endsWith(".md")) {
      throw new Error(`English page requires a root-level translation_key ending in .md: ${english.relativePath}`)
    }
    const chinese = chineseByPath.get(key)
    if (!chinese) {
      throw new Error(`English translation_key does not match a Chinese source page: ${english.relativePath} -> ${key}`)
    }
    if (chineseToEnglish.has(key)) {
      throw new Error(
        `Chinese source has multiple English counterparts: ${key} -> ` +
        `${chineseToEnglish.get(key)} and ${english.relativePath}`,
      )
    }
    if (frontmatterValue(english.markdown, "lang") !== "en") {
      throw new Error(`English page requires lang: en: ${english.relativePath}`)
    }
    const expectedHash = translationSourceHash(chinese.markdown)
    const actualHash = String(frontmatterValue(english.markdown, "translation_source_hash") ?? "").trim()
    if (actualHash !== expectedHash) {
      throw new Error(
        `English translation is stale or missing translation_source_hash: ${english.relativePath} ` +
        `(expected ${expectedHash})`,
      )
    }
    englishToChinese.set(english.relativePath, key)
    chineseToEnglish.set(key, english.relativePath)
  }

  const missing = [...chineseByPath.keys()].filter((relativePath) => !chineseToEnglish.has(relativePath))
  if (missing.length > 0) {
    throw new Error(
      `Chinese pages without English counterparts (${missing.length}): ${missing.slice(0, 20).join(", ")}`,
    )
  }
  if (englishSources.length !== chineseSources.length) {
    throw new Error(
      `Translation pair count mismatch: ${chineseSources.length} Chinese pages, ${englishSources.length} English pages`,
    )
  }

  assertEnglishSourceLanguage(englishSources)

  return { chineseToEnglish, englishToChinese, pairCount: chineseSources.length }
}

function firstHeading(markdown) {
  const body = splitFrontmatter(markdown).body
  return body.match(/^#\s+(.+?)\s*$/m)?.[1]?.replace(/\s+#+\s*$/, "").trim()
}

function yamlString(value) {
  return JSON.stringify(String(value))
}

export function ensureTitleAndStripProgress(markdown, fallbackTitle, extraFields = {}) {
  const title = frontmatterValue(markdown, "title") || firstHeading(markdown) || fallbackTitle
  const fields = Object.entries({ title, ...extraFields })
    .filter(([, value]) => value !== undefined)
  const parts = splitFrontmatter(markdown)
  if (!parts.full) {
    const frontmatter = fields.map(([key, value]) => `${key}: ${yamlString(value)}`).join("\n")
    return `---\n${frontmatter}\n---\n\n${markdown.replace(/^\uFEFF/, "")}`
  }

  const document = parseDocument(parts.frontmatter, {
    uniqueKeys: true,
    merge: false,
    prettyErrors: false,
    logLevel: "silent",
  })
  const yamlIssue = document.errors[0] ?? document.warnings[0]
  if (yamlIssue) throw new Error(`Invalid YAML frontmatter while stripping progress: ${yamlIssue.code}`)
  if (!document.contents || !isMap(document.contents)) {
    throw new Error("YAML frontmatter must be a root mapping while stripping progress")
  }

  document.contents.items = document.contents.items.filter((pair) =>
    !isScalar(pair.key) || String(pair.key.value).toLowerCase() !== "ai_learning_completed",
  )
  // Keep the generated title first and explicitly quoted. Apart from preserving
  // the established staged frontmatter shape, this avoids YAML's plain-scalar
  // edge cases for titles that begin with punctuation or YAML keywords.
  const titleIndex = document.contents.items.findIndex((pair) =>
    isScalar(pair.key) && String(pair.key.value) === "title",
  )
  const titlePair = titleIndex === -1
    ? document.createPair("title", title)
    : document.contents.items.splice(titleIndex, 1)[0]
  const titleNode = document.createNode(title)
  if (isScalar(titleNode)) titleNode.type = "QUOTE_DOUBLE"
  titlePair.value = titleNode
  document.contents.items.unshift(titlePair)

  for (const [key, value] of fields) {
    if (key !== "title") document.set(key, value)
  }
  const frontmatter = document.toString().trimEnd()
  return `---\n${frontmatter}\n---\n${parts.body}`
}

function escapeMarkdownPlainText(value) {
  return String(value).replace(/[\\`*_[\]<>]/g, (character) => `\\${character}`)
}

export function injectThirdPartyAttribution(markdown, relativePath, locale = DEFAULT_LOCALE) {
  const metadata = validateContentMetadata(relativePath, markdown)
  if (metadata.origin !== "third-party" || metadata.license?.toLowerCase() !== "cc-by-4.0") {
    return markdown
  }
  if (metadata.requiresThirdPartyStub) {
    throw new Error(`Cannot inject attribution for a non-publishable third-party page: ${relativePath}`)
  }

  const marker = "<!-- aae-visible-third-party-attribution -->"
  if (markdown.includes(marker)) {
    throw new Error(`Duplicate generated third-party attribution marker in ${relativePath}`)
  }
  const safeSourceUrl = markdownSafeUrl(metadata.sourceUrl)
  const english = locale === "en"
  const notice = [
    marker,
    english ? "> [!quote] Third-party source, license, and local changes" : "> [!quote] 第三方来源、许可与本地改动",
    english ? `> Upstream attribution: ${escapeMarkdownPlainText(metadata.attribution)}` : `> 上游署名：${escapeMarkdownPlainText(metadata.attribution)}`,
    english ? `> Original page: [View the upstream source](<${safeSourceUrl}>)` : `> 原始页面：[查看上游来源](<${safeSourceUrl}>)`,
    "> License: [Creative Commons Attribution 4.0 International](https://creativecommons.org/licenses/by/4.0/)",
    english ? `> Local changes: ${escapeMarkdownPlainText(metadata.localChanges)}` : `> 本地改动：${escapeMarkdownPlainText(metadata.localChanges)}`,
  ].join("\n")

  const parts = splitFrontmatter(markdown)
  return `${parts.full}${notice}\n\n${parts.body}`
}

export function redactMachineSpecificPaths(markdown) {
  return redactVaultRoot(markdown, LOCAL_VAULT_ROOT)
}

export function redactVaultRoot(markdown, vaultRoot) {
  const escapePattern = (value) => value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")
  const configuredRoot = String(vaultRoot ?? "").trim()
  if (!configuredRoot) return markdown

  // A Windows path is not absolute according to path.resolve() on a Linux CI
  // runner. Detect both path dialects before falling back to a host-relative
  // path so exported content is redacted identically on every platform.
  const isPortableAbsolute = path.win32.isAbsolute(configuredRoot) || path.posix.isAbsolute(configuredRoot)
  const absoluteRoot = isPortableAbsolute ? configuredRoot : path.resolve(configuredRoot)
  const rootWithoutTrailingSeparators = absoluteRoot.replace(/[\\/]+$/, "")
  if (!rootWithoutTrailingSeparators || /^[A-Za-z]:$/.test(rootWithoutTrailingSeparators)) return markdown

  const variants = [
    [rootWithoutTrailingSeparators.replaceAll("/", "\\"), "X:\\path\\to\\your-vault"],
    [rootWithoutTrailingSeparators.replaceAll("\\", "/"), "X:/path/to/your-vault"],
  ]

  return variants.reduce((result, [candidate, replacement]) => {
    return result.replace(new RegExp(escapePattern(candidate), "gi"), replacement)
  }, markdown)
}

function transformOutsideInlineCode(line, transform) {
  let output = ""
  let cursor = 0
  let delimiter = 0
  const matches = [...line.matchAll(/`+/g)]
  for (const match of matches) {
    const index = match.index ?? 0
    const run = match[0].length
    const segment = line.slice(cursor, index)
    output += delimiter === 0 ? transform(segment) : segment
    output += match[0]
    if (delimiter === 0) delimiter = run
    else if (delimiter === run) delimiter = 0
    cursor = index + run
  }
  const tail = line.slice(cursor)
  return output + (delimiter === 0 ? transform(tail) : tail)
}

export function transformOutsideCode(markdown, transform) {
  const lines = markdown.split(/(?<=\n)/)
  let fence = null
  return lines
    .map((line) => {
      const marker = line.match(/^\s*(`{3,}|~{3,})/)
      if (marker) {
        const token = marker[1][0]
        if (fence === null) fence = token
        else if (fence === token) fence = null
        return line
      }
      return fence === null ? transformOutsideInlineCode(line, transform) : line
    })
    .join("")
}

function countUnescapedPipes(value) {
  let count = 0
  for (let index = 0; index < value.length; index += 1) {
    if (value[index] !== "|") continue
    let slashes = 0
    for (let cursor = index - 1; cursor >= 0 && value[cursor] === "\\"; cursor -= 1) slashes += 1
    if (slashes % 2 === 0) count += 1
  }
  return count
}

function escapeWikilinkPipes(wikilink) {
  return wikilink.replace(/\|/g, (match, offset, value) => {
    let slashes = 0
    for (let cursor = offset - 1; cursor >= 0 && value[cursor] === "\\"; cursor -= 1) slashes += 1
    return slashes % 2 === 0 ? "\\|" : match
  })
}

/**
 * Markdown tables treat the alias separator in `[[target|alias]]` as a cell
 * delimiter. Obsidian accepts `[[target\|alias]]`, while the escaped form is
 * also understood by the Quartz Obsidian parser. Source notes should already
 * use the escaped form; this keeps imported or older notes publishable.
 */
function wikilinkTargetExists(wikilink, relativePath, sourcePaths) {
  if (!(sourcePaths instanceof Set)) return false
  const raw = wikilink.replace(/^!?\[\[/, "").replace(/\]\]$/, "")
  const target = raw.split(/\\?\|/, 1)[0].split("#", 1)[0].replaceAll("\\", "/").trim()
  if (!target) return false
  const sourceDirectory = path.posix.dirname(relativePath || "")
  const vaultRelativeTarget = stripVaultPrefix(target)
  const candidates = vaultRelativeTarget !== undefined
    ? [vaultRelativeTarget]
    : [target, path.posix.normalize(path.posix.join(sourceDirectory, target))]
  return candidates.some((candidate) =>
    sourcePaths.has(candidate) || (!path.posix.extname(candidate) && sourcePaths.has(`${candidate}.md`)),
  )
}

export function normalizeTableWikilinks(markdown, relativePath = "", sourcePaths) {
  const lines = markdown.split(/(?<=\n)/)
  let fence = null
  return lines.map((line) => {
    const marker = line.match(/^\s*(`{3,}|~{3,})/)
    if (marker) {
      const token = marker[1][0]
      if (fence === null) fence = token
      else if (fence === token) fence = null
      return line
    }
    // The authored vault uses leading-pipe Markdown table rows. Requiring that
    // shape avoids mistaking prose such as `|a ∩ b|` for a table.
    if (fence !== null || !/^\s*\|/.test(line) || !line.includes("[[") || !line.includes("|")) return line

    const probe = line.replace(/(`+)?!?\[\[[^\]\r\n]+\]\]\1?/g, "WIKILINK")
    if (countUnescapedPipes(probe) < 2) return line

    // Some source notes wrapped a wikilink in code ticks to keep the table
    // intact. In the web staging layer it should be an actual link.
    const unwrapped = line.replace(
      /(`+)(!?\[\[[^\]\r\n]+\]\])\1/g,
      (full, _ticks, wikilink) => wikilinkTargetExists(wikilink, relativePath, sourcePaths) ? wikilink : full,
    )
    return unwrapped.replace(/!?\[\[[^\]\r\n]+\]\]/g, escapeWikilinkPipes)
  }).join("")
}

function decodedPath(value) {
  try {
    return decodeURIComponent(value)
  } catch {
    return value
  }
}

function encodedPath(value) {
  return value.split("/").map((segment) => encodeURIComponent(segment)).join("/")
}

export function normalizeRelativeMarkdownLinks(markdown, relativePath, sourcePaths) {
  const sourceDirectory = path.posix.dirname(relativePath)
  const normalizeTarget = (target) => {
    if (!target || target.startsWith("#") || target.startsWith("/") ||
        /^(?:https?:|mailto:|tel:|data:|blob:|javascript:|\/\/)/i.test(target)) return undefined
    const match = target.match(/^([^?#]*)([?#].*)?$/)
    const targetPath = decodedPath((match?.[1] ?? target).replaceAll("\\", "/"))
    const suffix = match?.[2] ?? ""
    const vaultRelativeTarget = stripVaultPrefix(targetPath)
    const resolved = vaultRelativeTarget !== undefined
      ? vaultRelativeTarget
      : path.posix.normalize(path.posix.join(sourceDirectory, targetPath)).replace(/^\.\//, "")
    const knownTarget = sourcePaths.has(resolved) ||
      (!path.posix.extname(resolved) && sourcePaths.has(`${resolved}.md`))
    if (!knownTarget || resolved.startsWith("../")) return undefined
    return `${encodedPath(resolved)}${suffix}`
  }

  return transformOutsideCode(markdown, (segment) => {
    const markdownLinks = segment.replace(
      /(!?\[[^\]\r\n]*\]\()(<[^>\r\n]+>|[^)\s\r\n]+)([^)\r\n]*\))/g,
      (full, opening, rawTarget, closing) => {
        const wrapped = rawTarget.startsWith("<") && rawTarget.endsWith(">")
        const target = wrapped ? rawTarget.slice(1, -1) : rawTarget
        const normalized = normalizeTarget(target)
        return normalized ? `${opening}${normalized}${closing}` : full
      },
    )
    return markdownLinks.replace(
      /\b(src|href)=(['"])([^'"]+)\2/gi,
      (full, attribute, quote, target) => {
        const normalized = normalizeTarget(target)
        return normalized ? `${attribute}=${quote}${normalized}${quote}` : full
      },
    )
  })
}

function sourceUrlFor(relativePath, markdown = "") {
  const explicit = frontmatterValue(markdown, "source_url") || frontmatterValue(markdown, "source")
  const normalizedExplicit = normalizedPublicSourceUrl(explicit)
  if (normalizedExplicit) return normalizedExplicit
  if (relativePath.startsWith("Python基础/")) {
    const upstream = relativePath.slice("Python基础/".length)
    const encoded = upstream.split("/").map(encodeURIComponent).join("/")
    return `https://github.com/jackfrued/Python-100-Days/blob/master/${encoded}`
  }
  if (relativePath.startsWith("Agentic Design Patterns/")) {
    return "https://github.com/xindoo/agentic-design-patterns/tree/effb52f1730913be650a04e5ffb251c093096894/chapters"
  }
  return undefined
}

function rewriteDeniedEmbeds(segment) {
  return segment.replace(/!\[\[([^\]]+)\]\]/g, (full, rawTarget) => {
    const target = String(rawTarget).split("|")[0].split("#")[0].replaceAll("\\", "/")
    const normalized = VAULT_PREFIXES.reduce(
      (value, prefix) => value.startsWith(prefix) ? value.slice(prefix.length) : value,
      target,
    )
    if (normalized.startsWith("Agentic Design Patterns/attachments/")) {
      return "[第三方附件未随公开站点再分发](https://github.com/xindoo/agentic-design-patterns)"
    }
    if (normalized.startsWith("Python基础/") &&
        !isAllowedByPrefix(normalized, PYTHON_PUBLIC_FILES, PYTHON_PUBLIC_PREFIXES)) {
      return "[原课程附件请前往上游仓库查看](https://github.com/jackfrued/Python-100-Days)"
    }
    return full
  })
}

export function transformVaultPaths(markdown) {
  return transformOutsideCode(markdown, (segment) =>
    rewriteDeniedEmbeds(segment)
      .replace(/\[\[Obsidian\/附件整理规则(?:#[^|\]]*)?(?:\|([^\]]+))?\]\]/g, (_full, alias) =>
        `${alias || "附件整理规则"}（仅在本机 Obsidian Vault 中提供）`,
      )
      .replace(new RegExp(VAULT_PREFIXES.map((prefix) =>
        prefix.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|"), "g"), ""),
  )
}

export function courseRecordsFromSources(markdownSources, locale = DEFAULT_LOCALE) {
  const definition = getSiteLocale(locale)
  const supplementalTopLevel = new Set(definition.supplementalTopLevel)
  const courseIndexPattern = new RegExp(`^[^/]+/${definition.courseIndexFilename.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}$`)
  const courses = markdownSources
    .filter(({ relativePath }) => {
      if (!courseIndexPattern.test(relativePath)) return false
      return !supplementalTopLevel.has(relativePath.split("/", 1)[0])
    })
    .map(({ relativePath, markdown }) => parseCourseIndex(relativePath, markdown))

  if (courses.length === 0) throw new Error("Expected at least one top-level course index")

  const seenOrders = new Map()
  const seenCatalogOrders = new Map()
  const seenIds = new Map()
  const seenTrackOrders = new Map()
  for (const course of courses) {
    if (!course.stage) {
      throw new Error(`Course index is missing a non-empty ai_learning_stage: ${course.name}/${definition.courseIndexFilename}`)
    }
    if (!Number.isFinite(course.order)) {
      throw new Error(`Course index has an invalid ai_learning_order: ${course.name}/${definition.courseIndexFilename}`)
    }
    if (seenOrders.has(course.order)) {
      throw new Error(
        `Course order must be unique: ${course.order} is used by ${seenOrders.get(course.order)} and ${course.name}`,
      )
    }
    seenOrders.set(course.order, course.name)

    if (seenCatalogOrders.has(course.catalogOrder)) {
      throw new Error(
        `Course catalog order must be unique: ${course.catalogOrder} is used by ` +
        `${seenCatalogOrders.get(course.catalogOrder)} and ${course.name}`,
      )
    }
    seenCatalogOrders.set(course.catalogOrder, course.name)

    if (course.schema === COURSE_SCHEMA_VERSION) {
      if (seenIds.has(course.id)) {
        throw new Error(`Course ID must be unique: ${course.id} is used by ${seenIds.get(course.id)} and ${course.name}`)
      }
      seenIds.set(course.id, course.name)
      for (const [role, track] of Object.entries(course.tracks)) {
        const key = `${role}:${track.order}`
        if (seenTrackOrders.has(key)) {
          throw new Error(
            `Course track order must be unique for ${role}: ${track.order} is used by ` +
            `${seenTrackOrders.get(key)} and ${course.name}`,
          )
        }
        seenTrackOrders.set(key, course.name)
      }
    }
  }

  const versionedCourses = courses.filter((course) => course.schema === COURSE_SCHEMA_VERSION)
  const versionedById = new Map(versionedCourses.map((course) => [course.id, course]))
  for (const course of versionedCourses) {
    for (const prerequisite of course.hardPrerequisites) {
      if (!versionedById.has(prerequisite)) {
        throw new Error(`Unknown hard prerequisite ${prerequisite} in ${course.name}/00-目录.md`)
      }
      const prerequisiteCourse = versionedById.get(prerequisite)
      for (const [role, track] of Object.entries(course.tracks)) {
        const prerequisiteTrack = prerequisiteCourse.tracks[role]
        if (!prerequisiteTrack) {
          throw new Error(
            `Hard prerequisite ${prerequisite} must appear in role ${role} before ${course.id}`,
          )
        }
        if (prerequisiteTrack.order >= track.order) {
          throw new Error(
            `Hard prerequisite ${prerequisite} must have an earlier ${role} track order than ${course.id}`,
          )
        }
        if (track.kind === "core" && prerequisiteTrack.kind !== "core") {
          throw new Error(
            `Core course ${course.id} requires ${prerequisite} to be core in role ${role}`,
          )
        }
      }
    }
  }

  const visiting = new Set()
  const visited = new Set()
  function visit(course) {
    if (visiting.has(course.id)) {
      throw new Error(`Course hard prerequisites contain a cycle at ${course.id}`)
    }
    if (visited.has(course.id)) return
    visiting.add(course.id)
    for (const prerequisite of course.hardPrerequisites) visit(versionedById.get(prerequisite))
    visiting.delete(course.id)
    visited.add(course.id)
  }
  for (const course of versionedCourses) visit(course)

  return courses.sort((left, right) => left.catalogOrder - right.catalogOrder)
}

function parseCourseIndex(relativePath, markdown) {
  const { frontmatter } = splitFrontmatter(markdown)
  if (!frontmatter) throw new Error(`Course index is missing YAML frontmatter: ${relativePath}`)
  const document = parseDocument(frontmatter, {
    uniqueKeys: true,
    merge: false,
    prettyErrors: false,
    logLevel: "silent",
  })
  const yamlIssue = document.errors[0] ?? document.warnings[0]
  if (yamlIssue) throw new Error(`Invalid YAML frontmatter in ${relativePath}: ${yamlIssue.code}`)
  if (!document.contents || !isMap(document.contents)) {
    throw new Error(`YAML frontmatter must be a root mapping in ${relativePath}`)
  }

  const fields = new Map()
  for (const pair of document.contents.items) {
    if (!isScalar(pair.key) || pair.key.tag || pair.key.anchor) {
      throw new Error(`Unsupported YAML key in course index: ${relativePath}`)
    }
    fields.set(String(pair.key.value), pair.value)
  }

  function scalar(key, expectedType) {
    const node = fields.get(key)
    if (!isScalar(node) || node.tag || node.anchor || typeof node.value !== expectedType) return undefined
    return node.value
  }

  const stage = scalar("ai_learning_stage", "string")?.trim()
  const order = scalar("ai_learning_order", "number")
  const schemaNodePresent = fields.has("ai_learning_schema")
  const schema = scalar("ai_learning_schema", "number")
  const v2Keys = [...fields.keys()].filter((key) =>
    key.startsWith("ai_learning_") &&
    !["ai_learning_stage", "ai_learning_order", "ai_learning_completed", "ai_learning_schema"].includes(key),
  )
  if (schemaNodePresent && schema === undefined) {
    throw new Error(`Course index has an invalid ai_learning_schema: ${relativePath}`)
  }
  if (schema === undefined && v2Keys.length > 0) {
    throw new Error(`Course v2 fields require ai_learning_schema: 2 in ${relativePath}`)
  }
  if (schema !== undefined && schema !== COURSE_SCHEMA_VERSION) {
    throw new Error(`Unsupported ai_learning_schema in ${relativePath}: ${schema}`)
  }
  if (schema === COURSE_SCHEMA_VERSION) {
    const allowedV2Fields = new Set([
      "ai_learning_id",
      "ai_learning_domain",
      "ai_learning_catalog_order",
      "ai_learning_hard_prerequisites",
    ])
    for (const key of v2Keys) {
      if (!allowedV2Fields.has(key) && !key.startsWith("ai_learning_track_")) {
        throw new Error(`Unknown course metadata field ${key} in ${relativePath}`)
      }
    }
  }

  const base = {
    name: relativePath.split("/")[0],
    title: scalar("title", "string")?.trim(),
    stage,
    order,
    schema: schema ?? 1,
    catalogOrder: Number.isFinite(order) ? order * 100 : Number.NaN,
  }
  if (schema === undefined) return base

  const id = scalar("ai_learning_id", "string")?.trim()
  const domain = scalar("ai_learning_domain", "string")?.trim()
  const catalogOrder = scalar("ai_learning_catalog_order", "number")
  if (!id || !/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(id)) {
    throw new Error(`Course index has an invalid ai_learning_id: ${relativePath}`)
  }
  if (!COURSE_DOMAINS.has(domain)) {
    throw new Error(`Course index has an invalid ai_learning_domain: ${relativePath}`)
  }
  if (!Number.isSafeInteger(catalogOrder) || catalogOrder <= 0) {
    throw new Error(`Course index has an invalid ai_learning_catalog_order: ${relativePath}`)
  }

  const prerequisiteNode = fields.get("ai_learning_hard_prerequisites")
  if (!isSeq(prerequisiteNode) || prerequisiteNode.tag || prerequisiteNode.anchor) {
    throw new Error(`Course index must declare ai_learning_hard_prerequisites as a list: ${relativePath}`)
  }
  const hardPrerequisites = prerequisiteNode.items.map((item) => {
    if (!isScalar(item) || item.tag || item.anchor || typeof item.value !== "string") {
      throw new Error(`Course hard prerequisites must be string IDs: ${relativePath}`)
    }
    return item.value.trim()
  })
  if (hardPrerequisites.some((item) => !/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(item))) {
    throw new Error(`Course hard prerequisites contain an invalid ID: ${relativePath}`)
  }
  if (new Set(hardPrerequisites).size !== hardPrerequisites.length) {
    throw new Error(`Course hard prerequisites contain duplicates: ${relativePath}`)
  }
  if (hardPrerequisites.includes(id)) {
    throw new Error(`Course hard prerequisites contain a self reference: ${relativePath}`)
  }

  const trackFields = new Map()
  for (const key of fields.keys()) {
    if (!key.startsWith("ai_learning_track_")) continue
    const match = key.match(/^ai_learning_track_([a-z0-9_]+)_(order|kind)$/)
    if (!match || !COURSE_TRACK_ROLES.has(match[1])) {
      throw new Error(`Unknown course track field ${key} in ${relativePath}`)
    }
    const [, role, field] = match
    const record = trackFields.get(role) ?? {}
    record[field] = fields.get(key)
    trackFields.set(role, record)
  }
  const tracks = {}
  for (const [role, record] of trackFields) {
    if (!record.order || !record.kind) {
      throw new Error(`Course track ${role} must declare order and kind together: ${relativePath}`)
    }
    const trackOrder = isScalar(record.order) && !record.order.tag && !record.order.anchor &&
      typeof record.order.value === "number" ? record.order.value : undefined
    const trackKind = isScalar(record.kind) && !record.kind.tag && !record.kind.anchor &&
      typeof record.kind.value === "string" ? record.kind.value.trim() : undefined
    if (!Number.isSafeInteger(trackOrder) || trackOrder <= 0) {
      throw new Error(`Course track ${role} has an invalid order: ${relativePath}`)
    }
    if (!COURSE_TRACK_KINDS.has(trackKind)) {
      throw new Error(`Course track ${role} has an invalid kind: ${relativePath}`)
    }
    tracks[role] = { order: trackOrder, kind: trackKind }
  }

  return {
    ...base,
    id,
    domain,
    catalogOrder,
    hardPrerequisites,
    tracks,
  }
}

export function assertCompleteV2Migration(courses) {
  const legacy = courses.filter((course) => course.schema !== COURSE_SCHEMA_VERSION)
  if (legacy.length > 0) {
    throw new Error(
      `All top-level courses must use ai_learning_schema: 2; legacy courses: ` +
      legacy.map((course) => course.name).join(", "),
    )
  }
}

export function buildRoadmapTable(courses, locale = DEFAULT_LOCALE) {
  const definition = getSiteLocale(locale)
  const copy = courseCopy(locale)
  const lines = locale === "en"
    ? ["| Knowledge domain | Learning focus |", "| --- | --- |"]
    : ["| 知识域 | 学习重点 |", "| --- | --- |"]
  for (const [domain, label] of copy.domains) {
    const links = courses
      .filter((course) => course.domain === domain)
      .sort((left, right) => left.catalogOrder - right.catalogOrder)
      // A wikilink alias must escape its separator inside a Markdown table;
      // otherwise the table parser treats it as another cell boundary.
      .map((course) => {
        const label = locale === "en" ? course.title || course.name : course.name
        return `[[${course.name}/${definition.courseIndexLink}\\|${label}]]`
      })
      .join(" · ")
    if (links) lines.push(`| ${label} | ${links} |`)
  }
  return lines.join("\n")
}

export function buildRoleTrackTables(courses, locale = DEFAULT_LOCALE) {
  const definition = getSiteLocale(locale)
  const copy = courseCopy(locale)
  const sections = []
  for (const [role, label] of copy.tracks) {
    const trackCourses = courses
      .filter((course) => course.tracks?.[role])
      .sort((left, right) => left.tracks[role].order - right.tracks[role].order)
    const counts = { core: 0, recommended: 0, optional: 0 }
    for (const course of trackCourses) counts[course.tracks[role].kind] += 1
    const lines = locale === "en"
      ? [
        `### ${label}`,
        "",
        `${trackCourses.length} courses: ${counts.core} core, ${counts.recommended} recommended, and ${counts.optional} optional.`,
        "",
        "| Order | Course | Placement |",
        "| ---: | --- | --- |",
      ]
      : [
        `### ${label}`,
        "",
        `共 ${trackCourses.length} 门：${counts.core} 门核心、${counts.recommended} 门推荐、${counts.optional} 门可选。`,
        "",
        "| 顺序 | 课程 | 定位 |",
        "| ---: | --- | --- |",
      ]
    trackCourses.forEach((course, index) => {
      const kind = copy.trackKinds.get(course.tracks[role].kind)
      const label = locale === "en" ? course.title || course.name : course.name
      lines.push(`| ${index + 1} | [[${course.name}/${definition.courseIndexLink}\\|${label}]] | ${kind} |`)
    })
    sections.push(lines.join("\n"))
  }
  return sections.join("\n\n")
}

function replaceRoadmapSnapshot(markdown, marker, content) {
  const start = `<!-- ${marker}:START -->`
  const end = `<!-- ${marker}:END -->`
  const pattern = new RegExp(
    `${start.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}[\\s\\S]*?` +
    `${end.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}`,
    "g",
  )
  const matches = [...markdown.matchAll(pattern)]
  if (matches.length !== 1) {
    throw new Error(`All of AI.md must contain exactly one ${marker} snapshot, found ${matches.length}`)
  }
  return markdown.replace(pattern, `${start}\n${content}\n${end}`)
}

export function replaceRoadmapCatalogForPublication(markdown, courses, locale = DEFAULT_LOCALE) {
  const catalogMarker = "<!-- AI_LEARNING_CATALOG:START -->"
  const catalogEndMarker = "<!-- AI_LEARNING_CATALOG:END -->"
  const hasCatalogSnapshot = markdown.includes(catalogMarker) || markdown.includes(catalogEndMarker)
  const pattern = /```dataviewjs[ \t]*\r?\n[ \t]*await\s+dv\.view\(\s*["']tools\/dataview\/ai-learning-roadmap["']\s*\)\s*;?[ \t]*\r?\n```/g

  if (hasCatalogSnapshot) {
    if (/```dataviewjs\b/.test(markdown)) {
      throw new Error(
        "All of AI.md cannot contain both an interactive Dataview catalog and a catalog snapshot",
      )
    }
    const catalogStartCount = (markdown.match(/<!-- AI_LEARNING_CATALOG:START -->/g) ?? []).length
    const catalogEndCount = (markdown.match(/<!-- AI_LEARNING_CATALOG:END -->/g) ?? []).length
    if (catalogStartCount !== 1 || catalogEndCount !== 1) {
      throw new Error(
        `All of AI.md must contain exactly one AI_LEARNING_CATALOG snapshot, found ${catalogStartCount} starts and ${catalogEndCount} ends`,
      )
    }
    const expected = replaceRoadmapSnapshot(
      markdown,
      "AI_LEARNING_CATALOG",
      buildRoadmapTable(courses, locale),
    )
    if (expected.replaceAll("\r\n", "\n") !== markdown.replaceAll("\r\n", "\n")) {
      throw new Error(
        "All of AI.md catalog snapshot is stale or differs from the generated v2 catalog",
      )
    }
    return markdown
  }

  const matches = [...markdown.matchAll(pattern)]
  if (matches.length !== 1) {
    throw new Error(
      `All of AI.md must contain exactly one interactive Dataview catalog, found ${matches.length}`,
    )
  }

  return markdown.replace(
    pattern,
    `${catalogMarker}\n${buildRoadmapTable(courses, locale)}\n${catalogEndMarker}`,
  )
}

export function replaceRoadmapRoleTrackSnapshot(markdown, courses, locale = DEFAULT_LOCALE) {
  return replaceRoadmapSnapshot(
    markdown,
    "AI_LEARNING_ROLE_TRACKS",
    buildRoleTrackTables(courses, locale),
  )
}

export function replaceRoadmapSnapshots(markdown, courses, locale = DEFAULT_LOCALE) {
  return replaceRoadmapRoleTrackSnapshot(
    replaceRoadmapCatalogForPublication(markdown, courses, locale),
    courses,
    locale,
  )
}

export function buildStub(relativePath, markdown, stubReason, locale = DEFAULT_LOCALE) {
  const definition = getSiteLocale(locale)
  const english = locale === "en"
  const fallbackTitle = path.posix.basename(relativePath, ".md")
  const rawTitle = frontmatterValue(markdown, "title") || firstHeading(markdown) || fallbackTitle
  const title = safeStubTitle(rawTitle, fallbackTitle)
  const sourceUrl = sourceUrlFor(relativePath, markdown)
  const safeSourceUrl = sourceUrl ? markdownSafeUrl(sourceUrl) : undefined
  const course = relativePath.split("/")[0]
  const chineseReasons = {
    "python-complete-replica": "原 Python-100-Days 课程未在固定来源中提供明确的再分发许可证。",
    "agentic-unlicensed-translation": "该固定 commit 的中文译文层未提供明确的再分发许可证。",
    "third-party-metadata-missing": "该上游参考页尚未完成逐页的来源、内容来源和再分发许可标记；公开层先保留安全的来源跳转页。",
    "third-party-reference-needs-review": "该冻结参考页已发现术语、事实、来源或示例质量问题，并明确标记为待复核；完成逐段审阅前不公开其完整正文。",
    "third-party-source-unregistered": "该上游来源尚未进入项目的公开来源与许可声明注册表。",
    "third-party-source-license-mismatch": "页面声明的许可证与该上游项目已核验的许可不一致。",
    "third-party-attribution-missing": "该 CC BY 4.0 页面尚未记录上游署名信息。",
    "third-party-change-notice-missing": "该 CC BY 4.0 页面尚未说明本地翻译、整理或格式变更。",
  }
  const englishReasons = {
    "python-complete-replica": "The fixed Python-100-Days source does not provide clear redistribution permission.",
    "agentic-unlicensed-translation": "The translated layer at this fixed commit does not provide clear redistribution permission.",
    "third-party-metadata-missing": "This upstream reference has not completed its page-level source, provenance, and redistribution-license record, so the public site keeps only a safe source link.",
    "third-party-reference-needs-review": "This frozen upstream reference has known terminology, factual, source, or example quality issues and remains unavailable until it is reviewed section by section.",
    "third-party-source-unregistered": "This upstream source is not yet registered in the project's verified public-source and license registry.",
    "third-party-source-license-mismatch": "The page's declared license does not match the verified license for its upstream project.",
    "third-party-attribution-missing": "This CC BY 4.0 page does not yet record the required upstream attribution.",
    "third-party-change-notice-missing": "This CC BY 4.0 page does not yet describe its local translation, editing, or formatting changes.",
  }
  const reason = (english ? englishReasons : chineseReasons)[stubReason] ??
    (english
      ? "This page is marked as third-party material without a clear, verifiable redistribution license."
      : "本页标记为第三方材料，但尚未提供明确、可核验的再分发许可证。")
  return `---
title: ${yamlString(title)}
tags:
  - third-party-reference
third_party_stub: true
---

# ${title}

> [!info] ${english ? "The third-party body is not reproduced here" : "本页未复制第三方原文"}
> ${reason} ${english ? "The public site keeps only a source link." : "公开网站仅保留来源跳转页；你仍可在本机 Obsidian 中阅读已有参考资料。"}

${safeSourceUrl
    ? english ? `[View this section at its upstream source](<${safeSourceUrl}>)` : `[前往上游来源查看本节](<${safeSourceUrl}>)`
    : english ? "See the upstream project for the original material." : "请从上游项目主页查看原始材料。"}

${english ? "Return to" : "返回"} [[${course}/${definition.courseIndexLink}|${course}${english ? " course overview" : " 学习入口"}]]。
`
}

function safeStubTitle(value, fallback) {
  const rawValue = String(value ?? "")
  const isStructurallyUnsafe = /[\u0000-\u001f\u007f\u2028\u2029]/u.test(rawValue) ||
    /!?\[[^\]]*\]\([^\r\n)]*\)|<[^\r\n>]*>|https?:\/\//i.test(rawValue)
  const sanitize = (candidate) => String(candidate ?? "")
    .replace(/!?\[([^\]]*)\]\([^\r\n)]*\)/g, "$1")
    .replace(/<[^\r\n>]*>/g, "")
    .replace(/https?:\/\/\S+/gi, "")
    .replace(/[\u0000-\u001f\u007f\u2028\u2029]/gu, " ")
    .replace(/[\\`*_[\]<>!#|]/g, "")
    .replace(/\s+/g, " ")
    .trim()
  if (isStructurallyUnsafe) return sanitize(fallback) || "第三方参考页"
  return sanitize(rawValue) || sanitize(fallback) || "第三方参考页"
}

function encodedMarkdownTarget(relativePath) {
  return relativePath.split("/").map((segment) => encodeURIComponent(segment)).join("/")
}

function buildResourceIndex(assets, locale = DEFAULT_LOCALE) {
  const english = locale === "en"
  const codeAssets = assets.filter((asset) => CODE_EXTENSIONS.has(path.posix.extname(asset).toLowerCase()))
  const byCourse = new Map()
  for (const asset of codeAssets) {
    const course = asset.split("/")[0]
    if (!byCourse.has(course)) byCourse.set(course, [])
    byCourse.get(course).push(asset)
  }
  const sections = [...byCourse.entries()]
    .sort(([left], [right]) => left.localeCompare(right, english ? "en" : "zh-CN"))
    .map(([course, files]) => {
      const links = files
        .sort((left, right) => left.localeCompare(right, english ? "en" : "zh-CN", { numeric: true }))
        .map((file) => `- [${file.slice(course.length + 1)}](./${encodedMarkdownTarget(file)})`)
        .join("\n")
      return `## ${course}\n\n${links}`
    })
    .join("\n\n")

  return english
    ? `---
title: Resource index
tags:
  - ai-agent-engineer
  - examples
---

# Resource index

These files are published as read-only resources rather than standalone documentation pages. A link opens the on-site preview and can be downloaded; no example may contain real keys or credentials.

${sections || "> [!info]\n> No code or data resources currently meet the public-release policy."}
`
    : `---
title: 示例资源索引
tags:
  - ai-agent-engineer
  - examples
---

# 示例资源索引

下列文件以只读资源发布，不生成独立文档页面。点击链接会打开站内预览，可继续下载原文件；所有示例都不得包含真实密钥或凭据。

${sections || "> [!info]\n> 当前没有符合公开规则的代码或数据资源。"}
`
}

function buildThirdPartyNotices(locale = DEFAULT_LOCALE) {
  if (locale === "en") {
    return `---
title: Third-party materials and license notices
tags:
  - legal
  - third-party
---

# Third-party materials and license notices

This page records third-party materials used or redistributed by the public site. Sources and licenses were checked on **2026-07-20**.

## Website runtime

- [Quartz 5](https://github.com/jackyzha0/quartz/releases/tag/v5.0.0): MIT License; this project pins release v5.0.0 at commit \`ab346fa66a895e12d63a308e70ce330ba795822a\`; [view the Quartz MIT text](_licenses/Quartz-MIT.txt).
- [Quartz Community plugins](https://github.com/quartz-community): the site pins 28 plugins to exact commits and retains the upstream MIT notice; [view the plugin MIT text](_licenses/Quartz-Community-MIT.txt).
- [GSAP 3.15.0](https://gsap.com/docs/v3/): used only for interface motion under the [GSAP Standard “No Charge” License](https://gsap.com/standard-license/).
- [Mermaid 11.16.0](https://github.com/mermaid-js/mermaid/releases/tag/mermaid%4011.16.0): MIT License; the build copies the lockfile-pinned dependency into same-origin static assets instead of loading a browser CDN; [view the Mermaid MIT text](_licenses/Mermaid-MIT.txt).

## Build and publishing tools

- [YAML 2.9.0](https://www.npmjs.com/package/yaml/v/2.9.0): ISC License; used only to parse and validate frontmatter during the build; [view the upstream license](https://github.com/eemeli/yaml/blob/v2.9.0/LICENSE).

## Public reference material

- [D2L Chinese edition](https://github.com/d2l-ai/d2l-zh): Apache License 2.0. The site retains page-level source and license information; [view Apache-2.0](_licenses/Apache-2.0.txt).
- [LangChain documentation](https://github.com/langchain-ai/docs): MIT License. Its license copy is also retained in the LangChain license page; [view the LangChain MIT text](_licenses/LangChain-MIT.txt).
- [Model Context Protocol archived documentation repository](https://github.com/modelcontextprotocol/docs): MIT License; [view the archived-repository MCP MIT text](_licenses/MCP-MIT.txt). New monorepo documentation after 2026-01-05 and pages spanning the license transition remain fail-closed unless independently verified.
- [Agent Skills documentation](https://github.com/agentskills/agentskills/tree/38a2ff82958afee88dadf4831509e6f7e9d8ef4e/docs): CC BY 4.0. Any individually approved reference page keeps project attribution, an original-page link, and a local-change notice; [view the upstream document license](_licenses/Agent-Skills-CC-BY-4.0.txt).

## Complete reference layers not reproduced here

- [Python-100-Days](https://github.com/jackfrued/Python-100-Days): the fixed source does not provide a clear LICENSE, so this site publishes only original Agent-engineering material and source-link stubs.
- [xindoo/agentic-design-patterns](https://github.com/xindoo/agentic-design-patterns): the fixed commit does not provide a clear LICENSE, so this site publishes only the original beginner route and source-link stubs.

Source-link stubs never reproduce excluded bodies or attachments. This notice is an engineering publication policy, not legal advice.
`
  }
  return `---
title: 第三方材料与许可声明
tags:
  - legal
  - third-party
---

# 第三方材料与许可声明

本页记录公开网站使用或再发布的第三方材料。获取与核对日期：**2026-07-20**。

## 网站运行时

- [Quartz 5](https://github.com/jackyzha0/quartz/releases/tag/v5.0.0)：MIT License；项目锁定正式版 v5.0.0 的 commit \`ab346fa66a895e12d63a308e70ce330ba795822a\`；[查看 Quartz MIT 全文](_licenses/Quartz-MIT.txt)。
- [Quartz Community 插件](https://github.com/quartz-community)：本站锁定 28 个插件的精确 commit，统一保留上游 MIT 声明；[查看插件 MIT 全文](_licenses/Quartz-Community-MIT.txt)。
- [GSAP 3.15.0](https://gsap.com/docs/v3/)：按 [GSAP Standard “No Charge” License](https://gsap.com/standard-license/) 使用，仅用于界面动效。
- [Mermaid 11.16.0](https://github.com/mermaid-js/mermaid/releases/tag/mermaid%4011.16.0)：MIT License；构建时从 lockfile 固定依赖复制到同源静态资源，不再在浏览器中加载第三方 CDN；[查看 Mermaid MIT 全文](_licenses/Mermaid-MIT.txt)。

## 构建与发布工具

- [YAML 2.9.0](https://www.npmjs.com/package/yaml/v/2.9.0)：ISC License；仅在构建期解析并校验 frontmatter，[查看上游许可](https://github.com/eemeli/yaml/blob/v2.9.0/LICENSE)。

## 公开参考材料

- [D2L 中文版](https://github.com/d2l-ai/d2l-zh)：Apache License 2.0。本站保留各页来源和许可说明；[查看 Apache-2.0 全文](_licenses/Apache-2.0.txt)。
- [LangChain 文档](https://github.com/langchain-ai/docs)：MIT License。许可副本同时保留在 [[LangChain/LICENSE-LangChain-docs|LangChain 许可页]]；[查看 LangChain MIT 全文](_licenses/LangChain-MIT.txt)。
- [Model Context Protocol 已归档旧文档仓库](https://github.com/modelcontextprotocol/docs)：MIT License；[查看该旧仓库的 MCP MIT 全文](_licenses/MCP-MIT.txt)。2026-01-05 后的新单仓库文档及跨许可迁移页面不由这份登记覆盖，继续逐页失败关闭。
- [Agent Skills 文档](https://github.com/agentskills/agentskills/tree/38a2ff82958afee88dadf4831509e6f7e9d8ef4e/docs)：CC BY 4.0。逐页放行的中文参考页必须保留 Agent Skills 项目署名、原始页面链接，并明确说明中文翻译、整理与格式变更；[查看上游文档许可全文](_licenses/Agent-Skills-CC-BY-4.0.txt)。仓库代码的 Apache-2.0 不能替代文档许可证；明确声明 CC0-1.0 的示例仍按各自声明处理。
- Requests Quickstart 等零散官方参考页按其页面来源和上游 Apache-2.0 许可说明使用。

## 未在本站复制的完整参考层

- [Python-100-Days](https://github.com/jackfrued/Python-100-Days)：固定来源未提供明确 LICENSE，本站仅发布原创 Agent 工程层和来源跳转页。
- [xindoo/agentic-design-patterns](https://github.com/xindoo/agentic-design-patterns)：所用固定 commit 未提供明确 LICENSE，本站仅发布原创初学者路线和来源跳转页。

来源跳转页不包含被排除文档的正文或附件。本声明不替代原作者的版权和许可文件，也不构成法律意见。
`
}

function buildHomepageFrontmatter(stats, locale = DEFAULT_LOCALE) {
  const english = locale === "en"
  return `---
title: AI Agent Engineer
description: ${english ? "An engineering learning roadmap for building, evaluating, and deploying AI agents." : "从零构建、评测与部署 AI Agent 的中文工程学习路线。"}
aliases:
  - ${english ? "AI Agent Engineer home" : "AI Agent Engineer 首页"}
site_page: home
site_source_document_count: ${stats.sourceMarkdown}
site_full_document_count: ${stats.fullMarkdown}
site_stub_count: ${stats.stubs}
site_asset_count: ${stats.assets}
---
`
}

async function writeText(contentRoot, relativePath, text, timestamps) {
  const destination = path.join(contentRoot, ...relativePath.split("/"))
  assertInside(contentRoot, destination, "generated content")
  await mkdir(path.dirname(destination), { recursive: true })
  await writeFile(destination, text, "utf8")
  if (timestamps) await utimes(destination, timestamps.atime, timestamps.mtime)
}

async function copyAsset(contentRoot, source, relativePath, timestamps) {
  const destination = path.join(contentRoot, ...relativePath.split("/"))
  assertInside(contentRoot, destination, "generated asset")
  await mkdir(path.dirname(destination), { recursive: true })
  await copyFile(source, destination)
  if (timestamps) await utimes(destination, timestamps.atime, timestamps.mtime)
}

export function assertVerifiedLangChainReferenceAsset(relativePath, bytes) {
  const expectedDigest = LANGCHAIN_PUBLIC_REFERENCE_IMAGE_DIGESTS.get(relativePath)
  if (!expectedDigest) return
  const actualDigest = createHash("sha256").update(bytes).digest("hex")
  if (actualDigest !== expectedDigest) {
    throw new Error(
      `Verified LangChain reference asset digest mismatch: ${relativePath}`,
    )
  }
}

async function collectLocaleSource(locale) {
  const definition = getSiteLocale(locale)
  const sourceRoot = sourceRootFor(WEBSITE_ROOT, locale)
  const sourceFiles = await walk(sourceRoot)
  const sourcePaths = new Set(sourceFiles.map((source) => toPosix(path.relative(sourceRoot, source))))
  const markdownSources = []
  for (const source of sourceFiles) {
    const relativePath = toPosix(path.relative(sourceRoot, source))
    if (relativePath.toLowerCase().endsWith(".md")) {
      markdownSources.push({ relativePath, markdown: await readFile(source, "utf8") })
    }
  }
  return {
    locale,
    definition,
    sourceRoot,
    sourceFiles,
    sourcePaths,
    markdownSources,
    markdownByPath: new Map(markdownSources.map((entry) => [entry.relativePath, entry.markdown])),
  }
}

function courseContract(course) {
  return JSON.stringify({
    schema: course.schema,
    id: course.id,
    order: course.order,
    domain: course.domain,
    catalogOrder: course.catalogOrder,
    hardPrerequisites: course.hardPrerequisites,
    tracks: course.tracks,
  })
}

export function assertCourseMetadataParity(chineseCourses, englishCourses) {
  const englishById = new Map(englishCourses.map((course) => [course.id, course]))
  const missing = chineseCourses.filter((course) => !englishById.has(course.id)).map((course) => course.id)
  const extra = englishCourses.filter((course) => !chineseCourses.some((item) => item.id === course.id)).map((course) => course.id)
  if (missing.length > 0 || extra.length > 0) {
    throw new Error(
      `Course ID mismatch between Chinese and English sources: missing ${missing.join(", ") || "none"}; ` +
      `extra ${extra.join(", ") || "none"}`,
    )
  }
  for (const chinese of chineseCourses) {
    const english = englishById.get(chinese.id)
    if (courseContract(chinese) !== courseContract(english)) {
      throw new Error(`Course metadata differs between languages for ${chinese.id}`)
    }
  }
}

function sourcePageKind(bundle, relativePath) {
  return relativePath === bundle.definition.roadmapFilename ? "roadmap" : undefined
}

function generatedPagePath(locale, kind) {
  const definition = getSiteLocale(locale)
  if (kind === "home") return "index.md"
  if (kind === "resources") return definition.resourceIndexFilename
  if (kind === "third-party-notices") return definition.thirdPartyNoticesFilename
  throw new Error(`Unknown generated page kind: ${kind}`)
}

function translationFields(locale, relativePath, pairs, pageKind) {
  const english = locale === "en"
  const chinesePath = english ? pairs.englishToChinese.get(relativePath) : relativePath
  const englishPath = english ? relativePath : pairs.chineseToEnglish.get(relativePath)
  if (!chinesePath || !englishPath) {
    throw new Error(`Missing translation pair while staging ${locale}: ${relativePath}`)
  }
  return {
    lang: english ? "en" : "zh-CN",
    translation_key: chinesePath,
    translation_route: pageRouteFor(english ? DEFAULT_LOCALE : "en", english ? chinesePath : englishPath),
    translation_default_route: pageRouteFor(DEFAULT_LOCALE, chinesePath),
    site_page: pageKind,
  }
}

async function stagedChineseSourceHash(relativePath) {
  const chineseRoot = contentRootFor(GENERATED_ROOT, DEFAULT_LOCALE)
  const chineseOutput = path.join(chineseRoot, ...relativePath.split("/"))
  return translationSourceHash(await readFile(chineseOutput, "utf8"))
}

async function stagedTranslationSourceHash(locale, relativePath, pairs) {
  if (locale !== "en") return undefined
  const chinesePath = pairs.englishToChinese.get(relativePath)
  if (!chinesePath) {
    throw new Error(`Missing Chinese translation pair while staging English page: ${relativePath}`)
  }
  // The public snapshot rewrites the Chinese frontmatter while stripping local
  // state. Its English counterpart must fingerprint that published Chinese
  // page, not the private source version that is no longer in this tree.
  return stagedChineseSourceHash(chinesePath)
}

function generatedTranslationFields(locale, kind) {
  const chinesePath = generatedPagePath(DEFAULT_LOCALE, kind)
  const englishPath = generatedPagePath("en", kind)
  return {
    lang: locale === "en" ? "en" : "zh-CN",
    translation_key: chinesePath,
    translation_route: pageRouteFor(locale === "en" ? DEFAULT_LOCALE : "en", locale === "en" ? chinesePath : englishPath),
    translation_default_route: pageRouteFor(DEFAULT_LOCALE, chinesePath),
    site_page: kind,
  }
}

function pageTranslationRecord(locale, relativePath, fields) {
  return {
    relativePath,
    route: pageRouteFor(locale, relativePath),
    alternateRoute: fields.translation_route,
    defaultRoute: fields.translation_default_route,
  }
}

function aliasesFromMarkdown(relativePath, markdown) {
  const { frontmatter } = splitFrontmatter(markdown)
  if (!frontmatter) return []
  const document = parseDocument(frontmatter, { uniqueKeys: true, merge: false, prettyErrors: false, logLevel: "silent" })
  const issue = document.errors[0] ?? document.warnings[0]
  if (issue || !document.contents || !isMap(document.contents)) return []
  const aliases = document.contents.items.find((pair) => isScalar(pair.key) && pair.key.value === "aliases")?.value
  if (!aliases) return []
  const values = isSeq(aliases) ? aliases.items : [aliases]
  return values.map((node) => {
    if (!isScalar(node) || typeof node.value !== "string" || !node.value.trim()) {
      throw new Error(`Aliases must contain non-empty strings in ${relativePath}`)
    }
    return node.value.trim()
  })
}

function normalizeLegacyRoute(route, source) {
  const normalized = String(route ?? "").replaceAll("\\", "/").replace(/^\/+|\/+$/g, "")
  if (!normalized || normalized.split("/").some((part) => !part || part === "." || part === "..")) {
    throw new Error(`Unsafe legacy route from ${source}: ${route}`)
  }
  return normalized
}

function legacyRoutesFor(relativePath, markdown, targetRoute) {
  const sourceRoute = slugifyPublishedPath(relativePath.replace(/\.md$/i, ""))
  const routes = sourceRoute === "index" ? [] : [normalizeLegacyRoute(sourceRoute, relativePath)]
  for (const alias of aliasesFromMarkdown(relativePath, markdown)) {
    const resolved = alias.startsWith(".")
      ? path.posix.normalize(path.posix.join(sourceRoute, "..", alias))
      : alias
    routes.push(normalizeLegacyRoute(resolved, `${relativePath} alias`))
  }
  return routes.map((route) => ({ route, targetRoute }))
}

function isCourseIndex(relativePath, locale) {
  const definition = getSiteLocale(locale)
  return new RegExp(`^[^/]+/${definition.courseIndexFilename.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}$`).test(relativePath)
}

function forceEnglishThirdPartyStub(relativePath, chineseSource) {
  if (!chineseSource || isCourseIndex(chineseSource.relativePath, DEFAULT_LOCALE)) return undefined
  const classification = classifyPath(
    chineseSource.relativePath,
    Buffer.byteLength(chineseSource.markdown, "utf8"),
    chineseSource.markdown,
    DEFAULT_LOCALE,
  )
  const metadata = validateContentMetadata(chineseSource.relativePath, chineseSource.markdown)
  return classification.action === "stub" || metadata.origin === "third-party"
    ? { action: "stub", reason: "third-party-source-language-stub" }
    : undefined
}

async function stageLocaleContent(bundle, pairs, courses, chineseBundle) {
  const { locale, definition, sourceRoot, sourceFiles, sourcePaths, markdownSources, markdownByPath } = bundle
  const contentRoot = contentRootFor(GENERATED_ROOT, locale)
  await mkdir(contentRoot, { recursive: true })

  assertPortablePublishedMarkdown(markdownSources, locale)
  assertCompleteV2Migration(courses)
  const courseNames = new Set(courses.map((course) => course.name))
  const supplementalTopLevel = new Set(definition.supplementalTopLevel)
  const unknownTopLevel = [...sourcePaths].filter((relativePath) => {
    if (relativePath === definition.roadmapFilename) return false
    const topLevel = relativePath.split("/")[0]
    return !courseNames.has(topLevel) && !supplementalTopLevel.has(topLevel)
  })
  if (unknownTopLevel.length > 0) {
    throw new Error(
      `Source files outside the ${locale} course or supplemental publishing scope: ` +
      unknownTopLevel.slice(0, 10).join(", "),
    )
  }

  const publicAssets = []
  for (const source of sourceFiles) {
    const relativePath = toPosix(path.relative(sourceRoot, source))
    if (markdownByPath.has(relativePath)) continue
    const fileStat = await stat(source)
    if (classifyPath(relativePath, fileStat.size, undefined, locale).action === "asset") {
      publicAssets.push(relativePath)
    }
  }
  if (locale === DEFAULT_LOCALE) assertThirdPartyAssetBoundaries(markdownSources, publicAssets, locale)

  const manifest = {
    locale,
    generatedAt: new Date().toISOString(),
    sourceRoot: toPosix(path.relative(WEBSITE_ROOT, sourceRoot)),
    publishedMarkdown: [],
    stubMarkdown: [],
    assets: [],
    excluded: [],
    courses,
    pageTranslations: [],
    legacyRoutes: [],
    sourceDigest: "",
  }
  const sourceHash = createHash("sha256")
  const legacyTargets = new Map()
  const recordLegacyRoutes = (relativePath, markdown, targetRoute) => {
    if (locale !== DEFAULT_LOCALE) return
    for (const entry of legacyRoutesFor(relativePath, markdown, targetRoute)) {
      const existing = legacyTargets.get(entry.route)
      if (existing && existing !== entry.targetRoute) {
        throw new Error(`Legacy route collision: ${entry.route} -> ${existing} and ${entry.targetRoute}`)
      }
      if (!existing) {
        legacyTargets.set(entry.route, entry.targetRoute)
        manifest.legacyRoutes.push(entry)
      }
    }
  }

  for (const source of sourceFiles) {
    const relativePath = toPosix(path.relative(sourceRoot, source))
    const fileStat = await stat(source)
    const sourceBytes = markdownByPath.has(relativePath)
      ? Buffer.from(markdownByPath.get(relativePath), "utf8")
      : await readFile(source)
    sourceHash.update(relativePath)
    sourceHash.update("\0")
    sourceHash.update(sourceBytes)
    sourceHash.update("\0")

    let classification = classifyPath(relativePath, fileStat.size, markdownByPath.get(relativePath), locale)
    if (locale === "en" && markdownByPath.has(relativePath)) {
      const chinesePath = pairs.englishToChinese.get(relativePath)
      const chineseSource = chineseBundle.markdownByPath.has(chinesePath)
        ? { relativePath: chinesePath, markdown: chineseBundle.markdownByPath.get(chinesePath) }
        : undefined
      classification = forceEnglishThirdPartyStub(relativePath, chineseSource) ?? classification
    }

    if (classification.action === "exclude") {
      manifest.excluded.push({ path: relativePath, reason: classification.reason, bytes: fileStat.size })
      continue
    }
    if (classification.action === "asset") {
      if (locale === DEFAULT_LOCALE) assertVerifiedLangChainReferenceAsset(relativePath, sourceBytes)
      await copyAsset(contentRoot, source, relativePath, fileStat)
      manifest.assets.push(relativePath)
      continue
    }

    const original = sourceBytes.toString("utf8")
    const fields = {
      ...translationFields(locale, relativePath, pairs, sourcePageKind(bundle, relativePath)),
      translation_source_hash: await stagedTranslationSourceHash(locale, relativePath, pairs),
    }
    const fallbackTitle = path.posix.basename(relativePath, ".md")
    if (classification.action === "stub") {
      if (isCourseIndex(relativePath, locale)) {
        throw new Error(`Top-level course index cannot be published as a metadata-free stub: ${relativePath}`)
      }
      const stub = ensureTitleAndStripProgress(
        buildStub(relativePath, original, classification.reason, locale),
        fallbackTitle,
        fields,
      )
      await writeText(contentRoot, relativePath, stub, fileStat)
      manifest.stubMarkdown.push(relativePath)
      manifest.pageTranslations.push(pageTranslationRecord(locale, relativePath, fields))
      recordLegacyRoutes(relativePath, original, pageRouteFor(locale, relativePath))
      continue
    }

    let transformed = original
    if (relativePath === definition.roadmapFilename) {
      const catalogForPublication = replaceRoadmapCatalogForPublication(original, courses, locale)
      transformed = replaceRoadmapRoleTrackSnapshot(catalogForPublication, courses, locale)
      if (transformed !== catalogForPublication) {
        throw new Error(`${definition.roadmapFilename} role-track snapshot is stale in ${locale}`)
      }
    }
    transformed = normalizeTableWikilinks(transformed, relativePath, sourcePaths)
    transformed = normalizeRelativeMarkdownLinks(transformed, relativePath, sourcePaths)
    transformed = transformVaultPaths(transformed)
    transformed = redactMachineSpecificPaths(transformed)
    transformed = ensureTitleAndStripProgress(transformed, fallbackTitle, fields)
    transformed = injectThirdPartyAttribution(transformed, relativePath, locale)
    await writeText(contentRoot, relativePath, transformed, fileStat)
    manifest.publishedMarkdown.push(relativePath)
    manifest.pageTranslations.push(pageTranslationRecord(locale, relativePath, fields))
    recordLegacyRoutes(relativePath, original, pageRouteFor(locale, relativePath))
  }

  const stats = {
    sourceMarkdown: markdownSources.length,
    fullMarkdown: manifest.publishedMarkdown.length,
    stubs: manifest.stubMarkdown.length,
    assets: manifest.assets.length,
  }
  const generatedPages = [
    ["home", generatedPagePath(locale, "home"), buildHomepageFrontmatter(stats, locale)],
    ["resources", generatedPagePath(locale, "resources"), buildResourceIndex(manifest.assets, locale)],
    ["third-party-notices", generatedPagePath(locale, "third-party-notices"), buildThirdPartyNotices(locale)],
  ]
  for (const [kind, relativePath, markdown] of generatedPages) {
    const fields = {
      ...generatedTranslationFields(locale, kind),
      translation_source_hash: locale === "en"
        ? await stagedChineseSourceHash(generatedPagePath(DEFAULT_LOCALE, kind))
        : undefined,
    }
    await writeText(
      contentRoot,
      relativePath,
      ensureTitleAndStripProgress(markdown, path.posix.basename(relativePath, ".md"), fields),
    )
    manifest.pageTranslations.push(pageTranslationRecord(locale, relativePath, fields))
    recordLegacyRoutes(relativePath, markdown, pageRouteFor(locale, relativePath))
  }

  const legalRoot = path.join(WEBSITE_ROOT, "legal")
  for (const filename of LEGAL_LICENSE_FILES) {
    const source = path.join(legalRoot, filename)
    const destination = path.join(contentRoot, "_licenses", filename)
    assertInside(contentRoot, destination, "license destination")
    assertLegalLicenseDigest(filename, await readFile(source))
    await mkdir(path.dirname(destination), { recursive: true })
    await copyFile(source, destination)
  }

  manifest.generatedPages = generatedPages.map(([, relativePath]) => relativePath)
  manifest.sourceDigest = sourceHash.digest("hex")
  manifest.summary = {
    ...stats,
    legacyCourseMetadata: courses.filter((course) => course.schema === 1).length,
    v2CourseMetadata: courses.filter((course) => course.schema === COURSE_SCHEMA_VERSION).length,
    generatedPages: manifest.generatedPages.length,
    excludedFiles: manifest.excluded.length,
    stagedMarkdown: stats.fullMarkdown + stats.stubs + manifest.generatedPages.length,
  }
  const manifestPath = manifestPathFor(GENERATED_ROOT, locale)
  await mkdir(path.dirname(manifestPath), { recursive: true })
  await writeFile(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`, "utf8")

  const stagedTextFiles = await walk(contentRoot)
  const publicTextExtensions = new Set([".md", ".json", ".csv", ".ipynb", ".jsonl", ".py", ".sh", ".txt"])
  const progressPattern = /(?:["']ai_learning_completed["']|ai_learning_completed)\s*:/i
  for (const file of stagedTextFiles.filter((item) =>
    publicTextExtensions.has(path.extname(item).toLowerCase()) || item.toLowerCase().endsWith(".env.example"),
  )) {
    const text = await readFile(file, "utf8")
    if (progressPattern.test(text)) throw new Error(`Progress metadata leaked into ${locale} staging: ${file}`)
    const secret = HIGH_CONFIDENCE_SECRET_PATTERNS.find(([, pattern]) => pattern.test(text))
    if (secret) throw new Error(`Possible ${secret[0]} leaked into ${locale} staging: ${file}`)
  }

  return manifest
}

export async function prepareContent() {
  assertInside(WEBSITE_ROOT, GENERATED_ROOT, "generated root")
  await rm(GENERATED_ROOT, { recursive: true, force: true })
  await mkdir(GENERATED_ROOT, { recursive: true })

  const bundles = new Map(await Promise.all(SITE_LOCALE_IDS.map(async (locale) => [
    locale,
    await collectLocaleSource(locale),
  ])))
  const chineseBundle = bundles.get(DEFAULT_LOCALE)
  const englishBundle = bundles.get("en")
  const pairs = assertTranslationPairs(chineseBundle.markdownSources, englishBundle.markdownSources)
  const chineseCourses = courseRecordsFromSources(chineseBundle.markdownSources, DEFAULT_LOCALE)
  const englishCourses = courseRecordsFromSources(englishBundle.markdownSources, "en")
  assertCompleteV2Migration(chineseCourses)
  assertCompleteV2Migration(englishCourses)
  assertCourseMetadataParity(chineseCourses, englishCourses)

  const manifests = []
  for (const locale of SITE_LOCALE_IDS) {
    manifests.push(await stageLocaleContent(
      bundles.get(locale),
      pairs,
      locale === DEFAULT_LOCALE ? chineseCourses : englishCourses,
      chineseBundle,
    ))
  }
  const result = {
    pairCount: pairs.pairCount,
    locales: Object.fromEntries(manifests.map((manifest) => [manifest.locale, manifest.summary])),
  }
  await writeFile(
    path.join(GENERATED_ROOT, "translation-manifest.json"),
    `${JSON.stringify(result, null, 2)}\n`,
    "utf8",
  )
  console.log(JSON.stringify(result))
  return result
}

if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) {
  await prepareContent()
}
