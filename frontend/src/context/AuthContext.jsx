import { createContext, useContext, useEffect, useState } from 'react'
import { getMe } from '../api/auth'

// 1. Create the context — this is the shared whiteboard
const AuthContext = createContext(null)

// 2. Provider — wraps the whole app and holds the actual state
export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  // On app load, check if a token already exists and fetch the user
  useEffect(() => {
    const token = localStorage.getItem('token')
    if (token) {
      getMe()
        .then((data) => setUser(data))
        .catch(() => localStorage.removeItem('token'))
        .finally(() => setLoading(false))
    } else {
      setLoading(false)
    }
  }, [])

  const login = (token, userData) => {
    localStorage.setItem('token', token)
    setUser(userData)
  }

  const logout = () => {
    localStorage.removeItem('token')
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

// 3. Custom hook — how any component accesses the context
export const useAuth = () => useContext(AuthContext)
