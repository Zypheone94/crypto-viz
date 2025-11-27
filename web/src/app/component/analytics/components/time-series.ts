import { Component, OnInit, OnDestroy } from '@angular/core';
import { ApiService } from '../../../services/api.service';
import { ComponentState } from '../../../shared/enums/component-state.enum';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { CommonModule } from '@angular/common';

import { StoreService } from '../../../services/store.service';
import { Subscription } from 'rxjs';
import { TimeSeriesParams } from '../../../shared/interface/timeSeries-interface';

import { BaseChartDirective } from 'ng2-charts';
import { ChartConfiguration, ChartOptions, ChartType } from 'chart.js';
// import 'chartjs-adapter-date-fns'; // Temporarily commented out - will be needed for time-series charts

@Component({
  selector: 'app-time-series',
  standalone: true,
  imports: [MatProgressSpinnerModule, CommonModule, BaseChartDirective],
  templateUrl: 'time-series.html',
})
export class TimeSeries implements OnInit, OnDestroy {
  componentState = ComponentState;
  currentState: ComponentState = ComponentState.LOADING;
  errorMessage = '';

  // Subscription to new dates from the store
  private dataASubscription: Subscription = new Subscription();
  private dataBSubscription: Subscription = new Subscription();
  private dateRangeSubscription: Subscription = new Subscription();
  // Data received from the store
  timeSeriesParamsA: TimeSeriesParams | null = null;
  timeSeriesParamsB: TimeSeriesParams | null = null;
  // Data received from the API
  dataA: any[] = [];
  dataB: any[] = [];

  public areaChartData: ChartConfiguration<'line'>['data'] = {
    datasets: [],
  };

  public areaChartOptions: ChartOptions<'line'> = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: {
      intersect: false,
      mode: 'index',
    },
    scales: {
      x: {
        type: 'time',
        time: {
          displayFormats: {
            hour: 'MMM dd, HH:mm',
            day: 'MMM dd',
            week: 'MMM dd',
            month: 'MMM yyyy'
          },
          tooltipFormat: 'PPpp'
        },
        title: {
          display: true,
          text: 'Date/Heure',
        },
        grid: {
          display: true,
          color: 'rgba(0, 0, 0, 0.1)',
        },
      },
      y: {
        title: {
          display: true,
          text: 'Volume',
        },
        beginAtZero: true,
        grid: {
          display: true,
          color: 'rgba(0, 0, 0, 0.1)',
        },
      },
    },
    plugins: {
      legend: {
        display: true,
        position: 'top',
      },
      tooltip: {
        mode: 'index',
        intersect: false,
        callbacks: {
          title: function(tooltipItems) {
            if (tooltipItems.length > 0 && tooltipItems[0].parsed.x !== null) {
              const date = new Date(tooltipItems[0].parsed.x);
              return date.toLocaleString();
            }
            return '';
          },
          label: function(context) {
            let label = context.dataset.label || '';
            if (label) {
              label += ': ';
            }
            if (context.parsed.y !== null) {
              label += context.parsed.y.toLocaleString();
            }
            return label;
          }
        }
      },
    },
    elements: {
      point: {
        radius: 2,
        hoverRadius: 6,
      },
      line: {
        tension: 0.2,
        borderWidth: 2,
      },
    },
  };
  public areaChartLegend = true;

  constructor(
    private api: ApiService,
    private storeService: StoreService,
  ) {}

  ngOnInit() {
    // Subscribe to date range changes from the store
    this.dateRangeSubscription = this.storeService.dateRange$.subscribe((dateRange) => {
      if (dateRange.startDate && dateRange.endDate) {
        this.timeSeriesParamsA = {
          from: dateRange.startDate.toISOString(),
          to: dateRange.endDate.toISOString(),
          bucket: this.determineBucket(dateRange.startDate, dateRange.endDate)
        };
        this.callTimeSeriesApi('A');
      }
    });

    // Subscribe to the legacy data updates from sidebar (fallback)
    this.dataASubscription = this.storeService.getDataA().subscribe((res) => {
      if (res && res.startDate && res.endDate) {
        // Convert the new date range format to the expected TimeSeriesParams format
        this.timeSeriesParamsA = {
          from: res.startDate.toISOString(),
          to: res.endDate.toISOString(),
          bucket: this.determineBucket(res.startDate, res.endDate)
        };
        this.callTimeSeriesApi('A');
      }
    });

    // Initialize with default data for period A
    const defaultEndDate = new Date();
    const defaultStartDate = new Date(defaultEndDate.getTime() - 7 * 24 * 60 * 60 * 1000);
    this.timeSeriesParamsA = {
      from: defaultStartDate.toISOString(),
      to: defaultEndDate.toISOString(),
      bucket: this.determineBucket(defaultStartDate, defaultEndDate)
    };
    
    // Set initial date range in store
    this.storeService.setDateRange(defaultStartDate, defaultEndDate);
    this.callTimeSeriesApi('A');
  }

  ngOnDestroy() {
    this.dataASubscription.unsubscribe();
    this.dataBSubscription.unsubscribe();
    this.dateRangeSubscription.unsubscribe();
  }

  private determineBucket(startDate: Date, endDate: Date): 'hour' | 'day' {
    const diffMs = endDate.getTime() - startDate.getTime();
    const diffDays = diffMs / (1000 * 60 * 60 * 24);
    
    // If the range is less than 3 days, use hourly buckets
    // Otherwise use daily buckets
    return diffDays <= 3 ? 'hour' : 'day';
  }

  callTimeSeriesApi(periode: 'A' | 'B') {
    const params = periode === 'A' ? this.timeSeriesParamsA : this.timeSeriesParamsB;
    if (!params) return;

    // On garde les vraies dates mais on mock les valeurs
    const from = new Date(params.from);
    const to = new Date(params.to);
    const stepMs = params.bucket === 'hour' ? 60 * 60 * 1000 : 24 * 60 * 60 * 1000;
    const mockedData: any = [];
    for (let time = from.getTime(); time <= to.getTime(); time += stepMs) {
      mockedData.push({
        date: new Date(time).toISOString(),
        value: Math.round(Math.random() * 100),
      });
    }

    this.api.getTimeseries(params).subscribe({
      next: (data) => {
        if (!data || data.length === 0) {
          if (periode === 'A') {
            this.dataA = [];
          } else {
            this.dataB = [];
          }
          this.updateChart();
          return;
        }

        if (periode === 'A') {
          this.dataA = mockedData;
        } else {
          this.dataB = mockedData;
        }
        this.currentState = ComponentState.READY;
        this.updateChart();
        console.log('Données API', data);
      },
      error: (err) => {
        console.error('Erreur API', err);
        this.currentState = ComponentState.ERROR;
        this.errorMessage = `Erreur lors de la récupération des données : ${err.error.detail}`;
      },
    });
  }

  private updateChart() {
    const hasA = this.dataA && this.dataA.length > 0;
    const hasB = this.dataB && this.dataB.length > 0;

    if (!hasA && !hasB) {
      this.currentState = ComponentState.EMPTY;
      return;
    }

    // Déterminer le niveau de granularité à afficher
    const bucketA = this.timeSeriesParamsA?.bucket;
    const bucketB = this.timeSeriesParamsB?.bucket;

    // Si au moins une période utilise 'hour', on affiche les heures
    const displayGranularity = bucketA === 'hour' || bucketB === 'hour' ? 'hour' : 'day';

    // Normaliser les dates selon la granularité d'affichage
    const normalizeDate = (dateStr: string, granularity: string): string => {
      const d = new Date(dateStr);
      if (granularity === 'hour') {
        // Arrondir à l'heure
        d.setMinutes(0, 0, 0);
      } else {
        // Arrondir au jour
        d.setHours(0, 0, 0, 0);
      }
      return d.toISOString();
    };

    // Créer des maps normalisées pour chaque période
    const dataAMap = new Map<string, number>();
    const dataBMap = new Map<string, number>();

    if (hasA) {
      this.dataA.forEach((d) => {
        const normalizedDate = normalizeDate(d.date, displayGranularity);
        dataAMap.set(normalizedDate, d.value);
      });
    }

    if (hasB) {
      this.dataB.forEach((d) => {
        const normalizedDate = normalizeDate(d.date, displayGranularity);
        dataBMap.set(normalizedDate, d.value);
      });
    }

    // Créer une timeline unifiée avec toutes les dates uniques
    const allDates = new Set<string>([...dataAMap.keys(), ...dataBMap.keys()]);

    // Trier les dates chronologiquement
    const sortedDates = Array.from(allDates).sort(
      (a, b) => new Date(a).getTime() - new Date(b).getTime(),
    );

    const datasets: any[] = [];

    if (hasA && dataAMap.size > 0) {
      // Create data points with x,y coordinates for datetime axis
      const dataAPoints = sortedDates.map((date) => ({
        x: new Date(date).getTime(),
        y: dataAMap.get(date) || null,
      })).filter(point => point.y !== null);

      datasets.push({
        data: dataAPoints,
        label: 'Analyse Crypto (Période A)',
        borderColor: 'rgba(59, 130, 246, 1)',
        backgroundColor: 'rgba(59, 130, 246, 0.1)',
        fill: true,
        tension: 0.2,
        pointRadius: 3,
        pointHoverRadius: 6,
        borderWidth: 2,
      });
    }

    if (hasB && dataBMap.size > 0) {
      // Create data points with x,y coordinates for datetime axis
      const dataBPoints = sortedDates.map((date) => ({
        x: new Date(date).getTime(),
        y: dataBMap.get(date) || null,
      })).filter(point => point.y !== null);

      datasets.push({
        data: dataBPoints,
        label: 'Analyse Crypto (Période B)',
        borderColor: 'rgba(239, 68, 68, 1)',
        backgroundColor: 'rgba(239, 68, 68, 0.1)',
        fill: true,
        tension: 0.2,
        pointRadius: 3,
        pointHoverRadius: 6,
        borderWidth: 2,
      });
    }

    // For time-based charts, we don't need labels array
    this.areaChartData = {
      datasets,
    };
  }
}