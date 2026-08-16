import type { SelectHTMLAttributes } from 'react'
import { cn } from '@/lib/utils'

export function Select({ className, children, ...props }: SelectHTMLAttributes<HTMLSelectElement>) {
  return <select className={cn('h-11 w-full appearance-none rounded-xl border border-white/8 bg-[#0c0f15] px-3.5 text-sm text-white outline-none focus:border-red-400/40 focus:ring-2 focus:ring-red-400/10', className)} {...props}>{children}</select>
}
