import { Routes, Route, Navigate } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import Project from './pages/Project'

function App() {
  return (
    <div className="min-h-screen bg-background">
      <header className="border-b bg-card">
        <div className="container mx-auto px-4 py-4">
          <h1 className="text-2xl font-bold bg-gradient-to-r from-primary to-purple-500 bg-clip-text text-transparent">
            VJ-Gen System
          </h1>
          <p className="text-sm text-muted-foreground">
            Audio + Lyrics to VJ Video
          </p>
        </div>
      </header>
      
      <main className="container mx-auto px-4 py-8">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/project/:id" element={<Project />} />
        </Routes>
      </main>
    </div>
  )
}

export default App
