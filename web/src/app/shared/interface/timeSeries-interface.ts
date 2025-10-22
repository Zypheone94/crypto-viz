export interface TimeSeriesParams {
  from: string;
  to: string;
  bucket: 'hour' | 'day';
}

export interface TimeSeriesResponse {
  timestamp: string;
  value: number;
}
