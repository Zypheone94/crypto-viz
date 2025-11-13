import { Component, OnInit, OnDestroy, ViewChild, ElementRef, AfterViewInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { Chart, ChartConfiguration, ChartType, registerables } from 'chart.js';
import { Subscription, interval } from 'rxjs';

Chart.register(...registerables);

interface RollingStdData {
  timestamp: string;
  value: number;
  label: string;
}

@Component({
  selector: 'app-ecart-type-glissant',
  standalone: true,
  imports: [CommonModule, MatCardModule, MatIconModule, MatProgressSpinnerModule],
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
  
  isLoading = true;
  currentStd = 0;
  avgStd = 0;
  maxStd = 0;
  minStd = 0;
  avgChangeIcon = 'trending_flat';
  avgChangeClass = '';

  ngOnInit() {
    this.loadData();
    
    // Refresh data every 30 seconds
    this.subscription.add(
      interval(30000).subscribe(() => {
        this.loadData();
      })
    );
  }

  ngAfterViewInit() {
    if (this.chartCanvas) {
      this.initChart();
    }
  }

  ngOnDestroy() {
    this.subscription.unsubscribe();
    if (this.chart) {
      this.chart.destroy();
    }
  }

  private loadData() {
    // Simulate loading time
    setTimeout(() => {
      this.generateMockData();
      this.updateChart();
      this.isLoading = false;
    }, 1000);
  }

  private generateMockData(): RollingStdData[] {
    const data: RollingStdData[] = [];
    const now = new Date();
    const baseStd = 2.5; // Base standard deviation percentage
    
    // Generate 30 days of data
    for (let i = 29; i >= 0; i--) {
      const date = new Date(now);
      date.setDate(date.getDate() - i);
      
      // Simulate realistic volatility patterns
      const randomFactor = 0.5 + Math.random() * 1.5; // 0.5 to 2.0 multiplier
      const trendFactor = Math.sin((i / 30) * Math.PI * 2) * 0.3 + 1; // Cyclical trend
      const value = baseStd * randomFactor * trendFactor;
      
      data.push({
        timestamp: date.toISOString(),
        value: Math.max(0.1, value), // Minimum 0.1% volatility
        label: date.toLocaleDateString('fr-FR', { month: 'short', day: 'numeric' })
      });
    }
    
    // Calculate statistics
    const values = data.map(d => d.value);
    this.currentStd = values[values.length - 1];
    this.avgStd = values.reduce((a, b) => a + b, 0) / values.length;
    this.maxStd = Math.max(...values);
    this.minStd = Math.min(...values);
    
    // Determine trend
    const recent = values.slice(-7).reduce((a, b) => a + b, 0) / 7;
    const previous = values.slice(-14, -7).reduce((a, b) => a + b, 0) / 7;
    
    if (recent > previous * 1.05) {
      this.avgChangeIcon = 'trending_up';
      this.avgChangeClass = 'danger';
    } else if (recent < previous * 0.95) {
      this.avgChangeIcon = 'trending_down';
      this.avgChangeClass = 'success';
    } else {
      this.avgChangeIcon = 'trending_flat';
      this.avgChangeClass = '';
    }
    
    return data;
  }

  private initChart() {
    if (!this.chartCanvas) return;
    
    const ctx = this.chartCanvas.nativeElement.getContext('2d');
    if (!ctx) return;

    const data = this.generateMockData();

    const config: ChartConfiguration = {
      type: 'line' as ChartType,
      data: {
        labels: data.map(d => d.label),
        datasets: [{
          label: 'Écart-type (%)',
          data: data.map(d => d.value),
          borderColor: '#ffd700',
          backgroundColor: 'rgba(255, 215, 0, 0.1)',
          borderWidth: 3,
          fill: true,
          tension: 0.4,
          pointBackgroundColor: '#ffd700',
          pointBorderColor: '#fff',
          pointBorderWidth: 2,
          pointRadius: 4,
          pointHoverRadius: 6
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
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
            callbacks: {
              label: (context) => {
                const value = context.parsed?.y ?? 0;
                return `Volatilité: ${value.toFixed(2)}%`;
              }
            }
          }
        },
        scales: {
          x: {
            grid: {
              color: 'rgba(0, 0, 0, 0.1)',
            },
            ticks: {
              color: '#666',
            }
          },
          y: {
            grid: {
              color: 'rgba(0, 0, 0, 0.1)',
            },
            ticks: {
              color: '#666',
              callback: (value) => `${value}%`
            },
            beginAtZero: true
          }
        },
        elements: {
          line: {
            tension: 0.4
          }
        }
      }
    };

    this.chart = new Chart(ctx, config);
  }

  private updateChart() {
    if (!this.chart) return;
    
    const data = this.generateMockData();
    this.chart.data.labels = data.map(d => d.label);
    this.chart.data.datasets[0].data = data.map(d => d.value);
    this.chart.update();
  }
}