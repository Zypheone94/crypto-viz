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

Chart.register(...registerables);

interface RollingStdData {
  timestamp: string;
  value: number;
  label: string;
}

interface EcartTypeResponse {
  symbol: string;
  window_days: number;
  data: RollingStdData[];
  stats: {
    current: number;
    average: number;
    max: number;
    min: number;
  };
}

@Component({
  selector: 'app-ecart-type-glissant',
  standalone: true,
  imports: [CommonModule, MatCardModule, MatIconModule, MatProgressSpinnerModule, MatSelectModule, MatFormFieldModule, FormsModule],
  template: `
    <div class="ecart-type-container">
      <mat-card class="chart-card">
        <mat-card-header>
          <mat-card-title class="chart-title">
            <mat-icon class="title-icon">trending_down</mat-icon>
            Écart-type glissant (14 jours)
          </mat-card-title>
          <mat-card-subtitle>
            Mesure de la volatilité des prix sur une fenêtre glissante
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

          <div class="chart-wrapper" *ngIf="!isLoading">
            <canvas #chartCanvas class="chart-canvas"></canvas>
          </div>
          
          <div class="loading-container" *ngIf="isLoading">
            <mat-spinner diameter="50"></mat-spinner>
            <p>Chargement des données de volatilité...</p>
          </div>
        </mat-card-content>
      </mat-card>

      <div class="stats-grid">
        <mat-card class="stat-card">
          <mat-card-content>
            <div class="stat-content">
              <mat-icon class="stat-icon">timeline</mat-icon>
              <div class="stat-info">
                <h3>{{ currentStd | number:'1.2-2' }}%</h3>
                <p>Écart-type actuel</p>
              </div>
            </div>
          </mat-card-content>
        </mat-card>

        <mat-card class="stat-card">
          <mat-card-content>
            <div class="stat-content">
              <mat-icon class="stat-icon" [ngClass]="avgChangeClass">{{ avgChangeIcon }}</mat-icon>
              <div class="stat-info">
                <h3>{{ avgStd | number:'1.2-2' }}%</h3>
                <p>Moyenne 30j</p>
              </div>
            </div>
          </mat-card-content>
        </mat-card>

        <mat-card class="stat-card">
          <mat-card-content>
            <div class="stat-content">
              <mat-icon class="stat-icon danger">warning</mat-icon>
              <div class="stat-info">
                <h3>{{ maxStd | number:'1.2-2' }}%</h3>
                <p>Maximum 30j</p>
              </div>
            </div>
          </mat-card-content>
        </mat-card>

        <mat-card class="stat-card">
          <mat-card-content>
            <div class="stat-content">
              <mat-icon class="stat-icon success">check_circle</mat-icon>
              <div class="stat-info">
                <h3>{{ minStd | number:'1.2-2' }}%</h3>
                <p>Minimum 30j</p>
              </div>
            </div>
          </mat-card-content>
        </mat-card>
      </div>
    </div>
  `,
  styleUrls: ['./time-series.css'],
  styles: [`
    .ecart-type-container {
      display: flex;
      flex-direction: column;
      gap: 1.5rem;
      padding: 1rem;
    }

    .chart-card {
      background: #ffffff;
      color: #333;
      border-radius: 12px;
      box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
      border: 1px solid #e0e0e0;
    }

    .chart-title {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      color: #333;
      font-size: 1.25rem;
      font-weight: 600;
    }

    .title-icon {
      color: #ffd700;
    }

    .chart-content {
      padding: 1.5rem;
    }

    .controls-section {
      display: flex;
      gap: 1rem;
      margin-bottom: 1rem;
      flex-wrap: wrap;
      align-items: center;
    }

    .controls-section mat-form-field {
      min-width: 250px;
      flex: 1;
    }

    .symbol-info {
      color: #666;
      font-size: 0.875rem;
      padding: 0.5rem 1rem;
      background: #f0f7ff;
      border-radius: 4px;
      border-left: 3px solid #2196F3;
    }

    .chart-wrapper {
      position: relative;
      height: 400px;
      background: #f8f9fa;
      border-radius: 8px;
      padding: 1rem;
    }

    .chart-canvas {
      width: 100% !important;
      height: 100% !important;
    }

    .loading-container {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      height: 300px;
      gap: 1rem;
    }

    .stats-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 1rem;
    }

    .stat-card {
      border-radius: 8px;
      transition: transform 0.2s ease, box-shadow 0.2s ease;
    }

    .stat-card:hover {
      transform: translateY(-2px);
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
    }

    .stat-content {
      display: flex;
      align-items: center;
      gap: 1rem;
    }

    .stat-icon {
      font-size: 2rem;
      width: 2rem;
      height: 2rem;
      color: #2196F3;
    }

    .stat-icon.success {
      color: #4CAF50;
    }

    .stat-icon.danger {
      color: #FF5722;
    }

    .stat-icon.warning {
      color: #FF9800;
    }

    .stat-info h3 {
      margin: 0;
      font-size: 1.5rem;
      font-weight: 700;
      color: #333;
    }

    .stat-info p {
      margin: 0.25rem 0 0 0;
      color: #666;
      font-size: 0.875rem;
    }

    @media (max-width: 768px) {
      .ecart-type-container {
        padding: 0.5rem;
        gap: 1rem;
      }
      
      .stats-grid {
        grid-template-columns: 1fr;
      }
    }
  `]
})
export class EcartTypeGlissantComponent implements OnInit, OnDestroy, AfterViewInit {
  @ViewChild('chartCanvas', { static: false }) chartCanvas!: ElementRef<HTMLCanvasElement>;
  
  private chart: Chart | null = null;
  private subscription: Subscription = new Subscription();
  private dateRangeSubscription: Subscription = new Subscription();
  
  isLoading = true;
  currentStd = 0;
  avgStd = 0;
  maxStd = 0;
  minStd = 0;
  avgChangeIcon = 'trending_flat';
  avgChangeClass = '';
  
  private ecartTypeData: RollingStdData[] = [];
  selectedSymbol = 'BTC'; // Default symbol - public for template binding
  availableSymbols: string[] = []; // Dynamic symbol list

  constructor(
    private apiService: ApiService
  ) {}

  ngOnInit() {
    console.log('EcartTypeGlissantComponent initialized');
    console.log('API base URL:', this.apiService.baseUrl);
    
    // Load available symbols first
    this.loadAvailableSymbols();
    
    // Refresh data every 5 minutes
    this.subscription.add(
      interval(300000).subscribe(() => {
        this.loadData();
      })
    );
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
          this.availableSymbols = ['BTC', 'ETH', 'ADA', 'SOL']; // Fallback
        }
        
        // Set default symbol if not already set
        if (this.availableSymbols.length > 0 && !this.selectedSymbol) {
          this.selectedSymbol = this.availableSymbols[0];
        }
        
        console.log(`Loaded ${this.availableSymbols.length} symbols`);
        
        // Now load data for the selected symbol
        this.loadData();
      },
      error: (error) => {
        console.error('Error loading symbols:', error);
        // Fallback to common symbols
        this.availableSymbols = ['BTC', 'ETH', 'ADA', 'SOL', 'BNB', 'XRP', 'DOGE', 'DOT'];
        this.loadData();
      }
    });
  }

  ngAfterViewInit() {
    if (this.ecartTypeData.length > 0) {
      console.log('Initializing chart from ngAfterViewInit');
      this.scheduleChartRender();
    }
  }

  ngOnDestroy() {
    this.subscription.unsubscribe();
    this.dateRangeSubscription.unsubscribe();
    if (this.chart) {
      this.chart.destroy();
    }
  }

  onSymbolChange(): void {
    console.log('Symbol changed to:', this.selectedSymbol);
    this.loadData();
  }

  private loadData() {
    this.isLoading = true;
    
    // Call API with parameters - use selected symbol
    const symbol = this.selectedSymbol;
    const params = {
      period: 14,
      limit: 100  // Optimize for performance - reduced data points
    };
    
    console.log('🔄 Fetching écart-type data for symbol:', symbol, 'with params:', params);
    console.log('🌐 API base URL:', this.apiService['baseUrl']);
    
    // Use symbol-specific endpoint for better data structure
    this.apiService.getEcartType(symbol, params).subscribe({
      next: (response: any) => {
        console.log('Écart-type API response:', response);
        const payload = response || {};
        
        // Handle API response structure - check for time_series first (symbol-specific endpoint)
        if (payload.time_series && Array.isArray(payload.time_series)) {
          // Symbol-specific endpoint returns time_series data
          const timeSeries = payload.time_series;
          console.log('Processing time_series with', timeSeries.length, 'items');
          
          this.ecartTypeData = timeSeries
            .filter((item: any) => item.price_volatility_std != null && !isNaN(item.price_volatility_std))
            .map((item: any) => ({
              timestamp: item.ts,
              value: Number((item.price_volatility_std || 0).toFixed(3)),
              label: new Date(item.ts).toLocaleDateString('fr-FR', { month: 'short', day: 'numeric' })
            }))
            .sort((a: any, b: any) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());
            
          console.log('Processed écart-type data:', this.ecartTypeData.length, 'points');
          console.log('Sample data:', this.ecartTypeData.slice(0, 3));
            
          // Calculate stats from time series data
          const volatilityValues = this.ecartTypeData.map(item => item.value);
            
          if (volatilityValues.length > 0) {
            const stats = {
              current: volatilityValues[volatilityValues.length - 1] || 0,
              average: volatilityValues.reduce((sum: number, val: number) => sum + val, 0) / volatilityValues.length,
              max: Math.max(...volatilityValues),
              min: Math.min(...volatilityValues)
            };
            this.updateStats(stats);
            
            // Override with latest_stats if available
            if (payload.latest_stats && payload.latest_stats.price_volatility_std != null) {
              this.currentStd = Number(payload.latest_stats.price_volatility_std.toFixed(3));
            }
          }
        } else if (payload.detailed_results && Array.isArray(payload.detailed_results)) {
          // General endpoint returns detailed_results
          const detailedResults = payload.detailed_results;
          console.log('Processing detailed_results with', detailedResults.length, 'items');
          
          this.ecartTypeData = detailedResults
            .filter((item: any) => item.price_volatility_std != null && !isNaN(item.price_volatility_std))
            .map((item: any) => ({
              timestamp: item.ts,
              value: Number((item.price_volatility_std || 0).toFixed(3)),
              label: new Date(item.ts).toLocaleDateString('fr-FR', { month: 'short', day: 'numeric' })
            }))
            .sort((a: any, b: any) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());
            
          // Calculate stats from the detailed results
          const volatilityValues = this.ecartTypeData.map(item => item.value);
            
          if (volatilityValues.length > 0) {
            const stats = {
              current: volatilityValues[volatilityValues.length - 1] || 0,
              average: volatilityValues.reduce((sum: number, val: number) => sum + val, 0) / volatilityValues.length,
              max: Math.max(...volatilityValues),
              min: Math.min(...volatilityValues)
            };
            this.updateStats(stats);
          }
        } else if (payload.latest_data && Array.isArray(payload.latest_data)) {
          // If no detailed results, use latest_data and summary for basic stats
          const latestData = payload.latest_data;
          
          // Generate basic time series from available data
          this.ecartTypeData = latestData.map((item: any, index: number) => ({
            timestamp: item.latest_timestamp || new Date().toISOString(),
            value: item.current_volatility || 0,
            label: `${item.symbol || 'Data'} ${index + 1}`
          }));
          
          if (latestData.length > 0) {
            const volatilityValues = latestData.map((item: any) => item.current_volatility || 0);
            const stats = {
              current: volatilityValues[0] || 0,
              average: volatilityValues.reduce((sum: number, val: number) => sum + val, 0) / volatilityValues.length,
              max: Math.max(...volatilityValues),
              min: Math.min(...volatilityValues)
            };
            this.updateStats(stats);
          }
        } else if (payload.data) {
          // Mock data structure fallback
          this.ecartTypeData = payload.data || [];
          this.updateStats(payload.stats || {});
        } else {
          console.warn('No valid data structure in API response:', response);
          this.ecartTypeData = [];
          this.updateStats({ current: 0, average: 0, max: 0, min: 0 });
        }
        
        this.isLoading = false;
        this.scheduleChartRender();
      },
      error: (error) => {
        console.error('Error loading écart-type data:', error);
        this.ecartTypeData = [];
        this.updateStats({ current: 0, average: 0, max: 0, min: 0 });
        this.isLoading = false;
      }
    });
  }

  private loadDataForDateRange(startDate: Date, endDate: Date): void {
    // For now, we'll load all data and filter client-side
    // In a real implementation, you might want to pass date range to API
    this.loadData();
  }

  private updateStats(stats: any): void {
    this.currentStd = stats.current || 0;
    this.avgStd = stats.average || 0;
    this.maxStd = stats.max || 0;
    this.minStd = stats.min || 0;
    
    // Update trend indicators
    if (this.currentStd > this.avgStd * 1.1) {
      this.avgChangeIcon = 'trending_up';
      this.avgChangeClass = 'warning';
    } else if (this.currentStd < this.avgStd * 0.9) {
      this.avgChangeIcon = 'trending_down';
      this.avgChangeClass = 'success';
    } else {
      this.avgChangeIcon = 'trending_flat';
      this.avgChangeClass = '';
    }
  }



  private scheduleChartRender(): void {
    if (!this.ecartTypeData.length) {
      return;
    }

    // Let Angular render the canvas before trying to access it
    setTimeout(() => {
      if (!this.chartCanvas?.nativeElement) {
        console.warn('Chart canvas still unavailable after scheduling render');
        return;
      }

      if (!this.chart) {
        this.initChart();
      } else {
        this.updateChart();
      }
    });
  }

  private initChart() {
    console.log('📊 Initializing chart...');
    if (!this.chartCanvas?.nativeElement) {
      console.warn('❌ Chart canvas not available');
      return;
    }
    
    const ctx = this.chartCanvas.nativeElement.getContext('2d');
    if (!ctx) {
      console.error('❌ Cannot get 2D context from canvas');
      return;
    }

    // Destroy existing chart if any
    if (this.chart) {
      this.chart.destroy();
      this.chart = null;
    }

    // Ensure we have data to display
    if (!this.ecartTypeData || this.ecartTypeData.length === 0) {
      console.warn('No data available for chart. Data array:', this.ecartTypeData);
      console.warn('Selected symbol:', this.selectedSymbol);
      return;
    }
    
    console.log('Chart data available:', this.ecartTypeData.length, 'points for symbol:', this.selectedSymbol);

    const labels = this.ecartTypeData.map(d => d.label);
    const dataValues = this.ecartTypeData.map(d => d.value);

    console.log('Creating area chart with', dataValues.length, 'data points');

    const config: ChartConfiguration = {
      type: 'line' as ChartType,
      data: {
        labels: labels,
        datasets: [{
          label: 'Volatilité (%)',
          data: dataValues,
          borderColor: '#ffd700',
          backgroundColor: 'rgba(255, 215, 0, 0.2)',
          borderWidth: 3,
          fill: true, // This creates the area chart effect
          tension: 0.4,
          pointBackgroundColor: '#ffd700',
          pointBorderColor: '#ffffff',
          pointBorderWidth: 2,
          pointRadius: 5,
          pointHoverRadius: 8,
          pointHoverBackgroundColor: '#ffed4e',
          pointHoverBorderColor: '#ffffff',
          pointHoverBorderWidth: 3
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          intersect: false,
          mode: 'index'
        },
        plugins: {
          legend: {
            display: true,
            position: 'top',
            labels: {
              color: '#333',
              font: {
                size: 14,
                weight: 'bold'
              },
              usePointStyle: true,
              pointStyle: 'circle'
            }
          },
          tooltip: {
            backgroundColor: 'rgba(0, 0, 0, 0.8)',
            titleColor: '#fff',
            bodyColor: '#fff',
            borderColor: '#ffd700',
            borderWidth: 2,
            cornerRadius: 8,
            displayColors: true,
            callbacks: {
              title: (context) => {
                return `Date: ${context[0].label}`;
              },
              label: (context) => {
                const value = context.parsed?.y ?? 0;
                return `Volatilité: ${value.toFixed(3)}%`;
              }
            }
          }
        },
        scales: {
          x: {
            display: true,
            title: {
              display: true,
              text: 'Période',
              color: '#333',
              font: {
                size: 14,
                weight: 'bold'
              }
            },
            grid: {
              display: true,
              color: 'rgba(0, 0, 0, 0.1)',
              lineWidth: 1
            },
            ticks: {
              color: '#666',
              font: {
                size: 12
              },
              maxTicksLimit: 10
            }
          },
          y: {
            display: true,
            title: {
              display: true,
              text: 'Écart-type (%)',
              color: '#333',
              font: {
                size: 14,
                weight: 'bold'
              }
            },
            grid: {
              display: true,
              color: 'rgba(0, 0, 0, 0.1)',
              lineWidth: 1
            },
            ticks: {
              color: '#666',
              font: {
                size: 12
              },
              callback: (value) => `${Number(value).toFixed(1)}%`
            },
            beginAtZero: true
          }
        },
        elements: {
          line: {
            tension: 0.4
          },
          point: {
            hoverRadius: 8
          }
        },
        animation: {
          duration: 1000,
          easing: 'easeInOutQuart'
        }
      }
    };

    try {
      this.chart = new Chart(ctx, config);
      console.log('Area chart created successfully');
    } catch (error) {
      console.error('Error creating chart:', error);
    }
  }

  private updateChart() {
    if (!this.chart || !this.ecartTypeData || this.ecartTypeData.length === 0) {
      console.warn('Chart or data not available for update');
      return;
    }
    
    const labels = this.ecartTypeData.map(d => d.label);
    const dataValues = this.ecartTypeData.map(d => d.value);
    
    console.log('Updating area chart with', dataValues.length, 'data points');
    
    this.chart.data.labels = labels;
    this.chart.data.datasets[0].data = dataValues;
    
    // Update chart with animation
    this.chart.update('active');
  }
}