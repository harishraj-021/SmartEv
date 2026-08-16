import type { ReactNode } from 'react'
import { Card } from './Card'

export function StatCard({ label, value, detail, icon, accent = 'neutral' }: { label: string; value: string; detail?: string; icon?: ReactNode; accent?: 'neutral'|'red'|'green'|'blue' }) {
  const colors = { neutral: 'text-white', red: 'text-red-300', green: 'text-emerald-300', blue: 'text-sky-300' }
  return <Card className="p-5">
    <div className="flex items-start justify-between gap-3">
      <div>
        <p className="text-xs font-medium text-white/40">{label}</p>
        <p className={`mt-2 text-2xl font-semibold tracking-tight ${colors[accent]}`}>{value}</p>
        {detail && <p className="mt-1 text-xs text-white/35">{detail}</p>}
      </div>
      {icon && <div className="rounded-xl border border-white/7 bg-white/[.035] p-2.5 text-white/55">{icon}</div>}
    </div>
  </Card>
}
