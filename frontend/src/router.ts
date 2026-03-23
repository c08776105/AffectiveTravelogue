import { createRouter, createWebHistory } from 'vue-router'
import AppLayout from './components/AppLayout.vue'
import Home from './views/Home.vue'
import RouteStudio from './views/RouteStudio.vue'
import Journal from './views/Journal.vue'
import TravelogueView from './views/TravelogueView.vue'
import EvaluationView from './views/EvaluationView.vue'

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
                },
                {
                    path: '/journal/:id',
                    name: 'Travelogue',
                    component: TravelogueView
                },
                {
                    path: '/journal/:id/evaluation',
                    name: 'Evaluation',
                    component: EvaluationView
                }
            ]
        }
    ]
})

export default router
