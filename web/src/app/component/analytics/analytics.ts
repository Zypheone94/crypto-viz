import { CommonModule } from '@angular/common';
import { Component, OnDestroy, OnInit } from '@angular/core';
import { interval, Subscription } from 'rxjs';
import { TimeSeries } from './components/time-series';
import { StoreService } from '../../services/store.service';

@Component({
  selector: 'app-analytics',
  standalone: true,
  imports: [CommonModule, TimeSeries],
  templateUrl: './analytics.html',
  styleUrls: ['./analytics.css'],
})
export class Analytics implements OnInit, OnDestroy {
  data: any = null;

  constructor(private storeService: StoreService) {}

  // Subscription to manage the interval
  private intervalSubscription: Subscription = new Subscription();
  // Interval duration in milliseconds
  private intervalDuration: number = 5000;

  ngOnInit() {
    this.intervalSubscription = interval(this.intervalDuration).subscribe((n) => {
      console.log('tick', n);
    });
    this.data = this.storeService.getData();
  }

  ngOnDestroy(): void {
    this.intervalSubscription.unsubscribe();
    console.log('Component unmounted');
  }
}
