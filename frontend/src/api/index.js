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
  parkingScatter: () => api.get('/station/parking/scatter'),
  peakComparison: (topN = 20) => api.get('/station/peak/comparison', { params: { topN } }),
  hourly: (stationId) => api.get(`/station/${stationId}/hourly`),
  transferHub: (topN = 20) => api.get('/station/transfer-hub', { params: { topN } }),
  clusterParkingStats: () => api.get('/station/cluster/parking-stats'),
  hubRanking: () => api.get('/station/hub-ranking'),
}

export const sectionApi = {
  drivingStats: (timeRange = 'all', topN = 50) =>
    api.get('/section/driving/stats', { params: { timeRange, topN } }),
  pathsByStation: (stationId) =>
    api.get(`/section/by-station/${stationId}`),
  pathsByRoute: (routeId) =>
    api.get(`/section/by-route/${routeId}`),
  allPaths: () =>
    api.get('/section/all-paths'),
}

export const routeApi = {
  list: () => api.get('/route/list'),
  detail: (routeId) => api.get(`/route/${routeId}/detail`),
  byCluster: (clusterId) => api.get(`/route/by-cluster/${clusterId}`),
  analysis: (routeId, direction = 'up') => api.get(`/route/${routeId}/analysis`, { params: { direction } }),
}
