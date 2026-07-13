import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { ThemeDashboard } from '@/features/dashboard/ThemeDashboard'

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-background">
        <Routes>
          <Route path="/" element={<ThemeDashboard />} />
        </Routes>
      </div>
    </Router>
  )
}

export default App
