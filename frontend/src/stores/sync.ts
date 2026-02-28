import { defineStore } from "pinia";
import { ref, watch } from "vue";
import { apiService } from "@/api/services";
import type { WaypointCreate, RouteUpdate } from "@/api/types";

export interface SyncTask {
    type: 'createRoute' | 'submitWaypoint' | 'finaliseRoute';
    payload: any;
}

export const useSyncStore = defineStore("sync", () => {
    const isOnline = ref(true);
    const pendingTasks = ref<SyncTask[]>([]);

    // Load from local storage if exists
    const storedTasks = localStorage.getItem('sync_tasks');
    if (storedTasks) {
        try {
            pendingTasks.value = JSON.parse(storedTasks);
        } catch (e) { }
    }

    watch(() => pendingTasks.value, (tasks) => {
        localStorage.setItem('sync_tasks', JSON.stringify(tasks));
    }, { deep: true });

    const checkHealth = async () => {
        try {
            await apiService.healthCheck();
            if (!isOnline.value) {
                isOnline.value = true;
                processQueue();
            } else {
                isOnline.value = true;
            }
        } catch (error) {
            isOnline.value = false;
        }
    };

    const startHealthCheck = () => {
        // Check every 30 seconds
        setInterval(checkHealth, 30000);
        checkHealth();
    };

    const enqueueTask = (task: SyncTask) => {
        pendingTasks.value.push(task);
    };

    const processQueue = async () => {
        if (!isOnline.value || pendingTasks.value.length === 0) return;

        console.log(`Processing ${pendingTasks.value.length} pending offline tasks...`);

        // Take a snapshot
        const queue = [...pendingTasks.value];
        pendingTasks.value = [];

        for (const task of queue) {
            try {
                if (task.type === 'submitWaypoint') {
                    await apiService.submitWaypoint(task.payload as WaypointCreate);
                } else if (task.type === 'finaliseRoute') {
                    await apiService.finaliseRoute(task.payload.id, task.payload.data as RouteUpdate);
                } else if (task.type === 'createRoute') {
                    // For now handled optimistically in the route store where we just cache the request
                    // We might need to map fake IDs to real IDs later. 
                    // This serves as an example of what can be expanded.
                }
            } catch (e) {
                console.error('Failed to process task in queue, pushing back', e);
                pendingTasks.value.push(task);
                isOnline.value = false; // likely offline again
                break; // Stop processing further
            }
        }
    };

    return {
        isOnline,
        pendingTasks,
        startHealthCheck,
        enqueueTask,
        processQueue
    };
});
