import React from 'react'
import { Outlet } from 'react-router-dom'
import { AIChatPanel } from '../ai/AIChatPanel'

export function AppShell() {
  return (
    <div style={{ display: 'flex', height: '100vh', overflow: 'hidden' }}>
      <div style={{ flex: 1, overflowY: 'auto' }}>
        <Outlet />
      </div>
      <AIChatPanel />
    </div>
  )
}