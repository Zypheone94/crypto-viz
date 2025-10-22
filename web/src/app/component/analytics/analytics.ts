import { CommonModule } from '@angular/common';
import { Component, OnDestroy, OnInit } from '@angular/core';
import { interval, Subscription } from 'rxjs';
import { TimeSeries } from './components/time-series';
import {TrendingNowComponent} from './components/trending-now';
import {MetricsSwitcherComponent} from './components/metrics-switcher';

@Component({
  selector: 'app-analytics',
  standalone: true,
  imports: [CommonModule, MetricsSwitcherComponent],
  templateUrl: './analytics.html',
  styleUrls: ['./analytics.css'],
})
export class Analytics implements OnInit, OnDestroy {
  data: any = null;

  constructor() {}

  // Subscription to manage the interval
  private intervalSubscription: Subscription = new Subscription();
  // Interval duration in milliseconds
  private intervalDuration: number = 5000;

  ngOnInit() {
    this.intervalSubscription = interval(this.intervalDuration).subscribe((n) => {
      //console.log('tick', n);
    });
  }

  ngOnDestroy(): void {
    this.intervalSubscription.unsubscribe();
    console.log('Component unmounted');
  }
}
