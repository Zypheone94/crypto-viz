import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';
import { distinctUntilChanged } from 'rxjs/operators';

@Injectable({
  providedIn: 'root',
})
export class StoreService {
  // BehaviorSubject to hold the data
  private dataSubject = new BehaviorSubject<any>(null);
  // Observable for components to subscribe to
  public data$: Observable<any> = this.dataSubject
    .asObservable()
    .pipe(distinctUntilChanged((prev, curr) => JSON.stringify(prev) === JSON.stringify(curr)));

  // Method to update the data
  setData(data: any) {
    this.dataSubject.next(data);
  }

  // Method to get the current value of the data
  getData(): any {
    return this.dataSubject.getValue();
  }
}
