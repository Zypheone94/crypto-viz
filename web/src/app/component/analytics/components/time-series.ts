import { Component, OnInit } from '@angular/core';
import { ApiService } from '../../../services/api.service';
import { ComponentState } from '../../../shared/enums/component-state.enum';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { CommonModule } from '@angular/common';

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

  data: any[] = [];

  // mokedData
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

  constructor(private api: ApiService) {}

  ngOnInit() {
    this.api.getTimeseries({
      from: '2023-01-01T00:00:00Z',
      to: '2023-01-07T23:59:59Z',
      bucket: 'day',
    }).subscribe((data) => {
      this.data = data;
      console.log('Time Series Data:', data);
    });
  }
}
