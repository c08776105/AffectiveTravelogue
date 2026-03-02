<template>
  <v-dialog :model-value="modelValue" @update:model-value="$emit('update:modelValue', $event)" fullscreen transition="dialog-bottom-transition">
    <v-card class="bg-surface">
      <v-toolbar color="surface" density="compact">
        <v-btn icon="mdi-close" @click="close"></v-btn>
        <v-toolbar-title class="text-subtitle-1">Add Observation</v-toolbar-title>
        <v-spacer></v-spacer>
        <v-btn
            color="primary"
            variant="text"
            @click="saveObservation"
            :disabled="!hasContent"
        >
            Save
        </v-btn>
      </v-toolbar>

      <div class="pa-4">
        <div class="text-caption text-medium-emphasis mb-4">
            📍 {{ location.lat.toFixed(4) }}, {{ location.lng.toFixed(4) }}
        </div>

        <v-tabs v-model="activeTab" color="primary" grow class="mb-6">
          <v-tab value="text">
            <v-icon start>mdi-text</v-icon>
            Reflect
          </v-tab>
          <v-tab value="image">
            <v-icon start>mdi-camera</v-icon>
            Capture
          </v-tab>
        </v-tabs>

        <v-window v-model="activeTab">

          <!-- Text / reflection tab -->
          <v-window-item value="text">
            <p class="text-caption text-medium-emphasis mb-3">
                Tap a prompt to use it, or write freely below.
            </p>
            <div class="d-flex flex-wrap gap-2 mb-4">
                <v-chip
                    v-for="prompt in prompts"
                    :key="prompt"
                    @click="noteText = prompt"
                    variant="outlined"
                    color="primary"
                    size="small"
                    class="mr-2 mb-2"
                >
                    {{ prompt }}
                </v-chip>
            </div>
            <v-textarea
              v-model="noteText"
              label="Your observation"
              placeholder="Write your thoughts…"
              variant="outlined"
              rows="6"
              auto-grow
              counter
            ></v-textarea>
          </v-window-item>

          <!-- Image / capture tab -->
          <v-window-item value="image">
            <div
                v-if="!imagePreview"
                class="text-center py-8 border-dashed rounded-lg"
                @click="triggerCamera"
            >
                <v-icon size="64" color="medium-emphasis" class="mb-2">mdi-camera-plus</v-icon>
                <div class="text-body-1 text-medium-emphasis">Tap to take a photo</div>
                <!-- capture=environment opens the rear camera directly on mobile -->
                <input
                    ref="fileInput"
                    type="file"
                    accept="image/*"
                    capture="environment"
                    @change="handlePhotoUpload"
                    style="display: none"
                />
            </div>

            <div v-else class="position-relative">
                <v-img :src="imagePreview" height="300" cover class="rounded-lg mb-4"></v-img>
                <v-btn
                    icon="mdi-close"
                    color="error"
                    size="small"
                    class="position-absolute top-0 right-0 ma-2"
                    @click="clearImage"
                ></v-btn>
                <v-textarea
                    v-model="imageCaption"
                    label="What does this image mean to you?"
                    placeholder="Describe the atmosphere, memory, or tension captured here…"
                    variant="outlined"
                    density="compact"
                    rows="3"
                    auto-grow
                ></v-textarea>
            </div>
          </v-window-item>

        </v-window>
      </div>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

const props = defineProps<{
  modelValue: boolean
  location: { lat: number; lng: number }
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  'save-observation': [observation: { type: string; text?: string; imageData?: string; caption?: string }]
}>()

const activeTab = ref<'text' | 'image'>('text')
const noteText = ref('')
const imagePreview = ref('')
const imageData = ref('')
const imageCaption = ref('')
const fileInput = ref<HTMLInputElement>()

const prompts = [
    "What mood does this space impose on you?",
    "What pulls you forward, or makes you want to linger?",
    "Whose space is this — and how do you know?",
    "What traces of other lives can you sense here?",
    "How does the architecture want you to move?",
    "What is the texture of the atmosphere around you?",
    "What memory does this place bring to the surface?",
    "If you followed desire rather than direction, where would you go?",
    "What sounds reveal where power lies here?",
    "What would you find if you took the unexpected path?",
]

const hasContent = computed(() => noteText.value.trim().length > 0 || imageData.value.length > 0)

function triggerCamera() {
    fileInput.value?.click()
}

function handlePhotoUpload(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (file) {
    const reader = new FileReader()
    reader.onload = (e) => {
        const result = e.target?.result as string
        imagePreview.value = result
        imageData.value = result
    }
    reader.readAsDataURL(file)
  }
}

function clearImage() {
  imagePreview.value = ''
  imageData.value = ''
  imageCaption.value = ''
  if (fileInput.value) fileInput.value.value = ''
}

function saveObservation() {
  let observation: { type: string; text?: string; imageData?: string; caption?: string } | null = null

  if (activeTab.value === 'text' && noteText.value.trim()) {
    observation = { type: 'text', text: noteText.value.trim() }
  } else if (activeTab.value === 'image' && imageData.value) {
    observation = { type: 'image', imageData: imageData.value }
    if (imageCaption.value.trim()) observation.caption = imageCaption.value.trim()
  }

  if (observation) {
    emit('save-observation', observation)
    close()
  }
}

function close() {
  emit('update:modelValue', false)
  // Reset for next use
  noteText.value = ''
  imageData.value = ''
  imagePreview.value = ''
  imageCaption.value = ''
  activeTab.value = 'text'
}
</script>

<style scoped>
.border-dashed {
    border: 2px dashed rgba(255, 255, 255, 0.2);
    cursor: pointer;
    transition: border-color 0.2s;
}
.border-dashed:hover {
    border-color: rgb(var(--v-theme-primary));
    background: rgba(255, 255, 255, 0.05);
}
</style>
