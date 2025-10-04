import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';

@Injectable({
  providedIn: 'root',
})
export class StoreService {
  // BehaviorSubject to hold the data
  private dataSubject = new BehaviorSubject<any>(null);
  // Observable for components to subscribe to
  public data$: Observable<any> = this.dataSubject.asObservable();

  // Method to update the data
  setData(data: any) {
    this.dataSubject.next(data);
  }

  // Method to get the current value of the data
  getData(): any {
    return this.dataSubject.getValue();
  }
}
