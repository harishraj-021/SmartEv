import { useEffect, useState } from 'react'
import { ArrowUpRight, BatteryCharging, BrainCircuit, Gauge, Route, Zap } from 'lucide-react'
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { StatCard } from '@/components/ui/StatCard'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { api, type Overview } from '@/lib/api'
import { Link } from 'react-router-dom'

const fallbackChart = [
  { name: 'Jan', value: 4.8 }, { name: 'Feb', value: 5.0 }, { name: 'Mar', value: 5.2 }, { name: 'Apr', value: 5.1 }, { name: 'May', value: 5.4 }, { name: 'Jun', value: 5.3 }, { name: 'Jul', value: 5.5 },
]

export default function Dashboard() {
  const [overview, setOverview] = useState<Overview | null>(null)
  useEffect(() => { api.overview().then(setOverview).catch(() => undefined) }, [])
  const model = overview?.model
  return <div className="space-y-7">
    <div className="flex flex-col justify-between gap-4 md:flex-row md:items-end"><div><Badge tone="red">ML + REAL-TIME DATA</Badge><h1 className="mt-3 text-3xl font-semibold tracking-tight md:text-4xl">EV intelligence, without the guesswork.</h1><p className="mt-2 max-w-2xl text-sm leading-6 text-white/40">Plan a route, estimate energy consumption and see whether the selected EV can complete the trip with a configurable safety reserve.</p></div><Link to="/trip"><Button><Route size={16}/> Plan a trip</Button></Link></div>
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <StatCard label="Vehicles in dataset" value={overview ? overview.dataset_rows.toLocaleString() : '—'} detail={`${overview?.makes ?? '—'} makes · ${overview?.models ?? '—'} models`} icon={<BatteryCharging size={18}/>} />
      <StatCard label="Model R²" value={model ? model.r2.toFixed(3) : '—'} detail="20% held-out test split" icon={<BrainCircuit size={18}/>} accent="green" />
      <StatCard label="Validation MAE" value={model ? `${model.mae.toFixed(3)}` : '—'} detail="km/kWh" icon={<Gauge size={18}/>} accent="blue" />
      <StatCard label="Mean efficiency" value={overview ? overview.efficiency_mean.toFixed(2) : '—'} detail="km/kWh across dataset" icon={<Zap size={18}/>} accent="red" />
    </div>
    <div className="grid gap-5 xl:grid-cols-[1.55fr_1fr]">
      <Card><CardHeader><div className="flex items-center justify-between"><div><CardTitle>Efficiency overview</CardTitle><p className="mt-1 text-xs text-white/30">Reference visualization · live model analytics are available in Model Analytics.</p></div><Badge tone="neutral">Dataset</Badge></div></CardHeader><CardContent><div className="h-[290px] pt-5"><ResponsiveContainer width="100%" height="100%"><AreaChart data={fallbackChart}><defs><linearGradient id="effFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#ef4444" stopOpacity={.26}/><stop offset="100%" stopColor="#ef4444" stopOpacity={0}/></linearGradient></defs><CartesianGrid stroke="#ffffff08" vertical={false}/><XAxis dataKey="name" stroke="#ffffff30" tickLine={false} axisLine={false} fontSize={11}/><YAxis stroke="#ffffff30" tickLine={false} axisLine={false} fontSize={11}/><Tooltip contentStyle={{background:'#11141b',border:'1px solid #ffffff12',borderRadius:12,color:'#fff'}}/><Area type="monotone" dataKey="value" stroke="#ef4444" strokeWidth={2} fill="url(#effFill)"/></AreaChart></ResponsiveContainer></div></CardContent></Card>
      <Card className="overflow-hidden"><CardHeader><CardTitle>How SmartEV decides</CardTitle><p className="mt-1 text-xs text-white/30">Three stages keep the prediction explainable.</p></CardHeader><CardContent><div className="space-y-3 pt-3">{[['01','Vehicle ML','Vehicle specifications → base efficiency'],['02','Trip factors','Terrain × weather × driving conditions'],['03','Feasibility','Energy available vs energy required']].map(([n,t,d]) => <div key={n} className="flex gap-3 rounded-xl border border-white/7 bg-white/[.02] p-4"><span className="text-xs font-semibold text-red-300">{n}</span><div><p className="text-sm font-semibold">{t}</p><p className="mt-1 text-xs leading-5 text-white/35">{d}</p></div></div>)}</div><Link to="/analytics" className="mt-4 flex items-center justify-between rounded-xl border border-white/7 px-4 py-3 text-xs text-white/45 hover:bg-white/5 hover:text-white">View model analytics <ArrowUpRight size={15}/></Link></CardContent></Card>
    </div>
    <Card className="glow-red"><CardContent><div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between"><div><p className="text-sm font-semibold">Ready to test a real route?</p><p className="mt-1 text-xs text-white/35">Enter your vehicle, battery state and locations. The backend will query routing and weather services.</p></div><Link to="/trip"><Button variant="outline">Open Trip Planner <ArrowUpRight size={15}/></Button></Link></div></CardContent></Card>
  </div>
}
