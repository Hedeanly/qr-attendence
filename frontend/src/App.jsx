import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './context/AuthContext'
import Login from './pages/Login'
import TeacherDashboard from './pages/TeacherDashboard'
import QRSession from './pages/QRSession'
import StudentDashboard from './pages/StudentDashboard'
import AdminDashboard from './pages/AdminDashboard'

// Blocks access to a page if user is not logged in
function ProtectedRoute({ children, allowedRoles }) {
  const { user, loading } = useAuth()

  if (loading) return <div>Loading...</div>
  if (!user) return <Navigate to="/login" />
  if (allowedRoles && !allowedRoles.includes(user.role)) return <Navigate to="/login" />

  return children
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />

        <Route path="/teacher" element={
          <ProtectedRoute allowedRoles={['teacher', 'admin']}>
            <TeacherDashboard />
          </ProtectedRoute>
        } />

        <Route path="/teacher/session/:classId" element={
          <ProtectedRoute allowedRoles={['teacher', 'admin']}>
            <QRSession />
          </ProtectedRoute>
        } />

        <Route path="/student" element={
          <ProtectedRoute allowedRoles={['student']}>
            <StudentDashboard />
          </ProtectedRoute>
        } />

        <Route path="/admin" element={
          <ProtectedRoute allowedRoles={['admin']}>
            <AdminDashboard />
          </ProtectedRoute>
        } />

        <Route path="*" element={<Navigate to="/login" />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
