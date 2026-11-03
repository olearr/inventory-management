<template>
  <div class="restocking">
    <div class="page-header">
      <h2>{{ t('restocking.title') }}</h2>
      <p>{{ t('restocking.description') }}</p>
    </div>

    <div v-if="loading" class="loading">{{ t('common.loading') }}</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else>
      <div class="card budget-card">
        <div class="budget-header">
          <label for="restock-budget" class="budget-label">{{ t('restocking.budgetLabel') }}</label>
          <span class="budget-value">{{ formatMoney(budget, 0) }}</span>
        </div>
        <input
          id="restock-budget"
          class="budget-slider"
          type="range"
          min="0"
          :max="maxBudget"
          step="500"
          v-model.number="budget"
          :disabled="submitting"
          :aria-valuetext="formatMoney(budget, 0)"
        />
        <div class="budget-scale">
          <span>{{ formatMoney(0, 0) }}</span>
          <span>{{ formatMoney(maxBudget, 0) }}</span>
        </div>
      </div>

      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-label">{{ t('restocking.tiles.budget') }}</div>
          <div class="stat-value">{{ formatMoney(budget, 0) }}</div>
        </div>
        <div class="stat-card accent">
          <div class="stat-label">{{ t('restocking.tiles.recommendedTotal') }}</div>
          <div class="stat-value">{{ formatMoney(recommendedTotal) }}</div>
        </div>
        <div class="stat-card success">
          <div class="stat-label">{{ t('restocking.tiles.remaining') }}</div>
          <div class="stat-value">{{ formatMoney(remainingBudget) }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">{{ t('restocking.tiles.leadTime') }}</div>
          <div class="stat-value">{{ recommendation.length ? t('restocking.days', { count: orderLeadTime }) : '–' }}</div>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <h3 class="card-title">{{ t('restocking.recommendation') }} ({{ recommendation.length }})</h3>
          <button
            type="button"
            class="place-order-btn"
            :disabled="recommendation.length === 0 || submitting"
            @click="placeOrder"
          >
            {{ submitting ? t('restocking.submitting') : t('restocking.placeOrder') }}
          </button>
        </div>

        <div v-if="submitError" class="error" role="alert">{{ submitError }}</div>

        <div v-if="confirmation" class="confirmation" role="status">
          <p class="confirmation-title">{{ t('restocking.success', { orderNumber: confirmation.order_number }) }}</p>
          <p class="confirmation-meta">
            {{ t('restocking.successTotal') }}: <strong>{{ formatMoney(confirmation.total_cost) }}</strong>
            &nbsp;|&nbsp;
            {{ t('restocking.successLeadTime') }}: <strong>{{ t('restocking.days', { count: confirmation.lead_time_days }) }}</strong>
          </p>
          <router-link to="/orders" class="confirmation-link">{{ t('restocking.viewOrders') }}</router-link>
        </div>

        <div v-if="recommendation.length === 0" class="empty-state">
          <template v-if="candidates.length === 0">
            <p>{{ t('restocking.emptyNoCandidates') }}</p>
          </template>
          <template v-else>
            <p class="empty-title">{{ t('restocking.emptyTitle') }}</p>
            <p>{{ t('restocking.empty', { amount: formatMoney(minimumBudget) }) }}</p>
          </template>
        </div>

        <div v-else class="table-container">
          <table>
            <thead>
              <tr>
                <th>{{ t('restocking.table.item') }}</th>
                <th>{{ t('restocking.table.growth') }}</th>
                <th>{{ t('restocking.table.quantity') }}</th>
                <th>{{ t('restocking.table.unitCost') }}</th>
                <th>{{ t('restocking.table.lineTotal') }}</th>
                <th>{{ t('restocking.table.leadTime') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in recommendation" :key="item.item_sku">
                <td>
                  <strong>{{ translateProductName(item.item_name) }}</strong>
                  <div class="sku">{{ item.item_sku }}</div>
                </td>
                <td><span class="badge increasing">+{{ item.growthPercent }}%</span></td>
                <td>{{ item.quantity }}</td>
                <td>{{ formatMoney(item.unit_cost) }}</td>
                <td><strong>{{ formatMoney(item.lineTotal) }}</strong></td>
                <td>{{ t('restocking.days', { count: item.lead_time_days }) }}</td>
              </tr>
            </tbody>
            <tfoot>
              <tr>
                <td colspan="4"><strong>{{ t('restocking.total') }}</strong></td>
                <td><strong>{{ formatMoney(recommendedTotal) }}</strong></td>
                <td></td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, watch, onMounted } from 'vue'
import { api } from '../api'
import { useI18n } from '../composables/useI18n'
import { formatCurrencyWithDecimals } from '../utils/currency'

// Slider granularity in USD
const BUDGET_STEP = 500
const DEFAULT_BUDGET = 10000

// Rounds to whole cents so sums of unit_cost * quantity do not drift (e.g. 0.1 + 0.2)
const toCents = (value) => Math.round(value * 100) / 100

export default {
  name: 'Restocking',
  setup() {
    const { t, currentCurrency, translateProductName } = useI18n()

    const loading = ref(true)
    const error = ref(null)
    const forecasts = ref([])
    const budget = ref(0) // USD; converted only for display
    const submitting = ref(false)
    const submitError = ref(null)
    const confirmation = ref(null)

    // Backend amounts are USD with cents; budget tiles use 0 decimals, item prices 2
    const formatMoney = (amount, decimals = 2) =>
      formatCurrencyWithDecimals(amount, currentCurrency.value, decimals)

    // Items with rising demand, highest growth first. Items with zero current demand are
    // excluded because growth cannot be computed (division by zero).
    const candidates = computed(() => {
      return forecasts.value
        // forecasted_demand > 0 as well: the server rejects quantities below 1, which
        // would fail the whole order
        .filter(f => String(f.trend).toLowerCase() === 'increasing' && f.current_demand > 0 && f.forecasted_demand > 0)
        .map(f => {
          const growth = (f.forecasted_demand - f.current_demand) / f.current_demand
          return {
            ...f,
            quantity: f.forecasted_demand,
            lineTotal: toCents(f.forecasted_demand * f.unit_cost),
            growth,
            growthPercent: (growth * 100).toFixed(1)
          }
        })
        .sort((a, b) => b.growth - a.growth)
    })

    // Slider max = cost of ordering every candidate in full, rounded up to the next step,
    // so the top of the slider always shows the complete recommendation
    const maxBudget = computed(() => {
      const total = candidates.value.reduce((sum, c) => sum + c.lineTotal, 0)
      return Math.ceil(total / BUDGET_STEP) * BUDGET_STEP
    })

    // Greedy walk in priority order. We stop at the first item that does not fit instead of
    // skipping to cheaper ones, so a lower-priority item never displaces a higher-priority one.
    const recommendation = computed(() => {
      const picked = []
      let running = 0
      for (const item of candidates.value) {
        const next = toCents(running + item.lineTotal)
        if (next > budget.value) break
        picked.push(item)
        running = next
      }
      return picked
    })

    const recommendedTotal = computed(() =>
      recommendation.value.reduce((sum, i) => toCents(sum + i.lineTotal), 0)
    )

    const remainingBudget = computed(() => toCents(budget.value - recommendedTotal.value))

    // The order arrives when its slowest item arrives
    const orderLeadTime = computed(() =>
      recommendation.value.reduce((max, i) => Math.max(max, i.lead_time_days), 0)
    )

    // Smallest budget that yields a non-empty recommendation (first candidate must fit)
    const minimumBudget = computed(() =>
      candidates.value.length ? candidates.value[0].lineTotal : 0
    )

    const loadForecasts = async () => {
      try {
        loading.value = true
        error.value = null
        forecasts.value = await api.getDemandForecasts()
        // Initial value depends on the data-driven max, so it is set after loading
        budget.value = Math.min(DEFAULT_BUDGET, maxBudget.value)
      } catch (err) {
        error.value = t('restocking.loadError') + ': ' + err.message
      } finally {
        loading.value = false
      }
    }

    // A confirmation or error describes the previous budget and would be misleading afterwards
    watch(budget, () => {
      confirmation.value = null
      submitError.value = null
    })

    const placeOrder = async () => {
      // Guard in addition to the disabled button to prevent double submits
      if (submitting.value || recommendation.value.length === 0) return
      submitting.value = true
      submitError.value = null
      confirmation.value = null
      try {
        // Only SKUs and quantities are sent; the server prices the order itself
        confirmation.value = await api.createRestockOrder({
          budget: budget.value,
          items: recommendation.value.map(({ item_sku, quantity }) => ({ item_sku, quantity }))
        })
      } catch (err) {
        submitError.value = err.response?.data?.detail || err.message
      } finally {
        submitting.value = false
      }
    }

    onMounted(loadForecasts)

    return {
      t,
      loading,
      error,
      budget,
      maxBudget,
      candidates,
      recommendation,
      recommendedTotal,
      remainingBudget,
      orderLeadTime,
      minimumBudget,
      submitting,
      submitError,
      confirmation,
      formatMoney,
      translateProductName,
      placeOrder
    }
  }
}
</script>

<style scoped>
.budget-header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 0.75rem;
}

.budget-label {
  font-weight: 600;
  color: var(--ink-900);
}

.budget-value {
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--accent);
}

.budget-slider {
  width: 100%;
  accent-color: var(--accent);
  cursor: pointer;
}

.budget-slider:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 4px;
  border-radius: 4px;
}

.budget-scale {
  display: flex;
  justify-content: space-between;
  margin-top: 0.25rem;
  font-size: 0.813rem;
  color: var(--ink-500);
}

.sku {
  font-size: 0.813rem;
  color: var(--ink-500);
}

tfoot td {
  border-top: 2px solid var(--line);
}

.place-order-btn {
  background: var(--accent);
  color: white;
  border: none;
  border-radius: 8px;
  padding: 0.5rem 1.25rem;
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
}

.place-order-btn:hover:not(:disabled) {
  background: var(--accent-strong);
}

.place-order-btn:focus-visible {
  outline: 2px solid var(--ink-900);
  outline-offset: 2px;
}

.place-order-btn:disabled {
  background: var(--line-strong);
  cursor: not-allowed;
}

.confirmation {
  background: var(--accent-soft);
  border: 1px solid var(--accent-line);
  border-radius: 8px;
  padding: 1rem;
  margin: 1rem 0;
  color: var(--ink-900);
}

.confirmation-title {
  font-weight: 700;
  margin-bottom: 0.25rem;
}

.confirmation-meta {
  color: var(--ink-500);
  font-size: 0.875rem;
  margin-bottom: 0.5rem;
}

.confirmation-link {
  color: var(--accent);
  font-weight: 600;
  font-size: 0.875rem;
}

.empty-state {
  text-align: center;
  padding: 2rem 1rem;
  color: var(--ink-500);
  font-size: 0.938rem;
}

.empty-title {
  color: var(--ink-900);
  font-weight: 700;
  margin-bottom: 0.25rem;
}
</style>
