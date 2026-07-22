import test from "node:test"
import assert from "node:assert/strict"
import { mkdtempSync, mkdirSync, rmSync, writeFileSync } from "node:fs"
import { tmpdir } from "node:os"
import path from "node:path"
import { resolvePreviewPath } from "../scripts/preview-static.mjs"

function withFixture(callback) {
  const root = mkdtempSync(path.join(tmpdir(), "aae-preview-"))
  try {
    mkdirSync(path.join(root, "RAG"), { recursive: true })
    mkdirSync(path.join(root, "深度学习"), { recursive: true })
    writeFileSync(path.join(root, "index.html"), "home")
    writeFileSync(path.join(root, "RAG.html"), "rag")
    writeFileSync(path.join(root, "RAG", "00-目录.html"), "course")
    writeFileSync(path.join(root, "深度学习", "04-02.3-线性代数.html"), "numbered lesson")
    return callback(root)
  } finally {
    rmSync(root, { recursive: true, force: true })
  }
}

test("preview resolves the base homepage and extensionless Quartz routes", () => {
  withFixture((root) => {
    assert.equal(
      resolvePreviewPath(root, "/AI-Agent-Engineer", "/AI-Agent-Engineer/"),
      path.join(root, "index.html"),
    )
    assert.equal(
      resolvePreviewPath(root, "/AI-Agent-Engineer", "/AI-Agent-Engineer/RAG"),
      path.join(root, "RAG.html"),
    )
    assert.equal(
      resolvePreviewPath(
        root,
        "/AI-Agent-Engineer",
        "/AI-Agent-Engineer/RAG/00-%E7%9B%AE%E5%BD%95",
      ),
      path.join(root, "RAG", "00-目录.html"),
    )
    assert.equal(
      resolvePreviewPath(
        root,
        "/AI-Agent-Engineer",
        "/AI-Agent-Engineer/%E6%B7%B1%E5%BA%A6%E5%AD%A6%E4%B9%A0/04-02.3-%E7%BA%BF%E6%80%A7%E4%BB%A3%E6%95%B0",
      ),
      path.join(root, "深度学习", "04-02.3-线性代数.html"),
    )
  })
})

test("preview rejects paths outside the configured site base", () => {
  withFixture((root) => {
    assert.equal(resolvePreviewPath(root, "/AI-Agent-Engineer", "/other/RAG"), null)
    assert.equal(
      resolvePreviewPath(root, "/AI-Agent-Engineer", "/AI-Agent-Engineer/%2e%2e/secret"),
      null,
    )
    assert.equal(
      resolvePreviewPath(root, "/AI-Agent-Engineer", "/AI-Agent-Engineer/RAG%5csecret"),
      null,
    )
  })
})
