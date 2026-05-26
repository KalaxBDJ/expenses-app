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
  const [config, setConfig] = useState(session.config);
  const [currency, setCurrency] = useState<Currency>(session.config.default_currency);
  const [locale, setLocale] = useState(session.config.locale);
  const [saving, setSaving] = useState(false);
  const [smsApiKey, setSmsApiKey] = useState("");
  const [generatingKey, setGeneratingKey] = useState(false);
  const [deletingKey, setDeletingKey] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    try {
      const config = await api.updateConfig(session.user.id, {
        default_currency: currency,
        locale
      });
      setConfig(config);
      onUpdated({ ...session, config }, "Configuración guardada");
    } finally {
      setSaving(false);
    }
  }

  async function generateSmsApiKey() {
    setGeneratingKey(true);
    try {
      const response = await api.rotateSmsApiKey(session.user.id);
      const nextSession = { ...session, config: response.config };
      setConfig(response.config);
      setSmsApiKey(response.api_key);
      localStorage.setItem("claridad_session", JSON.stringify(nextSession));
    } finally {
      setGeneratingKey(false);
    }
  }

  async function deleteSmsApiKey() {
    if (!window.confirm("¿Eliminar la API key para SMS? Las automatizaciones que la usen dejarán de funcionar.")) return;
    setDeletingKey(true);
    try {
      const config = await api.deleteSmsApiKey(session.user.id);
      setConfig(config);
      setSmsApiKey("");
      onUpdated({ ...session, config }, "API key eliminada");
    } finally {
      setDeletingKey(false);
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

      <section className="panel">
        <div className="section-head">
          <div>
            <h2>API key para SMS</h2>
            <p>Úsala en iOS Automation para registrar gastos desde mensajes.</p>
          </div>
        </div>
        <div className="api-key-table">
          <div>
            <span>Estado</span>
            <strong>{config.has_sms_api_key ? "Activa" : "Sin API key"}</strong>
          </div>
          <div>
            <span>Terminación</span>
            <strong>{config.sms_api_key_suffix ? `•••••${config.sms_api_key_suffix}` : "No disponible"}</strong>
          </div>
        </div>
        <div className="api-key-actions">
          <button className="ghost-button" onClick={generateSmsApiKey} disabled={generatingKey || deletingKey}>
            {generatingKey ? "Generando..." : config.has_sms_api_key ? "Generar nueva" : "Generar API key"}
          </button>
          {config.has_sms_api_key ? (
            <button className="ghost-button danger-action" onClick={deleteSmsApiKey} disabled={generatingKey || deletingKey}>
              {deletingKey ? "Eliminando..." : "Eliminar"}
            </button>
          ) : null}
        </div>
        {smsApiKey ? (
          <div className="generated-key-box">
            <strong>API key generada</strong>
            <p>Guárdala ahora. No se volverá a mostrar completa.</p>
            <input readOnly value={smsApiKey} onFocus={(event) => event.currentTarget.select()} />
          </div>
        ) : null}
      </section>
    </div>
  );
}
