import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { catchError, map, Observable, of, timeout, retry } from 'rxjs';
import { environment } from '../../../env';

import { TimeSeriesParams, TimeSeriesResponse } from '../shared/interface/timeSeries-interface';
import { TrendingItem } from '../shared/interface/trending-interface';

@Injectable({
  providedIn: 'root',
})
export class ApiService {
  public baseUrl = environment.production
    ? `http://api:${environment.apiPort}`
    : `http://localhost:${environment.apiPort}`;

  // API timeout in milliseconds (30 seconds for slow database queries)
  private readonly API_TIMEOUT = 30000;

  constructor(private http: HttpClient) {}

  getHealthCheck(): Observable<any> {
    return this.http.get(`${this.baseUrl}/api/health/check`);
  }

  getNews(limit: number = 50): Observable<any> {
    const httpParams = new HttpParams().set('limit', String(limit));
    return this.http.get<any>(`${this.baseUrl}/data/news`, { params: httpParams })
      .pipe(
        catchError(error => {
          console.error('Error fetching news:', error);
          return of({ response: { articles: [] } });
        })
      );
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
  getTopGainers(limit: number = 10): Observable<any> {
    const httpParams = new HttpParams().set('limit', String(limit));
    return this.http
      .get<any>(`${this.baseUrl}/api/crypto/gainers`, { params: httpParams })
      .pipe(map((payload) => this.extractResponse(payload)));
  }

  getTopLosers(limit: number = 10): Observable<any> {
    const httpParams = new HttpParams().set('limit', String(limit));
    return this.http
      .get<any>(`${this.baseUrl}/api/crypto/losers`, { params: httpParams })
      .pipe(map((payload) => this.extractResponse(payload)));
  }

  getMarketOverview(): Observable<any> {
    return this.http
      .get<any>(`${this.baseUrl}/api/market/overview`)
      .pipe(map((payload) => this.extractResponse(payload)));
  }

  getHomeDashboard(limit: number = 5): Observable<any> {
    const httpParams = new HttpParams().set('limit', String(limit));
    return this.http
      .get<any>(`${this.baseUrl}/api/market/home`, { params: httpParams })
      .pipe(
        timeout(this.API_TIMEOUT),
        retry(1), // Retry once on failure
        map((payload) => this.extractResponse(payload)),
        catchError((error) => {
          console.error('Home dashboard API error:', error);
          if (error.name === 'TimeoutError') {
            throw new Error('Le serveur met trop de temps à répondre. Réessayez plus tard.');
          }
          throw error;
        })
      );
  }

  getMarketTrending(params: { window: string; limit?: number }): Observable<TrendingItem[]> {
    const httpParams = new HttpParams()
      .set('window', params.window)
      .set('limit', String(params.limit ?? 5));
    return this.http
      .get<any>(`${this.baseUrl}/api/market/trending`, { params: httpParams })
      .pipe(
        map((payload) => {
          const response = this.extractResponse(payload);
          // Handle nested structure: response.data.trending or response.trending
          if (response?.data?.trending) {
            return response.data.trending;
          }
          if (response?.trending) {
            return response.trending;
          }
          if (Array.isArray(response)) {
            return response;
          }
          console.warn('Unexpected trending payload shape:', response);
          return [];
        })
      );
  }

  // Écart-type (Standard Deviation) API methods
  getEcartType(symbol?: string, params?: {
    period?: number;
    limit?: number;
    date_from?: string;
    date_to?: string;
  }): Observable<any> {
    let httpParams = new HttpParams();

    if (params?.period) {
      httpParams = httpParams.set('period', String(params.period));
    }
    if (params?.limit) {
      httpParams = httpParams.set('limit', String(params.limit));
    }
    if (params?.date_from) {
      httpParams = httpParams.set('date_from', params.date_from);
    }
    if (params?.date_to) {
      httpParams = httpParams.set('date_to', params.date_to);
    }
    if (symbol && !symbol) {
      // This won't execute, but keeping for general endpoint compatibility
      httpParams = httpParams.set('symbol', symbol);
    }

    const endpoint = symbol ? `/data/ecart-type/${symbol}` : '/data/ecart-type';
    return this.http.get(`${this.baseUrl}${endpoint}`, { params: httpParams })
      .pipe(
        map((payload) => {
          const response = this.extractResponse(payload);
          // Return the response directly - it may contain warnings or data
          return response;
        }),
        catchError(error => {
          console.error('Error fetching écart-type data:', error);
          // Re-throw error so component can handle it
          throw error;
        })
      );
  }

  calculateEcartType(): Observable<any> {
    return this.http.post(`${this.baseUrl}/data/ecart-type/calculate`, {})
      .pipe(
        catchError(error => {
          console.error('Error triggering écart-type calculation:', error);
          return of({ status: 'error', message: 'Failed to trigger calculation' });
        })
      );
  }

  // RSI (Relative Strength Index) API methods
  getRsiAnalysis(params?: {
    period?: number;
    limit?: number;
    symbol?: string;
    date_from?: string;
    date_to?: string;
  }): Observable<any> {
    let httpParams = new HttpParams();

    if (params?.period) {
      httpParams = httpParams.set('period', String(params.period));
    }
    if (params?.limit) {
      httpParams = httpParams.set('limit', String(params.limit));
    }
    if (params?.symbol) {
      httpParams = httpParams.set('symbol', params.symbol);
    }
    if (params?.date_from) {
      httpParams = httpParams.set('date_from', params.date_from);
    }
    if (params?.date_to) {
      httpParams = httpParams.set('date_to', params.date_to);
    }

    return this.http.get<any>(`${this.baseUrl}/data/rsi`, { params: httpParams })
      .pipe(
        catchError(error => {
          console.error('Error fetching RSI analysis:', error);
          return of({ status: 'error', message: 'Failed to fetch RSI analysis' });
        })
      );
  }

  getSymbolRsiAnalysis(symbol: string, params?: {
    period?: number;
    limit?: number;
    date_from?: string;
    date_to?: string;
  }): Observable<any> {
    let httpParams = new HttpParams();

    if (params?.period) {
      httpParams = httpParams.set('period', String(params.period));
    }
    if (params?.limit) {
      httpParams = httpParams.set('limit', String(params.limit));
    }
    if (params?.date_from) {
      httpParams = httpParams.set('date_from', params.date_from);
    }
    if (params?.date_to) {
      httpParams = httpParams.set('date_to', params.date_to);
    }

    return this.http.get<any>(`${this.baseUrl}/data/rsi/${symbol}`, { params: httpParams })
      .pipe(
        catchError(error => {
          console.error('Error fetching symbol RSI analysis:', error);
          return of(error);
        })
      );
  }

  triggerRsiCalculation(params?: {
    period?: number;
    limit?: number;
  }): Observable<any> {
    let httpParams = new HttpParams();

    if (params?.period) {
      httpParams = httpParams.set('period', String(params.period));
    }
    if (params?.limit) {
      httpParams = httpParams.set('limit', String(params.limit));
    }

    return this.http.post<any>(`${this.baseUrl}/data/rsi/calculate`, {}, { params: httpParams })
      .pipe(
        catchError(error => {
          console.error('Error triggering RSI calculation:', error);
          return of({ status: 'error', message: 'Failed to trigger RSI calculation' });
        })
      );
  }


  getTrending(params: { window: string; baseline: string; limit?: number }): Observable<TrendingItem[]> {
    // Convert frontend parameters to API parameters
    const now = new Date();
    const to = now.toISOString();

    // Calculate 'from' time based on baseline (e.g., "24h" -> 24 hours ago)
    const baselineHours = parseInt(params.baseline.replace('h', '')) || 24;
    const from = new Date(now.getTime() - (baselineHours * 60 * 60 * 1000)).toISOString();

    // Convert window to bucket format
    const bucket = params.window === '1h' ? 'hour' : 'day';

    const httpParams = new HttpParams()
      .set('from', from)
      .set('to', to)
      .set('bucket', bucket)
      .set('limit', String(params.limit ?? 5));

    return this.http
      .get<{ response?: TrendingItem[] } | TrendingItem[]>(`${this.baseUrl}/metrics/trending`, { params: httpParams })
      .pipe(
        map((payload) => {
          const data = this.extractResponse(payload);
          if (Array.isArray(data)) {
            return data;
          }
          console.warn('Unexpected trending payload shape, returning empty list');
          return [];
        })
      );
  }

  getMarketStats(): Observable<any> {
    return this.http
      .get<any>(`${this.baseUrl}/api/market/stats`)
      .pipe(map((payload) => this.extractResponse(payload)));
  }

  getMovingAverages(params: {
    from: string;
    to: string;
    window: number;
    ma_type: string;
    bucket: string;
    symbol?: string;
    limit?: number;
  }): Observable<any> {
    let httpParams = new HttpParams()
      .set('from', params.from)
      .set('to', params.to)
      .set('window', String(params.window))
      .set('ma_type', params.ma_type)
      .set('bucket', params.bucket);

    if (params.symbol) {
      httpParams = httpParams.set('symbol', params.symbol);
    }
    if (params.limit) {
      httpParams = httpParams.set('limit', String(params.limit));
    }

    return this.http.get<any>(`${this.baseUrl}/algo/moving-averages`, { params: httpParams });
  }

  // Random Forest API methods
  trainRandomForest(params: {
    symbol: string | null;
    n_estimators: number;
    max_depth: number;
    test_size: number;
  }): Observable<any> {
    let httpParams = new HttpParams()
      .set('n_estimators', String(params.n_estimators))
      .set('max_depth', String(params.max_depth))
      .set('test_size', String(params.test_size));

    if (params.symbol) {
      httpParams = httpParams.set('symbol', params.symbol);
    }

    return this.http.post<any>(`${this.baseUrl}/algo/random-forest/train`, {}, { params: httpParams });
  }

  predictRandomForest(symbol: string, recentCount: number): Observable<any> {
    const httpParams = new HttpParams()
      .set('symbol', symbol)
      .set('recent_count', String(recentCount));

    return this.http.get<any>(`${this.baseUrl}/algo/random-forest/predict`, { params: httpParams });
  }

  getRandomForestInfo(): Observable<any> {
    return this.http.get<any>(`${this.baseUrl}/algo/random-forest/info`);
  }

  getAvailableSymbols(): Observable<any> {
    return this.http.get<any>(`${this.baseUrl}/api/symbols`);
  }

  private extractResponse<T = any>(payload: any): T {
    if (payload?.response?.data !== undefined) {
      return payload.response.data as T;
    }
    if (payload?.response !== undefined) {
      return payload.response as T;
    }
    return payload as T;
  }
}
