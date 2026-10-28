import { IMPOSSIBLE, VersionInfo } from '@start9labs/start-sdk'

export const current = VersionInfo.of({
  version: '2026.10.28:0',
  releaseNotes: {
    en_US:
      'First release of VardKey for StartOS. One service with the web interface and its own SQLite database on the persistent "main" volume: the multisig key setup, the annual health check, the follow-up alerts, the history, and the CSV export. On a fresh install, set the admin password first and then configure the keys. No wallet secret is ever asked for or stored.',
    es_ES:
      'Primera versión de VardKey para StartOS. Un servicio con la interfaz web y su propia base de datos SQLite en el volumen persistente "main": la configuración de claves multifirma, la revisión anual, los avisos de seguimiento, el historial y la exportación en CSV. En una instalación nueva, establece primero la contraseña de administrador y después configura las claves. Nunca se pide ni se guarda un secreto de monedero.',
    de_DE:
      'Erste Version von VardKey für StartOS. Ein Dienst mit der Weboberfläche und einer eigenen SQLite-Datenbank auf dem persistenten Volume "main": die Multisig-Schlüsselkonfiguration, die jährliche Prüfung, die Folgehinweise, der Verlauf und der CSV-Export. Bei einer Neuinstallation zuerst das Admin-Passwort festlegen und danach die Schlüssel einrichten. Ein Wallet-Geheimnis wird niemals abgefragt oder gespeichert.',
    pl_PL:
      'Pierwsze wydanie VardKey dla StartOS. Jedna usługa z interfejsem webowym i własną bazą SQLite na trwałym wolumenie "main": konfiguracja kluczy multisig, coroczny przegląd, alerty do dalszych działań, historia i eksport do CSV. W nowej instalacji najpierw ustaw hasło administratora, a następnie skonfiguruj klucze. Sekret portfela nigdy nie jest pytany ani przechowywany.',
    fr_FR:
      'Première version de VardKey pour StartOS. Un seul service avec l’interface web et sa propre base SQLite sur le volume persistant « main » : la configuration des clés multisig, le contrôle annuel, les alertes de suivi, l’historique et l’export CSV. Sur une nouvelle installation, définissez d’abord le mot de passe administrateur, puis configurez les clés. Aucun secret de portefeuille n’est jamais demandé ni stocké.',
  },
  migrations: {
    up: async ({ effects }) => {},
    down: IMPOSSIBLE,
  },
})
