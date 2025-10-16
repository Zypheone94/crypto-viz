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
  // Data received from the store
  timeSeriesParamsA: TimeSeriesParams | null = null;
  timeSeriesParamsB: TimeSeriesParams | null = null;
  // Data received from the API
  dataA: any[] = [];
  dataB: any[] = [];

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
          text: 'Valeur',
        },
      },
    },
    plugins: {
      legend: {
        display: true,
        position: 'top',
      },
      tooltip: {
        filter: function (tooltipItem) {
          // Ne pas afficher de tooltip pour les valeurs null
          return tooltipItem.parsed.y !== null;
        },
      },
    },
    elements: {
      point: {
        radius: function (context) {
          // Ne pas afficher de points pour les valeurs null
          return context.parsed.y === null ? 0 : 3;
        },
      },
    },
  };
  public lineChartLegend = true;

  constructor(
    private api: ApiService,
    private storeService: StoreService,
  ) {}

  ngOnInit() {
    this.dataASubscription = this.storeService.getDataA().subscribe((res) => {
      this.timeSeriesParamsA = res;
      if (res) this.callTimeSeriesApi('A');
      else {
        this.dataA = [];
        this.updateChart();
      }
    });

    this.dataBSubscription = this.storeService.getDataB().subscribe((res) => {
      this.timeSeriesParamsB = res;
      if (res) this.callTimeSeriesApi('B');
      else {
        this.dataB = [];
        this.updateChart();
      }
    });
  }

  ngOnDestroy() {
    this.dataASubscription.unsubscribe();
    this.dataBSubscription.unsubscribe();
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
      // Pour chaque date de la timeline, récupérer la valeur de A (ou null si absente)
      const dataAValues = sortedDates.map((date) =>
        dataAMap.has(date) ? dataAMap.get(date) : null,
      );

      datasets.push({
        data: dataAValues,
        label: 'Période A',
        borderColor: 'rgba(54,162,235,1)',
        backgroundColor: 'rgba(54,162,235,0.3)',
        fill: false,
        tension: 0.3,
        spanGaps: true,
      });
    }

    if (hasB && dataBMap.size > 0) {
      // Pour chaque date de la timeline, récupérer la valeur de B (ou null si absente)
      const dataBValues = sortedDates.map((date) =>
        dataBMap.has(date) ? dataBMap.get(date) : null,
      );

      datasets.push({
        data: dataBValues,
        label: 'Période B',
        borderColor: 'rgba(255,99,132,1)',
        backgroundColor: 'rgba(255,99,132,0.3)',
        fill: false,
        tension: 0.3,
        spanGaps: true,
      });
    }

    // Formater les labels selon la granularité d'affichage
    const formattedLabels = sortedDates.map((date) => {
      const d = new Date(date);

      if (displayGranularity === 'hour') {
        // Affichage avec heures
        return d.toLocaleString('fr-FR', {
          day: '2-digit',
          month: '2-digit',
          hour: '2-digit',
          minute: '2-digit',
        });
      } else {
        // Affichage jours uniquement
        return d.toLocaleDateString('fr-FR', {
          day: '2-digit',
          month: '2-digit',
        });
      }
    });

    this.lineChartData = {
      labels: formattedLabels,
      datasets,
    };
  }
}
