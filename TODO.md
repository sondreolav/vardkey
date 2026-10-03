# TODO — Helsesjekk for StartOS 0.4.0

## Mål

Bygg ein **enkel lokal web-app** som køyrer som ein StartOS 0.4.0-service.

Appen skal hjelpe éin brukar å gjennomføre og dokumentere ein årleg health check av eit **2-av-3 multisig-oppsett** med tre nøklar (namn og type blir konfigurerte ved første oppstart, §23.2):

- Nøkkel 1: SeedSigner
- Nøkkel 2: Blockstream Jade
- Nøkkel 3: sky-nøkkel hos Nunchuk

Appen skal **berre registrere resultat og historikk**. Han skal ikkje signere Bitcoin-transaksjonar, handtere private nøklar eller utføre wallet-operasjonar.

Denne `TODO.md` er det einaste kravgrunnlaget du treng for MVP.

**Om dokumentet:** §1–§18 er kravspecen og gjeld som han står. Fire avgjerder vart tekne undervegs, alle implementerte og verifiserte, og er innarbeidde i §1–§18; dei står att som eit kort vedlegg i §19–§22. §23 er konfigurerbart nøkkeloppsett, implementert og verifisert. §24 er avtalt arbeid som **ikkje er implementert**, og som skal gjerast før steg 9–12 i §18. Den fulle grunngjevinga for kvar avgjerd ligg i git-historikken.

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

**Merk:** denne lista er eit varig forbod, ikke ei oppgåveliste. Punkta blir difor ikkje kryssa av, men skal stadfestast på nytt før release.

---

# 2. Viktige reglar for appen

- [x] Appen skal aldri spørje etter seed phrase, private keys, PIN, passord eller wallet-hemmeligheiter.
- [x] Appen skal aldri lagre slike hemmelegheiter, og ikkje lagre kontaktinnhald.
- [x] Kontaktinformasjon til nøkkelhaldarar skal ikkje lagrast; berre om kontaktinfo er verifisert.
- [x] Appen skal ikkje late som han sjølv har utført ein hardware-test. Brukaren registrerer resultatet av testen.
- [x] Appen skal vere lokal og enkel.
- [x] Dersom noko ikkje er nødvendig for den årlege health check-en, skal det ikkje byggjast i MVP.

---

# 3. Nøkkeloppsettet appen er bygd for

Appen er bygd for eitt 2-av-3 multisig-oppsett. Tabellen under viser standardoppsettet:

| Nøkkel | Type | Einheit |
|---|---|---|
| 1 | Hardware | SeedSigner |
| 2 | Hardware | Blockstream Jade |
| 3 | Cloud | Nunchuk |

- [x] Vis 2-av-3 som oppsettet i dashboardet.
- [x] Ha tre nøkkelprofilar, éin for kvar nøkkel.
- [x] Ikkje bygg generell støtte for mange oppsett enno.
- [x] La brukaren gi nøklane lesbare namn dersom ønskjeleg. (Avgjort: ja, via §23.2 — brukaren gir namn og type ved første oppstart, og dei er låste etterpå.)

**Merk:** §23.2 erstattar det faste oppsettet i denne seksjonen: kvar nøkkel blir konfigurert ved første oppstart, og namnet brukaren skriv, blir produktnamnet. Tabellen over viser standardoppsettet appen vart bygd for.

---

# 4. Datamodell

SQLite med så få tabellar som mogleg. Kvar tabell har éi rad per kolonne her; kolonnar merkte `*` er legacy-kolonnar som berre finst for gamle rader og aldri blir skrivne på nytt.

**`keys`** — dei tre nøkkelplassane.
`id`, `key_number` (1–3), `name`, `type` (`hardware`/`cloud`), `created_at`.

**`health_checks`** — éi rad per innsending, som gjeld éin vald nøkkel (§19).
`id`, `checked_at`, `next_check_due`, `wallet_software`, `software_version`, `software_compatibility_status`, `sparrow_version*`, `nunchuk_version*`, `software_comments`, `contact_info_verified`, `comments`.

**`key_checks`** — eitt record for den valde nøkkelen i kvar innsending.
`id`, `health_check_id`, `key_id`, `available`, `hardware_works`, `firmware_version`, `seed_backup_verified`, `cloud_health_status`, `cloud_provider_operational`, `address_path_verified`, `address_path`, `comments`.

**`ai_security_checks`** — KI-sikkerheitsstatus per leverandør.
`id`, `health_check_id`, `provider`, `status`, `comments`.

Reglar:

- [x] `hardware_works`, `firmware_version` og `seed_backup_verified` er berre relevante for hardware-nøklar.
- [x] `cloud_health_status` og `cloud_provider_operational` er berre relevante for cloud-nøklar, og blir ikkje spurt om (§20).
- [x] `seed_backup_verified` og `address_path_verified` har berre verdiane `OK` eller `PROBLEM`, og er obligatoriske når `available` er Ja.
- [x] `address_path` lagrar den verifiserte adressestien.
- [x] Når `available` er Nei, blir dei andre nøkkelfelta tømde, medan nøkkelnotatet blir behalde. For ein cloud-nøkkel blir dei to cloud-felta likevel lagra, utleidde (§20).
- [x] `seed_backup_status`, `address_verified` og `derivation_height` er fjerna (§19).
- [x] Når `available` er Nei, blir `wallet_software` og `ai_security_checks` ikkje registrerte i det heile (§22).
- [x] `name` og `type` i `keys` blir lagra éin gong ved første oppstart og er låste etterpå (§23.2).
- [x] `provider` lagrar det konfigurerte nøkkelnamnet og den valde programvara, ikkje faste produktnamn (§23.3).
- [x] `wallet_software` og `contact_info_verified` er fri tekst; dei faste listene er fjerna (§23.1, §23.3).
- [x] `device`-kolonnen er fjerna; det konfigurerte namnet er den einaste produktetikketten (§23.2).
- [ ] `hardware_works` er obligatorisk (`0` eller `1`) for ein tilgjengeleg hardware-nøkkel (§24.1).
- [ ] `contact_info_verified` er obligatorisk og har ingen «not assessed»-verdi (§24.1).
- [ ] `tool_checks`-tabellen er fjerna (§24.2, §24.4).

---

# 5. Statusverdiar

- [x] Generelle kontrollar brukar `OK`, `PROBLEM` eller `NOT_ASSESSED`.
- [x] `seed_backup_verified` og `address_path_verified` brukar berre `OK` eller `PROBLEM`.
- [x] KI-sikkerheitsstatus brukar nøyaktig `SECURE`, `PATCHED`, `VULNERABLE` og `COMPROMISED`. Ingen andre.
- [x] Same statuslogikk i database, validering, varsel, CSV-eksport og UI.
- [x] Ikkje bland saman «ikkje vurdert» og eit faktisk negativt resultat.
- [x] Kontaktstadfesting brukar `Confirmed current` eller `Needs external update` i staden for Ja/Nei (§23.1).
- [x] `Software compatibility` krev eit aktivt val (`OK` / `PROBLEM`) for ein hardware-nøkkel (§23.1).
- [ ] `Hardware works` krev eit aktivt val (`Yes` / `No`) for ein tilgjengeleg hardware-nøkkel (§24.1).
- [ ] Kontaktstadfesting er obligatorisk og har ingen «not assessed»-verdi (§24.1).
- [ ] `NOT_ASSESSED` er berre lovleg som den utleidde verdien for `software_compatibility_status` når nøkkelen er utilgjengeleg (§24.1).
- [ ] BIP327- og SLIP39-statusane er fjerna saman med funksjonen sin (§24.2).

---

# 6. Årleg health check — steg for steg

Stega følgjer seksjonane i skjemaet.

## Steg 1 — Schedule (01 / Schedule)

- [x] Brukaren trykkjer `Start årleg health check`.
- [x] Dagens dato blir føreslått automatisk.
- [x] Neste sjekkdato blir rekna ut på serveren som eitt kalenderår etter sjekkdatoen, og kan ikkje redigerast i skjemaet.

## Steg 2 — Key (02 / Key)

- [x] Brukaren vel kva nøkkel innsendinga gjeld (§19). Ei innsending gjeld éin nøkkel.
- [x] `Availability` er obligatorisk: Ja eller Nei (§22).

### Hardware-nøkkel

- [x] Tilgjengeleg / ikkje tilgjengeleg.
- [ ] `Hardware works` er obligatorisk: Ja eller Nei (§24.1).
- [x] Registrer firmware-versjon.
- [x] Seed-backup intakt og stemmer med hardware → `seed_backup_verified` (`OK` / `PROBLEM`).
- [x] Verifiser adresse, derivasjonshøgd og adresse-sti → `address_path_verified` (`OK` / `PROBLEM`) og `address_path`.
- [x] Kommentar ved behov.
- [x] Når nøkkelen ikkje er tilgjengeleg, blir resten skjult og ikkje kravd (§22).

### Cloud-nøkkel

- [x] Berre `Availability` blir spurt om. Cloud-helse og «leverandøren er i drift» blir utleidde frå han (§20).
- [x] Verifiser relevant adresse/oppsett → `address_path_verified` (`OK` / `PROBLEM`) og `address_path`.
- [x] Kommentar ved behov.

## Steg 3 — Compatibility (03 / Compatibility)

- [x] Brukaren vel éi wallet-programvare: `Sparrow Wallet` eller namnet på ein konfigurert cloud-nøkkel. Ein cloud-nøkkel er låst til sitt eige namn (§23.3).
- [x] Registrer versjonen til den valde programvara i `software_version`.
- [x] Registrer `OK` eller `PROBLEM`, med kommentar ved problem.
- [x] For ein cloud-nøkkel er feltet skjult og utleidd (§20).
- [x] Når nøkkelen ikkje er tilgjengeleg, er feltet skjult og valfritt (§22).

## Steg 4 — External research (04 / External research)

- [x] Leverandørar per innsending: den valde nøkkelen (ved namn) og den valde programvara (§23.3).
- [x] Registrer status (`SECURE` / `PATCHED` / `VULNERABLE` / `COMPROMISED`) og ein kort kommentar.
- [x] Berre den valde nøkkelen og den valde programvara blir registrerte; vidareføringa av ein tredje leverandør (§20) er fjerna (§23.3).
- [x] Når nøkkelen ikkje er tilgjengeleg, blir ingen statusar registrerte (§22).
- [x] Appen kontaktar ikkje KI sjølv i MVP.

## Steg 5 — Contact confirmation (05 / Contact confirmation)

- [x] Stadfest at kontaktinformasjonen til nøkkelhaldaren til den valde nøkkelen er gyldig, og lagre berre statusen (§23.1).
- [ ] Stadfestinga er obligatorisk: `Confirmed current` eller `Needs external update` (§24.1). Ho blir spurt om også når nøkkelen er utilgjengeleg.
- [x] Ikkje lagre namn, telefonnummer, e-post eller anna kontaktinnhald.

## Steg 6 — Notes (06 / Notes)

- [x] Eitt overordna kommentarfelt for observasjonar, og eigne kommentarar per nøkkel der det trengst.

## Oppsummering før lagring (Review-panelet)

- [x] Før lagring viser appen alle kontrollpunkt, alle problem, alle manglande kontrollar, neste sjekkdato, handlingar som bør følgjast opp, og utleidde verdiar merkte som nettopp det (§20).
- [x] Brukaren må trykkje `Lagre health check` for å lagre kontrollen.

---

# 7. Varsel og oppfølging

- [x] Nøkkel ikkje tilgjengeleg → kritisk varsel om at nøkkelen må bytast ut før ein går vidare, og at resten av nøkkelfelta ikkje kan registrerast. For ein cloud-nøkkel eitt samanslått varsel som òg nemner at leverandøren er registrert som nede (§20).
- [x] Hardware fungerer ikkje → seed-backupen bør testast på annan kompatibel hardware.
- [x] Seed-backup manglar eller er øydelagd → PROTOKOLL 3: Nøkkeltap skal aktiverast. Skal ikkje utløysast når nøkkelen er utilgjengeleg.
- [x] Cloud-helse `PROBLEM` eller leverandøren ute av drift → leverandørstatusen bør kontrollerast før ein går vidare. Skal ikkje utløysast når nøkkelen er utilgjengeleg.
- [x] Adresseverifisering feilar → adressa bør kontrollerast mot BSMS og testast på nytt. Skal ikkje utløysast når nøkkelen er utilgjengeleg.
- [x] Programvare støttar ikkje lenger hardware → alternativ programvare eller løysing bør vurderast.
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
- [x] Vis oppsettsteget i staden for dashboardet når nøkkeloppsettet manglar (§23.2).

---

# 9. Historikk

- [x] Vis alle gjennomførte health checks kronologisk, nyaste først, med kva nøkkel kvar innsending gjeld (§19).
- [x] Opne ein health check i read-only-visning med dato, neste sjekk, status per nøkkel, programvare og versjon, KI-status og kommentarar.
- [x] Gamle health checks blir aldri overskrivne.

---

# 10. Rapporteksport

- [x] `GET /api/export` gjev rein CSV (UTF-8, komma, CRLF, header). Ingen XLSX, og appen lovar ikkje Excel-kompatibilitet.
- [x] Éi rad per nøkkelsjekk. Kolonnen `Check id` knyter saman rader frå same innsending.
- [x] Inneheld dato, neste sjekk, nøkkelstatus, hardware/firmware, seed/cloud-resultat, adresse-sti, programvare og kompatibilitet, KI-status, kontaktstadfesting og kommentarar.
- [x] Resultat med meir enn éin verdi per innsending ligg i éi celle som `SeedSigner: VULNERABLE; Sparrow Wallet: SECURE`.
- [x] Statusverdiane blir skrivne slik dei er lagra (§21).
- [x] Nøkkelnamnet og nøkkeltypen kjem frå oppsettet (§23.3).

---

# 11. Backend

- [x] SQLite med initialisering og migrering. Skjemaet er no versjon 8 (§21, §23.1, §23.4) og blir versjon 9 når §24.2 er implementert.
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

**Merk:** `GET /api/setup`, `POST /api/setup`, `GET /api/key-status`, `GET /api/previous-values` og `GET /api/alerts` er ekstra endepunkt utanom minimumslista, fordi oppsettsteget, dashboardet og skjemaet treng dei. Dei står ikkje i spesifikasjonen enno.

- [x] `POST /api/health-checks` krev éin konfigurert nøkkel, `available` og gyldige, relevante resultat, og avviser manglande eller dupliserte registreringar (§22).
- [x] `POST /api/health-checks` krev ikkje programvare eller KI-status når nøkkelen er utilgjengeleg (§22).
- [x] `POST /api/setup` lagrar nøkkeloppsettet éin gong, krev unike og ikkje-tømme namn, og avviser eit nytt oppsett med `409` (§23.2).

---

# 12. Frontend

- [x] Enkel responsiv web-UI. Enkelheit går framfor grafisk kompleksitet.
- [x] Tydlege statusfelt, og faste val der statusen skal vere ein avgrensa verdi.
- [x] Vis problem tydeleg.
- [x] Vis kva som står att før ein health check kan lagrast.
- [x] Skjul felt som ikkje gjeld for vald nøkkel eller vald programvare (§20, §21).
- [x] Skjul programvare og KI-status når nøkkelen er utilgjengeleg (§22).
- [x] Eige oppsettsteg for namn og type ved første oppstart (§23.2).
- [x] Bygg `Wallet software`-vala frå oppsettet i staden for ei fast liste (§23.3).
- [ ] Følg den nye seksjonsrekkjefølgja: 01 Schedule, 02 Key, 03 Compatibility, 04 External research, 05 Contact confirmation, 06 Notes (§24.3).
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

**Merk:** denne lista er eit varig forbod, ikke ei oppgåveliste. Punkta blir difor ikkje kryssa av, men skal stadfestast på nytt før release.

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
- [x] Ingen unødvendige personopplysningar. Kontaktinfo blir berre registrert som status (`Confirmed current` / `Needs external update`).
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
- [ ] Test at `Hardware works` krev eit val.
- [ ] Test at kontaktstadfesting krev eit val.
- [ ] Test KI-status `VULNERABLE`.
- [ ] Test KI-status `COMPROMISED`.
- [ ] Test kontaktinfo `Needs external update`.

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
- [ ] KI-status kan registrerast som SECURE, PATCHED, VULNERABLE eller COMPROMISED.
- [ ] Kontaktinfo kan verifiserast utan å lagre kontaktinformasjonen.
- [ ] Problem gir tydelege varsel.
- [ ] Neste sjekk blir lagra.
- [ ] Historikk fungerer.
- [ ] CSV-rapport kan eksporterast.
- [ ] Data overlever restart.
- [ ] Backup og restore fungerer.
- [ ] Ingen wallet-hemmelegheiter blir lagra.

---

# 18. Arbeidsrekkefølgje for AI-programmeraren

Utfør oppgåvene i denne rekkjefølgja og ikkje hopp fram til avanserte funksjonar:

- [x] 1. Opprett grunnleggande web-app.
- [x] 2. Opprett SQLite og datamodellen.
- [x] 3. Implementer dei tre nøklane.
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

**Merk:** §23 er implementert og verifisert. §24 er avtalt, men **ikkje implementert**, og skal gjerast før steg 9–12.

**Testar:** 178 grøne testar etter §23. Talet blir oppdatert når §24 er implementert og testane er grøne. Køyr `python3 -m unittest discover -s tests`.

**Hovudregel:** Bygg den minste løysinga som oppfyller lista over. Ikkje legg til nye funksjonar, tenester eller arkitektur utan at dei er nødvendige for punkta i denne TODO-lista.

---

# 19–22. Vedtekne avgjerder (implementerte og verifiserte)

Desse fire vart tekne undervegs og er no innarbeidde i §1–§18. Kvar referanse i §1–§18 peikar på avsnittet nedanfor. Den fulle grunngjevinga ligg i git-historikken. §23 endra enkelte av detaljane etterpå; det står i så fall i parentes.

**§19 — registrering per nøkkel.** Ei innsending gjeld **éin vald nøkkel**, ikkje alle tre. Brukaren vel éi wallet-programvare med eitt versjonsfelt. `seed_backup_status`, `address_verified` og `derivation_height` er fjerna. Migreringa er bakoverkompatibel, og eldre historikk blir framleis vist. (§23.3 endra vala: `Sparrow Wallet` pluss namnet på kvar cloud-nøkkel, og ein cloud-nøkkel er låst til sitt eige namn.)

**§20 — skjulte felt som blir utleidde.** Ein cloud-nøkkel samlar berre `Availability`; cloud-helse, «leverandøren er i drift» og kompatibilitet blir utleidde. Førre lagra verdi blir fylt inn i feltet. Alt utleidd blir lista i Review-oppsummeringa, merkt som nettopp det. (§23.1 gjorde den førre verdien til ein vanleg input-verdi i staden for ein placeholder, og §23.3 fjerna vidareføringa av ein tredje leverandør.)

**§21 — engelske statusverdiar, adressesti og alle varsel.** `IKKJE_VURDERT` → `NOT_ASSESSED`. Skjema versjon 6 (no versjon 8, §23.4; versjon 9 når §24.4 er implementert): kvar råka tabell blir bygd opp att med `PRAGMA foreign_keys = OFF` og `PRAGMA foreign_key_check` før commit. `Address path` blir berre vist og lagra når verifiseringa er `OK`. `GET /api/alerts` summerer alle lagra kontrollar, med `check_id` og `checked_at`, slår saman like varsel og listar kritiske først. «Helsesjekk» og `data/helsesjekk.sqlite3` er dokumenterte unntak frå engelskregelen.

**§22 — utilgjengeleg nøkkel gjer resten valfritt.** `Availability` er obligatorisk med berre Ja/Nei. Når han er Nei, blir programvare og KI-status skjulte og ikkje kravde, og dei må vere tomme i POST — elles svarar serveren `400`. Det blir ikkje lagra nokon slike rader, `wallet_software` er `NULL`, og `software_compatibility_status` blir `NOT_ASSESSED`. Ein cloud-nøkkel held fram med dei utleidde cloud-verdiane sine og gir det samanslåtte varselet. Databasen kravde inga endring.

## Framtidig arbeid, ikke no

- [ ] Ein måte å lukke eller kvittere ut varsel på.

---

# 23. Konfigurerbart nøkkeloppsett (implementert og verifisert)

Avtalt 02.10.2026, implementert og verifisert før steg 9–12 i §18. Reglane står i §3–§6; dette er berre eit kort samandrag, så fila er lett å lese.

- Kvar nøkkel blir konfigurert éin gong ved første oppstart: namn og type (`hardware`/`cloud`), låste etterpå. Namna må vere unike.
- Namnet brukaren skriv er produktetiketten overalt: skjema, varsel, historikk og CSV-eksport. Nøkkelnummeret blir vist saman med namnet der det trengst, t.d. `Key 1: ColdCard`.
- Nøkkeltypen styrer kontrollane, aldri nøkkelnummeret. Ein cloud-nøkkel følgjer Nunchuk-modellen med det konfigurerte namnet.
- `Wallet software`-vala er `Sparrow Wallet` pluss namnet på kvar konfigurert cloud-nøkkel. Namn på hardware-nøklar er aldri eit software-val.
- Oppsettet blir lagra i SQLite saman med historikken. Nye databasar får eit oppsettsteg; eksisterande databasar blir migrerte frå nøkkelradene sine. Ei uleseleg database gir ein feil og blir ikkje behandla som ny.
- Skjemafiksar: `Firmware version`, `Address path` og `Software version` blir fylte med førre lagra verdi som ein vanleg input-verdi; `Software compatibility` krev eit aktivt val; kontaktspørsmålet gjeld berre nøkkelhaldaren til den valde nøkkelen, med verdiane `Confirmed current` / `Needs external update`.
- Skjemaversjon 8, og 178 grøne testar. Nye endepunkt: `GET /api/setup` og `POST /api/setup`.
- Verifisert med testsuiten. Nettlesarflytane og migreringa av ein verkeleg eldre database står att som manuelle testar i §16.

## Framtidig arbeid, ikkje no

- [ ] Fleire enn tre nøklar, og andre tersklar enn 2-av-3.
- [ ] Ei brukardefinert liste over wallet-programvare, slik at brukaren kan leggje inn si eiga liste.

---

# 24. Avtalt arbeid før StartOS-pakken (IKKJE IMPLEMENTERT)

Avtalt 03.10.2026. Ingenting i §24 er implementert, og alle punkta står opne til testane er grøne. Arbeidet skal gjerast **før** steg 9–12 i §18. Der §24 seier noko anna enn §3–§12, gjeld §24.

## 24.1 Obligatoriske val

- [ ] `Hardware works` blir eit obligatorisk val mellom `Yes` og `No`. Nedtrekkslista startar på `Select status`, som ikkje kan veljast. Feltet er berre relevant for ein hardware-nøkkel, og kravet blir fjerna når nøkkelen er utilgjengeleg.
- [ ] Serveren avviser ein tilgjengeleg hardware-nøkkel utan `hardware_works` med `400`.
- [ ] `Contact confirmation` blir eit obligatorisk val mellom `Confirmed current` og `Needs external update`. Nedtrekkslista startar på `Select status`, som ikkje kan veljast.
- [ ] Kontaktstadfestinga er obligatorisk også når nøkkelen er utilgjengeleg, sidan ho framleis blir spurt om. Serveren avviser manglande verdi med `400`.
- [ ] `NOT_ASSESSED` er berre lovleg som den utleidde verdien for `software_compatibility_status` når nøkkelen er utilgjengeleg. Ingen andre felt tilbyr eller godtar han.

## 24.2 Fjerning av BIP327/SLIP39

- [ ] Heile BIP327/SLIP39-funksjonen blir fjerna: skjema, validering, varsel, historikk, CSV-eksport og databasetabellen `tool_checks`.
- [ ] Gamle BIP327/SLIP39-verdiar blir sletta saman med tabellen. Appen er ikkje lansert, og databasen er ein testdatabase, så inga historikk går tapt for ein brukar.
- [ ] Etter dette kan appen ikkje registrere, vise eller eksportere BIP327- eller SLIP39-resultat.
- [ ] Grunngjeving: appen skal haldast enkel og ryddig.

## 24.3 Skjemastruktur

Det nye skjemaet har denne rekkjefølgja:

| Seksjon | Innhald |
|---|---|
| 01 / Schedule | Sjekkdato og neste sjekk |
| 02 / Key | Nøkkelval og nøkkelkontrollar |
| 03 / Compatibility | Wallet-programvare, versjon og kompatibilitet |
| 04 / External research | KI-sikkerheitsstatus, uendra innhald |
| 05 / Contact confirmation | Kontaktstadfesting for nøkkelhaldaren |
| 06 / Notes | Overordna kommentar |

- [ ] `04 / Standards` går ut, og dei tre seksjonane etter blir omnummererte.

## 24.4 Datamodell og migrering

- [ ] Skjemaversjon 9: `tool_checks`-tabellen blir droppen i migreringa, saman med dataa sine.
- [ ] Migreringa køyrer framleis med `PRAGMA foreign_keys = OFF` og `PRAGMA foreign_key_check` før commit (§21).
- [ ] `tool_checks` er ei barnetabell, så droppet krev inga omskriving av `health_checks`.
- [ ] Alle andre tabellar er uendra.

## 24.5 Testar og dokumentasjon

- [ ] Fjern testane som gjeld BIP327/SLIP39, og legg til testar for at `Hardware works` og kontaktstadfesting krev eit val, både i skjemaet og på serveren.
- [ ] Legg til ein test for migrering av ein database med `tool_checks` til versjon 9.
- [ ] Oppdater `README.md` for skjemaoversikt, statusverdiar, eksportkolonnar og varsel.
- [ ] Alle testar skal vere grøne, og talet i §18 skal oppdaterast.
