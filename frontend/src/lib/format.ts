export const today = () => new Date().toISOString().slice(0, 10);
export const currentMonth = () => new Date().toISOString().slice(0, 7);

import type { Currency } from "../types";

export const money = (value: number, currency: Currency = "COP", locale = "es-CO") =>
  new Intl.NumberFormat(locale, {
    style: "currency",
    currency,
    maximumFractionDigits: 0
  }).format(value || 0);

export const categoryName = (key: string) => {
  const names: Record<string, string> = {
    expense: "General",
    food: "Comida",
    vehicle: "Vehículo",
    housing: "Vivienda",
    transport: "Transporte",
    entertainment: "Entretenimiento",
    subscriptions: "Suscripciones",
    groceries: "Mercado",
    health: "Salud"
  };
  return names[key] ?? key;
};

export const friendlyDate = (date: string) =>
  new Intl.DateTimeFormat("es", { day: "numeric", month: "short" }).format(new Date(`${date}T00:00:00`));
