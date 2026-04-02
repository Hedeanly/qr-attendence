import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { login as loginRequest, getMe } from '../api/auth'
import { useAuth } from '../context/AuthContext'
import styles from './Login.module.css'

function Login() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const { login } = useAuth()
  const navigate = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      // 1. Call backend → get token back
      const data = await loginRequest(username, password)

      // 2. Save token to localStorage so getMe() can use it via the interceptor
      localStorage.setItem('token', data.access_token)

      // 3. Fetch the full user object now that token is saved
      const userData = await getMe()

      // 4. Save token + user into context
      login(data.access_token, userData)

      // 5. Redirect based on role
      if (userData.role === 'admin') navigate('/admin')
      else if (userData.role === 'teacher') navigate('/teacher')
      else navigate('/student')

    } catch (err) {
      setError('Invalid username or password')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className={styles.container}>
      <div className={styles.card}>
        <h1 className={styles.title}>QR Attendance</h1>
        <p className={styles.subtitle}>Sign in to continue</p>

        <form onSubmit={handleSubmit} className={styles.form}>
          <div className={styles.field}>
            <label>Username</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Enter your username"
              required
            />
          </div>

          <div className={styles.field}>
            <label>Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter your password"
              required
            />
          </div>

          {error && <p className={styles.error}>{error}</p>}

          <button type="submit" className={styles.button} disabled={loading}>
            {loading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>
      </div>
    </div>
  )
}

export default Login
