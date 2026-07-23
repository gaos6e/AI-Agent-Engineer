import test from "node:test"
import assert from "node:assert/strict"
import { existsSync, readFileSync, readdirSync } from "node:fs"
import path from "node:path"
import { fileURLToPath } from "node:url"
import {
  assertPortablePublishedMarkdown,
  assertCourseMetadataParity,
  assertEnglishSourceLanguage,
  assertTranslationPairs,
  assertVerifiedLangChainReferenceAsset,
  assertLegalLicenseDigest,
  assertThirdPartyAssetBoundaries,
  assertCompleteV2Migration,
  buildRoadmapTable,
  buildRoleTrackTables,
  GENERATED_ROOT,
  buildStub,
  classifyPath,
  courseRecordsFromSources,
  ensureTitleAndStripProgress,
  frontmatterValue,
  injectThirdPartyAttribution,
  normalizeTableWikilinks,
  normalizeRelativeMarkdownLinks,
  redactMachineSpecificPaths,
  redactVaultRoot,
  replaceRoadmapCatalogForPublication,
  replaceRoadmapRoleTrackSnapshot,
  replaceRoadmapSnapshots,
  transformVaultPaths,
  prepareContent,
  translationSourceHash,
  validateContentMetadata,
} from "../scripts/prepare-content.mjs"
import {
  localMermaidCompiled,
  localMermaidSource,
  removeMermaidCdnPreconnect,
  secureMermaidCompiled,
  secureMermaidSource,
} from "../scripts/bootstrap-runtime.mjs"
import {
  countKatexErrorSpans,
  localTarget,
  markdownToHtmlPath,
  slugifyPublishedPath,
} from "../scripts/validate-site.mjs"

function markdownSourcesFrom(root) {
  const sources = []
  const visit = (directory) => {
    for (const entry of readdirSync(directory, { withFileTypes: true })) {
      const absolute = path.join(directory, entry.name)
      if (entry.isDirectory()) visit(absolute)
      else if (entry.isFile() && entry.name.endsWith(".md")) {
        sources.push({
          relativePath: path.relative(root, absolute).replaceAll(path.sep, "/"),
          markdown: readFileSync(absolute, "utf8"),
        })
      }
    }
  }
  if (existsSync(root)) visit(root)
  return sources
}

test("publication policy keeps original layers out and preserves authored layers", () => {
  assert.equal(classifyPath("Python基础/Day01-20/01.初识Python.md", 100).action, "stub")
  assert.equal(classifyPath("Python基础/res/logo.png", 100).action, "exclude")
  assert.equal(classifyPath("Python基础/Agent工程路线/01-基础.md", 100).action, "publish")
  assert.equal(classifyPath("Agentic Design Patterns/01-核心模式/01-提示链.md", 100).action, "stub")
  assert.equal(classifyPath("Agentic Design Patterns/00-初学者路线/01-选择模式.md", 100).action, "publish")
})

test("known upstream reference paths fail closed without per-page provenance metadata", () => {
  const mcpPage = "---\nsource_url: https://modelcontextprotocol.io/docs/learn/architecture.md\n---\n# MCP"
  const d2lPage = "---\nsource: https://zh-v2.d2l.ai/chapter_preface/\n---\n# D2L"
  const langchainPage = "---\nsource: https://docs.langchain.com/oss/python/learn\nlicense: MIT\n---\n# LangChain"

  assert.deepEqual(classifyPath("MCP/02-了解 MCP/01-架构.md", 100, mcpPage), {
    action: "stub",
    reason: "third-party-metadata-missing",
  })
  const curatedMcpNeedsReview = [
    "---",
    "content_origin: curated",
    "content_status: needs-review",
    "source_url: https://modelcontextprotocol.io/docs/learn/architecture.md",
    "---",
    "# MCP 本地摘要",
  ].join("\n")
  assert.deepEqual(
    classifyPath("MCP/02-了解 MCP/01-架构.md", 100, curatedMcpNeedsReview),
    { action: "stub", reason: "third-party-reference-needs-review" },
  )
  assert.deepEqual(
    classifyPath(
      "MCP/03-使用 MCP 开发/04-构建 MCP 服务器.md",
      100,
      "---\nsource_url: https://modelcontextprotocol.io/docs/develop/build-server.md\n---\n# Build server",
    ),
    { action: "stub", reason: "third-party-metadata-missing" },
  )
  assert.deepEqual(classifyPath("深度学习/01-前言/01-前言.md", 100, d2lPage), {
    action: "stub",
    reason: "third-party-metadata-missing",
  })
  assert.deepEqual(classifyPath("LangChain/01-Learn.md", 100, langchainPage), {
    action: "stub",
    reason: "third-party-metadata-missing",
  })
  const needsReviewPage = [
    "---",
    "content_origin: third-party",
    "content_status: needs-review",
    "source_url: https://docs.langchain.com/oss/python/langchain/knowledge-base",
    "license: MIT",
    "---",
    "# Semantic Search",
    "PRIVATE BROKEN BODY",
  ].join("\n")
  assert.deepEqual(
    classifyPath("LangChain/02-LangChain/01-Semantic Search.md", 100, needsReviewPage),
    { action: "stub", reason: "third-party-reference-needs-review" },
  )
  assert.equal(
    classifyPath(
      "深度学习/00-来源与目录.md",
      100,
      "---\ncontent_origin: curated\ncontent_status: validated\n---\n# 来源与目录",
    ).action,
    "publish",
  )
  for (const bypass of [
    "content_origin: original\ncontent_status: validated",
    "content_origin: curated\ncontent_status: frozen-reference",
    "content_origin: mixed\ncontent_status: frozen-reference",
    "content_origin: third-party\ncontent_status: validated\nlicense: CC-BY-4.0\nsource_url: https://agentskills.io/specification.md\nattribution: Agent Skills project\nlocal_changes: Chinese translation and formatting",
  ]) {
    const page = `---\n${bypass}\n---\n# frozen body`
    assert.deepEqual(
      classifyPath("Agent Skills/01-概览/02-Specification.md", 100, page),
      { action: "stub", reason: "third-party-metadata-missing" },
    )
  }
  assert.equal(classifyPath("LangChain/00-初学者路线/01-新课.md", 100, "# original").action, "publish")
  assert.deepEqual(classifyPath("LangChain/attachments/legacy.png", 100), {
    action: "exclude",
    reason: "third-party-metadata-missing",
  })

  const stub = buildStub("LangChain/01-Learn.md", langchainPage, "third-party-metadata-missing")
  assert.match(stub, /https:\/\/docs\.langchain\.com\/oss\/python\/learn/)
  assert.match(stub, /逐页的来源、内容来源和再分发许可标记/)

  const needsReviewStub = buildStub(
    "LangChain/02-LangChain/01-Semantic Search.md",
    needsReviewPage,
    "third-party-reference-needs-review",
  )
  assert.match(needsReviewStub, /术语、事实、来源或示例质量问题/)
  assert.doesNotMatch(needsReviewStub, /PRIVATE BROKEN BODY/)
})

test("Mermaid re-rendering keeps source text inert and uses strict security", () => {
  const source = secureMermaidSource([
    "const oldText = textMapping.get(node);",
    "node.innerHTML = oldText;",
    'securityLevel: "loose",',
  ].join("\n"))
  assert.match(source, /node\.textContent = oldText;/)
  assert.match(source, /securityLevel: "strict"/)
  assert.doesNotMatch(source, /node\.innerHTML = oldText;/)

  const compiled = secureMermaidCompiled([
    "// src/scripts/mermaid.inline.ts",
    'var x="i.innerHTML=c;securityLevel:"loose"";',
    "// src/styles/mermaid.inline.scss",
    "var css = true;",
  ].join("\n"))
  assert.match(compiled, /i\.textContent=c/)
  assert.match(compiled, /securityLevel:"strict"/)
  assert.doesNotMatch(compiled, /i\.innerHTML=c/)
})

test("Mermaid loads the pinned same-origin module instead of a CDN", () => {
  const source = localMermaidSource([
    "let mermaidImport = undefined;",
    "mermaidImport ||= await import(\n",
    "  // @ts-expect-error -- remote ESM import\n",
    '  "https://cdnjs.cloudflare.com/ajax/libs/mermaid/11.4.0/mermaid.esm.min.mjs"\n',
    ");",
  ].join("\n"))
  assert.match(source, /getMermaidAssetUrl\(\)/)
  assert.match(source, /static\/mermaid\.esm\.min\.mjs/)
  assert.match(source, /Unable to resolve the same-origin Mermaid asset/)
  assert.doesNotMatch(source, /cdnjs\.cloudflare\.com/)
  assert.equal(localMermaidSource(source), source)

  const compiled = localMermaidCompiled([
    "// src/scripts/mermaid.inline.ts",
    'var x="L;async function M(){L||(L=await import(\"https://cdnjs.cloudflare.com/ajax/libs/mermaid/11.4.0/mermaid.esm.min.mjs\"))}";',
    "// src/styles/mermaid.inline.scss",
    "var css = true;",
  ].join("\n"))
  assert.match(compiled, /function aaeMermaidAssetUrl\(\)\{/)
  assert.match(compiled, /await import\(aaeMermaidAssetUrl\(\)\)/)
  assert.match(compiled, /static\/mermaid\.esm\.min\.mjs/)
  assert.match(compiled, /Unable to resolve the same-origin Mermaid asset/)
  assert.doesNotMatch(compiled, /cdnjs\.cloudflare\.com/)
  assert.equal(localMermaidCompiled(compiled), compiled)
})

test("Quartz head drops the obsolete Mermaid cdnjs preconnect", () => {
  const source = [
    "<head>",
    '  <link rel="preconnect" href="https://fonts.googleapis.com" />',
    '  <link rel="preconnect" href="https://cdnjs.cloudflare.com" crossOrigin="anonymous" />',
    "</head>",
  ].join("\n")
  const patched = removeMermaidCdnPreconnect(source)

  assert.match(patched, /fonts\.googleapis\.com/)
  assert.doesNotMatch(patched, /cdnjs\.cloudflare\.com/)
  assert.equal(removeMermaidCdnPreconnect(patched), patched)
})

test("content provenance metadata uses controlled values but remains gradual", () => {
  const document = (origin, status) => [
    "---",
    `content_origin: ${origin}`,
    `content_status: ${status}`,
    ...(origin === "third-party" ? ["source_url: https://example.com/upstream"] : []),
    "---",
    "# 示例",
  ].join("\n")

  for (const origin of ["original", "curated", "third-party", "mixed"]) {
    for (const status of ["validated", "dynamic", "needs-review", "frozen-reference"]) {
      const metadata = validateContentMetadata("课程/示例.md", document(origin, status))
      assert.equal(metadata.origin, origin)
      assert.equal(metadata.status, status)
    }
  }

  assert.deepEqual(validateContentMetadata("课程/历史页.md", "# 尚未分类"), {
    origin: undefined,
    status: undefined,
    referenceStatus: undefined,
    license: undefined,
    sourceUrl: undefined,
    attribution: undefined,
    localChanges: undefined,
    requiresThirdPartyStub: false,
  })
  assert.throws(
    () => validateContentMetadata("课程/空来源.md", "---\ncontent_origin:\n---\n"),
    /Empty content_origin in 课程\/空来源\.md/,
  )
  assert.equal(
    validateContentMetadata(
      "课程/带注释.md",
      "---\ncontent_origin: original # 项目原创\ncontent_status: dynamic # 需定期复核\n---\n",
    ).origin,
    "original",
  )
  assert.equal(
    validateContentMetadata(
      "课程/引号键.md",
      "---\n'content_origin' : original\n\"content_status\" : validated\n---\n",
    ).status,
    "validated",
  )
  assert.equal(
    validateContentMetadata(
      "课程/许可证说明.md",
      "---\ntags:\n  - license\nlicense: MIT\n---\n",
    ).license,
    "MIT",
  )
  assert.throws(
    () => validateContentMetadata("课程/非法来源.md", "---\ncontent_origin: copied\n---\n"),
    /Invalid content_origin in 课程\/非法来源\.md/,
  )
  assert.throws(
    () => validateContentMetadata("课程/非法状态.md", "---\ncontent_status: stable\n---\n"),
    /Invalid content_status in 课程\/非法状态\.md/,
  )
  assert.throws(
    () => validateContentMetadata(
      "课程/重复状态.md",
      "---\ncontent_status: dynamic\ncontent_status: validated\n---\n",
    ),
    /Duplicate content_status in 课程\/重复状态\.md/,
  )
  for (const unsupported of [
    "---\n{content_origin: third-party, license: unknown}\n---\n",
    "---\n content_origin: third-party\n license: unknown\n---\n",
    "---\ndefaults: &defaults\n  content_origin: third-party\n<<: *defaults\nlicense: unknown\n---\n",
    "---\n? content_origin\n: third-party\nlicense: unknown\n---\n",
    "---\nitems:\n  - content_origin: third-party\nlicense: unknown\n---\n",
    "---\n{? content_origin: third-party, license: unknown}\n---\n",
    "---\n{ ? \"content_origin\" : third-party, license: unknown }\n---\n",
    "---\n!!str content_origin: third-party\nlicense: unknown\n---\n",
    "---\n&origin content_origin: third-party\nlicense: unknown\n---\n",
    "---\n\"content_\\u006Frigin\": third-party\nlicense: unknown\n---\n",
    "---\n? >-\n  content_origin\n: third-party\nlicense: unknown\n---\n",
    "---\n{!!str content_origin: third-party, license: unknown}\n---\n",
    "---\nitems:\n  - !!str content_origin: third-party\nlicense: unknown\n---\n",
  ]) {
    assert.throws(
      () => validateContentMetadata("课程/非规范YAML.md", unsupported),
      /Unsupported content_origin YAML syntax in 课程\/非规范YAML\.md/,
    )
  }
  assert.throws(
    () => validateContentMetadata(
      "课程/别名键.md",
      "---\nkey_name: &origin content_origin\n? *origin\n: third-party\n---\n",
    ),
    /Unsupported YAML mapping key syntax in 课程\/别名键\.md/,
  )
  assert.throws(
    () => validateContentMetadata(
      "课程/合并键.md",
      "---\nbase: &base {safe: value}\n<<: *base\n---\n",
    ),
    /YAML merge keys are not allowed in 课程\/合并键\.md/,
  )
  assert.throws(
    () => validateContentMetadata(
      "课程/标签值.md",
      "---\ncontent_origin: !!str original\n---\n",
    ),
    /Unsupported content_origin value syntax in 课程\/标签值\.md/,
  )
  for (const escapedControl of ["\\n", "\\r", "\\u000a"]) {
    assert.throws(
      () => validateContentMetadata(
        "课程/转义控制字符.md",
        [
          "---",
          "content_origin: third-party",
          "content_status: frozen-reference",
          "license: CC-BY-4.0",
          "source_url: https://agentskills.io/specification.md",
          "attribution: Agent Skills project contributors",
          `local_changes: "Chinese translation${escapedControl}# injected heading"`,
          "---",
        ].join("\n"),
      ),
      /Decoded control characters are not allowed in local_changes/,
    )
  }
})

test("third-party pages require a registered source and matching license", () => {
  const thirdParty = (licenseLine = "", sourceLine = "source_url: https://example.com/upstream") => [
    "---",
    "content_origin: third-party",
    licenseLine,
    sourceLine,
    "---",
    "# 第三方资料",
  ].filter(Boolean).join("\n")

  for (const markdown of [
    thirdParty(),
    thirdParty("license:"),
    thirdParty("license: unknown"),
    thirdParty('license: "UNKNOWN"'),
    thirdParty("license: unknown # 尚未确认"),
    thirdParty("license: null"),
  ]) {
    assert.deepEqual(classifyPath("RAG/参考/第三方资料.md", 100, markdown), {
      action: "stub",
      reason: "third-party-license-unknown",
    })
  }
  assert.equal(
    classifyPath(
      "RAG/参考/MIT资料.md",
      100,
      thirdParty(
        "license: MIT",
        "source_url: https://github.com/langchain-ai/docs/blob/main/LICENSE",
      ),
    ).action,
    "publish",
  )
  assert.deepEqual(
    classifyPath(
      "RAG/参考/MCP当前官网.md",
      100,
      thirdParty(
        "license: MIT",
        "source_url: https://modelcontextprotocol.io/docs/learn/architecture",
      ),
    ),
    { action: "stub", reason: "third-party-source-unregistered" },
  )
  assert.equal(
    classifyPath(
      "RAG/参考/MCP归档仓库.md",
      100,
      thirdParty(
        "license: MIT",
        "source_url: https://github.com/modelcontextprotocol/docs/blob/main/LICENSE",
      ),
    ).action,
    "publish",
  )
  assert.equal(
    classifyPath(
      "RAG/参考/MIT注释资料.md",
      100,
      thirdParty(
        'license: "MIT" # 已核验声明',
        "source_url: https://docs.langchain.com/oss/python/langchain/overview",
      ),
    ).action,
    "publish",
  )
  assert.equal(
    classifyPath(
      "RAG/参考/Apache资料.md",
      100,
      thirdParty(
        "license: Apache-2.0",
        "source_url: https://github.com/d2l-ai/d2l-zh/blob/master/LICENSE",
      ),
    ).action,
    "publish",
  )
  const ccByPage = (extraLines = []) => [
    "---",
    "content_origin: third-party",
    "content_status: frozen-reference",
    "license: CC-BY-4.0",
    "source_url: https://agentskills.io/specification.md",
    ...extraLines,
    "---",
    "# Agent Skills 规范译文",
  ].join("\n")
  assert.equal(
    classifyPath(
      "Agent Skills/01-概览/02-Specification.md",
      100,
      ccByPage([
        "attribution: Agent Skills project contributors",
        "local_changes: Chinese translation, link normalization, and Obsidian formatting",
      ]),
    ).action,
    "publish",
  )
  assert.deepEqual(
    classifyPath(
      "Agent Skills/01-概览/02-Specification.md",
      100,
      ccByPage(["local_changes: Chinese translation, link normalization, and Obsidian formatting"]),
    ),
    { action: "stub", reason: "third-party-attribution-missing" },
  )
  assert.deepEqual(
    classifyPath(
      "Agent Skills/01-概览/02-Specification.md",
      100,
      ccByPage(["attribution: Agent Skills project contributors"]),
    ),
    { action: "stub", reason: "third-party-change-notice-missing" },
  )
  for (const [attribution, localChanges, reason] of [
    ["false", "Chinese translation, link normalization, and Obsidian formatting", "third-party-attribution-missing"],
    ["0", "Chinese translation, link normalization, and Obsidian formatting", "third-party-attribution-missing"],
    ["unrelated project", "Chinese translation, link normalization, and Obsidian formatting", "third-party-attribution-missing"],
    ["Agent Skills project contributors", "false", "third-party-change-notice-missing"],
    ["Agent Skills project contributors", "No change from upstream", "third-party-change-notice-missing"],
    ["Agent Skills project contributors", "This page was not translated from upstream", "third-party-change-notice-missing"],
    ["Agent Skills project is not the creator", "Chinese translation, link normalization, and Obsidian formatting", "third-party-attribution-missing"],
  ]) {
    assert.deepEqual(
      classifyPath(
        "Agent Skills/01-概览/02-Specification.md",
        100,
        ccByPage([
          `attribution: ${attribution}`,
          `local_changes: ${localChanges}`,
        ]),
      ),
      { action: "stub", reason },
    )
  }
  assert.deepEqual(
    classifyPath(
      "Agent Skills/01-概览/02-Specification.md",
      100,
      ccByPage([
        "attribution: Agent Skills project contributors",
        "local_changes: Chinese translation, link normalization, and Obsidian formatting",
      ]).replace("/specification.md", "/private/source.py"),
    ),
    { action: "stub", reason: "third-party-source-unregistered" },
  )
  assert.deepEqual(
    classifyPath(
      "Agent Skills/01-概览/01-Agent Skills Overview.md",
      100,
      ccByPage([
        "attribution: Agent Skills project contributors",
        "local_changes: Chinese translation, link normalization, and Obsidian formatting",
      ]),
    ),
    { action: "stub", reason: "third-party-source-unregistered" },
  )
  assert.deepEqual(
    classifyPath(
      "Agent Skills/01-概览/02-Specification.md",
      100,
      ccByPage([]).replace("license: CC-BY-4.0", "license: Apache-2.0"),
    ),
    { action: "stub", reason: "third-party-source-license-mismatch" },
  )
  assert.deepEqual(
    classifyPath("RAG/参考/未登记MIT.md", 100, thirdParty("license: MIT")),
    { action: "stub", reason: "third-party-source-unregistered" },
  )
  for (const suffix of ["?next=https://evil.example", "#alternate"]) {
    assert.deepEqual(
      classifyPath(
        "Agent Skills/01-概览/02-Specification.md",
        100,
        ccByPage([
          "attribution: Agent Skills project contributors",
          "local_changes: Chinese translation, link normalization, and Obsidian formatting",
        ]).replace("/specification.md", `/specification.md${suffix}`),
      ),
      { action: "stub", reason: "third-party-source-unregistered" },
    )
  }
  assert.deepEqual(
    classifyPath(
      "RAG/参考/许可证错配.md",
      100,
      thirdParty(
        "license: MIT",
        "source_url: https://github.com/d2l-ai/d2l-zh/blob/master/LICENSE",
      ),
    ),
    { action: "stub", reason: "third-party-source-license-mismatch" },
  )
  assert.deepEqual(
    classifyPath(
      "RAG/参考/前缀伪造.md",
      100,
      thirdParty(
        "license: MIT",
        "source_url: https://github.com/langchain-ai/docs-evil/blob/main/LICENSE",
      ),
    ),
    { action: "stub", reason: "third-party-source-unregistered" },
  )
  assert.deepEqual(
    classifyPath(
      "RAG/参考/编码路径歧义.md",
      100,
      thirdParty(
        "license: MIT",
        "source_url: https://github.com/langchain-ai/docs/%252e%252e%252fother",
      ),
    ),
    { action: "stub", reason: "third-party-source-unregistered" },
  )
  assert.deepEqual(
    classifyPath("RAG/参考/专有资料.md", 100, thirdParty("license: All rights reserved")),
    { action: "stub", reason: "third-party-license-not-allowlisted" },
  )
  assert.throws(
    () => classifyPath("RAG/参考/无来源.md", 100, thirdParty("license: unknown", "")),
    /requires an absolute source_url in RAG\/参考\/无来源\.md/,
  )
  assert.throws(
    () => classifyPath(
      "RAG/参考/危险来源.md",
      100,
      thirdParty("license: unknown", "source_url: javascript:alert(1)"),
    ),
    /source_url must use http or https in RAG\/参考\/危险来源\.md/,
  )
  assert.throws(
    () => classifyPath(
      "RAG/参考/凭据来源.md",
      100,
      thirdParty("license: unknown", "source_url: https://user:secret@example.com/upstream"),
    ),
    /source_url must not contain credentials in RAG\/参考\/凭据来源\.md/,
  )
  assert.deepEqual(
    classifyPath("RAG/参考/拼写错误.md", 100, thirdParty("license: Apach-2.0")),
    { action: "stub", reason: "third-party-license-not-allowlisted" },
  )
  assert.equal(
    classifyPath(
      "RAG/00-目录.md",
      100,
      "---\ncontent_origin: mixed\nreference_layer_license: unknown\n---\n",
    ).action,
    "publish",
  )

  assert.equal(
    classifyPath("Python基础/Day01-20/01.初识Python.md", 100, thirdParty()).reason,
    "python-complete-replica",
  )
  assert.equal(
    classifyPath("Agentic Design Patterns/01-核心模式/01-提示链.md", 100, thirdParty()).reason,
    "agentic-unlicensed-translation",
  )
})

test("generic third-party stubs fail closed when adjacent assets would remain public", () => {
  const unlicensed = {
    relativePath: "RAG/参考层/01-第三方资料.md",
    markdown: [
      "---",
      "content_origin: third-party",
      "license: unknown",
      "source_url: https://example.com/upstream",
      "---",
      "# 资料",
    ].join("\n"),
  }
  assert.doesNotThrow(() => assertThirdPartyAssetBoundaries([unlicensed], []))
  assert.doesNotThrow(() => assertThirdPartyAssetBoundaries(
    [unlicensed],
    ["API/examples/demo.py"],
  ))
  assert.throws(
    () => assertThirdPartyAssetBoundaries(
      [unlicensed],
      ["RAG/attachments/chart.png", "RAG/原创项目/examples/demo.py"],
    ),
    /01-第三方资料\.md -> RAG\/attachments\/chart\.png/,
  )
  const unregistered = {
    relativePath: "RAG/参考层/02-伪造许可.md",
    markdown: [
      "---",
      "content_origin: third-party",
      "license: MIT",
      "source_url: https://example.com/unregistered",
      "---",
      "# 资料",
    ].join("\n"),
  }
  assert.throws(
    () => assertThirdPartyAssetBoundaries(
      [unregistered],
      ["RAG/examples/demo.py"],
    ),
    /02-伪造许可\.md -> RAG\/examples\/demo\.py/,
  )
})

test("frozen Agent Skills pages exempt only the audited local example assets", () => {
  const frozenPage = [{
    relativePath: "Agent Skills/01-概览/02-Specification.md",
    markdown: "---\nsource_url: https://agentskills.io/specification.md\n---\n# Specification",
  }]

  assert.doesNotThrow(() => assertThirdPartyAssetBoundaries(frozenPage, [
    "Agent Skills/examples/validate_skill.py",
    "Agent Skills/examples/text-statistics/scripts/text_stats.py",
  ]))
  assert.doesNotThrow(() => assertThirdPartyAssetBoundaries([{
    relativePath: "Agent Skills/01-概览/02-Specification.md",
    markdown: [
      "---",
      "content_origin: third-party",
      "content_status: frozen-reference",
      "license: CC-BY-4.0",
      "source_url: https://agentskills.io/specification.md",
      "local_changes: Chinese translation, link normalization, and Obsidian formatting",
      "---",
      "# Specification",
    ].join("\n"),
  }], ["Agent Skills/examples/validate_skill.py"]))
  assert.throws(
    () => assertThirdPartyAssetBoundaries(frozenPage, [
      "Agent Skills/examples/new-unreviewed.py",
    ]),
    /new-unreviewed\.py/,
  )
  assert.deepEqual(classifyPath("Agent Skills/examples/new-unreviewed.py", 100), {
    action: "exclude",
    reason: "agent-skills-example-not-audited",
  })
  assert.deepEqual(
    classifyPath("Agent Skills/examples/new-unreviewed.md", 100, "# unreviewed"),
    { action: "exclude", reason: "agent-skills-example-not-audited" },
  )
  assert.equal(
    classifyPath(
      "Agent Skills/examples/text-statistics/SKILL.md",
      100,
      "---\nname: text-statistics\n---\n# Skill",
    ).action,
    "publish",
  )
})

test("deep-learning releases only its exact original overlay and audited offline examples", () => {
  const overlay = [
    "---",
    "content_origin: original",
    "content_status: validated",
    "---",
    "# 深度学习：工程实践与现代化路线",
  ].join("\n")
  assert.deepEqual(
    classifyPath("深度学习/00-工程实践与现代化路线.md", 100, overlay),
    { action: "publish", reason: "markdown" },
  )

  const frozenPage = [{
    relativePath: "深度学习/01-前言/01-前言.md",
    markdown: "---\nsource: https://zh-v2.d2l.ai/chapter_preface/\n---\n# D2L",
  }]
  assert.doesNotThrow(() => assertThirdPartyAssetBoundaries(frozenPage, [
    "深度学习/examples/training_run_audit.py",
    "深度学习/examples/test_training_run_audit.py",
  ]))
  assert.throws(
    () => assertThirdPartyAssetBoundaries(frozenPage, [
      "深度学习/examples/unreviewed.py",
    ]),
    /unreviewed\.py/,
  )
})

test("generic third-party stubs keep only metadata and an upstream link", () => {
  const source = [
    "---",
    "title: 第三方资料",
    "content_origin: third-party",
    "license: unknown",
    "source_url: https://example.com/upstream",
    "---",
    "# 第三方资料",
    "PRIVATE THIRD-PARTY BODY MUST NOT LEAK",
  ].join("\n")
  const stub = buildStub("RAG/参考层/第三方资料.md", source, "third-party-license-unknown")
  assert.match(stub, /third_party_stub: true/)
  assert.match(stub, /\(<https:\/\/example\.com\/upstream>\)/)
  assert.doesNotMatch(stub, /PRIVATE THIRD-PARTY BODY MUST NOT LEAK/)

  const injectedSource = source.replace(
    "https://example.com/upstream",
    "https://example.com/a) [second](https://evil.example",
  )
  validateContentMetadata("RAG/参考层/注入.md", injectedSource)
  const safeStub = buildStub("RAG/参考层/注入.md", injectedSource, "third-party-license-unknown")
  assert.doesNotMatch(safeStub, /\[second\]\(/)
  assert.match(safeStub, /\]\(<https:\/\/example\.com\//)
})

test("third-party stub titles cannot inject headings, HTML, or remote images", () => {
  for (const title of [
    '"![tracker](https://evil.example/pixel)\\n# injected"',
    '"<img src=https://evil.example/pixel>\\r# injected"',
    '"[click](https://evil.example)\\u000a# injected"',
  ]) {
    const source = [
      "---",
      `title: ${title}`,
      "source_url: https://example.com/upstream",
      "---",
      "PRIVATE BODY",
    ].join("\n")
    const stub = buildStub("RAG/参考层/第三方资料.md", source, "third-party-metadata-missing")

    assert.doesNotMatch(stub, /evil\.example|<img|!\[|# injected/)
    assert.doesNotMatch(stub, /PRIVATE BODY/)
    assert.match(stub, /https:\/\/example\.com\/upstream/)
  }
})

test("published CC BY pages receive a visible, escaped attribution and change notice", () => {
  const source = [
    "---",
    "title: Agent Skills 规范译文",
    "content_origin: third-party",
    "content_status: frozen-reference",
    "license: CC-BY-4.0",
    "source_url: https://agentskills.io/specification.md",
    "attribution: Agent Skills project contributors",
    "local_changes: Chinese translation, link normalization, and Obsidian formatting",
    "---",
    "",
    "# Agent Skills 规范译文",
    "",
    "正文",
  ].join("\n")
  const published = injectThirdPartyAttribution(
    source,
    "Agent Skills/01-概览/02-Specification.md",
  )

  assert.match(published, /aae-visible-third-party-attribution/)
  assert.match(published, /> 上游署名：Agent Skills project contributors/)
  assert.match(published, /Creative Commons Attribution 4\.0 International/)
  assert.match(published, /本地改动：Chinese translation, link normalization, and Obsidian formatting/)
  assert.match(published, /第三方来源、许可与本地改动[\s\S]+# Agent Skills 规范译文[\s\S]+正文/)
  assert.throws(
    () => injectThirdPartyAttribution(
      published,
      "Agent Skills/01-概览/02-Specification.md",
    ),
    /Duplicate generated third-party attribution marker/,
  )
})

test("visible CC BY attribution cannot be injected inside an early fenced heading", () => {
  const source = [
    "---",
    "content_origin: third-party",
    "content_status: frozen-reference",
    "license: CC-BY-4.0",
    "source_url: https://agentskills.io/specification.md",
    "attribution: Agent Skills project contributors",
    "local_changes: Chinese translation, link normalization, and Obsidian formatting",
    "---",
    "",
    "```markdown",
    "# fake heading",
    "```",
    "",
    "# real heading",
  ].join("\n")
  const published = injectThirdPartyAttribution(
    source,
    "Agent Skills/01-概览/02-Specification.md",
  )

  assert.ok(
    published.indexOf("aae-visible-third-party-attribution") < published.indexOf("```markdown"),
  )
})

test("the pinned Agent Skills documentation license is hash-verified", () => {
  const licensePath = fileURLToPath(new URL("../legal/Agent-Skills-CC-BY-4.0.txt", import.meta.url))
  const contents = readFileSync(licensePath)

  assert.doesNotThrow(() => assertLegalLicenseDigest("Agent-Skills-CC-BY-4.0.txt", contents))
  assert.throws(
    () => assertLegalLicenseDigest(
      "Agent-Skills-CC-BY-4.0.txt",
      Buffer.concat([contents, Buffer.from("tampered")]),
    ),
    /Copied license digest mismatch/,
  )
})

test("only allowlisted code, data, and image assets enter staging", () => {
  assert.equal(classifyPath("RAG/examples/demo.py", 100).action, "asset")
  assert.equal(classifyPath("RAG/examples/input.json", 100).action, "asset")
  assert.equal(classifyPath("RAG/examples/data.csv", 100).action, "asset")
  assert.equal(classifyPath("RAG/examples/lab.ipynb", 100).action, "asset")
  assert.equal(classifyPath("RAG/examples/run.sh", 100).action, "asset")
  assert.equal(classifyPath("RAG/examples/events.jsonl", 100).action, "asset")
  assert.equal(classifyPath("RAG/examples/requirements.txt", 100).action, "asset")
  assert.equal(classifyPath("RAG/attachments/diagram.png", 100).action, "asset")
  assert.equal(classifyPath("RAG/credentials.json", 100).action, "exclude")
  assert.equal(classifyPath("RAG/diagram.png", 100).action, "exclude")
  assert.equal(classifyPath("RAG/model.pt", 100).action, "exclude")
  assert.equal(classifyPath("RAG/examples/huge.csv", 2_000_001).action, "exclude")
})

test("frozen LangChain reference images use a narrow verified allowlist", () => {
  const frozenPage = [{
    relativePath: "LangChain/01-Conceptual Overviews/02-Providers and Models.md",
    markdown: "---\nsource_url: https://docs.langchain.com/oss/python/concepts/providers-and-models\n---\n# Providers",
  }]
  for (const image of [
    "LangChain/attachments/images/rag_indexing.png",
    "LangChain/attachments/images/rag_retrieval_generation.png",
    "LangChain/attachments/images/langgraph-hybrid-rag-tutorial.png",
    "LangChain/attachments/oss/images/agentic-rag-output.png",
    "LangChain/attachments/oss/images/sql-agent-langgraph.png",
    "LangChain/attachments/images/data_analysis_slack_response.png",
  ]) {
    assert.equal(classifyPath(image, 100).action, "asset")
  }
  assert.doesNotThrow(() => assertThirdPartyAssetBoundaries(frozenPage, [
    "LangChain/attachments/images/rag_indexing.png",
  ]))
  assert.deepEqual(classifyPath("LangChain/attachments/images/unreviewed.png", 100), {
    action: "exclude",
    reason: "third-party-metadata-missing",
  })
  assert.throws(
    () => assertThirdPartyAssetBoundaries(frozenPage, [
      "LangChain/attachments/images/unreviewed.png",
    ]),
    /unreviewed\.png/,
  )
  const verifiedImagePath = fileURLToPath(
    new URL("../../docs-CN/LangChain/attachments/images/rag_indexing.png", import.meta.url),
  )
  assert.doesNotThrow(() => assertVerifiedLangChainReferenceAsset(
    "LangChain/attachments/images/rag_indexing.png",
    readFileSync(verifiedImagePath),
  ))
  assert.throws(
    () => assertVerifiedLangChainReferenceAsset(
      "LangChain/attachments/images/rag_indexing.png",
      Buffer.from("tampered"),
    ),
    /digest mismatch/,
  )
})

test("vault path transformation skips fenced and inline code", () => {
  const source = [
    "[[Knowledge/AI Agent Engineer/docs/RAG/00-目录|RAG]]",
    "`[[Knowledge/AI Agent Engineer/docs/API/00-目录]]`",
    "```markdown",
    "[[Knowledge/AI Agent Engineer/docs/Git/00-目录]]",
    "```",
  ].join("\n")
  const result = transformVaultPaths(source)
  assert.match(result, /^\[\[RAG\/00-目录\|RAG\]\]/)
  assert.match(result, /`\[\[Knowledge\/AI Agent Engineer\/docs\/API\/00-目录\]\]`/)
  assert.match(result, /```markdown\n\[\[Knowledge\/AI Agent Engineer\/docs\/Git\/00-目录\]\]/)
})

test("translation pairs require one current English counterpart for every Chinese page", () => {
  const chinese = [{ relativePath: "RAG/00-目录.md", markdown: "---\ntitle: RAG\n---\n# RAG" }]
  const english = [{
    relativePath: "retrieval/00-index.md",
    markdown: [
      "---",
      "lang: en",
      "translation_key: RAG/00-目录.md",
      `translation_source_hash: ${translationSourceHash(chinese[0].markdown)}`,
      "---",
      "# RAG",
    ].join("\n"),
  }]
  const pairs = assertTranslationPairs(chinese, english)
  assert.equal(pairs.pairCount, 1)
  assert.equal(pairs.chineseToEnglish.get("RAG/00-目录.md"), "retrieval/00-index.md")
  assert.throws(() => assertTranslationPairs(chinese, []), /without English counterparts/)
  assert.throws(
    () => assertTranslationPairs(chinese, [{ ...english[0], markdown: english[0].markdown.replace(/[a-f0-9]{64}/, "0".repeat(64)) }]),
    /stale or missing translation_source_hash/,
  )
})

test("checked-in English pages each map to a current Chinese source page", () => {
  const chineseRoot = fileURLToPath(new URL("../../docs-CN", import.meta.url))
  const englishRoot = fileURLToPath(new URL("../../docs-EN", import.meta.url))
  const chineseByPath = new Map(markdownSourcesFrom(chineseRoot).map((source) => [source.relativePath, source]))
  const english = markdownSourcesFrom(englishRoot)
  const chinese = english.map((source) => {
    const key = frontmatterValue(source.markdown, "translation_key")
    assert.ok(typeof key === "string" && chineseByPath.has(key), `Unknown translation_key in ${source.relativePath}`)
    return chineseByPath.get(key)
  })
  assertTranslationPairs(chinese, english)
})

test("staged English pages each fingerprint their staged Chinese counterparts", async () => {
  await prepareContent()
  const stagedChinese = markdownSourcesFrom(path.join(GENERATED_ROOT, "content", "zh-CN"))
  const stagedEnglish = markdownSourcesFrom(path.join(GENERATED_ROOT, "content", "en"))
  assertTranslationPairs(stagedChinese, stagedEnglish)
})

test("English source language guard permits code literals but rejects untranslated prose", () => {
  assert.doesNotThrow(() => assertEnglishSourceLanguage([{
    relativePath: "agents/example.md",
    markdown: [
      "---",
      "lang: en",
      "translation_key: Agent 核心/01-示例.md",
      "translation_route: zh-CN/Agent 核心/01-示例",
      "translation_default_route: zh-CN/Agent 核心/01-示例",
      "---",
      "# Example",
      "",
      "The fixture keeps its original user-visible payload.",
      "",
      "```json",
      '{ "message": "中文示例" }',
      "```",
    ].join("\n"),
  }]))
  assert.throws(
    () => assertEnglishSourceLanguage([{
      relativePath: "agents/example.md",
      markdown: "---\nlang: en\ntranslation_key: Agent 核心/01-示例.md\n---\n# Example\n\n这段正文尚未翻译。",
    }]),
    /unlocalized Chinese prose/,
  )
  assert.throws(
    () => assertEnglishSourceLanguage([{
      relativePath: "agents/中文示例.md",
      markdown: "---\nlang: en\ntranslation_key: Agent 核心/01-示例.md\n---\n# Example",
    }]),
    /semantic English names/,
  )
})

test("course metadata remains identical across language trees", () => {
  const chinese = [{
    id: "rag", domain: "retrieval-and-data", catalogOrder: 100, hardPrerequisites: ["json"],
    tracks: { rag: { order: 100, kind: "core" } },
  }]
  const english = structuredClone(chinese)
  assert.doesNotThrow(() => assertCourseMetadataParity(chinese, english))
  english[0].catalogOrder = 200
  assert.throws(() => assertCourseMetadataParity(chinese, english), /Course metadata differs/)
})

test("staging removes progress metadata and injects a title without touching body text", () => {
  const source = "---\ntags: [demo]\n\"AI_LEARNING_COMPLETED\": true\n---\n\n# 示例标题\n\n正文"
  const result = ensureTitleAndStripProgress(source, "fallback")
  assert.match(result, /^---\ntitle: "示例标题"/)
  assert.doesNotMatch(result, /ai_learning_completed/)
  assert.match(result, /# 示例标题\n\n正文$/)
})

test("staging removes a progress block value without leaking its sequence items", () => {
  const source = [
    "---",
    "tags:",
    "  - demo",
    "ai_learning_completed:",
    "  - chapter-1",
    "  - chapter-2",
    "aliases:",
    "  - 示例",
    "---",
    "",
    "# 示例标题",
  ].join("\n")
  const result = ensureTitleAndStripProgress(source, "fallback")

  assert.doesNotMatch(result, /ai_learning_completed|chapter-[12]/i)
  assert.match(result, /tags:\n\s+- demo/)
  assert.match(result, /aliases:\n\s+- 示例/)
})

test("relative Markdown and HTML assets become vault-root paths outside code", () => {
  const source = [
    "[demo](../examples/demo.py)",
    '<img src="../attachments/diagram.png" alt="diagram">',
    "`[keep](../examples/demo.py)`",
  ].join("\n")
  const paths = new Set([
    "RAG/examples/demo.py",
    "RAG/attachments/diagram.png",
  ])
  const result = normalizeRelativeMarkdownLinks(source, "RAG/课程/项目.md", paths)
  assert.match(result, /\(RAG\/examples\/demo\.py\)/)
  assert.match(result, /src="RAG\/attachments\/diagram\.png"/)
  assert.match(result, /`\[keep\]\(\.\.\/examples\/demo\.py\)`/)
})

test("course discovery accepts fractional orders and ignores nested or supplemental indexes", () => {
  const index = (stage, order) => `---\nai_learning_stage: ${stage}\nai_learning_order: ${order}\n---\n`
  const courses = courseRecordsFromSources([
    { relativePath: "课程甲/00-目录.md", markdown: index("1. 基础", 1) },
    { relativePath: "课程乙/00-目录.md", markdown: index("1. 基础", 1.5) },
    { relativePath: "课程乙/单元/00-目录.md", markdown: index("9. 不应发现", 99) },
    { relativePath: "维护记录/00-目录.md", markdown: "# 审计记录索引" },
    { relativePath: "All of AI.md", markdown: "# 路线" },
  ])

  assert.deepEqual(courses.map(({ name, stage, order }) => ({ name, stage, order })), [
    { name: "课程甲", stage: "1. 基础", order: 1 },
    { name: "课程乙", stage: "1. 基础", order: 1.5 },
  ])
})

test("course discovery rejects missing stages, invalid orders, and duplicate orders", () => {
  assert.throws(
    () => courseRecordsFromSources([
      { relativePath: "课程甲/00-目录.md", markdown: "---\nai_learning_order: 1\n---\n" },
    ]),
    /non-empty ai_learning_stage/,
  )
  assert.throws(
    () => courseRecordsFromSources([
      { relativePath: "课程甲/00-目录.md", markdown: "---\nai_learning_stage: 1. 基础\nai_learning_order: later\n---\n" },
    ]),
    /invalid ai_learning_order/,
  )
  assert.throws(
    () => courseRecordsFromSources([
      { relativePath: "课程甲/00-目录.md", markdown: '---\nai_learning_stage: 1. 基础\nai_learning_order: ""\n---\n' },
    ]),
    /invalid ai_learning_order/,
  )
  assert.throws(
    () => courseRecordsFromSources([
      { relativePath: "课程甲/00-目录.md", markdown: "---\nai_learning_stage: 1. 基础\nai_learning_order: 2\n---\n" },
      { relativePath: "课程乙/00-目录.md", markdown: "---\nai_learning_stage: 2. 进阶\nai_learning_order: 2.0\n---\n" },
    ]),
    /Course order must be unique/,
  )
})

test("course metadata v2 validates IDs, hard prerequisites, tracks, and catalog order", () => {
  const v2 = ({ id, order, catalogOrder, prerequisites = [], tracks = "" }) => [
    "---",
    "ai_learning_stage: 5. 单 Agent 与工具",
    `ai_learning_order: ${order}`,
    "ai_learning_schema: 2",
    `ai_learning_id: ${id}`,
    "ai_learning_domain: agent-runtime",
    `ai_learning_catalog_order: ${catalogOrder}`,
    prerequisites.length > 0 ? "ai_learning_hard_prerequisites:" : "ai_learning_hard_prerequisites: []",
    ...prerequisites.map((item) => `  - ${item}`),
    tracks,
    "---",
  ].filter(Boolean).join("\n")
  const courses = courseRecordsFromSources([
    {
      relativePath: "Agent 核心/00-目录.md",
      markdown: v2({
        id: "agent-core",
        order: 32,
        catalogOrder: 3200,
        prerequisites: ["tool-calling"],
        tracks: "ai_learning_track_agent_app_order: 600\nai_learning_track_agent_app_kind: core",
      }),
    },
    {
      relativePath: "Tool Calling/00-目录.md",
      markdown: v2({
        id: "tool-calling",
        order: 30,
        catalogOrder: 3000,
        tracks: "ai_learning_track_agent_app_order: 500\nai_learning_track_agent_app_kind: core",
      }),
    },
  ])

  assert.deepEqual(courses.map((course) => course.id), ["tool-calling", "agent-core"])
  assert.deepEqual(courses[1].hardPrerequisites, ["tool-calling"])
  assert.deepEqual(courses[1].tracks.agent_app, { order: 600, kind: "core" })
})

test("production course migration gate rejects any remaining legacy course", () => {
  assert.throws(
    () => assertCompleteV2Migration([{ name: "旧课程", schema: 1 }]),
    /All top-level courses must use ai_learning_schema: 2.*旧课程/,
  )
  assert.doesNotThrow(() => assertCompleteV2Migration([
    { name: "新课程", schema: 2 },
  ]))
})

test("course metadata v2 fails closed on partial tracks, unknown prerequisites, and cycles", () => {
  const index = (id, order, prerequisite, extra = "") => [
    "---",
    "ai_learning_stage: 5. 单 Agent 与工具",
    `ai_learning_order: ${order}`,
    "ai_learning_schema: 2",
    `ai_learning_id: ${id}`,
    "ai_learning_domain: agent-runtime",
    `ai_learning_catalog_order: ${order * 100}`,
    prerequisite ? "ai_learning_hard_prerequisites:" : "ai_learning_hard_prerequisites: []",
    ...(prerequisite ? [`  - ${prerequisite}`] : []),
    extra,
    "---",
  ].filter(Boolean).join("\n")

  assert.throws(
    () => courseRecordsFromSources([
      {
        relativePath: "课程甲/00-目录.md",
        markdown: index("course-a", 1, "", "ai_learning_track_agent_app_order: 100"),
      },
    ]),
    /must declare order and kind together/,
  )
  assert.throws(
    () => courseRecordsFromSources([
      { relativePath: "课程甲/00-目录.md", markdown: index("course-a", 1, "missing-course") },
    ]),
    /Unknown hard prerequisite/,
  )
  assert.throws(
    () => courseRecordsFromSources([
      { relativePath: "课程甲/00-目录.md", markdown: index("course-a", 1, "course-b") },
      { relativePath: "课程乙/00-目录.md", markdown: index("course-b", 2, "course-a") },
    ]),
    /contain a cycle/,
  )
  assert.throws(
    () => courseRecordsFromSources([
      { relativePath: "课程甲/00-目录.md", markdown: index("course-a", 1, "course-a") },
    ]),
    /self reference/,
  )
  const repeatedPrerequisite = index("course-a", 1, "course-b").replace(
    "  - course-b",
    "  - course-b\n  - course-b",
  )
  assert.throws(
    () => courseRecordsFromSources([
      { relativePath: "课程甲/00-目录.md", markdown: repeatedPrerequisite },
    ]),
    /contain duplicates/,
  )
})

test("course metadata v2 keeps hard prerequisites visible and earlier in every dependent role", () => {
  const index = ({ id, order, prerequisite = "", trackOrder = 0, kind = "core" }) => [
    "---",
    "ai_learning_stage: 5. 单 Agent 与工具",
    `ai_learning_order: ${order}`,
    "ai_learning_schema: 2",
    `ai_learning_id: ${id}`,
    "ai_learning_domain: agent-runtime",
    `ai_learning_catalog_order: ${order * 100}`,
    prerequisite ? "ai_learning_hard_prerequisites:" : "ai_learning_hard_prerequisites: []",
    ...(prerequisite ? [`  - ${prerequisite}`] : []),
    ...(trackOrder > 0 ? [
      `ai_learning_track_agent_app_order: ${trackOrder}`,
      `ai_learning_track_agent_app_kind: ${kind}`,
    ] : []),
    "---",
  ].join("\n")
  const source = (name, options) => ({
    relativePath: `${name}/00-目录.md`,
    markdown: index(options),
  })

  assert.throws(
    () => courseRecordsFromSources([
      source("课程甲", { id: "course-a", order: 1, prerequisite: "course-b", trackOrder: 200 }),
      source("课程乙", { id: "course-b", order: 2 }),
    ]),
    /must appear in role agent_app before course-a/,
  )
  assert.throws(
    () => courseRecordsFromSources([
      source("课程甲", { id: "course-a", order: 1, prerequisite: "course-b", trackOrder: 100 }),
      source("课程乙", { id: "course-b", order: 2, trackOrder: 200 }),
    ]),
    /must have an earlier agent_app track order than course-a/,
  )
  assert.throws(
    () => courseRecordsFromSources([
      source("课程甲", { id: "course-a", order: 1, prerequisite: "course-b", trackOrder: 200 }),
      source("课程乙", {
        id: "course-b",
        order: 2,
        trackOrder: 100,
        kind: "recommended",
      }),
    ]),
    /requires course-b to be core in role agent_app/,
  )
})

test("course metadata v2 rejects duplicate IDs, catalog positions, and per-role positions", () => {
  const index = ({ id, order, catalogOrder, trackOrder = 0, domain = "agent-runtime" }) => [
    "---",
    "ai_learning_stage: 5. 单 Agent 与工具",
    `ai_learning_order: ${order}`,
    "ai_learning_schema: 2",
    `ai_learning_id: ${id}`,
    `ai_learning_domain: ${domain}`,
    `ai_learning_catalog_order: ${catalogOrder}`,
    "ai_learning_hard_prerequisites: []",
    ...(trackOrder > 0 ? [
      `ai_learning_track_agent_app_order: ${trackOrder}`,
      "ai_learning_track_agent_app_kind: core",
    ] : []),
    "---",
  ].join("\n")
  const source = (name, options) => ({
    relativePath: `${name}/00-目录.md`,
    markdown: index(options),
  })

  assert.throws(
    () => courseRecordsFromSources([
      source("课程甲", { id: "same-id", order: 1, catalogOrder: 100 }),
      source("课程乙", { id: "same-id", order: 2, catalogOrder: 200 }),
    ]),
    /Course ID must be unique/,
  )
  assert.throws(
    () => courseRecordsFromSources([
      source("课程甲", { id: "course-a", order: 1, catalogOrder: 100 }),
      source("课程乙", { id: "course-b", order: 2, catalogOrder: 100 }),
    ]),
    /Course catalog order must be unique/,
  )
  assert.throws(
    () => courseRecordsFromSources([
      source("课程甲", { id: "course-a", order: 1, catalogOrder: 100, trackOrder: 500 }),
      source("课程乙", { id: "course-b", order: 2, catalogOrder: 200, trackOrder: 500 }),
    ]),
    /Course track order must be unique/,
  )
  assert.throws(
    () => courseRecordsFromSources([
      source("课程甲", { id: "course-a", order: 1, catalogOrder: 100, domain: "typo-domain" }),
    ]),
    /invalid ai_learning_domain/,
  )
})

test("course metadata v2 rejects malformed schema declarations and tagged track scalars", () => {
  assert.throws(
    () => courseRecordsFromSources([
      {
        relativePath: "课程甲/00-目录.md",
        markdown: "---\nai_learning_stage: 5. 单 Agent 与工具\nai_learning_order: 1\nai_learning_schema: two\n---\n",
      },
    ]),
    /invalid ai_learning_schema/,
  )

  const taggedTrack = [
    "---",
    "ai_learning_stage: 5. 单 Agent 与工具",
    "ai_learning_order: 1",
    "ai_learning_schema: 2",
    "ai_learning_id: course-a",
    "ai_learning_domain: agent-runtime",
    "ai_learning_catalog_order: 100",
    "ai_learning_hard_prerequisites: []",
    "ai_learning_track_agent_app_order: !!int 100",
    "ai_learning_track_agent_app_kind: core",
    "---",
  ].join("\n")
  assert.throws(
    () => courseRecordsFromSources([
      { relativePath: "课程甲/00-目录.md", markdown: taggedTrack },
    ]),
    /invalid order/,
  )

  const unknownField = taggedTrack.replace(
    "ai_learning_track_agent_app_order: !!int 100",
    "ai_learning_track_agent_app_order: 100\nai_learning_typo: accepted",
  )
  assert.throws(
    () => courseRecordsFromSources([
      { relativePath: "课程甲/00-目录.md", markdown: unknownField },
    ]),
    /Unknown course metadata field ai_learning_typo/,
  )

  const unsafeCatalogOrder = taggedTrack
    .replace("ai_learning_catalog_order: 100", "ai_learning_catalog_order: 9007199254740993")
    .replace("ai_learning_track_agent_app_order: !!int 100", "ai_learning_track_agent_app_order: 100")
  assert.throws(
    () => courseRecordsFromSources([
      { relativePath: "课程甲/00-目录.md", markdown: unsafeCatalogOrder },
    ]),
    /invalid ai_learning_catalog_order/,
  )

  const unsafeTrackOrder = taggedTrack.replace(
    "ai_learning_track_agent_app_order: !!int 100",
    "ai_learning_track_agent_app_order: 9007199254740993",
  )
  assert.throws(
    () => courseRecordsFromSources([
      { relativePath: "课程甲/00-目录.md", markdown: unsafeTrackOrder },
    ]),
    /invalid order/,
  )
})

test("v2 roadmap tables preserve domain catalog order and role track order", () => {
  const courses = [
    {
      name: "课程乙",
      schema: 2,
      domain: "foundations",
      catalogOrder: 200,
      tracks: { agent_app: { order: 20, kind: "recommended" } },
    },
    {
      name: "课程甲",
      schema: 2,
      domain: "foundations",
      catalogOrder: 100,
      tracks: { agent_app: { order: 10, kind: "core" } },
    },
    {
      name: "课程丙",
      schema: 2,
      domain: "agent-runtime",
      catalogOrder: 300,
      tracks: { rag: { order: 30, kind: "optional" } },
    },
  ]
  const table = buildRoadmapTable(courses)
  assert.equal((table.match(/\[\[/g) ?? []).length, courses.length)
  assert.ok(table.indexOf("课程甲/00-目录") < table.indexOf("课程乙/00-目录"))
  assert.match(table, /工程与数学基础/)
  assert.match(table, /Agent 运行时/)

  const tracks = buildRoleTrackTables(courses)
  assert.ok(tracks.indexOf("课程甲/00-目录") < tracks.indexOf("课程乙/00-目录"))
  assert.match(tracks, /Agent 应用开发/)
  assert.match(tracks, /1 门核心、1 门推荐、0 门可选/)
})

test("roadmap publication replaces one interactive catalog and one role-track region", () => {
  const source = [
    "## 课程地图",
    "```dataviewjs",
    'await dv.view("tools/dataview/ai-learning-roadmap");',
    "```",
    "## 角色路径",
    "<!-- AI_LEARNING_ROLE_TRACKS:START -->",
    "旧路径",
    "<!-- AI_LEARNING_ROLE_TRACKS:END -->",
  ].join("\n")
  const result = replaceRoadmapSnapshots(source, [{
    name: "课程甲",
    schema: 2,
    domain: "foundations",
    catalogOrder: 100,
    tracks: { agent_app: { order: 10, kind: "core" } },
  }])

  assert.match(result, /\| 工程与数学基础 \| \[\[课程甲\/00-目录\\\|课程甲\]\] \|/)
  assert.match(result, /### Agent 应用开发/)
  assert.doesNotMatch(result, /dataviewjs|旧路径/)
  assert.throws(() => replaceRoadmapSnapshots("# 没有课程地图", []), /exactly one interactive Dataview catalog/)
  const generatedCatalog = replaceRoadmapCatalogForPublication([
    "```dataviewjs",
    'await dv.view("tools/dataview/ai-learning-roadmap");',
    "```",
  ].join("\n"), [])
  assert.equal(replaceRoadmapCatalogForPublication(generatedCatalog, []), generatedCatalog)
  assert.throws(
    () => replaceRoadmapCatalogForPublication(
      `${generatedCatalog}\n<!-- AI_LEARNING_CATALOG:START -->`,
      [],
    ),
    /exactly one AI_LEARNING_CATALOG snapshot/,
  )
  assert.throws(
    () => replaceRoadmapCatalogForPublication([
      "<!-- AI_LEARNING_CATALOG:START -->",
      "过期内容",
      "<!-- AI_LEARNING_CATALOG:END -->",
    ].join("\n"), []),
    /catalog snapshot is stale or differs from the generated v2 catalog/,
  )
  assert.throws(
    () => replaceRoadmapCatalogForPublication([
      "```dataviewjs",
      'await dv.view("tools/dataview/ai-learning-roadmap");',
      "```",
      "<!-- AI_LEARNING_CATALOG:START -->",
      "<!-- AI_LEARNING_CATALOG:END -->",
    ].join("\n"), []),
    /cannot contain both an interactive Dataview catalog and a catalog snapshot/,
  )
  assert.match(
    replaceRoadmapCatalogForPublication([
      "```dataviewjs",
      "await dv.view('tools/dataview/ai-learning-roadmap')",
      "```",
    ].join("\n"), []),
    /<!-- AI_LEARNING_CATALOG:START -->/,
  )
})

test("table wikilink normalization does not alter prose that happens to contain pipes", () => {
  const source = "`ANN Recall = |approximate ∩ exact| / k`; see [[评测体系/00-目录|评测体系]]。"
  assert.equal(normalizeTableWikilinks(source), source)
})

test("course navigator and homepage consume v2 domains, catalog order, and role tracks", () => {
  const navigatorPath = fileURLToPath(new URL(
    "../overlay/quartz/components/CourseNavigator.tsx",
    import.meta.url,
  ))
  const homepagePath = fileURLToPath(new URL(
    "../overlay/quartz/components/Homepage.tsx",
    import.meta.url,
  ))
  const navigator = readFileSync(navigatorPath, "utf8")
  const homepage = readFileSync(homepagePath, "utf8")

  assert.match(navigator, /localeCopy/)
  assert.match(navigator, /uiLocale/)
  assert.match(navigator, /ai_learning_catalog_order/)
  assert.match(navigator, /ai_learning_track_/)
  assert.match(navigator, /ai_learning_id/)
  assert.doesNotMatch(navigator, /ai_learning_stage|ai_learning_order/)
  assert.match(homepage, /localeCopy/)
  assert.match(homepage, /uiLocale/)
  assert.match(homepage, /ai_learning_catalog_order/)
  assert.match(homepage, /ai_learning_track_/)
  assert.doesNotMatch(homepage, /ai_learning_stage|ai_learning_order/)
})

test("roadmap source keeps an interactive catalog or its generated static export", () => {
  const roadmapPath = fileURLToPath(new URL("../../docs-CN/All of AI.md", import.meta.url))
  const docsRoot = path.dirname(roadmapPath)
  const source = readFileSync(roadmapPath, "utf8")
  const headings = [...source.matchAll(/^## (.+)$/gm)].map((match) => match[1])
  const catalogStarts = source.match(/<!-- AI_LEARNING_CATALOG:START -->/g) ?? []
  const catalogEnds = source.match(/<!-- AI_LEARNING_CATALOG:END -->/g) ?? []
  const hasInteractiveCatalog = /```dataviewjs\s+await dv\.view\("tools\/dataview\/ai-learning-roadmap"\);\s+```/.test(source)

  assert.ok(headings.length > 0)

  assert.equal((source.match(/<!-- AI_LEARNING_ROLE_TRACKS:START -->/g) ?? []).length, 1)
  assert.match(source, /cssclasses:\n\s+- ai-learning-roadmap/)
  assert.equal(Number(hasInteractiveCatalog) + catalogStarts.length, 1)
  assert.equal(catalogStarts.length, catalogEnds.length)

  if (hasInteractiveCatalog) {
    assert.equal(catalogStarts.length, 0)
  } else {
    assert.equal(catalogStarts.length, 1)
    assert.doesNotMatch(source, /dataviewjs/)
  }

  const courseSources = readdirSync(docsRoot, { withFileTypes: true })
    .filter((entry) => entry.isDirectory())
    .map((entry) => entry.name)
    .filter((name) => existsSync(path.join(docsRoot, name, "00-目录.md")))
    .sort((left, right) => left.localeCompare(right, "zh-CN"))
    .map((course) => ({
      relativePath: `${course}/00-目录.md`,
      markdown: readFileSync(path.join(docsRoot, course, "00-目录.md"), "utf8"),
    }))
  const actualCourses = courseRecordsFromSources(courseSources)
  assert.ok(actualCourses.length > 0)
  assert.equal(actualCourses.length, courseSources.length)
  assert.doesNotThrow(() => assertCompleteV2Migration(actualCourses))
  assert.equal(replaceRoadmapRoleTrackSnapshot(source, actualCourses), source)

  if (hasInteractiveCatalog) {
    const publicationRoadmap = replaceRoadmapSnapshots(source, actualCourses)
    assert.match(publicationRoadmap, /<!-- AI_LEARNING_CATALOG:START -->/)
    assert.doesNotMatch(publicationRoadmap, /dataviewjs/)
  } else {
    const expectedCatalog = [
      "<!-- AI_LEARNING_CATALOG:START -->",
      buildRoadmapTable(actualCourses),
      "<!-- AI_LEARNING_CATALOG:END -->",
    ].join("\n")
    const publishedCatalog = source.match(
      /<!-- AI_LEARNING_CATALOG:START -->[\s\S]*?<!-- AI_LEARNING_CATALOG:END -->/,
    )

    assert.equal(publishedCatalog?.length, 1)
    assert.equal(publishedCatalog[0].replaceAll("\r\n", "\n"), expectedCatalog)
  }

  const versionedById = new Map(
    actualCourses
      .filter((course) => course.schema === 2)
      .map((course) => [course.id, course]),
  )
  const expectedV2Ids = [
    "ai-foundations",
    "python-foundations",
    "data-structures",
    "json",
    "api",
    "markdown",
    "git",
    "linux-cli",
    "regular-expressions",
    "probability-statistics",
    "linear-algebra",
    "calculus",
    "machine-learning",
    "deep-learning",
    "vector-fundamentals",
    "data-cleaning",
    "data-annotation",
    "data-visualization",
    "llm-model-selection",
    "prompt-engineering",
    "context-engineering",
    "llm-api",
    "document-parsing",
    "knowledge-base",
    "chunking",
    "embedding",
    "vector-database",
    "semantic-search",
    "reranking",
    "rag",
    "tool-calling",
    "mcp",
    "agent-core",
    "environment-agent",
    "agent-skills",
    "agentic-design-patterns",
    "workflow-automation",
    "langchain",
    "crewai",
    "mlops",
    "evaluation",
    "runtime-monitoring",
    "ai-safety",
    "ai-governance",
    "llmops",
    "benchmark-design",
    "synthetic-data",
    "privacy-enhancing-technologies",
    "multi-agent-collaboration",
    "multimodal-ai",
    "ocr",
    "speech-recognition",
    "speech-synthesis",
    "realtime-multimodal-interaction",
    "image-generation",
    "video-generation",
    "a2a-protocol",
  ]
  for (const id of expectedV2Ids) {
    assert.ok(versionedById.has(id), `expected authored v2 course ${id}`)
  }
  assert.equal(versionedById.size, expectedV2Ids.length)
  assert.deepEqual(versionedById.get("context-engineering").hardPrerequisites, ["prompt-engineering"])
  assert.deepEqual(versionedById.get("document-parsing").hardPrerequisites, ["data-cleaning", "json"])
  assert.deepEqual(versionedById.get("knowledge-base").hardPrerequisites, ["document-parsing"])
  for (const id of ["chunking", "embedding", "vector-database", "semantic-search", "reranking"]) {
    assert.deepEqual(versionedById.get(id).hardPrerequisites, [])
  }
  assert.deepEqual(versionedById.get("agent-core").hardPrerequisites, ["tool-calling"])
  assert.deepEqual(versionedById.get("llmops").hardPrerequisites, ["evaluation"])
  assert.deepEqual(versionedById.get("benchmark-design").hardPrerequisites, ["evaluation"])
  assert.deepEqual(versionedById.get("synthetic-data").hardPrerequisites, [
    "data-cleaning",
    "data-annotation",
    "evaluation",
  ])
  assert.deepEqual(versionedById.get("multi-agent-collaboration").hardPrerequisites, ["agent-core"])
  assert.deepEqual(versionedById.get("a2a-protocol").hardPrerequisites, [])
  assert.equal(versionedById.get("a2a-protocol").domain, "frontier-reference")
  assert.deepEqual(versionedById.get("a2a-protocol").tracks.agent_app, {
    order: 1450,
    kind: "optional",
  })
  assert.deepEqual(versionedById.get("a2a-protocol").tracks.agent_platform, {
    order: 1700,
    kind: "optional",
  })
  assert.deepEqual(versionedById.get("rag").tracks.rag, { order: 1200, kind: "core" })
  assert.deepEqual(versionedById.get("chunking").tracks.rag, { order: 700, kind: "core" })
  assert.deepEqual(versionedById.get("embedding").tracks.rag, { order: 800, kind: "core" })
  assert.deepEqual(versionedById.get("vector-database").tracks.rag, { order: 900, kind: "core" })
  assert.deepEqual(versionedById.get("semantic-search").tracks.rag, { order: 1000, kind: "core" })
  assert.deepEqual(versionedById.get("reranking").tracks.rag, { order: 1100, kind: "core" })
  assert.deepEqual(versionedById.get("runtime-monitoring").tracks.agent_platform, {
    order: 1300,
    kind: "core",
  })
  assert.deepEqual(versionedById.get("ai-safety").tracks.agent_platform, {
    order: 1400,
    kind: "core",
  })
  assert.deepEqual(versionedById.get("ai-governance").tracks.agent_platform, {
    order: 1500,
    kind: "core",
  })
  assert.deepEqual(versionedById.get("multimodal-ai").tracks.multimodal_realtime, {
    order: 200,
    kind: "core",
  })
  assert.deepEqual(versionedById.get("ocr").tracks.multimodal_realtime, {
    order: 250,
    kind: "recommended",
  })
  assert.deepEqual(versionedById.get("speech-recognition").tracks.multimodal_realtime, {
    order: 300,
    kind: "core",
  })
  assert.deepEqual(versionedById.get("speech-synthesis").tracks.multimodal_realtime, {
    order: 400,
    kind: "core",
  })
  const trackCounts = Object.fromEntries(
    ["agent_app", "rag", "agent_platform", "multimodal_realtime"].map((role) => [
      role,
      actualCourses.filter((course) => course.tracks[role]).length,
    ]),
  )
  assert.deepEqual(trackCounts, {
    agent_app: 32,
    rag: 35,
    agent_platform: 38,
    multimodal_realtime: 29,
  })
})

test("authored Markdown escapes wikilink aliases inside table rows", () => {
  const docsRoot = fileURLToPath(new URL("../../docs-CN/", import.meta.url))
  const collectMarkdownFiles = (directory) => readdirSync(directory, { withFileTypes: true })
    .flatMap((entry) => {
      const entryPath = path.join(directory, entry.name)
      if (entry.isDirectory()) return collectMarkdownFiles(entryPath)
      return entry.isFile() && entry.name.endsWith(".md") ? [entryPath] : []
    })
  const violations = collectMarkdownFiles(docsRoot)
    .map((filePath) => ({
      relativePath: path.relative(docsRoot, filePath).replaceAll("\\", "/"),
      source: readFileSync(filePath, "utf8"),
    }))
    .filter(({ source }) => normalizeTableWikilinks(source) !== source)
    .map(({ relativePath }) => relativePath)

  assert.deepEqual(
    violations,
    [],
    "Wikilink aliases inside Markdown tables must use \\| so the alias is not parsed as a table column.",
  )
})

test("table wikilinks escape alias pipes and unwrap link-only code spans", () => {
  const source = [
    "| 顺序 | 课程 |",
    "| --- | --- |",
    "| 1 | [[RAG/01-系统边界|系统边界]] |",
    "| 2 | `[[RAG/02-查询路由|查询路由]]` |",
    "| 3 | [[RAG/03-已转义\\|已转义]] |",
    "正文 [[RAG/04-正文|正文链接]] 不应改写。",
    "```markdown",
    "| 5 | [[RAG/05-代码|代码示例]] |",
    "```",
  ].join("\n")
  const result = normalizeTableWikilinks(source, "RAG/00-目录.md", new Set([
    "RAG/01-系统边界.md",
    "RAG/02-查询路由.md",
    "RAG/03-已转义.md",
  ]))
  assert.match(result, /\[\[RAG\/01-系统边界\\\|系统边界\]\]/)
  assert.match(result, /\[\[RAG\/02-查询路由\\\|查询路由\]\]/)
  assert.doesNotMatch(result, /`\[\[RAG\/02/)
  assert.match(result, /\[\[RAG\/03-已转义\\\|已转义\]\]/)
  assert.match(result, /正文 \[\[RAG\/04-正文\|正文链接\]\] 不应改写/)
  assert.match(result, /```markdown\n\| 5 \| \[\[RAG\/05-代码\|代码示例\]\] \|/)
})

test("table syntax examples stay code when their wikilink targets do not exist", () => {
  const source = "| 语法 | 说明 |\n| --- | --- |\n| `[[路径/笔记|别名]]` | 教学示例 |"
  const result = normalizeTableWikilinks(source, "Markdown/语法.md", new Set(["Markdown/语法.md"]))
  assert.match(result, /`\[\[路径\/笔记\\\|别名\]\]`/)
})

test("public staging redacts the configured vault path without changing generic examples", () => {
  const vaultRoot = "D:\\vaults\\Gao"
  const source = [
    'Set-Location "D:\\vaults\\Gao\\Knowledge\\AI Agent Engineer"',
    "source: D:/vaults/Gao/Knowledge/AI Agent Engineer",
    "example: C:\\Users\\<用户名>",
  ].join("\n")
  const result = redactVaultRoot(source, vaultRoot)
  assert.doesNotMatch(result, /D:[\\/]vaults/i)
  assert.match(result, /X:\\path\\to\\your-vault/)
  assert.match(result, /X:\/path\/to\/your-vault/)
  assert.match(result, /C:\\Users\\<用户名>/)
})

test("public staging redacts POSIX roots independently of the host platform", () => {
  const source = [
    "source: /home/alice/Gao/Knowledge/AI Agent Engineer",
    "escaped: \\home\\alice\\Gao\\Knowledge\\AI Agent Engineer",
  ].join("\n")
  const result = redactVaultRoot(source, "/home/alice/Gao/")
  assert.doesNotMatch(result, /home[\\/]alice[\\/]Gao/i)
  assert.match(result, /X:\/path\/to\/your-vault/)
  assert.match(result, /X:\\path\\to\\your-vault/)
})

test("default machine-path redaction remains callable for production staging", () => {
  assert.equal(redactMachineSpecificPaths("generic path"), "generic path")
})

test("published course Markdown rejects the legacy local project root before redaction", () => {
  const localRoot = String.raw`Z:\portable-fixture\AI Agent Engineer`
  const authored = [
    {
      relativePath: "Agent 核心/项目.md",
      markdown: `---\ncontent_origin: original\ncontent_status: validated\n---\n${localRoot}\\docs`,
    },
  ]

  assert.throws(
    () => assertPortablePublishedMarkdown(authored),
    /project-root-relative paths.*Agent 核心\/项目\.md/,
  )
  assert.doesNotThrow(() => assertPortablePublishedMarkdown([
    {
      relativePath: "Agent 核心/项目.md",
      markdown: "从项目根目录运行：`docs\\Agent 核心`",
    },
    {
      relativePath: "维护记录/历史快照.md",
      markdown: localRoot,
    },
  ]))
})

test("publication routes match Quartz slugification", () => {
  assert.equal(slugifyPublishedPath("Agent 核心/examples/demo.py"), "Agent-核心/examples/demo.py")
  assert.equal(slugifyPublishedPath("Tool & API/100% ready?.json"), "Tool--and--API/100-percent-ready.json")
  assert.equal(markdownToHtmlPath("Agent Skills/00-目录.md"), "Agent-Skills/00-目录.html")
})

test("KaTeX gate counts only rendered error spans", () => {
  const html = [
    '<span class="katex-error" title="ParseError">bad formula</span>',
    "<span class='math katex-error diagnostic'>another bad formula</span>",
    '<span class="katex">valid formula</span>',
    '<div class="katex-error">not a KaTeX error span</div>',
    '<p>Documentation may mention span.katex-error without rendering one.</p>',
  ].join("\n")

  assert.equal(countKatexErrorSpans(html), 2)
  assert.equal(countKatexErrorSpans('<span class="katex">x</span>'), 0)
})

test("site links stay inside the GitHub Pages base path and reject unsafe schemes", () => {
  assert.equal(localTarget("RAG/00-目录.html", "https://example.com"), null)
  assert.deepEqual(localTarget("RAG/00-目录.html", "/AI-Agent-Engineer/API/00-目录"), { target: "API/00-目录" })
  assert.deepEqual(localTarget("RAG/00-目录.html", "../API/00-目录"), { target: "API/00-目录" })
  assert.deepEqual(localTarget("RAG/00-目录.html", "/outside"), { outsideBase: "/outside" })
  assert.deepEqual(localTarget("RAG/00-目录.html", "../../outside"), { outsideBase: "../../outside" })
  assert.deepEqual(localTarget("RAG/00-目录.html", "javascript:alert(1)"), {
    unsupportedScheme: "javascript:alert(1)",
  })
  assert.deepEqual(localTarget("RAG/00-目录.html", "data:text/html,unsafe"), {
    unsupportedScheme: "data:text/html,unsafe",
  })
})
