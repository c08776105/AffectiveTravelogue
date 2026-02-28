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
                class="position-absolute bottom-0 left-0 right-0 z-10 pa-4 pb-8 d-flex gap-4"
            >
                <v-btn
                    v-if="planningMode === 'route' && startPoint"
                    color="surface"
                    height="56"
                    class="flex-1 rounded-xl font-weight-bold text-error"
                    elevation="3"
                    @click="resetRoute"
                >
                    Reset
                </v-btn>

                <v-btn
                    block
                    height="56"
                    color="primary"
                    class="flex-1 rounded-xl font-weight-bold shadow-lg"
                    elevation="4"
                    @click="startWalk"
                    :disabled="
                        planningMode === 'route' && (!startPoint || !endPoint)
                    "
                >
                    <v-icon start size="24">{{
                        planningMode === "free" ? "mdi-play" : "mdi-navigation"
                    }}</v-icon>
                    Start {{ planningMode === "free" ? "Adventure" : "Route" }}
                </v-btn>
            </div>
        </template>

        <!-- ACTIVE WALKING MODE -->
        <template v-else>
            <div
                class="position-absolute bottom-0 left-0 right-0 z-20 bg-surface rounded-t-xl elevation-10 pa-6 pb-8 safe-area-bottom"
            >
                <!-- Recording Indicator -->
                <div
                    class="d-flex align-center justify-space-between mb-6 pa-3 bg-red-lighten-5 rounded-lg border-thin-red"
                >
                    <div class="d-flex align-center">
                        <div
                            class="pulse-animation rounded-circle bg-error mr-3"
                            style="width: 12px; height: 12px"
                        ></div>
                        <span class="text-body-2 font-weight-bold text-error"
                            >Live Recording</span
                        >
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
import { ref, computed, onMounted, onUnmounted, shallowRef } from "vue";
import { useRouter } from "vue-router";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import MapLibreGlDirections from "@maplibre/maplibre-gl-directions";
import ObservationDialog from "@/components/ObservationDialog.vue";
import { useRouteStore } from "@/stores/route";
import { useTimer } from "@/utils/useTimer";
import { storeToRefs } from "pinia";
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

// Mock current location (Dublin)
const currentLocation = ref({ lat: 53.3498, lng: -6.2603 });

onMounted(() => {
    if (!navigator.geolocation) {
        canLocate.value = false;
    }

    map.value = new maplibregl.Map({
        container: "map-container",
        style: "https://tiles.openfreemap.org/styles/liberty",
        center: [-6.2603, 53.3498],
        zoom: 13,
        attributionControl: false,
    });

    map.value.on("click", handleMapClick);

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

        // Calculate dérive jitter (forced deviation)
        // Midpoint
        const midLat = (startPoint.value.lat + endPoint.value.lat) / 2;
        const midLng = (startPoint.value.lng + endPoint.value.lng) / 2;

        // Random offset: roughly 0.5km to 1.5km
        // 1 degree latitude is approx 111km, so 0.01 is about 1.1km.
        // Used 0.03 (3.3km) of a deviation for a starting point
        const offsetLat = (Math.random() - 0.5) * 0.03;
        const offsetLng = (Math.random() - 0.5) * 0.03;

        const jitterPoint = {
            lat: midLat + offsetLat,
            lng: midLng + offsetLng,
        };

        // Ensure the routing plugin includes this jittered point
        directions.value.interactive = true;
        directions.value.setWaypoints([
            [startPoint.value.lng, startPoint.value.lat], // Start point
            [jitterPoint.lng, jitterPoint.lat], // Jitter deviation
            [endPoint.value.lng, endPoint.value.lat], // End point
        ]);

        drawRouteLine(); // Fallback dashed line connecting the 3 points
    }
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

    // Attempt to inject the jitter point for the visual dashed line if available
    try {
        if (
            directions.value &&
            directions.value.getWaypoints &&
            directions.value.getWaypoints().length === 3
        ) {
            coords = [
                [startPoint.value.lng, startPoint.value.lat],
                directions.value.getWaypoints()[1].geometry.coordinates,
                [endPoint.value.lng, endPoint.value.lat],
            ];
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
    markers.value.forEach((m) => m.remove());
    markers.value = [];
    if (map.value?.getLayer("route")) map.value.removeLayer("route");
    if (map.value?.getSource("route")) map.value.removeSource("route");
}

async function startWalk() {
    // Start new route via store
    await routeStore.createRoute({
        startLat: currentLocation.value.lat, // Should be real GPS
        startLon: currentLocation.value.lng,
        endLat:
            planningMode.value === "route" && endPoint.value
                ? endPoint.value.lat
                : currentLocation.value.lat,
        endLon:
            planningMode.value === "route" && endPoint.value
                ? endPoint.value.lng
                : currentLocation.value.lng,
    });

    isWalking.value = true;
    startTimer();
}

async function endWalk() {
    isWalking.value = false;
    stopTimer();

    // Slight delay for visual feedback
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

.border-thin-red {
    border: 1px solid rgba(239, 68, 68, 0.2);
}

.safe-area-bottom {
    padding-bottom: max(24px, env(safe-area-inset-bottom));
}
</style>
