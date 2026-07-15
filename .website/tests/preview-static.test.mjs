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
    writeFileSync(path.join(root, "index.html"), "home")
    writeFileSync(path.join(root, "RAG.html"), "rag")
    writeFileSync(path.join(root, "RAG", "00-目录.html"), "course")
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
