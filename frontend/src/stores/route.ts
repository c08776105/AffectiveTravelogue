import { defineStore } from "pinia";
import { ref, computed } from "vue";
import { apiClient } from "@/api/client";
import type { Route, Walk, Observation, LatLng } from "@/types";

// Mock initial history
const MOCK_HISTORY: Walk[] = [
  {
    id: "1",
    startTime: Date.now() - 86400000 * 2,
    endTime: Date.now() - 86400000 * 2 + 2700000,
    title: "Urban Exploration",
    mood: "🌆",
    path: [
      { lat: 53.3498, lng: -6.2603 },
      { lat: 53.3508, lng: -6.2593 },
    ],
    observations: [],
    distance: 3.2,
    duration: 45,
    isActive: false,
  },
];

export const useRouteStore = defineStore("route", () => {
  // State
  const currentRoute = ref<Route | null>(null);
  const waypoints = ref<any[]>([]);
  const currentPath = ref<LatLng[]>([]);
  const history = ref<Walk[]>(MOCK_HISTORY);

  // Getters
  const currentWalk = computed((): Walk | null => {
    if (!currentRoute.value) return null;
    return {
      id: currentRoute.value.id,
      startTime: new Date().getTime(), // Approximate start time if not in route object
      title: "Current Journey",
      mood: "🚶",
      path: currentPath.value,
      observations: [], // Mapped from waypoints if we had full observation objects
      distance: 0, // Should be calculated from path
      duration: 0,
      isActive: true,
    };
  });

  const pastWalks = computed(() => history.value);

  // Actions
  const createRoute = async (routeData: any) => {
    try {
      const response = await apiClient.post("/routes", routeData);
      currentRoute.value = response.data;
      currentPath.value = []; // Reset path for new route
      waypoints.value = [];
      return response.data;
    } catch (e) {
      console.warn("Backend not available. Using mock route.", e);
      currentRoute.value = { id: "mock-route-" + Date.now(), ...routeData };
      currentPath.value = [];
      waypoints.value = [];
      return currentRoute.value;
    }
  };

  const submitWaypoint = async (waypoint: {
    latitude: number;
    longitude: number;
    text_note?: string;
  }) => {
    if (!currentRoute.value) return;

    try {
      const response = await apiClient.post("/waypoint", {
        route_id: currentRoute.value.id,
        ...waypoint,
        timestamp: new Date().toISOString(),
      });

      const newPoint = response.data;
      waypoints.value.push(newPoint);
      currentPath.value.push({
        lat: waypoint.latitude,
        lng: waypoint.longitude,
      });
      return newPoint;
    } catch (error) {
      console.warn("Failed to submit waypoint, mocking success:", error);
      const newPoint = { id: "mock-wp-" + Date.now(), ...waypoint };
      waypoints.value.push(newPoint);
      currentPath.value.push({
        lat: waypoint.latitude,
        lng: waypoint.longitude,
      });
      return newPoint;
    }
  };

  const submitObservation = async (observation: {
    latitude: number;
    longitude: number;
    type: string;
    content: string;
    image?: string;
    audio?: string;
  }) => {
    const noteContent = JSON.stringify({
      type: observation.type,
      text: observation.content,
      hasImage: !!observation.image,
      hasAudio: !!observation.audio,
    });

    return submitWaypoint({
      latitude: observation.latitude,
      longitude: observation.longitude,
      text_note: noteContent,
    });
  };

  const finaliseRoute = async () => {
    if (!currentRoute.value) return;

    try {
      await apiClient.post("/route/finalise", {
        route_id: currentRoute.value.id,
        end_time: new Date().toISOString(),
      });
    } catch (error) {
      console.warn("Failed to finalise route, mocking success:", error);
    }

    // Add to local history for immediate feedback
    history.value.unshift({
      id: currentRoute.value.id,
      startTime: Date.now() - currentPath.value.length * 60000, // Approximate
      endTime: Date.now(),
      title: "New Walk",
      mood: "🌟",
      path: [...currentPath.value],
      observations: waypoints.value.map((w) => ({
        type: "note",
        text: w.text_note,
      })),
      distance: currentPath.value.length * 0.5, // Mock calculate
      duration: currentPath.value.length, // Mock Calculate
      isActive: false,
    });

    // Reset current state
    currentRoute.value = null;
    currentPath.value = [];
    waypoints.value = [];
  };

  return {
    // State
    currentRoute,
    waypoints,
    currentPath,
    history,

    // Getters
    currentWalk,
    pastWalks,

    // Actions
    createRoute,
    submitWaypoint,
    submitObservation,
    finaliseRoute,
  };
});
