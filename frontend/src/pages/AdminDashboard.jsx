import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { getClasses, createClass, getClassStudents, enrollStudent, deleteClass } from '../api/classes'
import { registerUser, getUsers } from '../api/auth'
import styles from './AdminDashboard.module.css'

function AdminDashboard() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  // Tab state — which panel is currently visible
  const [activeTab, setActiveTab] = useState('classes')

  // Classes state
  const [classes, setClasses] = useState([])
  const [newClass, setNewClass] = useState({ name: '', description: '', teacher_id: '' })
  const [allTeachers, setAllTeachers] = useState([])

  // Users state
  const [newUser, setNewUser] = useState({ username: '', email: '', password: '', role: 'student' })

  // Enroll state
  const [selectedClassId, setSelectedClassId] = useState('')
  const [classStudents, setClassStudents] = useState([])
  const [allStudents, setAllStudents] = useState([])
  const [studentIdToEnroll, setStudentIdToEnroll] = useState('')

  // Feedback messages
  const [message, setMessage] = useState({ text: '', success: true })

  const showMessage = (text, success = true) => {
    setMessage({ text, success })
    // Auto-clear message after 3 seconds
    setTimeout(() => setMessage({ text: '', success: true }), 3000)
  }

  // Fetch classes and all students on load
  useEffect(() => {
    getClasses().then(setClasses).catch(() => showMessage('Failed to load classes', false))
    getUsers()
      .then((users) => {
        setAllStudents(users.filter((u) => u.role === 'student'))
        setAllTeachers(users.filter((u) => u.role === 'teacher'))
      })
      .catch(() => showMessage('Failed to load users', false))
  }, [])

  // Fetch students of selected class when admin picks a class in enroll tab
  useEffect(() => {
    if (selectedClassId) {
      getClassStudents(selectedClassId)
        .then(setClassStudents)
        .catch(() => showMessage('Failed to load students', false))
    }
  }, [selectedClassId])

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const handleCreateClass = async (e) => {
    e.preventDefault()
    try {
      const payload = {
        ...newClass,
        teacher_id: parseInt(newClass.teacher_id),
      }
      const created = await createClass(payload)
      setClasses((prev) => [...prev, created])
      setNewClass({ name: '', description: '', teacher_id: '' })
      showMessage('Class created successfully')
    } catch {
      showMessage('Failed to create class', false)
    }
  }

  // Safely extract error message — FastAPI sometimes returns detail as an array
  const extractError = (err, fallback) => {
    const detail = err.response?.data?.detail
    if (!detail) return fallback
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail)) return detail.map((e) => e.msg).join(', ')
    return fallback
  }

  const handleCreateUser = async (e) => {
    e.preventDefault()
    try {
      await registerUser(newUser)
      showMessage(`${newUser.role} account created successfully`)
      setNewUser({ username: '', email: '', password: '', role: 'student' })
      // Refresh student and teacher lists
      const updated = await getUsers()
      setAllStudents(updated.filter((u) => u.role === 'student'))
      setAllTeachers(updated.filter((u) => u.role === 'teacher'))
    } catch (err) {
      showMessage(extractError(err, 'Failed to create user'), false)
    }
  }

  const handleDeleteClass = async (classId, className) => {
    if (!window.confirm(`Delete "${className}" and all its sessions? This cannot be undone.`)) return
    try {
      await deleteClass(classId)
      setClasses((prev) => prev.filter((c) => c.id !== classId))
      showMessage('Class deleted')
    } catch {
      showMessage('Failed to delete class', false)
    }
  }

  const handleEnroll = async (e) => {
    e.preventDefault()
    try {
      await enrollStudent(selectedClassId, parseInt(studentIdToEnroll))
      setStudentIdToEnroll('')
      // Refresh the student list for this class
      const updated = await getClassStudents(selectedClassId)
      setClassStudents(updated)
      showMessage('Student enrolled successfully')
    } catch (err) {
      showMessage(extractError(err, 'Failed to enroll student'), false)
    }
  }

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <h1>Admin Dashboard</h1>
        <div className={styles.headerRight}>
          <span>Welcome, {user?.username}</span>
          <button onClick={handleLogout} className={styles.logoutBtn}>Logout</button>
        </div>
      </header>

      {/* Tab Navigation */}
      <nav className={styles.tabs}>
        <button
          className={activeTab === 'classes' ? styles.activeTab : styles.tab}
          onClick={() => setActiveTab('classes')}
        >
          Classes
        </button>
        <button
          className={activeTab === 'users' ? styles.activeTab : styles.tab}
          onClick={() => setActiveTab('users')}
        >
          Create User
        </button>
        <button
          className={activeTab === 'enroll' ? styles.activeTab : styles.tab}
          onClick={() => setActiveTab('enroll')}
        >
          Enroll Student
        </button>
      </nav>

      <main className={styles.main}>
        {/* Feedback message */}
        {message.text && (
          <p className={message.success ? styles.success : styles.error}>
            {message.text}
          </p>
        )}

        {/* ── CLASSES TAB ── */}
        {activeTab === 'classes' && (
          <div className={styles.panel}>
            <div className={styles.half}>
              <h2>Create Class</h2>
              <form onSubmit={handleCreateClass} className={styles.form}>
                <input
                  type="text"
                  placeholder="Class name"
                  value={newClass.name}
                  onChange={(e) => setNewClass({ ...newClass, name: e.target.value })}
                  required
                />
                <input
                  type="text"
                  placeholder="Description (optional)"
                  value={newClass.description}
                  onChange={(e) => setNewClass({ ...newClass, description: e.target.value })}
                />
                <select
                  value={newClass.teacher_id}
                  onChange={(e) => setNewClass({ ...newClass, teacher_id: e.target.value })}
                  className={styles.select}
                  required
                >
                  <option value="">Assign a teacher</option>
                  {allTeachers.map((t) => (
                    <option key={t.id} value={t.id}>{t.username}</option>
                  ))}
                </select>
                <button type="submit" className={styles.submitBtn}>Create Class</button>
              </form>
            </div>

            <div className={styles.half}>
              <h2>All Classes ({classes.length})</h2>
              {classes.length === 0 ? (
                <p className={styles.empty}>No classes yet.</p>
              ) : (
                <ul className={styles.list}>
                  {classes.map((cls) => (
                    <li key={cls.id} className={styles.listItem}>
                      <div>
                        <span className={styles.listName}>{cls.name}</span>
                        <span className={styles.listSub}>{cls.description || 'No description'}</span>
                      </div>
                      <button
                        className={styles.deleteBtn}
                        onClick={() => handleDeleteClass(cls.id, cls.name)}
                      >
                        Delete
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        )}

        {/* ── USERS TAB ── */}
        {activeTab === 'users' && (
          <div className={styles.panel}>
            <div className={styles.half}>
              <h2>Create New User</h2>
              <form onSubmit={handleCreateUser} className={styles.form}>
                <input
                  type="text"
                  placeholder="Username"
                  value={newUser.username}
                  onChange={(e) => setNewUser({ ...newUser, username: e.target.value })}
                  required
                />
                <input
                  type="email"
                  placeholder="Email"
                  value={newUser.email}
                  onChange={(e) => setNewUser({ ...newUser, email: e.target.value })}
                  required
                />
                <input
                  type="password"
                  placeholder="Password"
                  value={newUser.password}
                  onChange={(e) => setNewUser({ ...newUser, password: e.target.value })}
                  required
                />
                <select
                  value={newUser.role}
                  onChange={(e) => setNewUser({ ...newUser, role: e.target.value })}
                  className={styles.select}
                >
                  <option value="student">Student</option>
                  <option value="teacher">Teacher</option>
                  <option value="admin">Admin</option>
                </select>
                <button type="submit" className={styles.submitBtn}>Create User</button>
              </form>
            </div>
          </div>
        )}

        {/* ── ENROLL TAB ── */}
        {activeTab === 'enroll' && (
          <div className={styles.panel}>
            <div className={styles.half}>
              <h2>Enroll Student into Class</h2>
              <form onSubmit={handleEnroll} className={styles.form}>
                <select
                  value={selectedClassId}
                  onChange={(e) => setSelectedClassId(e.target.value)}
                  className={styles.select}
                  required
                >
                  <option value="">Select a class</option>
                  {classes.map((cls) => (
                    <option key={cls.id} value={cls.id}>{cls.name}</option>
                  ))}
                </select>
                <select
                  value={studentIdToEnroll}
                  onChange={(e) => setStudentIdToEnroll(e.target.value)}
                  className={styles.select}
                  required
                >
                  <option value="">Select a student</option>
                  {allStudents.map((s) => (
                    <option key={s.id} value={s.id}>{s.username} ({s.email})</option>
                  ))}
                </select>
                <button type="submit" className={styles.submitBtn}>Enroll Student</button>
              </form>
            </div>

            {/* Show currently enrolled students for selected class */}
            {selectedClassId && (
              <div className={styles.half}>
                <h2>Enrolled Students ({classStudents.length})</h2>
                {classStudents.length === 0 ? (
                  <p className={styles.empty}>No students enrolled yet.</p>
                ) : (
                  <ul className={styles.list}>
                    {classStudents.map((s) => (
                      <li key={s.id} className={styles.listItem}>
                        <span className={styles.listName}>{s.username}</span>
                        <span className={styles.listSub}>{s.email}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  )
}

export default AdminDashboard
