import { Component, Input, OnDestroy, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { BaseChartDirective } from 'ng2-charts';
import { ChartConfiguration, ChartOptions } from 'chart.js';

import { ApiService } from '../../../services/api.service';
import { ComponentState } from '../../../shared/enums/component-state.enum';
import { TrendingItem } from '../../../shared/interface/trending-interface';
import { Subscription, timer } from 'rxjs';

@Component({
  selector: 'app-trending-now',
  standalone: true,
  imports: [CommonModule, MatProgressSpinnerModule, BaseChartDirective],
  templateUrl: 'trending-now.html',
})
export class TrendingNowComponent implements OnInit, OnDestroy {
  componentState = ComponentState;
  currentState: ComponentState = ComponentState.LOADING;
  errorMessage = '';

  @Input() window = '1h';
  @Input() baseline = '24h';
  @Input() limit = 5;
  @Input() autoRefreshSec = 60;

  data: TrendingItem[] = [];
  private sub?: Subscription;

  public barChartData: ChartConfiguration<'bar'>['data'] = {
    labels: [],
    datasets: [
      {
        data: [],
        label: 'Δ % (Trending)',
        borderWidth: 1,
        backgroundColor: [],
        borderColor: [],
      } as any,
    ],
  };

  public barChartOptions: ChartOptions<'bar'> = {
    responsive: true,
    maintainAspectRatio: false,
    scales: {
      x: { ticks: { autoSkip: false } },
      y: {
        title: { display: true, text: 'Δ %' },
        beginAtZero: true,
      },
    },
    plugins: {
      legend: { display: true },
      tooltip: {
        callbacks: {
          label: (ctx) => {
            const val = ctx.raw as number;
            return `Δ %: ${val.toFixed(1)}%`;
          },
        },
      },
    },
  };

  constructor(private api: ApiService) {}

  ngOnInit(): void {
    this.fetch();
    if (this.autoRefreshSec && this.autoRefreshSec > 0) {
      this.sub = timer(this.autoRefreshSec * 1000, this.autoRefreshSec * 1000).subscribe(() => this.fetch());
    }
  }

  ngOnDestroy(): void {
    this.sub?.unsubscribe();
  }

  private fetch(): void {
    this.currentState = ComponentState.LOADING;

    this.api.getTrending({ window: this.window, baseline: this.baseline, limit: this.limit }).subscribe({
      next: (items) => {
        this.data = Array.isArray(items) ? items : [];
        if (!this.data.length) {
          this.currentState = ComponentState.EMPTY;
          this.applyChart([], []);
          return;
        }

        const top = [...this.data]
          .sort((a, b) => (b.delta_pct ?? 0) - (a.delta_pct ?? 0))
          .slice(0, this.limit);

        const labels = top.map((t) => t.source);
        const valuesPct = top.map((t) => (t.delta_pct ?? 0) * 100);

        // couleurs par barre : vert si hausse, rouge si baisse, gris si neutre
        const bgColors = valuesPct.map((v) =>
          v > 0 ? 'rgba(0, 200, 83, 0.6)' : v < 0 ? 'rgba(229, 57, 53, 0.6)' : 'rgba(158, 158, 158, 0.5)'
        );
        const bdColors = valuesPct.map((v) =>
          v > 0 ? 'rgba(0, 200, 83, 1)' : v < 0 ? 'rgba(211, 47, 47, 1)' : 'rgba(117, 117, 117, 1)'
        );

        this.applyChart(labels, valuesPct, bgColors, bdColors);
        this.currentState = ComponentState.READY;
      },
      error: (err) => {
        console.error('Erreur API /metrics/trending', err);
        this.currentState = ComponentState.ERROR;
        this.errorMessage =
          err?.error?.detail ??
          (typeof err?.message === 'string' ? err.message : 'Erreur lors de la récupération des tendances');
      },
    });
  }

  private applyChart(
    labels: string[],
    valuesPct: number[],
    bgColors: (string | CanvasGradient | CanvasPattern)[] = [],
    bdColors: (string | CanvasGradient | CanvasPattern)[] = []
  ) {
    this.barChartData = {
      labels,
      datasets: [
        {
          data: valuesPct,
          label: 'Δ % (Trending)',
          backgroundColor: bgColors,
          borderColor: bdColors,
          borderWidth: 1,
        } as any,
      ],
    };
  }

  trendArrow(item: TrendingItem): '▲' | '▼' | '–' {
    if (item.delta_pct > 0) return '▲';
    if (item.delta_pct < 0) return '▼';
    return '–';
  }
  trendClass(item: TrendingItem): string {
    if (item.delta_pct > 0) return 'trend-up';
    if (item.delta_pct < 0) return 'trend-down';
    return 'trend-flat';
  }
}
