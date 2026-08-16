import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AppShell } from '@/components/layout/AppShell'
import Dashboard from '@/pages/Dashboard'
import TripPlanner from '@/pages/TripPlanner'
import Vehicles from '@/pages/Vehicles'
import Analytics from '@/pages/Analytics'
import { About, Settings } from '@/pages/Static'

export default function App() {
  return <BrowserRouter><AppShell><Routes><Route path="/" element={<Dashboard/>}/><Route path="/trip" element={<TripPlanner/>}/><Route path="/vehicles" element={<Vehicles/>}/><Route path="/analytics" element={<Analytics/>}/><Route path="/settings" element={<Settings/>}/><Route path="/about" element={<About/>}/><Route path="*" element={<Navigate to="/" replace/>}/></Routes></AppShell></BrowserRouter>
}
