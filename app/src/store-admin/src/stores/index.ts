import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import type { Product, Order } from '@/types'

export const useProductStore = defineStore('product', () => {
  const products = ref<Product[]>([])
  const count = computed(() => products.value.length)
  const addProducts = (data: Product[]) => {
    products.value.push(...data)
  }
  const addProduct = (product: Product) => {
    products.value.push(product)
  }
  const updateProduct = (product: Product) => {
    const index = products.value.findIndex((p) => p.id === product.id)
    if (index === -1) return
    products.value[index] = product
  }
  const removeProduct = (product: Product) => {
    const index = products.value.findIndex((p) => p.id === product.id)
    if (index === -1) return
    products.value.splice(index, 1)
  }

  return { products, count, addProducts, addProduct, updateProduct, removeProduct }
})

export const useOrderStore = defineStore('order', () => {
  const orders = ref<Order[]>([])
  const initialized = ref(false)
  const loading = ref(false)
  const loadError = ref<string | null>(null)
  const lastUpdated = ref<string | null>(null)
  const count = computed(() => orders.value.length)
  const addOrders = (data: Order[]) => {
    orders.value = data
    initialized.value = true
  }
  const fetchOrders = async () => {
    if (loading.value) return
    loading.value = true
    try {
      const response = await fetch('/api/makeline/order/recent', {
        cache: 'no-store',
        signal: AbortSignal.timeout(10000),
      })
      if (!response.ok) throw new Error(`Order history request failed: HTTP ${response.status}`)
      const data: unknown = await response.json()
      if (!Array.isArray(data) || data.length > 50 || !data.every(isOrder)) {
        throw new Error('Invalid order history response')
      }
      addOrders(data)
      loadError.value = null
      lastUpdated.value = new Date().toISOString()
    } catch (error) {
      console.error('Error occurred while fetching orders', error)
      loadError.value = 'Unable to load orders. The order service or database may be unavailable.'
    } finally {
      initialized.value = true
      loading.value = false
    }
  }
  const addOrder = (order: Order) => {
    orders.value.push(order)
    initialized.value = true
  }
  const removeOrder = (order: Order) => {
    const index = orders.value.findIndex((o) => o.id === order.id)
    if (index === -1) return
    orders.value.splice(index, 1)
  }

  return { orders, count, initialized, loading, loadError, lastUpdated,
    addOrders, addOrder, removeOrder, fetchOrders }
})

function isOrder(value: unknown): value is Order {
  return typeof value === 'object' && value !== null &&
    'orderId' in value && typeof value.orderId === 'string' && value.orderId.length > 0 &&
    'customerId' in value && typeof value.customerId === 'string' &&
    'status' in value && typeof value.status === 'number' &&
    Number.isInteger(value.status) && value.status >= 0 && value.status <= 2 &&
    'updatedAtUnixSeconds' in value && typeof value.updatedAtUnixSeconds === 'number' &&
    Number.isFinite(value.updatedAtUnixSeconds) && value.updatedAtUnixSeconds > 0 &&
    'items' in value && Array.isArray(value.items) &&
    value.items.every((item: unknown) => typeof item === 'object' && item !== null &&
      'productId' in item && (typeof item.productId === 'string' || typeof item.productId === 'number') &&
      'quantity' in item && typeof item.quantity === 'number' && Number.isFinite(item.quantity) &&
      'price' in item && typeof item.price === 'number' && Number.isFinite(item.price))
}
