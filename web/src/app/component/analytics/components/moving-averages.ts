import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { BaseChartDirective } from 'ng2-charts';
import { ChartConfiguration, ChartOptions } from 'chart.js';

import { ApiService } from '../../../services/api.service';
import { ComponentState } from '../../../shared/enums/component-state.enum';

interface MovingAverageData {
  symbol: string;
  bucket: string;
  window: number;
  types: string[];
  count: number;
  sma?: Array<{ t: string; value: number }>;
  wma?: Array<{ t: string; value: number }>;
  ema?: Array<{ t: string; value: number }>;
}

@Component({
  selector: 'app-moving-averages',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatProgressSpinnerModule,
    MatSelectModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    BaseChartDirective
  ],
  templateUrl: './moving-averages.html',
  styleUrls: ['./moving-averages.css']
})
export class MovingAveragesComponent implements OnInit {
  componentState = ComponentState;
  currentState: ComponentState = ComponentState.NOTREADY;
  errorMessage = '';

  // Form parameters
  symbol: string = 'BTC';
  fromDate: string = '';
  toDate: string = '';
  window: number = 7;
  maType: string = 'sma';
  bucket: string = 'day';

  maTypes = [
    { value: 'sma', label: 'SMA (Simple Moving Average)' },
    { value: 'wma', label: 'WMA (Weighted Moving Average)' },
    { value: 'ema', label: 'EMA (Exponential Moving Average)' },
    { value: 'all', label: 'Toutes les moyennes' }
  ];

  buckets = [
    { value: 'day', label: 'Jour' },
    { value: 'hour', label: 'Heure' }
  ];

  public lineChartData: ChartConfiguration<'line'>['data'] = {
    datasets: [],
  };

  public lineChartOptions: ChartOptions<'line'> = {
    responsive: true,
    scales: {
      x: {
        type: 'category',
        title: {
          display: true,
          text: 'Date',
        },
      },
      y: {
        title: {
          display: true,
          text: 'Prix / Moyenne',
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
      },
    },
  };

  constructor(private apiService: ApiService) {}

  ngOnInit(): void {
    // Set default dates (last 30 days)
    const today = new Date();
    const thirtyDaysAgo = new Date(today.getTime() - 30 * 24 * 60 * 60 * 1000);

    this.toDate = today.toISOString().split('T')[0];
    this.fromDate = thirtyDaysAgo.toISOString().split('T')[0];
  }

  fetchMovingAverages(): void {
    if (!this.fromDate || !this.toDate || !this.symbol) {
      this.errorMessage = 'Veuillez remplir tous les champs requis';
      this.currentState = ComponentState.ERROR;
      return;
    }

    this.currentState = ComponentState.LOADING;
    this.errorMessage = '';

    const params = {
      from: `${this.fromDate}T00:00:00Z`,
      to: `${this.toDate}T23:59:59Z`,
      window: this.window,
      ma_type: this.maType,
      bucket: this.bucket,
      symbol: this.symbol,
      limit: 10000
    };

    this.apiService.getMovingAverages(params).subscribe({
      next: (response: any) => {
        if (!response || !response.response) {
          this.currentState = ComponentState.EMPTY;
          return;
        }

        const data: MovingAverageData = response.response;
        this.updateChart(data);
        this.currentState = ComponentState.READY;
      },
      error: (err) => {
        console.error('Erreur API moving averages', err);
        this.currentState = ComponentState.ERROR;
        this.errorMessage = err?.error?.detail || 'Erreur lors de la récupération des moyennes mobiles';
      }
    });
  }

  private updateChart(data: MovingAverageData): void {
    const datasets: any[] = [];
    const colors = {
      sma: { border: 'rgba(75, 192, 192, 1)', background: 'rgba(75, 192, 192, 0.2)' },
      wma: { border: 'rgba(255, 159, 64, 1)', background: 'rgba(255, 159, 64, 0.2)' },
      ema: { border: 'rgba(153, 102, 255, 1)', background: 'rgba(153, 102, 255, 0.2)' }
    };

    // Extract labels from the first available dataset
    let labels: string[] = [];

    if (data.sma && data.sma.length > 0) {
      labels = data.sma.map(d => this.formatDate(d.t, data.bucket));
      datasets.push({
        data: data.sma.map(d => d.value),
        label: `SMA-${data.window}`,
        borderColor: colors.sma.border,
        backgroundColor: colors.sma.background,
        fill: false,
        tension: 0.3,
      });
    }

    if (data.wma && data.wma.length > 0) {
      if (labels.length === 0) {
        labels = data.wma.map(d => this.formatDate(d.t, data.bucket));
      }
      datasets.push({
        data: data.wma.map(d => d.value),
        label: `WMA-${data.window}`,
        borderColor: colors.wma.border,
        backgroundColor: colors.wma.background,
        fill: false,
        tension: 0.3,
      });
    }

    if (data.ema && data.ema.length > 0) {
      if (labels.length === 0) {
        labels = data.ema.map(d => this.formatDate(d.t, data.bucket));
      }
      datasets.push({
        data: data.ema.map(d => d.value),
        label: `EMA-${data.window}`,
        borderColor: colors.ema.border,
        backgroundColor: colors.ema.background,
        fill: false,
        tension: 0.3,
      });
    }

    this.lineChartData = {
      labels,
      datasets,
    };
  }

  private formatDate(dateStr: string, bucket: string): string {
    const d = new Date(dateStr);
    if (bucket === 'hour') {
      return d.toLocaleString('fr-FR', {
        day: '2-digit',
        month: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
      });
    } else {
      return d.toLocaleDateString('fr-FR', {
        day: '2-digit',
        month: '2-digit',
      });
    }
  }
}
