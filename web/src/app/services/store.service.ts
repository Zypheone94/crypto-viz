import { Injectable } from '@angular/core';
import { BehaviorSubject, combineLatest, Observable } from 'rxjs';

@Injectable({
  providedIn: 'root',
})
export class StoreService {
  private dataA = new BehaviorSubject<any>(null);
  private dataB = new BehaviorSubject<any>(null);

  combined$ = combineLatest([this.dataA, this.dataB]);

  setData(periode: 'A' | 'B' | 'ALL', data: any) {
    if (periode === 'A') {
      this.dataA.next(data);
    } else if (periode === 'B') {
      this.dataB.next(data);
    } else if (periode === 'ALL') {
      this.dataA.next(null);
      this.dataB.next(null);
    }
  }

  getDataA(): Observable<any> {
    return this.dataA.asObservable();
  }

  getDataB(): Observable<any> {
    return this.dataB.asObservable();
  }
}
