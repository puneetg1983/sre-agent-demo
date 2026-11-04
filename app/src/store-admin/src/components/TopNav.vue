<template>
  <nav>
    <div class="logo">
      <router-link to="/">
        <img src="/contoso-sports-store-logo.svg" alt="Contoso Sports Store Logo" />
      </router-link>
      Admin Portal
    </div>
    <ul id="admin-navigation" class="nav-links" :class="{ 'nav-links--open': isNavOpen }">
      <li><router-link to="/orders" @click="closeNav">Orders</router-link></li>
      <li><router-link to="/products" @click="closeNav">Products</router-link></li>
    </ul>
    <button class="hamburger" aria-label="Toggle navigation" aria-controls="admin-navigation"
      :aria-expanded="isNavOpen" @click="toggleNav">
      <span class="hamburger-icon"></span>
    </button>
  </nav>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const isNavOpen = ref(false)

function toggleNav(): void {
  isNavOpen.value = !isNavOpen.value
}

function closeNav(): void {
  isNavOpen.value = false
}
</script>

<style scoped>
nav {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background-color: var(--cp-surface);
  color: var(--cp-text);
  border-bottom: 1px solid var(--cp-border);
  padding: 8px 24px;
  min-height: 80px;
  box-sizing: border-box;
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  font-size: 1.125rem;
  font-weight: 600;
}

nav img {
  width: 64px;
  height: 64px;
  object-fit: contain;
  align-self: center;
}

.nav-links {
  display: flex;
  list-style: none;
  gap: 8px;
}

.nav-links li {
  margin: 0;
}

.nav-links a {
  display: block;
  color: var(--cp-text-muted);
  padding: 10px 16px;
  border-radius: 0.625rem;
}

.nav-links a:hover,
.nav-links .router-link-active {
  background: var(--cp-accent-soft);
  color: var(--cp-accent);
}

.logo {
  display: flex;
  align-items: center;
  gap: 12px;
}

.hamburger {
  display: none;
  background: none;
  border: none;
  cursor: pointer;
  padding: 0;
  margin: 0;
  width: 40px;
  height: 40px;
}

.hamburger-icon {
  display: block;
  width: 20px;
  height: 2px;
  background-color: var(--cp-text);
  margin: 0 auto;
  position: relative;
  top: 50%;
  transform: translateY(-50%);
}

.hamburger-icon::before,
.hamburger-icon::after {
  content: '';
  display: block;
  width: 20px;
  height: 2px;
  background-color: var(--cp-text);
  position: absolute;
  left: 0;
}

.hamburger-icon::before {
  top: -6px;
}

.hamburger-icon::after {
  bottom: -6px;
}

@media (max-width: 768px) {
  .nav-links {
    display: none;
    position: absolute;
    top: 100%;
    left: 0;
    right: 0;
    background-color: var(--cp-surface);
    border-bottom: 1px solid var(--cp-border);
    padding: 1rem;
  }

  .nav-links--open {
    display: block;
  }

  .nav-links--open li {
    padding: 0.5rem 0;
  }

  .hamburger {
    display: block;
  }
}
</style>
