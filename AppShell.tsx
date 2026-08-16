import { useState, type ReactNode } from 'react'
import { NavLink } from 'react-router-dom'
import { Activity, BarChart3, CarFront, ChevronLeft, ChevronRight, CircleHelp, LayoutDashboard, MapPinned, Settings, Zap } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/Badge'

const links = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/trip', label: 'Trip Planner', icon: MapPinned },
  { to: '/vehicles', label: 'Vehicles', icon: CarFront },
  { to: '/analytics', label: 'Model Analytics', icon: BarChart3 },
]

export function AppShell({ children }: { children: ReactNode }) {
  const [collapsed, setCollapsed] = useState(false)
  return <div className="min-h-screen bg-[#090b10] text-white">
    <aside className={cn('fixed inset-y-0 left-0 z-30 hidden border-r border-white/7 bg-[#0c0f15] transition-all lg:flex lg:flex-col', collapsed ? 'w-[76px]' : 'w-[248px]')}>
      <div className="flex h-20 items-center gap-3 border-b border-white/7 px-5">
        <div className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-red-500 shadow-lg shadow-red-500/20"><Zap size={18} fill="currentColor" /></div>
        {!collapsed && <div><div className="text-sm font-bold tracking-tight">SmartEV</div><div className="text-[10px] text-white/35">EV INTELLIGENCE</div></div>}
      </div>
      <nav className="flex-1 space-y-1 p-3">
        {!collapsed && <p className="px-3 pb-2 pt-3 text-[10px] font-semibold uppercase tracking-[.18em] text-white/25">Workspace</p>}
        {links.map(({ to, label, icon: Icon }) => <NavLink key={to} to={to} end={to === '/'} className={({ isActive }) => cn('group flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition', isActive ? 'bg-white/7 text-white' : 'text-white/45 hover:bg-white/5 hover:text-white', collapsed && 'justify-center px-0')}>
          <Icon size={18} className={cn('shrink-0', 'group-[.active]:text-red-300')} />
          {!collapsed && <span>{label}</span>}
        </NavLink>)}
        {!collapsed && <p className="px-3 pb-2 pt-7 text-[10px] font-semibold uppercase tracking-[.18em] text-white/25">System</p>}
        <NavLink to="/settings" className={cn('flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm text-white/45 hover:bg-white/5 hover:text-white', collapsed && 'justify-center px-0')}><Settings size={18}/>{!collapsed && 'Settings'}</NavLink>
        <NavLink to="/about" className={cn('flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm text-white/45 hover:bg-white/5 hover:text-white', collapsed && 'justify-center px-0')}><CircleHelp size={18}/>{!collapsed && 'About'}</NavLink>
      </nav>
      <div className="border-t border-white/7 p-3">
        {!collapsed && <div className="rounded-xl border border-white/7 bg-white/[.025] p-3"><div className="flex items-center gap-2"><span className="h-2 w-2 rounded-full bg-emerald-400"/><span className="text-xs font-medium">Backend ready</span></div><p className="mt-1 text-[10px] text-white/30">FastAPI · ML · Routing</p></div>}
        <button onClick={() => setCollapsed(v => !v)} className="mt-2 flex w-full items-center justify-center rounded-xl py-2 text-white/35 hover:bg-white/5 hover:text-white">{collapsed ? <ChevronRight size={17}/> : <ChevronLeft size={17}/>}</button>
      </div>
    </aside>
    <div className={cn('transition-all lg:pl-[248px]', collapsed && 'lg:pl-[76px]')}>
      <header className="sticky top-0 z-20 flex h-20 items-center justify-between border-b border-white/7 bg-[#090b10]/85 px-5 backdrop-blur-xl lg:px-8">
        <div><p className="text-xs text-white/35">SmartEV / Intelligent Mobility</p><p className="text-sm font-semibold">Energy & range planner</p></div>
        <div className="flex items-center gap-2"><Badge tone="green"><Activity size={11}/> API online</Badge><div className="hidden rounded-xl border border-white/7 bg-white/[.025] px-3 py-2 text-xs text-white/45 sm:block">Dataset edition</div></div>
      </header>
      <main className="mx-auto max-w-[1500px] p-5 lg:p-8">{children}</main>
    </div>
  </div>
}
