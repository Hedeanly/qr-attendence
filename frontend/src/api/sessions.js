import api from './axios'

export const startSession = async (classId, lateThresholdMinutes = 10) => {
  const response = await api.post('/sessions/start', {
    class_id: classId,
    late_threshold_minutes: lateThresholdMinutes,
  })
  return response.data
}

export const endSession = async (sessionId) => {
  const response = await api.post(`/sessions/${sessionId}/end`)
  return response.data
}

export const refreshQR = async (sessionId) => {
  const response = await api.post(`/sessions/${sessionId}/refresh-qr`)
  return response.data
}

export const getSession = async (sessionId) => {
  const response = await api.get(`/sessions/${sessionId}`)
  return response.data
}

export const getClassSessions = async (classId) => {
  const response = await api.get(`/sessions/class/${classId}`)
  return response.data
}
