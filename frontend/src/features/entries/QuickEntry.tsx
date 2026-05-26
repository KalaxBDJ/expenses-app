import { FormEvent, useState } from "react";
import { Calendar, CreditCard, DollarSign, Tags } from "lucide-react";
import { api } from "../../lib/api";
import { categoryName, today } from "../../lib/format";
import type { Category, Currency } from "../../types";

type Props = {
  categories: Category[];
  userId: number;
  defaultCurrency: Currency;
  onSaved: () => void;
};

export function QuickEntry({ categories, userId, defaultCurrency, onSaved }: Props) {
  const [kind, setKind] = useState<"expense" | "income">("expense");
  const [amount, setAmount] = useState("");
  const [category, setCategory] = useState("food");
  const [date, setDate] = useState(today());
  const [description, setDescription] = useState("");
  const [paymentMethod, setPaymentMethod] = useState("");
  const [saving, setSaving] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    try {
      if (kind === "expense") {
        await api.createExpense({
          user_id: userId,
          currency: defaultCurrency,
          amount: Number(amount),
          date,
          category,
          description: description || categoryName(category),
          payment_method: paymentMethod || null,
          note: null
        });
      } else {
        await api.createIncome({
          user_id: userId,
          currency: defaultCurrency,
          amount: Number(amount),
          date,
          source: description || "Ingreso",
          description: description || null
        });
      }
      setAmount("");
      setDescription("");
      setPaymentMethod("");
      onSaved();
    } finally {
      setSaving(false);
    }
  }

  return (
    <form className="entry-form" onSubmit={submit}>
      <div className="segmented" role="tablist" aria-label="Tipo de movimiento">
        <button type="button" className={kind === "expense" ? "is-active" : ""} onClick={() => setKind("expense")}>Gasto</button>
        <button type="button" className={kind === "income" ? "is-active" : ""} onClick={() => setKind("income")}>Ingreso</button>
      </div>

      <label className="amount-field">
        <span>Monto</span>
        <div>
          <DollarSign size={24} />
          <input autoFocus inputMode="decimal" value={amount} onChange={(event) => setAmount(event.target.value)} placeholder="0" required />
        </div>
      </label>

      {kind === "expense" ? (
        <section className="field-group">
          <label><Tags size={18} /> Categoría</label>
          <div className="chip-grid">
            {categories.map((item) => (
              <button type="button" key={item.key} className={category === item.key ? "chip is-active" : "chip"} onClick={() => setCategory(item.key)}>
                {categoryName(item.key)}
              </button>
            ))}
          </div>
        </section>
      ) : null}

      <div className="form-grid">
        <label>
          <span><Calendar size={16} /> Fecha</span>
          <input type="date" value={date} onChange={(event) => setDate(event.target.value)} required />
        </label>
        {kind === "expense" ? (
          <label>
            <span><CreditCard size={16} /> Método</span>
            <input value={paymentMethod} onChange={(event) => setPaymentMethod(event.target.value)} placeholder="Tarjeta, efectivo..." />
          </label>
        ) : null}
      </div>

      <label>
        <span>{kind === "expense" ? "Nota opcional" : "Fuente"}</span>
        <input value={description} onChange={(event) => setDescription(event.target.value)} placeholder={kind === "expense" ? "Ej. Almuerzo" : "Ej. Salario"} />
      </label>

      <button className="primary-button full" disabled={saving || !amount}>
        {saving ? "Guardando..." : kind === "expense" ? "Guardar gasto" : "Guardar ingreso"}
      </button>
    </form>
  );
}
