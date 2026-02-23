import { ref, computed } from 'vue'

export function useTimer() {
    const elapsedTime = ref(0)
    let timerInterval: number | null = null

    const formattedDuration = computed(() => {
        const mins = Math.floor(elapsedTime.value / 60)
        const secs = elapsedTime.value % 60
        return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
    })

    const startTimer = () => {
        elapsedTime.value = 0
        if (timerInterval) clearInterval(timerInterval)
        timerInterval = window.setInterval(() => {
            elapsedTime.value++
        }, 1000)
    }

    const stopTimer = () => {
        if (timerInterval) clearInterval(timerInterval)
        timerInterval = null
    }

    return {
        elapsedTime,
        formattedDuration,
        startTimer,
        stopTimer
    }
}
