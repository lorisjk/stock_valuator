/**
 * The screen that replaces the app when the export cannot be read — item 24.
 *
 * `app.py` names the missing files and stops (app.py:819-833). The frontend
 * cannot enumerate a directory, so it names *what it asked for* and what the
 * answer was, and `diagnose` turns that into the one remedy that applies.
 *
 * A failure that is a normal state of a partial dev bundle is presented as
 * such — the same reasoning `MissingTickerFile` carries — because "copy one
 * more file into public/" and "your export is broken" are different days.
 */
import { diagnose } from "./guard.ts";

export default function GuardScreen({ error, what }: { error: Error; what: string }) {
  const d = diagnose(error, what);
  return (
    <main className="guard" role="alert">
      <h1>Kyhestlo</h1>
      <h2>{d.headline}</h2>
      {d.expectedInDev && (
        <p className="guard__note">
          This is a normal state of a partial development bundle, not a fault in the data.
        </p>
      )}
      <p>{d.remedy}</p>
      <pre className="guard__detail">{error.message}</pre>
    </main>
  );
}
