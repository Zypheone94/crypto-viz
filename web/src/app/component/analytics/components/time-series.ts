import { Component, OnInit } from '@angular/core';
import { ApiService } from '../../../services/api.service';
import { ComponentState } from '../../../shared/enums/component-state.enum';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { CommonModule } from '@angular/common';

import { StoreService } from '../../../services/store.service';
import { Subscription } from 'rxjs';
import { TimeSeriesParams } from '../../../shared/interface/timeSeries-interface';

import { BaseChartDirective } from 'ng2-charts';
import { ChartConfiguration, ChartOptions, ChartType } from 'chart.js';

@Component({
  selector: 'app-time-series',
  standalone: true,
  imports: [MatProgressSpinnerModule, CommonModule, BaseChartDirective],
  templateUrl: 'time-series.html',
})
export class TimeSeries implements OnInit {
  componentState = ComponentState;
  currentState: ComponentState = ComponentState.LOADING;
  errorMessage = '';

  // Subscription to new dates from the store
  private dataSubscription: Subscription = new Subscription();
  // Data received from the store
  timeSeriesParamsA: TimeSeriesParams | null = null;
  timeSeriesParamsB: TimeSeriesParams | null = null;
  // Data received from the API
  dataA: any[] = [];
  dataB: any[] = [];

  private randomInt = () => {
    return Math.floor(Math.random() * 100);
  };

  public lineChartData: ChartConfiguration<'line'>['data'] = {
    labels: ['January', 'February', 'March', 'April', 'May', 'June', 'July'],
    datasets: [
      {
        data: [
          this.randomInt(),
          this.randomInt(),
          this.randomInt(),
          this.randomInt(),
          this.randomInt(),
          this.randomInt(),
          this.randomInt(),
        ],
        label: 'Series A',
        fill: true,
        tension: 0.5,
        borderColor: 'black',
        backgroundColor: 'rgba(255,0,0,0.3)',
      },
    ],
  };

  public lineChartOptions: ChartOptions<'line'> = {
    responsive: false,
  };
  public lineChartLegend = true;

  constructor(
    private api: ApiService,
    private storeService: StoreService,
  ) {}

  ngOnInit() {
    this.storeService.getDataA().subscribe((res) => {
      this.timeSeriesParamsA = res;
      if (res) this.callTimeSeriesApi('A');
      else this.updateChart();
    });

    this.storeService.getDataB().subscribe((res) => {
      this.timeSeriesParamsB = res;
      if (res) this.callTimeSeriesApi('B');
      else this.updateChart();
    });
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
          this.currentState = ComponentState.EMPTY;
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

    // Labels = ceux du premier jeu de données disponible
    const labels = (hasA ? this.dataA : this.dataB).map((d: any) => d.date || d.label);

    const datasets: any[] = [];

    if (hasA) {
      datasets.push({
        data: this.dataA.map((d: any) => d.value),
        label: 'Période A',
        borderColor: 'rgba(54,162,235,1)',
        backgroundColor: 'rgba(54,162,235,0.3)',
        fill: true,
        tension: 0.3,
      });
    }

    if (hasB) {
      datasets.push({
        data: this.dataB.map((d: any) => d.value),
        label: 'Période B',
        borderColor: 'rgba(255,99,132,1)',
        backgroundColor: 'rgba(255,99,132,0.3)',
        fill: true,
        tension: 0.3,
      });
    }

    this.lineChartData = { labels, datasets };
  }
}
