<template>
    <div
        class="fill-height position-relative bg-surface-variant overflow-hidden"
    >
        <!-- Map Container -->
        <div id="map-container" class="w-100 h-100"></div>

        <!-- PLANNING / HISTORY MODE CONTROLS (not walking) -->
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
                        class="px-4 font-weight-bold"
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
                        class="px-4 font-weight-bold"
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
                    <v-btn
                        variant="text"
                        rounded="lg"
                        height="40"
                        class="px-4 font-weight-bold"
                        :color="
                            planningMode === 'history'
                                ? 'primary'
                                : 'medium-emphasis'
                        "
                        :class="{
                            'bg-primary-lighten-5': planningMode === 'history',
                        }"
                        @click="setMode('history')"
                    >
                        <v-icon start icon="mdi-map-clock-outline"></v-icon>
                        History
                    </v-btn>
                </div>
            </div>

            <!-- ── PLANNING MODE UI ──────────────────────────────────── -->
            <template v-if="planningMode !== 'history'">
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
                            <div
                                class="d-flex justify-space-between align-center mb-1"
                            >
                                <span class="text-caption text-medium-emphasis"
                                    >Deviation Points</span
                                >
                                <v-chip
                                    size="x-small"
                                    color="primary"
                                    variant="tonal"
                                    >{{ derivePoints }}</v-chip
                                >
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
                            <div
                                class="d-flex justify-space-between align-center mb-1"
                            >
                                <span class="text-caption text-medium-emphasis"
                                    >Deviation Distance</span
                                >
                                <v-chip
                                    size="x-small"
                                    color="secondary"
                                    variant="tonal"
                                    >{{ deviationMeters }}m</v-chip
                                >
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
                    <template
                        v-else-if="startPoint && endPoint && !routeCalculated"
                    >
                        <div class="d-flex gap-4">
                            <v-btn
                                color="surface"
                                height="56"
                                class="rounded-xl font-weight-bold text-error"
                                elevation="3"
                                @click="resetRoute"
                                >Reset</v-btn
                            >
                            <v-btn
                                height="56"
                                color="primary"
                                class="flex-1 rounded-xl font-weight-bold shadow-lg"
                                elevation="4"
                                @click="calculateRoute"
                            >
                                <v-icon start size="22"
                                    >mdi-map-marker-path</v-icon
                                >
                                Calculate Route
                            </v-btn>
                        </div>
                    </template>

                    <!-- Route plan: route calculated -->
                    <template
                        v-else-if="startPoint && endPoint && routeCalculated"
                    >
                        <div class="d-flex gap-4">
                            <v-btn
                                color="surface"
                                height="56"
                                class="rounded-xl font-weight-bold text-error"
                                elevation="3"
                                @click="resetRoute"
                                >Reset</v-btn
                            >
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

                    <!-- Route plan: placing points -->
                    <template v-else>
                        <div class="d-flex gap-4">
                            <v-btn
                                v-if="startPoint"
                                color="surface"
                                height="56"
                                class="rounded-xl font-weight-bold text-error"
                                elevation="3"
                                @click="resetRoute"
                                >Reset</v-btn
                            >
                            <v-btn
                                v-if="!startPoint && canLocate"
                                height="56"
                                variant="outlined"
                                color="primary"
                                class="rounded-xl font-weight-bold"
                                @click="useCurrentLocationAsStart"
                            >
                                <v-icon start size="20"
                                    >mdi-crosshairs-gps</v-icon
                                >
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

            <!-- ── HISTORY MODE UI ──────────────────────────────────── -->
            <template v-else>
                <!-- Loading history list -->
                <div
                    v-if="loadingHistory"
                    class="position-absolute bottom-0 left-0 right-0 z-10 bg-surface rounded-t-xl elevation-10 d-flex justify-center pa-8"
                >
                    <v-progress-circular indeterminate color="primary" />
                </div>

                <!-- Walk list (no walk selected) -->
                <div
                    v-else-if="!selectedWalkId"
                    class="position-absolute bottom-0 left-0 right-0 z-10 bg-surface rounded-t-xl elevation-10 pa-4 safe-area-bottom"
                    style="
                        max-height: 55vh;
                        display: flex;
                        flex-direction: column;
                    "
                >
                    <h3
                        class="text-h6 font-weight-bold text-grey-darken-4 mb-1 px-1"
                    >
                        Completed Walks
                    </h3>
                    <p class="text-caption text-medium-emphasis mb-3 px-1">
                        Tap a walk to view it on the map
                    </p>

                    <div class="overflow-y-auto flex-1" style="min-height: 0">
                        <v-card
                            v-for="walk in historyWalks"
                            :key="walk.id"
                            class="mb-2 rounded-xl"
                            border
                            flat
                            style="cursor: pointer"
                            @click="selectWalk(walk.id)"
                        >
                            <v-card-item class="pa-3">
                                <div
                                    class="d-flex justify-space-between align-center"
                                >
                                    <div class="overflow-hidden mr-3">
                                        <p
                                            class="text-body-2 font-weight-bold text-grey-darken-3 text-truncate"
                                        >
                                            {{ walk.name }}
                                        </p>
                                        <p
                                            class="text-caption text-medium-emphasis"
                                        >
                                            {{ formatWalkDate(walk.createdAt) }}
                                        </p>
                                    </div>
                                    <div
                                        class="d-flex align-center"
                                        style="gap: 6px; flex-shrink: 0"
                                    >
                                        <v-chip
                                            v-if="walk.waypointCount"
                                            size="x-small"
                                            variant="tonal"
                                            color="secondary"
                                        >
                                            {{ walk.waypointCount }} notes
                                        </v-chip>
                                        <v-icon size="18" color="grey-lighten-1"
                                            >mdi-chevron-right</v-icon
                                        >
                                    </div>
                                </div>
                            </v-card-item>
                        </v-card>

                        <div
                            v-if="historyWalks.length === 0"
                            class="text-center py-8"
                        >
                            <v-icon
                                size="48"
                                color="grey-lighten-2"
                                class="mb-3"
                                >mdi-map-clock-outline</v-icon
                            >
                            <p class="text-body-2 text-medium-emphasis">
                                No completed walks yet.
                            </p>
                        </div>
                    </div>
                </div>

                <!-- Loading selected walk -->
                <div
                    v-else-if="loadingWalk"
                    class="position-absolute bottom-0 left-0 right-0 z-10 bg-surface rounded-t-xl elevation-10 pa-6 d-flex justify-center align-center"
                    style="height: 100px"
                >
                    <v-progress-circular
                        indeterminate
                        color="primary"
                        size="28"
                        class="mr-3"
                    />
                    <span class="text-body-2 text-medium-emphasis"
                        >Loading walk…</span
                    >
                </div>

                <!-- Selected walk panel -->
                <div
                    v-else
                    class="position-absolute bottom-0 left-0 right-0 z-10 bg-surface rounded-t-xl elevation-10 pa-4 pb-6 safe-area-bottom"
                >
                    <div class="d-flex align-center mb-3">
                        <v-btn
                            icon
                            size="small"
                            variant="text"
                            @click="backToHistory"
                        >
                            <v-icon>mdi-arrow-left</v-icon>
                        </v-btn>
                        <div class="ml-2 flex-1 overflow-hidden">
                            <p
                                class="text-body-1 font-weight-bold text-grey-darken-3 text-truncate"
                            >
                                {{ selectedWalkRoute?.name }}
                            </p>
                            <p class="text-caption text-medium-emphasis">
                                {{ selectedWalkWaypoints.length }} waypoints ·
                                tap a marker to view notes
                            </p>
                        </div>
                        <v-btn
                            variant="tonal"
                            color="primary"
                            size="small"
                            rounded="lg"
                            class="ml-2"
                            :to="`/journal/${selectedWalkId}`"
                        >
                            Journal
                        </v-btn>
                    </div>

                    <div
                        class="d-flex align-center"
                        style="gap: 8px; flex-wrap: wrap"
                    >
                        <v-chip
                            v-if="selectedWalkEvaluation"
                            size="small"
                            :color="
                                selectedWalkEvaluation.isEquivalent
                                    ? 'success'
                                    : 'warning'
                            "
                            variant="tonal"
                        >
                            <v-icon start size="14">
                                {{
                                    selectedWalkEvaluation.isEquivalent
                                        ? "mdi-check-circle"
                                        : "mdi-alert-circle"
                                }}
                            </v-icon>
                            BERTScore F1:
                            {{
                                (
                                    selectedWalkEvaluation.bertscoreF1 * 100
                                ).toFixed(1)
                            }}%
                        </v-chip>
                        <v-chip
                            v-else
                            size="small"
                            variant="tonal"
                            color="grey"
                        >
                            <v-icon start size="14">mdi-chart-bar</v-icon>
                            No evaluation
                        </v-chip>
                        <v-chip
                            v-if="selectedWalkRoute?.distanceKm"
                            size="small"
                            variant="tonal"
                            color="blue-grey"
                        >
                            <v-icon start size="14"
                                >mdi-map-marker-distance</v-icon
                            >
                            {{ selectedWalkRoute.distanceKm }} km
                        </v-chip>
                    </div>
                </div>
            </template>
        </template>

        <!-- ── ACTIVE WALKING MODE ──────────────────────────────────── -->
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
                        <v-icon color="primary" class="mr-2" size="20"
                            >mdi-walk</v-icon
                        >
                        <span class="text-body-2 font-weight-bold text-primary"
                            >Walking</span
                        >
                    </div>
                    <div class="text-h5 font-weight-mono font-weight-black">
                        {{ formattedDuration }}
                    </div>
                </div>

                <!-- Controls -->
                <div class="d-flex gap-4 mb-3">
                    <v-btn
                        color="primary"
                        height="64"
                        class="flex-1 rounded-xl font-weight-bold"
                        elevation="2"
                        :loading="isLocating"
                        @click="captureLocationAndAddNote"
                    >
                        <v-icon start size="28">mdi-plus-circle</v-icon>
                        Add Note
                    </v-btn>
                    <v-btn
                        color="error"
                        height="64"
                        class="flex-1 rounded-xl font-weight-bold"
                        variant="flat"
                        @click="showFinishDialog = true"
                    >
                        <v-icon start size="28">mdi-stop</v-icon>
                        Finish
                    </v-btn>
                </div>
                <div class="text-center">
                    <v-btn
                        variant="text"
                        color="grey"
                        size="small"
                        class="text-none"
                        @click="showCancelDialog = true"
                    >
                        Cancel walk &amp; discard
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

        <!-- Cancel Walk Confirmation -->
        <v-dialog v-model="showCancelDialog" max-width="340">
            <v-card class="rounded-xl pa-2">
                <v-card-title class="text-h6 font-weight-bold pt-4 px-4">
                    Discard this walk?
                </v-card-title>
                <v-card-text class="text-body-2 text-medium-emphasis px-4">
                    This will permanently delete the route and all recorded
                    waypoints from the database. This cannot be undone.
                </v-card-text>
                <v-card-actions class="pa-4 pt-0 d-flex gap-3">
                    <v-btn
                        variant="tonal"
                        class="flex-1 rounded-lg font-weight-bold text-none"
                        @click="showCancelDialog = false"
                        >Keep walking</v-btn
                    >
                    <v-btn
                        color="error"
                        variant="flat"
                        class="flex-1 rounded-lg font-weight-bold text-none"
                        :loading="cancelling"
                        @click="discardWalk"
                        >Discard</v-btn
                    >
                </v-card-actions>
            </v-card>
        </v-dialog>

        <!-- Finish Journey Dialog -->
        <v-bottom-sheet v-model="showFinishDialog" inset>
            <v-card class="rounded-t-xl pa-6 pb-8">
                <h3 class="text-h6 font-weight-bold text-grey-darken-4 mb-1">
                    Finish your journey?
                </h3>
                <p class="text-body-2 text-medium-emphasis mb-5">
                    Add an optional final note before saving.
                </p>
                <v-textarea
                    v-model="finalNote"
                    variant="outlined"
                    rounded="lg"
                    rows="4"
                    hide-details
                    placeholder="Any final thoughts about your walk…"
                    class="mb-5"
                />
                <div class="d-flex gap-4">
                    <v-btn
                        variant="tonal"
                        color="grey"
                        height="48"
                        class="flex-1 rounded-xl font-weight-bold"
                        @click="showFinishDialog = false"
                        >Cancel</v-btn
                    >
                    <v-btn
                        variant="tonal"
                        color="primary"
                        height="48"
                        class="flex-1 rounded-xl font-weight-bold"
                        :loading="finishing"
                        @click="confirmEndWalk(false)"
                        >Skip & Finish</v-btn
                    >
                    <v-btn
                        color="error"
                        height="48"
                        class="flex-1 rounded-xl font-weight-bold"
                        :disabled="!finalNote.trim()"
                        :loading="finishing"
                        @click="confirmEndWalk(true)"
                        >Save & Finish</v-btn
                    >
                </div>
            </v-card>
        </v-bottom-sheet>

        <!-- ── WAYPOINT DETAIL SHEET (History mode) ──────────────────── -->
        <v-bottom-sheet v-model="showWaypointSheet" max-height="78vh">
            <v-card class="rounded-t-xl pa-0">
                <div class="pa-4 overflow-y-auto" style="max-height: 78vh">
                    <!-- Header -->
                    <div class="d-flex align-center justify-space-between mb-4">
                        <div>
                            <p class="text-caption text-medium-emphasis">
                                {{
                                    formatWaypointTime(
                                        selectedWaypoint?.storedAt,
                                    )
                                }}
                            </p>
                            <p
                                class="text-body-1 font-weight-bold text-grey-darken-3"
                            >
                                Logged Observation
                            </p>
                        </div>
                        <v-btn
                            icon
                            size="small"
                            variant="text"
                            @click="showWaypointSheet = false"
                        >
                            <v-icon>mdi-close</v-icon>
                        </v-btn>
                    </div>

                    <!-- Human note -->
                    <div class="mb-4">
                        <div class="d-flex align-center mb-2" style="gap: 6px">
                            <v-icon size="16" color="secondary"
                                >mdi-pencil-outline</v-icon
                            >
                            <span
                                class="text-caption font-weight-bold text-uppercase text-grey-darken-1"
                                >Your Note</span
                            >
                        </div>
                        <v-card class="rounded-lg pa-3" border flat>
                            <p
                                class="text-body-2 text-grey-darken-2"
                                style="line-height: 1.6"
                            >
                                {{
                                    parseNoteText(selectedWaypoint?.textNote) ||
                                    "No text note recorded at this waypoint."
                                }}
                            </p>
                        </v-card>
                    </div>

                    <!-- AI Travelogue -->
                    <div class="mb-4">
                        <div
                            class="d-flex align-center justify-space-between mb-2"
                        >
                            <div class="d-flex align-center" style="gap: 6px">
                                <v-icon size="16" color="primary"
                                    >mdi-robot-outline</v-icon
                                >
                                <span
                                    class="text-caption font-weight-bold text-uppercase text-grey-darken-1"
                                    >AI Synthesis</span
                                >
                            </div>
                            <v-chip
                                size="x-small"
                                variant="tonal"
                                color="primary"
                                >Full Route</v-chip
                            >
                        </div>
                        <v-card
                            v-if="selectedWalkRoute?.travelogue"
                            class="rounded-lg pa-3"
                            border
                            flat
                        >
                            <p
                                class="text-body-2 text-grey-darken-2 font-italic"
                                style="line-height: 1.7"
                            >
                                {{ traveloguePreview }}
                            </p>
                            <v-btn
                                v-if="
                                    (selectedWalkRoute?.travelogue?.length ??
                                        0) > 320
                                "
                                variant="text"
                                size="x-small"
                                color="primary"
                                class="mt-2 text-none px-0"
                                @click="expandTravelogue = !expandTravelogue"
                            >
                                {{
                                    expandTravelogue
                                        ? "Show less"
                                        : "Show full travelogue"
                                }}
                            </v-btn>
                        </v-card>
                        <v-card
                            v-else
                            class="rounded-lg pa-3 text-center"
                            border
                            flat
                        >
                            <p class="text-body-2 text-medium-emphasis">
                                No travelogue generated yet for this walk.
                            </p>
                        </v-card>
                    </div>

                    <!-- Semantic Equivalence -->
                    <div v-if="selectedWalkEvaluation">
                        <div class="d-flex align-center mb-2" style="gap: 6px">
                            <v-icon size="16" color="blue-grey"
                                >mdi-chart-bar</v-icon
                            >
                            <span
                                class="text-caption font-weight-bold text-uppercase text-grey-darken-1"
                                >Semantic Equivalence</span
                            >
                        </div>
                        <v-card
                            class="rounded-lg pa-3"
                            :color="
                                selectedWalkEvaluation.isEquivalent
                                    ? 'success'
                                    : 'warning'
                            "
                            variant="tonal"
                            flat
                        >
                            <div
                                class="d-flex align-center justify-space-between mb-2"
                            >
                                <div
                                    class="d-flex align-center"
                                    style="gap: 6px"
                                >
                                    <v-icon size="18">
                                        {{
                                            selectedWalkEvaluation.isEquivalent
                                                ? "mdi-check-circle"
                                                : "mdi-alert-circle"
                                        }}
                                    </v-icon>
                                    <span class="text-body-2 font-weight-bold">
                                        {{
                                            selectedWalkEvaluation.isEquivalent
                                                ? "Semantically Equivalent"
                                                : "Not Equivalent"
                                        }}
                                    </span>
                                </div>
                                <span class="text-h6 font-weight-black">
                                    {{
                                        (
                                            selectedWalkEvaluation.bertscoreF1 *
                                            100
                                        ).toFixed(1)
                                    }}%
                                </span>
                            </div>
                            <v-progress-linear
                                :model-value="
                                    selectedWalkEvaluation.bertscoreF1 * 100
                                "
                                :color="
                                    selectedWalkEvaluation.isEquivalent
                                        ? 'success'
                                        : 'warning'
                                "
                                bg-color="rgba(255,255,255,0.4)"
                                rounded
                                height="6"
                                class="mb-2"
                            />
                            <p class="text-caption text-medium-emphasis">
                                BERTScore F1 threshold ≥ 85% for semantic
                                equivalence
                            </p>
                        </v-card>
                    </div>
                </div>
            </v-card>
        </v-bottom-sheet>
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
import { apiService } from "@/api/services";
import type {
    RouteResponse,
    WaypointResponse,
    EvaluationResponse,
} from "@/api/types";
import type { LatLng } from "@/types";

const router = useRouter();
const routeStore = useRouteStore();

// ── Planning / walking state ─────────────────────────────────────────────────

const showFinishDialog = ref(false);
const finalNote = ref("");
const finishing = ref(false);
const showCancelDialog = ref(false);
const cancelling = ref(false);
const canLocate = ref(true);
const map = shallowRef<maplibregl.Map | null>(null);
const directions = shallowRef<any>(null);
const planningMode = ref<"free" | "route" | "history">("free");
const isWalking = ref(false);
const showObservationModal = ref(false);
const { elapsedTime, formattedDuration, startTimer, stopTimer } = useTimer();

const isDestroyed = ref(false);

const startPoint = ref<{ lat: number; lng: number } | null>(null);
const endPoint = ref<{ lat: number; lng: number } | null>(null);
const markers = ref<maplibregl.Marker[]>([]);

const derivePoints = ref(1);
const deviationMeters = ref(500);
const routeCalculated = ref(false);

const currentLocation = ref({ lat: 53.3498, lng: -6.2603 });
const isLocating = ref(false);

// ── History mode state ───────────────────────────────────────────────────────

const historyWalks = ref<RouteResponse[]>([]);
const loadingHistory = ref(false);
const selectedWalkId = ref<string | null>(null);
const selectedWalkRoute = ref<RouteResponse | null>(null);
const selectedWalkWaypoints = ref<WaypointResponse[]>([]);
const selectedWalkEvaluation = ref<EvaluationResponse | null>(null);
const loadingWalk = ref(false);
const historyMarkers = ref<maplibregl.Marker[]>([]);

// Waypoint sheet
const showWaypointSheet = ref(false);
const selectedWaypoint = ref<WaypointResponse | null>(null);
const expandTravelogue = ref(false);

// ── Computed ─────────────────────────────────────────────────────────────────

const traveloguePreview = computed(() => {
    const full = selectedWalkRoute.value?.travelogue ?? "";
    if (expandTravelogue.value || full.length <= 320) return full;
    return full.slice(0, 320) + "…";
});

// ── Lifecycle ────────────────────────────────────────────────────────────────

onMounted(() => {
    if (!navigator.geolocation) canLocate.value = false;

    const elapsedSeconds = routeStore.restoreWalk();
    if (elapsedSeconds !== null) {
        isWalking.value = true;
        startTimer(elapsedSeconds);
    }

    map.value = new maplibregl.Map({
        container: "map-container",
        style: "https://tiles.openfreemap.org/styles/liberty",
        center: [-6.2603, 53.3498],
        zoom: 13,
        attributionControl: false,
    });

    map.value.on("click", handleMapClick);

    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
            (position) => {
                const { latitude, longitude } = position.coords;
                currentLocation.value = { lat: latitude, lng: longitude };
                map.value?.flyTo({ center: [longitude, latitude], zoom: 15 });
            },
            () => {
                /* stay on default centre */
            },
        );
    }

    map.value.on("load", () => {
        if (isDestroyed.value) return;

        directions.value = new MapLibreGlDirections(map.value as any, {
            api: "https://router.project-osrm.org/route/v1",
            profile: "foot",
            requestOptions: { alternatives: "true", overview: "full" },
        });

        directions.value.interactive = true;
    });
});

onUnmounted(() => {
    isDestroyed.value = true;
    stopTimer();
    clearHistoryFromMap();

    if (directions.value) {
        directions.value.interactive = false;
        directions.value.clear();
    }
    if (map.value) map.value.remove();
});

// ── Map helpers ──────────────────────────────────────────────────────────────

function locateMe() {
    navigator.geolocation.getCurrentPosition(
        (position) => {
            const { latitude, longitude } = position.coords;
            map.value?.flyTo({ center: [longitude, latitude], zoom: 15 });
        },
        (error) => {
            console.error(`Error getting location: ${error.message}`);
        },
    );
}

function handleMapClick(e: maplibregl.MapMouseEvent) {
    if (isWalking.value) return;
    if (planningMode.value !== "route") return;
    const { lng, lat } = e.lngLat;
    if (!startPoint.value) {
        startPoint.value = { lat, lng };
        addMarker(lng, lat, "#7C3AED");
    } else if (!endPoint.value) {
        endPoint.value = { lat, lng };
        addMarker(lng, lat, "#EC4899");
    }
}

function useCurrentLocationAsStart() {
    if (startPoint.value) return;
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
        const latDeg = deviationMeters.value / 111000;
        const lngDeg =
            deviationMeters.value /
            (111000 * Math.cos((baseLat * Math.PI) / 180));
        waypoints.push([
            baseLng + (Math.random() - 0.5) * 2 * lngDeg,
            baseLat + (Math.random() - 0.5) * 2 * latDeg,
        ]);
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
    let coords: [number, number][] = [
        [startPoint.value.lng, startPoint.value.lat],
        [endPoint.value.lng, endPoint.value.lat],
    ];
    try {
        if (directions.value?.getWaypoints) {
            const wps = directions.value.getWaypoints();
            if (wps.length >= 2)
                coords = wps.map((wp: any) => wp.geometry.coordinates);
        }
    } catch {
        /* ignore */
    }

    const geojson: GeoJSON.Feature<GeoJSON.LineString> = {
        type: "Feature",
        properties: {},
        geometry: { type: "LineString", coordinates: coords },
    };

    if (map.value.getSource("route")) {
        (map.value.getSource("route") as maplibregl.GeoJSONSource).setData(
            geojson,
        );
    } else {
        map.value.addSource("route", { type: "geojson", data: geojson });
        map.value.addLayer({
            id: "route",
            type: "line",
            source: "route",
            layout: { "line-join": "round", "line-cap": "round" },
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

// ── Mode switching ───────────────────────────────────────────────────────────

function setMode(mode: "free" | "route" | "history") {
    if (mode === "history") {
        resetRoute();
        planningMode.value = mode;
        loadHistory();
    } else {
        backToHistory();
        planningMode.value = mode;
        resetRoute();
    }
}

// ── History mode ─────────────────────────────────────────────────────────────

async function loadHistory() {
    loadingHistory.value = true;
    try {
        historyWalks.value = await apiService.listRoutes();
    } catch (e) {
        console.warn("Failed to load walk history:", e);
        historyWalks.value = [];
    }
    loadingHistory.value = false;
}

async function selectWalk(walkId: string) {
    loadingWalk.value = true;
    selectedWalkId.value = walkId;
    selectedWalkRoute.value = null;
    selectedWalkWaypoints.value = [];
    selectedWalkEvaluation.value = null;
    clearHistoryFromMap();

    try {
        [selectedWalkRoute.value, selectedWalkWaypoints.value] =
            await Promise.all([
                apiService.getRoute(walkId),
                apiService.getWaypoints(walkId),
            ]);
    } catch (e) {
        console.warn("Failed to load walk:", e);
    }

    try {
        selectedWalkEvaluation.value = await apiService.getEvaluation(walkId);
    } catch {
        selectedWalkEvaluation.value = null; // No evaluation yet — expected
    }

    loadingWalk.value = false;
    renderWalkOnMap();
}

function backToHistory() {
    selectedWalkId.value = null;
    selectedWalkRoute.value = null;
    selectedWalkWaypoints.value = [];
    selectedWalkEvaluation.value = null;
    clearHistoryFromMap();
}

function clearHistoryFromMap() {
    historyMarkers.value.forEach((m) => m.remove());
    historyMarkers.value = [];
    if (map.value?.getLayer("history-route"))
        map.value.removeLayer("history-route");
    if (map.value?.getSource("history-route"))
        map.value.removeSource("history-route");
}

function renderWalkOnMap() {
    const route = selectedWalkRoute.value;
    const wps = selectedWalkWaypoints.value;
    if (!route || !map.value) return;

    // allCoords includes the end marker position and is used only for fitBounds.
    const allCoords: [number, number][] = [];
    // routingPoints = start + sorted waypoints — the spine fed to OSRM.
    const routingPoints: [number, number][] = [];

    // Start marker
    if (route.startLat != null && route.startLon != null) {
        const c: [number, number] = [route.startLon, route.startLat];
        routingPoints.push(c);
        allCoords.push(c);
        const startEl = makeEndpointMarkerEl("#7C3AED", "mdi-flag-variant");
        const m = new maplibregl.Marker({ element: startEl })
            .setLngLat([route.startLon, route.startLat])
            .addTo(map.value);
        historyMarkers.value.push(m);
    }

    // Waypoint markers (sorted by stored_at)
    const sorted = [...wps].sort(
        (a, b) =>
            new Date(a.storedAt).getTime() - new Date(b.storedAt).getTime(),
    );
    sorted.forEach((wp) => {
        const c: [number, number] = [wp.longitude, wp.latitude];
        routingPoints.push(c);
        allCoords.push(c);
        const el = makeWaypointMarkerEl(!!wp.textNote);
        el.addEventListener("click", (e) => {
            e.stopPropagation();
            openWaypointSheet(wp);
        });
        const m = new maplibregl.Marker({ element: el })
            .setLngLat([wp.longitude, wp.latitude])
            .addTo(map.value!);
        historyMarkers.value.push(m);
    });

    // End marker — pin only, not part of the routed line
    if (
        route.endLat != null &&
        route.endLon != null &&
        !(Math.abs(route.endLat - route.startLat) < 0.00001 &&
          Math.abs(route.endLon - route.startLon) < 0.00001)
    ) {
        allCoords.push([route.endLon, route.endLat]);
        const endEl = makeEndpointMarkerEl("#EC4899", "mdi-flag-checkered");
        const m = new maplibregl.Marker({ element: endEl })
            .setLngLat([route.endLon, route.endLat])
            .addTo(map.value);
        historyMarkers.value.push(m);
    }

    // Straight lines between consecutive waypoints — the most faithful
    // representation possible without a continuous GPS track log.
    const lineCoords = routingPoints;

    if (lineCoords.length >= 2 && map.value.isStyleLoaded()) {
        map.value.addSource("history-route", {
            type: "geojson",
            data: {
                type: "Feature",
                properties: {},
                geometry: { type: "LineString", coordinates: lineCoords },
            },
        });
        map.value.addLayer({
            id: "history-route",
            type: "line",
            source: "history-route",
            layout: { "line-join": "round", "line-cap": "round" },
            paint: {
                "line-color": "#7C3AED",
                "line-width": 3,
                "line-opacity": 0.8,
            },
        });
    }

    // Fit map to show the whole route (includes end marker position)
    if (allCoords.length > 0) {
        const bounds = allCoords.reduce(
            (b, c) => b.extend(c as maplibregl.LngLatLike),
            new maplibregl.LngLatBounds(allCoords[0], allCoords[0]),
        );
        map.value.fitBounds(bounds, { padding: 80, maxZoom: 16 });
    }
}

/** Circular marker for start / end pins */
function makeEndpointMarkerEl(color: string, _icon: string): HTMLElement {
    const el = document.createElement("div");
    el.style.cssText = `
        width: 28px; height: 28px; border-radius: 50%;
        background: ${color}; border: 3px solid white;
        box-shadow: 0 2px 8px rgba(0,0,0,0.35);
        display: flex; align-items: center; justify-content: center;
    `;
    // Simple inner dot
    const dot = document.createElement("div");
    dot.style.cssText =
        "width: 8px; height: 8px; border-radius: 50%; background: white;";
    el.appendChild(dot);
    return el;
}

/** Interactive marker for logged waypoints */
function makeWaypointMarkerEl(hasNote: boolean): HTMLElement {
    // Outer element is left unstyled so MapLibre can apply its positioning
    // transform to it freely. Applying transform to the outer element directly
    // would overwrite MapLibre's translate and snap the marker to the top-left.
    const el = document.createElement("div");

    const inner = document.createElement("div");
    inner.style.cssText = `
        width: 34px; height: 34px; border-radius: 50%;
        background: ${hasNote ? "#10B981" : "#94A3B8"};
        border: 3px solid white;
        box-shadow: 0 2px 8px rgba(0,0,0,0.3);
        cursor: pointer;
        display: flex; align-items: center; justify-content: center;
        transition: transform 0.15s ease;
    `;
    inner.onmouseenter = () => { inner.style.transform = "scale(1.2)"; };
    inner.onmouseleave = () => { inner.style.transform = ""; };

    inner.innerHTML = `
        <svg width="16" height="16" viewBox="0 0 24 24" fill="white">
            <path d="M20.71,7.04C21.1,6.65 21.1,6 20.71,5.63L18.37,3.29C18,2.9 17.35,2.9 16.96,3.29L15.12,5.12L18.87,8.87M3,17.25V21H6.75L17.81,9.93L14.06,6.18L3,17.25Z"/>
        </svg>
    `;
    el.appendChild(inner);
    return el;
}

function openWaypointSheet(wp: WaypointResponse) {
    selectedWaypoint.value = wp;
    expandTravelogue.value = false;
    showWaypointSheet.value = true;
}

// ── Walk actions ─────────────────────────────────────────────────────────────

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
}

async function discardWalk() {
    cancelling.value = true;
    await routeStore.cancelRoute();
    cancelling.value = false;
    showCancelDialog.value = false;
    isWalking.value = false;
    stopTimer();
    router.push("/");
}

async function confirmEndWalk(withNote: boolean) {
    finishing.value = true;
    if (withNote && finalNote.value.trim()) {
        await routeStore.submitObservation({
            latitude: currentLocation.value.lat,
            longitude: currentLocation.value.lng,
            type: "note",
            content: finalNote.value.trim(),
        });
    }
    showFinishDialog.value = false;
    finalNote.value = "";
    finishing.value = false;
    await endWalk();
}

async function endWalk() {
    isWalking.value = false;
    stopTimer();
    setTimeout(async () => {
        await routeStore.finaliseRoute();
        router.push("/journal");
    }, 500);
}

function captureLocationAndAddNote() {
    if (!navigator.geolocation) {
        showObservationModal.value = true;
        return;
    }
    isLocating.value = true;
    navigator.geolocation.getCurrentPosition(
        (position) => {
            currentLocation.value = {
                lat: position.coords.latitude,
                lng: position.coords.longitude,
            };
            isLocating.value = false;
            showObservationModal.value = true;
        },
        () => {
            isLocating.value = false;
            showObservationModal.value = true;
        },
        { enableHighAccuracy: true, timeout: 8000, maximumAge: 30000 },
    );
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
    addMarker(currentLocation.value.lng, currentLocation.value.lat, "#10B981");
}

// ── Formatting helpers ───────────────────────────────────────────────────────

function parseNoteText(raw: string | null | undefined): string {
    if (!raw) return "";
    try {
        const parsed = JSON.parse(raw);
        return (parsed.text || parsed.content || raw).trim();
    } catch {
        return raw.trim();
    }
}

function formatWalkDate(dateStr: string): string {
    return new Date(dateStr).toLocaleDateString("en-IE", {
        day: "numeric",
        month: "short",
        year: "numeric",
    });
}

function formatWaypointTime(dateStr: string | undefined): string {
    if (!dateStr) return "";
    return new Date(dateStr).toLocaleTimeString("en-IE", {
        hour: "2-digit",
        minute: "2-digit",
    });
}
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
