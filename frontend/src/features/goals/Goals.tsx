import { FormEvent, useState } from "react";
import { ProgressBar } from "../../components/ProgressBar";
import { StateBlock } from "../../components/StateBlock";
import { api } from "../../lib/api";
import { money } from "../../lib/format";
import type { Currency, SavingsGoal } from "../../types";

type Props = {
  goals: SavingsGoal[];
  userId: number;
  defaultCurrency: Currency;
  onSaved: () => void;
};

export function Goals({ goals, userId, defaultCurrency, onSaved }: Props) {
  const [name, setName] = useState("");
  const [target, setTarget] = useState("");

  async function submit(event: FormEvent) {
    event.preventDefault();
    await api.createGoal({ user_id: userId, name, target_amount: Number(target), currency: defaultCurrency, current_amount: 0 });
    setName("");
    setTarget("");
    onSaved();
  }

  return (
    <div className="stack">
      <form className="compact-form" onSubmit={submit}>
        <h2>Nueva meta</h2>
        <div className="form-grid">
          <label><span>Nombre</span><input value={name} onChange={(event) => setName(event.target.value)} placeholder="Fondo de emergencia" required /></label>
          <label><span>Objetivo</span><input inputMode="decimal" value={target} onChange={(event) => setTarget(event.target.value)} placeholder="1000" required /></label>
        </div>
        <button className="primary-button full">Crear meta</button>
      </form>

      {goals.length ? goals.map((goal) => <GoalCard key={goal.id} goal={goal} onSaved={onSaved} />) : (
        <StateBlock variant="empty" title="Sin metas todavía" text="Puedes crear una meta para seguir tu ahorro visualmente." />
      )}
    </div>
  );
}

function GoalCard({ goal, onSaved }: { goal: SavingsGoal; onSaved: () => void }) {
  const [amount, setAmount] = useState("");

  async function contribute() {
    if (!amount) return;
    await api.contributeGoal(goal.id, Number(amount));
    setAmount("");
    onSaved();
  }

  return (
    <article className="goal-card">
      <div className="section-head">
        <div>
          <h2>{goal.name}</h2>
          <p>Vas en {Math.round(goal.progress * 100)}% de tu meta.</p>
        </div>
        <strong>{money(goal.current_amount, goal.currency)}</strong>
      </div>
      <ProgressBar value={goal.progress} />
      <p className="muted">Te faltan {money(Math.max(goal.target_amount - goal.current_amount, 0), goal.currency)} para completar esta meta.</p>
      <div className="inline-form">
        <input inputMode="decimal" value={amount} onChange={(event) => setAmount(event.target.value)} placeholder="Aporte" />
        <button className="primary-button" onClick={contribute}>Agregar</button>
      </div>
    </article>
  );
}
