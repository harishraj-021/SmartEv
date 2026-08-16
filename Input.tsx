import type { InputHTMLAttributes } from 'react'
import { cn } from '@/lib/utils'

export function Input({ className, ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return <input className={cn('h-11 w-full rounded-xl border border-white/8 bg-[#0c0f15] px-3.5 text-sm text-white outline-none transition placeholder:text-white/25 focus:border-red-400/40 focus:ring-2 focus:ring-red-400/10', className)} {...props} />
}
