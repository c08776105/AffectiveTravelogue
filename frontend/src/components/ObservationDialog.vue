<template>
  <v-dialog :model-value="modelValue" @update:model-value="$emit('update:modelValue', $event)" fullscreen transition="dialog-bottom-transition">
    <v-card class="bg-surface">
      <v-toolbar color="surface" density="compact">
        <v-btn icon="mdi-close" @click="$emit('update:modelValue', false)"></v-btn>
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
            Text
          </v-tab>
          <v-tab value="voice">
            <v-icon start>mdi-microphone</v-icon>
            Voice
          </v-tab>
          <v-tab value="image">
            <v-icon start>mdi-camera</v-icon>
            Image
          </v-tab>
        </v-tabs>

        <v-window v-model="activeTab">
          <!-- Text Tab -->
          <v-window-item value="text">
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
              label="Your notes"
              placeholder="Write your observations..."
              variant="outlined"
              rows="6"
              auto-grow
              counter
            ></v-textarea>
          </v-window-item>

          <!-- Voice Tab -->
          <v-window-item value="voice">
            <div class="text-center py-8">
              <v-btn
                :color="isRecordingVoice ? 'error' : 'primary'"
                size="x-large"
                icon
                class="mb-4 pulse-on-record"
                :class="{ 'pulse-animation': isRecordingVoice }"
                @click="toggleVoiceRecording"
                :loading="isProcessingAudio"
                width="80"
                height="80"
              >
                <v-icon size="40">{{ isRecordingVoice ? 'mdi-stop' : 'mdi-microphone' }}</v-icon>
              </v-btn>
              
              <div class="text-h6 font-weight-medium">
                {{ isRecordingVoice ? formatDuration(voiceRecordingTime) : 'Tap to Record' }}
              </div>
              
              <v-expand-transition>
                <div v-if="voiceData" class="mt-4 text-success d-flex align-center justify-center">
                    <v-icon start color="success">mdi-check-circle</v-icon>
                    Audio captured
                </div>
              </v-expand-transition>
            </div>
          </v-window-item>

          <!-- Image Tab -->
          <v-window-item value="image">
            <div v-if="!imagePreview" class="text-center py-8 border-dashed rounded-lg" @click="$refs.fileInput.click()">
                <v-icon size="64" color="medium-emphasis" class="mb-2">mdi-camera-plus</v-icon>
                <div class="text-body-1 text-medium-emphasis">Tap to upload photo</div>
                <input
                    ref="fileInput"
                    type="file"
                    accept="image/*"
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
                <v-text-field
                    v-model="imageCaption"
                    label="Caption"
                    variant="outlined"
                    density="compact"
                ></v-text-field>
            </div>
          </v-window-item>
        </v-window>
      </div>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { ref, computed, onUnmounted } from 'vue'

const props = defineProps<{
  modelValue: boolean
  location: { lat: number; lng: number }
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  'save-observation': [observation: { type: string; text?: string; imageData?: string; audioData?: string; caption?: string }]
}>()

const activeTab = ref<'text' | 'voice' | 'image'>('text')
const noteText = ref('')
const voiceData = ref('')
const isRecordingVoice = ref(false)
const voiceRecordingTime = ref(0)
const isProcessingAudio = ref(false)
const imagePreview = ref('')
const imageData = ref('')
const imageCaption = ref('')
const fileInput = ref<HTMLInputElement>()

let mediaRecorder: MediaRecorder | null = null
let audioChunks: Blob[] = []
let voiceTimer: number | null = null

const prompts = [
    "👁️ What do you see?",
    "👃 What do you smell?",
    "👂 What do you hear?",
    "💭 How do you feel?"
]

const hasContent = computed(() => {
  return noteText.value || voiceData.value || imageData.value
})

function formatDuration(seconds: number) {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}:${secs.toString().padStart(2, '0')}`
}

function toggleVoiceRecording() {
  if (isRecordingVoice.value) {
    stopVoiceRecording()
  } else {
    startVoiceRecording()
  }
}

async function startVoiceRecording() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    mediaRecorder = new MediaRecorder(stream)
    audioChunks = []

    mediaRecorder.ondataavailable = (event) => {
      audioChunks.push(event.data)
    }

    mediaRecorder.onstop = () => {
      const audioBlob = new Blob(audioChunks, { type: 'audio/webm' })
      const reader = new FileReader()
      reader.onload = (e) => {
        voiceData.value = e.target?.result as string
        isProcessingAudio.value = false
      }
      reader.readAsDataURL(audioBlob)
      stream.getTracks().forEach((track) => track.stop())
    }

    mediaRecorder.start()
    isRecordingVoice.value = true
    voiceRecordingTime.value = 0

    voiceTimer = window.setInterval(() => {
      voiceRecordingTime.value++
    }, 1000)
  } catch (error) {
    console.error('Error accessing microphone:', error)
    alert('Unable to access microphone. Please check permissions.')
  }
}

function stopVoiceRecording() {
  if (mediaRecorder && isRecordingVoice.value) {
    isProcessingAudio.value = true
    mediaRecorder.stop()
    isRecordingVoice.value = false
    if (voiceTimer) {
      clearInterval(voiceTimer)
      voiceTimer = null
    }
  }
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
  if (fileInput.value) {
    fileInput.value.value = ''
  }
}

function saveObservation() {
  const observation: any = {}

  if (activeTab.value === 'text' && noteText.value) {
    observation.type = 'text'
    observation.text = noteText.value
  } else if (activeTab.value === 'voice' && voiceData.value) {
    observation.type = 'voice'
    observation.audioData = voiceData.value
  } else if (activeTab.value === 'image' && imageData.value) {
    observation.type = 'image'
    observation.imageData = imageData.value
    if (imageCaption.value) {
      observation.caption = imageCaption.value
    }
  }

  if (Object.keys(observation).length > 0) {
    emit('save-observation', observation)
    emit('update:modelValue', false)
    // Reset state
    noteText.value = ''
    voiceData.value = ''
    imageData.value = ''
    imagePreview.value = ''
    activeTab.value = 'text'
  }
}

onUnmounted(() => {
    if (voiceTimer) clearInterval(voiceTimer)
    if (mediaRecorder && isRecordingVoice.value) {
        mediaRecorder.stream.getTracks().forEach(t => t.stop())
    }
})
</script>

<style scoped>
.border-dashed {
    border: 2px dashed rgba(255, 255, 255, 0.2);
    cursor: pointer;
    transition: all 0.2s;
}
.border-dashed:hover {
    border-color: var(--v-primary-base);
    background: rgba(255, 255, 255, 0.05);
}
</style>
