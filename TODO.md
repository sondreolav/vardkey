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

- [x] Brukargrensesnittet, app-tekst, kjeldekode, variabel- og funksjonsnamn, kommentarar og teknisk dokumentasjon skal vere på engelsk.
- [x] `TODO.md` kan vere på norsk; dette er det einaste unntaket.

---

# 1. Scope for første versjon

## Dette skal vere med

- [x] Ein enkel web-app med dashboard.
- [x] Registrering av dei tre nøklane.
- [x] Registrering av årleg health check.
- [x] Kontroll av alle punkta i den årlege sjekklista.
- [x] Varsel når eit kontrollpunkt krev oppfølging.
- [x] Historikk over gjennomførte health checks.
- [x] Automatisk forslag til neste sjekk, ca. eitt år fram i tid.
- [ ] Rapporteksport i Excel-kompatibelt format.
- [x] Lokal SQLite-database.
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

- [x] Appen skal aldri spørje etter seed phrase.
- [x] Appen skal aldri spørje etter private keys.
- [x] Appen skal aldri lagre PIN, passord eller wallet-hemmeligheiter.
- [x] Kontaktinformasjon til nøkkelhaldarar skal ikkje lagrast i appen; berre om kontaktinfo er verifisert.
- [x] Appen skal ikkje late som han sjølv har utført ein hardware-test. Brukaren registrerer resultatet av testen.
- [x] Appen skal vere lokal og enkel.
- [x] Dersom noko ikkje er nødvendig for den årlege health check-en, skal det ikkje byggjast i MVP.

---

# 3. Fast oppsett som appen skal støtte

Appen skal starte med eitt fast multisig-oppsett:

| Nøkkel | Type | Einheit |
|---|---|---|
| 1 | Hardware | SeedSigner |
| 2 | Hardware | Blockstream Jade |
| 3 | Cloud | Nunchuk |

- [x] Vis 2-av-3 som oppsettet i dashboardet.
- [x] Ha tre nøkkelprofilar, éin for kvar nøkkel.
- [ ] La brukaren gi nøklane lesbare namn dersom ønskjeleg.
- [x] Ikkje bygg generell støtte for mange oppsett enno.

---

# 4. Datamodell

Bruk SQLite med så få tabellar som mogleg.

## 4.1 `keys`

- [x] `id`
- [x] `key_number` = 1, 2 eller 3
- [x] `name`
- [x] `type` = `hardware` eller `cloud`
- [x] `device` = SeedSigner / Blockstream Jade / Nunchuk
- [x] `created_at`

## 4.2 `health_checks`

Ein rad/record for kvar årlege health check.

- [x] `id`
- [x] `checked_at`
- [x] `next_check_due`
- [x] `software_compatibility_status`
- [x] `sparrow_version`
- [x] `nunchuk_version`
- [ ] `ai_security_status`
- [x] `contact_info_verified`
- [x] `comments`

## 4.3 `key_checks`

Eitt record per nøkkel i kvar health check.

- [x] `id`
- [x] `health_check_id`
- [x] `key_id`
- [x] `available`
- [x] `hardware_works`
- [x] `firmware_version`
- [x] `seed_backup_status`
- [x] `cloud_health_status`
- [x] `cloud_provider_operational`
- [x] `address_path_verified`
- [x] `address_path`
- [x] `comments`

Reglar:

- [x] `hardware_works` skal vere relevant for nøkkel 1 og 2.
- [x] `firmware_version` skal vere relevant for nøkkel 1 og 2.
- [x] `cloud_health_status` og `cloud_provider_operational` skal vere relevante for nøkkel 3.
- [x] `address_path` skal kunne lagre den verifiserte adressestien.

## 4.4 `tool_checks`

Ein enkel matrise for støtte-kontrollen.

Produkta som skal vurderast:

- SeedSigner
- Blockstream Jade
- Nunchuk
- Sparrow Wallet

Felt:

- [x] `id`
- [x] `health_check_id`
- [x] `product`
- [x] `bip327_status`
- [x] `slip39_status`
- [x] `version`
- [x] `checked_at`
- [x] `notes`

---

# 5. Statusverdiar

## 5.1 Generelle kontrollar

Bruk enkle statusar som:

- `OK`
- `PROBLEM`
- `IKKJE_VURDERT`

- [x] Bruk same statuslogikk i database og UI.
- [x] Ikkje bland saman «ikkje vurdert» og eit faktisk negativt resultat.

## 5.2 KI-sikkerheitsstatus

Bruk nøyaktig desse fire verdiane:

- [x] `TRYGG`
- [x] `PATCHA`
- [x] `SÅRBAR`
- [x] `KOMPROMITTERT`

Ingen andre sikkerheitsstatusar skal brukast.

---

# 6. Årleg health check — steg for steg

## Steg 1 — Start kontroll

- [x] Brukaren trykkjer `Start årleg health check`.
- [x] Dagens dato blir føreslått automatisk.
- [x] Neste sjekk blir føreslått ca. eitt år fram i tid.

## Steg 2 — Kontroller nøkkel 1: SeedSigner

- [x] Tilgjengeleg / ikkje tilgjengeleg.
- [x] Hardware fungerer / fungerer ikkje.
- [x] Registrer firmware-versjon.
- [x] Kontroller seed-backup.
- [x] Kontroller at backupen er intakt og stemmer med hardware.
- [x] Verifiser adresse.
- [x] Verifiser derivasjonshøgd.
- [x] Verifiser adresse-sti.
- [x] Kommentar ved behov.

## Steg 3 — Kontroller nøkkel 2: Blockstream Jade

- [x] Tilgjengeleg / ikkje tilgjengeleg.
- [x] Hardware fungerer / fungerer ikkje.
- [x] Registrer firmware-versjon.
- [x] Kontroller seed-backup.
- [x] Kontroller at backupen er intakt og stemmer med hardware.
- [x] Verifiser adresse.
- [x] Verifiser derivasjonshøgd.
- [x] Verifiser adresse-sti.
- [x] Kommentar ved behov.

## Steg 4 — Kontroller nøkkel 3: Nunchuk sky-nøkkel

- [x] Tilgjengeleg / ikkje tilgjengeleg.
- [x] Gjennomfør cloud health check.
- [x] Verifiser at Nunchuk framleis er i drift.
- [x] Registrer resultatet av leverandør-kontrollen.
- [x] Verifiser relevant adresse/oppsett.
- [x] Kommentar ved behov.

## Steg 5 — Programvare-kompatibilitet

- [x] Registrer Sparrow-versjon dersom Sparrow blir brukt.
- [x] Registrer Nunchuk-versjon dersom Nunchuk blir brukt.
- [x] Verifiser at Sparrow og/eller Nunchuk støttar hardware-oppsettet.
- [x] Registrer `OK` eller `PROBLEM`.
- [x] Legg inn kommentar dersom det er problem.

## Steg 6 — BIP327 / SLIP39

Sjekk status for kvart av desse fire produkta:

- [x] SeedSigner — BIP327
- [x] SeedSigner — SLIP39
- [x] Blockstream Jade — BIP327
- [x] Blockstream Jade — SLIP39
- [x] Nunchuk — BIP327
- [x] Nunchuk — SLIP39
- [x] Sparrow Wallet — BIP327
- [x] Sparrow Wallet — SLIP39

For kvart resultat:

- [x] Registrer status.
- [x] Registrer versjon dersom relevant.
- [x] Registrer dato.
- [x] Registrer kommentar/kjelde dersom relevant.

Appen skal berre **registrere** dette resultatet. Han skal ikkje starte ei oppgradering.

## Steg 7 — KI-sikkerheitsstatus

Brukaren skal registrere resultat frå ein ekstern KI-/research-sjekk av leverandørane.

Leverandørar:

- [x] SeedSigner
- [x] Blockstream Jade
- [x] Nunchuk
- [x] Sparrow Wallet

For kvar leverandør:

- [x] Registrer status: TRYGG / PATCHA / SÅRBAR / KOMPROMITTERT.
- [x] Registrer kort kommentar.

Appen skal ikkje kontakte KI sjølv i MVP.

## Steg 8 — Kontaktinfo

- [x] Stadfest at kontaktinformasjonen til alle nøkkelhaldarane er gyldig.
- [x] Lagre berre `JA` / `NEI`.
- [x] Ikkje lagre namn, telefonnummer, e-post eller anna kontaktinnhald.

## Steg 9 — Kommentar

- [x] Eitt overordna kommentarfelt for observasjonar.
- [x] Eigne kommentarar per nøkkel der nødvendig.

## Steg 10 — Oppsummering

Før lagring skal appen vise:

- [x] Alle kontrollpunkt.
- [x] Alle problem.
- [x] Alle manglande kontrollar.
- [x] Neste sjekkdato.
- [x] Eventuelle handlingar som bør følgjast opp.

- [x] Brukaren må trykkje `Lagre health check` for å lagre kontrollen.

---

# 7. Varsel og oppfølging

Appen skal gi tydelege varsel når resultatet krev handling.

- [x] Nøkkel ikkje tilgjengeleg → vis at dette krev umiddelbar oppfølging.
- [x] Hardware fungerer ikkje → vis at seed-backup bør testast på annan kompatibel hardware.
- [x] Seed-backup manglar eller er øydelagd → vis at PROTOKOLL 3: Nøkkeltap skal aktiverast.
- [x] Adresseverifisering feilar → vis at adressa bør kontrollerast mot BSMS og testast på nytt.
- [x] Programvare støttar ikkje lenger hardware → vis at alternativ programvare/løysing bør vurderast.
- [x] BIP327-status er positiv → vis at framtidig BIP327-oppgradering kan vurderast.
- [x] SLIP39-status er positiv → vis at framtidig SLIP39-aktivering kan vurderast.
- [x] KI-status `SÅRBAR` → vis at firmware-/sikkerheitsproblem må følgjast opp.
- [x] KI-status `KOMPROMITTERT` → vis at nøkkeltapsprosedyre må følgjast.
- [x] Kontaktinfo er ikkje stadfesta → vis at kontaktinformasjon må oppdaterast i den eksterne dokumentasjonen.

Appen skal ikkje automatisk utføre nokon av desse tiltaka.

---

# 8. Dashboard

Dashboardet skal vere enkelt.

- [x] Vis 2-av-3 oppsettet.
- [ ] Vis status for nøkkel 1.
- [ ] Vis status for nøkkel 2.
- [ ] Vis status for nøkkel 3.
- [x] Vis dato for siste health check.
- [x] Vis neste health check.
- [x] Vis aktive varsel.
- [x] Knapp: `Start årleg health check`.
- [x] Knapp/lenke: `Historikk`.

---

# 9. Historikk

- [x] Vis alle gjennomførte health checks kronologisk.
- [x] Opne ein health check i read-only-visning.
- [x] Vis dato.
- [x] Vis neste sjekk.
- [x] Vis status per nøkkel.
- [x] Vis programvarestatus.
- [x] Vis BIP327/SLIP39-resultat.
- [x] Vis KI-status.
- [x] Vis kommentarar.
- [x] Gamle health checks skal ikkje overskrivast når ein ny blir registrert.

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

- [x] Implementer SQLite.
- [x] Implementer database-initialisering/migrering.
- [x] Implementer lagring av nøklar.
- [x] Implementer lagring av health checks.
- [x] Implementer historikk.
- [x] Implementer varsellogikken.
- [ ] Implementer rapporteksport.
- [x] Implementer health endpoint.

Minimum:

- [x] `GET /health`
- [x] `GET /api/keys`
- [x] `GET /api/health-checks`
- [x] `GET /api/health-checks/:id`
- [x] `POST /api/health-checks`
- [ ] `GET /api/export`

---

# 12. Frontend

- [x] Lag enkel responsiv web-UI.
- [x] Prioriter enkelheit framfor grafisk kompleksitet.
- [x] Bruk tydelege statusfelt.
- [x] Bruk faste val der status skal vere ein avgrensa verdi.
- [x] Vis problem tydeleg.
- [x] Vis kva som står att før ein health check kan lagrast.
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

- [x] Ingen seed phrase i database.
- [x] Ingen private keys i database.
- [x] Ingen wallet-passord i database.
- [x] Ingen sky-passord eller tokens i database.
- [x] Ingen unødvendige personopplysningar.
- [x] Kontaktinfo blir berre registrert som verifisert/ikkje verifisert.
- [x] Valider input på serveren.
- [x] Bruk parameteriserte SQL-spørringar.
- [x] Ikkje implementer eigen kryptografi.
- [x] Ikkje send data til eksterne tenester i MVP.

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

Utfør oppgåvene i denne rekkjefølgja og ikkje hopp fram til avanserte funksjonar:

- [x] 1. Opprett grunnleggande web-app.
- [x] 2. Opprett SQLite og datamodellen.
- [x] 3. Implementer dei tre faste nøklane.
- [x] 4. Implementer health check-skjemaet.
- [x] 5. Implementer lagring og historikk.
- [x] 6. Implementer varsellogikken.
- [ ] 7. Implementer dashboard.
- [ ] 8. Implementer rapporteksport.
- [ ] 9. Implementer StartOS package.
- [ ] 10. Implementer persistent storage og backup.
- [ ] 11. Test restart og restore.
- [ ] 12. Bygg endeleg `.s9pk` og gjer første release.

**Hovudregel:** Bygg den minste løysinga som oppfyller lista over. Ikkje legg til nye funksjonar, tenester eller arkitektur utan at dei er nødvendige for punkta i denne TODO-lista.

---

# 19. Ny avgjerd: registrering per nøkkel

Denne delen er den nyaste avgjerda og overstyrer motstridande krav ovanfor om at alle nøklane eller alle produkta må registrerast i same innsending. Eksisterande historiske data skal bevarast.

## Kvar innsending

- [ ] Ei innsending skal registrere kontrollen av éin vald nøkkel, ikkje alle tre samtidig.
- [ ] Brukaren skal velje nøkkel 1 (SeedSigner), nøkkel 2 (Blockstream Jade) eller nøkkel 3 (Nunchuk).
- [ ] Alle nøkkelkontrollar og nøkkelnotat i innsendinga skal gjelde berre den valde nøkkelen.
- [ ] Brukaren vel sjekkdato. Neste sjekkdato skal automatisk vere eitt kalenderår etter sjekkdatoen, skal ikkje vere redigerbar i skjemaet, og skal reknast/validerast på serveren.
- [ ] Kontaktstadfesting og overordna kommentar skal framleis kunne registrerast per innsending.

## Programvarekompatibilitet

- [ ] Brukaren skal velje éi wallet-programvare: Sparrow eller Nunchuk.
- [ ] Registrer kompatibilitetsstatus og versjonen til den valde programvara for den valde nøkkelen.
- [ ] Fjern dei separate Sparrow- og Nunchuk-versjonsfelta.

## BIP327 / SLIP39

- [ ] Registrer berre BIP327-status og SLIP39-status for den valde nøkkelen/produktet i kvar innsending.
- [ ] Fjern «Version checked», «Date checked» og «Notes or source» frå denne delen.
- [ ] Ikkje krev status for dei andre nøklane/produkta i same innsending.

## Security status

- [ ] SeedSigner-status skal berre følgje registreringar av nøkkel 1.
- [ ] Blockstream Jade-status skal berre følgje registreringar av nøkkel 2.
- [ ] Nunchuk- og Sparrow-status skal følgje kvar registrering, sidan dei også er wallet-programvare.
- [ ] Ha berre éin Nunchuk-status per innsending. Ved nøkkel 3 gjeld den statusen Nunchuk-programvara og Nunchuk-nøkkelen; ikkje lag to dupliserte statusfelt.
- [ ] Vis og krev berre security status-felt som er relevante for vald nøkkel og programvare. Ikkje krev status for alle tre nøklane i éi innsending.

## Lagring, historikk og verifikasjon

- [ ] Knytt nøkkelsjekk, programvarekompatibilitet, BIP327/SLIP39 og relevante security status-resultat til same innsending og vald nøkkel.
- [ ] Oppdater historikkdetaljen slik at han tydeleg viser vald nøkkel og tilhøyrande resultat.
- [ ] Bevar eksisterande lagra registreringar; bruk trygg, bakoverkompatibel databasemigrering dersom datamodellen må endrast.
- [ ] Oppdater servervalidering og testar: ei innsending skal krevje éin konfigurert nøkkel og gyldige, relevante resultat, og avvise manglande eller dupliserte nøkkel-/produktregistreringar og ugyldige programvareval.
- [ ] Test registrering av kvar nøkkel, automatisk neste dato, relevante programvare- og security status-resultat, og at eldre historikk framleis kan lesast.
