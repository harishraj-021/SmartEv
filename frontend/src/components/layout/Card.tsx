import type { ReactNode } from 'react'
import { cn } from '@/lib/utils'

export function Card({ className, children }: { className?: string; children: ReactNode }) {
  return <section className={cn('rounded-2xl border border-white/7 bg-[#11141b] shadow-[0_10px_40px_rgba(0,0,0,.16)]', className)}>{children}</section>
}

export function CardHeader({ className, children }: { className?: string; children: ReactNode }) {
  return <div className={cn('px-5 pt-5', className)}>{children}</div>
}
export function CardContent({ className, children }: { className?: string; children: ReactNode }) {
  return <div className={cn('px-5 pb-5', className)}>{children}</div>
}
export function CardTitle({ children }: { children: ReactNode }) {
  return <h3 className="text-sm font-semibold tracking-tight text-white">{children}</h3>
}
