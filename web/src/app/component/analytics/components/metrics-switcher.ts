import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { TimeSeries } from './time-series';
import { TrendingNowComponent } from './trending-now';
import { TopGainersComponent } from './top-gainers';
import { TopLosersComponent } from './top-losers';
import { EcartTypeGlissantComponent } from './ecart-type-glissant';
import { RsiComponent } from './rsi';
import { MatIconModule } from '@angular/material/icon';

@Component({
  selector: 'app-metrics-switcher',
  standalone: true,
  imports: [CommonModule, TimeSeries, TrendingNowComponent, TopGainersComponent, TopLosersComponent, EcartTypeGlissantComponent, RsiComponent, MatIconModule],
  templateUrl: './metrics-switcher.html',
  styleUrls: ['./time-series.css'],
})
export class MetricsSwitcherComponent {
  view: 'timeseries' | 'trending' | 'topGainers' | 'topLosers' | 'ecartTypeGlissant' | 'rsi' = 'timeseries';

  select(view: 'timeseries' | 'trending' | 'topGainers' | 'topLosers' | 'ecartTypeGlissant' | 'rsi') {
    this.view = view;
  }
}
