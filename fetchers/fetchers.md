
# `fetchers/edgar.py`
 
## Zweck
 
Dieses Modul kapselt **alles, was mit SEC EDGAR zu tun hat**: Rohdaten holen (mit Caching), Ticker in CIK-Nummern übersetzen, und aus den verschachtelten XBRL-Rohdaten saubere Jahres-Zeitreihen extrahieren.
 
Kein Netzwerk-Code außerhalb dieser Datei sollte EDGAR-URLs oder die rohe JSON-Struktur kennen müssen – alles, was "wie spricht man mit EDGAR" bedeutet, ist hier gekapselt.
 
---
 
## Funktionen im Überblick
 
| Funktion | Zweck | Input | Output |
|---|---|---|---|
| `fetch_or_cache` | Generischer HTTP-GET mit Datei-Cache | URL, Cache-Pfad, Headers | rohes Dict (aus JSON) |
| `build_ticker_to_cik` | Wandelt rohes Ticker-Mapping in schnellen Lookup um | rohes Mapping-Dict | `{ticker: cik}` |
| `get_cik` | Lookup: Ticker → CIK | Ticker, `{ticker: cik}`-Dict | CIK als 10-stelliger String |
| `get_company_info` | Holt CompanyFacts (alle XBRL-Daten) für eine Firma | Ticker, CIK, User-Agent | rohes CompanyFacts-Dict |
| `extract_annual_values` | Extrahiert **einen** Jahreswert pro Jahr aus einem einzelnen XBRL-Konzept | Konzept-Rohdaten, Flag `is_point_in_time` | Liste von `{end, value, filed}` |
| `extract_summed_annual_values` | Wie oben, aber summiert **mehrere** Tags pro Jahr (z. B. verschiedene Schuldenarten) | us-gaap-Dict, Liste von Tag-Namen, Flag | Liste von `{end, value}` |
 
---
 
## Wichtige Design-Entscheidungen
 
### 1. Caching-Pattern (`fetch_or_cache`)
Erst lokal nachschauen, nur bei Bedarf nachladen. Bewusst **generisch** gehalten (kennt keine EDGAR-Spezifika) – URL, Cache-Pfad und Headers kommen immer von außen, damit die Funktion auch für andere APIs (FMP, etc.) wiederverwendbar bleibt.
 
Wichtig: `os.makedirs(os.path.dirname(cache_path), exist_ok=True)` **vor** dem Schreiben – `open(path, "w")` legt keine fehlenden Ordner an, nur die Datei selbst.
 
### 2. Zeitraumwerte vs. Stichtagswerte (`is_point_in_time`)
Zwei grundverschiedene Datenarten in XBRL:
- **Zeitraumwerte** (Revenue, Net Income, Cashflow): haben `start` und `end`, gelten für eine Periode. Zusätzlicher Check: Zeitraum muss ~1 Jahr sein (350–380 Tage), um Quartalswerte auszufiltern, die fälschlich mit `fp: "FY"` getaggt sind.
- **Stichtagswerte** (Eigenkapital, Schulden, Cash): haben nur `end`, kein `start` – Bilanzpositionen zu einem bestimmten Datum. Kein Zeitraum-Check nötig/möglich.
Eine Funktion mit Flag statt zwei fast identischer Funktionen – vermeidet Code-Duplikation.
 
### 3. Deduplizierung nach `filed`-Datum
Firmen reichen manchmal berichtigte Zahlen nach (`10-K/A`). Für dasselbe `end`-Datum kann es mehrere Einträge mit unterschiedlichen Werten geben. Regel: der Eintrag mit dem **späteren `filed`-Datum** gewinnt (aktuellste/korrigierte Fassung). String-Vergleich (`>`) funktioniert hier nur, weil das Datumsformat `JJJJ-MM-TT` ist – bei anderen Formaten wäre das nicht sicher.
 
### 4. Tag-Wechsel über Zeit (gehört eigentlich zu `parsers/parse_edgar.py`, aber hier relevant)
Manche Konzepte ändern über die Jahre ihren XBRL-Tag-Namen (z. B. Revenue durch die ASC-606-Umstellung 2018). `extract_annual_values` selbst kennt das nicht – das Zusammenführen mehrerer Kandidaten-Tags passiert eine Ebene höher.
 
### 5. Automatische Einheiten-Erkennung
`extract_annual_values` nimmt **die erste verfügbare Einheit** aus `concept_data["units"]`, statt hart `"USD"` anzunehmen. Notwendig, weil z. B. EPS in `"USD/shares"` geführt wird, nicht in `"USD"`.
 
### 6. Summieren vs. Fallback
- **Fallback** (`extract_merged_annual_values`, in `parsers/`): "nimm den ersten Tag, der für dieses Jahr Daten hat" – für Konzepte, die sich gegenseitig über die Zeit ablösen (z. B. Revenue-Tags).
- **Summieren** (`extract_summed_annual_values`, hier): "addiere alle Tags pro Jahr" – für Konzepte, die tatsächlich **gleichzeitig nebeneinander existieren** und zusammengehören (z. B. `LongTermDebtNoncurrent` + `ConvertibleDebtNoncurrent` = Gesamtschulden).
---
 
## Häufige Fehler aus der Entwicklung (zur Erinnerung für später)
 
1. **Datei nicht gespeichert, bevor `main.py` lief** → `ImportError`/`AttributeError`, obwohl der Code "im Editor" richtig aussah. Merke: `python`/`import` sieht nur, was **auf der Platte** liegt, nicht was im Editor offen ist. Bei kryptischen Import-Fehlern immer zuerst mit `type dateiname.py` (Windows) / `cat dateiname.py` (Mac/Linux) prüfen, was tatsächlich gespeichert ist.
2. **Schleifenvariable überschreibt Funktionsparameter** – z. B. `def get_cik(ticker, cik_mapping): for ticker in cik_mapping: ...` – die Schleife überschreibt sofort den übergebenen `ticker`-Wert. Schleifenvariable und Parameter dürfen nie denselben Namen tragen, wenn beide gebraucht werden.
3. **Modul-Level-Code statt nur Funktionsdefinitionen** – ein Funktionsaufruf (`mapping = fetch_or_cache(...)`) direkt in `edgar.py` statt nur in `main.py` führte dazu, dass **jeder Import** von `edgar.py` diesen Code mit ausführte (unerwarteter Download beim bloßen Importieren). Fetcher-/Parser-Dateien sollten nur Funktionen *definieren*, nie aufrufen.
4. **`os.makedirs(...)` vergessen** vor `open(path, "w")` → `FileNotFoundError`, weil `open` zwar die Datei, aber nicht fehlende Zwischenordner anlegt.
5. **Falscher Key-Name geraten statt nachgeschaut** (`entry["cik"]` statt `entry["cik_str"]`) – immer zuerst einen Beispiel-Eintrag ausgeben (`print(list(mapping.values())[0])`), bevor man Keys benutzt.
6. **`.zfill()` auf einem `int` aufgerufen** statt auf einem `str` – `.zfill()` ist eine String-Methode, `cik_str` kam aber als Integer aus dem JSON. Erst `str(...)`, dann `.zfill(10)`.
7. **Verketteter Vergleich missverstanden**: `if ticker in TICKERS == ["AAPL"]:` wird von Python als **zwei** Bedingungen gelesen (`ticker in TICKERS` UND `TICKERS == ["AAPL"]`), nicht wie beabsichtigt. Führte dazu, dass der Block nie ausgeführt wurde.
8. **Hart codierte Einheit (`"USD"`)** statt generischer Ermittlung – EPS-Werte liegen unter `"USD/shares"`, nicht `"USD"`. Lösung: erste verfügbare Einheit automatisch ermitteln (`list(units.keys())[0]`), mit Schutz gegen leeres `units`-Dict.
9. **Fehlende Daten vorschnell als Bug interpretiert** – z. B. NVIDIA hatte in manchen Jahren tatsächlich keine langfristigen Schulden (oder sie steckten unter einem anderen Tag wie `ConvertibleDebtNoncurrent`/`PaymentsToAcquireProductiveAssets`). Lücken in Finanzdaten bedeuten nicht automatisch einen Code-Fehler – oft ist es fachlich erklärbar (Geschäftsjahresumstellung, Tag-Wechsel, reale Abwesenheit der Kennzahl).
---
 
## Offene / bewusst nicht vollständig gelöste Punkte
 
- `LongTermDebt` und `Capex` haben bei NVDA weiterhin Lücken (12 bzw. 8 von 19 Jahren) – bewusst akzeptiert, um nicht unverhältnismäßig viel Zeit in Nebenkennzahlen zu stecken.
- Keine automatische Tag-Erkennung – neue Ticker könnten neue, noch unbekannte Tag-Varianten verwenden, die manuell nachgetragen werden müssten.
 








