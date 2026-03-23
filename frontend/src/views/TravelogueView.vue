<template>
    <v-container fluid class="fill-height align-start bg-grey-lighten-5 pa-0">
        <!-- Toolbar -->
        <v-toolbar flat color="transparent" class="px-2">
            <v-btn icon @click="router.push('/journal')">
                <v-icon>mdi-arrow-left</v-icon>
            </v-btn>
            <v-toolbar-title
                class="font-serif font-weight-bold text-grey-darken-4"
            >
                {{ route?.name || "Journey" }}
            </v-toolbar-title>
        </v-toolbar>

        <div class="pa-4 w-100">
            <!-- Loading -->
            <div v-if="loading" class="d-flex justify-center py-12">
                <v-progress-circular indeterminate color="primary" />
            </div>

            <template v-else-if="route">
                <p class="text-caption text-medium-emphasis mb-6">
                    {{ formatDate(route.createdAt) }}
                </p>

                <!-- Human Travelogue waypoints timeline -->
                <div class="mb-6">
                    <h2
                        class="text-subtitle-1 font-weight-bold text-grey-darken-3 d-flex align-center mb-3"
                        style="gap: 8px"
                    >
                        <v-icon size="18" color="secondary"
                            >mdi-pencil-outline</v-icon
                        >
                        Your Journey Notes
                        <v-chip
                            size="x-small"
                            variant="tonal"
                            color="secondary"
                        >
                            {{ noteWaypoints.length }} notes
                        </v-chip>
                    </h2>

                    <div v-if="noteWaypoints.length > 0">
                        <div
                            v-for="(wp, i) in noteWaypoints"
                            :key="wp.id"
                            class="d-flex mb-3"
                        >
                            <!-- Timeline spine -->
                            <div
                                class="d-flex flex-column align-center mr-3"
                                style="width: 32px; flex-shrink: 0"
                            >
                                <div
                                    class="rounded-circle d-flex align-center justify-center"
                                    style="
                                        width: 28px;
                                        height: 28px;
                                        background: rgba(
                                            var(--v-theme-secondary),
                                            0.15
                                        );
                                    "
                                >
                                    <v-icon size="14" color="secondary"
                                        >mdi-map-marker</v-icon
                                    >
                                </div>
                                <div
                                    v-if="i < noteWaypoints.length - 1"
                                    class="bg-grey-lighten-3 mt-1"
                                    style="
                                        width: 2px;
                                        flex: 1;
                                        min-height: 12px;
                                    "
                                />
                            </div>

                            <div class="flex-1 pb-2">
                                <p
                                    class="text-caption text-medium-emphasis mb-1"
                                >
                                    {{ formatTime(wp.storedAt) }}
                                </p>
                                <v-card class="rounded-lg pa-3" border flat>
                                    <p
                                        class="text-body-2 text-grey-darken-2"
                                        style="line-height: 1.6"
                                    >
                                        {{ parseNoteText(wp.textNote) }}
                                    </p>
                                </v-card>
                            </div>
                        </div>
                    </div>

                    <v-card
                        v-else
                        class="rounded-xl pa-4 text-center"
                        border
                        flat
                    >
                        <p class="text-body-2 text-medium-emphasis">
                            No notes were recorded on this journey.
                        </p>
                    </v-card>
                </div>

                <!-- AI Travelogue -->
                <div class="mb-6">
                    <div class="d-flex align-center justify-space-between mb-3">
                        <h2
                            class="text-subtitle-1 font-weight-bold text-grey-darken-3 d-flex align-center"
                            style="gap: 8px"
                        >
                            <v-icon size="18" color="primary"
                                >mdi-robot-outline</v-icon
                            >
                            AI Travelogue
                        </h2>
                        <v-btn
                            size="x-small"
                            variant="text"
                            :color="showConfig ? 'primary' : 'grey'"
                            @click="showConfig = !showConfig"
                        >
                            <v-icon size="18">mdi-tune</v-icon>
                        </v-btn>
                    </div>

                    <!-- Generation config panel -->
                    <v-expand-transition>
                        <v-card v-if="showConfig" class="rounded-xl pa-4 mb-3" border flat>
                            <p class="text-caption text-uppercase font-weight-bold text-grey-darken-1 mb-3">
                                Generation Settings
                            </p>
                            <v-combobox
                                v-model="configModel"
                                :items="availableModels"
                                label="AI Model"
                                variant="outlined"
                                density="compact"
                                hide-details
                                class="mb-3"
                                placeholder="e.g. llama3.1:8b"
                            />
                            <v-select
                                v-model="configPromptType"
                                :items="promptTypeOptions"
                                item-title="label"
                                item-value="value"
                                label="Prompt Type"
                                variant="outlined"
                                density="compact"
                                hide-details
                                class="mb-3"
                            />
                            <p v-if="configPromptType === 'few_shot'" class="text-caption text-medium-emphasis">
                                Few Shot includes a human-written journal from another completed journey as a style example in the prompt.
                            </p>
                            <v-btn
                                block
                                color="primary"
                                variant="flat"
                                class="mt-3 rounded-lg"
                                :loading="generating"
                                @click="generateNew"
                            >
                                <v-icon start>mdi-creation</v-icon>
                                Generate
                            </v-btn>
                        </v-card>
                    </v-expand-transition>

                    <v-btn
                        v-if="!showConfig"
                        size="x-small"
                        variant="tonal"
                        color="primary"
                        class="mb-3"
                        :loading="generating"
                        @click="generateNew"
                    >
                        <v-icon start size="14">mdi-creation</v-icon>
                        Generate New
                    </v-btn>

                    <!-- Version dropdown -->
                    <v-select
                        v-if="travelogues.length > 0"
                        :model-value="selectedTravelogue"
                        :items="travelogues"
                        :item-title="(t) => `${t.llmModel} — ${formatDate(t.createdAt)}`"
                        item-value="id"
                        return-object
                        label="Generation"
                        variant="outlined"
                        density="compact"
                        class="mb-3"
                        hide-details
                        @update:model-value="selectedTravelogue = $event"
                    >
                        <template #item="{ item, props }">
                            <v-list-item v-bind="props" :title="undefined">
                                <template #title>
                                    <span class="text-body-2 font-weight-medium">{{ item.raw.llmModel }}</span>
                                    <v-chip size="x-small" variant="tonal" color="primary" class="ml-2">
                                        {{ item.raw.promptType === 'few_shot' ? 'Few Shot' : 'Zero Shot' }}
                                    </v-chip>
                                </template>
                                <template #subtitle>
                                    <span class="text-caption text-medium-emphasis">{{ formatDate(item.raw.createdAt) }}</span>
                                    <template v-if="item.raw.evaluation">
                                        <v-chip
                                            size="x-small"
                                            :color="item.raw.evaluation.isEquivalent ? 'success' : 'warning'"
                                            variant="tonal"
                                            class="ml-2"
                                        >F1 {{ (item.raw.evaluation.bertscoreF1 * 100).toFixed(1) }}%</v-chip>
                                        <v-chip
                                            size="x-small"
                                            :color="item.raw.evaluation.aiSentiment >= 0.05 ? 'success' : item.raw.evaluation.aiSentiment <= -0.05 ? 'error' : 'grey'"
                                            variant="tonal"
                                            class="ml-1"
                                        >{{ item.raw.evaluation.aiSentiment >= 0.05 ? 'Positive' : item.raw.evaluation.aiSentiment <= -0.05 ? 'Negative' : 'Neutral' }}</v-chip>
                                    </template>
                                </template>
                            </v-list-item>
                        </template>
                        <template #selection="{ item }">
                            <span class="text-body-2">{{ item.raw.llmModel }} — {{ formatDate(item.raw.createdAt) }}</span>
                            <v-chip size="x-small" variant="tonal" color="primary" class="ml-2">
                                {{ item.raw.promptType === 'few_shot' ? 'Few Shot' : 'Zero Shot' }}
                            </v-chip>
                            <template v-if="item.raw.evaluation">
                                <v-chip
                                    size="x-small"
                                    :color="item.raw.evaluation.isEquivalent ? 'success' : 'warning'"
                                    variant="tonal"
                                    class="ml-2"
                                >F1 {{ (item.raw.evaluation.bertscoreF1 * 100).toFixed(1) }}%</v-chip>
                                <v-chip
                                    size="x-small"
                                    :color="item.raw.evaluation.aiSentiment >= 0.05 ? 'success' : item.raw.evaluation.aiSentiment <= -0.05 ? 'error' : 'grey'"
                                    variant="tonal"
                                    class="ml-1"
                                >{{ item.raw.evaluation.aiSentiment >= 0.05 ? 'Positive' : item.raw.evaluation.aiSentiment <= -0.05 ? 'Negative' : 'Neutral' }}</v-chip>
                            </template>
                        </template>
                    </v-select>

                    <!-- Selected travelogue text -->
                    <v-card
                        v-if="selectedTravelogue"
                        class="rounded-xl pa-5"
                        border
                        flat
                    >
                        <p
                            v-for="(para, i) in selectedTravelogueParagraphs"
                            :key="i"
                            class="text-body-2 text-grey-darken-2 mb-3 font-italic"
                            style="line-height: 1.7"
                        >
                            {{ para }}
                        </p>
                    </v-card>

                    <!-- Legacy travelogue (no Travelogue nodes yet) -->
                    <v-card
                        v-else-if="route.travelogue"
                        class="rounded-xl pa-5"
                        border
                        flat
                    >
                        <v-chip size="x-small" variant="tonal" color="grey" class="mb-3">Legacy</v-chip>
                        <p
                            v-for="(para, i) in legacyParagraphs"
                            :key="i"
                            class="text-body-2 text-grey-darken-2 mb-3 font-italic"
                            style="line-height: 1.7"
                        >
                            {{ para }}
                        </p>
                        <p class="text-caption text-medium-emphasis mt-2">
                            Generate a new travelogue to enable per-generation tracking.
                        </p>
                    </v-card>

                    <v-card
                        v-else
                        class="rounded-xl pa-5 text-center"
                        border
                        flat
                    >
                        <v-icon size="40" color="grey-lighten-1" class="mb-3"
                            >mdi-text-box-outline</v-icon
                        >
                        <p class="text-body-2 text-medium-emphasis">
                            No travelogue has been generated yet for this journey.
                        </p>
                    </v-card>
                </div>

                <!-- Actions -->
                <template v-if="selectedTravelogue">
                    <v-btn
                        block
                        color="primary"
                        :variant="hasEvaluation ? 'tonal' : 'flat'"
                        height="52"
                        class="rounded-xl font-weight-bold mb-3"
                        :loading="evaluating"
                        :disabled="noteWaypoints.length === 0"
                        @click="runEvaluation"
                    >
                        <v-icon start>{{ hasEvaluation ? 'mdi-refresh' : 'mdi-chart-bar' }}</v-icon>
                        {{ hasEvaluation ? 'Re-evaluate' : 'Compare Travelogues' }}
                    </v-btn>
                    <v-btn
                        block
                        variant="outlined"
                        color="primary"
                        height="44"
                        class="rounded-xl font-weight-bold"
                        @click="viewEvaluation"
                    >
                        View Evaluation
                    </v-btn>
                </template>

                <!-- Legacy evaluation link (route-level eval, no Travelogue nodes) -->
                <template v-else-if="route.travelogue">
                    <v-btn
                        block
                        variant="outlined"
                        color="primary"
                        height="44"
                        class="rounded-xl font-weight-bold"
                        @click="router.push(`/journal/${routeId}/evaluation`)"
                    >
                        View Evaluation
                    </v-btn>
                </template>
            </template>

            <div v-else class="text-center py-12">
                <v-icon size="64" color="grey-lighten-2" class="mb-4"
                    >mdi-alert-circle-outline</v-icon
                >
                <p class="text-body-2 text-medium-emphasis">
                    Journey not found.
                </p>
            </div>
        </div>

        <v-snackbar v-model="errorSnack" color="error" :timeout="4000">
            {{ errorMessage }}
        </v-snackbar>
    </v-container>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useRouter, useRoute } from "vue-router";
import { apiService } from "@/api/services";
import type { RouteResponse, WaypointResponse, TravelogueResponse } from "@/api/types";

const router = useRouter();
const vueRoute = useRoute();
const routeId = vueRoute.params.id as string;

const route = ref<RouteResponse | null>(null);
const waypoints = ref<WaypointResponse[]>([]);
const travelogues = ref<TravelogueResponse[]>([]);
const selectedTravelogue = ref<TravelogueResponse | null>(null);
const loading = ref(true);
const generating = ref(false);
const evaluating = ref(false);
const errorSnack = ref(false);
const errorMessage = ref("");

// Generation config
const showConfig = ref(false);
const configModel = ref<string>("");
const configPromptType = ref("zero_shot");
const availableModels = ref<string[]>([]);
const promptTypeOptions = [
    { label: "Zero Shot", value: "zero_shot" },
    { label: "Few Shot", value: "few_shot" },
];

const hasEvaluation = computed(() => !!selectedTravelogue.value?.evaluation);

const noteWaypoints = computed(() =>
    waypoints.value.filter((wp) => {
        if (!wp.textNote) return false;
        return parseNoteText(wp.textNote).trim().length > 0;
    }),
);

const selectedTravelogueParagraphs = computed(() =>
    (selectedTravelogue.value?.text ?? "").split("\n").filter((p) => p.trim()),
);

const legacyParagraphs = computed(() =>
    (route.value?.travelogue ?? "").split("\n").filter((p) => p.trim()),
);

function parseNoteText(raw: string | null | undefined): string {
    if (!raw) return "";
    try {
        const parsed = JSON.parse(raw);
        return (parsed.text || parsed.content || raw).trim();
    } catch {
        return raw.trim();
    }
}

function formatDate(dateStr: string) {
    return new Date(dateStr).toLocaleDateString("en-US", {
        weekday: "long",
        year: "numeric",
        month: "long",
        day: "numeric",
    });
}

function formatShortDate(dateStr: string) {
    return new Date(dateStr).toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
    });
}

function formatTime(dateStr: string) {
    return new Date(dateStr).toLocaleTimeString("en-US", {
        hour: "2-digit",
        minute: "2-digit",
    });
}

async function generateNew() {
    generating.value = true;
    showConfig.value = false;
    try {
        const newTravelogue = await apiService.generateTravelogue(routeId, {
            llmModel: configModel.value || undefined,
            promptType: configPromptType.value,
        });
        travelogues.value.unshift(newTravelogue);
        selectedTravelogue.value = newTravelogue;
    } catch {
        errorMessage.value =
            "Failed to generate travelogue. Is Ollama running?";
        errorSnack.value = true;
    } finally {
        generating.value = false;
    }
}

async function runEvaluation() {
    if (!selectedTravelogue.value) return;
    evaluating.value = true;
    try {
        const evaluation = await apiService.evaluateRoute(routeId, selectedTravelogue.value.id);
        selectedTravelogue.value = { ...selectedTravelogue.value, evaluation };
        // Update in list too
        const idx = travelogues.value.findIndex((t) => t.id === selectedTravelogue.value!.id);
        if (idx !== -1) travelogues.value[idx] = selectedTravelogue.value;
        viewEvaluation();
    } catch (e: any) {
        errorMessage.value =
            e?.response?.data?.detail ?? "Evaluation failed. Please try again.";
        errorSnack.value = true;
    } finally {
        evaluating.value = false;
    }
}

function viewEvaluation() {
    if (!selectedTravelogue.value) return;
    router.push(`/journal/${routeId}/evaluation?travelogueId=${selectedTravelogue.value.id}`);
}

onMounted(async () => {
    try {
        const [routeData, waypointData, travelogueData, modelsData] = await Promise.all([
            apiService.getRoute(routeId),
            apiService.getWaypoints(routeId),
            apiService.getTravelogues(routeId),
            apiService.getModels().catch(() => ({ models: [], default: "" })),
        ]);
        route.value = routeData;
        waypoints.value = waypointData;
        travelogues.value = travelogueData;
        availableModels.value = modelsData.models;
        configModel.value = modelsData.default;
        if (travelogues.value.length > 0) {
            selectedTravelogue.value = travelogues.value[0];
        }
    } catch {
        route.value = null;
    }

    loading.value = false;
});
</script>
