import { describe, it, expect } from 'vitest'

import { mount, RouterLinkStub } from '@vue/test-utils'
import TopNav from '../TopNav.vue'

function renderNav() {
  return mount(TopNav, { global: { stubs: { RouterLink: RouterLinkStub } } })
}

describe('TopNav', () => {
  it('renders properly', () => {
    const wrapper = renderNav()
    expect(wrapper.find('nav').exists()).toBe(true)
    expect(wrapper.find('.logo').exists()).toBe(true)
    expect(wrapper.find('.logo').text()).toContain('Admin Portal')
    expect(wrapper.find('.logo img').attributes('src')).toBe('/contoso-sports-store-logo.svg')
  })

  it('contains navigation links', () => {
    const wrapper = renderNav()
    expect(wrapper.find('.nav-links').exists()).toBe(true)
    expect(wrapper.findAll('.nav-links li').length).toBe(2)
    const links = wrapper.findAllComponents(RouterLinkStub)
    expect(links.at(1)?.props('to')).toBe('/orders')
    expect(links.at(2)?.props('to')).toBe('/products')
  })

  it('toggles mobile menu when hamburger is clicked', async () => {
    const wrapper = renderNav()
    expect(wrapper.find('.nav-links').classes()).not.toContain('nav-links--open')

    await wrapper.find('.hamburger').trigger('click')
    expect(wrapper.find('.nav-links').classes()).toContain('nav-links--open')

    await wrapper.find('.hamburger').trigger('click')
    expect(wrapper.find('.nav-links').classes()).not.toContain('nav-links--open')
  })
})
