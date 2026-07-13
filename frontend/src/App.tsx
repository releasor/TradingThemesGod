import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { ThemeDashboard } from '@/features/dashboard/ThemeDashboard'
import { ThemeLibrary } from '@/features/themes/ThemeLibrary'

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-background">
        <Routes>
          <Route path="/" element={<ThemeDashboard />} />
          <Route path="/themes" element={<ThemeLibrary />} />
        </Routes>
      </div>
    </Router>
  )
}

export default App
