import { Component, Input, OnDestroy, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatIconModule } from '@angular/material/icon';
import { BaseChartDirective } from 'ng2-charts';
import { ChartConfiguration, ChartOptions } from 'chart.js';

import { ApiService } from '../../../services/api.service';
import { ComponentState } from '../../../shared/enums/component-state.enum';
import { TrendingItem } from '../../../shared/interface/trending-interface';
import { Subscription, timer } from 'rxjs';

@Component({
  selector: 'app-trending-now',
  standalone: true,
  imports: [CommonModule, MatProgressSpinnerModule, MatIconModule, BaseChartDirective],
  templateUrl: 'trending-now.html',
  styleUrls: ['./time-series.css'],
  styles: [`
    .trending-now {
      background: #ffffff;
      border-radius: 12px;
      padding: 1.5rem;
      box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
      border: 1px solid #e0e0e0;
    }

    .trending-title {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      margin: 0 0 1.5rem 0;
      font-size: 1.25rem;
      font-weight: 600;
      color: #333;
    }

    .title-icon {
      color: #4CAF50;
    }

    .loading-container, .error-container, .no-result-container {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      height: 200px;
      gap: 1rem;
    }

    .error-message {
      color: #d32f2f;
      font-weight: 500;
    }

    .table {
      width: 100%;
      border-collapse: collapse;
      margin-bottom: 1.5rem;
      background: #f8f9fa;
      border-radius: 8px;
      overflow: hidden;
    }

    .table th {
      background: #f1f5f9;
      padding: 12px;
      text-align: left;
      font-weight: 600;
      color: #374151;
      border-bottom: 2px solid #e2e8f0;
    }

    .table td {
      padding: 12px;
      border-bottom: 1px solid #e2e8f0;
      color: #4b5563;
    }

    .table tbody tr:hover {
      background: #f8fafc;
    }

    .chart-container {
      height: 360px;
      margin-top: 1rem;
      background: #f8f9fa;
      border-radius: 8px;
      padding: 1rem;
    }

    .trend-up {
      color: #00c853;
      font-weight: 600;
    }

    .trend-down {
      color: #d32f2f;
      font-weight: 600;
    }

    .trend-flat {
      color: #666666;
      font-weight: 500;
    }

    @media (max-width: 768px) {
      .trending-now {
        padding: 1rem;
      }
      
      .chart-container {
        height: 300px;
      }
      
      .table {
        font-size: 0.875rem;
      }
      
      .table th, .table td {
        padding: 8px;
      }
    }
  `]
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
      x: { 
        ticks: { 
          autoSkip: false,
          color: '#666',
          font: {
            size: 12,
            weight: 'normal'
          }
        },
        grid: {
          display: false
        }
      },
      y: {
        title: { 
          display: true, 
          text: 'Variation %',
          color: '#374151',
          font: {
            size: 14,
            weight: 'bold'
          }
        },
        beginAtZero: true,
        ticks: {
          color: '#666',
          callback: function(value) {
            return value + '%';
          }
        },
        grid: {
          color: 'rgba(0, 0, 0, 0.1)',
          lineWidth: 1
        }
      },
    },
    plugins: {
      legend: { 
        display: false 
      },
      tooltip: {
        backgroundColor: 'rgba(0, 0, 0, 0.8)',
        titleColor: '#fff',
        bodyColor: '#fff',
        borderColor: '#ffd700',
        borderWidth: 1,
        cornerRadius: 8,
        displayColors: true,
        callbacks: {
          label: (ctx) => {
            const val = ctx.raw as number;
            const symbol = ctx.label;
            return `${symbol}: ${val.toFixed(2)}%`;
          },
        },
      },
    },
    elements: {
      bar: {
        borderRadius: 4,
        borderSkipped: false,
      }
    }
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
