import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';

import { TrendingNowComponent } from './trending-now';
import { EcartTypeGlissantComponent } from './ecart-type-glissant';
import { RsiComponent } from './rsi';
import { CrossCorrelationComponent } from './cross-correlation';
import { MovingAveragesComponent } from './moving-averages';
import { RandomForestComponent } from './random-forest';
import { MatIconModule } from '@angular/material/icon';

@Component({
  selector: 'app-metrics-switcher',
  standalone: true,
  imports: [CommonModule, TrendingNowComponent, EcartTypeGlissantComponent, RsiComponent, CrossCorrelationComponent, MovingAveragesComponent, RandomForestComponent, MatIconModule],
  templateUrl: './metrics-switcher.html',
  styleUrls: ['./time-series.css'],
})
export class MetricsSwitcherComponent {
  // Metrics switcher component for analytics dashboard
  view: 'trending' | 'ecartTypeGlissant' | 'rsi' | 'crossCorrelation' | 'movingAverages' | 'randomForest' = 'trending';

  select(view: 'trending' | 'ecartTypeGlissant' | 'rsi' | 'crossCorrelation' | 'movingAverages' | 'randomForest') {
    this.view = view;
  }
}


