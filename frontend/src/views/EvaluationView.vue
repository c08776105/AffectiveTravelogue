<template>
    <v-container fluid class="fill-height align-start bg-grey-lighten-5 pa-0">
        <!-- Toolbar -->
        <v-toolbar flat color="transparent" class="px-2">
            <v-btn icon @click="router.push(`/journal/${routeId}`)">
                <v-icon>mdi-arrow-left</v-icon>
            </v-btn>
            <v-toolbar-title class="font-serif font-weight-bold text-grey-darken-4">
                Evaluation Results
            </v-toolbar-title>
        </v-toolbar>

        <div class="pa-4 w-100">
            <!-- Loading -->
            <div v-if="loading" class="d-flex justify-center py-12">
                <v-progress-circular indeterminate color="primary" />
            </div>

            <template v-else-if="evaluation">
                <!-- Equivalence verdict -->
                <v-card
                    class="rounded-xl pa-5 mb-5 text-center"
                    :color="evaluation.isEquivalent ? 'success' : 'warning'"
                    variant="tonal"
                    flat
                >
                    <v-icon size="36" class="mb-2">
                        {{ evaluation.isEquivalent ? 'mdi-check-circle' : 'mdi-alert-circle' }}
                    </v-icon>
                    <p class="text-h6 font-weight-bold mb-1">
                        {{ evaluation.isEquivalent ? 'Semantically Equivalent' : 'Not Equivalent' }}
                    </p>
                    <p class="text-body-2 text-medium-emphasis">
                        {{ evaluation.isEquivalent
                            ? 'Your journal and the AI travelogue convey similar meaning.'
                            : 'Your journal and the AI travelogue diverge significantly.'
                        }}
                    </p>
                </v-card>

                <!-- BERTScore Metrics -->
                <h2 class="text-subtitle-1 font-weight-bold text-grey-darken-3 mb-3">
                    Semantic Similarity (BERTScore)
                </h2>

                <!-- Per-waypoint breakdown -->
                <v-card v-if="waypointScores.length > 0" class="rounded-xl pa-5 mb-3" border flat>
                    <p class="text-caption text-uppercase font-weight-bold text-grey-darken-1 mb-3">
                        Per-Waypoint Scores
                    </p>
                    <div v-for="(wp, i) in waypointScores" :key="i" class="mb-4">
                        <div class="d-flex justify-space-between align-center mb-1">
                            <span class="text-caption font-weight-bold text-grey-darken-2 d-flex align-center" style="gap:6px">
                                Waypoint {{ i + 1 }}
                                <v-chip v-if="wp.isTruncated" size="x-small" color="warning" variant="tonal">truncated</v-chip>
                            </span>
                            <span class="text-caption font-weight-bold" :class="scoreColor(wp.f1)">
                                F1 {{ (wp.f1 * 100).toFixed(1) }}%
                            </span>
                        </div>
                        <v-progress-linear
                            :model-value="wp.f1 * 100"
                            :color="scoreColor(wp.f1)"
                            bg-color="grey-lighten-3"
                            rounded
                            height="6"
                            class="mb-1"
                        />
                        <div class="d-flex justify-end" style="gap: 12px">
                            <span class="text-caption text-medium-emphasis">P {{ (wp.precision * 100).toFixed(1) }}%</span>
                            <span class="text-caption text-medium-emphasis">R {{ (wp.recall * 100).toFixed(1) }}%</span>
                        </div>
                    </div>
                </v-card>

                <!-- Macro averages -->
                <v-card class="rounded-xl pa-5 mb-5" border flat>
                    <p class="text-caption text-uppercase font-weight-bold text-grey-darken-1 mb-3">
                        {{ waypointScores.length > 1 ? 'Macro Average' : 'Overall' }}
                    </p>
                    <div v-for="metric in bertMetrics" :key="metric.label" class="mb-4">
                        <div class="d-flex justify-space-between align-center mb-1">
                            <span class="text-caption font-weight-bold text-grey-darken-2">
                                {{ metric.label }}
                            </span>
                            <span class="text-caption font-weight-bold" :class="scoreColor(metric.value)">
                                {{ (metric.value * 100).toFixed(1) }}%
                            </span>
                        </div>
                        <v-progress-linear
                            :model-value="metric.value * 100"
                            :color="scoreColor(metric.value)"
                            bg-color="grey-lighten-3"
                            rounded
                            height="8"
                        />
                    </div>
                    <p class="text-caption text-medium-emphasis mt-2">
                        Threshold for equivalence: F1 ≥ 85%
                        <span v-if="waypointScores.length > 1"> · macro-averaged over {{ waypointScores.length }} waypoints</span>
                    </p>
                    <p v-if="evaluation.bertscoreModel" class="text-caption text-medium-emphasis mt-1">
                        BERTScore model: {{ evaluation.bertscoreModel }}
                    </p>
                    <p v-if="evaluation.promptType" class="text-caption text-medium-emphasis mt-1">
                        Prompt type: {{ evaluation.promptType === 'few_shot' ? 'Few Shot' : 'Zero Shot' }}
                    </p>
                    <v-alert
                        v-if="evaluation.isTruncated"
                        type="warning"
                        variant="tonal"
                        density="compact"
                        class="mt-3 text-caption"
                        icon="mdi-alert-outline"
                    >
                        One or more waypoints exceeded the 512-token limit and were truncated before scoring. Results may not reflect the full content.
                    </v-alert>
                </v-card>

                <!-- Sentiment Comparison -->
                <h2 class="text-subtitle-1 font-weight-bold text-grey-darken-3 mb-3">
                    Sentiment Comparison
                </h2>
                <v-card class="rounded-xl pa-5 mb-5" border flat>
                    <v-row no-gutters>
                        <v-col cols="6" class="pr-3">
                            <div class="text-caption text-uppercase font-weight-bold text-grey-darken-1 mb-2">
                                Your Journal
                            </div>
                            <div class="text-h5 font-weight-bold mb-1" :class="sentimentColor(evaluation.humanSentiment)">
                                {{ sentimentLabel(evaluation.humanSentiment) }}
                            </div>
                            <div class="text-caption text-medium-emphasis">
                                Score: {{ evaluation.humanSentiment.toFixed(3) }}
                            </div>
                        </v-col>
                        <v-divider vertical class="mx-2" />
                        <v-col cols="6" class="pl-3">
                            <div class="text-caption text-uppercase font-weight-bold text-grey-darken-1 mb-2">
                                AI Travelogue
                            </div>
                            <div class="text-h5 font-weight-bold mb-1" :class="sentimentColor(evaluation.aiSentiment)">
                                {{ sentimentLabel(evaluation.aiSentiment) }}
                            </div>
                            <div class="text-caption text-medium-emphasis">
                                Score: {{ evaluation.aiSentiment.toFixed(3) }}
                            </div>
                        </v-col>
                    </v-row>
                    <p class="text-caption text-medium-emphasis mt-4">
                        VADER compound score: −1 (most negative) → +1 (most positive)
                    </p>
                </v-card>

                <!-- Travelogues side by side -->
                <h2 class="text-subtitle-1 font-weight-bold text-grey-darken-3 mb-3">
                    Travelogue Comparison
                </h2>

                <!-- Human journal -->
                <div class="mb-4">
                    <div class="text-caption text-uppercase font-weight-bold text-grey-darken-1 mb-2 d-flex align-center" style="gap:6px">
                        <v-icon size="14" color="secondary">mdi-pencil-outline</v-icon>
                        Your Journey Notes
                    </div>
                    <v-card class="rounded-xl pa-4" border flat>
                        <p
                            v-if="!humanExpanded"
                            class="text-body-2 text-grey-darken-2"
                            style="white-space: pre-wrap; line-height: 1.7"
                        >{{ humanExcerpt }}</p>
                        <p
                            v-else
                            class="text-body-2 text-grey-darken-2"
                            style="white-space: pre-wrap; line-height: 1.7"
                        >{{ evaluation.humanJournal }}</p>
                        <v-btn
                            v-if="humanJournalLong"
                            variant="text"
                            size="x-small"
                            class="mt-2 text-none"
                            color="primary"
                            @click="humanExpanded = !humanExpanded"
                        >{{ humanExpanded ? 'Show less' : 'Read more' }}</v-btn>
                    </v-card>
                </div>

                <!-- AI travelogue -->
                <div class="mb-4">
                    <div class="text-caption text-uppercase font-weight-bold text-grey-darken-1 mb-2 d-flex align-center" style="gap:6px">
                        <v-icon size="14" color="primary">mdi-robot-outline</v-icon>
                        AI Travelogue
                    </div>
                    <v-card class="rounded-xl pa-4" border flat>
                        <p
                            v-if="!aiExpanded"
                            class="text-body-2 text-grey-darken-2 font-italic"
                            style="white-space: pre-wrap; line-height: 1.7"
                        >{{ aiExcerpt }}</p>
                        <p
                            v-else
                            class="text-body-2 text-grey-darken-2 font-italic"
                            style="white-space: pre-wrap; line-height: 1.7"
                        >{{ evaluation.aiTravelogue }}</p>
                        <v-btn
                            v-if="aiTravelogueLong"
                            variant="text"
                            size="x-small"
                            class="mt-2 text-none"
                            color="primary"
                            @click="aiExpanded = !aiExpanded"
                        >{{ aiExpanded ? 'Show less' : 'Read more' }}</v-btn>
                    </v-card>
                </div>

                <p class="text-caption text-medium-emphasis mb-2">
                    Evaluated on {{ formatDate(evaluation.createdAt) }}
                </p>
            </template>

            <!-- No evaluation -->
            <div v-else class="text-center py-12">
                <v-icon size="64" color="grey-lighten-2" class="mb-4">mdi-chart-bar</v-icon>
                <p class="text-body-1 font-weight-bold text-grey-darken-3 mb-2">No evaluation yet</p>
                <p class="text-body-2 text-medium-emphasis mb-6">
                    Write your journal entry and run a comparison first.
                </p>
                <v-btn color="primary" variant="tonal" @click="router.push(`/journal/${routeId}`)">
                    Go to Travelogue
                </v-btn>
            </div>
        </div>
    </v-container>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { apiService } from '@/api/services'
import type { EvaluationResponse } from '@/api/types'

const router = useRouter()
const vueRoute = useRoute()
const routeId = vueRoute.params.id as string
const travelogueId = vueRoute.query.travelogueId as string | undefined

const evaluation = ref<EvaluationResponse | null>(null)
const loading = ref(true)
const humanExpanded = ref(false)
const aiExpanded = ref(false)

const EXCERPT_LEN = 400

const humanExcerpt = computed(() => {
    const text = evaluation.value?.humanJournal ?? ''
    return text.length > EXCERPT_LEN ? text.slice(0, EXCERPT_LEN).trimEnd() + '…' : text
})
const humanJournalLong = computed(() => (evaluation.value?.humanJournal?.length ?? 0) > EXCERPT_LEN)

const aiExcerpt = computed(() => {
    const text = evaluation.value?.aiTravelogue ?? ''
    return text.length > EXCERPT_LEN ? text.slice(0, EXCERPT_LEN).trimEnd() + '…' : text
})
const aiTravelogueLong = computed(() => (evaluation.value?.aiTravelogue?.length ?? 0) > EXCERPT_LEN)

const bertMetrics = computed(() => [
    { label: 'F1 Score', value: evaluation.value?.bertscoreF1 ?? 0 },
    { label: 'Precision', value: evaluation.value?.bertscorePrecision ?? 0 },
    { label: 'Recall', value: evaluation.value?.bertscoreRecall ?? 0 },
])

const waypointScores = computed(() => {
    const f1s  = evaluation.value?.pairF1 ?? []
    const prec = evaluation.value?.pairPrecision ?? []
    const rec  = evaluation.value?.pairRecall ?? []
    const trunc = evaluation.value?.pairIsTruncated ?? []
    return f1s.map((f1, i) => ({
        f1,
        precision: prec[i] ?? 0,
        recall: rec[i] ?? 0,
        isTruncated: trunc[i] ?? false,
    }))
})

function scoreColor(value: number): string {
    if (value >= 0.85) return 'success'
    if (value >= 0.70) return 'warning'
    return 'error'
}

function sentimentLabel(score: number): string {
    if (score >= 0.05) return 'Positive'
    if (score <= -0.05) return 'Negative'
    return 'Neutral'
}

function sentimentColor(score: number): string {
    if (score >= 0.05) return 'text-success'
    if (score <= -0.05) return 'text-error'
    return 'text-grey-darken-2'
}

function formatDate(dateStr: string) {
    return new Date(dateStr).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
    })
}

onMounted(async () => {
    try {
        evaluation.value = await apiService.getEvaluation(routeId, travelogueId)
    } catch {
        evaluation.value = null
    }
    loading.value = false
})
</script>

<style scoped>
.gap-2 {
    gap: 8px;
}
</style>
