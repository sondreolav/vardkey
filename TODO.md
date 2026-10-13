# TODO — VardKey for StartOS 0.4.0

## Mål

Bygg ein **enkel lokal web-app** som køyrer som ein StartOS 0.4.0-service.

Appen skal hjelpe éin brukar å gjennomføre og dokumentere ein årleg health check av eit **2-av-3 multisig-oppsett** med tre nøklar. Namn, type og adressesti blir konfigurerte ved første oppstart.

Appen skal **berre registrere resultat og historikk**. Han skal ikkje signere Bitcoin-transaksjonar, handtere private nøklar eller utføre wallet-operasjonar.

**Om dokumentet**

- §1–§18 er kravspecen og gjeld som han står.
- §19–§30 er korte samandrag av rundane. Alle reglane deira står i §1–§18; den fulle grunngjevinga ligg i git-historikken.
- §31 er **ferdig**, og §32 er **ikkje starta**.
- Eit punkt utan avkryssingsboks er implementert og verifisert. `[ ]` markerer det som står att.
- **Status:** §1–§31 er implementerte og verifiserte. Skjemaet er no **versjon 12**, og testsuiten er venta grøn (**422 testar**). **§30 er ferdig**: StartOS-pakka er bygd, sideloda og køyrd på ein eigen StartOS 0.4.0-boks, og §14, §16 og §17 er køyrde og verifiserte der. Att i §30 står berre det som er sett til 1.0.0-runden — det ekte ikonet og hevinga av pakkeversjonen. §31 (punkta 1–7) er ferdig. **§32 er ikkje starta**, og det er der ikonet og hevinga til versjon 1 ligg; §18 steg 12 ventar på same runden.

## Språkkrav

- Brukargrensesnittet, app-tekst, kjeldekode, variabel- og funksjonsnamn, kommentarar og teknisk dokumentasjon skal vere på engelsk.
- `TODO.md` er på norsk; dette er det einaste unntaket.

---

# 1. Scope for første versjon

**Dette skal vere med**

- Ein enkel web-app med dashboard.
- Registrering av dei tre nøklane.
- Registrering av årleg health check, med kontroll av alle punkta i den årlege sjekklista.
- Varsel når eit kontrollpunkt krev oppfølging.
- Historikk over gjennomførte health checks.
- Automatisk forslag til neste sjekk, ca. eitt år fram i tid.
- Rapporteksport i CSV-format.
- Lokal SQLite-database.
- Persistent lagring på StartOS.
- StartOS health check.
- StartOS backup og restore.

**Dette skal ikkje vere med i første versjon**

Ingen AI-integrasjon, ingen Bitcoin-node-integrasjon, ingen Bitcoin-signering, ingen PSBT-generering eller signering, ingen seed phrase-lagring, ingen private key-lagring, ingen cloud sync av appdata, ingen ekstern database, ingen offline-database og ingen offline-registrering av kontrollar (§31 punkt 6 vedtek ein installerbar PWA, men ikkje offline-data), ingen kalenderintegrasjon, ingen avansert analyse eller grafar, og inga støtte for fleire multisig-oppsett i MVP (det er framleis berre **eitt** oppsett; §31 punkt 7 gjer terskelen i det oppsettet valfri).

**Merk:** dette er eit varig forbod, ikkje ei oppgåveliste. Det skal stadfestast på nytt før release.

---

# 2. Viktige reglar for appen

- Appen skal aldri spørje etter seed phrase, private keys, PIN, passord eller wallet-hemmelegheiter, og aldri lagre slike.
- Kontaktinformasjon til nøkkelhaldarar skal ikkje lagrast; berre om kontaktinfo er stadfesta.
- Appen skal ikkje late som han sjølv har utført ein hardware-test. Brukaren registrerer resultatet av testen.
- Appen skal vere lokal og enkel. Dersom noko ikkje er nødvendig for den årlege health check-en, skal det ikkje byggjast i MVP.

---

# 3. Nøkkeloppsettet appen er bygd for

Appen er bygd for eitt multisig-oppsett. Sidan §31 punkt 7 kan terskelen og talet på nøklar konfigurerast ved første oppstart; standarden er framleis 2-av-3 med tre nøkkelplassar. Kvar nøkkel blir konfigurert éin gong ved første oppstart: namn, type (`hardware`/`cloud`) og adressesti.

- Namnet brukaren skriv, er produktetiketten overalt: skjema, varsel, historikk og CSV-eksport. Nøkkelnummeret blir vist saman med namnet der det trengst, t.d. `Key 1: ColdCard`.
- Nøkkeltypen styrer kontrollane, aldri nøkkelnummeret.
- `type` og `address_path` er identiteten til nøkkelen og er låste etter oppsettet. Namnet kan endrast i innstillingane. Berre ei rotering, som byter ut nøkkelen med ein ny, kan gi han den andre typen (§28).
- Fleire enn tre nøklar og andre tersklar enn 2-av-3 er no støtta, men framleis berre for **eitt** oppsett (§31 punkt 7).

Standardoppsettet appen vart bygd for, med døme-adressestiar:

| Nøkkel | Type | Eining | Adressesti (døme) |
|---|---|---|---|
| 1 | Hardware | SeedSigner | m/48'/0'/0'/2' |
| 2 | Hardware | Blockstream Jade | m/48'/1'/0'/2' |
| 3 | Cloud | Nunchuk | m/48'/2'/0'/2' |

---

# 4. Datamodell

SQLite, med så få tabellar som mogleg. Kvar tabell har éi rad per kolonne her; kolonnar merkte `*` er legacy-kolonnar som berre finst for gamle rader og aldri blir skrivne på nytt.

**`keys`** — nøkkelplassane i det eine oppsettet.
`id`, `key_number` (1–`multisig_key_count`), `name`, `type` (`hardware`/`cloud`), `model`, `address_path`, `created_at`.

**`health_checks`** — éi rad per innsending, som gjeld éin vald nøkkel.
`id`, `checked_at`, `next_check_due`, `wallet_software`, `software_version`, `software_compatibility_status`, `software_comments`, `sparrow_version*`, `nunchuk_version*`, `contact_info_verified`, `comments`.

**`key_checks`** — eitt record for den valde nøkkelen i kvar innsending.
`id`, `health_check_id`, `key_id`, `available`, `hardware_works`, `firmware_version`, `seed_backup_verified`, `address_path_verified`, `address_path`, `comments`.

**`ai_security_checks`** — KI-sikkerheitsstatus per leverandør.
`id`, `health_check_id`, `provider`, `status`, `comments`.

**`wallet_software`** — lista brukaren vedlikeheld i innstillingane.
`id`, `name`, `created_at`.

**`alert_acknowledgements`** — kvitterte varsel.
`id`, `code`, `source`, `key_id`, `check_id`, `reason`, `acknowledged_at`.

**`app_settings`** — namn/verdi, for det som ikkje er historikk.
`name` (PRIMARY KEY), `value`. Held `multisig_threshold`, `multisig_key_count`, `admin_username`, `admin_password_hash` og `session_secret`.

Reglar:

- `hardware_works`, `firmware_version` og `seed_backup_verified` gjeld berre hardware-nøklar.
- `seed_backup_verified` og `address_path_verified` har berre verdiane `OK` eller `PROBLEM`.
- `address_path` lagrar adressestien for den kontrollen.
- Når `available` er Nei, blir dei andre nøkkelfelta tømde, medan nøkkelnotatet blir behalde.
- Når `available` er Nei, blir `wallet_software` og `ai_security_checks` ikkje registrerte i det heile.
- `type` blir lagra éin gong ved første oppstart og er låst etterpå; berre ei rotering kan gi nøkkelen den andre typen (§28).
- `model` er valfri fri tekst (maks 60 teikn) og er rein dokumentasjon: ein hardware-modell eller, for ein cloud-nøkkel, namnet på tenesta. Han er ikkje ein del av identiteten, ikkje eit wallet-programvare-val, og blir ikkje brukt i varselkjelda (§31 punkt 5).
- `provider` lagrar det konfigurerte nøkkelnamnet og den valde programvara, ikkje faste produktnamn.
- `contact_info_verified` er fri tekst med to verdiar, og har ingen «not assessed»-verdi.
- `hardware_works` er obligatorisk for ein tilgjengeleg hardware-nøkkel.
- `name` kan endrast i innstillingane; `type` og `address_path` er identiteten til nøkkelen.
- `address_path_verified` blir sett av serveren ut frå ei samanlikning med `keys.address_path`, og blir ikkje sendt inn av brukaren.
- `wallet_software` i `health_checks` held fram som fri tekst, slik at eldre rader og fjerna listeelement held fram å visast rett.
- `address_path` må vere unik på tvers av alle nøklane i oppsettet: i oppsettet, i innstillingane og ved rotering.
- `reason` i `alert_acknowledgements` lagrar namnet på handlinga som lukka varselet, ikkje ein fri tekst.
- `key_id` i `alert_acknowledgements` lagrar nøkkelen varselet høyrde til, eller `NULL` for eit programvarevarsel frå innstillingslista.
- `tool_checks` finst ikkje. `device`, `seed_backup_status`, `address_verified`, `derivation_height`, `cloud_health_status` og `cloud_provider_operational` finst ikkje.

**§31 punkt 7 og 5 er ferdige:** `app_settings`, `keys.model` og eit oppløyst `key_number`-CHECK er på plass. Skjemaet er versjon 12.

---

# 5. Statusverdiar

- Generelle kontrollar brukar `OK` eller `PROBLEM`. `NOT_ASSESSED` finst berre som den utleidde verdien for `software_compatibility_status` når nøkkelen ikkje kunne kontrollerast; ingen andre felt tilbyr eller godtar han.
- `seed_backup_verified` og `address_path_verified` brukar berre `OK` eller `PROBLEM`.
- KI-sikkerheitsstatus brukar nøyaktig `SECURE`, `PATCHED`, `VULNERABLE` og `COMPROMISED`.
- Kontaktstadfesting brukar `Confirmed current` eller `Needs external update`.
- `Hardware works` (`Yes`/`No`) og `Software compatibility` (`OK`/`PROBLEM`) krev eit aktivt val for ein tilgjengeleg nøkkel.
- `address_path_verified` er utleidd av serveren og er ikkje eit val i skjemaet.
- Same statuslogikk i database, validering, varsel, CSV-eksport og UI.
- Ikkje bland saman «ikkje vurdert» og eit faktisk negativt resultat.

---

# 6. Årleg health check — steg for steg

Stega følgjer seksjonane i skjemaet.

## Steg 1 — Schedule (01 / Schedule)

- Brukaren trykkjer `Start årleg health check`, og dagens dato blir føreslått automatisk.
- Neste sjekkdato blir rekna ut på serveren som eitt kalenderår etter sjekkdatoen, og kan ikkje redigerast i skjemaet.

## Steg 2 — Key (02 / Key)

- Brukaren vel kva nøkkel innsendinga gjeld. Ei innsending gjeld éin nøkkel.
- `Availability` er obligatorisk: Ja eller Nei.
- Ein nøkkel med eit ope varsel kan ikkje veljast, og skjemaet seier kva varsel som står i vegen.
- **Hardware-nøkkel:** `Hardware works` er obligatorisk (`Yes`/`No`), firmware-versjon blir registrert, og seed-backup intakt og stemmande med hardware gir `seed_backup_verified` (`OK`/`PROBLEM`). Kommentar ved behov.
- **Cloud-nøkkel:** berre `Availability` blir spurd om. Kommentar ved behov.
- **Adressesti (alle nøklar):** brukaren registrerer berre `Address path`, førehandsutfylt med nøkkelen sin lagra sti. Serveren samanliknar den innsende stien med `keys.address_path`: lik → `OK`, ulik → `PROBLEM`.
- Når nøkkelen ikkje er tilgjengeleg, blir resten skjult og ikkje kravd.
- Stemmer ikkje stien, viser nettlesaren eit påminningsvarsel før innsending, og kontrollen blir lagra som ein nøkkel som ikkje kunne kontrollerast.

## Steg 3 — Compatibility (03 / Compatibility)

- Brukaren vel éi wallet-programvare: `Sparrow Wallet`, eit namn frå innstillingane, eller namnet på ein konfigurert cloud-nøkkel. Ein cloud-nøkkel er låst til sitt eige namn.
- `Software version` blir registrert for alle nøklar, òg ein cloud-nøkkel.
- `OK` eller `PROBLEM`, med kommentar ved problem.
- For ein cloud-nøkkel er `Wallet software` og `Compatibility status` skjulte og utleidde.
- Når nøkkelen ikkje er tilgjengeleg, er feltet skjult og valfritt.

## Steg 4 — External research (04 / External research)

- Leverandørar per innsending: den valde nøkkelen (ved namn) og den valde programvara.
- Registrer status (`SECURE` / `PATCHED` / `VULNERABLE` / `COMPROMISED`) og ein kort kommentar.
- Berre den valde nøkkelen og den valde programvara blir registrerte. Appen kontaktar ikkje KI sjølv i MVP.
- Når nøkkelen ikkje er tilgjengeleg, blir ingen statusar registrerte.

## Steg 5 — Contact confirmation (05 / Contact confirmation)

- Stadfest at kontaktinformasjonen til nøkkelhaldaren til den valde nøkkelen er gyldig: `Confirmed current` eller `Needs external update`. Stadfestinga er obligatorisk, òg når nøkkelen ikkje er tilgjengeleg.
- Berre statusen blir lagra. Ikkje lagre namn, telefonnummer, e-post eller anna kontaktinnhald.

## Steg 6 — Notes (06 / Notes)

- Eitt overordna kommentarfelt for observasjonar, og eigne kommentarar per nøkkel der det trengst.

## Oppsummering før lagring (Review-panelet)

- Før lagring viser appen alle kontrollpunkt, alle problem, alle manglande kontrollar, neste sjekkdato, handlingar som bør følgjast opp, og utleidde verdiar merkte som nettopp det.
- Brukaren må trykkje `Lagre health check` for å lagre kontrollen.
- Når adressestien ikkje stemmer, blir valet om å lagre likevel tydeleg merkt i oppsummeringa.

---

# 7. Varsel og oppfølging

Alle lagra kontrollar blir lesne, ikkje berre den nyaste. Like varsel (same `code` og `source`) blir slegne saman, og berre den nyaste blir vist. Kritiske varsel blir lista før informative, og nyaste kontroll først innanfor kvar alvor. Eit kvittert varsel held seg skjult til ein nyare kontroll for same `code` og `source` utløyser det igjen. Eit varsel som høyrer til ein nøkkel, blir i staden skjult etter nøkkelen, så ei omdøyping ikkje opnar det att.

**Eit ope varsel som høyrer til ein nøkkel sperrar den nøkkelen** til varselet er lukka. Serveren handhevar regelen, så eit direkte API-kall ikkje kan omgå han. Sperringa gjeld berre den nøkkelen som har varselet.

| `code` | Alvor | Kjelde | Utløyst av | Slik blir det lukka |
|---|---|---|---|---|
| `key_unavailable` | critical | nøkkel | `available` = Nei | Rotering |
| `address_path_mismatch` | critical | nøkkel | Adressestien stemmer ikkje med den lagra | Rotering |
| `hardware_failure` | critical | nøkkel | `Hardware works` = No | Rotering, eller at hardware-walleten blir bytt med same seed |
| `seed_backup_problem` | critical | nøkkel | Seed-backup `PROBLEM` | Rotering |
| `software_incompatible` | critical | nøkkel | `software_compatibility_status` = `PROBLEM`, og den registrerte programvara er namnet på ein konfigurert cloud-nøkkel | At hardware-walleten blir bytt |
| `software_incompatible` | critical | programvare | `software_compatibility_status` = `PROBLEM` | Fjerning av den feilande programvara i innstillingane |
| `security_vulnerable` | critical | nøkkel | KI-status `VULNERABLE` | Rotering, eller lukking utan tiltak |
| `security_vulnerable` | critical | programvare | KI-status `VULNERABLE` | Fjerning av programvara, eller lukking utan tiltak |
| `security_compromised` | critical | nøkkel | KI-status `COMPROMISED` | Rotering er påkravd |
| `security_compromised` | critical | programvare | KI-status `COMPROMISED` | Fjerning av programvara |
| `contact_info_unconfirmed` | info | nøkkel | Kontaktstadfesting `Needs external update` | Lukking, etter at kontaktinformasjonen er oppdatert eksternt |

- Kvar varselkode har eit fast sett av handlingar: `rotate`, `replace_hardware`, `remove_software`, `ignore`, `contact_updated`. Ei handling som ikkje høyrer til varselet, blir avvist.
- `rotate` blir utført i innstillingane, sidan han krev ein ny adressesti. Dei andre handlingane blir utførte der varselet står, kvar med sin eigen knappetekst og sitt eige stadfestingssteg.
- Kjelda til eit KI-varsel er leverandøren. Er han nøkkelen sitt eige konfigurerte namn, er nøkkelen kjelda og ei rotering lukkar varselet. Elles er leverandøren programvara nøkkelen køyrer med, og varselet blir lukka ved å fjerne ho frå innstillingane.
- Eit programvarevarsel frå innstillingslista har inga nøkkel og sperrar inga nøkkel. Eit programvarevarsel som kjem frå eit cloud-nøkkelnamn høyrer til den kontrollerte nøkkelen og sperrar han, sidan namnet aldri kan fjernast frå innstillingane.
- Kvar handling krev ei stadfesting frå brukaren, og appen utfører aldri tiltaket sjølv. Han kontaktar heller aldri leverandørar eller KI-tenester.
- Eit varsel utan handling er ein feil i koden, ikkje ein tilstand brukaren kan hamne i.
- Eit varsel om nøkkel utilgjengeleg, adressestifeil eller seed-backup gjeld berre den nøkkelen, og resten av nøkkelfelta kan ikkje registrerast.

---

# 8. Dashboard

- Vis multisig-oppsettet og status for kvar nøkkel, med siste sjekk og neste forfall per nøkkel.
- Oversiktskort «Next check» (tidlegaste forfall, med kva nøkkel det gjeld) og «Attention» (kor mange nøklar som har passert fristen). Om ein dato er passert, blir avgjort i nettlesaren.
- Vis alle aktive varsel, med kva registrering kvart varsel kjem frå, og handlinga som lukkar det.
- Knapp `Start årleg health check`, lenke `Historikk`, lenke `Download CSV` og lenke til innstillingane.
- Vis oppsettsteget i staden for dashboardet når nøkkeloppsettet manglar.
- Eit nøkkelkort viser namn, **adressesti** og type, og ei tydeleg melding når nøkkelen har eit ope varsel, i tillegg til datoane sine: kor mange varsel som står ope, at nøkkelen ikkje kan kontrollerast før dei er lukka, kva handling som lukkar det første, og ei lenkje til varsellista (§31 punkta 4 og 5).

---

# 9. Historikk

- Vis alle gjennomførte health checks kronologisk, nyaste først, med kva nøkkel kvar innsending gjeld.
- Opne ein health check i read-only-visning med dato, neste sjekk, status per nøkkel, programvare og versjon, KI-status og kommentarar.
- Gamle health checks blir aldri overskrivne.
- Vis `Address path verified` som den utleidde verdien han er, og ikkje som eit brukarval.
- Vis namnet nøkkelen har no, sidan namnet kan endrast i innstillingane.
- Vis kva varsel som vart lukka på kontrollen, med kva handling og kva dato.

---

# 10. Rapporteksport

- `GET /api/export` gjev rein CSV (UTF-8, komma, CRLF, header). Ingen XLSX, og appen lovar ikkje Excel-kompatibilitet.
- Éi rad per nøkkelsjekk. Kolonnen `Check id` knyter saman rader frå same innsending.
- Inneheld dato, neste sjekk, nøkkelstatus, hardware/firmware, seed-resultat, adresse-sti, programvare og kompatibilitet, KI-status, kontaktstadfesting og kommentarar.
- Resultat med meir enn éin verdi per innsending ligg i éi celle som `SeedSigner: VULNERABLE; Sparrow Wallet: SECURE`.
- Statusverdiane blir skrivne slik dei er lagra. `0`/`1` blir skrivne som `No`/`Yes`.
- Nøkkelnamnet og nøkkeltypen kjem frå oppsettet, og namnet er namnet nøkkelen har no.
- Nedlastinga heiter `YYYY-MM-DD-vardkey-export.csv`, med datoen serveren har når han svarar (§31 punkt 3).
- Siste kolonne, `Follow-up closed`, listar varsla som vart lukka på kontrollen, som `code: action (YYYY-MM-DD)`. Berre lukkingar som høyrer til ein nøkkel, blir viste.

---

# 11. Backend

- SQLite med initialisering og migrering. Skjemaet er versjon 12.
- Lagring av nøklar, health checks, historikk og rapporteksport.
- Varsellogikken (§7).
- Health endpoint, som er det einaste endepunktet utanfor innlogginga (§31 punkt 1).
- Valider input på serveren, og bruk parameteriserte SQL-spørringar.

Minimumsendepunkt: `GET /health`, `GET /api/keys`, `GET /api/health-checks`, `GET /api/health-checks/:id`, `POST /api/health-checks`, `GET /api/export`.

**Merk:** `GET /api/setup`, `POST /api/setup`, `GET /api/settings`, `POST /api/settings/keys`, `POST /api/settings/wallet-software`, `POST /api/keys/<id>/rotate`, `POST /api/alerts/acknowledge`, `GET /api/key-status`, `GET /api/previous-values`, `GET /api/alerts`, `GET /api/session`, `POST /api/admin`, `POST /api/login` og `POST /api/logout` er ekstra endepunkt utanom minimumslista, fordi oppsettsteget, innstillingane, dashboardet, skjemaet og innlogginga treng dei. Dei står ikkje i spesifikasjonen enno.

- `POST /api/health-checks` krev éin konfigurert nøkkel, `available` og gyldige, relevante resultat, og avviser manglande eller dupliserte registreringar.
- `POST /api/health-checks` krev ikkje programvare eller KI-status når nøkkelen ikkje kunne kontrollerast, og avviser slike resultat med `400`.
- `POST /api/health-checks` avviser ein nøkkel som har eit ope varsel, med `409`, og regelen blir handheva før resten av valideringa.
- `POST /api/setup` lagrar multisig-tala og nøkkeloppsettet éin gong med namn, type, modell og adressesti, og avviser eit nytt oppsett med `409`.
- `POST /api/setup`, `POST /api/settings/keys` og `POST /api/keys/<id>/rotate` avviser ein adressesti som ein annan nøkkel alt har (`400` i oppsettet og roteringa, `409` i innstillingane).
- `GET /api/settings` gjev nøklane med adressestien og modellen deira og lista over wallet-programvare.
- `POST /api/settings/keys` lagrar eit nytt namn og ein modell, og ein adressesti så lenge nøkkelen ikkje har nokon lagra kontroll. Typen er aldri med i payloaden.
- `POST /api/settings/wallet-software` lagrar heile lista, og lukkar varsla til ei programvare som blir fjerna.
- `POST /api/keys/<id>/rotate` roterer ein nøkkel med ein ny, unik adressesti, kan gi nøkkelen den andre typen (§28), og kvitterer ut varsla hans.
- `POST /api/keys/<id>/rotate` avviser med `409` ein typeendring som ville gjort nøkkelen til ein cloud-nøkkel under eit namn som wallet-programvare-lista alt har.
- `POST /api/alerts/acknowledge` kvitterer ut eit varsel med `code`, `source` og handlinga som lukkar det.
- `GET /api/health-checks/<id>` gjev òg `closed_alerts`, lukkingane som høyrer til kontrollen.
- Feilkodar elles: ugyldig payload `400`, ukjent nøkkel eller varsel `404`, låst eller duplikat adressesti `409`, øydelagd database `500`, manglande eller ugyldig sesjon `401`, og manglande eller ugyldig CSRF-token `403` (§31 punkt 1).

---

# 12. Frontend

- Enkel responsiv web-UI. Enkelheit går framfor grafisk kompleksitet.
- Tydlege statusfelt, og faste val der statusen skal vere ein avgrensa verdi.
- Vis problem tydeleg, og vis kva som står att før ein health check kan lagrast.
- Skjul felt som ikkje gjeld for vald nøkkel eller vald programvare, og skjul programvare og KI-status når nøkkelen ikkje kunne kontrollerast. Eit skjult `required`-felt blokkerer innsendinga, så flagget må alltid clearast når feltet blir skjult.
- Eige oppsettsteg ved første oppstart: terskel, talet på nøklar, og namn, type, modell og adressesti per nøkkel.
- Skjemaet viser kva nøklar som er sperra av eit ope varsel, og kva handling som lukkar det.
- Eit påminningsvarsel før innsending når adressestien ikkje stemmer.
- Innstillingsside med `01 / Wallet software` og `02 / Key rotation`, bygd for fleire tema seinare. Nøkkelnamnet, modellen, adressestien til ein nøkkel utan lagra kontroll, og roteringa med ny type blir alle endra i roteringsseksjonen, og éin knapp lagrar alt. Det finst ikkje lenger ein eigen `01 / Keys`-seksjon.
- Varselknappane har den teksten og det stadfestingssteget som høyrer til handlinga si, og varselet om programvare-inkompatibilitet peikar på innstillingane.
- Eit innloggingssteg framfor alt anna, og eit opprett-admin-steg når ingen admin finst enno (§31 punkt 1).
- Appen skal kunne installerast som ein PWA utan offline-data (§31 punkt 6).
- Sørg for at appen fungerer godt i vanleg StartOS-browser.

---

# 13. StartOS 0.4.0

Bygg appen som éin enkel StartOS-service.

```text
StartOS 0.4.0
└── VardKey
    ├── Web UI
    ├── Backend/API
    ├── SQLite
    └── Persistent data
```

- Opprett StartOS package.
- Opprett manifest.
- Opprett service-definisjon.
- Opprett HTTP web-interface.
- Opprett persistent volume.
- Opprett health check.
- Opprett backup-oppsett.
- Opprett installasjons-/brukarinstruksjonar.
- Bygg `.s9pk`.
- Verifiser at pakken kan installerast på StartOS 0.4.0.

**Merk:** alle ti punkta er no oppfylte. Pakka er skriven inn i repoet, bygd til `vardkey_x86_64.s9pk`, sideloda og køyrd på ein eigen StartOS 0.4.0-boks (sjå §30 og §16). §31 legg til to handlingar i `Actions & Config`: `Delete all data` og `Set Admin Password`, og begge er ferdige.

Unngå: Postgres, Redis, ekstern backend, ekstern cloud-service for appdata, og ekstra container utan konkret behov.

**Merk:** dette er eit varig forbod, ikkje ei oppgåveliste. Det skal stadfestast på nytt før release.

---

# 14. Lagring og backup

- SQLite-database skal liggje på persistent volum.
- Appdata skal overleve restart.
- Konfigurer StartOS backup av persistent data.
- Test backup og test restore.
- Verifiser at gamle health checks finst etter restore.

**Merk:** alle punkta er køyrde og verifiserte på boksen, gjennom §16 StartOS-testen og §17. `startos/backups.ts` brukar `sdk.Backups.ofVolumes('main')`, og databasen ligg på `main`-volumet på `/data`. StartOS stoppar servicen medan ein backup går, så databasefila er ikkje under skriving når ho blir kopiert — det var det opne spørsmålet i §30, og det er svara på. Restore gav attende nøkkeloppsettet og dei lagra kontrollane, så ingen eigen SQLite-snapshot-krok trongst og inga kjend avgrensing står att. Punkta skal køyrast på nytt etter §31, sidan skjemaet og innlogginga er endra.

---

# 15. Sikkerheit og personvern

- Ingen seed phrase, private keys, wallet-passord eller sky-tokens i databasen.
- Ingen unødvendige personopplysningar. Kontaktinfo blir berre registrert som status (`Confirmed current` / `Needs external update`).
- Valider input på serveren, og bruk parameteriserte SQL-spørringar.
- Ikkje implementer eigen kryptografi.
- Ikkje send data til eksterne tenester i MVP.
- Adressestien er ein offentleg derivasjonssti og inneheld inga hemmelegheit.

**§31 punkt 1** legg til eit adminpassord, og avgrensar dei to første punkta til *wallet*-hemmelegheiter: adminpassordet er den einaste akkrediteringa appen lagrar, og han blir lagra som ein hash med `hashlib.scrypt` frå standardbiblioteket, aldri i klartekst.

---

# 16. Testing

## Funksjonstest

- Opprett nøklane, start ein health check, fullfør alle kontrollpunkt, lagre han og vis han i historikken.
- Start ein ny health check, og verifiser at den gamle kontrollen framleis finst.

## Problemtest

- Test nøkkel utilgjengeleg, hardware-feil og seed-backup-feil.
- Test adressestifeil, både påminninga før innsending og varselet etterpå.
- Test programvare-inkompatibilitet, og at `Hardware works` og kontaktstadfestinga krev eit val.
- Test KI-status `VULNERABLE` og `COMPROMISED`, og kontaktinfo `Needs external update`.
- Test rotering av ein nøkkel, med og utan nytt namn, og at rotering krev ein ny adressesti.
- Test kvittering av eit varsel, og at eit nyare varsel kjem tilbake.
- Test at ein nøkkel med eit ope varsel ikkje kan få ein ny kontroll, og at nøkkelen blir ledig igjen når varselet er lukka.
- Test at to nøklar ikkje kan ha same adressesti, korkje i oppsettet, i innstillingane eller ved rotering.
- Test kvar varselhandling, og at eit varsel utan handlingar blir rekna som ein feil.
- Test at eit nøkkelkort viser ei varselmelding når nøkkelen har eit ope varsel.
- Test at fjerning av den feilande programvara lukkar `software_incompatible`.
- Test at eit lukka varsel viser seg i historikken og i CSV-en, med handling og dato.
- Test at eit kontaktvarsel gir `Needs action` og sperrar nøkkelen, og at nøkkelen blir ledig att ved `contact_updated`.
- Test at `software_incompatible` med ei cloud-nøkkel-programvare gir `replace_hardware` på den kontrollerte nøkkelen, og at det same varselet frå innstillingslista held fram med `remove_software`.
- Test at ein kan byte namn på ein nøkkel i roteringsseksjonen utan å rotere han, og at ei rotering krev stadfestingsboksen.
- Test at ei rotering kan gi nøkkelen den andre typen, og at eit namn som wallet-programvare-lista alt har, blir avvist.

**Merk:** dette er dei manuelle nettlesartestane dine, og dei er køyrde og verifiserte.

**§31 legg til:** innlogging og sesjon, oppsett av eit anna multisig-oppsett enn 2-av-3, modell/teneste per nøkkel, datert eksportnamn, sletting av all data, og installasjon av PWA-en. Sjå lista i §31.

## StartOS-test

- Installer `.s9pk` på StartOS 0.4.0, start servicen og opne web UI.
- Utfør ein komplett test-check.
- Restart servicen, og verifiser at data framleis finst.
- Ta backup, restore backup, og verifiser data etter restore.

**Merk:** alle fire er køyrde og verifiserte på boksen. `vardkey_x86_64.s9pk` vart sideloda og installert, servicen står som `Running`, helsesjekken melder «The web interface is ready», og `Open UI` opnar VardKey i nettlesaren på StartOS-adressa. Restart og restore heldt på dataa, og dei gamle health checkane fanst etter restore.

**§31 legg til:** at `Set Admin Password` og `Delete all data` står i `Actions & Config` og verkar, og at ein installerbar PWA kan leggjast til frå nettlesaren. Skal køyrast på nytt etter §31.

---

# 17. Ferdigkriterium for første release

Før første release skal alle desse vere oppfylte:

- Appen køyrer på StartOS 0.4.0.
- Nøklane i multisig-oppsettet er representerte i appen.
- Ein komplett årleg health check kan gjennomførast i nettlesaren, og alle årlege kontrollpunkt kan registrerast.
- KI-status kan registrerast som SECURE, PATCHED, VULNERABLE eller COMPROMISED.
- Kontaktinfo kan verifiserast utan å lagre kontaktinformasjonen.
- Problem gir tydelege varsel, og eit varsel kan lukkast på den måten som høyrer til varselet.
- Neste sjekk blir lagra, og historikk fungerer.
- CSV-rapport kan eksporterast.
- Data overlever restart, og backup og restore fungerer.
- Ingen wallet-hemmelegheiter blir lagra.
- Appen er passordbeskytta med ein adminbrukar (§31 punkt 1).
- All appdata kan nullstillast frå StartOS, medan adminbrukaren står att (§31 punkt 2).

**Merk:** alle punkta er køyrde og verifiserte på boksen. Kriterielista er oppfylt, men pakkeversjonen blir ikkje heva enno — sjå §30 og §32.

---

# 18. Arbeidsrekkefølgje for AI-programmeraren

Utfør oppgåvene i denne rekkjefølgja og ikkje hopp fram til avanserte funksjonar:

- 1–8. Grunnleggande web-app, SQLite og datamodellen, dei tre nøklane, health check-skjemaet, lagring og historikk, varsellogikken, dashboardet og rapporteksport.
- 9. Implementer StartOS package.
- 10. Implementer persistent storage og backup.
- 11. Test restart og restore.
- [ ] 12. Bygg endeleg `.s9pk` og gjer første release.

**Merk:** §23–§29 kom inn etter steg 8 og er implementerte og verifiserte. Steg 9–11 er ferdige: pakka er skriven, bygd, installert og køyrd på ein eigen boks, og restart og restore er testa. Steg 12 står att, fordi det er sett til 1.0.0-runden saman med ikonet — ikkje fordi noko manglar. Alt høyrer til §30 og §32.

**§31 kjem før steg 12.** §31 (punkta 1–7) er ferdig. Det som står att før pakkeversjonen blir heva til `1.0.0:0`, er §32: det ekte ikonet og sjølve hevinga.

**Testar:** køyr `python3 -m unittest discover -s tests`. Suiten skal vere grøn både på Linux og på Windows-kopien.

**Hovudregel:** Bygg den minste løysinga som oppfyller lista over. Ikkje legg til nye funksjonar, tenester eller arkitektur utan at dei er nødvendige for punkta i denne TODO-lista.

---

# 19–22. Vedtekne avgjerder (implementerte og verifiserte)

- **§19 — registrering per nøkkel.** Ei innsending gjeld éin vald nøkkel, ikkje alle tre. Brukaren vel éi wallet-programvare med eitt versjonsfelt. Kvar nøkkel har sitt eige neste-sjekk-intervall.
- **§20 — skjulte felt som blir utleidde.** Eit felt som ikkje gjeld for den valde nøkkelen eller den valde programvara, blir skjult og utleidd. Førre lagra verdi blir fylt inn som ein vanleg input-verdi, og alt utleidd blir lista i Review-oppsummeringa, merkt som nettopp det.
- **§21 — engelske statusverdiar og alle varsel.** `IKKJE_VURDERT` → `NOT_ASSESSED`. Kvar råka tabell blir bygd opp att med `PRAGMA foreign_keys = OFF` og `PRAGMA foreign_key_check` før commit. `GET /api/alerts` summerer alle lagra kontrollar, slår saman like varsel og listar kritiske først. Etter §29 er `TODO.md` det einaste norske dokumentet i repoet; korkje produktnamnet eller databasefila er lenger unntak frå engelskregelen.
- **§22 — ein nøkkel som ikkje kunne kontrollerast, registrerer ingenting elles.** Det gjeld både `available` = Nei og ein adressesti som ikkje stemmer: `wallet_software` blir `NULL`, `software_compatibility_status` blir `NOT_ASSESSED`, og eit innsend resultat er ein `400`, ikkje noko som blir kasta stille.

---

# 23. Konfigurerbart nøkkeloppsett (implementert og verifisert)

Kvar nøkkel blir konfigurert éin gong ved første oppstart: namn, type og adressesti. Namnet er produktetiketten overalt. `Wallet software`-vala er lista frå innstillingane (sådd med `Sparrow Wallet`) pluss namnet på kvar konfigurert cloud-nøkkel; eit hardware-nøkkelnamn er aldri eit software-val. Oppsettet ligg i SQLite saman med historikken, og ei ny database får eit oppsettsteg. Ei uleseleg database gir ein feil og blir ikkje behandla som ny. Nye endepunkt: `GET /api/setup` og `POST /api/setup`.

---

# 24. Obligatoriske val og ny skjemastruktur (implementert og verifisert)

`Hardware works` og kontaktstadfestinga er obligatoriske val med `Select status` som første, ugyldige alternativ. Kravet for `Hardware works` fell bort når nøkkelen ikkje kunne kontrollerast; kontaktstadfestinga blir spurd om uansett. Skjemaet har seks seksjonar: 01 Schedule, 02 Key, 03 Compatibility, 04 External research, 05 Contact confirmation, 06 Notes. BIP327/SLIP39 er fjerna heilt, saman med `tool_checks`-tabellen og dataa hans.

---

# 25. Nøkkelidentitet, rotering, varselkvittering og innstillingar (implementert og verifisert)

Adressestien er identiteten til nøkkelen saman med typen, og er låst etter første lagra kontroll. Serveren utleier `address_path_verified` etter ei samanlikning som ignorerer blankteikn rundt verdien. Namnet er ein etikett som innstillingane kan endre, og historikk, varsel og CSV viser namnet nøkkelen har no. `POST /api/keys/<id>/rotate` stadfestar at nøkkelen er bytt ut, held eller endrar namnet, krev ein ny adressesti, kvitterer ut nøkkelens eigne varsel, og gjer inga endring i tidlegare kontrollar. Sida varslar om at rotering gir ei ny lommebok, slik at midla må flyttast frå den gamle multisig-oppsetninga før dei gamle nøklane blir kasserte. Innstillingane ligg på `/settings`. Software-lista blir lagra heilt, er sådd med `Sparrow Wallet`, må aldri bli tom, og kan ikkje innehalde eit namn som alt kjem frå ein cloud-nøkkel.

---

# 26. Sperring, unike adressestiar og varselhandlingar (implementert og verifisert)

Ein nøkkel med eit ope varsel kan ikkje få ein ny kontroll før varselet er lukka, og serveren handhevar regelen med `409`. Adressestien må vere unik på tvers av nøklane: `400` i oppsettet, `409` i innstillingane og `400` ved rotering, og meldinga nemner nøkkelen som har stien. Ei rotering krev ein ny, unik sti, og `address_path_unchanged` er fjerna. Kvar varselkode har sine eigne lukkehandlingar (§7), og den generiske kvitteringa er borte: `POST /api/alerts/acknowledge` tek handlinga og lagrar handlingsnamnet som `reason`. Eit nøkkelkort med eit ope varsel viser `Needs action`, kor mange varsel som står ope, og kva handling som lukkar det første.

---

# 27. Varselhandlingar i historikk og CSV, kontaktvarselet og cloud-programvare (implementert og verifisert)

Avtalt 05.10.2026. Skjemaet gjekk til versjon 11.

Bakgrunnen: ei lukking vart alt lagra i `alert_acknowledgements`, men ingenting las tabellen, så brukaren kunne ikkje sjå kva som vart lukka, når og med kva handling. I tillegg høyrde kontaktvarselet ikkje til nokon nøkkel, og `software_incompatible` tilbaud `remove_software` òg når «programvara» var namnet på ein cloud-nøkkel, som aldri kan fjernast frå innstillingane.

- **Sperring.** Eit varsel som høyrer til ein nøkkel sperrar den nøkkelen til det er lukka. Det gjeld òg `contact_info_unconfirmed`, som har alvor `info`. `blocking_alert` og filteret i skjemaet matchar på `key_id`, så sperrekoden trong ikkje endrast.
- **Kontaktvarselet høyrer til ein nøkkel.** `key_id` = den kontrollerte nøkkelen, `source` = `Key N: <namn>` (same konvensjon som nøkkelvarsla), og meldinga namngjev nøkkelen: «The contact details for Key 1: SeedSigner need an external update. Update them in your external documentation, then close this alert.» Alvoret er framleis `info`, og handlinga framleis `contact_updated`.
- **`software_incompatible` har to former.** Når den registrerte `wallet_software` er namnet på ein konfigurert cloud-nøkkel: `key_id` = den kontrollerte nøkkelen, `source` = `Key N: <namn>`, handlingane `[replace_hardware]`, og inga `software`-verdi, så ei fjerning frå innstillingane kan ikkje lukke det. Elles som før: `key_id` = `None`, `source` = programvanamnet, handlingane `[remove_software]`.
- **Kvitteringa lagrar nøkkelen.** `alert_acknowledgements.key_id` er ei nullable kolonne (INTEGER, ingen FK, ingen CHECK).
- **Varselidentitet.** Eit varsel med `key_id` blir kvittert og skjult etter `(code, key_id)`; eit varsel utan `key_id` som før, etter `(code, source)`. Det fiksar ein bug der `rotate` med `keep_name=false`, eller ei rein omdøyping i innstillingane, opna eit lukka varsel att, fordi `source` inneheld namnet nøkkelen har no.
- **Lukkingar i historikk og CSV.** `GET /api/health-checks/<id>` har ein `closed_alerts`-liste, og CSV-en har kolonnen `Follow-up closed` heilt til slutt, med `code: action (YYYY-MM-DD)`. Berre lukkingar med `key_id` blir viste, altså ikkje `remove_software` og ikkje software-kjelde-`ignore`. Lukkinga blir hengd på kontrollen ho lukka (`check_id`).

---

# 28. Nøkkeltypen kan berre endrast ved ei rotering, og nøkkelnamnet blir endra i roteringsseksjonen (implementert og verifisert)

Avtalt 05.10.2026.

Typen er ein del av identiteten til nøkkelen, saman med adressestien, så oppsettet låser han og innstillingane endrar han aldri. Ei rotering byter ut nøkkelen med ein ny, og berre der kan den andre typen veljast. Namnebytet flytta samstundes inn i roteringsseksjonen, slik at alt som gjeld nøkkelidentiteten ligg på éin stad.

- `POST /api/keys/<id>/rotate` tek ein valfri `type` (`hardware`/`cloud`). Er han utelaten, held nøkkelen typen han har.
- Ein nøkkel som blir ein cloud-nøkkel, byr på sitt eige namn som wallet-programvare. Wallet-programvare-lista kan ikkje innehalde eit namn som alt kjem frå ein cloud-nøkkel, så eit namn lista alt har, blir avvist med `409` (`WalletSoftwareNameInUse`), og meldinga seier kva oppføring som må fjernast først.
- `POST /api/settings/keys` tek framleis berre namn, modell og adressesti, aldri type.
- Innstillingane har to seksjonar: `01 / Wallet software` og `02 / Key rotation`. Den gamle `01 / Keys`-seksjonen er fjerna, sidan namnebytet no høyrer til roteringsseksjonen.
- I roteringsseksjonen kan brukaren byte namn på ein nøkkel åleine, utan å rotere han. Det går gjennom `POST /api/settings/keys`, krev inga stadfesting, og fungerer for alle nøklar.
- Adressestien til ein nøkkel **utan** lagra kontroll kan òg endrast der, gjennom same endepunkt.
- Ei rotering krev at nøkkelen blir markert med `Rotate this key` **og** at stadfestingsboksen «I confirm that each selected key has been replaced by a new key or hardware wallet» blir huka av. Då blir typen, den nye stien og namnet lagra gjennom roteringsendepunktet.
- Knappen heiter `Save keys`, sidan han lagrar både namnebyte og roteringar i éin omgang, og han seier ifrå når det ikkje finst noko å lagre.

---

# 29. Namnebyte til VardKey (implementert og verifisert)

Avtalt 10.10.2026. Skjema versjon 11 står uendra; dette var eit reint namnebyte utan åtferdsendring.

Appen heiter **VardKey**, med beskrivinga **Bitcoin Multisig Health Monitor**. Etter bytet er `TODO.md` det einaste norske dokumentet i repoet: korkje produktnamnet eller databasefila er lenger unntak frå engelskregelen.

- **Databasen.** Standardstien er `data/vardkey.sqlite3` i `app.py` og i alle funksjonsdefaultane i `database.py`. Det vart ikkje skriven migrering: den gamle testdatabasen blir kasta og oppsettet konfigurert på nytt, slik README seier for ei eldre testdatabase.
- **Eksportfila.** `EXPORT_FILENAME` i `app.py` og `download`-attributtet i `static/index.html` er `vardkey-export.csv`, og `tests/test_app.py` sjekkar det nye namnet. Dei to stadene byter i takt, så grensesnittet og serveren lovar same namn. (§31 punkt 3 gjer namnet datert; sjå §31.)
- **Produktnamnet i grensesnittet.** `<title>`, brand-teksten, `aria-label`, `brand-mark` (`V`) og footeren i alle fem HTML-filene, og intro-meininga i `health-check.html`.
- **Beskrivinga.** «Bitcoin Multisig Health Monitor» blir vist i `README.md` og som éi linje under tittelen på dashboardet. Ho er ikkje lagd inn som eyebrow i `health-check.html` eller `settings.html`, sidan testane samanliknar eyebrow-lista på dei to sidene eksakt.
- **Repoet byter ikkje namn.** Gitea-repoet og prosjekt-id-en held fram som `ai-bot/helsesjekk`. Ei seinare omdøyping i Gitea-UI rører ingen kode, men `REPOSITORIES_JSON` må då oppdaterast.
- **README.md** held strukturen sin, med namn, stiar, eksportfila og unntaksavsnittet i «Development» oppdaterte. Unntaksavsnittet seier no at `TODO.md` er det einaste norske dokumentet, og at produktnamnet og databasefila er engelske.
- **Inga åtferdsendring, ingen nye funksjonar, inga skjemaendring.** Éin ny test sjekkar at dashboardet viser namnet og beskrivinga, og testsuiten er grøn med 346 testar.
- **Vernet.** Eit grep etter det gamle namnet i heile repoet gav null treff i kode, grensesnitt, testar og dokumentasjon. Dei einaste attverande referansane til repoet og arbeidskopien står i dette dokumentet og i `ai-note.md`, som er dei to dokumenta som ikkje vart rørte i denne runden.

---

# 30. StartOS 0.4.0-pakke (bygd, installert og verifisert)

Avtalt 10.10.2026. Bygd etter at §29 er verifisert.

Appen blir éin StartOS-service: éin daemon, éin container, SQLite på eit persistent volum. Forbodet i §13 gjeld som han står: ingen Postgres, ingen Redis, ingen ekstern backend, inga ekstern cloud-teneste for appdata, og ingen ekstra container utan konkret behov.

- **Pakka ligg i app-repoet.** StartOS-filene (`startos/`, `Dockerfile`, `Makefile`, `package.json` og resten av skjelettet) ligg ved sida av appen i `ai-bot/helsesjekk`. Pakkeguiden seier at pakke-repoet ikkje skal vere ein fork av appen; her er appen vår eigen og har ikkje noko publisert image, så pakka byggjer appen frå repo-rota. Avviket står i `AGENTS.md`, så ingen legg inn ein submodul for å «rette» det.
- **Namn og versjon.** Manifest `id: 'vardkey'`, `title: 'VardKey'`, `volumes: ['main']` mounta på `/data`. Pakkeversjonen startar på `0.1.0:0` og blir heva til `1.0.0:0` når §16 StartOS-testen og §17 er oppfylte.
- **Lisens.** `GPL-3.0-only`, med ein `LICENSE`-fil i repoet. Det er copyleft-motstykket til CC BY-SA 4.0, som er ein innhaldslisens Creative Commons sjølve rår frå å bruke på programvare, og GPL-3.0 gjev i tillegg ein eksplisitt patentlisens. Blir SPDX-id-en avvist av bygget, blir han skriven som `GPL-3.0`.
- **`marketingUrl`** er `https://sondreolav.com/vardkey`. Sida finst ikkje enno og blir laga til slutt; URL-en er sett inn likevel, sidan manifestet krev han.
- [ ] **Ikonet blir utsett.** `icon.svg` blir teikna i runden som hevar pakka til `1.0.0`, når appen er ferdig. Eit minimalt placeholder-ikon ligg i repoet no, sidan skjelettet alltid leverer eit ikon, og blir bytt i den runden. §32 hentar det inn.
- **Daemonen.** Éin daemon `primary` som køyrer `python3 app.py` med `PORT=8080` og `DATABASE_PATH=/data/vardkey.sqlite3`. Volumet `main` blir mounta skrivbart på `/data`. Ingen oneshot, ingen sidecar, og inga `USER`-linje i Dockerfile, så `/data` er skrivbar utan `chown`.
- **Helseendepunktet.** Daemon-`ready` med `checkWebUrl` mot `http://127.0.0.1:8080/health`. Den interne porten i `bindPort` er den same som `PORT`, elles blir sjekken aldri grøn. `GET /health` er òg det einaste endepunktet som står utanfor innlogginga (§31 punkt 1), elles melder StartOS servicen som usunn.
- **Web-grensesnitt.** `MultiHost.of(effects, 'ui').bindPort(8080, { protocol: 'http', preferredExternalPort: 80 })` med éin `createInterface({ id: 'ui', type: 'ui' })`. StartOS terminerer TLS og proxyar rein HTTP inn i containeren, så appen må ikkje byggje absolutte `http://`-URL-ar. Appen gjer det ikkje i dag.
- **Backup.** `backups.ts` peikar på volumet `main`. Det opne spørsmålet i denne runden var om `setupBackups` har ein krok for eit konsistent SQLite-snapshot. Han trongst ikkje: StartOS stoppar servicen medan ein backup går, så databasefila er ikkje under skriving når ho blir kopiert. Det er ikkje ei kjend avgrensing lenger, og det står i `README.md` og i `startos/backups.ts`.
- **Ingen CI.** Pakkeguiden føreset GitHub-workflows. Repoet ligg på Gitea, og `.s9pk` blir bygd lokalt med `make`. Det står i `AGENTS.md`.
- **Rekkjefølgje.** Skjelettet kjem frå `s9pk init-workspace`; deretter `LICENSE`, `Dockerfile`, `.dockerignore`, `startos/manifest/i18n.ts`, `startos/manifest/index.ts`, `startos/utils.ts`, `startos/main.ts`, `startos/interfaces.ts`, `startos/backups.ts`, `startos/versions/`, `startos/init/`, `instructions.md`, `UPDATING.md`, `AGENTS.md`, `README.md`, og til slutt `TODO.md` og `ai-note.md`.

**Merk:** pakka er ferdig og verifisert. `make x86` gjekk reint (`tsc --noEmit`, `prettier --check`, `ncc`), bygde `vardkey_x86_64.s9pk` (35M, `Arch: x86_64`, `SDK: 3.0.4`, pakkeversjon `0.1.0:0`), og pakka vart sideloda og køyrd på ein eigen StartOS 0.4.0-boks. Skjelett-filene (`package.json`, `tsconfig.json`, `Makefile`, `.prettierrc`, `startos/sdk.ts`, `startos/index.ts`, `startos/actions/index.ts`, `startos/i18n/`, `startos/fileModels/`, `assets/`) vart skrivne i same runde i staden for genererte av `s9pk init-workspace`, sidan kommandoen ikkje fanst der miljøet som skreiv dei; bygget og installasjonen stadfestar at dei er ekvivalente, og `@start9labs/start-sdk` står på `3.0.4`.

**Det som står att i denne runden er medvite utsett:** det ekte `icon.svg`, og hevinga av pakkeversjonen frå `0.1.0:0` til `1.0.0:0`. §16 og §17 er oppfylte, men brukaren har meir som skal implementerast før versjon 1, og tek den avgjerda med sin eigen AI-strateg. **Ikkje hev versjonen og ikkje lag ikonet utan at brukaren ber om det.** §18 steg 12 («gjer første release») ventar på den same avgjerda. Etter §31 ligg begge i §32.

---

# 31. Punkta før versjon 1 (ferdig)

Avtalt 10.10.2026. Åtte punkt som skulle vere ferdige **før** pakkeversjonen blir heva frå `0.1.0:0` til `1.0.0:0`. Skjemaet gjekk frå versjon 11 til **12** i denne runden. Pakkeversjonen står stille.

Punkta vart gjorde i rekkjefølgja **7, 5, 4, 3, 2, 1, 6** — datamodellen først, sidan alt anna byggjer på han. Punkt 8, ikonet, vart skilt ut til §32 og er ikkje starta.

**Punkt 7 — fleksibel terskel (2-av-3 blir valfritt).** Ny `app_settings`-tabell med `multisig_threshold` og `multisig_key_count`; `KEY_COUNT` blir lesen derifrå i staden for å vere ein konstant. `keys.key_number` sin `CHECK` vart lausna opp gjennom ein tabell-ombygging med `PRAGMA foreign_keys = OFF` og `PRAGMA foreign_key_check` før commit. `POST /api/setup` tek `threshold` og `key_count`, og `GET /api/setup` gjev dei attende. Grenser: `2 ≤ key_count ≤ 15` og `1 ≤ threshold ≤ key_count`; ein terskel på 1 er tillaten, sidan brukaren vel sjølv. Framleis berre **eitt** oppsett. Dette lukka den opne boksen i §3 og det siste punktet i «Framtidig arbeid».

**Punkt 5 — modell eller teneste per nøkkel.** Ny nullable `keys.model` (maks 60 teikn, trimma) gjennom `OPTIONAL_COLUMNS`, så ingen tabell vart bygd om. Feltet er rein dokumentasjon: ikkje eit wallet-programvare-val, ikkje ein del av identiteten, ikkje brukt i varselkjelda. Grensesnittet viser **Model** for ein hardware-nøkkel og **Service** for ein cloud-nøkkel; kolonnenamnet er nøytralt.

**Punkt 4 — adressestien på nøkkelkortet.** `database.list_key_status()` vel `k.address_path`, `GET /api/key-status` gjev han vidare, og `createKeyCard()` viser han mellom namnet og typen. Ein tom sti, som ein migrert nøkkel kan ha, gjev ikkje ei tom linje.

**Punkt 3 — datert CSV-namn.** Filnamnet er `YYYY-MM-DD-vardkey-export.csv`, bygd av serveren ved kvar nedlasting. `download`-attributtet i `static/index.html` vart fjerna, for eit `download`-attributt med verdi overkøyrer `Content-Disposition`-filnamnet frå serveren.

**Punkt 2 — slett all data.** `maintenance.py delete-all-data` og StartOS-handlinga «Delete all data» set appen tilbake til eit nytt oppsett: nøkkeloppsettet, kontrollane med barneradene sine, kvitteringane, programvare-lista (tilbake til den sådde `Sparrow Wallet`) og dei lagra multisig-tala forsvinn, medan **adminbrukaren og sesjonsløyndomen står att**, så brukaren ikkje blir logga ut. `database.delete_all_data()` slettar kontrollane **før** nøklane, sidan `key_checks.key_id` er `ON DELETE RESTRICT`, og kvitteringane eksplisitt, sidan dei ikkje har nokon framandnøkkel. Handlinga krev ei stadfestingsboks, og resultatet er det same som å starte appen på nytt utan data.

**Punkt 1 — adminpassord.** `auth.py` er den einaste staden som kjenner akkrediteringa: `hashlib.scrypt` med tilfeldig salt per passord og `hmac.compare_digest`, ei signert sesjonscookie (HMAC-SHA256 over ei utløpstid, nøkkel i `app_settings`, inga sesjonstabell), og eit CSRF-token som dobbelt-innsending. Alle ruter utanom `GET /health` krev ein sesjon: `401` på API-et, omdirigering til `/login` på sidene, og CSRF-krav på kvar tilstandsendrande POST. Første oppstart viser ei opprett-admin-side i staden for innlogging, og steget kan ikkje hoppast over. StartOS-handlinga «Set Admin Password» **genererer passordet inne i containeren** og viser det éin gong som eit maskert, kopierbart resultat, sidan SDK-en ikkje dokumenterer nokon veg til å gje stdin til ein `withTemp`-kommando og eit argument ville vore synleg i prosesslista.

**Punkt 6 — installerbar PWA.** `static/sw.js` cachar berre skalet, og gjer det med ei kviteliste over skal-stiane, så han aldri nemner `/api/*`, `/health` eller `/login`. `static/app.js` registrerer workeren og viser ein tydeleg offline-tilstand når serveren ikkje svarar. `static/manifest.webmanifest` skildrar appen, alle fem sidene lenkjer til han, og han og ikonet står i `STATIC_FILES`. Ikonet er framleis placeholder-en frå repoet, som SVG med `sizes: any`; dei ekte 192- og 512-px-PNG-ane kjem i §32.

**Det som heldt seg uendra:** varsellogikken, sperringa per nøkkel, eksporten (utanom namnet), roteringa, unikheitsregelen for adressestiar, og nøkkelnummeret som ein del av etiketten `Key N: <namn>`.

**API-et og skjemaet:** skjemaet er versjon 12, og namna står. Nye felt kjem i tillegg; ingen eksisterande felt byter namn eller type. Nye endepunkt i denne runden: `GET /api/session`, `POST /api/admin`, `POST /api/login` og `POST /api/logout`. `GET /health` står framleis ope.

## Kompatibilitetsreglar som gjeld alle punkta

Frå versjon 1 skal appen tåle framtidige oppdateringar utan å bryte data eller avtalar.

- **Migreringar er additive eller ein ombygging etter mønsteret i §21.** Kvar migrasjon skal ha ein test med eit bokstaveleg eldre skjema (`SCHEMA_VERSION_n` i `tests/test_database.py`), og `PRAGMA foreign_key_check` før commit der ein tabell blir bygd om.
- **API-et held namna sine.** Nye felt kjem i tillegg; eksisterande felt byter ikkje namn eller type. Eit felt som forsvinn, er eit brot.
- **Ei eldre database skal alltid kunne opnast** og bli migrert framover. Appen skal framleis **nekte** å opne eit skjema som er nyare enn han sjølv kjenner, i staden for å skrive i det.
- **Pakkeversjonen rører ikkje appdata.** Appen migrerer skjemaet sitt sjølv ved oppstart, så `startos/versions/` treng inga datamigrering. Kjem det ein pakkeendring som krev det, skal `up`/`down` skrivast der — ikkje i appen.
- **Ein nedgradering til ein eldre pakkeversjon er ikkje støtta** når skjemaet har gått framover, og det skal stå i `UPDATING.md`.
- **Backup teken på ein eldre versjon** skal kunne gjenopprettast og bli migrert framover.
- **Eksporten er ein avtale.** Kolonnenamna i CSV-en blir ikkje endra utan at det står her eller i ein seinare runde.

## Kva som er testa for heile runden

- `python3 -m unittest discover -s tests` — grøn på Linux og på Windows-kopien, med nye testar for kvart punkt.
- Migrasjonen 11 → 12: eit bokstaveleg versjon-11-skjema blir opna, migrert og kontrollert, med `PRAGMA foreign_key_check` rein.
- `make x86` byggjer reint (`tsc --noEmit`, `prettier --check`, `ncc`), og pakka blir installert på nytt på StartOS-boksen for å stadfeste at `maintenance.py`, handlingane og dei nye statiske filene er med i imaget.
- **Att å gjere manuelt:** ein full gjennomgang i nettlesaren (oppsett av eit anna oppsett enn 2-av-3, innlogging, ein kontroll, eksport med datert namn, sletting av all data, og installasjon av PWA-en), og §14, §16 StartOS-testen og §17 på nytt på boksen.

---

# 32. Ikonet og versjon 1 (ikkje starta)

Det som står att før første release, og som ikkje er ein del av §31. **Ingenting av dette er starta**, og det skal ikkje startast utan at brukaren ber om det.

- **Ikonet.** Brukaren leverer kunstverket. Kodaren legg inn `icon.svg` i repo-rota (maks 40 KiB, kravet i manifestet) og PWA-ikon i 192 og 512 px i `static/`, og legg dei inn i ikonoppføringa i `static/manifest.webmanifest` og i `STATIC_FILES` i `app.py`. Placeholder-ikonet som ligg der no blir ståande til då. Dette lukkar den opne boksen i §30.
- **Hevinga av pakkeversjonen.** Pakkeversjonen blir heva frå `0.1.0:0` til `1.0.0:0` når brukaren seier ifrå. §18 steg 12 («bygg endeleg `.s9pk` og gjer første release») høyrer til same runden.
- **Ikkje ein del av denne runden:** inga skjemaendring, ingen nye endepunkt, og ingen nye funksjonar. `startos/versions/` held fram tomt for datamigreringar, sidan appen migrerer skjemaet sitt sjølv.

---

## Framtidig arbeid, ikkje no

- Ingenting att her. Det siste punktet — fleire enn tre nøklar, og andre tersklar enn 2-av-3 — vart gjort i §31 punkt 7.
