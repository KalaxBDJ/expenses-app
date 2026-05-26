type Props = {
  value: number;
  tone?: "calm" | "watch" | "soft-danger";
};

export function ProgressBar({ value, tone = "calm" }: Props) {
  const width = Math.max(0, Math.min(value, 1)) * 100;
  return (
    <div className={`progress ${tone}`} aria-hidden="true">
      <span style={{ width: `${width}%` }} />
    </div>
  );
}
