<template>
    <v-dialog
        v-model="dialog"
        max-width="400"
        transition="dialog-bottom-transition"
        fullscreen
    >
        <v-card class="bg-white">
            <v-toolbar color="transparent" density="compact">
                <v-spacer></v-spacer>
                <v-btn icon @click="dialog = false">
                    <v-icon>mdi-close</v-icon>
                </v-btn>
            </v-toolbar>

            <v-card-text class="pa-6 pt-0">
                <!-- Profile Header -->
                <div class="d-flex flex-column align-center mb-8 text-center">
                    <v-avatar
                        size="88"
                        class="elevation-4 mb-4"
                        style="
                            background: linear-gradient(
                                135deg,
                                rgb(var(--v-theme-primary)),
                                rgb(var(--v-theme-secondary))
                            );
                        "
                    >
                        <v-img :src="avatar" alt="User Avatar"></v-img>
                    </v-avatar>
                    <h1
                        class="text-h4 font-serif font-weight-bold text-grey-darken-4"
                    >
                        {{ username }}
                    </h1>
                    <p class="text-body-1 text-medium-emphasis mt-1">
                        Documenting psychogeographical journeys
                    </p>
                </div>

                <!-- Stats Section -->
                <v-row class="mb-8">
                    <v-col cols="4">
                        <v-card
                            class="text-center pa-3 bg-grey-lighten-4 rounded-lg"
                            flat
                        >
                            <div
                                class="text-caption text-medium-emphasis text-uppercase font-weight-bold mb-1"
                            >
                                Walks
                            </div>
                            <div class="text-h5 font-weight-black text-primary">
                                {{ pastWalks.length }}
                            </div>
                        </v-card>
                    </v-col>
                    <v-col cols="4">
                        <v-card
                            class="text-center pa-3 bg-grey-lighten-4 rounded-lg"
                            flat
                        >
                            <div
                                class="text-caption text-medium-emphasis text-uppercase font-weight-bold mb-1"
                            >
                                Km
                            </div>
                            <div class="text-h5 font-weight-black text-primary">
                                {{ totalKm }}
                            </div>
                        </v-card>
                    </v-col>
                    <v-col cols="4">
                        <v-card
                            class="text-center pa-3 bg-grey-lighten-4 rounded-lg"
                            flat
                        >
                            <div
                                class="text-caption text-medium-emphasis text-uppercase font-weight-bold mb-1"
                            >
                                Notes
                            </div>
                            <div class="text-h5 font-weight-black text-primary">
                                {{ totalEntries }}
                            </div>
                        </v-card>
                    </v-col>
                </v-row>

                <!-- Preferences placeholder section -->
                <h2 class="text-h6 font-weight-bold text-grey-darken-4 mb-4">
                    Preferences Placeholder
                </h2>
                <v-list class="pa-0 bg-transparent mb-8">
                    <v-list-item class="px-0 mb-2"> {{ avatar }} </v-list-item>

                    <v-list-item class="px-0 mb-2">
                        <template v-slot:prepend>
                            <v-icon
                                color="primary"
                                class="mr-4 bg-primary-lighten-5 pa-2 rounded-lg"
                                size="small"
                                >mdi-shield-check</v-icon
                            >
                        </template>
                        <v-list-item-title class="font-weight-medium"
                            >Data Privacy</v-list-item-title
                        >
                        <template v-slot:append>
                            <v-icon size="small" color="grey"
                                >mdi-chevron-right</v-icon
                            >
                        </template>
                    </v-list-item>
                </v-list>
            </v-card-text>
        </v-card>
    </v-dialog>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { useRouteStore } from "@/stores/route";
import { storeToRefs } from "pinia";
import { useProfileStore } from "@/stores/profile";

const props = defineProps<{
    modelValue: boolean;
}>();

const emit = defineEmits<{
    (e: "update:modelValue", value: boolean): void;
}>();

const dialog = computed({
    get: () => props.modelValue,
    set: (val) => emit("update:modelValue", val),
});

const routeStore = useRouteStore();
const profileStore = useProfileStore();
const { pastWalks } = storeToRefs(routeStore);
const { username, avatar } = storeToRefs(profileStore);

const totalKm = computed(() => {
    return pastWalks.value
        .reduce((acc, walk) => acc + walk.distance, 0)
        .toFixed(1);
});

const totalEntries = computed(() => {
    return pastWalks.value.reduce(
        (acc, walk) => acc + walk.observations.length,
        0,
    );
});
</script>
