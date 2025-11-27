export interface TrendingItem {
  source: string;
  value: number;
  delta_pct: number;
  previous?: number;
  delta?: number;
}
