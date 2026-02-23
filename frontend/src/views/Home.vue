<template>
    <div class="home-wrapper fill-height">
        <v-fab
            :active="!hidden"
            icon
            location="top end"
            size="large"
            app
            color="white"
            class="mt-4 mr-4"
            @click="showProfile = true"
        >
            <v-avatar size="44">
                <v-img :src="avatar" alt="User Avatar"></v-img>
            </v-avatar>
        </v-fab>

        <v-container
            fluid
            class="fill-height align-start bg-grey-lighten-5 pa-6"
        >
            <v-row>
                <v-col cols="12">
                    <!-- Header Section -->
                    <div class="mb-8">
                        <h1
                            class="text-h4 font-serif font-weight-bold text-grey-darken-4 mb-1"
                        >
                            {{ greeting }},<br />{{ username }}.
                        </h1>
                        <p class="text-body-2 text-grey-darken-1">
                            {{ currentDate }}
                        </p>
                    </div>

                    <!-- Last Walk Card -->
                    <v-card
                        class="mb-8 rounded-xl"
                        elevation="1"
                        border
                        v-if="pastWalks.length > 0"
                    >
                        <v-card-item class="pa-5">
                            <div
                                class="d-flex align-center justify-space-between mb-4"
                            >
                                <h2
                                    class="text-h6 font-serif font-weight-bold text-grey-darken-4"
                                >
                                    {{ lastWalk?.title || "Recent Journey" }}
                                </h2>
                                <span class="text-h5">📍</span>
                            </div>

                            <v-row no-gutters class="mb-4">
                                <v-col cols="6">
                                    <div
                                        class="text-caption text-uppercase font-weight-bold text-grey-darken-1 mb-1"
                                    >
                                        Observations
                                    </div>
                                    <div
                                        class="text-h6 font-weight-bold text-grey-darken-4"
                                    >
                                        {{
                                            lastWalk?.observations?.length || 0
                                        }}
                                    </div>
                                </v-col>
                                <v-col cols="6">
                                    <div
                                        class="text-caption text-uppercase font-weight-bold text-grey-darken-1 mb-1"
                                    >
                                        Date
                                    </div>
                                    <div
                                        class="text-body-1 font-weight-bold text-grey-darken-4"
                                    >
                                        {{
                                            lastWalk
                                                ? new Date(
                                                      lastWalk.startTime,
                                                  ).toLocaleDateString()
                                                : ""
                                        }}
                                    </div>
                                </v-col>
                            </v-row>

                            <p
                                class="text-body-2 text-grey-darken-2 mb-4 font-italic"
                            >
                                "{{ lastWalk ? getSnippet(lastWalk) : "" }}"
                            </p>

                            <v-btn
                                block
                                flat
                                color="primary"
                                variant="tonal"
                                height="44"
                                class="text-none font-weight-bold"
                                to="/journal"
                            >
                                View in Journal
                            </v-btn>
                        </v-card-item>
                    </v-card>

                    <v-card
                        class="mb-8 rounded-xl pa-6 text-center"
                        elevation="0"
                        border
                        v-else
                    >
                        <div class="text-h1 mb-4">🗺️</div>
                        <h3
                            class="text-h6 font-weight-bold text-grey-darken-3 mb-2"
                        >
                            Ready to explore?
                        </h3>
                        <p class="text-body-2 text-grey-darken-1">
                            Begin your first journey.
                        </p>
                    </v-card>

                    <!-- Stats Section -->
                    <div class="mb-4">
                        <h3
                            class="text-h6 font-serif font-weight-bold text-grey-darken-4 mb-4"
                        >
                            Your Journey
                        </h3>
                        <v-row>
                            <v-col cols="6">
                                <v-card
                                    class="rounded-xl pa-4"
                                    elevation="0"
                                    border
                                >
                                    <div
                                        class="text-caption text-uppercase font-weight-bold text-grey-darken-1 mb-2"
                                    >
                                        Total Walks
                                    </div>
                                    <div
                                        class="text-h5 font-weight-bold text-grey-darken-4"
                                    >
                                        {{ pastWalks.length }}
                                    </div>
                                </v-card>
                            </v-col>
                            <v-col cols="6">
                                <v-card
                                    class="rounded-xl pa-4"
                                    elevation="0"
                                    border
                                >
                                    <div
                                        class="text-caption text-uppercase font-weight-bold text-grey-darken-1 mb-2"
                                    >
                                        Total Notes
                                    </div>
                                    <div
                                        class="text-h5 font-weight-bold text-grey-darken-4"
                                    >
                                        {{
                                            pastWalks.reduce(
                                                (acc, walk) =>
                                                    acc +
                                                    (walk.observations
                                                        ?.length || 0),
                                                0,
                                            )
                                        }}
                                    </div>
                                </v-card>
                            </v-col>
                        </v-row>
                    </div>
                </v-col>
            </v-row>
        </v-container>

        <v-fab
            :active="!hidden"
            icon="mdi-plus"
            location="bottom end"
            size="large"
            app
            color="primary"
            elevation="4"
            class="mb-4 mr-4"
            to="/map"
        >
        </v-fab>

        <!-- Profile Dialog -->
        <profile-dialog v-model="showProfile" />
    </div>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import { useRouteStore } from "@/stores/route";
import { storeToRefs } from "pinia";
import ProfileDialog from "@/components/ProfileDialog.vue";
import type { Walk } from "@/types";
import { useProfileStore } from "@/stores/profile";

const showProfile = ref(false);
const hidden = ref(false); // Controls visibility of FABs

const profileStore = useProfileStore();
const routeStore = useRouteStore();
const { pastWalks } = storeToRefs(routeStore);
const { username, avatar } = storeToRefs(profileStore);

const lastWalk = computed(() => {
    if (pastWalks.value.length === 0) return null;
    return pastWalks.value[pastWalks.value.length - 1];
});

function getSnippet(walk: Walk): string {
    const firstNote =
        walk.observations?.find((o) => o.type === "text" || o.type === "note")
            ?.content || walk.observations?.find((o) => o.text)?.text;
    if (firstNote) return firstNote;
    return "A journey through the quiet streets...";
}

const greeting = computed(() => {
    const hour = new Date().getHours();
    if (hour < 12) return "Good morning";
    if (hour < 18) return "Good afternoon";
    return "Good evening";
});

const currentDate = computed(() => {
    return new Date().toLocaleDateString("en-US", {
        weekday: "long",
        year: "numeric",
        month: "long",
        day: "numeric",
    });
});
</script>

<style scoped>
.home-wrapper {
    position: relative;
    width: 100%;
}
</style>
