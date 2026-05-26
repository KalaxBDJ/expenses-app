import { useMemo, useState } from "react";
import { Pencil, Search, Trash2 } from "lucide-react";
import { api } from "../../lib/api";
import { categoryName, friendlyDate, money } from "../../lib/format";
import type { Category, Expense, Income } from "../../types";
import { StateBlock } from "../../components/StateBlock";

type Props = {
  expenses: Expense[];
  incomes: Income[];
  categories: Category[];
  onChanged: (message?: string) => void;
};

type Movement =
  | { type: "expense"; id: number; date: string; title: string; meta: string; amount: number; expense: Expense }
  | { type: "income"; id: number; date: string; title: string; meta: string; amount: number; currency: Income["currency"] };

export function Movements({ expenses, incomes, categories, onChanged }: Props) {
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("all");
  const [editing, setEditing] = useState<Expense | null>(null);

  const movements = useMemo(() => {
    const expenseRows: Movement[] = expenses.map((expense) => ({
      type: "expense",
      id: expense.id,
      date: expense.date,
      title: expense.description || categoryName(expense.category),
      meta: `${categoryName(expense.category)} · ${expense.payment_method || "Sin método"}`,
      amount: expense.amount,
      expense
    }));
    const incomeRows: Movement[] = incomes.map((income) => ({
      type: "income",
      id: income.id,
      date: income.date,
      title: income.source,
      meta: income.description || "Ingreso",
      amount: income.amount,
      currency: income.currency
    }));
    return [...expenseRows, ...incomeRows]
      .filter((item) => item.title.toLowerCase().includes(query.toLowerCase()) || item.meta.toLowerCase().includes(query.toLowerCase()))
      .filter((item) => category === "all" || (item.type === "expense" && item.expense.category === category))
      .sort((a, b) => b.date.localeCompare(a.date));
  }, [category, expenses, incomes, query]);

  async function remove(expense: Expense) {
    if (!window.confirm("¿Borrar este gasto?")) return;
    await api.deleteExpense(expense.id);
    onChanged("Gasto borrado");
  }

  if (!expenses.length && !incomes.length) {
    return <StateBlock variant="empty" title="Aún no hay movimientos este mes" text="Agrega tu primer gasto o ingreso para ver tu resumen." />;
  }

  return (
    <div className="stack">
      <section className="filters">
        <label className="search-box">
          <Search size={18} />
          <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Buscar movimiento" />
        </label>
        <select value={category} onChange={(event) => setCategory(event.target.value)} aria-label="Filtrar por categoría">
          <option value="all">Todas</option>
          {categories.map((item) => <option key={item.key} value={item.key}>{categoryName(item.key)}</option>)}
        </select>
        {(query || category !== "all") ? <button className="ghost-button" onClick={() => { setQuery(""); setCategory("all"); }}>Limpiar</button> : null}
      </section>

      <section className="panel movement-list">
        {movements.map((item) => (
          <article className={`movement-item ${item.type}`} key={`${item.type}-${item.id}`}>
            <div className="movement-date">{friendlyDate(item.date)}</div>
            <div>
              <strong>{item.title}</strong>
              <span>{item.meta}</span>
            </div>
            <b>{item.type === "expense" ? "-" : "+"}{money(item.amount, item.type === "expense" ? item.expense.currency : item.currency)}</b>
            {item.type === "expense" ? (
              <div className="row-actions">
                <button aria-label="Editar gasto" onClick={() => setEditing(item.expense)}><Pencil size={16} /></button>
                <button aria-label="Borrar gasto" onClick={() => remove(item.expense)}><Trash2 size={16} /></button>
              </div>
            ) : <span className="income-pill">Ingreso</span>}
          </article>
        ))}
      </section>

      {editing ? <ExpenseEditor expense={editing} categories={categories} onClose={() => setEditing(null)} onSaved={() => { setEditing(null); onChanged("Gasto actualizado"); }} /> : null}
    </div>
  );
}

function ExpenseEditor({ expense, categories, onClose, onSaved }: { expense: Expense; categories: Category[]; onClose: () => void; onSaved: () => void }) {
  const [amount, setAmount] = useState(String(expense.amount));
  const [category, setCategory] = useState(expense.category);
  const [description, setDescription] = useState(expense.description || "");
  const [date, setDate] = useState(expense.date);

  async function save() {
    await api.updateExpense(expense.id, { amount: Number(amount), category, description, date });
    onSaved();
  }

  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true">
      <section className="modal">
        <h2>Editar gasto</h2>
        <label><span>Monto</span><input inputMode="decimal" value={amount} onChange={(event) => setAmount(event.target.value)} /></label>
        <label><span>Fecha</span><input type="date" value={date} onChange={(event) => setDate(event.target.value)} /></label>
        <label><span>Categoría</span><select value={category} onChange={(event) => setCategory(event.target.value)}>{categories.map((item) => <option key={item.key} value={item.key}>{categoryName(item.key)}</option>)}</select></label>
        <label><span>Descripción</span><input value={description} onChange={(event) => setDescription(event.target.value)} /></label>
        <div className="modal-actions">
          <button className="ghost-button" onClick={onClose}>Cancelar</button>
          <button className="primary-button" onClick={save}>Guardar</button>
        </div>
      </section>
    </div>
  );
}
