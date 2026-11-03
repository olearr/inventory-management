import { ref, computed, watch } from 'vue'

// Shared sidebar state (singleton pattern, same as useFilters)
const STORAGE_KEY = 'sidebar-collapsed'
const FULL_WIDTH = '248px'
const RAIL_WIDTH = '72px'

// Storage can be unavailable (private mode, blocked cookies), so every access is guarded
const readCollapsed = () => {
  try {
    return localStorage.getItem(STORAGE_KEY) === 'true'
  } catch {
    return false
  }
}

// User's choice for >= 1024px only; persisted
const collapsed = ref(readCollapsed())
// One flag for both the overlay (640-1023px) and the drawer (< 640px); derived from the breakpoint
const panelOpen = ref(false)
const isWide = ref(true) // >= 1024px
const isMedium = ref(true) // >= 640px

// full: 248px sidebar | rail: 72px icon-only | drawer: hidden, opened as a panel
const mode = computed(() => {
  if (isWide.value) return collapsed.value ? 'rail' : 'full'
  return isMedium.value ? 'rail' : 'drawer'
})

// Width the CONTENT must reserve. The open overlay/drawer panel floats above the content and
// never pushes it, so it does not count here (the panel has its own --sidebar-panel-w).
// The 640-1023px rail keeps its 72px; only the drawer reserves nothing.
const sidebarWidth = computed(() => {
  if (mode.value === 'full') return FULL_WIDTH
  if (mode.value === 'rail') return RAIL_WIDTH
  return '0px'
})

// True while the sidebar shows icons only (rail without an expanded overlay)
const isIconOnly = computed(() => mode.value === 'rail' && !panelOpen.value)

let initialised = false

// Called once: listeners live for the whole app lifetime, so guarding against a second
// registration is what prevents leaks when several components call useSidebar().
const init = () => {
  if (initialised || typeof window === 'undefined') return
  initialised = true

  const wideQuery = window.matchMedia('(min-width: 1024px)')
  const mediumQuery = window.matchMedia('(min-width: 640px)')
  const sync = () => {
    isWide.value = wideQuery.matches
    isMedium.value = mediumQuery.matches
    // A panel left open across a breakpoint change would be in the wrong layout
    panelOpen.value = false
  }
  sync()
  wideQuery.addEventListener('change', sync)
  mediumQuery.addEventListener('change', sync)

  // Existing rules (.app-main margin, .sidebar width) read --sidebar-w, so driving the variable
  // keeps them working without touching other files.
  watch(
    sidebarWidth,
    (width) => document.documentElement.style.setProperty('--sidebar-w', width),
    { immediate: true }
  )
}

export function useSidebar() {
  init()

  const toggleCollapsed = () => {
    collapsed.value = !collapsed.value
    try {
      localStorage.setItem(STORAGE_KEY, String(collapsed.value))
    } catch {
      // Persistence is optional; the in-memory state still works
    }
  }

  // At >= 1024px there is no panel (the sidebar is always visible), so opening is a no-op
  const openPanel = () => {
    if (!isWide.value) panelOpen.value = true
  }
  const closePanel = () => {
    panelOpen.value = false
  }
  const togglePanel = () => {
    if (panelOpen.value) closePanel()
    else openPanel()
  }

  return {
    collapsed,
    panelOpen,
    isWide,
    mode,
    sidebarWidth,
    isIconOnly,
    toggleCollapsed,
    openPanel,
    closePanel,
    togglePanel
  }
}
