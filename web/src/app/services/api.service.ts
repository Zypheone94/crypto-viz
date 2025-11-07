import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { catchError, Observable, of } from 'rxjs';
import { environment } from '../../../env';

import { TimeSeriesParams, TimeSeriesResponse } from '../shared/interface/timeSeries-interface';
import { TrendingItem } from '../shared/interface/trending-interface';

@Injectable({
  providedIn: 'root',
})
export class ApiService {
  private baseUrl = `http://localhost:${environment.apiPort}`;

  constructor(private http: HttpClient) { }

  getHealthCheck(): Observable<any> {
    return this.http.get(`${this.baseUrl}/api/health/check`);
  }

  getTimeseries(params: TimeSeriesParams | null): Observable<TimeSeriesResponse[]> {
    const httpParams = new HttpParams()
      .set('from', params?.from || '')
      .set('to', params?.to || '')
      .set('bucket', params?.bucket || '');

    return this.http.get<TimeSeriesResponse[]>(`${this.baseUrl}/metrics/timeseries`, {
      params: httpParams,
    });
  }
  private mockTrending(limit = 5): TrendingItem[] {
    const data: TrendingItem[] = [
      { source: 'coindesk', value: 32, prev: 20, delta: 12, delta_pct: 0.60 },
      { source: 'cointelegraph', value: 18, prev: 25, delta: -7, delta_pct: -0.28 },
      { source: 'decrypt', value: 14, prev: 10, delta: 4, delta_pct: 0.40 },
      { source: 'theblock', value: 9, prev: 9, delta: 0, delta_pct: 0.00 },
      { source: 'beincrypto', value: 11, prev: 8, delta: 3, delta_pct: 0.375 },
    ];
    return data.slice(0, limit);
  }
  getTrending(params: { window: string; baseline: string; limit?: number }): Observable<TrendingItem[]> {
    // Adapter les paramètres pour l'API SQLite
    // window et baseline sont des dates ISO, on les utilise comme from/to
    const httpParams = new HttpParams()
      .set('from', params.baseline)  // baseline = date de début
      .set('to', params.window)      // window = date de fin
      .set('bucket', 'day')          // bucket par défaut
      .set('limit', String(params.limit ?? 5));

    return this.http
      .get<TrendingItem[]>(`${this.baseUrl}/metrics/trending`, { params: httpParams })
      .pipe(
        catchError((err: any) => {
          console.error('getTrending fallback → mock (reason):', err);
          return of(this.mockTrending(params.limit ?? 5));
        })
      );
  }
}
