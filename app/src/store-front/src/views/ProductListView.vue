<template>
  <main class="catalog">
    <header class="catalog-heading">
      <p class="eyebrow">CONTOSO SPORTS STORE</p>
      <h1>Find your next move</h1>
      <p>Equipment for the court, the trail, and everything in between.</p>
    </header>
    <div class="category-filters" role="group" aria-label="Filter products by category">
      <button :aria-pressed="selectedCategory === ''" @click="selectCategory('')">
        All products <span>{{ products.length }}</span>
      </button>
      <button v-for="category in categories" :key="category.name"
        :aria-pressed="selectedCategory === category.name" @click="selectCategory(category.name)">
        {{ category.name }} <span>{{ category.count }}</span>
      </button>
    </div>
    <div class="catalog-summary">
      <h2>{{ selectedCategory || 'All products' }}</h2>
      <p role="status" aria-live="polite">{{ filteredProducts.length }} products</p>
    </div>
    <div class="product-list">
      <ProductCard v-for="product in visibleProducts" :key="product.id" :product="product" />
    </div>
    <p v-if="!filteredProducts.length" class="photo-note">No products in this category.</p>
    <button v-if="visibleProducts.length < filteredProducts.length" class="load-more"
      @click="visibleCount += PAGE_SIZE">
      Show more products
    </button>
    <p class="photo-note">Product-family photos are illustrative; finishes and quantities may vary.</p>
  </main>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useProductStore } from '@/stores'
import ProductCard from '@/components/ProductCard.vue'

const productStore = useProductStore()
const route = useRoute()
const router = useRouter()
const PAGE_SIZE = 24
const visibleCount = ref(PAGE_SIZE)
const products = computed(() => productStore.products)
const selectedCategory = computed(() =>
  typeof route.query.category === 'string' ? route.query.category : '')
const categories = computed(() => {
  const counts = new Map<string, number>()
  for (const product of products.value) {
    const category = product.category || 'General'
    counts.set(category, (counts.get(category) || 0) + 1)
  }
  return [...counts].sort(([a], [b]) => a.localeCompare(b))
    .map(([name, count]) => ({ name, count }))
})
const filteredProducts = computed(() => products.value.filter(product =>
  !selectedCategory.value || (product.category || 'General') === selectedCategory.value))
const visibleProducts = computed(() => filteredProducts.value.slice(0, visibleCount.value))
const selectCategory = (category: string) => {
  void router.replace({ query: { ...route.query, category: category || undefined } })
}
watch(selectedCategory, () => { visibleCount.value = PAGE_SIZE })
</script>

<style scoped>
.catalog { max-width: 1440px; margin: 0 auto; padding: 24px; text-align: left; }
.catalog-heading { padding: 16px 0 24px; }
.eyebrow { color: var(--cp-accent); font-size: 0.75rem; font-weight: 700; letter-spacing: 0.12em; }
h1 { margin: 8px 0; font-size: clamp(2rem, 4vw, 3rem); color: var(--cp-text); }
.catalog-heading > p:last-child, .catalog-summary p, .photo-note { color: var(--cp-text-muted); }
.category-filters { display: flex; flex-wrap: wrap; gap: 8px; padding: 0 0 24px; border-bottom: 1px solid var(--cp-border); }
.category-filters button { background: var(--cp-surface); color: var(--cp-text); border: 1px solid var(--cp-border); border-radius: 0.625rem; padding: 10px 12px; font: inherit; font-size: 0.875rem; }
.category-filters button span { margin-left: 8px; color: var(--cp-text-muted); font-size: 0.75rem; }
.category-filters button:hover { border-color: var(--cp-accent); }
.category-filters button[aria-pressed="true"] { background: var(--cp-accent-soft); color: var(--cp-accent); border-color: var(--cp-accent); }
.catalog-summary { display: flex; align-items: center; justify-content: space-between; gap: 16px; margin: 24px 0 16px; }
.catalog-summary h2, .catalog-summary p { margin: 0; }
.catalog-summary h2 { font-size: 1.25rem; }
.product-list { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 20px; }
.load-more { display: block; margin: 24px auto; font: inherit; }
.photo-note { font-size: 0.8125rem; margin-top: 24px; }
@media (max-width: 600px) {
  .catalog { padding: 16px; }
  .product-list { grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); }
}
</style>
