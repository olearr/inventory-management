<template>
  <!-- Scrim sits behind the open overlay/drawer and closes it on click (mouse users; keyboard uses Escape) -->
  <div v-if="panelOpen" class="sidebar-scrim" aria-hidden="true" @click="closePanel" />

  <!-- inert keeps the off-screen drawer out of the tab order and the accessibility tree while closed -->
  <aside
    class="sidebar"
    :class="{
      'is-rail': isIconOnly,
      'is-panel': mode === 'drawer' || panelOpen,
      'is-drawer-closed': mode === 'drawer' && !panelOpen
    }"
    :inert="mode === 'drawer' && !panelOpen"
  >
    <div class="brand">
      <div class="brand-mark" aria-hidden="true">CC</div>
      <div class="brand-text">
        <span class="brand-name">{{ t('nav.companyName') }}</span>
        <span class="brand-subtitle">{{ t('nav.subtitle') }}</span>
      </div>
      <button
        ref="toggleButton"
        type="button"
        class="sidebar-toggle"
        :aria-label="toggleLabel"
        :title="toggleLabel"
        :aria-expanded="mode === 'drawer' ? undefined : String(expanded)"
        @click="onToggle"
      >
        <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <path v-if="mode === 'drawer'" d="M4.5 4.5l9 9M13.5 4.5l-9 9" />
          <path v-else-if="expanded" d="M11 4.5L6.5 9l4.5 4.5" />
          <path v-else d="M7 4.5L11.5 9 7 13.5" />
        </svg>
      </button>
    </div>

    <nav class="sidebar-nav" :aria-label="t('nav.companyName')">
      <ul>
        <li v-for="item in items" :key="item.to">
          <router-link
            :to="item.to"
            class="nav-link"
            :class="{ active: route.path === item.to }"
            :aria-current="route.path === item.to ? 'page' : undefined"
            :title="isIconOnly ? t(item.label) : undefined"
            :aria-label="isIconOnly ? t(item.label) : undefined"
          >
            <svg
              class="nav-icon"
              width="20"
              height="20"
              viewBox="0 0 20 20"
              fill="none"
              stroke="currentColor"
              stroke-width="1.75"
              stroke-linecap="round"
              stroke-linejoin="round"
              aria-hidden="true"
              v-html="item.icon"
            />
            <span class="nav-label">{{ t(item.label) }}</span>
          </router-link>
        </li>
      </ul>
    </nav>

    <div class="sidebar-footer">
      <slot name="footer" />
    </div>
  </aside>
</template>

<script setup>
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from '../composables/useI18n'
import { useSidebar } from '../composables/useSidebar'

const route = useRoute()
const { t } = useI18n()
const { collapsed, panelOpen, isWide, mode, isIconOnly, toggleCollapsed, togglePanel, closePanel } = useSidebar()

const toggleButton = ref(null)

// "Expanded" means labels are visible: the full desktop sidebar or an open overlay/drawer
const expanded = computed(() => (isWide.value ? !collapsed.value : panelOpen.value))

const toggleLabel = computed(() => {
  if (mode.value === 'drawer') return t('nav.closeMenu')
  return expanded.value ? t('nav.collapseSidebar') : t('nav.expandSidebar')
})

// Desktop persists a collapse preference; smaller screens only open/close the transient panel
const onToggle = () => {
  if (isWide.value) toggleCollapsed()
  else togglePanel()
}

// Escape closes the transient panel. Registered on window so it works wherever focus is,
// and removed on unmount so remounting (e.g. hot reload) does not stack listeners.
const onKeydown = (event) => {
  if (event.key === 'Escape' && panelOpen.value) closePanel()
}
onMounted(() => window.addEventListener('keydown', onKeydown))
onUnmounted(() => window.removeEventListener('keydown', onKeydown))

// Choosing a route must dismiss the panel, otherwise it would cover the new page
watch(() => route.path, closePanel)

// Drawer focus handling: move focus into the drawer on open, back to the top bar's menu
// button on close. Waits a tick because the drawer is inert until the class state renders.
// The overlay needs none of this: its toggle is the same element that stays focused.
watch(panelOpen, async (open) => {
  if (mode.value !== 'drawer') return
  await nextTick()
  if (open) toggleButton.value?.focus()
  else document.getElementById('mobile-menu-button')?.focus()
})

// Icon markup is static, hard-coded SVG path data (never user input), so v-html is safe
// and keeps the seven icons in one data array instead of seven near-identical blocks.
const items = [
  {
    to: '/',
    label: 'nav.overview',
    icon: '<rect x="3" y="3" width="5.5" height="5.5" rx="1"/><rect x="11.5" y="3" width="5.5" height="5.5" rx="1"/><rect x="3" y="11.5" width="5.5" height="5.5" rx="1"/><rect x="11.5" y="11.5" width="5.5" height="5.5" rx="1"/>'
  },
  {
    to: '/inventory',
    label: 'nav.inventory',
    icon: '<path d="M10 2.5l6.5 3.5v8L10 17.5 3.5 14V6L10 2.5z"/><path d="M3.5 6L10 9.5 16.5 6"/><path d="M10 9.5v8"/>'
  },
  {
    to: '/orders',
    label: 'nav.orders',
    icon: '<rect x="4" y="4" width="12" height="13.5" rx="1.5"/><path d="M7.5 4V3a.5.5 0 01.5-.5h4a.5.5 0 01.5.5v1"/><path d="M7 9h6M7 12h6M7 15h3.5"/>'
  },
  {
    to: '/spending',
    label: 'nav.finance',
    icon: '<rect x="2.5" y="5.5" width="15" height="9" rx="1.5"/><circle cx="10" cy="10" r="2.25"/><path d="M5.5 8v4M14.5 8v4"/>'
  },
  {
    to: '/demand',
    label: 'nav.demandForecast',
    icon: '<path d="M3 3v14h14"/><path d="M6 12.5l3.5-3.5 2.5 2.5L17 6.5"/><path d="M13.5 6.5H17V10"/>'
  },
  {
    to: '/restocking',
    label: 'nav.restocking',
    icon: '<path d="M16.5 9a6.5 6.5 0 00-11.6-3.5L3.5 7"/><path d="M3.5 3.5V7H7"/><path d="M3.5 11a6.5 6.5 0 0011.6 3.5l1.4-1.5"/><path d="M16.5 16.5V13H13"/>'
  },
  {
    to: '/reports',
    label: 'nav.reports',
    icon: '<path d="M5 2.5h6.5L16 7v10a.5.5 0 01-.5.5h-10.5a.5.5 0 01-.5-.5V3a.5.5 0 01.5-.5z"/><path d="M11.5 2.5V7H16"/><path d="M7.5 10.5h5M7.5 13.5h5"/>'
  }
]
</script>

<style scoped>
.sidebar {
  position: fixed;
  inset: 0 auto 0 0;
  /* --sidebar-w is set by useSidebar (248px full, 72px rail, 0px drawer) */
  width: var(--sidebar-w);
  z-index: 100;
  display: flex;
  flex-direction: column;
  background: var(--ink-900);
  transition: width 200ms ease, transform 200ms ease;
}

/* Overlay (640-1023px) and drawer (< 640px): the panel uses its own fixed width and floats
   above the content. --sidebar-w stays the content's reserved width and is not used here. */
.sidebar.is-panel {
  width: var(--sidebar-panel-w);
  z-index: 160;
}

.sidebar.is-drawer-closed {
  transform: translateX(-100%);
}

.sidebar-scrim {
  position: fixed;
  inset: 0;
  z-index: 150;
  background: rgba(15, 23, 42, 0.45);
}

.sidebar-toggle {
  margin-left: auto;
  flex-shrink: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: var(--radius-control);
  color: var(--ink-400);
  cursor: pointer;
  transition: color 150ms ease, background-color 150ms ease;
}

.sidebar-toggle:hover {
  background: var(--ink-800);
  color: #e2e8f0;
}

.sidebar-toggle:focus-visible {
  outline: 2px solid var(--accent-on-dark);
  outline-offset: 2px;
}

/* Rail: labels stay in the DOM for screen readers, so they are clipped rather than display:none */
.is-rail .brand-text,
.is-rail .nav-label {
  position: absolute;
  width: 1px;
  height: 1px;
  margin: -1px;
  overflow: hidden;
  clip-path: inset(50%);
  white-space: nowrap;
}

/* Mark above the toggle, both centred in the 72px rail */
.is-rail .brand {
  flex-direction: column;
  padding: 1.25rem 0 0.5rem;
  gap: 0.75rem;
}

.is-rail .sidebar-toggle {
  margin-left: 0;
}

/* 48px nav track - 20px icon leaves 14px each side */
.is-rail .nav-link {
  justify-content: center;
  padding: 0.625rem 0;
  gap: 0;
}

.brand {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 1.25rem 1rem 1rem;
  flex-shrink: 0;
}

.brand-mark {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  background: var(--accent-on-dark);
  color: var(--ink-900);
  font-weight: 700;
  font-size: 0.875rem;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

/* min-width: 0 lets long (e.g. Japanese) names truncate instead of widening the sidebar */
.brand-text {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.brand-name {
  color: #ffffff;
  font-weight: 600;
  font-size: 0.9375rem;
  line-height: 1.3;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* Subtitle may wrap to two lines rather than being cut off */
.brand-subtitle {
  color: var(--ink-400);
  font-size: 0.75rem;
  line-height: 1.3;
}

/* The nav takes the free space and scrolls on short viewports so the footer stays pinned */
.sidebar-nav {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 0.5rem 0.75rem;
}

.sidebar-nav ul {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.nav-link {
  position: relative;
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.625rem 0.75rem;
  border-radius: var(--radius-control);
  color: var(--ink-400);
  font-weight: 500;
  font-size: 0.9rem;
  text-decoration: none;
  transition: color 150ms ease, background-color 150ms ease;
}

.nav-link:hover {
  background: var(--ink-800);
  color: #e2e8f0;
}

.nav-link.active {
  color: var(--accent-on-dark);
  background: rgba(94, 234, 212, 0.10);
}

/* Left marker bar makes the active page recognisable without relying on colour alone */
.nav-link.active::before {
  content: '';
  position: absolute;
  left: -0.75rem;
  top: 0.5rem;
  bottom: 0.5rem;
  width: 3px;
  border-radius: 0 3px 3px 0;
  background: var(--accent-on-dark);
}

.nav-link:focus-visible {
  outline: 2px solid var(--accent-on-dark);
  outline-offset: 2px;
}

.nav-icon {
  flex-shrink: 0;
}

.nav-label {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sidebar-footer {
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 0.75rem;
  border-top: 1px solid var(--ink-800);
}

@media (prefers-reduced-motion: reduce) {
  .nav-link,
  .sidebar,
  .sidebar-toggle {
    transition: none;
  }
}
</style>
