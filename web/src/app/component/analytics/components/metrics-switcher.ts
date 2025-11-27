import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { TimeSeries } from './time-series';
import { TrendingNowComponent } from './trending-now';
import { EcartTypeGlissantComponent } from './ecart-type-glissant';
import { RsiComponent } from './rsi';
import { CrossCorrelationComponent } from './cross-correlation';
import { MatIconModule } from '@angular/material/icon';

@Component({
  selector: 'app-metrics-switcher',
  standalone: true,
  imports: [CommonModule, TimeSeries, TrendingNowComponent, EcartTypeGlissantComponent, RsiComponent, CrossCorrelationComponent, MatIconModule],
  templateUrl: './metrics-switcher.html',
  styleUrls: ['./time-series.css'],
})
export class MetricsSwitcherComponent {
  view: 'timeseries' | 'trending' | 'ecartTypeGlissant' | 'rsi' | 'correlation' = 'timeseries';

  select(view: 'timeseries' | 'trending' | 'ecartTypeGlissant' | 'rsi' | 'correlation') {
    this.view = view;
  }
}