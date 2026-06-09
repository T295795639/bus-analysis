import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', redirect: '/map' },
  { path: '/map', component: () => import('../views/MapView.vue') },
  { path: '/ranking', component: () => import('../views/RankingView.vue') },
  { path: '/section', component: () => import('../views/SectionAnalysisView.vue') },
  { path: '/parking', component: () => import('../views/ParkingAnalysisView.vue') },
  { path: '/route', component: () => import('../views/RouteDetailView.vue') },
]

export default createRouter({
  history: createWebHistory(),
  routes,
})
