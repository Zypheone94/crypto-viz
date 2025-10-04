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
  timeSeriesParams: TimeSeriesParams | null = null;
  // Data received from the API
  data: any[] = [];

  public lineChartData: ChartConfiguration<'line'>['data'] = {
    labels: ['January', 'February', 'March', 'April', 'May', 'June', 'July'],
    datasets: [
      {
        data: [65, 59, 80, 81, 56, 55, 40],
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
    this.dataSubscription = this.storeService.data$.subscribe((data) => {
      console.log(data);
      this.data = data;
    });

    this.api
      // Fake API call to replace with good values later
      .getTimeseries(this.timeSeriesParams)
      .subscribe({
        next: (data) => {
          console.log('Data reçue:', data);
          this.data = data;

          if (!data || data.length === 0) {
            console.log('Pas de données → EMPTY');
            this.currentState = ComponentState.EMPTY;
            return;
          }

          console.log('Données disponibles → READY');
          this.currentState = ComponentState.READY;
        },
        error: (err) => {
          console.error('Erreur API', err);
          this.currentState = ComponentState.ERROR;
        },
      });
  }
}
