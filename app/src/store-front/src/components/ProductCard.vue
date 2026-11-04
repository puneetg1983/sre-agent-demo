<template>
  <div class="product-card">
    <img :src="product.image" :alt="product.name" loading="lazy" decoding="async" @click="routeToProduct" />
    <span class="category">{{ product.category || 'General' }}</span>
    <h2 @click="routeToProduct">{{ product.name }}</h2>
    <p @click="routeToProduct">{{ product.description }}</p>
    <div class="product-details">
      <div class="product-price">
        <p class="price">{{ product.price.toFixed(2) }}</p>
      </div>
      <div class="product-controls">
        <input type="number" v-model="quantity" min="1" class="quantity-input"
          :aria-label="`Quantity for ${product.name}`" />
        <button @click="addToCart">Add to Cart</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useProductStore, useCartStore } from '@/stores'
import type { Product, CartItem } from '@/types'

const productStore = useProductStore()
const cartStore = useCartStore()
const router = useRouter()

const props = defineProps<{
  product: Product
}>()

const product = ref<Product>(props.product)

const quantity = ref(1)

const addToCart = () => {
  const cartItem: CartItem = {
    product: product.value,
    quantity: quantity.value,
  }
  cartStore.addItem(cartItem)
}

const routeToProduct = () => {
  router.push(`/product/${product.value.id}`)
}

onMounted(() => {
  const fetchedProduct = productStore.products.find((p: Product) => p.id == props.product.id)
  if (fetchedProduct) {
    product.value = fetchedProduct
  }
})
</script>

<style scoped>
.product-card { margin: 0; padding: 20px; align-items: stretch; text-align: left; border: 1px solid var(--cp-border); background: var(--cp-surface); box-shadow: none; border-radius: 16px; }
.product-card img { width: 100%; aspect-ratio: 4 / 3; object-fit: contain; border-radius: 0.625rem; background: var(--cp-surface-soft); }
.category { color: var(--cp-accent); font-size: 0.75rem; font-weight: 600; }
h2 { color: var(--cp-text); font-size: 1rem; line-height: 1.5; margin: 8px 0; }
.product-card > p { display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; color: var(--cp-text-muted); font-size: 0.875rem; line-height: 1.5; margin: 0 0 16px; }
.product-details { margin-top: auto; }
.product-price .price { color: var(--cp-text); margin: 0 0 12px; }
.product-controls { margin: 0; gap: 8px; }
.quantity-input { box-sizing: border-box; width: 52px; height: 40px; margin: 0; background: var(--cp-surface); color: var(--cp-text); border-color: var(--cp-border); }
.product-controls button { flex: 1; height: 40px; font: inherit; font-size: 0.8125rem; padding: 8px; }
</style>
