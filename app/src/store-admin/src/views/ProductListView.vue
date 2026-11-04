<template>
  <div class="action-button">
    <router-link to="/product/add">
      <button class="button">Add Product</button>
    </router-link>
  </div>

  <div v-if="products.length > 0" class="product-table">
    <!-- Column headers -->
    <div class="table-header">
      <div class="column-id">Product ID</div>
      <div class="column-name">Product Name</div>
      <div class="column-category">Category</div>
      <div class="column-description">Description</div>
      <div class="column-price">Price</div>
    </div>

    <!-- Product rows -->
    <div
      v-for="product in products"
      :key="product.id"
      class="table-row clickable"
      @click="navigateToProduct(product.id)"
    >
      <div class="column-id">{{ product.id }}</div>
      <div class="column-name">{{ product.name }}</div>
      <div class="column-category">{{ product.category || 'General' }}</div>
      <div class="column-description">{{ product.description }}</div>
      <div class="column-price">{{ product.price }}</div>
    </div>
  </div>

  <div class="empty-list" v-else>
    <h3>No products available</h3>
    <p>Add your first product to get started</p>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useProductStore } from '@/stores'
import { useRouter } from 'vue-router'

const productStore = useProductStore()
const router = useRouter()

const products = computed(() => productStore.products)

const navigateToProduct = (productId: string | number) => {
  router.push(`/product/${productId}`)
}
</script>

<style scoped>
.action-button {
  text-align: right;
  margin: 1.5rem;
}

.product-table {
  background-color: var(--card-background);
  border-radius: var(--border-radius);
  box-shadow: var(--shadow);
  overflow: hidden;
  width: 95vw;
  margin: 2rem auto;
}

.table-header,
.table-row {
  display: grid;
  grid-template-columns: 0.5fr 1.5fr 1fr 2fr 0.5fr;
  gap: 12px;
  align-items: center;
  padding: 0.5rem 1rem;
}

.table-header {
  background-color: var(--cp-surface-soft);
  color: var(--cp-text-muted);
  font-weight: bold;
}

.table-row {
  border-bottom: 1px solid var(--cp-border);
}

.table-row:last-child {
  border-bottom: none;
}

.clickable {
  cursor: pointer;
  transition: background-color 0.2s;
}

.table-row:hover {
  background-color: var(--cp-accent-soft);
}

.column-id {
  text-align: left;
}

.column-name {
  white-space: nowrap;
  overflow: hidden;
  text-align: left;
  text-overflow: ellipsis;
}

.column-description {
  white-space: nowrap;
  overflow: hidden;
  text-align: left;
  text-overflow: ellipsis;
}

.column-price {
  text-align: right;
}

.empty-list {
  text-align: center;
  padding: 2rem;
  background-color: var(--card-background);
  border-radius: var(--border-radius);
  box-shadow: var(--shadow);
  margin: 1rem 0;
}

@media (max-width: 768px) {
  .page-container {
    width: 95%;
    padding: 0 1rem;
  }

  .table-header,
  .table-row {
    grid-template-columns: 0.2fr 1.5fr 1fr 2fr 0.5fr;
    font-size: 0.9rem;
  }
}
</style>
