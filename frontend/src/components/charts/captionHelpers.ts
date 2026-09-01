/** Human wording for the colour dimension in captions: "Account" -> "account", "State" -> "job state". */
export function dimensionLabel(colorBy: string | null | undefined): string | null {
  if (!colorBy) return null;
  const labels: Record<string, string> = {
    Account: 'account',
    Partition: 'partition',
    State: 'job state',
    QOS: 'QoS',
    User: 'user',
  };
  return labels[colorBy] ?? colorBy.toLowerCase();
}

/** Append ", stacked by <dim>" when a colour dimension is active. */
export function stackedBy(base: string, dim: string | null): string {
  return dim ? `${base.replace(/\.$/, '')}, stacked by ${dim}.` : base;
}
