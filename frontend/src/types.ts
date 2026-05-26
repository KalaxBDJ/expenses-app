export type View = "home" | "movements" | "add" | "budgets" | "goals";

export type Currency = "COP" | "USD" | "EUR" | "MXN" | "ARS" | "CLP" | "PEN" | "BRL";

export type User = {
  id: number;
  name: string;
  email: string;
  created_at: string;
};

export type UserConfig = {
  id: number;
  user_id: number;
  default_currency: Currency;
  locale: string;
  has_sms_api_key: boolean;
  sms_api_key_suffix?: string | null;
  created_at: string;
  updated_at: string;
};

export type AuthSession = {
  token: string;
  user: User;
  config: UserConfig;
};

export type Category = {
  id: number;
  key: string;
  name: string;
};

export type Expense = {
  id: number;
  user_id: number;
  amount: number;
  currency: Currency;
  date: string;
  category: string;
  description?: string | null;
  payment_method?: string | null;
  note?: string | null;
  source: string;
  created_at: string;
};

export type Income = {
  id: number;
  user_id: number;
  amount: number;
  currency: Currency;
  date: string;
  source: string;
  description?: string | null;
  created_at: string;
};

export type Budget = {
  id: number;
  user_id: number;
  month: string;
  category: string;
  amount: number;
  currency: Currency;
  spent: number;
  remaining: number;
  progress: number;
};

export type SavingsGoal = {
  id: number;
  user_id: number;
  name: string;
  target_amount: number;
  currency: Currency;
  target_date?: string | null;
  current_amount: number;
  progress: number;
  created_at: string;
};

export type DashboardSummary = {
  user_id: number;
  month: string;
  total_spent: number;
  total_income: number;
  balance: number;
  currency: Currency;
  previous_month_spent: number;
  spent_change_percent: number | null;
  spent_by_category: Array<{ category: string; total: number }>;
  budgets: Budget[];
  recent_expenses: Expense[];
};
