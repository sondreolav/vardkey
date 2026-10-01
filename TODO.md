# TODO — Helsesjekk for StartOS 0.4.0

## Mål

Bygg ein **enkel lokal web-app** som køyrer som ein StartOS 0.4.0-service.

Appen skal hjelpe éin brukar å gjennomføre og dokumentere ein årleg health check av eit fast **2-av-3 multisig-oppsett** med tre nøklar:

- Nøkkel 1: SeedSigner
- Nøkkel 2: Blockstream Jade
- Nøkkel 3: sky-nøkkel hos Nunchuk

Appen skal **berre registrere resultat og historikk**. Han skal ikkje signere Bitcoin-transaksjonar, handtere private nøklar eller utføre wallet-operasjonar.

Denne `TODO.md` er det einaste kravgrunnlaget du treng for MVP.

## Språkkrav

- [ ] Brukargrensesnittet, app-tekst, kjeldekode, variabel- og funksjonsnamn, kommentarar og teknisk dokumentasjon skal vere på engelsk.
- [ ] `TODO.md` kan vere på norsk; dette er det einaste unntaket.

---

# 1. Scope for første versjon

## Dette skal vere med

- [x] Ein enkel web-app med dashboard.
- [ ] Registrering av dei tre nøklane.
- [ ] Registrering av årleg health check.
- [ ] Kontroll av alle punkta i den årlege sjekklista.
- [ ] Varsel når eit kontrollpunkt krev oppfølging.
- [ ] Historikk over gjennomførte health checks.
- [ ] Automatisk forslag til neste sjekk, ca. eitt år fram i tid.
- [ ] Rapporteksport i Excel-kompatibelt format.
- [ ] Lokal SQLite-database.
- [ ] Persistent lagring på StartOS.
- [ ] StartOS health check.
- [ ] StartOS backup og restore.

## Dette skal ikkje vere med i første versjon

- [ ] Ingen AI-integrasjon i appen.
- [ ] Ingen Bitcoin-node-integrasjon.
- [ ] Ingen Bitcoin-signering.
- [ ] Ingen PSBT-generering eller signering.
- [ ] Ingen seed phrase-lagring.
- [ ] Ingen private key-lagring.
- [ ] Ingen cloud sync av appdata.
- [ ] Ingen ekstern database.
- [ ] Ingen PWA/offline-database.
- [ ] Ingen kalenderintegrasjon.
- [ ] Ingen avansert analyse eller grafar.
- [ ] Ingen støtte for fleire multisig-oppsett i MVP.

---

# 2. Viktige reglar for appen

- [ ] Appen skal aldri spørje etter seed phrase.
- [ ] Appen skal aldri spørje etter private keys.
- [ ] Appen skal aldri lagre PIN, passord eller wallet-hemmeligheiter.
- [ ] Kontaktinformasjon til nøkkelhaldarar skal ikkje lagrast i appen; berre om kontaktinfo er verifisert.
- [ ] Appen skal ikkje late som han sjølv har utført ein hardware-test. Brukaren registrerer resultatet av testen.
- [ ] Appen skal vere lokal og enkel.
- [ ] Dersom noko ikkje er nødvendig for den årlege health check-en, skal det ikkje byggjast i MVP.

---

# 3. Fast oppsett som appen skal støtte

Appen skal starte med eitt fast multisig-oppsett:

| Nøkkel | Type | Einheit |
|---|---|---|
| 1 | Hardware | SeedSigner |
| 2 | Hardware | Blockstream Jade |
| 3 | Cloud | Nunchuk |

- [ ] Vis 2-av-3 som oppsettet i dashboardet.
- [ ] Ha tre nøkkelprofilar, éin for kvar nøkkel.
- [ ] La brukaren gi nøklane lesbare namn dersom ønskjeleg.
- [ ] Ikkje bygg generell støtte for mange oppsett enno.

---

# 4. Datamodell

Bruk SQLite med så få tabellar som mogleg.

## 4.1 `keys`

- [ ] `id`
- [ ] `key_number` = 1, 2 eller 3
- [ ] `name`
- [ ] `type` = `hardware` eller `cloud`
- [ ] `device` = SeedSigner / Blockstream Jade / Nunchuk
- [ ] `created_at`

## 4.2 `health_checks`

Ein rad/record for kvar årlege health check.

- [ ] `id`
- [ ] `checked_at`
- [ ] `next_check_due`
- [ ] `software_compatibility_status`
- [ ] `sparrow_version`
- [ ] `nunchuk_version`
- [ ] `ai_security_status`
- [ ] `contact_info_verified`
- [ ] `comments`

## 4.3 `key_checks`

Eitt record per nøkkel i kvar health check.

- [ ] `id`
- [ ] `health_check_id`
- [ ] `key_id`
- [ ] `available`
- [ ] `hardware_works`
- [ ] `firmware_version`
- [ ] `seed_backup_status`
- [ ] `cloud_health_status`
- [ ] `cloud_provider_operational`
- [ ] `address_path_verified`
- [ ] `address_path`
- [ ] `comments`

Reglar:

- [ ] `hardware_works` skal vere relevant for nøkkel 1 og 2.
- [ ] `firmware_version` skal vere relevant for nøkkel 1 og 2.
- [ ] `cloud_health_status` og `cloud_provider_operational` skal vere relevante for nøkkel 3.
- [ ] `address_path` skal kunne lagre den verifiserte adressestien.

## 4.4 `tool_checks`

Ein enkel matrise for støtte-kontrollen.

Produkta som skal vurderast:

- SeedSigner
- Blockstream Jade
- Nunchuk
- Sparrow Wallet

Felt:

- [ ] `id`
- [ ] `health_check_id`
- [ ] `product`
- [ ] `bip327_status`
- [ ] `slip39_status`
- [ ] `version`
- [ ] `checked_at`
- [ ] `notes`

---

# 5. Statusverdiar

## 5.1 Generelle kontrollar

Bruk enkle statusar som:

- `OK`
- `PROBLEM`
- `IKKJE_VURDERT`

- [ ] Bruk same statuslogikk i database og UI.
- [ ] Ikkje bland saman «ikkje vurdert» og eit faktisk negativt resultat.

## 5.2 KI-sikkerheitsstatus

Bruk nøyaktig desse fire verdiane:

- [ ] `TRYGG`
- [ ] `PATCHA`
- [ ] `SÅRBAR`
- [ ] `KOMPROMITTERT`

Ingen andre sikkerheitsstatusar skal brukast.

---

# 6. Årleg health check — steg for steg

## Steg 1 — Start kontroll

- [ ] Brukaren trykkjer `Start årleg health check`.
- [ ] Dagens dato blir føreslått automatisk.
- [ ] Neste sjekk blir føreslått ca. eitt år fram i tid.

## Steg 2 — Kontroller nøkkel 1: SeedSigner

- [ ] Tilgjengeleg / ikkje tilgjengeleg.
- [ ] Hardware fungerer / fungerer ikkje.
- [ ] Registrer firmware-versjon.
- [ ] Kontroller seed-backup.
- [ ] Kontroller at backupen er intakt og stemmer med hardware.
- [ ] Verifiser adresse.
- [ ] Verifiser derivasjonshøgd.
- [ ] Verifiser adresse-sti.
- [ ] Kommentar ved behov.

## Steg 3 — Kontroller nøkkel 2: Blockstream Jade

- [ ] Tilgjengeleg / ikkje tilgjengeleg.
- [ ] Hardware fungerer / fungerer ikkje.
- [ ] Registrer firmware-versjon.
- [ ] Kontroller seed-backup.
- [ ] Kontroller at backupen er intakt og stemmer med hardware.
- [ ] Verifiser adresse.
- [ ] Verifiser derivasjonshøgd.
- [ ] Verifiser adresse-sti.
- [ ] Kommentar ved behov.

## Steg 4 — Kontroller nøkkel 3: Nunchuk sky-nøkkel

- [ ] Tilgjengeleg / ikkje tilgjengeleg.
- [ ] Gjennomfør cloud health check.
- [ ] Verifiser at Nunchuk framleis er i drift.
- [ ] Registrer resultatet av leverandør-kontrollen.
- [ ] Verifiser relevant adresse/oppsett.
- [ ] Kommentar ved behov.

## Steg 5 — Programvare-kompatibilitet

- [ ] Registrer Sparrow-versjon dersom Sparrow blir brukt.
- [ ] Registrer Nunchuk-versjon dersom Nunchuk blir brukt.
- [ ] Verifiser at Sparrow og/eller Nunchuk støttar hardware-oppsettet.
- [ ] Registrer `OK` eller `PROBLEM`.
- [ ] Legg inn kommentar dersom det er problem.

## Steg 6 — BIP327 / SLIP39

Sjekk status for kvart av desse fire produkta:

- [ ] SeedSigner — BIP327
- [ ] SeedSigner — SLIP39
- [ ] Blockstream Jade — BIP327
- [ ] Blockstream Jade — SLIP39
- [ ] Nunchuk — BIP327
- [ ] Nunchuk — SLIP39
- [ ] Sparrow Wallet — BIP327
- [ ] Sparrow Wallet — SLIP39

For kvart resultat:

- [ ] Registrer status.
- [ ] Registrer versjon dersom relevant.
- [ ] Registrer dato.
- [ ] Registrer kommentar/kjelde dersom relevant.

Appen skal berre **registrere** dette resultatet. Han skal ikkje starte ei oppgradering.

## Steg 7 — KI-sikkerheitsstatus

Brukaren skal registrere resultat frå ein ekstern KI-/research-sjekk av leverandørane.

Leverandørar:

- [ ] SeedSigner
- [ ] Blockstream Jade
- [ ] Nunchuk
- [ ] Sparrow Wallet

For kvar leverandør:

- [ ] Registrer status: TRYGG / PATCHA / SÅRBAR / KOMPROMITTERT.
- [ ] Registrer kort kommentar.

Appen skal ikkje kontakte KI sjølv i MVP.

## Steg 8 — Kontaktinfo

- [ ] Stadfest at kontaktinformasjonen til alle nøkkelhaldarane er gyldig.
- [ ] Lagre berre `JA` / `NEI`.
- [ ] Ikkje lagre namn, telefonnummer, e-post eller anna kontaktinnhald.

## Steg 9 — Kommentar

- [ ] Eitt overordna kommentarfelt for observasjonar.
- [ ] Eigne kommentarar per nøkkel der nødvendig.

## Steg 10 — Oppsummering

Før lagring skal appen vise:

- [ ] Alle kontrollpunkt.
- [ ] Alle problem.
- [ ] Alle manglande kontrollar.
- [ ] Neste sjekkdato.
- [ ] Eventuelle handlingar som bør følgjast opp.

- [ ] Brukaren må trykkje `Lagre health check` for å lagre kontrollen.

---

# 7. Varsel og oppfølging

Appen skal gi tydelege varsel når resultatet krev handling.

- [ ] Nøkkel ikkje tilgjengeleg → vis at dette krev umiddelbar oppfølging.
- [ ] Hardware fungerer ikkje → vis at seed-backup bør testast på annan kompatibel hardware.
- [ ] Seed-backup manglar eller er øydelagd → vis at PROTOKOLL 3: Nøkkeltap skal aktiverast.
- [ ] Adresseverifisering feilar → vis at adressa bør kontrollerast mot BSMS og testast på nytt.
- [ ] Programvare støttar ikkje lenger hardware → vis at alternativ programvare/løysing bør vurderast.
- [ ] BIP327-status er positiv → vis at framtidig BIP327-oppgradering kan vurderast.
- [ ] SLIP39-status er positiv → vis at framtidig SLIP39-aktivering kan vurderast.
- [ ] KI-status `SÅRBAR` → vis at firmware-/sikkerheitsproblem må følgjast opp.
- [ ] KI-status `KOMPROMITTERT` → vis at nøkkeltapsprosedyre må følgjast.
- [ ] Kontaktinfo er ikkje stadfesta → vis at kontaktinformasjon må oppdaterast i den eksterne dokumentasjonen.

Appen skal ikkje automatisk utføre nokon av desse tiltaka.

---

# 8. Dashboard

Dashboardet skal vere enkelt.

- [ ] Vis 2-av-3 oppsettet.
- [ ] Vis status for nøkkel 1.
- [ ] Vis status for nøkkel 2.
- [ ] Vis status for nøkkel 3.
- [ ] Vis dato for siste health check.
- [ ] Vis neste health check.
- [ ] Vis aktive varsel.
- [ ] Knapp: `Start årleg health check`.
- [ ] Knapp/lenke: `Historikk`.

---

# 9. Historikk

- [ ] Vis alle gjennomførte health checks kronologisk.
- [ ] Opne ein health check i read-only-visning.
- [ ] Vis dato.
- [ ] Vis neste sjekk.
- [ ] Vis status per nøkkel.
- [ ] Vis programvarestatus.
- [ ] Vis BIP327/SLIP39-resultat.
- [ ] Vis KI-status.
- [ ] Vis kommentarar.
- [ ] Gamle health checks skal ikkje overskrivast når ein ny blir registrert.

---

# 10. Rapporteksport

Rapporten skal kunne brukast i Excel.

- [ ] Implementer XLSX-eksport dersom dette kan gjerast enkelt.
- [ ] Elles implementer CSV med tydeleg dokumentasjon om Excel-kompatibilitet.
- [ ] Eksporter alle nødvendige felt frå health check.
- [ ] Éin gjennomført health check skal kunne identifiserast som éi historisk kontroll.
- [ ] Ta med dato.
- [ ] Ta med nøkkelstatus.
- [ ] Ta med hardware-/firmware-resultat.
- [ ] Ta med seed/cloud-resultat.
- [ ] Ta med adresse-sti.
- [ ] Ta med programvareversjon og kompatibilitet.
- [ ] Ta med BIP327/SLIP39.
- [ ] Ta med KI-status.
- [ ] Ta med kontaktinfo-verifisering.
- [ ] Ta med neste sjekk.
- [ ] Ta med kommentarar.

---

# 11. Backend

Vel den enklaste teknologien som passar godt for ein liten lokal web-app.

- [ ] Implementer SQLite.
- [ ] Implementer database-initialisering/migrering.
- [ ] Implementer lagring av nøklar.
- [ ] Implementer lagring av health checks.
- [ ] Implementer historikk.
- [ ] Implementer varsellogikken.
- [ ] Implementer rapporteksport.
- [ ] Implementer health endpoint.

Minimum:

- [ ] `GET /health`
- [ ] `GET /api/keys`
- [ ] `GET /api/health-checks`
- [ ] `GET /api/health-checks/:id`
- [ ] `POST /api/health-checks`
- [ ] `GET /api/export`

---

# 12. Frontend

- [ ] Lag enkel responsiv web-UI.
- [ ] Prioriter enkelheit framfor grafisk kompleksitet.
- [ ] Bruk tydelege statusfelt.
- [ ] Bruk faste val der status skal vere ein avgrensa verdi.
- [ ] Vis problem tydeleg.
- [ ] Vis kva som står att før ein health check kan lagrast.
- [ ] Sørg for at appen fungerer godt i vanleg StartOS-browser.

---

# 13. StartOS 0.4.0

Bygg appen som éin enkel StartOS-service.

```text
StartOS 0.4.0
└── Helsesjekk
    ├── Web UI
    ├── Backend/API
    ├── SQLite
    └── Persistent data
```

- [ ] Opprett StartOS package.
- [ ] Opprett manifest.
- [ ] Opprett service-definisjon.
- [ ] Opprett HTTP web-interface.
- [ ] Opprett persistent volume.
- [ ] Opprett health check.
- [ ] Opprett backup-oppsett.
- [ ] Opprett installasjons-/brukarinstruksjonar.
- [ ] Bygg `.s9pk`.
- [ ] Verifiser at pakken kan installerast på StartOS 0.4.0.

Unngå:

- [ ] Ingen Postgres.
- [ ] Ingen Redis.
- [ ] Ingen ekstern backend.
- [ ] Ingen ekstern cloud-service for appdata.
- [ ] Ingen ekstra container utan konkret behov.

---

# 14. Lagring og backup

- [ ] SQLite-database skal liggje på persistent volum.
- [ ] Appdata skal overleve restart.
- [ ] Konfigurer StartOS backup av persistent data.
- [ ] Test backup.
- [ ] Test restore.
- [ ] Verifiser at gamle health checks finst etter restore.

---

# 15. Sikkerheit og personvern

- [ ] Ingen seed phrase i database.
- [ ] Ingen private keys i database.
- [ ] Ingen wallet-passord i database.
- [ ] Ingen sky-passord eller tokens i database.
- [ ] Ingen unødvendige personopplysningar.
- [ ] Kontaktinfo blir berre registrert som verifisert/ikkje verifisert.
- [ ] Valider input på serveren.
- [ ] Bruk parameteriserte SQL-spørringar.
- [ ] Ikkje implementer eigen kryptografi.
- [ ] Ikkje send data til eksterne tenester i MVP.

---

# 16. Testing

## Funksjonstest

- [ ] Opprett dei tre nøklane.
- [ ] Start health check.
- [ ] Fullfør alle kontrollpunkt.
- [ ] Lagre health check.
- [ ] Vis han i historikken.
- [ ] Start ny health check.
- [ ] Verifiser at gammal kontroll framleis finst.

## Problemtest

- [ ] Test nøkkel utilgjengeleg.
- [ ] Test hardware-feil.
- [ ] Test seed-backup-feil.
- [ ] Test adresseverifiseringsfeil.
- [ ] Test programvare-inkompatibilitet.
- [ ] Test BIP327-resultat.
- [ ] Test SLIP39-resultat.
- [ ] Test KI-status `SÅRBAR`.
- [ ] Test KI-status `KOMPROMITTERT`.
- [ ] Test kontaktinfo `NEI`.

## StartOS-test

- [ ] Installer `.s9pk` på StartOS 0.4.0.
- [ ] Start service.
- [ ] Opne web UI.
- [ ] Utfør ein komplett test-check.
- [ ] Restart service.
- [ ] Verifiser at data framleis finst.
- [ ] Ta backup.
- [ ] Restore backup.
- [ ] Verifiser data etter restore.

---

# 17. Ferdigkriterium for første release

Før første release skal alle desse vere oppfylte:

- [ ] Appen køyrer på StartOS 0.4.0.
- [ ] Dei tre nøklane er representerte i appen.
- [ ] Ein komplett årleg health check kan gjennomførast i nettlesaren.
- [ ] Alle årlege kontrollpunkt kan registrerast.
- [ ] BIP327/SLIP39 kan registrerast for SeedSigner, Blockstream Jade, Nunchuk og Sparrow.
- [ ] KI-status kan registrerast som TRYGG, PATCHA, SÅRBAR eller KOMPROMITTERT.
- [ ] Kontaktinfo kan verifiserast utan å lagre kontaktinformasjonen.
- [ ] Problem gir tydelege varsel.
- [ ] Neste sjekk blir lagra.
- [ ] Historikk fungerer.
- [ ] Excel-kompatibel rapport kan eksporterast.
- [ ] Data overlever restart.
- [ ] Backup og restore fungerer.
- [ ] Ingen wallet-hemmeligheiter blir lagra.

---

# 18. Arbeidsrekkefølgje for AI-programmeraren

Utfør oppgåvene i denne rekkefølgja og ikkje hopp fram til avanserte funksjonar:

- [x] 1. Opprett grunnleggande web-app.
- [x] 2. Opprett SQLite og datamodellen.
- [x] 3. Implementer dei tre faste nøklane.
- [ ] 4. Implementer health check-skjemaet.
- [ ] 5. Implementer lagring og historikk.
- [ ] 6. Implementer varsellogikken.
- [ ] 7. Implementer dashboard.
- [ ] 8. Implementer rapporteksport.
- [ ] 9. Implementer StartOS package.
- [ ] 10. Implementer persistent storage og backup.
- [ ] 11. Test restart og restore.
- [ ] 12. Bygg endeleg `.s9pk` og gjer første release.

**Hovudregel:** Bygg den minste løysinga som oppfyller lista over. Ikkje legg til nye funksjonar, tenester eller arkitektur utan at dei er nødvendige for punkta i denne TODO-lista.
