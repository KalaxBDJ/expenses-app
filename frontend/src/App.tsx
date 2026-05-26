import { useCallback, useEffect, useMemo, useState } from "react";
import { BarChart3, CircleDollarSign, Home, List, Plus, Settings as SettingsIcon, Target } from "lucide-react";
import { api, setAuthToken } from "./lib/api";
import { currentMonth } from "./lib/format";
import type { AuthSession, Budget, Category, DashboardSummary, Expense, Income, SavingsGoal, View } from "./types";
import { Dashboard } from "./features/dashboard/Dashboard";
import { QuickEntry } from "./features/entries/QuickEntry";
import { Movements } from "./features/movements/Movements";
import { Budgets } from "./features/budgets/Budgets";
import { Goals } from "./features/goals/Goals";
import { AuthScreen } from "./features/auth/AuthScreen";
import { Settings } from "./features/settings/Settings";
import { StateBlock } from "./components/StateBlock";

type DataState = {
  dashboard?: DashboardSummary;
  categories: Category[];
  expenses: Expense[];
  incomes: Income[];
  budgets: Budget[];
  goals: SavingsGoal[];
};

const initialData: DataState = {
  categories: [],
  expenses: [],
  incomes: [],
  budgets: [],
  goals: []
};

const nav = [
  { id: "home", label: "Inicio", icon: Home },
  { id: "movements", label: "Movimientos", icon: List },
  { id: "add", label: "Agregar", icon: Plus },
  { id: "budgets", label: "Presupuestos", icon: BarChart3 },
  { id: "goals", label: "Metas", icon: Target }
] as const;

export function App() {
  const [view, setView] = useState<View>("home");
  const [showSettings, setShowSettings] = useState(false);
  const [session, setSession] = useState<AuthSession | null>(() => {
    const raw = localStorage.getItem("claridad_session");
    if (!raw) return null;
    try {
      const parsed = JSON.parse(raw) as AuthSession;
      setAuthToken(parsed.token);
      return parsed;
    } catch {
      localStorage.removeItem("claridad_session");
      return null;
    }
  });
  const [month, setMonth] = useState(currentMonth());
  const [data, setData] = useState<DataState>(initialData);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState("");

  const notify = useCallback((message: string) => {
    setToast(message);
    window.setTimeout(() => setToast(""), 2600);
  }, []);

  const saveSession = useCallback((nextSession: AuthSession) => {
    setSession(nextSession);
    setAuthToken(nextSession.token);
    localStorage.setItem("claridad_session", JSON.stringify(nextSession));
  }, []);

  const logout = useCallback(() => {
    setSession(null);
    setAuthToken("");
    localStorage.removeItem("claridad_session");
  }, []);

  const loadData = useCallback(async () => {
    if (!session) return;
    setLoading(true);
    setError(null);
    try {
      const [dashboard, categories, expenses, incomes, budgets, goals] = await Promise.all([
        api.dashboard(session.user.id, month),
        api.categories(),
        api.expenses(session.user.id, month),
        api.incomes(session.user.id, month),
        api.budgets(session.user.id, month),
        api.goals(session.user.id)
      ]);
      setData({ dashboard, categories, expenses, incomes, budgets, goals });
    } catch (err) {
      setError(err instanceof Error ? err.message : "No pudimos cargar tu resumen.");
    } finally {
      setLoading(false);
    }
  }, [month, session]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const refresh = useCallback(async (message?: string) => {
    await loadData();
    if (message) notify(message);
  }, [loadData, notify]);

  const content = useMemo(() => {
    if (loading) return <StateBlock variant="loading" title="Preparando tu resumen" text="Estamos organizando los movimientos del mes." />;
    if (error) return <StateBlock variant="error" title="No pudimos cargar los datos" text={error} actionLabel="Reintentar" onAction={loadData} />;

    if (!session) return null;
    if (showSettings) {
      return <Settings session={session} onUpdated={(nextSession, message) => { saveSession(nextSession); if (message) notify(message); }} onLogout={logout} />;
    }

    switch (view) {
      case "home":
        return <Dashboard data={data} onAdd={() => setView("add")} />;
      case "movements":
        return <Movements expenses={data.expenses} incomes={data.incomes} categories={data.categories} onChanged={refresh} />;
      case "add":
        return <QuickEntry categories={data.categories} userId={session.user.id} defaultCurrency={session.config.default_currency} onSaved={() => refresh("Movimiento guardado")} />;
      case "budgets":
        return <Budgets budgets={data.budgets} categories={data.categories} userId={session.user.id} defaultCurrency={session.config.default_currency} month={month} onSaved={() => refresh("Presupuesto actualizado")} />;
      case "goals":
        return <Goals goals={data.goals} userId={session.user.id} defaultCurrency={session.config.default_currency} onSaved={() => refresh("Meta actualizada")} />;
    }
  }, [data, error, loading, loadData, logout, month, notify, refresh, saveSession, session, showSettings, view]);

  if (!session) {
    return <AuthScreen onAuthenticated={saveSession} />;
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">Tu mes en claro</p>
          <h1><CircleDollarSign size={28} /> Claridad</h1>
        </div>
        <div className="top-actions">
          <label className="month-picker">
            <span>Mes</span>
            <input value={month} onChange={(event) => setMonth(event.target.value)} type="month" />
          </label>
          <button className={`settings-button ${showSettings ? "is-active" : ""}`} onClick={() => setShowSettings((value) => !value)} aria-label="Configuración">
            <SettingsIcon size={21} />
          </button>
        </div>
      </header>

      <main className="view">{content}</main>

      <nav className="bottom-nav" aria-label="Navegación principal">
        {nav.map((item) => {
          const Icon = item.icon;
          return (
            <button
              key={item.id}
              className={`nav-item ${view === item.id ? "is-active" : ""} ${item.id === "add" ? "nav-add" : ""}`}
              onClick={() => { setShowSettings(false); setView(item.id); }}
              aria-label={item.label}
            >
              <Icon size={22} />
              <span>{item.label}</span>
            </button>
          );
        })}
      </nav>

      <div className={`toast ${toast ? "is-visible" : ""}`} role="status" aria-live="polite">
        {toast}
      </div>
    </div>
  );
}
