import type { ReactNode } from 'react'
import { cn } from '@/lib/utils'

export function Badge({ children, tone = 'neutral', className }: { children: ReactNode; tone?: 'neutral'|'green'|'amber'|'red'|'blue'; className?: string }) {
  const tones = {
    neutral: 'bg-white/6 text-white/65 border-white/8',
    green: 'bg-emerald-400/10 text-emerald-300 border-emerald-400/15',
    amber: 'bg-amber-400/10 text-amber-300 border-amber-400/15',
    red: 'bg-red-400/10 text-red-300 border-red-400/15',
    blue: 'bg-sky-400/10 text-sky-300 border-sky-400/15',
  }
  return <span className={cn('inline-flex items-center rounded-full border px-2.5 py-1 text-[11px] font-medium', tones[tone], className)}>{children}</span>
}
