# Kennzahlen-Übersicht: Datenbasis & Aussagekraft
 
Stand: EDGAR-Fundamentaldaten (jährlich) vollständig gesammelt, Kursdaten (yfinance) noch ausstehend.
 
## Verfügbare Rohdaten (aus `historical_facts.csv`)
 
| Konzept | Bedeutung | Art |
|---|---|---|
| `Revenue` | Gesamtumsatz | Zeitraum |
| `NetIncomeLoss` | Nettogewinn (GAAP) | Zeitraum |
| `EPS` | Gewinn pro Aktie, verwässert | Zeitraum |
| `StockholdersEquity` | Eigenkapital | Stichtag |
| `OperatingIncomeLoss` | Operatives Ergebnis (EBIT-nah) | Zeitraum |
| `OperatingCashFlow` | Operativer Cashflow | Zeitraum |
| `LongTermDebt` | Verzinsliche Schulden (kurz- + langfristig, klassisch + Wandelanleihen) | Stichtag |
| `Capex` | Investitionen in Sachanlagen | Zeitraum |
| `CashAndEquivalents` | Zahlungsmittel und Äquivalente | Stichtag |
 
---
 
## Kennzahlen, die JETZT schon berechenbar sind (reine Fundamentaldaten, kein Kurs nötig)
 
| Kennzahl | Formel | Braucht | Sagt aus |
|---|---|---|---|
| **Umsatzwachstum (YoY)** | (Revenue Jahr N / Revenue Jahr N-1) − 1 | Revenue | Wie schnell wächst das Geschäft im Kerngeschäft |
| **GAAP-Gewinnwachstum (YoY)** | (NetIncomeLoss N / NetIncomeLoss N-1) − 1 | NetIncomeLoss | Wachstum des bilanzierten Gewinns – kann durch Sondereffekte verzerrt sein |
| **Operative Marge** | OperatingIncomeLoss / Revenue | OperatingIncomeLoss, Revenue | Wie viel vom Umsatz bleibt operativ übrig – Indikator für Preissetzungsmacht/Kostendisziplin |
| **Free Cashflow (FCF)** | OperatingCashFlow − Capex | OperatingCashFlow, Capex | Cash, der nach nötigen Reinvestitionen für Aktionäre/Schuldenabbau übrig bleibt |
| **FCF-Marge** | FCF / Revenue | FCF, Revenue | Wie viel Cash (nicht nur Buchgewinn) pro Umsatz-Euro erwirtschaftet wird |
| **ROE (Return on Equity)** | NetIncomeLoss / StockholdersEquity | NetIncomeLoss, StockholdersEquity | Wie effizient das Eigenkapital der Aktionäre verzinst wird |
| **Net Debt** | LongTermDebt − CashAndEquivalents | LongTermDebt, CashAndEquivalents | Tatsächliche Verschuldung nach Abzug der Cash-Reserven (negativ = mehr Cash als Schulden) |
| **Net Debt / Operating Income** (Annäherung an Net Debt/EBITDA, ohne Abschreibungen) | Net Debt / OperatingIncomeLoss | Net Debt, OperatingIncomeLoss | Wie viele Jahre operatives Ergebnis nötig wären, um die Nettoschulden zu tilgen – grobes Risikomaß |
| **Eigenkapitalquote-Trend** | StockholdersEquity über Zeit | StockholdersEquity | Wird die Bilanz solider oder riskanter (z. B. durch Buybacks/Schuldenaufnahme) |
 
---
 
## Kennzahlen, die NOCH NICHT berechenbar sind (fehlender Kurs/Marktdaten)
 
| Kennzahl | Zusätzlich nötig |
|---|---|
| **P/E (trailing)** | Aktueller Kurs |
| **Forward P/E** | Aktueller Kurs + Analystenschätzung (externe Quelle, nicht EDGAR) |
| **Historisches Ø-P/E (5J)** | Historische Kurse (für jedes Jahr) |
| **P/FCF** | Aktueller Kurs, Aktienanzahl (Marktkapitalisierung) |
| **P/B** | Aktueller Kurs, Aktienanzahl |
| **EV/EBITDA** | Marktkapitalisierung (für Enterprise Value), zusätzlich Abschreibungen (`DepreciationDepletionAndAmortization`, noch nicht gesammelt) |
| **EV/Sales** | Marktkapitalisierung |
| **Dividendenrendite** | Aktueller Kurs, Dividende pro Aktie (noch nicht gesammelt) |
| **PEG Ratio** | P/E (also auch Kurs) + Wachstumsrate |
| **Non-GAAP-Gewinnwachstum** | Nicht aus EDGAR extrahierbar (siehe Projekt-Notizen zu Non-GAAP) |
 
---
 
## Nächster Schritt
 
`fetchers/yfinance_fetcher.py` für aktuelle + historische Kurse und Aktienanzahl bauen, um die Lücke zwischen Fundamentaldaten (oben) und den kursbasierten Kennzahlen (unten) zu schließen.
 









