import { Routes, Route, Navigate } from 'react-router-dom'
import { Home } from './pages/Home'
import { CaseWizard } from './pages/CaseWizard'
import './App.css'

function App() {
  return (
    <div className="app">
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/case" element={<CaseWizard />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </div>
  )
}

export default App
