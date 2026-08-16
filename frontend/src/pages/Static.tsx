import type { ReactNode } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'

export function Settings() { return <Page title="Settings" badge="SYSTEM"><Card><CardHeader><CardTitle>SmartEV configuration</CardTitle></CardHeader><CardContent><p className="text-sm leading-6 text-white/40">Backend URL is controlled by <code className="text-white/70">VITE_API_URL</code>. The OpenRouteService key stays on the Python backend and is never bundled into the browser.</p></CardContent></Card></Page> }
export function About() { return <Page title="About SmartEV" badge="PROJECT"><Card><CardHeader><CardTitle>Machine-learning-assisted EV trip planning</CardTitle></CardHeader><CardContent><p className="text-sm leading-6 text-white/40">SmartEV combines a dataset-trained vehicle efficiency model with route elevation, live weather and transparent trip-condition factors. The supplied dataset is the source of vehicle records; battery capacity is entered separately because it is not a dataset column.</p></CardContent></Card></Page> }
function Page({title,badge,children}:{title:string;badge:string;children:ReactNode}) { return <div className="space-y-6"><div><Badge>{badge}</Badge><h1 className="mt-3 text-3xl font-semibold">{title}</h1></div>{children}</div> }
