import { FormEvent, useState } from "react";
import { CircleDollarSign } from "lucide-react";
import { api } from "../../lib/api";
import type { AuthSession } from "../../types";

type Props = {
  onAuthenticated: (session: AuthSession) => void;
};

export function AuthScreen({ onAuthenticated }: Props) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      const session = mode === "login"
        ? await api.login({ email, password })
        : await api.register({ name, email, password });
      onAuthenticated(session);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No pudimos iniciar sesión.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-card">
        <div className="brand-lockup">
          <CircleDollarSign size={34} />
          <div>
            <p className="eyebrow">Finanzas personales</p>
            <h1>Claridad</h1>
          </div>
        </div>

        <div className="segmented" role="tablist" aria-label="Acceso">
          <button type="button" className={mode === "login" ? "is-active" : ""} onClick={() => setMode("login")}>Ingresar</button>
          <button type="button" className={mode === "register" ? "is-active" : ""} onClick={() => setMode("register")}>Registro</button>
        </div>

        <form className="entry-form" onSubmit={submit}>
          {mode === "register" ? (
            <label>
              <span>Nombre</span>
              <input value={name} onChange={(event) => setName(event.target.value)} required />
            </label>
          ) : null}
          <label>
            <span>Email</span>
            <input type="email" value={email} onChange={(event) => setEmail(event.target.value)} required />
          </label>
          <label>
            <span>Contraseña</span>
            <input type="password" value={password} minLength={mode === "register" ? 8 : 1} onChange={(event) => setPassword(event.target.value)} required />
          </label>
          {error ? <p className="form-error">{error}</p> : null}
          <button className="primary-button full" disabled={loading}>
            {loading ? "Validando..." : mode === "login" ? "Entrar" : "Crear cuenta"}
          </button>
        </form>
      </section>
    </main>
  );
}
