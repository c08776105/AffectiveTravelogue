<template>
  <v-app>
    <router-view></router-view>
  </v-app>
</template>

<script setup lang="ts">
import { onMounted } from 'vue';
import { useSyncStore } from '@/stores/sync';

const syncStore = useSyncStore();

onMounted(() => {
  syncStore.startHealthCheck();
});
</script>

<style>
/* Global styles are imported in main.ts */
</style>
