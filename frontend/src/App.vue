<template>
  <v-app>
    <router-view></router-view>
  </v-app>
</template>

<script setup lang="ts">
import { onMounted } from 'vue';
import { useSyncStore } from '@/stores/sync';
import { useRouteStore } from '@/stores/route';

const syncStore = useSyncStore();
const routeStore = useRouteStore();

onMounted(() => {
  syncStore.startHealthCheck();
  routeStore.fetchHistory();
});
</script>

<style>
/* Global styles are imported in main.ts */
</style>
