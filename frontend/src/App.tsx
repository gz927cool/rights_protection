import { Routes, Route, Navigate } from 'react-router-dom'
import { Home } from './pages/Home'
import { CaseWizard } from './pages/CaseWizard'
import { AppShell } from './components/layout/AppShell'
import './App.css'

function App() {
  return (
    <div className="app">
      <Routes>
        <Route path="/" element={<Home />} />
        <Route element={<AppShell />}>
          <Route path="/case" element={<CaseWizard />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </div>
  )
}

export default App