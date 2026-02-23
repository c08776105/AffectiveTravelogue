<template>
  <v-container fluid class="fill-height align-start bg-white pa-6">
    <v-row>
      <v-col cols="12">
        <h1 class="text-h4 font-serif font-weight-bold text-grey-darken-4 mb-2">Your Journal</h1>
        <p class="text-body-2 text-medium-emphasis mb-8">
            A collection of your walks and AI-generated travelogues.
        </p>

        <!-- Walk List -->
        <v-slide-y-transition group>
            <v-card
                v-for="(walk, index) in pastWalks"
                :key="walk.id"
                class="mb-4 rounded-xl"
                border
                flat
                link
            >
                <v-card-item class="pa-5">
                    <div class="d-flex justify-space-between align-start mb-3">
                        <div>
                            <p class="font-serif text-h6 font-weight-bold text-grey-darken-4 mb-1">
                                {{ walk.title || `Walk #${pastWalks.length - index}` }}
                            </p>
                            <p class="text-caption text-medium-emphasis">{{ formatDate(walk.startTime) }}</p>
                        </div>
                        <span class="text-h5">🌍</span>
                    </div>
                    
                    <p class="text-body-2 text-grey-darken-1 overflow-hidden" style="display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;">
                        {{ getSnippet(walk) }}
                    </p>
                </v-card-item>
            </v-card>
        </v-slide-y-transition>

        <!-- Empty State -->
        <div v-if="pastWalks.length === 0" class="mt-8 text-center py-8">
            <v-icon size="64" color="grey-lighten-2" class="mb-4">mdi-notebook-outline</v-icon>
            <p class="text-body-2 text-medium-emphasis">
                Start a new walk to add entries to your journal.
            </p>
        </div>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup lang="ts">
import { useRouteStore } from '@/stores/route'
import { storeToRefs } from 'pinia'
import type { Walk } from '@/types'

const routeStore = useRouteStore()
const { pastWalks } = storeToRefs(routeStore)

function formatDate(timestamp: number) {
    const date = new Date(timestamp)
    return date.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric'
    })
}

function getSnippet(walk: Walk): string {
    const firstNote = walk.observations.find(o => o.type === 'text' || o.type === 'note')?.content || walk.observations.find(o => o.text)?.text
    if (firstNote) return firstNote
    return "A journey through the quiet streets, where the patter of rain on cobblestones became a meditation..."
}
</script>
