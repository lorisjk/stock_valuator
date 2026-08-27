import { useEffect, useState } from 'react'
import Plot from 'react-plotly.js';

type ChartProps = {
  ticker: string
  type: string
}

/** A pre-rendered figure as figures.py writes it. Replaced per chart type as
 *  each one is rebuilt from the raw series -- valuation already is. */
type PreRenderedFigure = {
  data: unknown[]
  layout: { height?: number } & Record<string, unknown>
}


export default function Chart({ ticker, type }: ChartProps) {
    const [fig, setFig] = useState<PreRenderedFigure | null>(null);

     useEffect(() => {
        fetch(`/${ticker}_${type}.json`)
        .then(r => r.json())
        .then(setFig)
    }, [ticker, type])
                    

    return (      
    <>
        {fig && (
        <Plot
          data={fig.data as never}
          layout={fig.layout as never}
          style={{ width: '100%', height: fig.layout.height ?? 600 }}
          useResizeHandler
        />
      )}
    </>
    )
}