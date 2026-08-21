import { useState } from 'react'
import Chart from './Chart'

export default function App() {
  const [ticker, setTicker] = useState<string>("AAPL");
  const [type, setType] = useState<string>("valuation");
  return (
    <>
      <select value={ticker} onChange={e => setTicker(e.target.value)}>
        <option value="AAPL">AAPL</option>
        <option value="MSFT">MSFT</option>
      </select>
      <select value={type} onChange={e => setType(e.target.value)}>
        <option value="valuation">Valuation</option>
        <option value="fundamentals">Fundamentals</option>
        <option value="growth">Growth</option>
      </select>
      <p>you choose: {ticker}</p>
      <Chart ticker={ticker} type={type} />
    </>
  )
}
  
