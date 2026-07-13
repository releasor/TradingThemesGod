import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { ThemeDashboard } from '@/features/dashboard/ThemeDashboard'
import { ThemeLibrary } from '@/features/themes/ThemeLibrary'
import { ThemeDetail } from '@/features/themes/ThemeDetail'

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-background">
        <Routes>
          <Route path="/" element={<ThemeDashboard />} />
          <Route path="/themes" element={<ThemeLibrary />} />
          <Route path="/themes/:id" element={<ThemeDetail />} />
        </Routes>
      </div>
    </Router>
  )
}

export default App
