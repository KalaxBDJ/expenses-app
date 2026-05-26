import { AlertCircle, Loader2, PlusCircle } from "lucide-react";

type Props = {
  variant: "empty" | "loading" | "error";
  title: string;
  text: string;
  actionLabel?: string;
  onAction?: () => void;
};

export function StateBlock({ variant, title, text, actionLabel, onAction }: Props) {
  const Icon = variant === "loading" ? Loader2 : variant === "error" ? AlertCircle : PlusCircle;

  return (
    <section className={`state-block ${variant}`}>
      <Icon className={variant === "loading" ? "spin" : ""} size={28} />
      <h2>{title}</h2>
      <p>{text}</p>
      {actionLabel && onAction ? (
        <button className="primary-button" onClick={onAction}>
          {actionLabel}
        </button>
      ) : null}
    </section>
  );
}
