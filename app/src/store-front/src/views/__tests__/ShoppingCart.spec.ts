import { beforeEach, afterEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import { useCartStore } from '@/stores'
import ShoppingCart from '../ShoppingCartView.vue'

beforeEach(() => {
  localStorage.clear()
  vi.spyOn(window, 'alert').mockImplementation(() => {})
})
afterEach(() => {
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
})

function renderCart() {
  const pinia = createPinia()
  setActivePinia(pinia)
  const cart = useCartStore()
  cart.addItem({ product: { id: 2, name: 'Court Pro Tennis Racket', price: 89.99 }, quantity: 2 })
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/', component: ShoppingCart }, { path: '/cart', component: ShoppingCart }],
  })
  return { cart, wrapper: mount(ShoppingCart, { global: { plugins: [pinia, router] } }) }
}

describe('Sports checkout', () => {
  it('submits the real order contract and clears the cart only on success', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(null, { status: 201 }))
    vi.stubGlobal('fetch', fetchMock)
    const { cart, wrapper } = renderCart()
    await wrapper.find('.checkout-button').trigger('click')
    await flushPromises()
    const [url, options] = fetchMock.mock.calls[0]!
    expect(url).toBe('/api/orders')
    const order = JSON.parse(options.body)
    expect(order.orderId).toMatch(/^\d{19}$/)
    expect(order.items).toEqual([{ productId: 2, quantity: 2, price: 89.99 }])
    expect(cart.count).toBe(0)
    expect(window.alert).toHaveBeenCalledWith('Order submitted successfully')
  })

  it('retains sports items when checkout is unavailable', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(null, { status: 503 })))
    const { cart, wrapper } = renderCart()
    await wrapper.find('.checkout-button').trigger('click')
    await flushPromises()
    expect(cart.count).toBe(2)
    expect(window.alert).toHaveBeenCalledWith('Error occurred while submitting order')
  })

  it('does not import pet items from the previous cart', () => {
    localStorage.setItem('cart', JSON.stringify([
      { product: { id: 1, name: 'Previous catalog item', price: 9.99 }, quantity: 1 },
    ]))
    setActivePinia(createPinia())
    expect(useCartStore().count).toBe(0)
  })
})
