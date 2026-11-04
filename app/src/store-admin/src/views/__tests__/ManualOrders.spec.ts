import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { flushPromises, mount, RouterLinkStub } from '@vue/test-utils'
import App from '../../App.vue'
import OrderDetailView from '../OrderDetailView.vue'
import { useOrderStore } from '@/stores'

const mocks = vi.hoisted(() => ({ push: vi.fn() }))
vi.mock('vue-router', async () => ({
  ...await vi.importActual<typeof import('vue-router')>('vue-router'),
  useRoute: () => ({ params: { id: 'manual-1' } }),
  useRouter: () => ({ push: mocks.push }),
}))

const pending = {
  orderId: 'manual-1', customerId: 'manual', status: 0,
  updatedAtUnixSeconds: 1793772000,
  items: [{ productId: 1, quantity: 1, price: 10 }],
}

beforeEach(() => {
  setActivePinia(createPinia())
  vi.spyOn(window, 'alert').mockImplementation(() => {})
  mocks.push.mockReset()
})
afterEach(() => {
  vi.useRealTimers()
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
})

const renderDetail = () => mount(OrderDetailView, {
  global: { stubs: { RouterLink: RouterLinkStub } },
})

describe('Manual order processing', () => {
  it('only changes displayed status after completion succeeds and retains completed history', async () => {
    const fetch = vi.fn()
      .mockResolvedValueOnce(new Response(null, { status: 202 }))
      .mockResolvedValueOnce(new Response(JSON.stringify([{ ...pending, status: 1 }])))
    vi.stubGlobal('fetch', fetch)
    const store = useOrderStore()
    store.addOrders([{ ...pending }])
    const wrapper = renderDetail()
    await wrapper.find('button').trigger('click')
    await flushPromises()
    expect(store.orders).toHaveLength(1)
    expect(store.orders[0]!.status).toBe(1)
    expect(JSON.parse(fetch.mock.calls[0]![1].body).status).toBe(1)
    expect(mocks.push).toHaveBeenCalledWith('/')
    wrapper.unmount()
  })

  it('does not silently mark an order completed when the backend fails', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('{}', { status: 500 })))
    const store = useOrderStore()
    store.addOrders([{ ...pending }])
    const wrapper = renderDetail()
    await wrapper.find('button').trigger('click')
    await flushPromises()
    expect(store.orders[0]!.status).toBe(0)
    expect(window.alert).toHaveBeenCalledWith('Error occurred while processing order')
    expect(mocks.push).not.toHaveBeenCalled()
    wrapper.unmount()
  })

  it('refreshes history every five seconds and stops when the app unmounts', async () => {
    vi.useFakeTimers()
    const fetch = vi.fn().mockImplementation(() => Promise.resolve(new Response('[]')))
    vi.stubGlobal('fetch', fetch)
    const wrapper = mount(App, {
      global: { stubs: { TopNav: true, RouterView: true } },
    })
    await flushPromises()
    const historyCalls = () => fetch.mock.calls.filter(call => call[0] === '/api/makeline/order/recent').length
    expect(historyCalls()).toBe(1)
    await vi.advanceTimersByTimeAsync(5000)
    expect(historyCalls()).toBe(2)
    wrapper.unmount()
    await vi.advanceTimersByTimeAsync(10000)
    expect(historyCalls()).toBe(2)
  })
})
