import { afterEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import PickupAvailability from '../PickupAvailability.vue'

afterEach(() => {
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
})

const available = { productId: 2, availableQuantity: 12, storeName: 'Contoso Central', readyInMinutes: 30 }

describe('SQL pickup availability', () => {
  it('loads real availability independently of the cart', async () => {
    const fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify(available)))
    vi.stubGlobal('fetch', fetch)
    const wrapper = mount(PickupAvailability, { props: { productId: 2 } })
    expect(wrapper.text()).toContain('Checking pickup availability')
    await flushPromises()
    expect(fetch.mock.calls[0]![0]).toBe('/api/pickup/2')
    expect(wrapper.text()).toContain('12 available')
    expect(wrapper.text()).toContain('Contoso Central')
    wrapper.unmount()
  })

  it('shows an explicit failure, never invented inventory, and can retry', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {})
    const fetch = vi.fn()
      .mockResolvedValueOnce(new Response('{}', { status: 503 }))
      .mockResolvedValueOnce(new Response(JSON.stringify(available)))
    vi.stubGlobal('fetch', fetch)
    const wrapper = mount(PickupAvailability, { props: { productId: 2 } })
    await flushPromises()
    expect(wrapper.find('[role="alert"]').text()).toContain('Shopping and checkout still work')
    expect(wrapper.text()).not.toContain('available at')
    await wrapper.find('button').trigger('click')
    await flushPromises()
    expect(wrapper.find('[role="alert"]').exists()).toBe(false)
    expect(wrapper.text()).toContain('12 available')
    wrapper.unmount()
  })

  it('rejects malformed or wrong-product data', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {})
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({ ...available, productId: 1 }))))
    const wrapper = mount(PickupAvailability, { props: { productId: 2 } })
    await flushPromises()
    expect(wrapper.find('[role="alert"]').exists()).toBe(true)
    expect(wrapper.text()).not.toContain('12 available')
    wrapper.unmount()
  })

  it('aborts stale requests when the product changes', async () => {
    const fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify(available)))
    vi.stubGlobal('fetch', fetch)
    const wrapper = mount(PickupAvailability, { props: { productId: 2 } })
    await flushPromises()
    const signal = fetch.mock.calls[0]![1].signal as AbortSignal
    fetch.mockResolvedValue(new Response(JSON.stringify({ ...available, productId: 1 })))
    await wrapper.setProps({ productId: 1 })
    await flushPromises()
    expect(signal.aborted).toBe(true)
    expect(fetch.mock.calls[1]![0]).toBe('/api/pickup/1')
    expect(wrapper.find('[role="alert"]').exists()).toBe(false)
    wrapper.unmount()
  })
})
