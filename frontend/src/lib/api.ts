import type { AuthSession, Budget, Category, Currency, DashboardSummary, Expense, Income, SavingsGoal, UserConfig } from "../types";

let authToken = "";
const legacyBackendUrl = import.meta.env.VITE_BACKEND_URL
  ? `${String(import.meta.env.VITE_BACKEND_URL).replace(/\/$/, "")}/api`
  : undefined;
const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? legacyBackendUrl ?? "/api").replace(/\/$/, "");

export function setAuthToken(token: string) {
  authToken = token;
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
      ...options?.headers
    },
    ...options
  });

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail ?? body?.description ?? "No pudimos completar la acción.");
  }

  return response.json() as Promise<T>;
}

export const api = {
  register: (payload: { name: string; email: string; password: string }) =>
    request<AuthSession>("/auth/register", { method: "POST", body: JSON.stringify(payload) }),
  login: (payload: { email: string; password: string }) =>
    request<AuthSession>("/auth/login", { method: "POST", body: JSON.stringify(payload) }),
  me: () => request<AuthSession>("/auth/me"),
  userConfig: (userId: number) => request<UserConfig>(`/users/${userId}/config`),
  updateConfig: (userId: number, payload: Partial<Pick<UserConfig, "default_currency" | "locale">>) =>
    request<UserConfig>(`/users/${userId}/config`, { method: "PATCH", body: JSON.stringify(payload) }),
  rotateSmsApiKey: (userId: number) =>
    request<{ api_key: string; config: UserConfig }>(`/users/${userId}/sms-api-key`, { method: "POST" }),
  deleteSmsApiKey: (userId: number) =>
    request<UserConfig>(`/users/${userId}/sms-api-key`, { method: "DELETE" }),
  dashboard: (userId: number, month: string) =>
    request<DashboardSummary>(`/dashboard/monthly?user_id=${userId}&month=${month}`),
  categories: () => request<Category[]>("/categories"),
  expenses: (userId: number, month: string) => request<Expense[]>(`/expenses?user_id=${userId}&month=${month}&limit=200`),
  incomes: (userId: number, month: string) => request<Income[]>(`/incomes?user_id=${userId}&month=${month}`),
  budgets: (userId: number, month: string) => request<Budget[]>(`/budgets?user_id=${userId}&month=${month}`),
  goals: (userId: number) => request<SavingsGoal[]>(`/savings-goals?user_id=${userId}`),
  createExpense: (payload: Omit<Expense, "id" | "created_at" | "source">) =>
    request<Expense>("/expenses", { method: "POST", body: JSON.stringify(payload) }),
  updateExpense: (id: number, payload: Partial<Expense>) =>
    request<Expense>(`/expenses/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  deleteExpense: (id: number) => request<{ deleted: boolean }>(`/expenses/${id}`, { method: "DELETE" }),
  createIncome: (payload: Omit<Income, "id" | "created_at">) =>
    request<Income>("/incomes", { method: "POST", body: JSON.stringify(payload) }),
  createBudget: (payload: { user_id: number; month: string; category: string; amount: number; currency: Currency }) =>
    request<Budget>("/budgets", { method: "POST", body: JSON.stringify(payload) }),
  createGoal: (payload: {
    user_id: number;
    name: string;
    target_amount: number;
    currency: Currency;
    current_amount: number;
    target_date?: string;
  }) => request<SavingsGoal>("/savings-goals", { method: "POST", body: JSON.stringify(payload) }),
  contributeGoal: (id: number, amount: number) =>
    request<SavingsGoal>(`/savings-goals/${id}/contributions`, {
      method: "POST",
      body: JSON.stringify({ amount })
    })
};
