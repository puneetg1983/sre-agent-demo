<template>
  <TopNav />
  <router-view />
  <p class="photo-credits">
    <a href="/image-credits.txt" target="_blank" rel="noopener noreferrer"
      >Product photo credits and licenses</a
    >
  </p>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import { useProductStore, useOrderStore } from '@/stores'
import type { Product } from '@/types'
import TopNav from './components/TopNav.vue'

const productStore = useProductStore()
const orderStore = useOrderStore()
let refreshTimer: ReturnType<typeof setInterval> | undefined

onMounted(() => {
  if (productStore.count === 0) {
    console.log('Fetching products')
    fetch('/api/products')
      .then((response) => response.json())
      .then((data: Product[]) => {
        productStore.addProducts(data)
        console.log(`Fetched ${data.length} products`)
      })
      .catch((error) => {
        console.log(error)
        alert('Error occurred while fetching products')
      })
  }
  void orderStore.fetchOrders()
  refreshTimer = setInterval(() => { void orderStore.fetchOrders() }, 5000)
})

onUnmounted(() => {
  if (refreshTimer !== undefined) clearInterval(refreshTimer)
})
</script>

<style scoped>
.photo-credits {
  margin: 1.5rem;
  font-size: 0.85rem;
}
.photo-credits a {
  color: inherit;
  text-decoration: underline;
}
</style>
