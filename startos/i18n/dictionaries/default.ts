export const DEFAULT_LANG = 'en_US'

const dict = {
  // main.ts
  'Starting VardKey': 0,
  'Web Interface': 1,
  'The web interface is ready': 2,
  'The web interface is not ready': 3,

  // interfaces.ts
  'Web UI': 4,
  'The web interface of VardKey': 5,

  // actions/deleteHistory.ts
  'Delete history': 6,
  'Delete every saved health check, with the follow-up it closed. The key setup and the wallet software list are kept.': 7,
  'I confirm that the stored history will be deleted and cannot be recovered': 8,
  'History deleted': 9,
  'The confirmation is required before the history can be deleted.': 10,
  'The history could not be deleted.': 11,
} as const

/**
 * Plumbing. DO NOT EDIT.
 */
export type I18nKey = keyof typeof dict
export type LangDict = Record<(typeof dict)[I18nKey], string>
export default dict
