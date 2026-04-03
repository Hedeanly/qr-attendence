import { useEffect, useState, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { QRCodeSVG as QRCode } from 'qrcode.react'
import { startSession, endSession, refreshQR } from '../api/sessions'
import { getSessionAttendance } from '../api/attendance'
import styles from './QRSession.module.css'

function QRSession() {
  const { classId } = useParams()
  const navigate = useNavigate()

  const [session, setSession] = useState(null)
  const [attendance, setAttendance] = useState([])
  const [timeLeft, setTimeLeft] = useState(60)
  const [loading, setLoading] = useState(true)
  const [ending, setEnding] = useState(false)
  const [error, setError] = useState('')

  // useRef stores the interval IDs so we can clear them on cleanup
  const qrIntervalRef = useRef(null)
  const attendanceIntervalRef = useRef(null)
  const countdownRef = useRef(null)

  // Start the session when the page loads
  useEffect(() => {
    startSession(classId)
      .then((data) => {
        setSession(data)
        setLoading(false)
        startIntervals(data.id)
      })
      .catch(() => {
        setError('Failed to start session')
        setLoading(false)
      })

    // Cleanup: clear all intervals when user leaves this page
    return () => {
      clearInterval(qrIntervalRef.current)
      clearInterval(attendanceIntervalRef.current)
      clearInterval(countdownRef.current)
    }
  }, [classId])

  const startIntervals = (sessionId) => {
    // Refresh QR token every 60 seconds
    qrIntervalRef.current = setInterval(async () => {
      try {
        const updated = await refreshQR(sessionId)
        setSession(updated)
        setTimeLeft(60)
      } catch {
        setError('Failed to refresh QR')
      }
    }, 60000)

    // Fetch live attendance every 5 seconds
    attendanceIntervalRef.current = setInterval(async () => {
      try {
        const data = await getSessionAttendance(sessionId)
        setAttendance(data)
      } catch {
        // Silently fail — attendance polling is non-critical
      }
    }, 5000)

    // Countdown timer — ticks every second
    countdownRef.current = setInterval(() => {
      setTimeLeft((prev) => (prev <= 1 ? 60 : prev - 1))
    }, 1000)
  }

  const handleEndSession = async () => {
    setEnding(true)
    try {
      await endSession(session.id)
      clearInterval(qrIntervalRef.current)
      clearInterval(attendanceIntervalRef.current)
      clearInterval(countdownRef.current)
      navigate('/teacher')
    } catch {
      setError('Failed to end session')
      setEnding(false)
    }
  }

  if (loading) return <div className={styles.center}>Starting session...</div>
  if (error) return <div className={styles.center}>{error}</div>

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <div className={styles.headerLeft}>
          <img src="/kasem_UNI.jpg" alt="Kasem Bundit University" className={styles.logo} />
          <h1>Live Session</h1>
        </div>
        <button
          onClick={handleEndSession}
          className={styles.endBtn}
          disabled={ending}
        >
          {ending ? 'Ending...' : 'End Session'}
        </button>
      </header>

      <div className={styles.content}>
        {/* Left: QR Code display */}
        <div className={styles.qrPanel}>
          <h2>Scan to Attend</h2>
          <div className={styles.qrBox}>
            <QRCode value={session.qr_token} size={220} />
          </div>
          <p className={styles.countdown}>
            Refreshes in <strong>{timeLeft}s</strong>
          </p>
        </div>

        {/* Right: Live attendance list */}
        <div className={styles.attendancePanel}>
          <h2>Live Attendance ({attendance.length})</h2>
          {attendance.length === 0 ? (
            <p className={styles.empty}>Waiting for students to scan...</p>
          ) : (
            <ul className={styles.list}>
              {attendance.map((record) => (
                <li key={record.id} className={styles.listItem}>
                  <span>{record.student_username}</span>
                  <span className={`${styles.badge} ${styles[record.status]}`}>
                    {record.status}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  )
}

export default QRSession
