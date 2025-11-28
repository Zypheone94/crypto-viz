import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';

import { TrendingNowComponent } from './trending-now';
import { EcartTypeGlissantComponent } from './ecart-type-glissant';
import { RsiComponent } from './rsi';
import { MovingAveragesComponent } from './moving-averages';
import { RandomForestComponent } from './random-forest';
import { MatIconModule } from '@angular/material/icon';

@Component({
  selector: 'app-metrics-switcher',
  standalone: true,
  imports: [CommonModule, TimeSeries, TrendingNowComponent, EcartTypeGlissantComponent, RsiComponent, MovingAveragesComponent, RandomForestComponent, MatIconModule],
  templateUrl: './metrics-switcher.html',
  styleUrls: ['./time-series.css'],
})
export class MetricsSwitcherComponent {
  view: 'timeseries' | 'trending' | 'ecartTypeGlissant' | 'rsi' | 'movingAverages' | 'randomForest' = 'timeseries';

  select(view: 'timeseries' | 'trending' | 'ecartTypeGlissant' | 'rsi' | 'movingAverages' | 'randomForest') {
    this.view = view;
  }
}
