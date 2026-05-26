import { FormEvent, useMemo, useState } from "react";
import { ProgressBar } from "../../components/ProgressBar";
import { StateBlock } from "../../components/StateBlock";
import { api } from "../../lib/api";
import { categoryName, money } from "../../lib/format";
import type { Budget, Category, Currency } from "../../types";

type Props = {
  budgets: Budget[];
  categories: Category[];
  userId: number;
  defaultCurrency: Currency;
  month: string;
  onSaved: () => void;
};

export function Budgets({ budgets, categories, userId, defaultCurrency, month, onSaved }: Props) {
  const [category, setCategory] = useState("food");
  const [amount, setAmount] = useState("");
  const sorted = useMemo(() => [...budgets].sort((a, b) => b.progress - a.progress), [budgets]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    await api.createBudget({ user_id: userId, month, category, amount: Number(amount), currency: defaultCurrency });
    setAmount("");
    onSaved();
  }

  return (
    <div className="stack">
      <form className="compact-form" onSubmit={submit}>
        <h2>Crear presupuesto</h2>
        <div className="form-grid">
          <label><span>Categoría</span><select value={category} onChange={(event) => setCategory(event.target.value)}>{categories.map((item) => <option key={item.key} value={item.key}>{categoryName(item.key)}</option>)}</select></label>
          <label><span>Monto</span><input inputMode="decimal" value={amount} onChange={(event) => setAmount(event.target.value)} placeholder="400" required /></label>
        </div>
        <button className="primary-button full">Guardar presupuesto</button>
      </form>

      <section className="stack">
        {sorted.length ? sorted.map((budget) => <BudgetCard key={budget.id} budget={budget} />) : (
          <StateBlock variant="empty" title="Sin presupuestos todavía" text="Crea presupuestos por categoría para saber cuánto margen tienes." />
        )}
      </section>
    </div>
  );
}

function BudgetCard({ budget }: { budget: Budget }) {
  const tone = budget.progress >= 1 ? "soft-danger" : budget.progress >= 0.8 ? "watch" : "calm";
  return (
    <article className={`budget-card ${tone}`}>
      <div className="section-head">
        <div>
          <h2>{categoryName(budget.category)}</h2>
          <p>Has usado el {Math.round(budget.progress * 100)}% de tu presupuesto.</p>
        </div>
        <strong>{money(budget.spent, budget.currency)} / {money(budget.amount, budget.currency)}</strong>
      </div>
      <ProgressBar value={budget.progress} tone={tone} />
      <p className="muted">{budget.remaining >= 0 ? `Te quedan ${money(budget.remaining, budget.currency)} este mes.` : `Este presupuesto está superado por ${money(Math.abs(budget.remaining), budget.currency)}.`}</p>
    </article>
  );
}
