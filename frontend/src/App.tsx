import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-background">
        <Routes>
          <Route path="/" element={<Home />} />
        </Routes>
      </div>
    </Router>
  )
}

function Home() {
  return (
    <div className="flex flex-col items-center justify-center min-h-screen">
      <h1 className="text-4xl font-bold text-foreground">
        TradingThemesGod
      </h1>
      <p className="mt-4 text-lg text-muted-foreground">
        股票题材与产业链分析平台
      </p>
    </div>
  )
}

export default App
