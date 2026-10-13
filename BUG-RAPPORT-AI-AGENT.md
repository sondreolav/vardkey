# Bug- og sikkerheitsrapport for AI-agent

**Prosjekt:** `ai-bot/helsesjekk` / VardKey  
**Dato:** 2026-10-13  
**Mål:** Verifiser funna nedanfor, rett stadfesta feil med små og målretta endringar, legg til regresjonstestar og dokumenter testresultata.

## Instruks til agenten

1. Start med å lese `AGENTS.md`, `README.md`, `TODO.md`, `SECURITY.md`, `PRIVACY.md`, `THREATMODEL.md`, `PLATFORM-ACCESS.md`, `ENCRYPTION.md`, `OFFLINE.md`, `AI-STATUS.md` og `DATA-MODEL.md` dersom dei finst i checkouten. Bruk den nyaste og mest konkrete spesifikasjonen i `TODO.md` (§§ 1–18 og § 31) som gjeldande funksjonskrav; ikkje implementer eldre motstridande dokument utan å avklare/oppdatere dei.
2. Verifiser kvart funn i faktisk kjeldekode før du konkluderer. For hypotesar merkte **VERIFISER**, skriv ein test som demonstrerer om feilen finst. Ikkje rapporter ei hypotese som stadfesta sårbarheit utan reproduksjon.
3. Rett stadfesta feil og legg til regresjonstestar. Ikkje berre skriv ei ny analyse eller TODO-liste.
4. Køyr `python3 -m unittest discover -s tests` og, dersom pakkefilene er til stades, `make x86`. Oppgi kva som faktisk vart køyrt og resultatet. Ikkje påstå at StartOS- eller nettlesartestar er køyrde utan å ha gjort dei.
5. Følg prosjektgrensene: ikkje legg til skytenester, AI-integrasjon, wallet-/signeringsfunksjonar eller ny infrastruktur. Ikkje be brukaren om seed phrase, private keys, PIN eller passord. Ikkje logg fritekst eller autentiseringshemm løyndomar. Ikkje hev pakkeversjonen til `1.0.0:0` eller erstatt ikon-placeholderen; `TODO.md` § 32 seier at dette krev eiga godkjenning.

## Oppsummering og prioritet

| ID | Prioritet | Status ved første gjennomgang | Tema |
|---|---|---|---|
| BR-001 | P0 dersom stadfesta | Må verifiserast i checkout | Repo-vising og dokumentasjon er i konflikt om kjeldefilene finst |
| BR-002 | P1 | Stadfesta krav-/risikokonflikt | Fritekst kan lagre lommebokløyndomar sjølv om produktkravet seier at dei aldri skal lagrast |
| BR-003 | P1 | Stadfesta testgap i spesifikasjonen | Ende-til-ende-test etter innlogging, datasletting og PWA er framleis oppført som attståande |
| BR-004 | P2 | Stadfesta dokumentasjonskonflikt | Ulike statusverdiar og ulike datamodellar i dokumenta |
| BR-005 | P1 | VERIFISER | Sesjon, cookie-attributt, CSRF og autentiseringsvern for alle ruter |
| BR-006 | P2 | VERIFISER | CSV-formelinjeksjon via brukarstyrte tekstfelt |
| BR-007 | P2 | VERIFISER | PWA/service worker kan ikkje cache personlege data eller omgå innlogging ved offline bruk |
| BR-008 | P2 | VERIFISER | Normalisering og unikheit for adressestiar |

---

## BR-001 — Kjeldefiler manglar i den offentlege repo-visinga

**Prioritet:** P0 dersom det blir stadfesta at kjeldefilene faktisk manglar; elles lukk som falsk positiv etter dokumentasjon.  
**Område:** Repo-/byggintegritet.

### Observasjon

Den offentlege rotvisinga viser Markdown-filer og oppgir `Languages: Markdown 100%`, medan den nyaste `TODO.md` seier at appen inneheld mellom anna `app.py`, `auth.py`, `database.py`, `maintenance.py`, `tests/`, `static/`, `startos/`, `Dockerfile`, `Makefile` og `package.json`.

- Repo: https://gitea.sondreolav.com/ai-bot/helsesjekk
- Gjeldande krav/status: https://gitea.sondreolav.com/ai-bot/helsesjekk/src/branch/main/TODO.md

Dette kan skuldast ei avgrensing i repo-visinga, feil branch eller at kjeldekode ikkje er committa. Det er ikkje forsvarleg å føresetje kva forklaring som er rett utan å kontrollere checkouten.

### Arbeid

- Køyr `git status --short`, `git branch --show-current` og `git ls-tree -r --name-only HEAD`.
- Stadfest at kjeldekode, testar og pakkefiler som TODO/README viser til, finst i branch `main` og er spora av Git.
- Dersom filer manglar: finn ut om dei er sletta, ignorerte, ligg i feil branch eller aldri vart committa. Gjenopprett den tilsikta prosjektstrukturen eller rett dokumentasjonen til den faktiske strukturen.
- Ikkje generer erstatningskode basert berre på beskrivingar og lat som han er originalimplementasjonen.

### Godkjenningskriterium

Ein rein clone av den tiltenkte branch-en inneheld alle filene som dokumentasjonen viser til, og bygg/test-kommandoane kan køyrast frå repo-rota. Dersom repoet med vilje berre skal innehalde dokumentasjon, må alle påstandar om køyrbar app, testar og StartOS-pakke rettast.

## BR-002 — Fritekst kan lagre løyndomar i klartekst

**Prioritet:** P1 (personvern-/sikkerheitsrisiko).  
**Område:** `label`, `notes`, `comments`, database og eksport.

### Observasjon

Produktkravet seier at appen aldri skal spørje etter eller lagre seed phrase, private keys, PIN, passord eller wallet-hemmelegheiter (`TODO.md` § 2). Samstundes tillèt datamodellen fleire fritekstfelt, og spesifikasjonen seier at innhaldet ikkje blir skanna. `ENCRYPTION.md` dokumenterer at live SQLite-database ligg ukryptert på disken. Dermed kan ein brukar ved eit uhell lime inn ei seed phrase eller anna løyndom i eit kommentar-/notatfelt, og appen lagrar henne trass i forbodet.

Relevante dokument:
- https://gitea.sondreolav.com/ai-bot/helsesjekk/src/branch/main/TODO.md
- https://gitea.sondreolav.com/ai-bot/helsesjekk/src/branch/main/DATA-MODEL.md
- https://gitea.sondreolav.com/ai-bot/helsesjekk/src/branch/main/ENCRYPTION.md
- https://gitea.sondreolav.com/ai-bot/helsesjekk/src/branch/main/PRIVACY.md

### Arbeid

- Finn alle fritekstfelt og alle stader teksten blir lagra, vist, logga eller eksportert.
- Lag ein realistisk, lokal safeguard mot vanlege format for wallet-hemmlegheiter (til dømes `xprv`/private-key-format og sannsynlege BIP39-fraseinnlimingar). Ikkje send innhald til eksterne tenester. Unngå å skrive feltinnhald i loggar eller feilmeldingar.
- Kombiner dette med tydeleg advarsel direkte ved kvart fritekstfelt og ei kort, forståeleg avvising når innhaldet blir stoppa. Vurder falske positive: ikkje blokker vanlege notat utan grunn.
- Dersom robust deteksjon ikkje er mogleg, dokumenter avgrensinga tydeleg og innfør minst streng lengdegrense, åtvaring ved feltet og trygg handtering. Ikkje påstå at fråvær av dedikerte kolonnar åleine garanterer at ingen løyndomar blir lagra.
- Kontroller at data som blir avviste, ikkje blir lagra delvis i SQLite eller kopierte til loggar.

### Regresjonstestar / godkjenningskriterium

- Test farlege eksempel for fleire typar løyndomar og vanleg, uskuldig fritekst.
- Avviste verdiar blir ikkje lagra og kjem ikkje med i historikk/CSV.
- Testane må ikkje innehalde ekte løyndomar; bruk syntetiske eksempel.
- Ingen nettverkstrafikk eller ekstern analyse blir introdusert.

## BR-003 — Ufullført manuell ende-til-ende-verifisering etter store endringar

**Prioritet:** P1 før release.  
**Område:** Autentisering, oppsett, sletting, PWA og StartOS-integrasjon.

### Observasjon

`TODO.md` § 31 introduserer adminpassord/sesjon, sletting av data og installerbar PWA. Same dokument seier eksplisitt at full manuell nettlesargjennomgang framleis står att: alternativt multisig-oppsett, innlogging, ein kontroll, datert eksport, sletting av data og PWA-installasjon; § 14, § 16 og § 17 skal òg køyrast på nytt. Dette er særleg viktig fordi autentisering og sletting påverkar tilgang og dataintegritet.

Kjelde: https://gitea.sondreolav.com/ai-bot/helsesjekk/src/branch/main/TODO.md (særleg §§ 31 og «Kva som er testa for heile runden»).

### Arbeid

- Køyr først automatiserte testar; rett feil dei avdekkjer.
- Utfør den manuelle gjennomgangen på den faktiske appen og StartOS 0.4.0 dersom miljøet er tilgjengeleg.
- Kontroller: første oppsett og obligatorisk oppretting av admin; login/logout; utløpt/ugyldig sesjon; direkte API-kall utan innlogging; full kontroll og CSV; alternativ terskel/nøkkeltal; datasletting med stadfesting; restart/backup/restore; PWA offline/online og etter logout.
- Registrer kvar test som bestått/feila/ikkje køyrd. Ikkje marker release-kriteriet som oppfylt berre fordi unit-testane er grøne.

### Godkjenningskriterium

Alle scenario er verifiserte i nettlesar/StartOS, eller tydeleg merkte som ikkje køyrde med grunn. Feil som blir funne, får eigne automatiserte regresjonstestar der det er mogleg.

## BR-004 — Motstridande statusverdiar og datamodell i dokumentasjonen

**Prioritet:** P2; kan bli P1 dersom implementasjonen faktisk brukar feil enum/schema.  
**Område:** Datamodell, validering, UI, varsling, eksport og agentinstruksjonar.

### Observasjon

Dokumenta gir to ulike kontraktar:

- `AI-STATUS.md` listar `ok`, `vulnerable`, `compromised`, `unknown` og skildrar éin status på kvar kontroll.
- Nyare `TODO.md` § 5 krev `SECURE`, `PATCHED`, `VULNERABLE`, `COMPROMISED`; § 4 skildrar `ai_security_checks` med `provider` og `status`, altså status per leverandør.
- `DATA-MODEL.md` brukar dessutan eldre tabellnamn (`settings`, `setup`, `key`, `check`, `key_check`, `tool_check`) som ikkje samsvarar med dei seinare namna i TODO (`app_settings`, `keys`, `health_checks`, `key_checks`, `ai_security_checks`).

Kjelder:
- https://gitea.sondreolav.com/ai-bot/helsesjekk/src/branch/main/AI-STATUS.md
- https://gitea.sondreolav.com/ai-bot/helsesjekk/src/branch/main/DATA-MODEL.md
- https://gitea.sondreolav.com/ai-bot/helsesjekk/src/branch/main/TODO.md

### Arbeid

- Fastset kva spesifikasjon som er autoritativ, med `TODO.md` §§ 4–7 som utgangspunkt.
- Kontroller faktiske enum-verdiar i SQLite-skjema, servervalidering, UI, varselgenerering, API-responsar, historikk og CSV.
- Oppdater dei utdaterte dokumenta slik at dei speglar den implementerte og vedtekne kontrakten. Ikkje migrer data eller endre API berre for å få nyare kode til å passe med utdaterte dokument.
- Sørg for at ugyldige eller gamle verdiar blir handterte eksplisitt, ikkje stille konverterte til ein annan trygg status.

### Regresjonstestar / godkjenningskriterium

Ein test for kvar tillaten status, ugyldig status, historikk/CSV og leverandørkopling. Ei statusendring må ikkje feilaktig lukke eit aktivt sikkerheitsvarsel.

## BR-005 — Verifiser autentisering, session-cookie og CSRF-beskyttelse

**Prioritet:** P1 dersom kontroll manglar; elles dokumenter verifikasjonen.  
**Status:** VERIFISER — offentleg dokumentasjon omtalar scrypt, signert cookie og CSRF-token, men eg har ikkje fått inspisert kjeldekoden eller køyrt appen.

### Arbeid

- Kartlegg alle HTTP-ruter. Verifiser at `GET /health` er einaste uautentiserte rute, og at han berre returnerer minimal readiness-info (ikkje konfigurasjon, secrets, exception-trace eller persondata).
- Test direkte tilgang til kvar `/api/*`-rute før login, etter logout og med utløpt/forfalska cookie. API-et skal svare med 401, ikkje returnere data eller gi HTML som klienten mistolkar som JSON.
- Kontroller cookie-attributta `HttpOnly`, `SameSite` og `Secure` i faktisk StartOS-proxyoppsett. TLS blir terminert av StartOS, så ikkje stol blindt på klientstyrte `X-Forwarded-*`-headarar. Verifiser at cookie blir sett sikkert bak proxyen.
- Verifiser CSRF-kontroll på alle tilstandsendrande ruter, inkludert adminoppsett, login/logout, nøkkelrotering, innstillingar, kvittering av varsel og sletting av data. Test både manglande token og token frå ein annan sesjon/opphav.
- Kontroller sesjonsutløp, signaturvalidering og at passord/session-secret aldri blir sendt til klienten eller logga. Verifiser også trygg feilatferd ved feil i auth-/databaseoppsett.

### Godkjenningskriterium

Automatiserte testar viser at ikkje-autentiserte og CSRF-forfalska kall ikkje kan lese eller endre appdata. Cookie-oppsett er testa bak den reelle reverse proxyen; ingen tryggleikseigenskap blir berre føresett frå utviklingsserveren.

## BR-006 — Verifiser CSV-formelinjeksjon

**Prioritet:** P2 dersom eksporterte tekstar kan bli tolka som formlar.  
**Status:** VERIFISER.

### Observasjon / risiko

CSV-eksporten inkluderer brukarkontrollerte namn, programvarenamn og kommentarar (`TODO.md` § 10). Dersom slike felt blir skrivne direkte til CSV og fila blir opna i eit rekneark, kan celleverdiar som byrjar med `=`, `+`, `-`, `@`, tab eller kontrollteikn bli tolka som formlar. CSV-sitatteikn åleine er ikkje nok til å avverje dette.

### Arbeid

- Test eksport med syntetiske celleverdiar som byrjar med dei nemnde prefiksa, også etter mellomrom/CR/LF og i Unicode-kanttilfelle.
- Dersom verdiane kan bli formeluttrykk, innfør ei dokumentert, konsistent nøytralisering av tekstceller før CSV-skriving utan å øydeleggje vanlege data. Hald kolonnenamn og CSV-formatavtalen stabile. Ikkje endre numeriske/dato/statusfelt feilaktig.

### Godkjenningskriterium

Testar demonstrerer at brukarstyrte tekstverdiar blir eksporterte som tekst og ikkje som reknearkformlar. Vanleg CSV-innhald er framleis korrekt.

## BR-007 — Verifiser PWA-cache, offline-tilstand og logout

**Prioritet:** P2 dersom persondata eller autentiserte sider blir cachelagde/tilgjengelege offline.  
**Status:** VERIFISER.

### Observasjon / risiko

`TODO.md` seier at service worker skal cache eit kvitelista app-skal, aldri `/api/*`, `/health` eller `/login`. Det må òg sikrast at statiske sider ikkje inneheld servergenererte persondata, at gamle cache-versjonar ikkje beheld sensitive skjermar, og at offline-/logout-tilstand ikkje gir inntrykk av at brukaren framleis er autentisert.

### Arbeid

- Inspiser `static/sw.js`, cache-nøklar og fallback-strategi. Test at alle API-kall og svar med privat data er `network-only`/ikkje cachelagde.
- Test innlogging → opne appen → logout → offline; sjekk at ingen data frå tidlegare sesjonar er synlege eller kan sendast.
- Test oppdatering av appen med gammal cache frå før oppdateringa, og at cache kan bytast/slettast kontrollert.
- Verifiser at service worker ikkje fangar opp `POST`-kall eller returnerer ein cached 200 for ein beskytta API-rute.

### Godkjenningskriterium

Ingen personlege kontrollar, API-svar, innloggingssvar eller sesjonssensitive sider blir cachelagde. Offline-modus viser ein tydeleg offline-tilstand og opnar ikkje for redigering eller innsending utan server.

## BR-008 — Verifiser kanonisering og unikheit for adressestiar

**Prioritet:** P2; P1 dersom to ulike nøklar kan bli registrerte med same faktiske derivation path.  
**Status:** VERIFISER.

### Observasjon / risiko

Spesifikasjonen krev at adressestien er identitet for nøkkelen og unik på tvers av oppsett, innstillingar og rotering (`TODO.md` § 4 og § 31). Kontroller om unikheitskontrollen berre samanliknar rå strengar. Same BIP32-sti kan bli uttrykt med alternative apostrof-/`h`-notasjonar eller ujamn whitespace; dersom dei blir tolka som same sti, kan rein strengsamanlikning tillate ein duplikat.

### Arbeid

- Finn kvar adressestiar blir trimma, validerte, samanlikna og lagra (oppsett, innstillingar, rotering og direkte API-kall).
- Bestem ein avgrensa kanonisk representasjon som samsvarar med støtta inputformat. Avvis ugyldig format på serveren, ikkje berre i nettlesaren. Ikkje anta at to stiar er like utan ei spesifisert normaliseringsregel.
- Test duplikat med ulik whitespace og alle alternative notasjonar appen faktisk støttar.

### Godkjenningskriterium

Serveren avviser duplikate/ugyldige stiar konsekvent på alle inngangar, og eksisterande data blir ikkje stille endra av normalisering.

---

## Avsluttrapport frå agenten

Når arbeidet er ferdig, svar med:

1. Funn som var stadfesta, falske positive og framleis uløyste.
2. Kva filer som vart endra, med ei kort forklaring per endring.
3. Kva regresjonstestar som vart lagde til.
4. Nøyaktig kva kommandoar som vart køyrde og resultata deira.
5. Eventuelle manuelle StartOS-/nettlesartestar som ikkje kunne køyrast, utan å markere dei som beståtte.