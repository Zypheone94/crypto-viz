import { Component, OnInit } from '@angular/core';
import { ApiService } from '../../services/api.service';
import { ComponentState } from '../../shared/enums/component-state.enum';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { CommonModule } from '@angular/common';

@Component({
    selector: 'app-time-series',
    standalone: true,
    imports: [MatProgressSpinnerModule, CommonModule],
    templateUrl: 'time-series.html'
})

export class TimeSeries implements OnInit {
    componentState = ComponentState;
    currentState: ComponentState = ComponentState.LOADING;
    errorMessage = '';

    data: any[] = [];   

    constructor(private api: ApiService) { }

    ngOnInit() {
        this.api.getTimeseries().subscribe(data => {
            this.data = data;
            console.log('Time Series Data:', data);
        });
     }
}