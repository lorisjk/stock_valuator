# `parsers/parse_edgar.py`
 
## Zweck
 
Dieses Modul ist die **Zusammenführungs-Ebene** zwischen den EDGAR-Rohdaten (`fetchers/edgar.py`) und dem finalen, benutzbaren DataFrame. Es kennt keine EDGAR-API-Details mehr (kein Netzwerk, kein Caching), sondern nutzt nur noch die bereits extrahierten Jahreswerte aus `edgar.py` und bringt sie in eine einheitliche Tabellenform.
 
Klare Aufgabenteilung zu `fetchers/edgar.py`:
- `edgar.py` → weiß, wie man **einen einzelnen** XBRL-Tag ausliest
- `parse_edgar.py` → weiß, wie man **mehrere Tags/Konzepte für eine ganze Firma** zu einer Tabelle zusammenbaut
---
 
## Funktionen im Überblick
 
| Funktion | Zweck | Input | Output |
|---|---|---|---|
| `extract_merged_annual_values` | Priorisiert mehrere Kandidaten-Tags, nimmt pro Jahr den ersten Treffer | us-gaap-Dict, Liste von Tag-Namen, Flag `is_point_in_time` | Liste von `{end, value, filed}` |
| `build_dataframe` | Baut aus allen konfigurierten Konzepten ein sortiertes DataFrame für einen Ticker | Ticker, CompanyFacts-Dict, `CONCEPT_CANDIDATES`-Dict | `pd.DataFrame` mit Spalten `ticker, concept, end, value` |
 
---
 
## Wichtige Design-Entscheidungen
 
### 1. Fallback-Priorisierung (`extract_merged_annual_values`)
Für Konzepte, die über die Zeit ihren XBRL-Tag gewechselt haben (z. B. Revenue durch die ASC-606-Umstellung 2018: erst `Revenues`, dann `RevenueFromContractWithCustomerExcludingAssessedTax`).
 
Prinzip: Kandidaten-Tags werden in Prioritätsreihenfolge (neuester/gebräuchlichster zuerst) durchprobiert. Für jedes Jahr gilt: **der erste Tag, der einen Wert liefert, gewinnt** – sobald ein Jahr im `merged`-Dict steht, wird es von nachfolgenden Tags nicht mehr überschrieben (`if v["end"] in merged: continue`).
 
Wichtig: Das ist bewusst **anders** als `extract_summed_annual_values` aus `edgar.py` – dort werden mehrere Tags **addiert** (z. B. kurzfristige + langfristige Schulden), hier wird nur der **beste einzelne** genommen. Diese Unterscheidung steuert das `mode`-Feld in `CONCEPT_CANDIDATES` (`"fallback"` vs. `"sum"`).
 
### 2. Konfigurationsgetriebenes Design (`CONCEPT_CANDIDATES`)
`build_dataframe` selbst enthält **keine** Kennzahlen-spezifische Logik – alles Wissen darüber, welche Tags zu welchem Konzept gehören, ob es ein Stichtags- oder Zeitraumwert ist, und ob summiert oder priorisiert wird, steckt in der Konfigurationsstruktur (`config.py`):
 
```python
CONCEPT_CANDIDATES = {
    "<logischer Name>": {
        "tags": [...],            # Kandidaten-Tags, priorisiert nach Reihenfolge
        "point_in_time": bool,    # True = Bilanz-Stichtag, False = Zeitraum
        "mode": "fallback"|"sum", # wie mehrere Tags kombiniert werden
    },
}
```
 
Vorteil: Ein neues Konzept hinzufügen bedeutet nur einen neuen Dict-Eintrag in `config.py`, kein Code-Change in `build_dataframe`.
 
### 3. Sortierung am Ende (`sort_values(...).reset_index(drop=True)`)
Python-Dicts behalten die Einfügereihenfolge – da verschiedene Tag-Kandidaten in unterschiedlicher chronologischer Reihenfolge einsortiert werden können (z. B. erst die neuen Jahre über Tag A, dann die alten Jahre über Tag B), kommt das ungefilterte Ergebnis **nicht chronologisch sortiert** heraus. `sort_values(["ticker", "concept", "end"])` behebt das explizit, `reset_index(drop=True)` macht die Zeilennummerierung danach wieder sauber durchgehend.
 
---
 
## Häufige Fehler aus der Entwicklung (zur Erinnerung für später)
 
1. **Falsche Datenstruktur beim Zusammenführen** – ursprünglich wurde beim Merge nur `{"value": ..., "filed": ...}` gespeichert, das `end`-Datum selbst (der Dict-Key) ging beim finalen `list(merged.values())` verloren. Merke: Wenn ein Wert aus einem Dict-Key gebraucht wird, muss er explizit **mit in den Value** gepackt werden, nicht nur implizit als Key vorhanden sein.
2. **Überflüssige/fehlerhafte innere Schleife** – ein Versuch, `concept_candidates[key]` nochmal manuell zu durchlaufen und `concept_data` zu prüfen, *bevor* `extract_merged_annual_values` aufgerufen wurde. Das war redundant (die Fallback-Logik steckt ja schon in der aufgerufenen Funktion) und fehlerhaft (die Schleifenvariable wurde bei jedem Kandidaten überschrieben, sodass am Ende nur der letzte Tag geprüft wurde – unabhängig davon, ob ein früherer Kandidat schon Daten hatte).
3. **Falscher Spaltenwert für `concept`** – `"concept": concept` (der zuletzt durchprobierte, evtl. gar nicht existierende Tag-Name) statt `"concept": key` (der logische, stabile Name aus der Konfiguration). Würde dazu führen, dass in derselben Spalte je nach Ticker unterschiedliche, verwirrende Tag-Namen statt eines einheitlichen Kennzeichners stehen.
4. **`if concept_data is None` als Abbruchkriterium verwendet**, obwohl `values` (eine Liste) die eigentlich relevante Rückgabe war. Korrekt: `if not values: continue` – prüft, ob die Liste leer ist, nicht ob ein einzelnes Rohdaten-Objekt fehlt.
5. **Scheinbare "kaputte" Daten, die tatsächlich korrekt waren** – ein erstes Testergebnis zeigte alle Jahre nicht chronologisch sortiert (z. B. 2017–2025 vor 2007–2016). Sah nach einem Fehler aus, war aber nur die von Dicts nicht garantierte Sortierreihenfolge – inhaltlich waren alle Jahre korrekt und ohne Duplikate vorhanden. Erst der Duplicate-Check (`df.duplicated(...)`) hat das zweifelsfrei bestätigt, statt sich auf den ersten optischen Eindruck zu verlassen.
---
 
## Zusammenspiel mit `config.py`
 
`build_dataframe` ist bewusst **unabhängig** von `config.py` gehalten – sie bekommt `concept_candidates` als Parameter übergeben, statt es selbst zu importieren. `main.py` importiert `CONCEPT_CANDIDATES` aus `config.py` und reicht es durch. Das hält `parse_edgar.py` wiederverwendbar (z. B. testbar mit einer eigenen, kleineren Test-Konfiguration), ohne Abhängigkeit von der globalen Projekt-Konfiguration.
 








