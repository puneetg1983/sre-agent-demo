import { JSDOM } from 'jsdom'

Object.defineProperty(globalThis, 'localStorage', {
  value: new JSDOM('', { url: 'http://localhost' }).window.localStorage,
  configurable: true,
})
