import { useEffect, useMemo, useState } from 'react'
import { AlertTriangle, Battery, CarFront, CheckCircle2, CloudSun, Loader2, MapPin, Navigation, Route, Wind, Zap } from 'lucide-react'
import { MapContainer, Marker, Polyline, Popup, TileLayer, useMap } from 'react-leaflet'
import L from 'leaflet'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Select } from '@/components/ui/Select'
import { api, type Vehicle } from '@/lib/api'

function FitRoute({ points }: { points: [number, number][] }) { const map = useMap(); useEffect(() => { if (points.length) map.fitBounds(L.latLngBounds(points), { padding: [30, 30] }) }, [map, points]); return null }

const icon = (color: string, symbol: string) => L.divIcon({ className: '', html: `<div style="width:30px;height:30px;border-radius:10px;background:${color};display:grid;place-items:center;color:white;font-weight:800;border:2px solid #fff;box-shadow:0 8px 20px rgba(0,0,0,.35)">${symbol}</div>`, iconSize:[30,30], iconAnchor:[15,15] })

export default function TripPlanner() {
  const [records, setRecords] = useState<Vehicle[]>([])
  const [make, setMake] = useState('')
  const [model, setModel] = useState('')
  const [record, setRecord] = useState<Vehicle | null>(null)
  const [start, setStart] = useState('Chennai')
  const [destination, setDestination] = useState('Hyderabad')
  const [battery, setBattery] = useState(40)
  const [charge, setCharge] = useState(80)
  const [reserve, setReserve] = useState(10)
  const [style, setStyle] = useState<'Gentle'|'Normal'|'Aggressive'>('Normal')
  const [result, setResult] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => { api.vehicleOptions().then(x => { setRecords(x.records); if (x.records[0]) { setMake(x.records[0].Make); setModel(x.records[0].Model); setRecord(x.records[0]) } }).catch(e => setError(e.message)) }, [])
  const makes = useMemo(() => [...new Set(records.map(x => x.Make))].sort(), [records])
  const models = useMemo(() => [...new Set(records.filter(x => x.Make === make).map(x => x.Model))].sort(), [records, make])
  const modelRecords = useMemo(() => records.filter(x => x.Make === make && x.Model === model), [records, make, model])
  useEffect(() => { const r = modelRecords[0]; if (r) { setRecord(r); setModel(r.Model) } }, [modelRecords])
  useEffect(() => { const r = records.find(x => x.Make === make); if (r && !models.includes(model)) setModel(r.Model) }, [make, model, models, records])

  async function analyze() {
    if (!record) return
    setLoading(true); setError(''); setResult(null)
    try { setResult(await api.analyzeTrip({ make: record.Make, model: record.Model, model_year: record['Model year'], motor_kw: record['Motor (kW)'], recharge_time_h: record['Recharge time (h)'], vehicle_class: record['Vehicle class'], battery_kwh: battery, charge_percent: charge, reserve_percent: reserve, start, destination, driving_style: style })) }
    catch (e: any) { setError(e.message || 'Trip analysis failed') }
    finally { setLoading(false) }
  }

  const p = result?.prediction
  const points = (result?.route?.points || []) as [number, number][]
  const center = points[0] || [13.0827, 80.2707] as [number, number]
  const statusTone = p?.status === 'REACHABLE' ? 'green' : p?.status === 'MARGINAL' ? 'amber' : 'red'
  const statusText = p?.status === 'REACHABLE' ? 'Reachable' : p?.status === 'MARGINAL' ? 'Marginal' : 'Charge required'

  return <div className="space-y-6">
    <div><Badge tone="red">TRIP PLANNER</Badge><h1 className="mt-3 text-3xl font-semibold tracking-tight">Plan your EV journey.</h1><p className="mt-2 text-sm text-white/40">Live route + weather, dataset-trained ML and an explainable energy model.</p></div>
    <div className="grid gap-5 xl:grid-cols-[430px_1fr]">
      <div className="space-y-5">
        <Card><CardHeader><CardTitle><span className="inline-flex items-center gap-2"><Navigation size={16} className="text-red-300"/> Route</span></CardTitle></CardHeader><CardContent><div className="space-y-4 pt-2"><label className="block"><span className="mb-2 block text-xs text-white/40">Start</span><Input value={start} onChange={e => setStart(e.target.value)} placeholder="Chennai" /></label><label className="block"><span className="mb-2 block text-xs text-white/40">Destination</span><Input value={destination} onChange={e => setDestination(e.target.value)} placeholder="Hyderabad" /></label></div></CardContent></Card>
        <Card><CardHeader><CardTitle><span className="inline-flex items-center gap-2"><CarFront size={16} className="text-red-300"/> Vehicle</span></CardTitle></CardHeader><CardContent><div className="space-y-4 pt-2"><label className="block"><span className="mb-2 block text-xs text-white/40">Make</span><Select value={make} onChange={e => setMake(e.target.value)}>{makes.map(x => <option key={x}>{x}</option>)}</Select></label><label className="block"><span className="mb-2 block text-xs text-white/40">Model</span><Select value={model} onChange={e => setModel(e.target.value)}>{models.map(x => <option key={x}>{x}</option>)}</Select></label>{record && <div className="rounded-xl border border-white/7 bg-white/[.02] p-3 text-xs text-white/45">{record['Model year']} · {record['Vehicle class']} · {record['Motor (kW)']} kW · {record['Recharge time (h)']} h recharge</div>}</div></CardContent></Card>
        <Card><CardHeader><CardTitle><span className="inline-flex items-center gap-2"><Battery size={16} className="text-red-300"/> Battery & driving</span></CardTitle></CardHeader><CardContent><div className="space-y-4 pt-2"><label className="block"><span className="mb-2 block text-xs text-white/40">Battery capacity (kWh)</span><Input type="number" min="1" max="300" value={battery} onChange={e => setBattery(Number(e.target.value))}/><span className="mt-1 block text-[10px] text-white/25">Not present in the supplied dataset, so entered separately.</span></label><label className="block"><div className="mb-2 flex justify-between text-xs text-white/40"><span>Current charge</span><b className="text-white">{charge}%</b></div><input type="range" min="0" max="100" value={charge} onChange={e => setCharge(Number(e.target.value))} className="w-full accent-red-500"/></label><label className="block"><div className="mb-2 flex justify-between text-xs text-white/40"><span>Safety reserve</span><b className="text-white">{reserve}%</b></div><input type="range" min="5" max="30" value={reserve} onChange={e => setReserve(Number(e.target.value))} className="w-full accent-red-500"/></label><label className="block"><span className="mb-2 block text-xs text-white/40">Driving style</span><Select value={style} onChange={e => setStyle(e.target.value as any)}><option>Gentle</option><option>Normal</option><option>Aggressive</option></Select></label><Button className="mt-2 w-full" onClick={analyze} disabled={loading || !record}>{loading ? <><Loader2 size={16} className="animate-spin"/> Analyzing…</> : <><Zap size={16}/> Analyze trip</>}</Button>{error && <div className="rounded-xl border border-red-400/15 bg-red-400/8 p-3 text-xs leading-5 text-red-200">{error}</div>}</div></CardContent></Card>
      </div>
      <div className="space-y-5">
        <Card className="overflow-hidden"><div className="h-[420px] w-full"><MapContainer center={center} zoom={6} scrollWheelZoom className="h-full w-full"><TileLayer attribution='&copy; OpenStreetMap contributors' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />{points.length > 1 && <><FitRoute points={points}/><Polyline positions={points} pathOptions={{color:'#ef4444',weight:5,opacity:.85}}/></>}{result?.locations?.start && <Marker position={[result.locations.start.lat, result.locations.start.lon]} icon={icon('#16a34a','S')}><Popup>{result.locations.start.label}</Popup></Marker>}{result?.locations?.destination && <Marker position={[result.locations.destination.lat, result.locations.destination.lon]} icon={icon('#dc2626','D')}><Popup>{result.locations.destination.label}</Popup></Marker>}</MapContainer></div></Card>
        {!result ? <Card><CardContent><div className="flex min-h-[210px] flex-col items-center justify-center text-center"><div className="grid h-14 w-14 place-items-center rounded-2xl border border-white/8 bg-white/[.03]"><Route className="text-white/30"/></div><p className="mt-4 text-sm font-semibold">Your trip result will appear here</p><p className="mt-1 max-w-sm text-xs leading-5 text-white/30">Run an analysis to fetch the route, terrain and weather and calculate the estimated energy requirement.</p></div></CardContent></Card> : <div className="space-y-5">
          <Card className="overflow-hidden"><div className={`border-b px-5 py-5 ${statusTone === 'green' ? 'border-emerald-400/15 bg-emerald-400/5' : statusTone === 'amber' ? 'border-amber-400/15 bg-amber-400/5' : 'border-red-400/15 bg-red-400/5'}`}><div className="flex items-center justify-between gap-3"><div><p className="text-xs text-white/40">Trip decision</p><p className="mt-1 text-2xl font-semibold">{statusText}</p></div><Badge tone={statusTone}>{p.status === 'REACHABLE' ? <CheckCircle2 size={12}/> : <AlertTriangle size={12}/>} {p.status.replace('_',' ')}</Badge></div></div><CardContent><div className="grid gap-3 pt-5 sm:grid-cols-2 lg:grid-cols-4"><Metric label="Distance" value={`${result.route.distance_km.toFixed(1)} km`}/><Metric label="Safe range" value={`${p.safe_range_km.toFixed(0)} km`}/><Metric label="Energy needed" value={`${p.energy_required_kwh.toFixed(1)} kWh`}/><Metric label="Arrival SOC" value={`${p.arrival_soc_percent.toFixed(0)}%`}/></div></CardContent></Card>
          <div className="grid gap-5 lg:grid-cols-2"><Card><CardHeader><CardTitle>Efficiency breakdown</CardTitle></CardHeader><CardContent><div className="space-y-3 pt-2"><Factor label="Base ML efficiency" value={`${p.base_efficiency_km_kwh.toFixed(2)} km/kWh`} factor="1.00"/><Factor label="Terrain" value={`${p.factors.terrain.toFixed(3)}×`} factor={`${((p.factors.terrain-1)*100).toFixed(1)}%`}/><Factor label="Weather" value={`${p.factors.weather.toFixed(3)}×`} factor={`${((p.factors.weather-1)*100).toFixed(1)}%`}/><Factor label="Driving" value={`${p.factors.driving.toFixed(3)}×`} factor={`${((p.factors.driving-1)*100).toFixed(1)}%`}/></div></CardContent></Card><Card><CardHeader><CardTitle>Live conditions</CardTitle></CardHeader><CardContent><div className="grid grid-cols-2 gap-3 pt-2"><Condition icon={<CloudSun size={16}/>} label="Temperature" value={`${result.weather.temperature_c.toFixed(1)}°C`}/><Condition icon={<Wind size={16}/>} label="Wind" value={`${result.weather.wind_kmh.toFixed(1)} km/h`}/><Condition icon={<MapPin size={16}/>} label="Climb" value={`${result.route.ascent_m.toFixed(0)} m`}/><Condition icon={<Route size={16}/>} label="Duration" value={`${result.route.duration_min?.toFixed(0) ?? '—'} min`}/></div></CardContent></Card></div>
        </div>}
      </div>
    </div>
  </div>
}
function Metric({label,value}:{label:string;value:string}) { return <div className="rounded-xl border border-white/7 bg-white/[.02] p-3"><p className="text-[10px] text-white/30">{label}</p><p className="mt-1 text-sm font-semibold">{value}</p></div> }
function Factor({label,value,factor}:{label:string;value:string;factor:string}) { return <div className="flex items-center justify-between rounded-xl border border-white/7 bg-white/[.02] p-3"><div><p className="text-xs font-medium">{label}</p><p className="mt-1 text-[10px] text-white/30">Impact {factor}</p></div><span className="text-sm font-semibold text-white/80">{value}</span></div> }
function Condition({icon,label,value}:{icon:any;label:string;value:string}) { return <div className="rounded-xl border border-white/7 bg-white/[.02] p-3"><div className="flex items-center gap-2 text-white/35">{icon}<span className="text-[10px]">{label}</span></div><p className="mt-2 text-sm font-semibold">{value}</p></div> }
