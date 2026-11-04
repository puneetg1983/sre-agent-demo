import { afterEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import ProductFormView from '../ProductFormView.vue'

afterEach(() => { vi.unstubAllGlobals() })

async function renderForm(status = 200) {
  const pinia = createPinia()
  setActivePinia(pinia)
  const fetch = vi.fn().mockImplementation((url: string, init?: RequestInit) =>
    Promise.resolve(new Response(JSON.stringify(init?.body
      ? status === 200 ? { ...JSON.parse(String(init.body)), id: 211 } : { error: 'Catalog unavailable' }
      : { status: 'ok', capabilities: [] }), { status: init?.body ? status : 200 })))
  vi.stubGlobal('fetch', fetch)
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/product/:id', component: ProductFormView }],
  })
  await router.push('/product/add')
  await router.isReady()
  const wrapper = mount(ProductFormView, { global: { plugins: [pinia, router] } })
  await wrapper.get('#product-name').setValue('Test Racket')
  await wrapper.get('#product-price').setValue(10)
  await wrapper.get('#product-description').setValue('A sports product')
  await wrapper.get('#product-category').setValue('Tennis')
  return { wrapper, fetch }
}

describe('Product category editing', () => {
  it('includes the category when saving a product', async () => {
    const { wrapper, fetch } = await renderForm()
    await wrapper.get('.action-button button').trigger('click')
    await flushPromises()
    const save = fetch.mock.calls.find(call => call[1]?.method === 'POST')!
    expect(JSON.parse(String(save[1].body)).category).toBe('Tennis')
    wrapper.unmount()
  })

  it('validates empty categories before sending a write', async () => {
    const { wrapper, fetch } = await renderForm()
    await wrapper.get('#product-category').setValue(' ')
    await wrapper.get('.action-button button').trigger('click')
    expect(wrapper.get('.validation-errors').text()).toContain('category')
    expect(fetch.mock.calls.some(call => call[1]?.method === 'POST')).toBe(false)
    wrapper.unmount()
  })

  it('does not present a failed SQL-backed save as success', async () => {
    const { wrapper } = await renderForm(503)
    await wrapper.get('.action-button button').trigger('click')
    await flushPromises()
    expect(wrapper.get('[role="status"]').text()).toContain('Error occurred while saving product.')
    wrapper.unmount()
  })
})
