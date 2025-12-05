import { Component, OnInit, ViewChild, ElementRef, AfterViewInit } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import {
  Chart,
  ChartConfiguration,
  registerables,
  LineElement,
  PointElement,
  LinearScale,
  CategoryScale,
  Title,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js';

// Register Chart.js components
Chart.register(...registerables);
Chart.register(
  LineElement,
  PointElement,
  LinearScale,
  CategoryScale,
  Title,
  Tooltip,
  Legend,
  Filler,
);

interface CorrelationResponse {
  symbol1: string;
  symbol2: string;
  timespan: string;
  usable_points: number;
  correlation_pearson: number;
  plot_data: {
    timestamps: string[];
    display_timestamps?: string[];
    series: Array<{
      name: string;
      data: number[];
      color: string;
    }>;
  };
  statistics: {
    [key: string]: number;
  };
  message: string;
}

interface SymbolsResponse {
  response: string[];
}

@Component({
  selector: 'app-correlation',
  standalone: true,
  templateUrl: './correlation.html',
  styleUrls: ['./correlation.css'],
  imports: [FormsModule, CommonModule],
})
export class Correlation implements OnInit, AfterViewInit {
  @ViewChild('chartCanvas') chartCanvas!: ElementRef<HTMLCanvasElement>;

  symbols: string[] = [];
  symbol1: string | null = null;
  symbol2: string | null = null;
  timespan: 'hour' | 'day' = 'hour';

  correlation: CorrelationResponse | null = null;
  loading = false;
  loadingSymbols = false;
  errorMsg = '';

  private chart: Chart | null = null;

  constructor(private http: HttpClient) {
    console.log('🔧 Correlation component constructor called');
    console.log('🔧 HttpClient injected:', !!this.http);
  }

  ngOnInit() {
    console.log('🚀 Correlation ngOnInit called');
    this.loadSymbols();
  }

  loadSymbols() {
    console.log('📡 loadSymbols called, about to make HTTP request to /api/symbols');
    this.loadingSymbols = true;
    this.http.get<SymbolsResponse>('http://localhost:8080/api/symbols').subscribe({
      next: (res) => {
        this.symbols = res.response || [];
        this.loadingSymbols = false;

        // Auto-select BTC and ETH as default if available
        if (this.symbols.includes('BTC') && this.symbols.includes('ETH')) {
          this.symbol1 = 'BTC';
          this.symbol2 = 'ETH';
          this.tryLoadCorrelation();
        } else if (this.symbols.length >= 2) {
          // Fallback to first two symbols if BTC/ETH not available
          this.symbol1 = this.symbols[0];
          this.symbol2 = this.symbols[1];
          this.tryLoadCorrelation();
        }
      },
      error: (err) => {
        console.error('Error loading symbols:', err);
        this.symbols = ['2Z', 'ETH', 'BTC']; // Fallback
        this.loadingSymbols = false;
      },
    });
  }

  ngAfterViewInit() {
    console.log('🎯 ngAfterViewInit called', {
      hasCorrelation: !!this.correlation,
      hasCanvas: !!this.chartCanvas,
      canvasElement: this.chartCanvas?.nativeElement,
      canvasInDOM: this.chartCanvas?.nativeElement?.isConnected,
    });

    // Test direct d'accès au canvas
    const canvas = document.querySelector('canvas');
    console.log('🎯 Canvas found in DOM:', !!canvas, canvas);

    // Test the canvas first
    setTimeout(() => {
      this.testCanvas();
    }, 200);

    // Retry rendering chart if correlation data was loaded before view init
    if (this.correlation && this.chartCanvas) {
      setTimeout(() => this.renderChart(), 100);
    }
  }

  onSelectionChange() {
    this.tryLoadCorrelation();
  }

  tryLoadCorrelation() {
    if (!this.symbol1 || !this.symbol2) {
      console.log('❌ Symbol1 or Symbol2 not selected', {
        symbol1: this.symbol1,
        symbol2: this.symbol2,
      });
      return;
    }

    console.log('🚀 Starting correlation request', {
      symbol1: this.symbol1,
      symbol2: this.symbol2,
      timespan: this.timespan,
    });

    this.loading = true;
    this.errorMsg = '';
    this.correlation = null;

    const params = new HttpParams()
      .set('symbol1', this.symbol1)
      .set('symbol2', this.symbol2)
      .set('timespan', this.timespan);

    console.log('📡 HTTP GET /correlation with params:', params.toString());

    this.http.get<CorrelationResponse>('http://localhost:8080/correlation', { params }).subscribe({
      next: (res) => {
        console.log('✅ Correlation response received:', res);
        console.log('📊 Plot data details:', {
          timestamps: res.plot_data?.timestamps?.length || 0,
          series: res.plot_data?.series?.length || 0,
          firstTimestamp: res.plot_data?.timestamps?.[0],
          lastTimestamp: res.plot_data?.timestamps?.[res.plot_data.timestamps.length - 1],
        });
        this.correlation = res;
        this.loading = false;

        // Attendre que Angular mette à jour le DOM
        setTimeout(() => this.renderChart(), 100);
      },
      error: (err) => {
        console.error('❌ Correlation error:', err);
        this.errorMsg = err.error?.detail || 'Erreur lors de la récupération des données';
        this.loading = false;
      },
    });
  }

  renderChart() {
    console.log('🎯 renderChart called');

    if (!this.correlation || !this.chartCanvas) {
      console.log('❌ Cannot render chart:', {
        hasCorrelation: !!this.correlation,
        hasCanvas: !!this.chartCanvas,
        canvasElement: this.chartCanvas?.nativeElement,
        canvasSize: this.chartCanvas?.nativeElement
          ? {
              width: this.chartCanvas.nativeElement.clientWidth,
              height: this.chartCanvas.nativeElement.clientHeight,
            }
          : null,
      });
      return;
    }

    console.log('📊 Rendering chart with data:', {
      timestamps: this.correlation.plot_data.timestamps.length,
      series: this.correlation.plot_data.series.length,
    });

    // Destroy previous chart if exists
    if (this.chart) {
      this.chart.destroy();
    }

    const canvasEl = this.chartCanvas.nativeElement;
    console.log('🎯 Canvas element details:', {
      width: canvasEl.clientWidth,
      height: canvasEl.clientHeight,
      offsetWidth: canvasEl.offsetWidth,
      offsetHeight: canvasEl.offsetHeight,
      style: canvasEl.style.cssText,
      isVisible: canvasEl.offsetParent !== null,
    });

    // Force canvas size if needed
    if (canvasEl.clientHeight === 0) {
      console.log('⚠️ Canvas has no height, setting explicit size');
      canvasEl.style.width = '100%';
      canvasEl.style.height = '400px';
    }

    const ctx = canvasEl.getContext('2d');
    if (!ctx) {
      console.log('❌ Cannot get canvas context');
      return;
    }

    const plotData = this.correlation.plot_data;

    // Vérifier que nous avons des données
    if (!plotData.timestamps.length || !plotData.series.length) {
      console.log('❌ No data to plot', {
        timestamps: plotData.timestamps,
        series: plotData.series,
      });
      return;
    }

    // Vérifier que les séries ont des données
    const validSeries = plotData.series.filter((s) => s.data && s.data.length > 0);
    if (validSeries.length === 0) {
      console.log('❌ No valid series data');
      return;
    }

    const config: ChartConfiguration = {
      type: 'line',
      data: {
        labels: plotData.display_timestamps || plotData.timestamps.map((ts) => {
          // Formatage des labels pour une meilleure lisibilité
          const date = new Date(ts);
          if (this.timespan === 'day') {
            return date.toLocaleDateString('fr-FR') + ' ' + 
                   date.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
          } else {
            return (
              date.toLocaleDateString('fr-FR') +
              ' ' +
              date.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })
            );
          }
        }),
        datasets: plotData.series.map((s, index) => ({
          label: s.name,
          data: s.data,
          borderColor: s.color,
          backgroundColor: s.color + '20', // Add transparency
          borderWidth: 2,
          tension: 0.4,
          pointRadius: plotData.timestamps.length > 100 ? 0 : 2, // Pas de points si trop de données
          pointHoverRadius: 5,
          fill: false,
          yAxisID: index === 0 ? 'y' : 'y1', // Échelles séparées pour chaque série
        })),
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          mode: 'index',
          intersect: false,
        },
        plugins: {
          title: {
            display: true,
            text: `${this.correlation.symbol1} vs ${this.correlation.symbol2} - Corrélation: ${this.correlation.correlation_pearson.toFixed(4)}`,
            font: {
              size: 16,
              weight: 'bold',
            },
          },
          legend: {
            display: true,
            position: 'top',
          },
          tooltip: {
            mode: 'index',
            intersect: false,
            callbacks: {
              label: (context) => {
                const value = context.parsed?.y;
                return `${context.dataset.label}: ${value != null ? value.toFixed(4) : 'N/A'}`;
              },
              title: (tooltipItems) => {
                if (tooltipItems.length > 0) {
                  const timestamp = plotData.timestamps[tooltipItems[0].dataIndex];
                  const date = new Date(timestamp);
                  return date.toLocaleDateString('fr-FR') + ' ' + date.toLocaleTimeString('fr-FR');
                }
                return '';
              },
            },
          },
        },
        scales: {
          x: {
            display: true,
            title: {
              display: true,
              text: this.timespan === 'day' ? 'Jours' : 'Temps',
            },
            ticks: {
              maxRotation: 45,
              minRotation: 0,
              maxTicksLimit: 15,
            },
          },
          y: {
            type: 'linear',
            display: true,
            position: 'left',
            title: {
              display: true,
              text: `Prix ${plotData.series[0]?.name || ''}`,
            },
            grid: {
              color: 'rgba(0,0,0,0.1)',
            },
          },
          y1: {
            type: 'linear',
            display: true,
            position: 'right',
            title: {
              display: true,
              text: `Prix ${plotData.series[1]?.name || ''}`,
            },
            grid: {
              drawOnChartArea: false,
            },
            ticks: {
              callback: function (value: any) {
                return typeof value === 'number' ? value.toFixed(4) : value;
              },
            },
          },
        },
      },
    };

    console.log('📊 Creating Chart.js instance with config:', {
      type: config.type,
      labelsCount: config.data.labels?.length,
      datasetsCount: config.data.datasets?.length,
      datasets: config.data.datasets?.map((d) => ({
        label: d.label,
        dataLength: d.data?.length,
      })),
    });

    try {
      this.chart = new Chart(ctx, config);
      console.log('✅ Chart created successfully', this.chart);
    } catch (error) {
      console.error('❌ Error creating chart:', error);
    }
  }

  testCanvas() {
    console.log('🧪 Testing canvas directly');

    if (!this.chartCanvas) {
      console.log('❌ No canvas reference');
      return;
    }

    const canvas = this.chartCanvas.nativeElement;
    const ctx = canvas.getContext('2d');

    if (!ctx) {
      console.log('❌ No canvas context');
      return;
    }

    // Test simple drawing
    ctx.fillStyle = 'red';
    ctx.fillRect(10, 10, 100, 100);
    console.log('✅ Drew red rectangle for testing');

    // Create simple test chart
    try {
      const testChart = new Chart(ctx, {
        type: 'line',
        data: {
          labels: ['Jan', 'Feb', 'Mar'],
          datasets: [
            {
              label: 'Test',
              data: [1, 2, 3],
              borderColor: 'blue',
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
        },
      });
      console.log('✅ Test chart created successfully', testChart);
    } catch (error) {
      console.error('❌ Test chart failed:', error);
    }
  }

  getCorrelationStrength(): string {
    if (!this.correlation) return '';

    const r = Math.abs(this.correlation.correlation_pearson);

    if (r >= 0.9) return 'Très forte';
    if (r >= 0.7) return 'Forte';
    if (r >= 0.5) return 'Modérée';
    if (r >= 0.3) return 'Faible';
    return 'Très faible';
  }

  getCorrelationColor(): string {
    if (!this.correlation) return '';

    const r = this.correlation.correlation_pearson;

    if (r > 0.7) return 'text-green-600';
    if (r > 0.3) return 'text-blue-600';
    if (r > -0.3) return 'text-gray-600';
    if (r > -0.7) return 'text-orange-600';
    return 'text-red-600';
  }
}
