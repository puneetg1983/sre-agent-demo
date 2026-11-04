import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { flushPromises, mount, RouterLinkStub } from '@vue/test-utils'
import { useOrderStore } from '@/stores'
import OrderListView from '../OrderListView.vue'

const order = (id: number, status = 2) => ({
  orderId: String(id),
  customerId: 'customer',
  status,
  updatedAtUnixSeconds: 1793772000 - id,
  items: [{ productId: 1, quantity: 2, price: 10 }],
})

beforeEach(() => {
  setActivePinia(createPinia())
})
afterEach(() => {
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
})

function renderOrders() {
  return mount(OrderListView, { global: { stubs: { RouterLink: RouterLinkStub } } })
}

describe('Recent order history', () => {
  it('displays exactly 15 records across statuses in the supplied database order', async () => {
    const records = Array.from({ length: 15 }, (_, index) => order(index, index === 0 ? 0 : 2))
    const fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify(records)))
    vi.stubGlobal('fetch', fetch)
    const store = useOrderStore()
    await store.fetchOrders()
    const wrapper = renderOrders()
    expect(fetch.mock.calls[0]![0]).toBe('/api/makeline/order/recent')
    expect(wrapper.findAll('tbody tr')).toHaveLength(15)
    expect(wrapper.text()).toContain('Latest 15 orders')
    expect(wrapper.find('tbody tr').text()).toContain('Pending')
    expect(wrapper.findAll('tbody tr')[1]!.text()).toContain('Completed')
    expect(store.orders.map(o => o.orderId)).toEqual(records.map(o => o.orderId))
    wrapper.unmount()
  })

  it('replaces history when refreshed rather than appending duplicates', async () => {
    vi.stubGlobal('fetch', vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify([order(1, 0)])))
      .mockResolvedValueOnce(new Response(JSON.stringify([order(1, 1)]))))
    const store = useOrderStore()
    await store.fetchOrders()
    const wrapper = renderOrders()
    await wrapper.find('button').trigger('click')
    await flushPromises()
    expect(store.orders).toHaveLength(1)
    expect(wrapper.find('tbody tr').text()).toContain('Completed')
    wrapper.unmount()
  })

  it('never presents a failed initial read as an empty order list', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {})
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('{}', { status: 500 })))
    await useOrderStore().fetchOrders()
    const wrapper = renderOrders()
    expect(wrapper.find('[role="alert"]').text()).toContain('Order history unavailable')
    expect(wrapper.text()).not.toContain('No orders available')
    wrapper.unmount()
  })

  it('marks cached history stale on failure and clears the error after recovery', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {})
    vi.stubGlobal('fetch', vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify([order(1)])))
      .mockResolvedValueOnce(new Response('{}', { status: 500 }))
      .mockResolvedValueOnce(new Response(JSON.stringify([order(2)]))))
    const store = useOrderStore()
    await store.fetchOrders()
    const lastSuccess = store.lastUpdated
    await store.fetchOrders()
    const wrapper = renderOrders()
    expect(wrapper.find('[role="alert"]').text()).toContain('not live data')
    expect(wrapper.findAll('tbody tr')).toHaveLength(1)
    expect(store.lastUpdated).toBe(lastSuccess)
    await store.fetchOrders()
    expect(store.loadError).toBeNull()
    expect(store.orders[0]!.orderId).toBe('2')
    wrapper.unmount()
  })

  it('distinguishes a successful empty result from a failure', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('[]')))
    await useOrderStore().fetchOrders()
    const wrapper = renderOrders()
    expect(wrapper.text()).toContain('No orders available')
    expect(wrapper.find('[role="alert"]').exists()).toBe(false)
    wrapper.unmount()
  })

  it.each([
    '{}',
    JSON.stringify([{}]),
    JSON.stringify(Array.from({ length: 16 }, (_, index) => order(index))),
  ])('rejects malformed or oversized history responses: %s', async (body) => {
    vi.spyOn(console, 'error').mockImplementation(() => {})
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(body)))
    const store = useOrderStore()
    await store.fetchOrders()
    expect(store.loadError).not.toBeNull()
    expect(store.orders).toHaveLength(0)
  })
})
