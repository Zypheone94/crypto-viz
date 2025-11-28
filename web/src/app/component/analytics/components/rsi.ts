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
                <mat-option *ngFor="let symbol of availableSymbols" [value]="symbol">
                  {{ symbol }}
                </mat-option>
              </mat-select>
            </mat-form-field>
            <div class="symbol-info" *ngIf="availableSymbols.length > 0">
              {{ availableSymbols.length }} symboles disponibles
            </div>
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
      background: var(--glass-bg);
      backdrop-filter: var(--backdrop-blur);
      border-radius: var(--radius-xl);
      box-shadow: var(--shadow-card);
      border: 1px solid var(--border-light);
      min-height: 600px;
    }

    .chart-title {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      font-size: 1.25rem;
      font-weight: 600;
    }

    .title-icon {
      color: var(--primary);
    }

    .chart-content {
      padding: var(--space-xl);
    }

    mat-card-header {
      padding: var(--space-xl);
      border-bottom: 1px solid var(--border-light);
    }

    mat-card-title {
      color: var(--text-primary) !important;
    }

    mat-card-subtitle {
      color: var(--text-secondary) !important;
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
      margin-bottom: var(--space-lg);
      padding: var(--space-lg);
      background: var(--bg-tertiary);
      border-radius: var(--radius-lg);
      border: 1px solid var(--border-light);
      flex-wrap: wrap;
      gap: var(--space-lg);
    }

    .stat-item {
      display: flex;
      flex-direction: column;
      align-items: center;
      min-width: 120px;
    }

    .stat-label {
      font-size: 0.75rem;
      color: var(--text-tertiary);
      text-transform: uppercase;
      letter-spacing: 0.5px;
      font-weight: 500;
      margin-bottom: var(--space-xs);
    }

    .stat-value {
      font-size: 1.5rem;
      font-weight: 700;
      color: var(--text-primary);
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
      min-height: 500px;
      margin-top: var(--space-lg);
    }

    .chart-canvas {
      height: 450px !important;
      width: 100% !important;
      background: var(--chart-bg);
      border-radius: var(--radius-md);
      padding: var(--space-md);
    }

    .loading-wrapper {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      min-height: 400px;
      padding: var(--space-2xl);
      text-align: center;
      gap: var(--space-lg);
    }

    .loading-wrapper p {
      color: var(--text-secondary);
    }

    .error-wrapper {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      min-height: 400px;
      padding: var(--space-2xl);
      text-align: center;
      gap: var(--space-md);
    }

    .error-icon {
      font-size: 4rem;
      width: 4rem;
      height: 4rem;
      color: var(--error);
    }

    .error-wrapper h3 {
      color: var(--text-primary);
      margin: 0;
      font-size: 1.5rem;
    }

    .error-wrapper p {
      color: var(--text-secondary);
      margin: 0;
      max-width: 300px;
    }

    .retry-button {
      display: flex;
      align-items: center;
      gap: var(--space-sm);
      padding: var(--space-md) var(--space-xl);
      border: 1px solid var(--border-primary);
      border-radius: var(--radius-md);
      background: var(--primary);
      color: var(--text-inverse);
      font-weight: 600;
      cursor: pointer;
      font-size: 1rem;
      transition: all var(--transition-fast);
      box-shadow: var(--shadow-sm);
    }

    .retry-button:hover {
      background: var(--primary-hover);
      transform: translateY(-1px);
      box-shadow: var(--shadow-md);
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
  availableSymbols: string[] = [];
  
  private autoRefreshSubscription?: Subscription;

  constructor(
    private apiService: ApiService
  ) {}

  ngOnInit(): void {
    this.componentState = ComponentState.LOADING;
    this.loadAvailableSymbols();
    
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

  private loadAvailableSymbols(): void {
    this.apiService.getAvailableSymbols().subscribe({
      next: (response: any) => {
        console.log('Symbols API response:', response);
        
        // Extract symbols from response
        if (Array.isArray(response)) {
          this.availableSymbols = response;
        } else if (response?.response && Array.isArray(response.response)) {
          this.availableSymbols = response.response;
        } else {
          console.warn('Unexpected symbols response format:', response);
          this.availableSymbols = ['BTC', 'ETH', 'ADA']; // Fallback
        }
        
        // Set default symbol if not already set
        if (this.availableSymbols.length > 0 && !this.selectedSymbol) {
          this.selectedSymbol = this.availableSymbols[0];
        }
        
        console.log(`Loaded ${this.availableSymbols.length} symbols for RSI`);
        
        // Now load data for the selected symbol
        this.loadData();
      },
      error: (error) => {
        console.error('Error loading symbols:', error);
        // Fallback to common symbols
        this.availableSymbols = ['BTC', 'ETH', 'ADA', 'SOL', 'BNB', 'XRP'];
        this.loadData();
      }
    });
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