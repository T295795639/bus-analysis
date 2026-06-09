import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000
})

api.interceptors.response.use(
  res => res.data,
  err => Promise.reject(err)
)

export const stationApi = {
  listAll: () => api.get('/station/all'),
  listRoutes: (stationId) => api.get(`/station/${stationId}/routes`),
  listByRoute: (routeId) => api.get(`/station/by-route/${routeId}`),
  ranking: (topN = 20) => api.get('/station/ranking', { params: { topN } }),
  parkingStats: (topN = 20) => api.get('/station/parking/stats', { params: { topN } }),
}

export const sectionApi = {
  drivingStats: (timeRange = 'all', topN = 50) =>
    api.get('/section/driving/stats', { params: { timeRange, topN } }),
  pathsByRoute: (routeId) =>
    api.get(`/section/by-route/${routeId}`),
}

export const routeApi = {
  list: () => api.get('/route/list'),
  detail: (routeId) => api.get(`/route/${routeId}/detail`),
}
