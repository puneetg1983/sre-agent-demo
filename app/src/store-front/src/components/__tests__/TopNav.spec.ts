import { describe, it, expect } from 'vitest'
import { mount, RouterLinkStub } from '@vue/test-utils'
import { createPinia } from 'pinia'
import TopNav from '../TopNav.vue'

function renderNav() {
  return mount(TopNav, {
    global: { plugins: [createPinia()], stubs: { RouterLink: RouterLinkStub } },
  })
}

describe('Sports store navigation', () => {
  it('renders the sports branding', () => {
    const wrapper = renderNav()
    expect(wrapper.find('.logo img').attributes('src')).toBe('/contoso-sports-store-logo.svg')
    expect(wrapper.find('.logo img').attributes('alt')).toBe('Contoso Sports Store Logo')
  })

  it('keeps products and shopping-cart navigation', () => {
    const wrapper = renderNav()
    const links = wrapper.findAllComponents(RouterLinkStub)
    expect(wrapper.findAll('.nav-links li')).toHaveLength(2)
    expect(links[1]?.props('to')).toBe('/')
    expect(links[2]?.props('to')).toBe('/cart')
    expect(links[2]?.text()).toContain('Cart (')
  })

  it('toggles the existing mobile menu', async () => {
    const wrapper = renderNav()
    await wrapper.find('.hamburger').trigger('click')
    expect(wrapper.find('.nav-links').classes()).toContain('nav-links--open')
    await wrapper.find('.hamburger').trigger('click')
    expect(wrapper.find('.nav-links').classes()).not.toContain('nav-links--open')
  })
})
