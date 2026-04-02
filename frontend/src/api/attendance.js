import api from './axios'

export const scanQR = async (qrToken) => {
  const response = await api.post('/attendance/scan', { qr_token: qrToken })
  return response.data
}

export const manualAttendance = async (sessionId, studentId, status) => {
  const response = await api.post('/attendance/manual', {
    session_id: sessionId,
    student_id: studentId,
    status,
  })
  return response.data
}

export const getSessionAttendance = async (sessionId) => {
  const response = await api.get(`/attendance/session/${sessionId}`)
  return response.data
}

export const getStudentAttendance = async (studentId) => {
  const response = await api.get(`/attendance/student/${studentId}`)
  return response.data
}

export const getAttendanceSummary = async (classId) => {
  const response = await api.get(`/attendance/summary/${classId}`)
  return response.data
}
