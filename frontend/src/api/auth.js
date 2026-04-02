import api from './axios'

// Login user and return token + user info
export const login = async (username, password) => {
  const formData = new FormData()
  formData.append('username', username)
  formData.append('password', password)

  const response = await api.post('/auth/login', formData)
  return response.data
}

// Get currently logged-in user info
export const getMe = async () => {
  const response = await api.get('/auth/me')
  return response.data
}

// Register a new user (admin only)
export const registerUser = async (userData) => {
  const response = await api.post('/auth/register', userData)
  return response.data
}

// Get all users (admin only)
export const getUsers = async () => {
  const response = await api.get('/auth/users')
  return response.data
}
