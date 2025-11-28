import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { TimeSeries } from './time-series';
import { TrendingNowComponent } from './trending-now';
import { EcartTypeGlissantComponent } from './ecart-type-glissant';
import { RsiComponent } from './rsi';
import { MovingAveragesComponent } from './moving-averages';
import { RandomForestComponent } from './random-forest';
import { MatIconModule } from '@angular/material/icon';
import { LinearRegressionNextHourComponent } from './linear-regression';

type MetricsView =
  | 'timeseries'
  | 'trending'
  | 'ecartTypeGlissant'
  | 'rsi'
  | 'movingAverages'
  | 'randomForest'
  | 'linearRegression';

@Component({
  selector: 'app-metrics-switcher',
  standalone: true,
  imports: [
    CommonModule,
    TimeSeries,
    TrendingNowComponent,
    EcartTypeGlissantComponent,
    RsiComponent,
    MovingAveragesComponent,
    RandomForestComponent,
    LinearRegressionNextHourComponent,
    MatIconModule,
  ],
  templateUrl: './metrics-switcher.html',
  styleUrls: ['./time-series.css'],
})
export class MetricsSwitcherComponent {
  view: MetricsView = 'timeseries';

  select(view: MetricsView) {
    this.view = view;
  }
}
