import api from './axios'

export const getClasses = async () => {
  const response = await api.get('/classes')
  return response.data
}

export const getClass = async (classId) => {
  const response = await api.get(`/classes/${classId}`)
  return response.data
}

export const createClass = async (classData) => {
  const response = await api.post('/classes', classData)
  return response.data
}

export const enrollStudent = async (classId, studentId) => {
  const response = await api.post(`/classes/${classId}/enroll`, { student_id: studentId, class_id: parseInt(classId) })
  return response.data
}

export const getClassStudents = async (classId) => {
  const response = await api.get(`/classes/${classId}/students`)
  return response.data
}

export const deleteClass = async (classId) => {
  await api.delete(`/classes/${classId}`)
}
