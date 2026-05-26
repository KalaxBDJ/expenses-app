import { FormEvent, useState } from "react";
import { LogOut } from "lucide-react";
import { api } from "../../lib/api";
import type { AuthSession, Currency } from "../../types";

const currencies: Currency[] = ["COP", "USD", "EUR", "MXN", "ARS", "CLP", "PEN", "BRL"];

type Props = {
  session: AuthSession;
  onUpdated: (session: AuthSession, message?: string) => void;
  onLogout: () => void;
};

export function Settings({ session, onUpdated, onLogout }: Props) {
  const [currency, setCurrency] = useState<Currency>(session.config.default_currency);
  const [locale, setLocale] = useState(session.config.locale);
  const [saving, setSaving] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    try {
      const config = await api.updateConfig(session.user.id, {
        default_currency: currency,
        locale
      });
      onUpdated({ ...session, config }, "Configuración guardada");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="stack">
      <section className="panel">
        <div className="section-head">
          <div>
            <h2>Cuenta</h2>
            <p>{session.user.name} · {session.user.email}</p>
          </div>
          <button className="ghost-button icon-text" onClick={onLogout}><LogOut size={17} /> Salir</button>
        </div>
      </section>

      <form className="compact-form" onSubmit={submit}>
        <h2>Configuración</h2>
        <label>
          <span>Moneda por defecto</span>
          <select value={currency} onChange={(event) => setCurrency(event.target.value as Currency)}>
            {currencies.map((item) => <option key={item} value={item}>{item}</option>)}
          </select>
        </label>
        <label>
          <span>Formato regional</span>
          <input value={locale} onChange={(event) => setLocale(event.target.value)} placeholder="es-CO" />
        </label>
        <p className="muted">Si un gasto importado por IA no trae moneda clara, se guardará usando esta moneda.</p>
        <button className="primary-button full" disabled={saving}>{saving ? "Guardando..." : "Guardar configuración"}</button>
      </form>
    </div>
  );
}
