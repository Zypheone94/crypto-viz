import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { TimeSeries } from './time-series';
import { TrendingNowComponent } from './trending-now';
@Component({
  selector: 'app-metrics-switcher',
  standalone: true,
  imports: [CommonModule, TimeSeries, TrendingNowComponent],
  templateUrl: './metrics-switcher.html',
  styleUrls: ['./time-series.css'],
})
export class MetricsSwitcherComponent {
  view: 'timeseries' | 'trending' = 'timeseries';

  select(view: 'timeseries' | 'trending') {
    this.view = view;
  }
}
