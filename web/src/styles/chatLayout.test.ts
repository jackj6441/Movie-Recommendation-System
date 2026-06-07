import { readFileSync } from "node:fs"
import { dirname, join } from "node:path"
import { fileURLToPath } from "node:url"
import { describe, expect, it } from "vitest"

const stylesDir = dirname(fileURLToPath(import.meta.url))
const chatCss = readFileSync(join(stylesDir, "chat.css"), "utf8")
const tokensCss = readFileSync(join(stylesDir, "tokens.css"), "utf8")

describe("desktop chat wing sticky layout", () => {
  it("defines sticky tokens and pins both wing columns on desktop", () => {
    expect(tokensCss).toContain("--chat-wing-sticky-top")
    expect(tokensCss).toContain("--chat-wing-sticky-max-height")

    expect(chatCss).toMatch(
      /@media \(min-width: 1024px\)[\s\S]*\.chat-session-sidebar[\s\S]*position: sticky/,
    )
    expect(chatCss).toMatch(
      /@media \(min-width: 1024px\)[\s\S]*\.taste-rail--desktop[\s\S]*position: sticky/,
    )
    expect(chatCss).toMatch(/\.chat-app-layout[\s\S]*align-items: start/)
  })
})
