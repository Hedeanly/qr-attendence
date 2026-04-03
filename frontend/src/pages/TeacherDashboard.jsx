import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { getClasses } from '../api/classes'
import styles from './TeacherDashboard.module.css'

function TeacherDashboard() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [classes, setClasses] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  // Fetch classes when page loads
  useEffect(() => {
    getClasses()
      .then((data) => setClasses(data))
      .catch(() => setError('Failed to load classes'))
      .finally(() => setLoading(false))
  }, [])

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const handleStartSession = (classId) => {
    // Navigate to QR session page for this class
    navigate(`/teacher/session/${classId}`)
  }

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <div className={styles.headerLeft}>
          <img src="/kasem_UNI.jpg" alt="Kasem Bundit University" className={styles.logo} />
          <h1>Teacher Dashboard</h1>
        </div>
        <div className={styles.headerRight}>
          <span>Welcome, {user?.username}</span>
          <button onClick={handleLogout} className={styles.logoutBtn}>Logout</button>
        </div>
      </header>

      <main className={styles.main}>
        <h2>Your Classes</h2>

        {loading && <p>Loading classes...</p>}
        {error && <p className={styles.error}>{error}</p>}

        {!loading && classes.length === 0 && (
          <p className={styles.empty}>No classes assigned yet.</p>
        )}

        <div className={styles.grid}>
          {classes.map((cls) => (
            <div key={cls.id} className={styles.card}>
              <h3>{cls.name}</h3>
              <p>{cls.description || 'No description'}</p>
              <button
                className={styles.startBtn}
                onClick={() => handleStartSession(cls.id)}
              >
                Start Session
              </button>
            </div>
          ))}
        </div>
      </main>
    </div>
  )
}

export default TeacherDashboard
