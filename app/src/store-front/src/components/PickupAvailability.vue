<template>
  <section class="pickup" aria-labelledby="pickup-heading" aria-live="polite">
    <h3 id="pickup-heading">Store pickup</h3>
    <p v-if="loading" role="status">Checking pickup availability...</p>
    <p v-else-if="error" class="pickup-error" role="alert">{{ error }}</p>
    <p v-else-if="availability">
      <strong>{{ availability.availableQuantity }} available</strong> at {{ availability.storeName }}.
      Ready in {{ availability.readyInMinutes }} minutes.
    </p>
    <button type="button" :disabled="loading" @click="checkAvailability">Check availability</button>
    <small>Delivery and checkout are available independently of store pickup.</small>
  </section>
</template>

<script setup lang="ts">
import { onBeforeUnmount, ref, watch } from 'vue'

interface Availability {
  productId: number
  availableQuantity: number
  storeName: string
  readyInMinutes: number
}

const props = defineProps<{ productId: number }>()
const availability = ref<Availability | null>(null)
const loading = ref(false)
const error = ref('')
let currentRequest: AbortController | undefined

async function checkAvailability() {
  currentRequest?.abort()
  const controller = new AbortController()
  currentRequest = controller
  const timeout = setTimeout(() => controller.abort(), 20000)
  loading.value = true
  error.value = ''
  availability.value = null
  try {
    const response = await fetch(`/api/pickup/${props.productId}`, { signal: controller.signal })
    if (!response.ok) throw new Error(`Pickup returned HTTP ${response.status}`)
    const result: unknown = await response.json()
    if (
      !result || typeof result !== 'object' ||
      !('productId' in result) || result.productId !== props.productId ||
      !('availableQuantity' in result) || typeof result.availableQuantity !== 'number' ||
      !Number.isInteger(result.availableQuantity) || result.availableQuantity < 0 ||
      !('storeName' in result) || typeof result.storeName !== 'string' ||
      !('readyInMinutes' in result) || typeof result.readyInMinutes !== 'number' ||
      !Number.isInteger(result.readyInMinutes) || result.readyInMinutes < 0
    ) throw new Error('Invalid pickup response')
    if (currentRequest === controller) availability.value = result as Availability
  } catch (failure) {
    if (currentRequest === controller) {
      console.error('Pickup availability failed', failure)
      error.value = 'Pickup availability is temporarily unavailable. Shopping and checkout still work.'
    }
  } finally {
    clearTimeout(timeout)
    if (currentRequest === controller) loading.value = false
  }
}

watch(() => props.productId, checkAvailability, { immediate: true })
onBeforeUnmount(() => {
  const request = currentRequest
  currentRequest = undefined
  request?.abort()
})
</script>

<style scoped>
.pickup { margin-top: 1.5rem; padding: 1rem; border: 1px solid #ddd; border-radius: 5px; }
.pickup h3 { margin-top: 0; }
.pickup p { margin: 0.75rem 0; }
.pickup small { display: block; margin-top: 0.75rem; }
.pickup-error { color: #a32121; }
</style>
