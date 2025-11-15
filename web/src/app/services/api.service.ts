import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import {catchError, Observable, of} from 'rxjs';
import { environment } from '../../../env';

import { TimeSeriesParams, TimeSeriesResponse } from '../shared/interface/timeSeries-interface';
import { TrendingItem } from '../shared/interface/trending-interface';

@Injectable({
  providedIn: 'root',
})
export class ApiService {
  private baseUrl = `http://localhost:${environment.apiPort}`;

  constructor(private http: HttpClient) {}

  getHealthCheck(): Observable<any> {
    return this.http.get(`${this.baseUrl}/api/health/check`);
  }

  getNews(): Observable<any> {
    return this.http.get(`${this.baseUrl}/api/news`);
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
      { source: 'coindesk',      value: 32, prev: 20, delta: 12, delta_pct:  0.60 },
      { source: 'cointelegraph', value: 18, prev: 25, delta: -7, delta_pct: -0.28 },
      { source: 'decrypt',       value: 14, prev: 10, delta:  4, delta_pct:  0.40 },
      { source: 'theblock',      value:  9, prev:  9, delta:  0, delta_pct:  0.00 },
      { source: 'beincrypto',    value: 11, prev:  8, delta:  3, delta_pct:  0.375 },
    ];
    return data.slice(0, limit);
  }
  getTopGainers(limit: number = 10): Observable<any[]> {
    const httpParams = new HttpParams().set('limit', String(limit));
    return this.http.get<any[]>(`${this.baseUrl}/api/crypto/gainers`, { params: httpParams })
      .pipe(
        catchError(error => {
          console.error('Error fetching top gainers:', error);
          return of(this.mockTopGainers(limit));
        })
      );
  }

  getTopLosers(limit: number = 10): Observable<any[]> {
    const httpParams = new HttpParams().set('limit', String(limit));
    return this.http.get<any[]>(`${this.baseUrl}/api/crypto/losers`, { params: httpParams })
      .pipe(
        catchError(error => {
          console.error('Error fetching top losers:', error);
          return of(this.mockTopLosers(limit));
        })
      );
  }

  private mockTopGainers(limit: number): any[] {
    const gainers = [
      { symbol: 'BTC', name: 'Bitcoin', price: 67500, change24h: 3250, changePercent24h: 5.06, volume24h: 45000000000, marketCap: 1330000000000 },
      { symbol: 'ETH', name: 'Ethereum', price: 3800, change24h: 180, changePercent24h: 4.97, volume24h: 25000000000, marketCap: 456000000000 },
      { symbol: 'SOL', name: 'Solana', price: 195, change24h: 8.5, changePercent24h: 4.56, volume24h: 3500000000, marketCap: 91000000000 },
      { symbol: 'AVAX', name: 'Avalanche', price: 42, change24h: 1.8, changePercent24h: 4.48, volume24h: 890000000, marketCap: 16500000000 },
      { symbol: 'DOT', name: 'Polkadot', price: 8.2, change24h: 0.34, changePercent24h: 4.32, volume24h: 420000000, marketCap: 10200000000 }
    ];
    return gainers.slice(0, limit);
  }

  private mockTopLosers(limit: number): any[] {
    const losers = [
      { symbol: 'DOGE', name: 'Dogecoin', price: 0.084, change24h: -0.0055, changePercent24h: -6.15, volume24h: 1200000000, marketCap: 12100000000 },
      { symbol: 'SHIB', name: 'Shiba Inu', price: 0.0000145, change24h: -0.0000009, changePercent24h: -5.84, volume24h: 450000000, marketCap: 8550000000 },
      { symbol: 'XRP', name: 'XRP', price: 0.52, change24h: -0.031, changePercent24h: -5.63, volume24h: 1800000000, marketCap: 29500000000 },
      { symbol: 'ADA', name: 'Cardano', price: 0.48, change24h: -0.025, changePercent24h: -4.95, volume24h: 680000000, marketCap: 16800000000 },
      { symbol: 'MATIC', name: 'Polygon', price: 0.92, change24h: -0.041, changePercent24h: -4.27, volume24h: 420000000, marketCap: 8520000000 }
    ];
    return losers.slice(0, limit);
  }

  // Écart-type (Standard Deviation) API methods
  getEcartType(symbol?: string): Observable<any> {
    const endpoint = symbol ? `/data/ecart-type/${symbol}` : '/data/ecart-type';
    return this.http.get(`${this.baseUrl}${endpoint}`)
      .pipe(
        catchError(error => {
          console.error('Error fetching écart-type data:', error);
          return of(this.mockEcartTypeData());
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

  getMarketOverview(): Observable<any> {
    return this.http.get(`${this.baseUrl}/api/market/overview`)
      .pipe(
        catchError(error => {
          console.error('Error fetching market overview:', error);
          return of(this.mockMarketOverview());
        })
      );
  }

  private mockMarketOverview(): any {
    return {
      bitcoin: {
        symbol: 'BTC',
        name: 'Bitcoin',
        price: 42350,
        change24h: 1035,
        changePercent24h: 2.5
      },
      ethereum: {
        symbol: 'ETH',
        name: 'Ethereum',
        price: 2680,
        change24h: -32.6,
        changePercent24h: -1.2
      },
      totalMarketCap: {
        value: '$1.85T',
        change: 0.8
      }
    };
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

  getTrending(params: { window: string; baseline: string; limit?: number }): Observable<TrendingItem[]> {
    const httpParams = new HttpParams()
      .set('window', params.window)
      .set('baseline', params.baseline)
      .set('limit', String(params.limit ?? 5));

    return this.http
      .get<TrendingItem[]>(`${this.baseUrl}/metrics/trending`, {params: httpParams})
      .pipe(
        catchError((err) => {
          console.error('getTrending fallback → mock (reason):', err);
          return of(this.mockTrending(params.limit ?? 5));
        })
      );
  }
}
