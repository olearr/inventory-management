<template>
  <div class="app">
    <SidebarNav>
      <template #footer>
        <LanguageSwitcher />
        <ProfileMenu
          @show-profile-details="showProfileDetails = true"
          @show-tasks="showTasks = true"
        />
      </template>
    </SidebarNav>
    <div class="app-main">
      <!-- Only visible below 640px, where the sidebar is a drawer opened from here -->
      <header class="mobile-bar">
        <button
          id="mobile-menu-button"
          type="button"
          class="mobile-bar-button"
          :aria-label="t('nav.openMenu')"
          :aria-expanded="String(panelOpen)"
          @click="togglePanel"
        >
          <svg width="22" height="22" viewBox="0 0 22 22" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" aria-hidden="true">
            <path d="M3.5 6h15M3.5 11h15M3.5 16h15" />
          </svg>
        </button>
        <div class="mobile-bar-mark" aria-hidden="true">CC</div>
      </header>
      <FilterBar />
      <main class="main-content">
        <router-view />
      </main>
    </div>

    <ProfileDetailsModal
      :is-open="showProfileDetails"
      @close="showProfileDetails = false"
    />

    <TasksModal
      :is-open="showTasks"
      :tasks="tasks"
      @close="showTasks = false"
      @add-task="addTask"
      @delete-task="deleteTask"
      @toggle-task="toggleTask"
    />
  </div>
</template>

<script>
import { ref, onMounted, computed } from 'vue'
import { api } from './api'
import { useAuth } from './composables/useAuth'
import { useI18n } from './composables/useI18n'
import FilterBar from './components/FilterBar.vue'
import ProfileMenu from './components/ProfileMenu.vue'
import ProfileDetailsModal from './components/ProfileDetailsModal.vue'
import TasksModal from './components/TasksModal.vue'
import LanguageSwitcher from './components/LanguageSwitcher.vue'
import SidebarNav from './components/SidebarNav.vue'
import { useSidebar } from './composables/useSidebar'

export default {
  name: 'App',
  components: {
    FilterBar,
    ProfileMenu,
    ProfileDetailsModal,
    TasksModal,
    LanguageSwitcher,
    SidebarNav
  },
  setup() {
    const { currentUser } = useAuth()
    const { t } = useI18n()
    const { panelOpen, togglePanel } = useSidebar()
    const showProfileDetails = ref(false)
    const showTasks = ref(false)
    const apiTasks = ref([])

    // Merge mock tasks from currentUser with API tasks
    const tasks = computed(() => {
      return [...currentUser.value.tasks, ...apiTasks.value]
    })

    const loadTasks = async () => {
      try {
        apiTasks.value = await api.getTasks()
      } catch (err) {
        console.error('Failed to load tasks:', err)
      }
    }

    const addTask = async (taskData) => {
      try {
        const newTask = await api.createTask(taskData)
        // Add new task to the beginning of the array
        apiTasks.value.unshift(newTask)
      } catch (err) {
        console.error('Failed to add task:', err)
      }
    }

    const deleteTask = async (taskId) => {
      try {
        // Check if it's a mock task (from currentUser)
        const isMockTask = currentUser.value.tasks.some(t => t.id === taskId)

        if (isMockTask) {
          // Remove from mock tasks
          const index = currentUser.value.tasks.findIndex(t => t.id === taskId)
          if (index !== -1) {
            currentUser.value.tasks.splice(index, 1)
          }
        } else {
          // Remove from API tasks
          await api.deleteTask(taskId)
          apiTasks.value = apiTasks.value.filter(t => t.id !== taskId)
        }
      } catch (err) {
        console.error('Failed to delete task:', err)
      }
    }

    const toggleTask = async (taskId) => {
      try {
        // Check if it's a mock task (from currentUser)
        const mockTask = currentUser.value.tasks.find(t => t.id === taskId)

        if (mockTask) {
          // Toggle mock task status
          mockTask.status = mockTask.status === 'pending' ? 'completed' : 'pending'
        } else {
          // Toggle API task
          const updatedTask = await api.toggleTask(taskId)
          const index = apiTasks.value.findIndex(t => t.id === taskId)
          if (index !== -1) {
            apiTasks.value[index] = updatedTask
          }
        }
      } catch (err) {
        console.error('Failed to toggle task:', err)
      }
    }

    onMounted(loadTasks)

    return {
      t,
      panelOpen,
      togglePanel,
      showProfileDetails,
      showTasks,
      tasks,
      addTask,
      deleteTask,
      toggleTask
    }
  }
}
</script>

<style>
:root {
  --ink-900: #0f172a;
  --ink-800: #1e293b;
  --ink-700: #334155;
  --ink-500: #64748b;
  --ink-400: #94a3b8;
  --canvas: #f1f5f9;
  --surface: #ffffff;
  --surface-muted: #f8fafc;
  --line: #e2e8f0;
  --line-strong: #cbd5e1;
  --accent: #0f766e;
  --accent-strong: #115e59;
  --accent-soft: #f0fdfa;
  --accent-line: #99f6e4;
  --accent-on-dark: #5eead4;
  --radius-card: 12px;
  --radius-control: 8px;
  --radius-badge: 6px;
  /* --sidebar-w is the width the CONTENT reserves; useSidebar overwrites it at runtime
     (248px full, 72px rail, 0px drawer). This value is only the pre-JS fallback. */
  --sidebar-w: 248px;
  /* Width of the sidebar when it floats as overlay/drawer; independent of --sidebar-w */
  --sidebar-panel-w: 248px;
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Hiragino Sans', 'Yu Gothic UI', 'Noto Sans JP', sans-serif;
  background: var(--canvas);
  color: var(--ink-900);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

.app {
  min-height: 100vh;
}

/* min-width: 0 stops wide tables from stretching the content column past the viewport */
.app-main {
  margin-left: var(--sidebar-w);
  min-width: 0;
  min-height: 100vh;
  transition: margin-left 200ms ease;
}

/* overflow-x: auto keeps wide, unwrapped tables (e.g. Inventory, Overview) scrolling inside the
   content area instead of stretching the whole page sideways on rail and drawer widths */
.main-content {
  max-width: 1440px;
  margin: 0 auto;
  padding: 1.5rem 2rem;
  overflow-x: auto;
}

.mobile-bar {
  display: none;
}

/* Below 640px the sidebar is an off-canvas drawer: no left margin, a sticky 56px bar instead */
@media (max-width: 639px) {
  .app-main {
    margin-left: 0;
  }

  .mobile-bar {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    height: 56px;
    padding: 0 0.75rem;
    background: var(--ink-900);
    position: sticky;
    top: 0;
    /* Above the filter bar (90), below the sidebar (100) and its scrim (150) */
    z-index: 95;
  }

  .main-content {
    padding: 1rem;
  }
}

.mobile-bar-button {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  border-radius: var(--radius-control);
  color: #e2e8f0;
  cursor: pointer;
}

.mobile-bar-button:hover {
  background: var(--ink-800);
}

.mobile-bar-button:focus-visible {
  outline: 2px solid var(--accent-on-dark);
  outline-offset: 2px;
}

.mobile-bar-mark {
  width: 32px;
  height: 32px;
  border-radius: 9px;
  background: var(--accent-on-dark);
  color: var(--ink-900);
  font-weight: 700;
  font-size: 0.8125rem;
  display: flex;
  align-items: center;
  justify-content: center;
}

@media (prefers-reduced-motion: reduce) {
  .app-main {
    transition: none;
  }
}

.page-header {
  margin-bottom: 1.5rem;
}

.page-header h2 {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--ink-900);
  margin-bottom: 0.375rem;
  letter-spacing: -0.02em;
}

.page-header p {
  color: var(--ink-500);
  font-size: 0.938rem;
}

.stats-grid {
  display: grid;
  /* 240px so that four cards fit in one row next to the 248px sidebar at 1440px wide */
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 1.25rem;
  margin-bottom: 1.5rem;
}

.stat-card {
  background: var(--surface);
  padding: 1.25rem;
  border-radius: var(--radius-card);
  border: 1px solid var(--line);
}

.stat-label {
  color: var(--ink-500);
  font-size: 0.8125rem;
  font-weight: 500;
  margin-bottom: 0.625rem;
}

.stat-value {
  font-size: 1.875rem;
  font-weight: 700;
  color: var(--ink-900);
  letter-spacing: -0.025em;
  font-variant-numeric: tabular-nums;
}

.stat-card.warning .stat-value {
  color: #ea580c;
}

.stat-card.success .stat-value {
  color: #059669;
}

.stat-card.danger .stat-value {
  color: #dc2626;
}

.stat-card.info .stat-value {
  color: #2563eb;
}

/* Brand colour for figures that are not a status (blue stays reserved for "info") */
.stat-card.accent .stat-value {
  color: var(--accent);
}

.card {
  background: var(--surface);
  border-radius: var(--radius-card);
  padding: 1.25rem;
  border: 1px solid var(--line);
  margin-bottom: 1.25rem;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
  padding-bottom: 0.875rem;
  border-bottom: 1px solid var(--line);
}

.card-title {
  font-size: 1rem;
  font-weight: 600;
  color: var(--ink-900);
  letter-spacing: -0.025em;
}

.table-container {
  overflow-x: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
}

thead {
  background: var(--surface-muted);
  border-top: 1px solid var(--line);
  border-bottom: 1px solid var(--line);
}

th {
  text-align: left;
  padding: 0.5rem 0.75rem;
  font-weight: 600;
  color: var(--ink-500);
  font-size: 0.8125rem;
}

td {
  padding: 0.5rem 0.75rem;
  border-top: 1px solid #f1f5f9;
  color: var(--ink-700);
  font-size: 0.875rem;
  /* Equal-width digits keep numeric columns aligned */
  font-variant-numeric: tabular-nums;
}

tbody tr {
  transition: background-color 0.15s ease;
}

tbody tr:hover {
  background: var(--surface-muted);
}

.badge {
  display: inline-block;
  padding: 0.313rem 0.75rem;
  border-radius: var(--radius-badge);
  font-size: 0.75rem;
  font-weight: 600;
}

.badge.success {
  background: #d1fae5;
  color: #065f46;
}

.badge.warning {
  background: #fed7aa;
  color: #92400e;
}

.badge.danger {
  background: #fecaca;
  color: #991b1b;
}

.badge.info {
  background: #dbeafe;
  color: #1e40af;
}

.badge.increasing {
  background: #d1fae5;
  color: #065f46;
}

.badge.decreasing {
  background: #fecaca;
  color: #991b1b;
}

.badge.stable {
  background: #e0e7ff;
  color: #3730a3;
}

.badge.high {
  background: #fecaca;
  color: #991b1b;
}

.badge.medium {
  background: #fed7aa;
  color: #92400e;
}

.badge.low {
  background: #dbeafe;
  color: #1e40af;
}

.loading {
  text-align: center;
  padding: 3rem;
  color: var(--ink-500);
  font-size: 0.938rem;
}

.error {
  background: #fef2f2;
  border: 1px solid #fecaca;
  color: #991b1b;
  padding: 1rem;
  border-radius: 8px;
  margin: 1rem 0;
  font-size: 0.938rem;
}
</style>
