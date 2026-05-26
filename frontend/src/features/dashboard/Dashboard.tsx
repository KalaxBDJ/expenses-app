import { ArrowDownRight, ArrowUpRight, WalletCards } from "lucide-react";
import type { ReactNode } from "react";
import { StateBlock } from "../../components/StateBlock";
import { ProgressBar } from "../../components/ProgressBar";
import { categoryName, money } from "../../lib/format";
import type { Budget, DashboardSummary, Expense, SavingsGoal } from "../../types";

type Props = {
  data: {
    dashboard?: DashboardSummary;
    goals: SavingsGoal[];
  };
  onAdd: () => void;
};

export function Dashboard({ data, onAdd }: Props) {
  const dashboard = data.dashboard;
  if (!dashboard) {
    return <StateBlock variant="empty" title="Aún no hay resumen" text="Agrega tu primer movimiento para ver tu mes con más claridad." actionLabel="Agregar movimiento" onAction={onAdd} />;
  }

  const topBudget = [...dashboard.budgets].sort((a, b) => b.progress - a.progress)[0];
  const insights = buildInsights(dashboard);
  const currency = dashboard.currency;

  return (
    <div className="stack">
      <section className="hero-summary">
        <div>
          <p className="eyebrow">Gastado este mes</p>
          <strong>{money(dashboard.total_spent, currency)}</strong>
          <span>{dashboard.spent_change_percent === null ? "Primer mes de referencia" : `${Math.abs(dashboard.spent_change_percent)}% ${dashboard.spent_change_percent >= 0 ? "más" : "menos"} que el mes anterior`}</span>
        </div>
        <button className="primary-button" onClick={onAdd}>Agregar gasto</button>
      </section>

      <section className="summary-grid" aria-label="Resumen mensual">
        <SummaryCard label="Ingresos" value={money(dashboard.total_income, currency)} tone="income" icon={<ArrowUpRight size={18} />} />
        <SummaryCard label={dashboard.balance >= 0 ? "Disponible" : "Balance"} value={money(dashboard.balance, currency)} tone={dashboard.balance >= 0 ? "income" : "watch"} icon={<WalletCards size={18} />} />
        <SummaryCard label="Mes anterior" value={money(dashboard.previous_month_spent, currency)} tone="neutral" icon={<ArrowDownRight size={18} />} />
      </section>

      <section className="panel">
        <div className="section-head">
          <h2>En qué se fue</h2>
          <span>{dashboard.spent_by_category.length} categorías</span>
        </div>
        {dashboard.spent_by_category.length ? (
          <div className="category-bars">
            {dashboard.spent_by_category.slice(0, 5).map((item) => (
              <div key={item.category} className="bar-row">
                <span>{categoryName(item.category)}</span>
                <strong>{money(item.total, currency)}</strong>
                <ProgressBar value={item.total / Math.max(dashboard.total_spent, 1)} />
              </div>
            ))}
          </div>
        ) : (
          <StateBlock variant="empty" title="Aún no hay movimientos este mes" text="Agrega tu primer gasto para ver tu resumen." actionLabel="Agregar gasto" onAction={onAdd} />
        )}
      </section>

      {topBudget ? <BudgetNotice budget={topBudget} /> : null}

      <section className="panel">
        <div className="section-head">
          <h2>Patrones para mirar</h2>
          <span>{insights.length}</span>
        </div>
        <div className="insight-list">
          {insights.map((insight) => <p key={insight}>{insight}</p>)}
        </div>
      </section>

      <section className="panel">
        <div className="section-head">
          <h2>Últimos movimientos</h2>
          <span>{dashboard.recent_expenses.length}</span>
        </div>
        {dashboard.recent_expenses.length ? dashboard.recent_expenses.slice(0, 4).map((expense) => <RecentExpense key={expense.id} expense={expense} />) : (
          <p className="muted">Aún no hay movimientos recientes.</p>
        )}
      </section>

      <section className="panel">
        <div className="section-head">
          <h2>Metas principales</h2>
          <span>{data.goals.length}</span>
        </div>
        {data.goals.length ? data.goals.slice(0, 2).map((goal) => (
          <div className="goal-mini" key={goal.id}>
            <div>
              <strong>{goal.name}</strong>
              <span>Vas en {Math.round(goal.progress * 100)}% de tu meta.</span>
            </div>
            <ProgressBar value={goal.progress} />
          </div>
        )) : <p className="muted">Puedes crear una meta para seguir tu ahorro visualmente.</p>}
      </section>
    </div>
  );
}

function SummaryCard({ label, value, tone, icon }: { label: string; value: string; tone: string; icon: ReactNode }) {
  return (
    <article className={`summary-card ${tone}`}>
      <span>{icon}</span>
      <p>{label}</p>
      <strong>{value}</strong>
    </article>
  );
}

function BudgetNotice({ budget }: { budget: Budget }) {
  const tone = budget.progress >= 1 ? "soft-danger" : budget.progress >= 0.8 ? "watch" : "calm";
  return (
    <section className={`budget-notice ${tone}`}>
      <p>Has usado el {Math.round(budget.progress * 100)}% de tu presupuesto de {categoryName(budget.category)}.</p>
      <strong>{budget.remaining >= 0 ? `Te quedan ${money(budget.remaining, budget.currency)} este mes.` : `Tus gastos superan este presupuesto por ${money(Math.abs(budget.remaining), budget.currency)}.`}</strong>
      <ProgressBar value={budget.progress} tone={tone} />
    </section>
  );
}

function RecentExpense({ expense }: { expense: Expense }) {
  return (
    <div className="movement-row">
      <div>
        <strong>{expense.description || categoryName(expense.category)}</strong>
        <span>{categoryName(expense.category)} · {expense.payment_method || "Sin método"}</span>
      </div>
      <b>-{money(expense.amount, expense.currency)}</b>
    </div>
  );
}

function buildInsights(dashboard: DashboardSummary) {
  const insights: string[] = [];
  const topCategory = dashboard.spent_by_category[0];
  const smallExpenses = dashboard.recent_expenses.filter((expense) => expense.amount <= 15);
  const repeated = dashboard.recent_expenses.reduce<Record<string, number>>((acc, expense) => {
    acc[expense.category] = (acc[expense.category] || 0) + 1;
    return acc;
  }, {});
  const repeatedCategory = Object.entries(repeated).sort((a, b) => b[1] - a[1])[0];

  if (topCategory) insights.push(`${categoryName(topCategory.category)} fue la categoría con mayor movimiento.`);
  if (smallExpenses.length >= 3) insights.push(`Notamos varios gastos pequeños frecuentes este mes.`);
  if (dashboard.spent_change_percent !== null) insights.push(`Este mes gastaste ${Math.abs(dashboard.spent_change_percent)}% ${dashboard.spent_change_percent >= 0 ? "más" : "menos"} que el anterior.`);
  if (repeatedCategory && repeatedCategory[1] >= 3) insights.push(`Hay varios movimientos similares en ${categoryName(repeatedCategory[0])}.`);
  if (!insights.length) insights.push("Cuando agregues más movimientos, aparecerán patrones útiles aquí.");
  return insights.slice(0, 4);
}
