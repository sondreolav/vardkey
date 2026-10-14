# TODO — VardKey for StartOS 0.4.0

## Mål

Bygg ein **enkel lokal web-app** som køyrer som ein StartOS 0.4.0-service.

Appen skal hjelpe éin brukar å gjennomføre og dokumentere ein årleg health check av eit **multisig-oppsett** (standard 2-av-3 med tre nøklar; terskel og talet på nøklar er valfritt). Namn, type, modell og adressesti blir konfigurerte ved første oppstart.

Appen skal **berre registrere resultat og historikk**. Han skal ikkje signere Bitcoin-transaksjonar, handtere private nøklar eller utføre wallet-operasjonar.

## Språkkrav

- Brukargrensesnittet, app-tekst, kjeldekode, variabel- og funksjonsnamn, kommentarar og teknisk dokumentasjon skal vere på engelsk.
- `TODO.md` er på norsk; dette er det einaste unntaket.

## Om dokumentet

- **§1–§18 er kravspecen og gjeld som han står.** Han skildrar appen slik han er no, ikkje slik han vart bygd.
- **§19–§31 er historikk.** Alle rundane der er ferdige og verifiserte, og står no som éi linje kvar. Reglane deira ligg i §1–§18 og i `ai-note.md`, som er handoveren.
- **§32 er runden som går no.** §32.4 (bug-rapporten) er utført i rundane 32-A og 32-B, med unntak av BR-003, som berre brukaren kan lukke. Resten av §32 står att.
- **Reglane under «Reglar som gjeld alle rundar» er bindande** for kvar framtidig endring.
- Eit punkt utan avkryssingsboks er implementert og verifisert. `[ ]` markerer det som står att.
- **Status:** alt til og med §31 er implementert og verifisert, og §32.4 er utført i rundane 32-A og 32-B (sjå §32), med unntak av BR-003, som berre brukaren kan lukke. Skjema **versjon 12**, testsuiten grøn (**475 testar**), og StartOS-pakka er bygd, sideloda og køyrd på ein eigen StartOS 0.4.0-boks. Pakkeversjonen står på `0.1.0:0` og blir ikkje heva før §32 er ferdig og brukaren seier ifrå.

---

# 1. Scope for første versjon

**Dette skal vere med**

- Ein enkel web-app med dashboard.
- Registrering av nøklane i multisig-oppsettet.
- Registrering av årleg health check, med kontroll av alle punkta i den årlege sjekklista.
- Varsel når eit kontrollpunkt krev oppfølging.
- Historikk over gjennomførte health checks.
- Automatisk forslag til neste sjekk, ca. eitt år fram i tid.
- Rapporteksport i CSV-format.
- Lokal SQLite-database.
- Persistent lagring på StartOS.
- StartOS health check.
- StartOS backup og restore.
- Passordvern med ein adminbrukar, og ein veg til å nullstille appdata frå StartOS.

**Dette skal ikkje vere med**

Ingen AI-integrasjon, ingen Bitcoin-node-integrasjon, ingen Bitcoin-signering, ingen PSBT-generering eller signering, ingen seed phrase-lagring, ingen private key-lagring, ingen cloud sync av appdata, ingen ekstern database, ingen offline-database og ingen offline-registrering av kontrollar (ein installerbar PWA utan offline-data er tillaten), ingen kalenderintegrasjon, ingen avansert analyse eller grafar, og inga støtte for fleire multisig-oppsett — det er framleis berre **eitt** oppsett, men terskelen og talet på nøklar i det er valfrie.

**Merk:** dette er eit varig forbod, ikkje ei oppgåveliste. Det skal stadfestast på nytt før release.

---

# 2. Viktige reglar for appen

- Appen skal aldri spørje etter seed phrase, private keys, PIN, passord eller wallet-hemmelegheiter, og aldri lagre slike. Det gjeld *wallet*-hemmelegheiter: adminpassordet er den einaste akkrediteringa appen lagrar, og han blir lagra som ein `hashlib.scrypt`-hash, aldri i klartekst.
- Eit fritekstfelt avviser eit innlimt wallet-hemmelegheit lokalt, før noko blir lagra (sjå §15), og kvart fritekstfelt har ei kort åtvaring ved feltet.
- Kontaktinformasjon til nøkkelhaldarar skal ikkje lagrast; berre om kontaktinfo er stadfesta.
- Appen skal ikkje late som han sjølv har utført ein hardware-test. Brukaren registrerer resultatet av testen.
- Appen skal vere lokal og enkel. Dersom noko ikkje er nødvendig for den årlege health check-en, skal det ikkje byggjast.

---

# 3. Nøkkeloppsettet

Appen er bygd for **eitt** multisig-oppsett. Ved første oppstart gjev brukaren terskelen og talet på nøklar, og kvar nøkkel får namn, type (`hardware`/`cloud`), ein valfri modell/teneste og ein adressesti.

- Terskelen er `1 ≤ threshold ≤ key_count`, og `2 ≤ key_count ≤ 15`. Appen legg inga meining i tala sine.
- Namnet brukaren skriv, er produktetiketten overalt: skjema, varsel, historikk og CSV-eksport. Nøkkelnummeret blir vist saman med namnet der det trengst, t.d. `Key 1: ColdCard`.
- Nøkkeltypen styrer kontrollane, aldri nøkkelnummeret.
- `type` og `address_path` er identiteten til nøkkelen og er låste etter oppsettet. Namnet og modellen kan endrast i innstillingane. Berre ei rotering, som byter ut nøkkelen med ein ny, kan gi han den andre typen.

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
- `type` blir lagra éin gong ved første oppstart og er låst etterpå; berre ei rotering kan gi nøkkelen den andre typen.
- `model` er valfri fri tekst (maks 60 teikn) og er rein dokumentasjon: ein hardware-modell eller, for ein cloud-nøkkel, namnet på tenesta. Han er ikkje ein del av identiteten, ikkje eit wallet-programvare-val, og blir ikkje brukt i varselkjelda.
- `provider` lagrar det konfigurerte nøkkelnamnet og den valde programvara, ikkje faste produktnamn.
- `contact_info_verified` er fri tekst med to verdiar, og har ingen «not assessed»-verdi.
- `hardware_works` er obligatorisk for ein tilgjengeleg hardware-nøkkel.
- `name` kan endrast i innstillingane; `type` og `address_path` er identiteten til nøkkelen.
- `address_path_verified` blir sett av serveren ut frå ei samanlikning med `keys.address_path`, og blir ikkje sendt inn av brukaren.
- `wallet_software` i `health_checks` held fram som fri tekst, slik at eldre rader og fjerna listeelement held fram å visast rett.
- `address_path` må vere unik på tvers av alle nøklane i oppsettet: i oppsettet, i innstillingane og ved rotering. Samanlikninga er kanonisk: `h`/`H` og `'` er same markør, og luft og store/små bokstavar blir ignorerte. Den lagra verdien blir aldri skriven om.
- `reason` i `alert_acknowledgements` lagrar namnet på handlinga som lukka varselet, ikkje ein fri tekst.
- `key_id` i `alert_acknowledgements` lagrar nøkkelen varselet høyrde til, eller `NULL` for eit programvarevarsel frå innstillingslista.
- `tool_checks` finst ikkje. `device`, `seed_backup_status`, `address_verified`, `derivation_height`, `cloud_health_status` og `cloud_provider_operational` finst ikkje.

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
- **Adressesti (alle nøklar):** brukaren registrerer berre `Address path`, førehandsutfylt med nøkkelen sin lagra sti. Serveren samanliknar den innsende stien med `keys.address_path` etter den kanoniske regelen i §4: lik → `OK`, ulik → `PROBLEM`.
- Når nøkkelen ikkje er tilgjengeleg, blir resten skjult og ikkje kravd.
- Stemmer ikkje stien, viser nettlesaren eit påminningsvarsel før innsending, og kontrollen blir lagra som ein nøkkel som ikkje kunne kontrollerast.

## Steg 3 — Compatibility (03 / Compatibility)

- Brukaren vel éi wallet-programvare: eit namn frå innstillingane, eller namnet på ein konfigurert cloud-nøkkel. Ein cloud-nøkkel er låst til sitt eige namn.
- `Software version` blir registrert for alle nøklar, òg ein cloud-nøkkel.
- `OK` eller `PROBLEM`, med kommentar ved problem.
- For ein cloud-nøkkel er `Wallet software` og `Compatibility status` skjulte og utleidde.
- Når nøkkelen ikkje er tilgjengeleg, er feltet skjult og valfritt.

## Steg 4 — External research (04 / External research)

- Leverandørar per innsending: den valde nøkkelen (ved namn) og den valde programvara.
- Registrer status (`SECURE` / `PATCHED` / `VULNERABLE` / `COMPROMISED`) og ein kort kommentar.
- Berre den valde nøkkelen og den valde programvara blir registrerte. Appen kontaktar ikkje KI sjølv.
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
- Eit nøkkelkort viser namn, adressesti, modell/teneste og type, og ei tydeleg melding når nøkkelen har eit ope varsel, i tillegg til datoane sine: kor mange varsel som står ope, at nøkkelen ikkje kan kontrollerast før dei er lukka, kva handling som lukkar det første, og ei lenkje til varsellista.

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
- Ei tekstcelle som eit rekneark ville lese som ein formel — `=`, `+`, `-`, `@` eller eit kontrollteikn, òg etter leiande mellomrom — får ein leiande apostrof, slik at ho blir tekst. Kolonnenamna, kolonnerekkjefølgja og alle vanlege verdiar er uendra.
- Nøkkelnamnet og nøkkeltypen kjem frå oppsettet, og namnet er namnet nøkkelen har no.
- Nedlastinga heiter `YYYY-MM-DD-vardkey-export.csv`, med datoen serveren har når han svarar.
- Siste kolonne, `Follow-up closed`, listar varsla som vart lukka på kontrollen, som `code: action (YYYY-MM-DD)`. Berre lukkingar som høyrer til ein nøkkel, blir viste.

---

# 11. Backend

- SQLite med initialisering og migrering. Skjemaet er versjon 12.
- Lagring av nøklar, health checks, historikk og rapporteksport.
- Varsellogikken (§7).
- Health endpoint, som er det einaste endepunktet utanfor innlogginga.
- Valider input på serveren, og bruk parameteriserte SQL-spørringar.

Minimumsendepunkt: `GET /health`, `GET /api/keys`, `GET /api/health-checks`, `GET /api/health-checks/:id`, `POST /api/health-checks`, `GET /api/export`.

**Merk:** `GET /api/session`, `POST /api/admin`, `POST /api/login`, `POST /api/logout`, `GET /api/setup`, `POST /api/setup`, `GET /api/settings`, `POST /api/settings/keys`, `POST /api/settings/wallet-software`, `POST /api/keys/<id>/rotate`, `POST /api/alerts/acknowledge`, `GET /api/key-status`, `GET /api/previous-values` og `GET /api/alerts` er ekstra endepunkt utanom minimumslista, fordi oppsettsteget, innstillingane, dashboardet, skjemaet og innlogginga treng dei. Dei står ikkje i spesifikasjonen enno.

- `POST /api/health-checks` krev éin konfigurert nøkkel, `available` og gyldige, relevante resultat, og avviser manglande eller dupliserte registreringar.
- `POST /api/health-checks` krev ikkje programvare eller KI-status når nøkkelen ikkje kunne kontrollerast, og avviser slike resultat med `400`.
- `POST /api/health-checks` avviser ein nøkkel som har eit ope varsel, med `409`, og regelen blir handheva før resten av valideringa.
- `POST /api/setup` lagrar multisig-tala og nøkkeloppsettet éin gong med namn, type, modell og adressesti, og avviser eit nytt oppsett med `409`.
- `POST /api/setup`, `POST /api/settings/keys` og `POST /api/keys/<id>/rotate` avviser ein adressesti som ein annan nøkkel alt har (`400` i oppsettet og roteringa, `409` i innstillingane). Samanlikninga er kanonisk, sjå §4.
- `GET /api/settings` gjev nøklane med adressestien og modellen deira og lista over wallet-programvare.
- `POST /api/settings/keys` lagrar eit nytt namn og ein modell, og ein adressesti så lenge nøkkelen ikkje har nokon lagra kontroll. Typen er aldri med i payloaden.
- `POST /api/settings/wallet-software` lagrar heile lista, og lukkar varsla til ei programvare som blir fjerna.
- `POST /api/keys/<id>/rotate` roterer ein nøkkel med ein ny, unik adressesti, kan gi nøkkelen den andre typen, og kvitterer ut varsla hans.
- `POST /api/keys/<id>/rotate` avviser med `409` ein typeendring som ville gjort nøkkelen til ein cloud-nøkkel under eit namn som wallet-programvare-lista alt har.
- `POST /api/alerts/acknowledge` kvitterer ut eit varsel med `code`, `source` og handlinga som lukkar det.
- `GET /api/health-checks/<id>` gjev òg `closed_alerts`, lukkingane som høyrer til kontrollen.
- Feilkodar: ugyldig payload `400`, ukjend nøkkel eller varsel `404`, låst eller duplikat adressesti `409`, øydelagd database `500`, manglande eller ugyldig sesjon `401`, og manglande eller ugyldig CSRF-token `403`. Eit fritekstfelt som ser ut som ei wallet-løyndom er òg ein `400` (sjå §15).

---

# 12. Frontend

- Enkel responsiv web-UI. Enkelheit går framfor grafisk kompleksitet.
- Tydlege statusfelt, og faste val der statusen skal vere ein avgrensa verdi.
- Vis problem tydeleg, og vis kva som står att før ein health check kan lagrast.
- Skjul felt som ikkje gjeld for vald nøkkel eller vald programvare, og skjul programvare og KI-status når nøkkelen ikkje kunne kontrollerast. Eit skjult `required`-felt blokkerer innsendinga, så flagget må alltid clearast når feltet blir skjult.
- Eige oppsettsteg ved første oppstart: terskel, talet på nøklar, og namn, type, modell og adressesti per nøkkel.
- Eit innloggingssteg framfor alt anna, og eit opprett-admin-steg når ingen admin finst enno.
- Skjemaet viser kva nøklar som er sperra av eit ope varsel, og kva handling som lukkar det.
- Eit påminningsvarsel før innsending når adressestien ikkje stemmer.
- Innstillingsside med `01 / Wallet software` og `02 / Key rotation`, bygd for fleire tema seinare. Nøkkelnamnet, modellen, adressestien til ein nøkkel utan lagra kontroll, og roteringa med ny type blir alle endra i roteringsseksjonen, og éin knapp lagrar alt. Det finst ikkje lenger ein eigen `01 / Keys`-seksjon.
- Varselknappane har den teksten og det stadfestingssteget som høyrer til handlinga si, og varselet om programvare-inkompatibilitet peikar på innstillingane.
- Kvart fritekstfelt har ei kort åtvaring ved feltet, i tillegg til sidenotisen, med stilen `.secret-warning` (§15).
- Appen skal kunne installerast som ein PWA utan offline-data.
- Sørg for at appen fungerer godt i vanleg StartOS-browser.

---

# 13. StartOS 0.4.0

Appen er éin enkel StartOS-service.

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

**Merk:** alle ti punkta er oppfylte. Pakka ligg i repoet, er bygd til `vardkey_x86_64.s9pk`, sideloda og køyrd på ein eigen StartOS 0.4.0-boks. To handlingar ligg i `Actions & Config`: `Delete all data` og `Set Admin Password`.

Unngå: Postgres, Redis, ekstern backend, ekstern cloud-service for appdata, og ekstra container utan konkret behov.

**Merk:** dette er eit varig forbod, ikkje ei oppgåveliste. Det skal stadfestast på nytt før release.

---

# 14. Lagring og backup

- SQLite-database skal liggje på persistent volum.
- Appdata skal overleve restart.
- Konfigurer StartOS backup av persistent data.
- Test backup og test restore.
- Verifiser at gamle health checks finst etter restore.

**Merk:** alle punkta er køyrde og verifiserte på boksen, gjennom §16 StartOS-testen og §17. `startos/backups.ts` brukar `sdk.Backups.ofVolumes('main')`, og databasen ligg på `main`-volumet på `/data`. StartOS stoppar servicen medan ein backup går, så databasefila er ikkje under skriving når ho blir kopiert — ingen eigen SQLite-snapshot-krok trongst, og inga kjend avgrensing står att. Punkta skal køyrast på nytt når §32 er ferdig, sidan skjemaet og innlogginga har endra seg.

---

# 15. Sikkerheit og personvern

- Ingen seed phrase, private keys, wallet-passord eller sky-tokens i databasen.
- Ingen unødvendige personopplysningar. Kontaktinfo blir berre registrert som status (`Confirmed current` / `Needs external update`).
- Valider input på serveren, og bruk parameteriserte SQL-spørringar.
- Ikkje implementer eigen kryptografi. Adminpassordet brukar `hashlib.scrypt` frå standardbiblioteket, og sesjonen ein HMAC-SHA256-signatur.
- Ikkje send data til eksterne tenester.
- Adressestien er ein offentleg derivasjonssti og inneheld inga hemmelegheit.
- Fritekst blir sjekka lokalt i `secret_guard.py` før lagring, og før lengdegrensa til feltet. Eit felt som ser ut som ei wallet-løyndom, blir avvist med `400`, ingenting blir lagra, og meldinga gjentek aldri verdien. Sjekken gjer ingen nettverkskall. Han er ei sperre mot dei vanlegaste formata, ikkje eit vern: eit nakent 64-teikns heks-streng, ei frase på eit anna språk, og ei løyndom delt over fleire felt, blir ikkje fanga.

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
- Test at to nøklar ikkje kan ha same adressesti, korkje i oppsettet, i innstillingane eller ved rotering, òg når den andre er skriven med `h`-markøren.
- Test kvar varselhandling, og at eit varsel utan handlingar blir rekna som ein feil.
- Test at eit nøkkelkort viser ei varselmelding når nøkkelen har eit ope varsel.
- Test at fjerning av den feilande programvara lukkar `software_incompatible`.
- Test at eit lukka varsel viser seg i historikken og i CSV-en, med handling og dato.
- Test at eit kontaktvarsel gir `Needs action` og sperrar nøkkelen, og at nøkkelen blir ledig att ved `contact_updated`.
- Test at `software_incompatible` med ei cloud-nøkkel-programvare gir `replace_hardware` på den kontrollerte nøkkelen, og at det same varselet frå innstillingslista held fram med `remove_software`.
- Test at ein kan byte namn på ein nøkkel i roteringsseksjonen utan å rotere han, og at ei rotering krev stadfestingsboksen.
- Test at ei rotering kan gi nøkkelen den andre typen, og at eit namn som wallet-programvare-lista alt har, blir avvist.
- Test innlogging og sesjon: første oppstart utan admin, rett og feil passord, `401` på API utan sesjon, omdirigering på sider, open `/health`, og eit manglande CSRF-token.
- Test at eit fritekstfelt som ser ut som ei wallet-løyndom, blir avvist, at meldinga seier kva ho ser ut som, og at ingenting blir lagra eller eksportert.
- Test at ein CSV-celle som byrjar med `=`, `+`, `-`, `@` eller eit kontrollteikn, blir eksportert som tekst, og at vanleg innhald er uendra.
- Test oppsett av eit annet multisig-oppsett enn 2-av-3, modell/teneste per nøkkel, det daterte eksportnamnet, sletting av all data, og installasjon av PWA-en.

**Merk:** dei manuelle nettlesartestane er køyrde og verifiserte fram til §31. §32 legg til nye manuelle punkt.

## StartOS-test

- Installer `.s9pk` på StartOS 0.4.0, start servicen og opne web UI.
- Utfør ein komplett test-check.
- Restart servicen, og verifiser at data framleis finst.
- Ta backup, restore backup, og verifiser data etter restore.
- Verifiser at `Set Admin Password` og `Delete all data` står i `Actions & Config` og verkar.
- Verifiser at ein installerbar PWA kan leggjast til frå nettlesaren.

**Merk:** alle er køyrde og verifiserte på boksen. `vardkey_x86_64.s9pk` vart sideloda og installert, servicen står som `Running`, helsesjekken melder «The web interface is ready», og `Open UI` opnar VardKey i nettlesaren på StartOS-adressa. Restart og restore heldt på dataa, og dei gamle health checkane fanst etter restore. Skal køyrast på nytt når §32 er ferdig.

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
- Appen er passordbeskytta med ein adminbrukar.
- All appdata kan nullstillast frå StartOS, medan adminbrukaren står att.

**Merk:** alle punkta er køyrde og verifiserte på boksen. Kriterielista er oppfylt, men pakkeversjonen blir ikkje heva før §32 er ferdig — sjå §32.

---

# 18. Arbeidsrekkefølgje for AI-programmeraren

Utfør oppgåvene i denne rekkjefølgja og ikkje hopp fram til avanserte funksjonar:

- 1–8. Grunnleggande web-app, SQLite og datamodellen, nøklane, health check-skjemaet, lagring og historikk, varsellogikken, dashboardet og rapporteksport.
- 9. Implementer StartOS package.
- 10. Implementer persistent storage og backup.
- 11. Test restart og restore.
- [ ] 12. Bygg endeleg `.s9pk` og gjer første release.

**Merk:** steg 1–11 er ferdige. Steg 12 ventar på §32.

**Testar:** køyr `python3 -m unittest discover -s tests`. Suiten skal vere grøn både på Linux og på Windows-kopien.

**Hovudregel:** Bygg den minste løysinga som oppfyller lista over. Ikkje legg til nye funksjonar, tenester eller arkitektur utan at dei er nødvendige for punkta i denne TODO-lista.

---

# Reglar som gjeld alle rundar

Desse er bindande for kvar framtidig endring, ikkje berre for éin runde.

- **Migreringar er additive, eller ein ombygging etter mønsteret i §21.** Kvar migrasjon skal ha ein test med eit bokstaveleg eldre skjema (`SCHEMA_VERSION_n` i `tests/test_database.py`), og `PRAGMA foreign_key_check` før commit der ein tabell blir bygd om.
- **API-et held namna sine.** Nye felt kjem i tillegg; eksisterande felt byter ikkje namn eller type. Eit felt som forsvinn, er eit brot.
- **Ei eldre database skal alltid kunne opnast** og bli migrert framover. Appen skal framleis **nekte** å opne eit skjema som er nyare enn han sjølv kjenner, i staden for å skrive i det.
- **Pakkeversjonen rører ikkje appdata.** Appen migrerer skjemaet sitt sjølv ved oppstart, så `startos/versions/` treng inga datamigrering. Kjem det ein pakkeendring som krev det, skal `up`/`down` skrivast der — ikkje i appen.
- **Ein nedgradering til ein eldre pakkeversjon er ikkje støtta** når skjemaet har gått framover, og det skal stå i `UPDATING.md`.
- **Backup teken på ein eldre versjon** skal kunne gjenopprettast og bli migrert framover.
- **Eksporten er ein avtale.** Kolonnenamna i CSV-en blir ikkje endra utan at det står her eller i ein seinare runde.
- **Forbodslistene i §1 og §13 skal stadfestast på nytt før release.**

---

# 19–31. Historikk (ferdige og verifiserte)

Alle rundane under er implementerte og verifiserte. Reglane deira ligg i §1–§18 og i `ai-note.md`; den fulle grunngjevinga ligg i git-historikken. Detaljane er ikkje gjengjevne her, sidan ingen av dei er opne lenger.

| Runde | Kva han gjorde |
|---|---|
| §19 | Registrering per nøkkel: éi innsending gjeld éin vald nøkkel, og kvar nøkkel har sitt eige neste-sjekk-intervall. |
| §20 | Eit felt som ikkje gjeld for den valde nøkkelen eller programvara, blir skjult og utleidd, og alt utleidd blir lista i Review-oppsummeringa. |
| §21 | Engelske statusverdiar (`IKKJE_VURDERT` → `NOT_ASSESSED`) og `GET /api/alerts`, som summerer alle lagra kontrollar og listar kritiske først. Skjema 11. |
| §22 | Ein nøkkel som ikkje kunne kontrollerast, registrerer ingenting elles: `wallet_software` blir `NULL`, `software_compatibility_status` blir `NOT_ASSESSED`, og eit innsend resultat er ein `400`. |
| §23 | Konfigurerbart nøkkeloppsett ved første oppstart; `GET`/`POST /api/setup`. |
| §24 | Obligatoriske val (`Hardware works`, kontaktstadfestinga) og skjemastrukturen i seks seksjonar. BIP327/SLIP39 og `tool_checks` fjerna. |
| §25 | Adressestien som identitet, rotering, varselkvittering og innstillingar. |
| §26 | Sperring av ein nøkkel med ope varsel (`409`), unike adressestiar, og eigne lukkehandlingar per varselkode. |
| §27 | Varselhandlingane i historikk og CSV, kontaktvarselet som eit nøkkelvarsel, og dei to formene av `software_incompatible`. Skjema 11. |
| §28 | Nøkkeltypen kan berre endrast ved ei rotering, og namnet blir endra i roteringsseksjonen. |
| §29 | Namnebyte til **VardKey**, med beskrivinga «Bitcoin Multisig Health Monitor», databasefila `data/vardkey.sqlite3` og eksportfila `vardkey-export.csv`. |
| §30 | StartOS 0.4.0-pakka: `id: 'vardkey'`, `volumes: ['main']`, `GPL-3.0-only`, bygd og verifisert på boksen. Pakkeversjonen startar på `0.1.0:0`. |
| §31 | Dei sju punkta før versjon 1: fleksibel terskel (skjema 12), modell/teneste per nøkkel, adressestien på nøkkelkortet, datert CSV-namn, sletting av all data, adminpassord med sesjon og CSRF, og ein installerbar PWA utan offline-data. |

---

# 32. Det som står att

Seks punkt, alle **før** pakkeversjonen blir heva frå `0.1.0:0` til `1.0.0:0`. §32.4 er utført i rundane 32-A og 32-B; resten står att, og eit punkt skal ikkje startast utan at brukaren ber om det.

**Status i §32:** 32.4 er utført i rundane 32-A og 32-B. Der står berre **BR-003** att, og han er ei manuell ende-til-ende-verifisering som berre brukaren kan gjere. 32.1, 32.2, 32.3, 32.6 og 32.5 står framleis att, og ingen av dei er starta.

## 32.1 Ikonet

- Brukaren leverer kunstverket. Kodaren legg inn `icon.svg` i repo-rota (maks 40 KiB, kravet i manifestet) og PWA-ikon i 192 og 512 px i `static/`, og legg dei inn i ikonoppføringa i `static/manifest.webmanifest` og i `STATIC_FILES` i `app.py`.
- Placeholder-ikonet som ligg der no — ein SVG med `sizes: "any"`, som er det manifest-testen sjekkar — blir ståande til kunstverket kjem.
- Dette lukkar den opne boksen i §30.

## 32.2 UI-finpuss

Ein gjennomgang av dei fem sidene for konsistens og ryddigheit, utan nye funksjonar:

- Same ord og same knappetekst for same handling på alle sidene, og same tone i hjelpetekstane.
- Kvar liste har ein tydeleg tom-tilstand, og ingen tekst er klypt, overfylt eller broten på ein smal telefon.
- Alle felt, val og feilmeldingar ser like ut der dei gjer same nytte, og feilmeldingane seier kva brukaren skal gjere.
- Den tydelege offline-tilstanden frå PWA-en held fram å vere tydeleg, også etter inn- og utlogging.
- Den korte åtvaringa ved kvart fritekstfelt, som runde 32-B la inn, skal sjå lik ut på alle sidene. Brukaren har stadfesta at ho er lesleg på ein telefon, så det som står att der, er berre at ho ser lik ut overalt.

## 32.3 Gjennomgang av meldingstekstane i varsla

- Kvar av dei elleve varselradene i §7 har ein `message` i `alerts.py`. Gå gjennom alle og gjer dei like i form: kva som er gale, kva nøkkel eller programvare det gjeld, og kva som lukkar varselet.
- Meldingane er engelske, korte og konkrete, og seier ikkje at appen sjølv har gjort noko.
- Oppdater testane som held på meldingstekstane, og hald varselkodane og handlingane uendra.

## 32.4 Bug-rapporten

- Arbeid gjennom `BUG-RAPPORT-AI-AGENT.md` (BR-001–BR-008): **verifiser kvart funn i koden først**, rett dei som blir stadfesta med små, målretta endringar, legg til regresjonstestar, og rapporter kva som var stadfesta, kva som var falske positive, og kva som ikkje kunne avgjerast.
- **Rapporten er skriven mot eit anna filsett enn dette repoet.** Han ber om `SECURITY.md`, `PRIVACY.md`, `THREATMODEL.md`, `PLATFORM-ACCESS.md`, `ENCRYPTION.md`, `OFFLINE.md`, `AI-STATUS.md` og `DATA-MODEL.md`, og ingen av dei finst her. BR-001, BR-004 og delar av BR-002 kviler på dei. Verifiser mot filene som faktisk ligg i repoet i staden, og meld frå om kva som fell bort av den grunn.
- **BR-001** (`P0 dersom stadfesta`) gjeld at kjeldefilene skulle mangle i repo-visinga. Dei ligg i `main` og er spora av Git, så han skal kunne lukkast som falsk positiv etter ein `git ls-tree -r --name-only HEAD`.
- **BR-002** er den tyngste: fritekstfelta (`name`, `model`, `comments` og notatfelta) kan lagre ei seed phrase eller ein privatnøkkel brukaren limer inn ved eit uhell. Ei realistisk lokal sperre mot dei vanlegaste wallet-format, i tillegg til ei åtvaring ved kvart fritekstfelt, er innanfor grensene i §2 og §15 — men ikkje send noko til ein ekstern teneste, og ikkje logg feltinnhald.
- **BR-005, BR-006, BR-007 og BR-008** krev ein verifikasjon først: autentisering og CSRF, CSV-formelinjeksjon, PWA-cachen og normaliseringa av adressestiar.
- Ikkje hev pakkeversjonen, ikkje byt ikonet, og ikkje legg til nye tenester eller infrastruktur som del av denne jobben.

**Utfall av runde 32-A (bug-triarge).** Kvar BR vart verifisert i koden som ligg i dette repoet før noko vart endra:

- **BR-001 — falsk positiv.** Kjeldefilene ligg i `main` og er spora av Git; rapporten bygde på repo-visinga, ikkje på ein checkout.
- **BR-002 — stadfesta, utsett.** Eit fritekstfelt kan framleis lagre ei løyndom brukaren limer inn ved eit uhell. Arbeidet høyrde til 32-B og vart ikkje starta i 32-A.
- **BR-003 — stadfesta som formulering, men han kviler på ein tekst som ikkje finst.** Sjå «Det som står att i 32.4» nedanfor.
- **BR-004 — fell bort.** `AI-STATUS.md` og `DATA-MODEL.md` finst ikkje i dette repoet. Koden følgjer alt kontrakten i §4–§7: statusane `SECURE`/`PATCHED`/`VULNERABLE`/`COMPROMISED`, tabellane `keys`, `health_checks`, `key_checks`, `ai_security_checks`, `wallet_software`, `alert_acknowledgements` og `app_settings`, og inga `tool_checks`. Den reelle dokdrifta er 32.6.
- **BR-005 — verifisert i koden, inga åtferdsendring.** Berre `GET /health`, `GET /api/session` og `/login` er opne; alle andre `/api/*` svarar `401` og sidene svarar `302` til `/login`; kvar tilstandsendrande POST krev ei gyldig økt og CSRF-tokenet (`403`). Passordet er ein `hashlib.scrypt`-hash med salt per passord, økta er ein HMAC-SHA256-signert cookie med utløp, og begge samanlikningane brukar `hmac.compare_digest`. Ingen `X-Forwarded-*`-header blir lesen. Det einaste som ikkje kan stadfestast her, er `Secure`-flagget mot den reelle StartOS-proxyen: flagget er medvite utelate fordi StartOS terminerer TLS og proxyar rein HTTP inn i containeren.
- **BR-006 — stadfesta og retta i `export.py`.** Kvar tekstcelle som byrjar med `=`, `+`, `-`, `@` eller eit kontrollteikn — òg etter leiande mellomrom — blir no prefiksa med ein apostrof. Kolonnenamna, kolonnerekkjefølgja og vanlege verdiar er uendra.
- **BR-007 — stadfesta og retta i `static/sw.js`.** Tenestearbeidaren lagrar no eit svar berre når det er vellukka, same-opphav og ikkje omdirigert, så loginsida kan ikkje lenger erstatta det cacha app-skalet.
- **BR-008 — stadfesta og retta i `validation.py`.** Samanlikninga av adressestiar fellar no den harda markøren (`h`/`H` ≡ `'`) i tillegg til store/små bokstavar og luft, så same derivasjonssti i to skrivemåtar blir avvist som duplikat i oppsettet, i innstillingane og ved rotering — og blir rekna som nøkkelen sin eigen sti i kontrollen. Den lagra verdien blir aldri skriven om.

**Nye bindande reglar frå 32-A:** (dei står òg i §4, §10 og §11)

- **Eksporten nøytraliserer formelceller.** Ei tekstcelle som eit rekneark ville lese som ein formel, får ein leiande apostrof. Kolonnenamna, kolonnerekkjefølgja og formatavtalen elles står fast.
- **Adressestien blir samanlikna kanonisk.** Same derivasjonssti i kvar av dei støtta skrivemåtane er den same stien, både for unikheit og for samanlikninga i kontrollen.
- **PWA-cachen lagrar berre eit gyldig skal-svar.** Eit svar som ikkje er vellukka, ikkje er same-opphav eller er omdirigert, blir ikkje cacha.

**Utfall av runde 32-B (BR-002).** Sperra mot wallet-løyndomar i fritekst er no på plass:

- **Ny modul `secret_guard.py`.** Han held den engelske BIP39-ordlista (2048 ord, bakt inn lokalt — appen gjer framleis ingen nettverkskall) og ein `find_secret()` som kjenner att eit PEM-privatnøkkelblock, ein utvida privatnøkkel (`xprv`/`yprv`/`zprv`/`tprv`/`uprv`/`vprv`), ein WIF-nøkkel (51 eller 52 teikn), ein BIP38-nøkkel og eit ordløp på 12 eller fleire BIP39-ord. Funksjonen gjev berre ei kort engelsk nemning attende, aldri teksten, så ingenting hamnar i ein logg eller ein feilmelding.
- **`validation.py` avviser slikt innhald i kvart fritekstfelt.** Sjekken sit i dei fire teksthjelparane (`_text`, `_key_name`, `_model`, `_required_path`), så kvart fritekstfelt er dekt av konstruksjon: nøkkelnamn, modell, wallet-programvarenamn, programvareversjon, firmware-versjon, notatfelta og KI-kommentarane. Han kastar `SecretDetected`, som er ein `ValidationError`, så svaret blir `400` og ikkje `500`. Valideringa køyrer før noko blir skrive, så eit avvist innhald blir aldri lagra delvis.
- **Sjekken køyrer òg før lengdegrensa til feltet.** Eit innlimt løyndom blir difor svara med kva det ser ut som, ikkje med «too long» — som elles ville bedt brukaren om å korte ned eit seed phrase i staden for å fjerne det. Lengdegrensa står framleis som ytre grense og gjeld for alt anna. Rekkjefølgja er medvite vald og festa i testar, både for eit løyndom som passar i feltet og eit som ikkje gjer det.
- **`auth.py` avviser òg eit adminbrukarnamn som ser ut som ei løyndom**, med same rekkjefølgje. Passordet blir medvite ikkje sjekka, sidan ein lang passfrase er eit legitimt passord og ei avvising der ville stengje brukaren ute frå sin eigen konto.
- **Meldinga gjentek aldri verdien.** Ho namngjev feltet og forma som vart kjend att, og seier at ingenting vart lagra.
- **Åtvaring ved kvart fritekstfelt i UI-et.** Ei kort linje i same ambra-palett som sidenotisen, lagd inn i `static/health-check.html`, `static/health-check.js`, `static/setup.html`, `static/setup.js` og `static/settings.js`, med stilen `.secret-warning` i `static/styles.css`. Sidenotisen om løyndomar står framleis, og sideoverskriftene er uendra.
- **Kjende avgrensingar** står i modulens docstring og blir ikkje tona ned: eit nakent 64-teikns heksadesimalt streng blir ikkje avvist (det kan like gjerne vere ein transaksjons-id, som er legitimt notatinnhald), berre den engelske ordlista blir brukt, og eit format utanom mønstra eller ei løyndom som er delt over fleire felt, blir ikkje fanga.

**Nye bindande reglar frå 32-B:** (dei står òg i §2, §12 og §15)

- **Fritekst blir sjekka lokalt før lagring, og før lengdegrensa til feltet.** Eit felt som ser ut som ei wallet-løyndom, blir avvist med `400` og med kva det ser ut som, ingenting blir lagra, og meldinga gjentek aldri verdien. Sjekken er lokal og gjer ingen nettverkskall.
- **Kvar fritekstfelt har ei åtvaring ved feltet**, i tillegg til sidenotisen, og stilen er `.secret-warning`.

**Testar lagde til:** ti i runde 32-A (fem i `tests/test_export.py`, ein i `tests/test_pwa.py` og fire i `tests/test_validation.py`) og 43 i runde 32-B, alle i den nye `tests/test_secret_guard.py` (5 ordlistetestar, 10 gjenkjenningstestar, 17 feltnivåtestar, 6 åtvaringstestar og 5 API-testar). Suiten gjekk frå 422 til **475 testar**, stadfesta grøn av brukaren.

**Det som står att i 32.4:** berre **BR-003**, og han må lesast rett. Rapporten vart skriven mot eit anna filsett og siterer ein §31-tekst om at den manuelle gjennomgangen står att, men den teksten finst ikkje lenger, og §16 og §17 seier at dei manuelle nettlesartestane og bokstestane vart køyrde og verifiserte fram til §31. Det som faktisk står att, er difor dei **nye** manuelle punkta §32 legg til — ikonet (32.1), UI-pussen (32.2), varseltekstane (32.3), at åtvaringa ved felta ser lik ut på alle sider (32.2), og heile bokstesten på nytt etter endringane (32.5) — og ei stadfesting frå brukaren på at dei er køyrde. Alt anna i rapporten er avgjort: BR-001 er ein falsk positiv, BR-004 fell bort, BR-005 er verifisert utan åtferdsendring, og BR-002, BR-006, BR-007 og BR-008 er retta med regresjonstestar. To manuelle punkt under 32-B er alt stadfesta av brukaren: at eit seed phrase blir stoppa i namnefeltet og i adressestifeltet, og at åtvaringa ved felta er lesleg på ein telefon.

## 32.5 Hevinga av pakkeversjonen

- Pakkeversjonen blir heva frå `0.1.0:0` til `1.0.0:0` når punkta over er ferdige og brukaren seier ifrå. §18 steg 12 («bygg endeleg `.s9pk` og gjer første release») høyrer til same runden.
- Inga skjemaendring, ingen nye endepunkt og ingen nye funksjonar i denne runden. `startos/versions/` held fram tomt for datamigrasjonar, sidan appen migrerer skjemaet sitt sjølv.

## 32.6 Dokumentasjonsdrifta

Dokumenta som skildrar pakka og appen, er skrivne før §31 og før 32-A og 32-B, og dei er framleis ikkje oppdaterte. Dette punktet rettar dei. Det må gjerast **etter** 32.1–32.3 og **før** 32.5, slik at dokumenta skildrar den utgåva som faktisk blir gitt ut, og det svarar samstundes på resten av BR-004 i bug-rapporten.

- `README.md` (pakke-README): «Actions: None» og `actions: []` i Quick Reference stemmer ikkje — pakka har to handlingar, `Delete all data` og `Set Admin Password`. Fyrstegongsflyten manglar admin-steget, og «Limitations» manglar at terskel og nøkkeltal er valfrie (`2 ≤ key_count ≤ 15`), at databasen ligg ukryptert på volumet, og at fritekst blir sjekka lokalt.
- `docs/application.md` (app-referansen): API-tabellen manglar `GET /api/session`, `POST /api/admin`, `POST /api/login` og `POST /api/logout`, og han skildrar korkje innloggingsvakta (`401` på API, `302` til `/login` på sider, `403` utan CSRF-token) eller kva ruter som er opne. Han manglar òg formelnøytraliseringa i CSV-en, den kanoniske stisamanlikninga og den lokale sperra mot wallet-løyndomar, og setninga om at den manuelle StartOS-testen framleis står ope er utdatert.
- `instructions.md`: manglar innloggingssteget, opprettinga av admin og dei to handlingane i `Actions & Config`. «exactly three keys … another threshold is not supported» er feil etter §31 punkt 7.
- `UPDATING.md`: seier skjema **11**; det er **12**. Versjoneksempla og tag-regelen skal framleis stå.
- `AGENTS.md`: modullista nemner ikkje `secret_guard.py`, og testavsnittet nemner ikkje at suiten òg dekkjer sperra.
- `startos/manifest/i18n.ts` og `startos/i18n/dictionaries/`: kort- og langskildringa seier «a fixed 2-of-3 … the three keys» på fem språk. Skal ordlyden bli «eit multisig-oppsett, 2-av-3 som standard», må alle fem språka skrivast om, og `make x86` køyrer `prettier --check startos`.

Ikkje bygg om overskriftstrukturen i `README.md` (han følgjer rettleiinga), og ikkje legg til nye dokument. Dei åtte filene bug-rapporten nemner (`SECURITY.md`, `PRIVACY.md`, `THREATMODEL.md`, `PLATFORM-ACCESS.md`, `ENCRYPTION.md`, `OFFLINE.md`, `AI-STATUS.md`, `DATA-MODEL.md`) skal **ikkje** opprettast. Dokumenta i repoet er `README.md`, `docs/application.md`, `instructions.md`, `UPDATING.md`, `AGENTS.md` og `TODO.md`.
