import test from "node:test"
import assert from "node:assert/strict"
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs"
import { tmpdir } from "node:os"
import path from "node:path"
import { runtimeEnvironment } from "../scripts/bootstrap-runtime.mjs"
import { scanPublicRepository } from "../scripts/scan-public-repository.mjs"

async function withRepositoryFixture(callback) {
  const root = mkdtempSync(path.join(tmpdir(), "aae-security-"))
  try {
    writeFileSync(path.join(root, "README.md"), "safe")
    return await callback(root)
  } finally {
    rmSync(root, { recursive: true, force: true })
  }
}

test("runtime rewrites pinned public GitHub SSH dependencies to HTTPS only for child processes", () => {
  const environment = runtimeEnvironment()
  assert.equal(environment.GIT_CONFIG_COUNT, "2")
  assert.equal(environment.GIT_CONFIG_KEY_0, "url.https://github.com/.insteadOf")
  assert.equal(environment.GIT_CONFIG_VALUE_0, "ssh://git@github.com/")
  assert.equal(environment.GIT_CONFIG_KEY_1, "url.https://github.com/.insteadOf")
  assert.equal(environment.GIT_CONFIG_VALUE_1, "git@github.com:")
})

test("repository scanner permits only the documented environment template", async () => {
  await withRepositoryFixture(async (root) => {
    writeFileSync(path.join(root, ".env.example"), "API_KEY=replace-me")
    await assert.doesNotReject(scanPublicRepository(root))
    writeFileSync(path.join(root, ".env.production"), "API_KEY=replace-me")
    await assert.rejects(
      scanPublicRepository(root),
      /Sensitive configuration filename/,
    )
  })
})

test("repository scanner rejects package-manager credential files", async () => {
  await withRepositoryFixture(async (root) => {
    writeFileSync(path.join(root, ".npmrc"), "registry=https://registry.npmjs.org/")
    await assert.rejects(scanPublicRepository(root), /Sensitive configuration filename/)
  })
})

test("repository scanner rejects unexpected or unpinned workflows", async () => {
  await withRepositoryFixture(async (root) => {
    const workflows = path.join(root, ".github", "workflows")
    mkdirSync(workflows, { recursive: true })
    writeFileSync(path.join(workflows, "extra.yml"), "permissions: {}\n")
    await assert.rejects(scanPublicRepository(root), /Unexpected workflow/)
    rmSync(path.join(workflows, "extra.yml"))
    writeFileSync(
      path.join(workflows, "deploy-pages.yml"),
      "permissions: {}\nsteps:\n  - uses: actions/checkout@main\n    with:\n      persist-credentials: false\n",
    )
    await assert.rejects(scanPublicRepository(root), /not pinned to a full commit SHA/)
  })
})
