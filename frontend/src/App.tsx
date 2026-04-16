import { BrowserRouter, Routes, Route } from "react-router-dom"
import HomePage from "./pages/HomePage"
import ChatPage from "./pages/ChatPage"
import CursorEffect from "./components/CursorEffect"

function App() {
  return (
    <>
      <CursorEffect />
      <BrowserRouter>
        <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/chat/:sessionId" element={<ChatPage />} />
        <Route path="/chat" element={<ChatPage />} />
      </Routes>
      </BrowserRouter>
    </>
  )
}

export default App
