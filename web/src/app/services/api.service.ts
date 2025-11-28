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
          const data = this.extractResponse<{ trending?: TrendingItem[] }>(payload);
          return data?.trending ?? [];
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
    if (symbol) {
      httpParams = httpParams.set('symbol', symbol);
    }

    const endpoint = symbol ? `/data/ecart-type/${symbol}` : '/data/ecart-type';
    return this.http.get(`${this.baseUrl}${endpoint}`, { params: httpParams })
      .pipe(
        map((payload) => this.extractResponse(payload)),
        catchError(error => {
          console.error('Error fetching écart-type data:', error);
          throw error; // Re-throw error instead of returning mock data
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
          return of(this.mockRsiData());
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
          return of(this.mockSymbolRsiData(symbol));
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


  private mockEcartTypeData(): any {
    // Generate mock rolling standard deviation data
    const data = [];
    const now = new Date();

    for (let i = 30; i >= 0; i--) {
      const date = new Date(now.getTime() - i * 24 * 60 * 60 * 1000);
      const baseValue = 2.5;
      const volatility = Math.sin(i * 0.2) * 1.5 + Math.random() * 0.5;

      data.push({
        timestamp: date.toISOString(),
        value: Math.max(0.1, baseValue + volatility),
        label: date.toLocaleDateString('fr-FR', { month: 'short', day: 'numeric' })
      });
    }

    return {
      symbol: 'BTC',
      window_days: 14,
      data: data,
      stats: {
        current: data[data.length - 1]?.value || 0,
        average: data.reduce((sum, item) => sum + item.value, 0) / data.length,
        max: Math.max(...data.map(item => item.value)),
        min: Math.min(...data.map(item => item.value))
      }
    };
  }

  private mockRsiData(): any {
    // Generate mock RSI analysis data
    const symbols = ['BTC', 'ETH', 'ADA'];
    const latestData = symbols.map(symbol => {
      const rsi = 30 + Math.random() * 40; // RSI between 30-70
      return {
        symbol,
        current_rsi: rsi,
        current_signal: rsi > 70 ? 'overbought' : rsi < 30 ? 'oversold' : 'neutral',
        current_strength: rsi > 50 ? 'bullish' : 'bearish',
        latest_price: Math.random() * 100,
        current_momentum: (Math.random() - 0.5) * 10
      };
    });

    const summary = symbols.map(symbol => ({
      symbol,
      avg_rsi: 45 + Math.random() * 10,
      max_rsi: 70 + Math.random() * 20,
      min_rsi: 10 + Math.random() * 20,
      overbought_periods: Math.floor(Math.random() * 5),
      oversold_periods: Math.floor(Math.random() * 3),
      dominant_signal: 'neutral',
      data_points: 50 + Math.floor(Math.random() * 50)
    }));

    return {
      level: 'info',
      message: 'RSI analysis completed (mock data)',
      response: {
        metadata: {
          period: 14,
          total_records: 150,
          symbols_analyzed: symbols.length,
          analysis_timestamp: new Date().toISOString()
        },
        summary,
        latest_data: latestData
      }
    };
  }

  private mockSymbolRsiData(symbol: string): any {
    // Generate mock time series RSI data for a specific symbol
    const timeSeries = [];
    const now = new Date();

    for (let i = 20; i >= 0; i--) {
      const date = new Date(now.getTime() - i * 60 * 60 * 1000); // hourly data
      const baseRsi = 50;
      const rsi = Math.max(0, Math.min(100, baseRsi + Math.sin(i * 0.3) * 20 + (Math.random() - 0.5) * 10));

      timeSeries.push({
        ts: date.toISOString(),
        price_usd: 40000 + Math.sin(i * 0.2) * 5000 + Math.random() * 1000,
        rsi: rsi,
        rsi_signal: rsi > 70 ? 'overbought' : rsi < 30 ? 'oversold' : 'neutral',
        rsi_strength: rsi > 50 ? 'bullish' : 'bearish',
        rsi_momentum: (Math.random() - 0.5) * 5
      });
    }

    const latest = timeSeries[timeSeries.length - 1];

    return {
      level: 'info',
      message: `RSI analysis completed for ${symbol} (mock data)`,
      response: {
        symbol,
        period: 14,
        latest_stats: {
          price_usd: latest.price_usd,
          rsi: latest.rsi,
          rsi_signal: latest.rsi_signal,
          rsi_strength: latest.rsi_strength,
          rsi_momentum: latest.rsi_momentum
        },
        time_series: timeSeries,
        metadata: {
          total_points: timeSeries.length,
          date_range: {
            start: timeSeries[0]?.ts,
            end: timeSeries[timeSeries.length - 1]?.ts
          }
        }
      }
    };
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
