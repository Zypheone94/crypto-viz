import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../env';

import { TimeSeriesParams, TimeSeriesResponse } from '../shared/interface/timeSeries-interface';

@Injectable({
  providedIn: 'root',
})
export class ApiService {
  private baseUrl = `http://localhost:${environment.apiPort}`;

  constructor(private http: HttpClient) {}

  getHealthCheck(): Observable<any> {
    return this.http.get(`${this.baseUrl}/api/health/check`);
  }

  getTimeseries(params: TimeSeriesParams): Observable<TimeSeriesResponse[]> {
    const httpParams = new HttpParams()
      .set('from', params.from)
      .set('to', params.to)
      .set('bucket', params.bucket);

    return this.http.get<TimeSeriesResponse[]>(`${this.baseUrl}/metrics/timeseries`, { params: httpParams });
  }
}
