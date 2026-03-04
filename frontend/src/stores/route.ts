import { defineStore } from "pinia";
import { ref, computed } from "vue";
import { apiService } from "@/api/services";
import { useSyncStore } from "@/stores/sync";
import type { Route, Walk, LatLng } from "@/types";

const STORAGE_KEY = "at_active_walk";
const WALK_EXPIRY_MS = 4 * 60 * 60 * 1000; // 4 hours

interface PersistedWalk {
  route: Route;
  waypoints: any[];
  path: LatLng[];
  startedAt: number;
}

function loadFromStorage(): PersistedWalk | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const saved: PersistedWalk = JSON.parse(raw);
    if (Date.now() - saved.startedAt >= WALK_EXPIRY_MS) {
      localStorage.removeItem(STORAGE_KEY);
      return null;
    }
    return saved;
  } catch {
    return null;
  }
}

export const useRouteStore = defineStore("route", () => {
  // State
  const currentRoute = ref<Route | null>(null);
  const waypoints = ref<any[]>([]);
  const currentPath = ref<LatLng[]>([]);
  const history = ref<Walk[]>([]);
  const walkStartedAt = ref<number | null>(null);

  // Initialise reactively — true if a valid unexpired walk is in storage
  const hasResumableWalk = ref<boolean>(loadFromStorage() !== null);

  // Getters
  const currentWalk = computed((): Walk | null => {
    if (!currentRoute.value) return null;
    return {
      id: currentRoute.value.id,
      startTime: walkStartedAt.value ?? new Date().getTime(),
      title: "Current Journey",
      mood: "🚶",
      path: currentPath.value,
      observations: [],
      distance: 0,
      duration: 0,
      isActive: true,
    };
  });

  const pastWalks = computed(() => history.value);

  // ── Persistence helpers ──────────────────────────────────────────────────

  function persistWalk() {
    if (!currentRoute.value) return;
    const data: PersistedWalk = {
      route: currentRoute.value,
      waypoints: waypoints.value,
      path: currentPath.value,
      startedAt: walkStartedAt.value ?? Date.now(),
    };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
    hasResumableWalk.value = true;
  }

  function clearPersistedWalk() {
    localStorage.removeItem(STORAGE_KEY);
    hasResumableWalk.value = false;
  }

  // ── Actions ──────────────────────────────────────────────────────────────

  /**
   * Restore an in-progress walk from localStorage.
   * Returns the elapsed seconds so the caller can resume the timer,
   * or null if there is nothing to restore.
   */
  const restoreWalk = (): number | null => {
    const saved = loadFromStorage();
    if (!saved) return null;
    currentRoute.value = saved.route;
    waypoints.value = saved.waypoints;
    currentPath.value = saved.path;
    walkStartedAt.value = saved.startedAt;
    hasResumableWalk.value = true;
    return Math.floor((Date.now() - saved.startedAt) / 1000);
  };

  const createRoute = async (routeData: any) => {
    const syncStore = useSyncStore();
    const startedAt = Date.now();
    try {
      const dbRoute = await apiService.createRoute(routeData);
      currentRoute.value = dbRoute;
      currentPath.value = [];
      waypoints.value = [];
      walkStartedAt.value = startedAt;
      persistWalk();
      return dbRoute;
    } catch (e) {
      console.warn("Backend not available. Using mock route.", e);
      syncStore.isOnline = false;
      currentRoute.value = { id: "mock-route-" + Date.now(), ...routeData };
      currentPath.value = [];
      waypoints.value = [];
      walkStartedAt.value = startedAt;
      persistWalk();
      return currentRoute.value;
    }
  };

  const submitWaypoint = async (waypoint: {
    latitude: number;
    longitude: number;
    text_note?: string;
  }) => {
    if (!currentRoute.value) return;

    const syncStore = useSyncStore();
    const payload = {
      routeId: currentRoute.value.id,
      latitude: waypoint.latitude,
      longitude: waypoint.longitude,
      textNote: waypoint.text_note,
    };

    try {
      const newPoint = await apiService.submitWaypoint(payload);
      waypoints.value.push(newPoint);
      currentPath.value.push({ lat: waypoint.latitude, lng: waypoint.longitude });
      persistWalk();
      return newPoint;
    } catch (error) {
      console.warn("Failed to submit waypoint, mocking success:", error);
      syncStore.isOnline = false;
      syncStore.enqueueTask({ type: "submitWaypoint", payload });
      const newPoint = {
        id: "mock-wp-" + Date.now(),
        ...waypoint,
        routeId: payload.routeId,
        storedAt: new Date().toISOString(),
      };
      waypoints.value.push(newPoint);
      currentPath.value.push({ lat: waypoint.latitude, lng: waypoint.longitude });
      persistWalk();
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

    const syncStore = useSyncStore();
    const payload = { id: currentRoute.value.id, data: { status: "completed" } };

    try {
      await apiService.finaliseRoute(payload.id, payload.data);
    } catch (error) {
      console.warn("Failed to finalise route, mocking success:", error);
      syncStore.isOnline = false;
      syncStore.enqueueTask({ type: "finaliseRoute", payload });
    }

    // Add to local history immediately
    history.value.unshift({
      id: currentRoute.value.id,
      startTime: walkStartedAt.value ?? Date.now(),
      endTime: Date.now(),
      title: currentRoute.value.name ?? "New Walk",
      mood: "🌟",
      path: [...currentPath.value],
      observations: waypoints.value.map((w) => ({ type: "note", text: w.text_note })),
      distance: currentPath.value.length * 0.5,
      duration: currentPath.value.length,
      isActive: false,
    });

    // Clear persisted state
    clearPersistedWalk();
    currentRoute.value = null;
    currentPath.value = [];
    waypoints.value = [];
    walkStartedAt.value = null;
  };

  const fetchHistory = async () => {
    const syncStore = useSyncStore();
    try {
      const routes = await apiService.listRoutes();
      history.value = routes.map((r) => ({
        id: r.id,
        title: r.name,
        startTime: new Date(r.createdAt).getTime(),
        mood: "🌍",
        path: [],
        observations: [],
        waypointCount: r.waypointCount ?? 0,
        distance: r.distanceKm ?? 0,
        duration: 0,
        isActive: false,
      }));
    } catch (e) {
      console.warn("Failed to fetch route history. Using local data.", e);
      syncStore.isOnline = false;
    }
  };

  return {
    // State
    currentRoute,
    waypoints,
    currentPath,
    history,
    walkStartedAt,
    hasResumableWalk,

    // Getters
    currentWalk,
    pastWalks,

    // Actions
    createRoute,
    submitWaypoint,
    submitObservation,
    finaliseRoute,
    fetchHistory,
    restoreWalk,
  };
});
