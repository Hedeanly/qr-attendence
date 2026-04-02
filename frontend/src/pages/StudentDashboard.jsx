import { useEffect, useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { Html5QrcodeScanner } from 'html5-qrcode'
import { useAuth } from '../context/AuthContext'
import { getStudentAttendance } from '../api/attendance'
import { scanQR } from '../api/attendance'
import styles from './StudentDashboard.module.css'

function StudentDashboard() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const [attendance, setAttendance] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [scanning, setScanning] = useState(false)
  const [scanResult, setScanResult] = useState(null)

  // Ref to hold the scanner instance so we can stop it later
  const scannerRef = useRef(null)

  // Fetch student's attendance history on page load
  useEffect(() => {
    getStudentAttendance(user.id)
      .then((data) => setAttendance(data))
      .catch(() => setError('Failed to load attendance'))
      .finally(() => setLoading(false))
  }, [user.id])

  // Start the QR scanner
  const startScanner = () => {
    setScanning(true)
    setScanResult(null)

    // Small delay to let the scanner div render in the DOM first
    setTimeout(() => {
      const scanner = new Html5QrcodeScanner('qr-reader', {
        fps: 10,         // scan attempts per second
        qrbox: 250,      // size of the scanning box in pixels
      })

      scanner.render(
        async (decodedText) => {
          // Success — student scanned a QR code
          scanner.clear()
          setScanning(false)

          try {
            const result = await scanQR(decodedText)
            setScanResult({ success: true, message: `Marked as ${result.status}` })

            // Refresh attendance list after successful scan
            const updated = await getStudentAttendance(user.id)
            setAttendance(updated)
          } catch (err) {
            const msg = err.response?.data?.detail || 'Scan failed'
            setScanResult({ success: false, message: msg })
          }
        },
        () => {
          // Error callback — ignore minor scan failures, scanner keeps trying
        }
      )

      scannerRef.current = scanner
    }, 100)
  }

  const stopScanner = () => {
    if (scannerRef.current) {
      scannerRef.current.clear()
      scannerRef.current = null
    }
    setScanning(false)
  }

  // Cleanup scanner if student navigates away mid-scan
  useEffect(() => {
    return () => {
      if (scannerRef.current) {
        scannerRef.current.clear()
      }
    }
  }, [])

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  // Group attendance records by class and calculate percentage
  const classStats = attendance.reduce((acc, record) => {
    const className = record.class_name
    if (!acc[className]) {
      acc[className] = { total: 0, present: 0, late: 0 }
    }
    acc[className].total += 1
    if (record.status === 'present') acc[className].present += 1
    if (record.status === 'late') acc[className].late += 1
    return acc
  }, {})

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <h1>Student Dashboard</h1>
        <div className={styles.headerRight}>
          <span>Welcome, {user?.username}</span>
          <button onClick={handleLogout} className={styles.logoutBtn}>Logout</button>
        </div>
      </header>

      <main className={styles.main}>

        {/* QR Scanner Section */}
        <section className={styles.scanSection}>
          <h2>Scan QR Code</h2>
          <p>Scan the QR code displayed by your teacher to mark attendance</p>

          {!scanning ? (
            <button onClick={startScanner} className={styles.scanBtn}>
              Open Camera & Scan
            </button>
          ) : (
            <button onClick={stopScanner} className={styles.cancelBtn}>
              Cancel
            </button>
          )}

          {/* Scanner renders into this div */}
          {scanning && <div id="qr-reader" className={styles.scanner}></div>}

          {/* Result message after scan */}
          {scanResult && (
            <p className={scanResult.success ? styles.success : styles.error}>
              {scanResult.message}
            </p>
          )}
        </section>

        {/* Attendance Summary Section */}
        <section className={styles.statsSection}>
          <h2>Your Attendance</h2>

          {loading && <p>Loading...</p>}
          {error && <p className={styles.error}>{error}</p>}

          {!loading && Object.keys(classStats).length === 0 && (
            <p className={styles.empty}>No attendance records yet.</p>
          )}

          <div className={styles.grid}>
            {Object.entries(classStats).map(([className, stats]) => {
              const percentage = Math.round(
                ((stats.present + stats.late) / stats.total) * 100
              )
              const atRisk = percentage < 75

              return (
                <div
                  key={className}
                  className={`${styles.card} ${atRisk ? styles.atRisk : ''}`}
                >
                  <h3>{className}</h3>
                  <p className={styles.percentage}>{percentage}%</p>
                  <p className={styles.breakdown}>
                    {stats.present} present · {stats.late} late · {stats.total - stats.present - stats.late} absent
                  </p>
                  {atRisk && (
                    <p className={styles.warning}>
                      ⚠ Below 75% attendance threshold
                    </p>
                  )}
                </div>
              )
            })}
          </div>
        </section>

      </main>
    </div>
  )
}

export default StudentDashboard
