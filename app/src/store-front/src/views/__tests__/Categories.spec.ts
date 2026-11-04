import { beforeEach, describe, expect, it } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import { useCartStore, useProductStore } from '@/stores'
import ProductListView from '../ProductListView.vue'

const products = Array.from({ length: 60 }, (_, index) => ({
  id: index + 1,
  name: `Product ${index + 1}`,
  price: 10,
  description: 'Demo sports equipment',
  image: '/tennis-racket.svg',
  category: index < 30 ? 'Tennis' : 'Table Tennis',
}))

beforeEach(() => { localStorage.clear() })

async function renderCatalog(url = '/') {
  const pinia = createPinia()
  setActivePinia(pinia)
  useProductStore().addProducts(products)
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/', component: ProductListView }],
  })
  await router.push(url)
  await router.isReady()
  const wrapper = mount(ProductListView, { global: { plugins: [pinia, router] } })
  return { wrapper, router }
}

describe('Catalog category browsing', () => {
  it('limits the initial grid and reveals the rest without losing products', async () => {
    const { wrapper } = await renderCatalog()
    expect(wrapper.findAll('.product-card')).toHaveLength(24)
    expect(wrapper.get('[role="status"]').text()).toBe('60 products')
    await wrapper.get('.load-more').trigger('click')
    expect(wrapper.findAll('.product-card')).toHaveLength(48)
    await wrapper.get('.load-more').trigger('click')
    expect(wrapper.findAll('.product-card')).toHaveLength(60)
    expect(wrapper.find('.load-more').exists()).toBe(false)
    wrapper.unmount()
  })

  it('filters exact categories, updates the URL, and restores all products', async () => {
    const { wrapper, router } = await renderCatalog('/?campaign=demo')
    const tennis = wrapper.findAll('.category-filters button').find(button => button.text() === 'Tennis 30')!
    await tennis.trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.query).toEqual({ campaign: 'demo', category: 'Tennis' })
    expect(tennis.attributes('aria-pressed')).toBe('true')
    expect(wrapper.get('[role="status"]').text()).toBe('30 products')
    expect(wrapper.findAll('.product-card .category').every(label => label.text() === 'Tennis')).toBe(true)
    await wrapper.get('.load-more').trigger('click')
    expect(wrapper.findAll('.product-card')).toHaveLength(30)
    await wrapper.get('.category-filters button').trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.query).toEqual({ campaign: 'demo' })
    expect(wrapper.findAll('.product-card')).toHaveLength(24)
    expect(wrapper.get('[role="status"]').text()).toBe('60 products')
    wrapper.unmount()
  })

  it('honors shared category links and supports adding filtered products to cart', async () => {
    const { wrapper } = await renderCatalog('/?category=Table%20Tennis')
    expect(wrapper.get('[role="status"]').text()).toBe('30 products')
    expect(wrapper.findAll('.product-card .category').every(label => label.text() === 'Table Tennis')).toBe(true)
    await wrapper.get('.product-controls button').trigger('click')
    expect(useCartStore().items[0]!.product.id).toBe(31)
    expect(useCartStore().count).toBe(1)
    wrapper.unmount()
  })

  it('shows an explicit empty result for an unknown category', async () => {
    const { wrapper } = await renderCatalog('/?category=Unknown')
    expect(wrapper.findAll('.product-card')).toHaveLength(0)
    expect(wrapper.text()).toContain('No products in this category.')
    wrapper.unmount()
  })
})
