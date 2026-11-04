<template>
  <section class="recent-orders">
    <header class="orders-heading">
      <div>
        <h1>Recent orders</h1>
        <p>Latest 15 orders across all statuses, most recently updated first. Refreshes every 5 seconds.</p>
        <p v-if="orderStore.lastUpdated" class="updated">
          Last successful refresh: {{ new Date(orderStore.lastUpdated).toLocaleTimeString() }}
        </p>
      </div>
      <button :disabled="orderStore.loading" @click="orderStore.fetchOrders()">
        {{ orderStore.loading ? 'Refreshing...' : 'Refresh orders' }}
      </button>
    </header>

    <div v-if="orderStore.loadError" class="orders-error" role="alert">
      <strong>Order history unavailable</strong>
      <p>{{ orderStore.loadError }}</p>
      <p v-if="orders.length">Showing previously loaded orders. This is not live data.</p>
    </div>

    <p v-if="!orderStore.initialized" role="status">Fetching orders...</p>
    <div v-else-if="orders.length" class="table-container">
      <table>
        <thead>
          <tr>
            <th>Order ID</th>
            <th>Customer ID</th>
            <th>Status</th>
            <th>Last updated</th>
            <th class="total">Total</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="order in orders" :key="order.orderId">
            <td><RouterLink :to="`/order/${order.orderId}`">{{ order.orderId }}</RouterLink></td>
            <td>{{ order.customerId }}</td>
            <td><span :class="order.status === 0 ? 'pending' : 'completed'">
              {{ order.status === 0 ? 'Pending' : 'Completed' }}
            </span></td>
            <td>{{ formatUpdated(order.updatedAtUnixSeconds) }}</td>
            <td class="total">{{ orderTotal(order) }}</td>
          </tr>
        </tbody>
      </table>
    </div>
    <p v-else-if="!orderStore.loadError" class="empty-list">No orders available</p>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { useOrderStore } from '@/stores'
import type { Order } from '@/types'

const orderStore = useOrderStore()
const orders = computed(() => orderStore.orders)
const orderTotal = (order: Order) =>
  order.items.reduce((total, item) => total + item.quantity * item.price, 0).toFixed(2)
const formatUpdated = (seconds: number | undefined) =>
  seconds ? new Date(seconds * 1000).toLocaleString() : 'Not available'
</script>

<style scoped>
.recent-orders {
  width: calc(100% - 48px);
  max-width: 1360px;
  margin: 2rem auto;
  color: var(--cp-text);
  font-family: "Segoe UI", Aptos, Calibri, -apple-system, BlinkMacSystemFont, sans-serif;
  text-align: left;
}
.orders-heading { display: flex; justify-content: space-between; gap: 16px; align-items: center; }
h1 { margin: 0; font-size: 1.75rem; font-weight: 650; }
.orders-heading p { color: var(--cp-text-muted); }
.updated { font-size: 0.875rem; }
button {
  background: var(--cp-accent);
  color: var(--cp-accent-fg);
  border-radius: 0.625rem;
  flex-shrink: 0;
}
button:hover { background: var(--cp-accent-hover); }
button:disabled { opacity: 0.65; cursor: wait; }
.orders-error {
  margin: 16px 0;
  padding: 16px;
  border: 1px solid var(--cp-danger);
  border-radius: 0.625rem;
  background: var(--cp-surface);
  color: var(--cp-danger);
}
.orders-error p { margin-bottom: 0; }
.table-container {
  overflow-x: auto;
  background: var(--cp-surface);
  border: 1px solid var(--cp-border);
  border-radius: 16px;
}
table { width: 100%; border-collapse: collapse; }
th, td { padding: 10px 16px; border-bottom: 1px solid var(--cp-border); white-space: nowrap; }
th { background: var(--cp-surface-soft); color: var(--cp-text-muted); font-size: 0.8125rem; font-weight: 600; }
td { font-size: 0.875rem; }
tbody tr:last-child td { border-bottom: 0; }
tbody tr:hover { background: var(--cp-accent-soft); }
a { color: var(--cp-link); text-decoration: underline; }
.total { text-align: right; }
.pending, .completed {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 8px;
  border-radius: 0.625rem;
  font-size: 0.8125rem;
  font-weight: 600;
}
.pending { color: var(--cp-accent); background: var(--cp-accent-soft); }
.completed { color: var(--cp-text); background: var(--cp-surface-soft); }
.completed::before {
  content: '';
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--cp-success);
}
.empty-list { padding: 32px; text-align: center; background: var(--cp-surface); border-radius: 16px; }
@media (max-width: 700px) {
  .orders-heading { align-items: flex-start; flex-direction: column; }
}
</style>
