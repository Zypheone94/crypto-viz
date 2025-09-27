import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../env';

@Injectable({
  providedIn: 'root',
})
export class ApiService {
  private baseUrl = `http://localhost:${environment.apiPort}`;

  constructor(private http: HttpClient) {}

  getHealthCheck(): Observable<any> {
    return this.http.get(`${this.baseUrl}/health/check`);
  }
}
