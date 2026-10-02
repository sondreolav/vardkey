# TODO — Helsesjekk for StartOS 0.4.0

## Mål

Bygg ein **enkel lokal web-app** som køyrer som ein StartOS 0.4.0-service.

Appen skal hjelpe éin brukar å gjennomføre og dokumentere ein årleg health check av eit fast **2-av-3 multisig-oppsett** med tre nøklar:

- Nøkkel 1: SeedSigner
- Nøkkel 2: Blockstream Jade
- Nøkkel 3: sky-nøkkel hos Nunchuk

Appen skal **berre registrere resultat og historikk**. Han skal ikkje signere Bitcoin-transaksjonar, handtere private nøklar eller utføre wallet-operasjonar.

Denne `TODO.md` er det einaste kravgrunnlaget du treng for MVP.

**Om dokumentet:** §1–§18 er kravspecen og gjeld som han står. §19–§22 er avgjerder som vart vedtekne undervegs, alle implementerte og verifiserte, og som er innarbeidde i §1–§18. Dei står att nedst som ein kort historikk over kva som vart endra og kvifor.

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
- [x] Rapporteksport i CSV-format.
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

**Merk:** denne lista er eit varig forbod, ikkje ei oppgåveliste. Punkta blir difor ikkje kryssa av, men skal stadfestast på nytt før release.

---

# 2. Viktige reglar for appen

- [x] Appen skal aldri spørje etter seed phrase, private keys, PIN, passord eller wallet-hemmeligheiter.
- [x] Appen skal aldri lagre slike hemmelegheiter, og ikkje lagre kontaktinnhald.
- [x] Kontaktinformasjon til nøkkelhaldarar skal ikkje lagrast; berre om kontaktinfo er verifisert.
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
- [x] Ikkje bygg generell støtte for mange oppsett enno.
- [ ] La brukaren gi nøklane lesbare namn dersom ønskjeleg. (Avgjort: ikkje no — faste namn er nok for MVP.)

---

# 4. Datamodell

SQLite med så få tabellar som mogleg. Kvar tabell har éi rad per kolonne her; kolonnar merkte `*` er legacy-kolonnar som berre finst for gamle rader og aldri blir skrivne på nytt.

**`keys`** — dei tre faste nøklane.
`id`, `key_number` (1–3), `name`, `type` (`hardware`/`cloud`), `device` (SeedSigner / Blockstream Jade / Nunchuk), `created_at`.

**`health_checks`** — éi rad per innsending, som gjeld éin vald nøkkel (§19).
`id`, `checked_at`, `next_check_due`, `wallet_software`, `software_version`, `software_compatibility_status`, `sparrow_version*`, `nunchuk_version*`, `software_comments`, `contact_info_verified`, `comments`.

**`key_checks`** — eitt record for den valde nøkkelen i kvar innsending.
`id`, `health_check_id`, `key_id`, `available`, `hardware_works`, `firmware_version`, `seed_backup_verified`, `cloud_health_status`, `cloud_provider_operational`, `address_path_verified`, `address_path`, `comments`.

**`tool_checks`** — BIP327/SLIP39, maks to rader per innsending (§19).
`id`, `health_check_id`, `product`, `bip327_status`, `slip39_status`, `version*`, `checked_at*`, `notes*`.

**`ai_security_checks`** — KI-sikkerheitsstatus per leverandør.
`id`, `health_check_id`, `provider`, `status`, `comments`.

Reglar:

- [x] `hardware_works`, `firmware_version` og `seed_backup_verified` er berre relevante for nøkkel 1 og 2.
- [x] `cloud_health_status` og `cloud_provider_operational` er berre relevante for nøkkel 3, og blir ikkje spurt om (§20).
- [x] `seed_backup_verified` og `address_path_verified` har berre verdiane `OK` eller `PROBLEM`, og er obligatoriske når `available` er Ja.
- [x] `address_path` lagrar den verifiserte adressestien.
- [x] Når `available` er Nei, blir dei andre nøkkelfelta tømde, medan nøkkelnotatet blir behalde. For nøkkel 3 blir dei to cloud-felta likevel lagra, utleidde (§20).
- [x] `seed_backup_status`, `address_verified` og `derivation_height` er fjerna (§19).
- [x] Når `available` er Nei, blir `wallet_software`, `tool_checks` og `ai_security_checks` ikkje registrerte i det heile (§22).

---

# 5. Statusverdiar

- [x] Generelle kontrollar brukar `OK`, `PROBLEM` eller `NOT_ASSESSED`.
- [x] `seed_backup_verified` og `address_path_verified` brukar berre `OK` eller `PROBLEM`.
- [x] BIP327- og SLIP39-statusane brukar `YES`, `NO` eller `NOT_ASSESSED` (§21).
- [x] KI-sikkerheitsstatus brukar nøyaktig `SECURE`, `PATCHED`, `VULNERABLE` og `COMPROMISED`. Ingen andre.
- [x] Same statuslogikk i database, validering, varsel, CSV-eksport og UI.
- [x] Ikkje bland saman «ikkje vurdert» og eit faktisk negativt resultat.

---

# 6. Årleg health check — steg for steg

## Steg 1 — Start kontroll

- [x] Brukaren trykkjer `Start årleg health check` og vel kva nøkkel innsendinga gjeld (§19).
- [x] `Availability` er obligatorisk: Ja eller Nei (§22).
- [x] Dagens dato blir føreslått automatisk.
- [x] Neste sjekkdato blir rekna ut på serveren som eitt kalenderår etter sjekkdatoen, og kan ikkje redigerast i skjemaet.

## Steg 2 — Nøkkel 1: SeedSigner

- [x] Tilgjengeleg / ikkje tilgjengeleg.
- [x] Hardware fungerer / fungerer ikkje.
- [x] Registrer firmware-versjon.
- [x] Seed-backup intakt og stemmer med hardware → `seed_backup_verified` (`OK` / `PROBLEM`).
- [x] Verifiser adresse, derivasjonshøgd og adresse-sti → `address_path_verified` (`OK` / `PROBLEM`) og `address_path`.
- [x] Kommentar ved behov.
- [x] Når nøkkelen ikkje er tilgjengeleg, blir resten skjult og ikkje kravd (§22).

## Steg 3 — Nøkkel 2: Blockstream Jade

- [x] Same kontrollar som for nøkkel 1: tilgjengeleg, hardware fungerer, firmware-versjon, seed-backup (`seed_backup_verified`), adresse og sti (`address_path_verified`, `address_path`), kommentar.
- [x] Når nøkkelen ikkje er tilgjengeleg, blir resten skjult og ikkje kravd (§22).

## Steg 4 — Nøkkel 3: Nunchuk sky-nøkkel

- [x] Berre `Availability` blir spurt om. Cloud-helse og «leverandøren er i drift» blir utleidde frå han (§20).
- [x] Verifiser relevant adresse/oppsett → `address_path_verified` (`OK` / `PROBLEM`) og `address_path`.
- [x] Kommentar ved behov.

## Steg 5 — Programvare-kompatibilitet

- [x] Brukaren vel éi wallet-programvare: `Sparrow Wallet` eller `Nunchuk`. Nøkkel 3 er låst til Nunchuk.
- [x] Registrer versjonen til den valde programvara i `software_version`.
- [x] Registrer `OK` eller `PROBLEM`, med kommentar ved problem.
- [x] For nøkkel 3 er feltet skjult og utleidd (§20).
- [x] Når nøkkelen ikkje er tilgjengeleg, er feltet skjult og valfritt (§22).

## Steg 6 — BIP327 / SLIP39

- [x] Registrer `bip327_status` og `slip39_status` for nøkkelproduktet og den valde programvara: maks to rader, utan duplikat, og éi rad for nøkkel 3.
- [x] Verdiane er `YES`, `NO` eller `NOT_ASSESSED` (§21).
- [x] «Version checked», «Date checked» og «Notes or source» er tekne ut.
- [x] Når nøkkelen ikkje er tilgjengeleg, blir ingen rader registrerte (§22).

## Steg 7 — KI-sikkerheitsstatus

- [x] Leverandørar per innsending: nøkkel 1 → SeedSigner, Sparrow Wallet, Nunchuk. Nøkkel 2 → Blockstream Jade, Sparrow Wallet, Nunchuk. Nøkkel 3 → Nunchuk åleine.
- [x] Registrer status (`SECURE` / `PATCHED` / `VULNERABLE` / `COMPROMISED`) og ein kort kommentar.
- [x] For nøkkel 1 og 2 blir berre nøkkelproduktet og den valde programvara vist; den tredje leverandøren blir vidareført (§20).
- [x] Når nøkkelen ikkje er tilgjengeleg, blir ingen statusar registrerte (§22).
- [x] Appen kontaktar ikkje KI sjølv i MVP.

## Steg 8 — Kontaktinfo

- [x] Stadfest at kontaktinformasjonen til alle nøkkelhaldarane er gyldig, og lagre berre Ja / Nei.
- [x] Ikkje lagre namn, telefonnummer, e-post eller anna kontaktinnhald.

## Steg 9 — Kommentar

- [x] Eitt overordna kommentarfelt for observasjonar, og eigne kommentarar per nøkkel der det trengst.

## Steg 10 — Oppsummering

- [x] Før lagring viser appen alle kontrollpunkt, alle problem, alle manglande kontrollar, neste sjekkdato, handlingar som bør følgjast opp, og utleidde eller vidareførte verdiar merkte som nettopp det (§20).
- [x] Brukaren må trykkje `Lagre health check` for å lagre kontrollen.

---

# 7. Varsel og oppfølging

- [x] Nøkkel ikkje tilgjengeleg → kritisk varsel om at nøkkelen må bytast ut før ein går vidare, og at resten av nøkkelfelta ikkje kan registrerast. For nøkkel 3 eitt samanslått varsel som òg nemner at leverandøren er registrert som nede (§20).
- [x] Hardware fungerer ikkje → seed-backupen bør testast på annan kompatibel hardware.
- [x] Seed-backup manglar eller er øydelagd → PROTOKOLL 3: Nøkkeltap skal aktiverast. Skal ikkje utløysast når nøkkelen er utilgjengeleg.
- [x] Cloud-helse `PROBLEM` eller leverandøren ute av drift → leverandørstatusen bør kontrollerast før ein går vidare. Skal ikkje utløysast når nøkkelen er utilgjengeleg.
- [x] Adresseverifisering feilar → adressa bør kontrollerast mot BSMS og testast på nytt. Skal ikkje utløysast når nøkkelen er utilgjengeleg.
- [x] Programvare støttar ikkje lenger hardware → alternativ programvare eller løysing bør vurderast.
- [x] BIP327-status `YES` → framtidig BIP327-oppgradering kan vurderast (§21).
- [x] SLIP39-status `YES` → framtidig SLIP39-aktivering kan vurderast (§21).
- [x] KI-status `VULNERABLE` → firmware- eller sikkerheitsproblemet må følgjast opp.
- [x] KI-status `COMPROMISED` → nøkkeltapsprosedyren må følgjast.
- [x] Kontaktinfo ikkje stadfesta → kontaktinformasjonen må oppdaterast i den eksterne dokumentasjonen.
- [x] Kritiske varsel blir lista før informative. Like varsel (same `code` og `source`) blir slegne saman, og berre den nyaste blir vist (§21).
- [x] Appen utfører aldri desse tiltaka sjølv.

---

# 8. Dashboard

- [x] Vis 2-av-3-oppsettet og status for kvar av dei tre nøklane.
- [x] Vis siste sjekk og neste forfall per nøkkel — kvar nøkkel har sitt eige intervall (§19).
- [x] Oversiktskort «Next check» (tidlegaste forfall, med kva nøkkel det gjeld) og «Attention» (kor mange nøklar som har passert fristen). Om ein dato er passert blir avgjort i nettlesaren.
- [x] Vis alle aktive varsel, med kva registrering kvart varsel kjem frå (§21).
- [x] Knapp `Start årleg health check`, lenke `Historikk` og lenke `Download CSV`.

---

# 9. Historikk

- [x] Vis alle gjennomførte health checks kronologisk, nyaste først, med kva nøkkel kvar innsending gjeld (§19).
- [x] Opne ein health check i read-only-visning med dato, neste sjekk, status per nøkkel, programvare og versjon, BIP327/SLIP39, KI-status og kommentarar.
- [x] Gamle health checks blir aldri overskrivne.

---

# 10. Rapporteksport

- [x] `GET /api/export` gjev rein CSV (UTF-8, komma, CRLF, header). Ingen XLSX, og appen lovar ikkje Excel-kompatibilitet.
- [x] Éi rad per nøkkelsjekk. Kolonnen `Check id` knyter saman rader frå same innsending.
- [x] Inneheld dato, neste sjekk, nøkkelstatus, hardware/firmware, seed/cloud-resultat, adresse-sti, programvare og kompatibilitet, BIP327/SLIP39, KI-status, kontaktstadfesting og kommentarar.
- [x] Resultat med meir enn éin verdi per innsending ligg i éi celle som `SeedSigner: YES; Sparrow Wallet: NO`.
- [x] Statusverdiane blir skrivne slik dei er lagra (§21).

---

# 11. Backend

- [x] SQLite med initialisering og migrering. Skjemaet er no versjon 6 (§21).
- [x] Lagring av nøklar, health checks, historikk og rapporteksport.
- [x] Varsellogikken (§7).
- [x] Health endpoint.

Minimumsendepunkt:

- [x] `GET /health`
- [x] `GET /api/keys`
- [x] `GET /api/health-checks`
- [x] `GET /api/health-checks/:id`
- [x] `POST /api/health-checks`
- [x] `GET /api/export`

**Merk:** `GET /api/key-status`, `GET /api/previous-values` og `GET /api/alerts` er ekstra endepunkt utanom minimumslista, fordi dashboardet og skjemaet treng dei. Dei står ikkje i spesifikasjonen enno.

- [x] `POST /api/health-checks` krev éin konfigurert nøkkel, `available` og gyldige, relevante resultat, og avviser manglande eller dupliserte registreringar (§22).
- [x] `POST /api/health-checks` krev ikkje programvare, standardar eller KI-status når nøkkelen er utilgjengeleg (§22).

---

# 12. Frontend

- [x] Enkel responsiv web-UI. Enkelheit går framfor grafisk kompleksitet.
- [x] Tydlege statusfelt, og faste val der statusen skal vere ein avgrensa verdi.
- [x] Vis problem tydeleg.
- [x] Vis kva som står att før ein health check kan lagrast.
- [x] Skjul felt som ikkje gjeld for vald nøkkel eller vald programvare (§20, §21).
- [x] Skjul programvare, standardar og KI-status når nøkkelen er utilgjengeleg (§22).
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

**Merk:** denne lista er eit varig forbod, ikkje ei oppgåveliste. Punkta blir difor ikkje kryssa av, men skal stadfestast på nytt før release.

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

- [x] Ingen seed phrase, private keys, wallet-passord eller sky-tokens i databasen.
- [x] Ingen unødvendige personopplysningar. Kontaktinfo blir berre registrert som verifisert / ikkje verifisert.
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
- [ ] Test KI-status `VULNERABLE`.
- [ ] Test KI-status `COMPROMISED`.
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
- [ ] KI-status kan registrerast som SECURE, PATCHED, VULNERABLE eller COMPROMISED.
- [ ] Kontaktinfo kan verifiserast utan å lagre kontaktinformasjonen.
- [ ] Problem gir tydelege varsel.
- [ ] Neste sjekk blir lagra.
- [ ] Historikk fungerer.
- [ ] CSV-rapport kan eksporterast.
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
- [x] 7. Implementer dashboard.
- [x] 8. Implementer rapporteksport.
- [ ] 9. Implementer StartOS package.
- [ ] 10. Implementer persistent storage og backup.
- [ ] 11. Test restart og restore.
- [ ] 12. Bygg endeleg `.s9pk` og gjer første release.

**Merk:** steg 4, 5 og 6 vart først fullførte før §19 vart vedteken, og gjorde på nytt etterpå. Steg 4 og 6 vart kryssa av då §22 var verifisert.

**Testar:** 123 grøne testar etter §22. Køyr `python3 -m unittest discover -s tests`.

**Hovudregel:** Bygg den minste løysinga som oppfyller lista over. Ikkje legg til nye funksjonar, tenester eller arkitektur utan at dei er nødvendige for punkta i denne TODO-lista.

---

# 19. Avgjerd (implementert og verifisert): registrering per nøkkel

Overstyrer kravet om at alle nøklane må registrerast i same innsending. Eksisterande historiske data er bevarte. Endra §4, §6, §7, §8, §9, §10 og §11.

- [x] Ei innsending gjeld kontrollen av **éin vald nøkkel**, ikkje alle tre.
- [x] Alle nøkkelkontrollar og nøkkelnotat i innsendinga gjeld berre den valde nøkkelen.
- [x] Brukaren vel sjekkdato. Neste sjekkdato blir rekna på serveren som eitt kalenderår etterpå, og kan ikkje redigerast.
- [x] Brukaren vel éi wallet-programvare: `Sparrow Wallet` eller `Nunchuk`. Nøkkel 3 er låst til Nunchuk. Eitt programvarefelt og eitt versjonsfelt erstattar dei separate versjonsfelta.
- [x] BIP327/SLIP39 blir registrert for nøkkelproduktet pluss vald programvare, utan duplikat: maks to rader, éi rad for nøkkel 3.
- [x] Security status følgjer vald nøkkel: nøkkelproduktet og vald programvare, og for nøkkel 3 berre Nunchuk — éin gong.
- [x] `seed_backup_verified` (nøkkel 1 og 2) og `address_path_verified` er `OK`/`PROBLEM` og obligatoriske når nøkkelen er tilgjengeleg.
- [x] `seed_backup_status`, `address_verified` og `derivation_height` er fjerna. Sjekkpunktet «Verifiser derivasjonshøgd» blir dekt av `address_path`.
- [x] Migreringa er bakoverkompatibel, og eldre historikk blir framleis vist.

---

# 20. Avgjerd (implementert og verifisert): skjulte felt som blir utleidde eller vidareførte

Endra §4, §6 (steg 4, 5, 7 og 10), §7, §11 og §19.

- [x] Nøkkel 3 samlar berre `Availability`. `Cloud health check` og `Provider operational` er fjerna frå skjemaet og blir utleidde: Ja → `cloud_health_status` = `OK` og `cloud_provider_operational` = 1; Nei → `PROBLEM` og 0. Ubesvart → begge tomme.
- [x] `Software compatibility` for nøkkel 3 er skjult og utleidd: Ja → `OK`, Nei → `NOT_ASSESSED`. Nøkkel 3 kan difor ikkje lenger gi varselet `software_incompatible`.
- [x] For nøkkel 1 og 2 viser `Security status` berre nøkkelproduktet og vald programvare. Den tredje leverandøren er skjult og får siste lagra status — men blir synleg att om den statusen var `VULNERABLE` eller `COMPROMISED`. Manglar han tidlegare status, startar han som `SECURE`.
- [x] Dei skjulte verdiane blir framleis sende inn, slik at POST-kontrakten, historikken og eksporten er uendra.
- [x] `Firmware version` og `Address path` viser førre lagra verdi som placeholder. `Software version` viser førre verdi berre når same programvare er vald no.
- [x] Alle utleidde og vidareførte verdiar blir lista i Review-oppsummeringa, merkte som utleidde eller vidareførte.
- [x] Når nøkkel 3 er utilgjengeleg, kjem det **eitt** samanslått kritisk varsel: «This key was not available and the cloud provider is recorded as not operating. Check the provider status and replace the key before continuing; the remaining checks for this key cannot be recorded.»
- [x] `cloud_provider_problem` held fram for rader der nøkkelen var tilgjengeleg (gamle rader).
- [x] Kolonnane `cloud_health_status`, `cloud_provider_operational` og `software_compatibility_status` er behaldne for gamle rader.

---

# 21. Avgjerd (implementert og verifisert): engelske statusverdiar, adressesti og alle varsel

Endra §4, §5, §6 (steg 2, 3 og 6), §7, §8, §10, §11 og §12.

- [x] `IKKJE_VURDERT` er bytt til `NOT_ASSESSED` på alle fire kolonnane som brukar han: `health_checks.software_compatibility_status`, `key_checks.cloud_health_status`, `tool_checks.bip327_status` og `tool_checks.slip39_status`.
- [x] BIP327- og SLIP39-statusane har verdiane `YES`, `NO` og `NOT_ASSESSED` i staden for `OK`, `PROBLEM` og `IKKJE_VURDERT`. Berre `YES` utløyser varsel; eit rapportert `NO` er eit negativt resultat og gir ingen.
- [x] Migreringa mappar gamle rader: `OK` → `YES`, `PROBLEM` → `NO`, `IKKJE_VURDERT` → `NOT_ASSESSED`. Skjemaet går til versjon 6.
- [x] Kvar råka tabell blir bygd opp att etter den dokumenterte SQLite-prosedyren. `health_checks` er ein foreldretabell, så migreringa køyrer med `PRAGMA foreign_keys = OFF`, sjekkar `PRAGMA foreign_key_check` før commit og rullar tilbake ved feil.
- [x] Skjemaval, validering, varsel, CSV-eksport og testar brukar dei nye verdiane.
- [x] `Address path` blir berre vist og lagra når `Address path verified` er `OK`; elles er feltet skjult og tømt.
- [x] `GET /api/alerts` summerer varsla frå alle lagra kontrollar, ikkje berre den siste. Kvart varsel har med `check_id` og `checked_at`.
- [x] Like varsel (same `code` og `source`) blir slegne saman, og berre den nyaste blir vist, med datoen sin.
- [x] Varsla blir lista med dei kritiske først, og deretter nyaste først. Framsida viser alle varsla frå endepunktet.
- [x] Produktnamnet «Helsesjekk» og databasefilnamnet `data/helsesjekk.sqlite3` er behaldne og dokumenterte som bevisste unntak frå engelskregelen i `README.md`.
- [ ] Framtidig, ikkje no: varsel om at oppsettet kan oppgraderast når alle nøklar og all programvare svarar `YES` på anten BIP327 eller SLIP39. Krev at appen ser på tvers av alle registreringar.
- [ ] Framtidig, ikkje no: ein måte å lukke eller kvittere ut varsel på.

---

# 22. Avgjerd (implementert og verifisert): utilgjengeleg nøkkel gjer resten valfritt

Vedteken etter §21. Endra §4 (reglane for `key_checks`), §6 (steg 1, 5, 6 og 7), §7, §11 og §12.

**Bakgrunn:** fram til no kravde skjemaet `Wallet software` og alle `Security status`-felta, og serveren kravde `wallet_software`, `tool_checks` og `ai_security_checks`. Når nøkkelen ikkje er tilgjengeleg, finst det ingenting å registrere, så innsendinga vart blokkert utan grunn. Ei innsending som berre seier at nøkkelen mangla, er eit fullgodt resultat og skal gi varselet `key_unavailable`.

## Availability blir obligatorisk

- [x] `Availability` har berre verdiane Ja og Nei. «Not assessed» er ikkje eit alternativ.
- [x] Serveren krev `available` og avviser ein POST utan det med `400`.

## Når nøkkelen ikkje er tilgjengeleg

- [x] `Software compatibility`, `BIP327 and SLIP39 support` og `Security status` er skjulte i skjemaet og blir ikkje kravde.
- [x] Innsendinga treng berre `Availability`, nøkkelnotat, kontaktstadfesting og overordna kommentar.
- [x] `wallet_software`, `tool_checks` og `ai_security_checks` er tomme. Er dei ikkje tomme, avviser serveren med `400` — data blir ikkje kasta i det stille.
- [x] `software_compatibility_status` kan utelatast og blir då lagra som `NOT_ASSESSED`.
- [x] Det blir ikkje lagra `tool_checks`- eller `ai_security_checks`-rader, og `wallet_software` er `NULL`.
- [x] Nøkkel 3 held fram med å lagre dei utleidde cloud-verdiane sine (§20) og gir det samanslåtte kritiske varselet (§7).

## Uendra

- [x] Varselet er framleis `key_unavailable`; det er sjølve poenget med innsendinga.
- [x] Databasen kravde ingen kolonneendring, og skjemaet held fram som versjon 6.
- [x] Historikk og CSV viser tomt for dei felta som ikkje er registrerte.
- [x] Når nøkkelen er tilgjengeleg, er krava uendra.
- [x] Kontaktstadfesting og overordna kommentar er framleis valfrie felt.

**Merknad:** ein `required`-kontroll inne i ein skjult container blir framleis validert av nettlesaren, så dei tre delane teiknar eit tomt-notat i staden for påkravde felt når nøkkelen er utilgjengeleg. Elles ville skjemaet sett rett ut, men ikkje kunne lagrast.
