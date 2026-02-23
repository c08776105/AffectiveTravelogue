import { defineStore } from "pinia";
import { ref, computed, watchEffect } from "vue";
import { apiClient } from "@/api/client";
import { sha256Hash } from "@/utils/hashUtils";
import type { Route, Walk, Observation, LatLng } from "@/types";

export const useProfileStore = defineStore("profile", () => {
  const username = ref("Wanderer");

  const avatar = ref("");

  watchEffect(async () => {
    if (!username.value) return;
    const hashValue = await sha256Hash(username.value);
    avatar.value = `https://www.gravatar.com/avatar/${hashValue}?s=200&d=robohash`;
  });

  return { username, avatar };
});
