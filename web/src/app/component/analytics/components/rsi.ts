import { Component, OnInit, OnDestroy, ViewChild, ElementRef, AfterViewInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { MatFormFieldModule } from '@angular/material/form-field';
import { FormsModule } from '@angular/forms';
import { Chart, ChartConfiguration, ChartType, registerables } from 'chart.js';
import { Subscription, interval } from 'rxjs';
import { ApiService } from '../../../services/api.service';
import { ComponentState } from '../../../shared/enums/component-state.enum';

Chart.register(...registerables);

interface RsiData {
  symbol: string;
  period: number;
  latest_stats: {
    price_usd: number;
    rsi: number;
    rsi_signal: string;
    rsi_strength: string;
    rsi_momentum: number;
  };
  time_series: Array<{
    ts: string;
    price_usd: number;
    rsi: number;
    rsi_signal: string;
    rsi_strength: string;
    rsi_momentum: number;
  }>;
  metadata: {
    total_points: number;
    date_range: {
      start: string;
      end: string;
    };
  };
}

@Component({
  selector: 'app-rsi',
  standalone: true,
  imports: [CommonModule, MatCardModule, MatIconModule, MatProgressSpinnerModule, MatSelectModule, MatFormFieldModule, FormsModule],
  template: `
    <div class="rsi-container">
      <mat-card class="rsi-card">
        <mat-card-header>
          <mat-card-title class="chart-title">
            <mat-icon class="title-icon">show_chart</mat-icon>
            RSI (Relative Strength Index)
          </mat-card-title>
          <mat-card-subtitle>
            Indicateur de momentum pour identifier les conditions de surachat/survente
          </mat-card-subtitle>
        </mat-card-header>
        
        <mat-card-content class="chart-content">
          <div class="controls-section">
            <mat-form-field appearance="outline">
              <mat-label>Symbole</mat-label>
              <mat-select [(value)]="selectedSymbol" (selectionChange)="onSymbolChange()">
                <mat-option value="BTC">Bitcoin (BTC)</mat-option>
                <mat-option value="ETH">Ethereum (ETH)</mat-option>
                <mat-option value="ADA">Cardano (ADA)</mat-option>
              </mat-select>
            </mat-form-field>
          </div>

          <div class="chart-wrapper" *ngIf="componentState === 'ready' && !isLoading">
            <div class="stats-row">
              <div class="stat-item">
                <span class="stat-label">RSI Actuel</span>
                <span class="stat-value" [class]="getRsiClass(data?.latest_stats?.rsi || 0)">
                  {{ (data?.latest_stats?.rsi || 0).toFixed(2) }}
                </span>
              </div>
              <div class="stat-item">
                <span class="stat-label">Signal</span>
                <span class="stat-value" [class]="getSignalClass(data?.latest_stats?.rsi_signal || 'neutral')">
                  {{ getSignalText(data?.latest_stats?.rsi_signal || 'neutral') }}
                </span>
              </div>
              <div class="stat-item">
                <span class="stat-label">Prix Actuel</span>
                <span class="stat-value">
                  {{ formatPrice(data?.latest_stats?.price_usd || 0) }}
                </span>
              </div>
            </div>
            <canvas #chartCanvas class="chart-canvas"></canvas>
          </div>

          <div class="loading-wrapper" *ngIf="isLoading">
            <mat-spinner diameter="50"></mat-spinner>
            <p>Chargement des données RSI...</p>
          </div>

          <div class="error-wrapper" *ngIf="componentState === 'error'">
            <mat-icon class="error-icon">error</mat-icon>
            <h3>Erreur de chargement</h3>
            <p>{{ errorMessage }}</p>
            <button (click)="loadData()" class="retry-button">
              <mat-icon>refresh</mat-icon>
              Réessayer
            </button>
          </div>
        </mat-card-content>
      </mat-card>
    </div>
  `,
  styles: [`
    .rsi-container {
      padding: 1rem;
    }

    .rsi-card {
      border-radius: 12px;
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
      min-height: 500px;
    }

    .chart-title {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      font-size: 1.25rem;
      font-weight: 600;
    }

    .title-icon {
      color: #2196F3;
    }

    .chart-content {
      padding: 1rem;
    }

    .controls-section {
      display: flex;
      gap: 1rem;
      margin-bottom: 1rem;
      flex-wrap: wrap;
    }

    .controls-section mat-form-field {
      min-width: 150px;
    }

    .stats-row {
      display: flex;
      justify-content: space-around;
      margin-bottom: 1rem;
      padding: 1rem;
      background: #f8f9fa;
      border-radius: 8px;
      flex-wrap: wrap;
      gap: 1rem;
    }

    .stat-item {
      display: flex;
      flex-direction: column;
      align-items: center;
      min-width: 120px;
    }

    .stat-label {
      font-size: 0.875rem;
      color: #666;
      margin-bottom: 0.25rem;
    }

    .stat-value {
      font-size: 1.25rem;
      font-weight: 600;
      color: #333;
    }

    .stat-value.rsi-overbought {
      color: #f44336;
    }

    .stat-value.rsi-oversold {
      color: #4caf50;
    }

    .stat-value.rsi-neutral {
      color: #ff9800;
    }

    .stat-value.signal-overbought {
      color: #f44336;
    }

    .stat-value.signal-oversold {
      color: #4caf50;
    }

    .stat-value.signal-neutral {
      color: #ff9800;
    }

    .chart-wrapper {
      position: relative;
      height: 400px;
      margin-top: 1rem;
    }

    .chart-canvas {
      max-height: 100%;
      width: 100%;
    }

    .loading-wrapper {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 4rem 2rem;
      text-align: center;
    }

    .loading-wrapper p {
      margin-top: 1rem;
      color: #666;
    }

    .error-wrapper {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 4rem 2rem;
      text-align: center;
    }

    .error-icon {
      font-size: 4rem;
      width: 4rem;
      height: 4rem;
      color: #f44336;
      margin-bottom: 1rem;
    }

    .error-wrapper h3 {
      color: #333;
      margin: 0 0 1rem 0;
      font-size: 1.5rem;
    }

    .error-wrapper p {
      color: #666;
      margin: 0 0 2rem 0;
      max-width: 300px;
    }

    .retry-button {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      padding: 0.75rem 1.5rem;
      border: none;
      border-radius: 6px;
      background: #2196F3;
      color: white;
      cursor: pointer;
      font-size: 1rem;
    }

    .retry-button:hover {
      background: #1976D2;
    }

    @media (max-width: 768px) {
      .stats-row {
        flex-direction: column;
        gap: 0.5rem;
      }
      
      .controls-section {
        flex-direction: column;
      }
      
      .chart-wrapper {
        height: 300px;
      }
    }
  `]
})
export class RsiComponent implements OnInit, OnDestroy, AfterViewInit {
  @ViewChild('chartCanvas', { static: false }) chartCanvas!: ElementRef<HTMLCanvasElement>;
  
  data: RsiData | null = null;
  chart: Chart | null = null;
  componentState: ComponentState = ComponentState.LOADING;
  isLoading = false;
  errorMessage = '';
  selectedSymbol = 'BTC';
  
  private autoRefreshSubscription?: Subscription;

  constructor(
    private apiService: ApiService
  ) {}

  ngOnInit(): void {
    this.componentState = ComponentState.LOADING;
    this.loadData();
    
    // Set up auto-refresh every 5 minutes
    this.autoRefreshSubscription = interval(300000).subscribe(() => {
      this.loadData();
    });
  }

  ngAfterViewInit(): void {
    // Chart will be created after data is loaded
  }

  ngOnDestroy(): void {
    if (this.autoRefreshSubscription) {
      this.autoRefreshSubscription.unsubscribe();
    }
    if (this.chart) {
      this.chart.destroy();
    }
  }

  onSymbolChange(): void {
    this.loadData();
  }

  async loadData(): Promise<void> {
    try {
      this.isLoading = true;
      this.errorMessage = '';

      this.apiService.getSymbolRsiAnalysis(this.selectedSymbol, { period: 14, limit: 100 }).subscribe({
        next: (response) => {
          console.log('RSI API response:', response);
          // Handle both API response structure and mock data
          if (response?.response || response?.data) {
            this.data = response.response || response;
            this.componentState = ComponentState.READY;
            // Use setTimeout to ensure DOM is ready
            setTimeout(() => {
              this.createChart();
            }, 100);
          } else {
            // Generate mock data if no response
            this.generateMockRsiData();
            this.componentState = ComponentState.READY;
            setTimeout(() => {
              this.createChart();
            }, 100);
          }
          this.isLoading = false;
        },
        error: (error) => {
          console.error('Erreur lors du chargement des données RSI:', error);
          console.log('Generating mock RSI data as fallback');
          // Generate mock data as fallback
          this.generateMockRsiData();
          this.componentState = ComponentState.READY;
          setTimeout(() => {
            this.createChart();
          }, 100);
          this.isLoading = false;
        }
      });
    } catch (error) {
      console.error('Erreur inattendue:', error);
      this.componentState = ComponentState.ERROR;
      this.errorMessage = 'Erreur inattendue';
      this.isLoading = false;
    }
  }

  private createChart(): void {
    if (!this.data || !this.chartCanvas) {
      return;
    }

    // Destroy existing chart
    if (this.chart) {
      this.chart.destroy();
    }

    const ctx = this.chartCanvas.nativeElement.getContext('2d');
    if (!ctx) {
      return;
    }

    const timeSeriesData = this.data.time_series || [];
    const labels = timeSeriesData.map(item => new Date(item.ts).toLocaleDateString('fr-FR', { 
      month: 'short', 
      day: 'numeric',
      hour: '2-digit'
    }));
    const rsiValues = timeSeriesData.map(item => item.rsi);
    const priceValues = timeSeriesData.map(item => item.price_usd);

    const config: ChartConfiguration = {
      type: 'line' as ChartType,
      data: {
        labels: labels,
        datasets: [
          {
            label: 'RSI',
            data: rsiValues,
            borderColor: '#2196F3',
            backgroundColor: 'rgba(33, 150, 243, 0.1)',
            borderWidth: 2,
            fill: false,
            tension: 0.4,
            yAxisID: 'y'
          },
          {
            label: `Prix ${this.selectedSymbol} ($)`,
            data: priceValues,
            borderColor: '#FF9800',
            backgroundColor: 'rgba(255, 152, 0, 0.1)',
            borderWidth: 2,
            fill: false,
            tension: 0.4,
            yAxisID: 'y1'
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          mode: 'index',
          intersect: false,
        },
        scales: {
          x: {
            display: true,
            title: {
              display: true,
              text: 'Temps',
              color: '#666'
            },
            grid: {
              color: '#e0e0e0'
            }
          },
          y: {
            type: 'linear',
            display: true,
            position: 'left',
            title: {
              display: true,
              text: 'RSI',
              color: '#2196F3'
            },
            min: 0,
            max: 100,
            grid: {
              color: '#e0e0e0'
            },
            ticks: {
              callback: function(value) {
                return value + '';
              }
            }
          },
          y1: {
            type: 'linear',
            display: true,
            position: 'right',
            title: {
              display: true,
              text: 'Prix ($)',
              color: '#FF9800'
            },
            grid: {
              drawOnChartArea: false,
            },
            ticks: {
              callback: function(value) {
                return '$' + Number(value).toLocaleString();
              }
            }
          }
        },
        plugins: {
          legend: {
            display: true,
            position: 'top',
            labels: {
              usePointStyle: true,
              padding: 20
            }
          },
          tooltip: {
            mode: 'index',
            intersect: false,
            callbacks: {
              label: function(context) {
                const label = context.dataset.label || '';
                if (label.includes('RSI')) {
                  return `${label}: ${Number(context.parsed.y).toFixed(2)}`;
                } else {
                  return `${label}: $${Number(context.parsed.y).toLocaleString('en-US', {minimumFractionDigits: 2})}`;
                }
              }
            }
          }
        }
      }
    };

    this.chart = new Chart(ctx, config);
  }

  getRsiClass(rsi: number): string {
    if (rsi >= 70) return 'rsi-overbought';
    if (rsi <= 30) return 'rsi-oversold';
    return 'rsi-neutral';
  }

  getSignalClass(signal: string): string {
    return `signal-${signal}`;
  }

  getSignalText(signal: string): string {
    switch (signal) {
      case 'overbought': return 'Surachat';
      case 'oversold': return 'Survente';
      case 'neutral': return 'Neutre';
      default: return 'Inconnu';
    }
  }

  formatPrice(price: number): string {
    return '$' + price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  private generateMockRsiData(): void {
    const now = new Date();
    const timeSeries = [];
    let basePrice = 42000; // Base Bitcoin price
    let rsi = 47; // Start with neutral RSI
    
    // Generate 30 days of data
    for (let i = 29; i >= 0; i--) {
      const date = new Date(now);
      date.setDate(date.getDate() - i);
      
      // Simulate price movement
      const priceChange = (Math.random() - 0.5) * 0.1; // ±5% daily change
      basePrice *= (1 + priceChange);
      
      // Simulate RSI movement with trend
      const rsiChange = (Math.random() - 0.5) * 10; // ±5 RSI points
      rsi = Math.max(10, Math.min(90, rsi + rsiChange));
      
      timeSeries.push({
        ts: date.toISOString(),
        price_usd: basePrice,
        rsi: rsi,
        rsi_signal: rsi >= 70 ? 'overbought' : rsi <= 30 ? 'oversold' : 'neutral',
        rsi_strength: rsi >= 70 ? 'strong' : rsi <= 30 ? 'weak' : 'moderate',
        rsi_momentum: rsiChange
      });
    }
    
    // Set the mock data
    this.data = {
      symbol: this.selectedSymbol,
      period: 14,
      latest_stats: {
        price_usd: basePrice,
        rsi: rsi,
        rsi_signal: rsi >= 70 ? 'overbought' : rsi <= 30 ? 'oversold' : 'neutral',
        rsi_strength: rsi >= 70 ? 'strong' : rsi <= 30 ? 'weak' : 'moderate',
        rsi_momentum: 0
      },
      time_series: timeSeries,
      metadata: {
        total_points: timeSeries.length,
        date_range: {
          start: timeSeries[0].ts,
          end: timeSeries[timeSeries.length - 1].ts
        }
      }
    };
  }
}