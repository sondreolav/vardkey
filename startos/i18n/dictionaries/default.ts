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

  // actions/deleteAllData.ts
  'Delete all data': 6,
  'Delete the key setup, the saved checks and the wallet software list, so the app is back at the first-run setup step. The admin account is kept.': 7,
  'I confirm that the key setup, the saved checks and the wallet software list will be deleted and cannot be recovered': 8,
  'Data deleted': 9,
  'The confirmation is required before the data can be deleted.': 10,
  'The data could not be deleted.': 11,

  // actions/setAdminPassword.ts
  'Set Admin Password': 12,
  'Generate a new admin password and show it once. Replaces any existing password.': 13,
  'Admin username': 14,
  'Leave blank to keep the current username, or to create the admin account when none exists.': 15,
  'Use at most 60 characters.': 16,
  'The admin password could not be set.': 17,
  'The admin password could not be read back.': 18,
  'Admin credentials': 19,
  'Sign in to VardKey with these credentials. The password is shown once, so store it somewhere safe.': 20,
  // A single word needs no quotes, and prettier removes them.
  Username: 21,
  Password: 22,

  // init/requireAdmin.ts
  'Set the admin password before VardKey can be used.': 23,
} as const

/**
 * Plumbing. DO NOT EDIT.
 */
export type I18nKey = keyof typeof dict
export type LangDict = Record<(typeof dict)[I18nKey], string>
export default dict
