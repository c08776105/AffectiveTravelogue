<template>
    <div
        class="fill-height position-relative bg-surface-variant overflow-hidden"
    >
        <!-- Map Container -->
        <div id="map-container" class="w-100 h-100"></div>

        <!-- PLANNING MODE CONTROLS -->
        <template v-if="!isWalking">
            <!-- Mode Toggle -->
            <div
                class="position-absolute top-0 left-0 right-0 z-10 pa-4 pt-12 d-flex justify-center pointer-events-none"
            >
                <div
                    class="bg-surface rounded-xl shadow-lg d-flex pa-1 pointer-events-auto"
                    style="border: 1px solid rgba(0, 0, 0, 0.05)"
                >
                    <v-btn
                        variant="text"
                        rounded="lg"
                        height="40"
                        class="px-6 font-weight-bold"
                        :color="
                            planningMode === 'free'
                                ? 'primary'
                                : 'medium-emphasis'
                        "
                        :class="{
                            'bg-primary-lighten-5': planningMode === 'free',
                        }"
                        @click="setMode('free')"
                    >
                        <v-icon start icon="mdi-walk"></v-icon>
                        Free Walk
                    </v-btn>
                    <v-btn
                        variant="text"
                        rounded="lg"
                        height="40"
                        class="px-6 font-weight-bold"
                        :color="
                            planningMode === 'route'
                                ? 'primary'
                                : 'medium-emphasis'
                        "
                        :class="{
                            'bg-primary-lighten-5': planningMode === 'route',
                        }"
                        @click="setMode('route')"
                    >
                        <v-icon start icon="mdi-map-marker-path"></v-icon>
                        Route Plan
                    </v-btn>
                </div>
            </div>

            <!-- Instructions (Route Mode) -->
            <div
                v-if="planningMode === 'route' && !startPoint"
                class="position-absolute top-0 left-0 right-0 mt-16 pt-12 d-flex justify-center pointer-events-none"
            >
                <v-card
                    class="px-4 py-2 rounded-lg bg-surface elevation-3 border-l-4 border-primary"
                >
                    <span class="text-caption font-weight-bold"
                        >Tap map to place START point</span
                    >
                </v-card>
            </div>
            <div
                v-if="planningMode === 'route' && startPoint && !endPoint"
                class="position-absolute top-0 left-0 right-0 mt-16 pt-12 d-flex justify-center pointer-events-none"
            >
                <v-card
                    class="px-4 py-2 rounded-lg bg-surface elevation-3 border-l-4 border-secondary"
                >
                    <span class="text-caption font-weight-bold"
                        >Tap map to place END point</span
                    >
                </v-card>
            </div>

            <!-- Locate me FAB -->
            <v-fab
                :disabled="!canLocate"
                icon
                location="right end"
                size="large"
                app
                color="white"
                class="mt-4 mr-4"
                @click="locateMe"
            >
                <v-icon>mdi-crosshairs-gps</v-icon>
            </v-fab>

            <!-- Start Actions -->
            <div
                class="position-absolute bottom-0 left-0 right-0 z-10 pa-4 pb-8"
            >
                <!-- Dérive Settings (Route Mode only) -->
                <v-card
                    v-if="planningMode === 'route'"
                    class="pa-4 mb-3 rounded-xl"
                    elevation="2"
                >
                    <div
                        class="text-overline font-weight-bold text-primary mb-3"
                        style="font-size: 0.65rem; letter-spacing: 0.08em"
                    >
                        Dérive Settings
                    </div>

                    <div class="mb-2">
                        <div class="d-flex justify-space-between align-center mb-1">
                            <span class="text-caption text-medium-emphasis">Deviation Points</span>
                            <v-chip size="x-small" color="primary" variant="tonal">
                                {{ derivePoints }}
                            </v-chip>
                        </div>
                        <v-slider
                            v-model="derivePoints"
                            :min="1"
                            :max="5"
                            :step="1"
                            hide-details
                            density="compact"
                            color="primary"
                            class="mt-n1"
                        />
                    </div>

                    <div>
                        <div class="d-flex justify-space-between align-center mb-1">
                            <span class="text-caption text-medium-emphasis">Deviation Distance</span>
                            <v-chip size="x-small" color="secondary" variant="tonal">
                                {{ deviationMeters }}m
                            </v-chip>
                        </div>
                        <v-slider
                            v-model="deviationMeters"
                            :min="100"
                            :max="2000"
                            :step="100"
                            hide-details
                            density="compact"
                            color="secondary"
                            class="mt-n1"
                        />
                    </div>
                </v-card>

                <!-- Action Buttons -->

                <!-- Free walk -->
                <template v-if="planningMode === 'free'">
                    <v-btn
                        block
                        height="56"
                        color="primary"
                        class="rounded-xl font-weight-bold shadow-lg"
                        elevation="4"
                        @click="startWalk"
                    >
                        <v-icon start size="24">mdi-play</v-icon>
                        Start Adventure
                    </v-btn>
                </template>

                <!-- Route plan: both points placed, route not yet calculated -->
                <template v-else-if="startPoint && endPoint && !routeCalculated">
                    <div class="d-flex gap-4">
                        <v-btn
                            color="surface"
                            height="56"
                            class="rounded-xl font-weight-bold text-error"
                            elevation="3"
                            @click="resetRoute"
                        >
                            Reset
                        </v-btn>
                        <v-btn
                            height="56"
                            color="primary"
                            class="flex-1 rounded-xl font-weight-bold shadow-lg"
                            elevation="4"
                            @click="calculateRoute"
                        >
                            <v-icon start size="22">mdi-map-marker-path</v-icon>
                            Calculate Route
                        </v-btn>
                    </div>
                </template>

                <!-- Route plan: route calculated — recalculate or start -->
                <template v-else-if="startPoint && endPoint && routeCalculated">
                    <div class="d-flex gap-4">
                        <v-btn
                            color="surface"
                            height="56"
                            class="rounded-xl font-weight-bold text-error"
                            elevation="3"
                            @click="resetRoute"
                        >
                            Reset
                        </v-btn>
                        <v-btn
                            height="56"
                            variant="outlined"
                            color="primary"
                            class="rounded-xl font-weight-bold"
                            @click="calculateRoute"
                        >
                            <v-icon start size="20">mdi-refresh</v-icon>
                            Recalculate
                        </v-btn>
                        <v-btn
                            height="56"
                            color="primary"
                            class="flex-1 rounded-xl font-weight-bold shadow-lg"
                            elevation="4"
                            @click="startWalk"
                        >
                            <v-icon start size="22">mdi-navigation</v-icon>
                            Start Route
                        </v-btn>
                    </div>
                </template>

                <!-- Route plan: placing points (start only or neither) -->
                <template v-else>
                    <div class="d-flex gap-4">
                        <v-btn
                            v-if="startPoint"
                            color="surface"
                            height="56"
                            class="rounded-xl font-weight-bold text-error"
                            elevation="3"
                            @click="resetRoute"
                        >
                            Reset
                        </v-btn>
                        <!-- Only show when no start placed and geolocation available -->
                        <v-btn
                            v-if="!startPoint && canLocate"
                            height="56"
                            variant="outlined"
                            color="primary"
                            class="rounded-xl font-weight-bold"
                            @click="useCurrentLocationAsStart"
                        >
                            <v-icon start size="20">mdi-crosshairs-gps</v-icon>
                            Use My Location
                        </v-btn>
                        <v-btn
                            height="56"
                            color="primary"
                            class="flex-1 rounded-xl font-weight-bold shadow-lg"
                            elevation="4"
                            disabled
                        >
                            <v-icon start size="22">mdi-navigation</v-icon>
                            Start Route
                        </v-btn>
                    </div>
                </template>
            </div>
        </template>

        <!-- ACTIVE WALKING MODE -->
        <template v-else>
            <div
                class="position-absolute bottom-0 left-0 right-0 z-20 bg-surface rounded-t-xl elevation-10 pa-6 pb-8 safe-area-bottom"
            >
                <!-- Walk status bar -->
                <div
                    class="d-flex align-center justify-space-between mb-6 pa-3 bg-primary-lighten-5 rounded-lg"
                    style="border: 1px solid rgba(var(--v-theme-primary), 0.2)"
                >
                    <div class="d-flex align-center">
                        <v-icon color="primary" class="mr-2" size="20">mdi-walk</v-icon>
                        <span class="text-body-2 font-weight-bold text-primary">Walking</span>
                    </div>
                    <div class="text-h5 font-weight-mono font-weight-black">
                        {{ formattedDuration }}
                    </div>
                </div>

                <!-- Controls -->
                <div class="d-flex gap-4">
                    <v-btn
                        color="primary"
                        height="64"
                        class="flex-1 rounded-xl font-weight-bold"
                        elevation="2"
                        @click="showObservationModal = true"
                    >
                        <v-icon start size="28">mdi-plus-circle</v-icon>
                        Add Note
                    </v-btn>
                    <v-btn
                        color="error"
                        height="64"
                        class="flex-1 rounded-xl font-weight-bold"
                        variant="flat"
                        @click="endWalk"
                    >
                        <v-icon start size="28">mdi-stop</v-icon>
                        Finish
                    </v-btn>
                </div>
            </div>
        </template>

        <!-- Observation Dialog -->
        <observation-dialog
            v-model="showObservationModal"
            :location="currentLocation"
            @save-observation="handleSaveObservation"
        ></observation-dialog>
    </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, shallowRef } from "vue";
import { useRouter } from "vue-router";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import MapLibreGlDirections from "@maplibre/maplibre-gl-directions";
import ObservationDialog from "@/components/ObservationDialog.vue";
import { useRouteStore } from "@/stores/route";
import { useTimer } from "@/utils/useTimer";
import type { LatLng } from "@/types";

const router = useRouter();
const routeStore = useRouteStore();

// State
const canLocate = ref(true);
const map = shallowRef<maplibregl.Map | null>(null);
const directions = shallowRef<any>(null);
const planningMode = ref<"free" | "route">("free");
const isWalking = ref(false);
const showObservationModal = ref(false);
const { elapsedTime, formattedDuration, startTimer, stopTimer } = useTimer();

// Lifecycle guard
const isDestroyed = ref(false);

// Route Planning State
const startPoint = ref<{ lat: number; lng: number } | null>(null);
const endPoint = ref<{ lat: number; lng: number } | null>(null);
const markers = ref<maplibregl.Marker[]>([]);

// Dérive configuration
const derivePoints = ref(1);
const deviationMeters = ref(500);
const routeCalculated = ref(false);

const currentLocation = ref({ lat: 53.3498, lng: -6.2603 });

// Live location tracking during walk
let geoWatchId: number | null = null;
const userLocationMarker = shallowRef<maplibregl.Marker | null>(null);

onMounted(() => {
    if (!navigator.geolocation) {
        canLocate.value = false;
    }

    map.value = new maplibregl.Map({
        // Default center used only until geolocation resolves
        container: "map-container",
        style: "https://tiles.openfreemap.org/styles/liberty",
        center: [-6.2603, 53.3498],
        zoom: 13,
        attributionControl: false,
    });

    map.value.on("click", handleMapClick);

    // Fly to the user's real position as soon as the map is ready
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
            (position) => {
                const { latitude, longitude } = position.coords;
                currentLocation.value = { lat: latitude, lng: longitude };
                map.value?.flyTo({ center: [longitude, latitude], zoom: 15 });
            },
            () => { /* stay on default centre */ },
        );
    }

    map.value.on("load", () => {
        if (isDestroyed.value) return; // Abort MapLibre plugins if component unmounted before map tiles finished loading

        directions.value = new MapLibreGlDirections(map.value as any, {
            api: "https://router.project-osrm.org/route/v1",
            profile: "foot",
            requestOptions: {
                alternatives: "true",
                overview: "full",
            },
        });

        directions.value.interactive = true;
    });
});

function locateMe() {
    navigator.geolocation.getCurrentPosition(
        (position) => {
            const { latitude, longitude } = position.coords;
            map.value.flyTo({ center: [longitude, latitude], zoom: 15 });
        },
        (error) => {
            console.error(`Error getting location: ${error.message}`);
        },
    );
}

function setMode(mode: "free" | "route") {
    planningMode.value = mode;
    resetRoute();
}

function handleMapClick(e: maplibregl.MapMouseEvent) {
    if (isWalking.value) return; // Don't interact during walk
    if (planningMode.value !== "route") return;

    const { lng, lat } = e.lngLat;

    if (!startPoint.value) {
        startPoint.value = { lat, lng };
        addMarker(lng, lat, "#7C3AED"); // Primary purple
    } else if (!endPoint.value) {
        endPoint.value = { lat, lng };
        addMarker(lng, lat, "#EC4899"); // Secondary pink
        // Route is not calculated yet — user must press Calculate Route
    }
}

function useCurrentLocationAsStart() {
    if (startPoint.value) return; // already placed
    startPoint.value = { ...currentLocation.value };
    addMarker(currentLocation.value.lng, currentLocation.value.lat, "#7C3AED");
}

function computeDeriveWaypoints(): [number, number][] {
    if (!startPoint.value || !endPoint.value) return [];

    const waypoints: [number, number][] = [
        [startPoint.value.lng, startPoint.value.lat],
    ];

    const n = derivePoints.value;
    for (let i = 1; i <= n; i++) {
        const fraction = i / (n + 1);
        const baseLat =
            startPoint.value.lat +
            fraction * (endPoint.value.lat - startPoint.value.lat);
        const baseLng =
            startPoint.value.lng +
            fraction * (endPoint.value.lng - startPoint.value.lng);

        // Convert metres to degrees (approximate)
        const latDeg = deviationMeters.value / 111000;
        const lngDeg =
            deviationMeters.value /
            (111000 * Math.cos((baseLat * Math.PI) / 180));

        const jitteredLat = baseLat + (Math.random() - 0.5) * 2 * latDeg;
        const jitteredLng = baseLng + (Math.random() - 0.5) * 2 * lngDeg;
        waypoints.push([jitteredLng, jitteredLat]);
    }

    waypoints.push([endPoint.value.lng, endPoint.value.lat]);
    return waypoints;
}

function calculateRoute() {
    if (!startPoint.value || !endPoint.value || !directions.value) return;
    directions.value.setWaypoints(computeDeriveWaypoints());
    drawRouteLine();
    routeCalculated.value = true;
}

function addMarker(lng: number, lat: number, color: string) {
    if (!map.value) return;
    const marker = new maplibregl.Marker({ color })
        .setLngLat([lng, lat])
        .addTo(map.value);
    markers.value.push(marker);
}

function drawRouteLine() {
    if (!map.value || !startPoint.value || !endPoint.value) return;
    // Simple straight line for mockup (if directions plugin fails)
    let coords = [
        [startPoint.value.lng, startPoint.value.lat],
        [endPoint.value.lng, endPoint.value.lat],
    ];

    // Use all waypoints set on the directions plugin for the dashed preview
    try {
        if (directions.value?.getWaypoints) {
            const wps = directions.value.getWaypoints();
            if (wps.length >= 2) {
                coords = wps.map((wp: any) => wp.geometry.coordinates);
            }
        }
    } catch (e) {
        /* ignore */
    }

    const geojson: GeoJSON.Feature<GeoJSON.LineString> = {
        type: "Feature",
        properties: {},
        geometry: {
            type: "LineString",
            coordinates: coords,
        },
    };

    if (map.value.getSource("route")) {
        (map.value.getSource("route") as maplibregl.GeoJSONSource).setData(
            geojson,
        );
    } else {
        map.value.addSource("route", {
            type: "geojson",
            data: geojson,
        });
        map.value.addLayer({
            id: "route",
            type: "line",
            source: "route",
            layout: {
                "line-join": "round",
                "line-cap": "round",
            },
            paint: {
                "line-color": "#7C3AED",
                "line-width": 4,
                "line-dasharray": [2, 2],
            },
        });
    }
}

function resetRoute() {
    startPoint.value = null;
    endPoint.value = null;
    routeCalculated.value = false;
    markers.value.forEach((m) => m.remove());
    markers.value = [];
    if (directions.value) directions.value.clear();
    if (map.value?.getLayer("route")) map.value.removeLayer("route");
    if (map.value?.getSource("route")) map.value.removeSource("route");
}

async function startWalk() {
    const isRoutePlan = planningMode.value === "route" && endPoint.value;
    await routeStore.createRoute({
        name: `Journey ${new Date().toLocaleDateString()}`,
        startLat: currentLocation.value.lat,
        startLon: currentLocation.value.lng,
        endLat: isRoutePlan ? endPoint.value!.lat : currentLocation.value.lat,
        endLon: isRoutePlan ? endPoint.value!.lng : currentLocation.value.lng,
        ...(isRoutePlan && {
            derivePoints: derivePoints.value,
            deviationMeters: deviationMeters.value,
        }),
    });

    isWalking.value = true;
    startTimer();

    // Track user position and keep map centred on them
    if (navigator.geolocation) {
        geoWatchId = navigator.geolocation.watchPosition(
            (position) => {
                const { latitude, longitude } = position.coords;
                currentLocation.value = { lat: latitude, lng: longitude };

                // Move or create the "you are here" marker
                if (userLocationMarker.value) {
                    userLocationMarker.value.setLngLat([longitude, latitude]);
                } else if (map.value) {
                    userLocationMarker.value = new maplibregl.Marker({
                        color: "#2196F3",
                        scale: 0.8,
                    })
                        .setLngLat([longitude, latitude])
                        .addTo(map.value);
                }

                map.value?.easeTo({ center: [longitude, latitude], duration: 800 });
            },
            (err) => console.warn("Location tracking error:", err),
            { enableHighAccuracy: true, maximumAge: 5000 },
        );
    }
}

async function endWalk() {
    isWalking.value = false;
    stopTimer();

    if (geoWatchId !== null) {
        navigator.geolocation.clearWatch(geoWatchId);
        geoWatchId = null;
    }
    userLocationMarker.value?.remove();
    userLocationMarker.value = null;

    setTimeout(async () => {
        await routeStore.finaliseRoute();
        router.push("/journal");
    }, 500);
}

function handleSaveObservation(obs: any) {
    routeStore.submitObservation({
        latitude: currentLocation.value.lat,
        longitude: currentLocation.value.lng,
        type: obs.type,
        content: obs.text || obs.audioData || obs.caption || "",
        image: obs.imageData,
        audio: obs.audioData,
    });
    // Add visual marker for observation
    addMarker(currentLocation.value.lng, currentLocation.value.lat, "#10B981");
}

onUnmounted(() => {
    isDestroyed.value = true;
    stopTimer();

    if (geoWatchId !== null) {
        navigator.geolocation.clearWatch(geoWatchId);
    }
    userLocationMarker.value?.remove();

    if (directions.value) {
        directions.value.interactive = false;
        directions.value.clear();
    }

    if (map.value) {
        map.value.remove();
    }
});
</script>

<style scoped>
.z-10 {
    z-index: 10;
}
.z-20 {
    z-index: 20;
}
.pointer-events-none {
    pointer-events: none;
}
.pointer-events-auto {
    pointer-events: auto;
}
.gap-3 {
    gap: 12px;
}
.gap-4 {
    gap: 16px;
}


.safe-area-bottom {
    padding-bottom: max(24px, env(safe-area-inset-bottom));
}
</style>
