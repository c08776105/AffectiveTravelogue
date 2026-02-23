<template>
  <v-main>
    <!-- Transition for route changes -->
    <router-view v-slot="{ Component }">
      <transition name="fade" mode="out-in">
        <component :is="Component" />
      </transition>
    </router-view>
  </v-main>

  <!-- Vuetify Bottom Navigation -->
  <v-bottom-navigation
    app
    grow
    color="primary"
    mode="shift"
    class="elevation-4"
  >
    <v-btn to="/" exact>
      <v-icon>mdi-home-variant-outline</v-icon>
      <span>Home</span>
    </v-btn>

    <v-btn to="/map">
      <v-icon>mdi-map-marker-radius-outline</v-icon>
      <span>Map</span>
    </v-btn>

    <v-btn to="/journal">
      <v-icon>mdi-book-open-page-variant-outline</v-icon>
      <span>Journal</span>
    </v-btn>
  </v-bottom-navigation>
</template>

<style scoped>
/* Minimal override just to ensuring fading works if needed, standard Vuetify otherwise */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
