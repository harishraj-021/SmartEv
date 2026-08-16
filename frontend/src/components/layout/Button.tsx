import type { ButtonHTMLAttributes } from 'react'
import { cn } from '@/lib/utils'

export function Button({ className, variant = 'default', ...props }: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: 'default'|'ghost'|'outline' }) {
  const styles = {
    default: 'bg-red-500 text-white hover:bg-red-400 shadow-lg shadow-red-500/10',
    ghost: 'bg-transparent text-white/65 hover:bg-white/6 hover:text-white',
    outline: 'border border-white/10 bg-white/[.02] text-white hover:bg-white/6',
  }
  return <button className={cn('inline-flex items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold transition disabled:cursor-not-allowed disabled:opacity-50', styles[variant], className)} {...props} />
}
