import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { MatButtonModule } from '@angular/material/button';
import { ApiService } from '../../../services/api.service';

interface LinearRegressionPredictionResponse {
  symbol: string;
  target_ts: string;
  prediction: number;
  last_observation_ts?: string;
  last_price?: number;
  model_version?: string;
  features?: Record<string, number>;
}

interface SymbolOption {
  code: string;
  label: string;
}

@Component({
  selector: 'app-linear-regression-next-hour',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatCardModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatFormFieldModule,
    MatSelectModule,
    MatButtonModule
  ],
  template: `
    <div class="lr-container">
      <mat-card class="chart-card">
        <mat-card-header>
          <mat-card-title class="chart-title">
            <mat-icon class="title-icon">analytics</mat-icon>
            Prédiction prochaine heure (régression linéaire)
          </mat-card-title>
          <mat-card-subtitle>
            Prévision du prix pour la prochaine heure d'aujourd'hui
          </mat-card-subtitle>
        </mat-card-header>

        <mat-card-content class="chart-content">

          <div class="controls-section">
            <mat-form-field appearance="outline">
              <mat-label>Symbole</mat-label>
              <mat-select
                [(ngModel)]="selectedSymbol"
                (selectionChange)="onSymbolChange()"
                [disabled]="isSymbolsLoading || isLoading">

                <mat-option *ngIf="isSymbolsLoading" disabled>
                  <mat-spinner diameter="20"></mat-spinner>
                  Chargement des symboles...
                </mat-option>

                <ng-container *ngIf="!isSymbolsLoading">
                  <mat-option
                    *ngFor="let s of symbols"
                    [value]="s.code">
                    {{ s.label || s.code }}
                  </mat-option>
                </ng-container>
              </mat-select>
            </mat-form-field>

            <div class="info-next-hour">
              <mat-icon>schedule</mat-icon>
              <div>
                <div class="label">Horizon de prédiction</div>
                <div class="value">
                  {{ nextHourLabel }}
                </div>
              </div>
            </div>

            <button
              mat-raised-button
              color="primary"
              class="action-button"
              (click)="loadPrediction()"
              [disabled]="isLoading || !selectedSymbol">
              <mat-icon>refresh</mat-icon>
              Mettre à jour la prédiction
            </button>
          </div>

          <div class="error-container" *ngIf="symbolsError && !isSymbolsLoading">
            <mat-icon>error_outline</mat-icon>
            <span>{{ symbolsError }}</span>
          </div>

          <div class="loading-container" *ngIf="isLoading">
            <mat-spinner diameter="50"></mat-spinner>
            <p>Calcul de la prédiction en cours...</p>
          </div>

          <div class="error-container" *ngIf="errorMessage && !isLoading">
            <mat-icon>error_outline</mat-icon>
            <span>{{ errorMessage }}</span>
          </div>

          <div class="result-section" *ngIf="prediction && !isLoading">
            <div class="result-header">
              <h2>
                {{ prediction.symbol }} &mdash;
                {{ targetDateTimeLabel }}
              </h2>
              <p *ngIf="prediction.model_version" class="model-version">
                Modèle : {{ prediction.model_version }}
              </p>
            </div>

            <div class="stats-grid">
              <mat-card class="stat-card main">
                <mat-card-content>
                  <div class="stat-content">
                    <mat-icon class="stat-icon primary">trending_up</mat-icon>
                    <div class="stat-info">
                      <p class="stat-label">Prix prédit (prochaine heure)</p>
                      <h3>{{ prediction.prediction | number:'1.2-2' }} $</h3>
                    </div>
                  </div>
                </mat-card-content>
              </mat-card>
              <mat-card class="stat-card" *ngIf="prediction.last_price != null">
                <mat-card-content>
                  <div class="stat-content">
                    <mat-icon class="stat-icon">history</mat-icon>
                    <div class="stat-info">
                      <p class="stat-label">Dernier prix connu</p>
                      <h3>{{ prediction.last_price | number:'1.2-2' }} $</h3>
                      <p class="stat-sub" *ngIf="prediction.last_observation_ts">
                        au {{ prediction.last_observation_ts | date:'short' }}
                      </p>
                    </div>
                  </div>
                </mat-card-content>
              </mat-card>
              <mat-card class="stat-card" *ngIf="predictedChangePct != null">
                <mat-card-content>
                  <div class="stat-content">
                    <mat-icon
                      class="stat-icon"
                      [ngClass]="predictedChangePct >= 0 ? 'success' : 'danger'">
                      {{ predictedChangePct >= 0 ? 'north_east' : 'south_east' }}
                    </mat-icon>
                    <div class="stat-info">
                      <p class="stat-label">Variation prévue</p>
                      <h3>
                        {{ predictedChangePct | number:'1.2-2' }} %
                      </h3>
                      <p class="stat-sub">
                        vs dernier prix observé
                      </p>
                    </div>
                  </div>
                </mat-card-content>
              </mat-card>
            </div>
            <div class="features-card" *ngIf="prediction?.features && featureEntries.length">
              <h3>Principales features utilisées</h3>
              <div class="features-grid">
                <div class="feature-item" *ngFor="let feat of featureEntries">
                  <span class="feature-name">{{ feat.key }}</span>
                  <span class="feature-value">
                    {{ feat.value | number:'1.2-2' }}
                  </span>
                </div>
              </div>
            </div>
          </div>

        </mat-card-content>
      </mat-card>
    </div>
  `,
  styleUrls: ['./time-series.css'],
  styles: [`
    .lr-container {
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
      color: #3f51b5;
    }

    .chart-content {
      padding: 1.5rem;
    }

    .controls-section {
      display: flex;
      gap: 1rem;
      margin-bottom: 1.5rem;
      flex-wrap: wrap;
      align-items: center;
    }

    .controls-section mat-form-field {
      min-width: 180px;
    }

    .info-next-hour {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      padding: 0.75rem 1rem;
      border-radius: 8px;
      background: #f5f5f5;
      color: #555;
    }

    .info-next-hour mat-icon {
      color: #3f51b5;
    }

    .info-next-hour .label {
      font-size: 0.8rem;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      color: #777;
    }

    .info-next-hour .value {
      font-weight: 600;
    }

    .action-button {
      white-space: nowrap;
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }

    .loading-container {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      height: 200px;
      gap: 1rem;
    }

    .error-container {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      padding: 0.75rem 1rem;
      border-radius: 8px;
      background: #ffebee;
      color: #c62828;
      margin-bottom: 1rem;
    }

    .error-container mat-icon {
      font-size: 20px;
    }

    .result-section {
      display: flex;
      flex-direction: column;
      gap: 1.5rem;
    }

    .result-header h2 {
      margin: 0;
      font-size: 1.4rem;
      font-weight: 600;
      color: #333;
    }

    .model-version {
      margin: 0.25rem 0 0 0;
      font-size: 0.85rem;
      color: #777;
    }

    .stats-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 1rem;
    }

    .stat-card {
      border-radius: 8px;
      transition: transform 0.2s ease, box-shadow 0.2s ease;
    }

    .stat-card.main {
      border-left: 4px solid #3f51b5;
    }

    .stat-card:hover {
      transform: translateY(-2px);
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.12);
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

    .stat-icon.primary {
      color: #3f51b5;
    }

    .stat-icon.success {
      color: #4CAF50;
    }

    .stat-icon.danger {
      color: #FF5722;
    }

    .stat-info {
      display: flex;
      flex-direction: column;
    }

    .stat-label {
      margin: 0;
      font-size: 0.85rem;
      color: #777;
    }

    .stat-info h3 {
      margin: 0.1rem 0 0;
      font-size: 1.5rem;
      font-weight: 700;
      color: #333;
    }

    .stat-sub {
      margin: 0.2rem 0 0;
      font-size: 0.8rem;
      color: #888;
    }

    .features-card {
      padding: 1rem 1.25rem;
      border-radius: 8px;
      border: 1px dashed #e0e0e0;
      background: #fafafa;
    }

    .features-card h3 {
      margin-top: 0;
      margin-bottom: 0.75rem;
      font-size: 1rem;
      font-weight: 600;
    }

    .features-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 0.5rem 1rem;
    }

    .feature-item {
      display: flex;
      justify-content: space-between;
      font-size: 0.85rem;
      padding: 0.35rem 0.5rem;
      border-radius: 4px;
      background: #fff;
    }

    .feature-name {
      color: #555;
    }

    .feature-value {
      font-weight: 600;
      color: #333;
    }

    @media (max-width: 768px) {
      .lr-container {
        padding: 0.5rem;
        gap: 1rem;
      }

      .controls-section {
        flex-direction: column;
        align-items: stretch;
      }

      .action-button {
        width: 100%;
        justify-content: center;
      }
    }
  `]
})
export class LinearRegressionNextHourComponent implements OnInit {

  selectedSymbol = '';
  symbols: SymbolOption[] = [];
  isSymbolsLoading = false;
  symbolsError = '';

  isLoading = false;
  errorMessage = '';

  prediction: LinearRegressionPredictionResponse | null = null;
  predictedChangePct: number | null = null;

  constructor(private apiService: ApiService) {}

  ngOnInit(): void {
    this.loadSymbols();
  }
  get nextHourLabel(): string {
    const target = this.computeNextHour();
    return target.toLocaleTimeString('fr-FR', {
      hour: '2-digit',
      minute: '2-digit'
    });
  }

  get targetDateTimeLabel(): string {
    if (!this.prediction?.target_ts) return '';
    const d = new Date(this.prediction.target_ts);
    return d.toLocaleString('fr-FR');
  }

  get featureEntries() {
    if (!this.prediction?.features) return [];
    return Object.entries(this.prediction.features).map(([key, value]) => ({
      key,
      value: Number(value)
    }));
  }
  private loadSymbols(): void {
    this.isSymbolsLoading = true;
    this.symbolsError = '';
    this.apiService.getSymbols().subscribe({
      next: (res: any) => {
        this.isSymbolsLoading = false;
        const rawData =
          res?.response ??
          res?.data ??
          res;

        let items: any[] = [];

        if (Array.isArray(rawData)) {
          items = rawData;
        } else if (rawData && Array.isArray(rawData.results)) {
          items = rawData.results;
        }

        this.symbols = items
          .map((row: any): SymbolOption => {
            if (typeof row === 'string') {
              return {
                code: row,
                label: row
              };
            }
            const code = row.symbol || row.code || row.ticker || '';
            const name = row.name || row.label || '';
            return {
              code,
              label: name ? `${code} (${name})` : code
            };
          })
          .filter(s => !!s.code);

        if (!this.symbols.length) {
          this.symbolsError = 'Aucun symbole disponible.';
          return;
        }

        if (!this.selectedSymbol) {
          this.selectedSymbol = this.symbols[0].code;
        }

        this.loadPrediction();
      },
      error: (err) => {
        console.error('Error loading symbols:', err);
        this.isSymbolsLoading = false;
        this.symbolsError =
          err?.error?.detail ||
          err?.message ||
          'Impossible de récupérer la liste des symboles.';
      }
    });
  }


  onSymbolChange(): void {
    if (!this.selectedSymbol) return;
    this.loadPrediction();
  }
  private computeNextHour(): Date {
    const now = new Date();
    const target = new Date(now);
    target.setMinutes(0, 0, 0);
    target.setHours(target.getHours() + 1);
    return target;
  }
loadPrediction(): void {
  if (!this.selectedSymbol) return;

  this.isLoading = true;
  this.errorMessage = '';
  this.prediction = null;
  this.predictedChangePct = null;

  const symbol = this.selectedSymbol;

  this.apiService.getLinearRegressionPrediction(symbol).subscribe({
    next: (res: any) => {
      console.log('Linear regression prediction response:', res);
      this.isLoading = false;
      const raw =
        res?.response?.data ??
        res?.data ??
        res;

      const payload: LinearRegressionPredictionResponse = {
        symbol: raw.symbol || symbol,
        target_ts: raw.target_ts || raw.date_end || new Date().toISOString(),
        prediction: Number(raw.prediction ?? raw.price_pred ?? 0),
        last_observation_ts: raw.last_observation_ts || raw.date_start,
        last_price:
          raw.last_price != null
            ? Number(raw.last_price)
            : raw.price_now != null
            ? Number(raw.price_now)
            : undefined,
        model_version: raw.model_version,
        features: raw.features || raw.features_used
      };

      this.prediction = payload;

      if (payload.last_price != null && payload.last_price !== 0) {
        this.predictedChangePct =
          ((payload.prediction - payload.last_price) / payload.last_price) * 100;
      } else {
        this.predictedChangePct = null;
      }
    },
    error: (err) => {
      console.error('Error fetching linear regression prediction:', err);
      this.isLoading = false;
      this.errorMessage =
        err?.error?.detail ||
        err?.message ||
        'Impossible de récupérer la prédiction pour la prochaine heure.';
    }
  });
  }
}
