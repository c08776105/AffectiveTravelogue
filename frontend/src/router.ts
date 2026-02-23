import { createRouter, createWebHistory } from 'vue-router'
import AppLayout from './components/AppLayout.vue'
import Home from './views/Home.vue'
import RouteStudio from './views/RouteStudio.vue'
import Journal from './views/Journal.vue'

const router = createRouter({
    history: createWebHistory(),
    routes: [
        {
            path: '/',
            component: AppLayout,
            children: [
                {
                    path: '',
                    name: 'Home',
                    component: Home
                },
                {
                    path: '/map',
                    name: 'Map',
                    component: RouteStudio
                },
                {
                    path: '/journal',
                    name: 'Journal',
                    component: Journal
                }
            ]
        }
    ]
})

export default router
