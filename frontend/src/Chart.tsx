import { useEffect, useState } from 'react'
import Plot from 'react-plotly.js';

type ChartProps = {
  ticker: string
  type: string
}


export default function Chart({ ticker, type }: ChartProps) {
    const [fig, setFig] = useState<any>(null);

     useEffect(() => {
        fetch(`/${ticker}_${type}.json`)
        .then(r => r.json())
        .then(setFig)
    }, [ticker, type])
                    

    return (      
    <>
        {fig && (
        <Plot
          data={fig.data}
          layout={fig.layout}
          style={{ width: '100%', height: fig.layout.height ?? 600 }}
          useResizeHandler
        />
      )}
    </>
    )
}