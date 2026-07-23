import { getSiteLocale } from "../config/site-locales.mjs"

export const SITE_BASE_PATH = process.env.SITE_BASE_PATH || "/AI-Agent-Engineer"
export const SITE_ORIGIN = process.env.SITE_ORIGIN || "https://gaos6e.github.io"
export const SITE_URL = `${SITE_ORIGIN}${SITE_BASE_PATH}`

export function localeSiteBasePath(locale) {
  const prefix = getSiteLocale(locale).routePrefix
  return `${SITE_BASE_PATH.replace(/\/+$/, "")}/${prefix}`
}

export function localeSiteUrl(locale) {
  return `${SITE_ORIGIN.replace(/\/+$/, "")}${localeSiteBasePath(locale)}`
}

export function quartzBaseUrl(locale) {
  const origin = new URL(SITE_ORIGIN)
  return `${origin.host}${localeSiteBasePath(locale)}`
}
