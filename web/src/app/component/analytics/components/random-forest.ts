import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatIconModule } from '@angular/material/icon';
import { MatDividerModule } from '@angular/material/divider';
import { BaseChartDirective } from 'ng2-charts';
import { ChartConfiguration } from 'chart.js';

import { ApiService } from '../../../services/api.service';
import { ComponentState } from '../../../shared/enums/component-state.enum';

interface ModelMetrics {
  accuracy: number;
  precision: number;
  recall: number;
  f1_score: number;
  confusion_matrix?: number[][];
}

interface FeatureImportance {
  [key: string]: number;
}

interface ModelInfo {
  symbol: string;
  metrics: ModelMetrics;
  feature_importance: FeatureImportance;
  feature_names?: string[];
}

interface Prediction {
  timestamp: string;
  price: number;
  prediction: string;
  probability: number;
  features: { [key: string]: number };
}

interface PredictionResponse {
  symbol: string;
  predictions: Prediction[];
}

@Component({
  selector: 'app-random-forest',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatProgressSpinnerModule,
    MatSelectModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatCardModule,
    MatChipsModule,
    MatIconModule,
    MatDividerModule,
    BaseChartDirective
  ],
  templateUrl: './random-forest.html',
  styleUrls: ['./random-forest.css']
})
export class RandomForestComponent implements OnInit {
  componentState = ComponentState;
  currentState: ComponentState = ComponentState.NOTREADY;
  trainingState: ComponentState = ComponentState.NOTREADY;
  predictionState: ComponentState = ComponentState.NOTREADY;
  errorMessage = '';
  trainingMessage = '';
  predictionMessage = '';

  // Training parameters
  trainSymbol: string = '';
  nEstimators: number = 100;
  maxDepth: number = 10;
  testSize: number = 0.2;

  // Prediction parameters
  predictSymbol: string = 'BTC';
  recentCount: number = 5;

  // Available symbols for dropdown
  availableSymbols: string[] = [];
  loadingSymbols: boolean = false;

  // UI state
  showDetails: boolean = false;

  // Model info
  modelInfo: ModelInfo | null = null;

  // Predictions
  predictions: Prediction[] = [];

  // Chart data for feature importance
  featureImportanceChartData: ChartConfiguration<'bar'>['data'] = {
    labels: [],
    datasets: []
  };

  featureImportanceChartOptions: ChartConfiguration<'bar'>['options'] = {
    responsive: true,
    maintainAspectRatio: false,
    indexAxis: 'y',
    plugins: {
      legend: {
        display: false
      },
      title: {
        display: true,
        text: 'Importance des Features'
      },
      tooltip: {
        callbacks: {
          label: (context) => {
            const value = context.parsed?.x ?? 0;
            return `Importance: ${(value * 100).toFixed(2)}%`;
          }
        }
      }
    },
    scales: {
      x: {
        title: {
          display: true,
          text: 'Importance'
        },
        min: 0,
        max: 1
      }
    }
  };

  constructor(private apiService: ApiService) {}

  ngOnInit(): void {
    this.loadModelInfo();
    this.loadAvailableSymbols();
  }

  loadAvailableSymbols(): void {
    this.loadingSymbols = true;
    this.apiService.getAvailableSymbols().subscribe({
      next: (data: any) => {
        if (data.response && Array.isArray(data.response)) {
          this.availableSymbols = data.response.sort();
          if (this.availableSymbols.length > 0 && !this.predictSymbol) {
            this.predictSymbol = this.availableSymbols[0];
          }
        }
        this.loadingSymbols = false;
      },
      error: (err: any) => {
        console.error('Failed to load symbols:', err);
        // Fallback to common symbols
        this.availableSymbols = ['BTC', 'ETH', 'ADA', 'SOL', 'XRP', 'DOGE', 'DOT', 'MATIC', 'LINK', 'UNI'];
        this.loadingSymbols = false;
      }
    });
  }

  loadModelInfo(): void {
    this.currentState = ComponentState.LOADING;

    this.apiService.getRandomForestInfo().subscribe({
      next: (data: any) => {
        if (data.response) {
          this.modelInfo = data.response;
          this.updateFeatureImportanceChart();
          this.currentState = ComponentState.READY;
        } else {
          this.currentState = ComponentState.NOTREADY;
        }
      },
      error: (err) => {
        console.error('Failed to load model info:', err);
        this.currentState = ComponentState.NOTREADY;
      }
    });
  }

  trainModel(): void {
    this.trainingState = ComponentState.LOADING;
    this.trainingMessage = '';

    const params = {
      symbol: this.trainSymbol || null,
      n_estimators: this.nEstimators,
      max_depth: this.maxDepth,
      test_size: this.testSize
    };

    this.apiService.trainRandomForest(params).subscribe({
      next: (data: any) => {
        if (data.response) {
          this.modelInfo = data.response;
          this.updateFeatureImportanceChart();
          this.trainingState = ComponentState.READY;
          this.trainingMessage = 'Modèle entraîné avec succès !';
          this.currentState = ComponentState.READY;

          // Clear message after 3 seconds
          setTimeout(() => {
            this.trainingMessage = '';
            this.trainingState = ComponentState.NOTREADY;
          }, 3000);
        }
      },
      error: (err) => {
        console.error('Training failed:', err);
        this.trainingState = ComponentState.ERROR;
        this.trainingMessage = err.error?.detail?.msg || 'Erreur lors de l\'entraînement';
      }
    });
  }

  predict(): void {
    this.predictionState = ComponentState.LOADING;
    this.predictionMessage = '';
    this.predictions = [];

    this.apiService.predictRandomForest(this.predictSymbol, this.recentCount).subscribe({
      next: (data: any) => {
        if (data.response) {
          const response = data.response as PredictionResponse;
          // Trier par probabilité décroissante (plus probable en premier)
          this.predictions = response.predictions.sort((a, b) => b.probability - a.probability);
          this.predictionState = ComponentState.READY;
          this.predictionMessage = `${this.predictions.length} prédiction(s) générée(s)`;
        }
      },
      error: (err: any) => {
        console.error('Prediction failed:', err);
        this.predictionState = ComponentState.ERROR;
        this.predictionMessage = err.error?.detail?.msg || 'Erreur lors de la prédiction';
      }
    });
  }

  updateFeatureImportanceChart(): void {
    if (!this.modelInfo?.feature_importance) return;

    const importance = this.modelInfo.feature_importance;
    const sortedFeatures = Object.entries(importance)
      .sort(([, a], [, b]) => b - a)
      .slice(0, 10); // Top 10 features

    this.featureImportanceChartData = {
      labels: sortedFeatures.map(([name]) => name),
      datasets: [
        {
          label: 'Importance',
          data: sortedFeatures.map(([, value]) => value),
          backgroundColor: 'rgba(54, 162, 235, 0.6)',
          borderColor: 'rgba(54, 162, 235, 1)',
          borderWidth: 1
        }
      ]
    };
  }

  getPredictionClass(prediction: string): string {
    return prediction === 'HAUSSE' ? 'prediction-up' : 'prediction-down';
  }

  getPredictionIcon(prediction: string): string {
    return prediction === 'HAUSSE' ? 'trending_up' : 'trending_down';
  }

  getMetricColor(metric: number): string {
    if (metric >= 0.8) return 'metric-excellent';
    if (metric >= 0.6) return 'metric-good';
    return 'metric-poor';
  }

  formatPercent(value: number): string {
    return `${(value * 100).toFixed(2)}%`;
  }

  // Global verdict methods
  getGlobalVerdict(): string {
    const hausseCount = this.predictions.filter(p => p.prediction === 'HAUSSE').length;
    const baisseCount = this.predictions.length - hausseCount;

    if (hausseCount > baisseCount) {
      const percentage = ((hausseCount / this.predictions.length) * 100).toFixed(0);
      return `✅ OUI, ça va MONTER (${percentage}% des prédictions)`;
    } else if (baisseCount > hausseCount) {
      const percentage = ((baisseCount / this.predictions.length) * 100).toFixed(0);
      return `❌ NON, ça va DESCENDRE (${percentage}% des prédictions)`;
    } else {
      return `⚖️ INCERTAIN - Tendance équilibrée`;
    }
  }

  getGlobalPredictionClass(): string {
    const hausseCount = this.predictions.filter(p => p.prediction === 'HAUSSE').length;
    const baisseCount = this.predictions.length - hausseCount;

    if (hausseCount > baisseCount) return 'verdict-up';
    if (baisseCount > hausseCount) return 'verdict-down';
    return 'verdict-neutral';
  }

  getGlobalPredictionIcon(): string {
    const hausseCount = this.predictions.filter(p => p.prediction === 'HAUSSE').length;
    const baisseCount = this.predictions.length - hausseCount;

    if (hausseCount > baisseCount) return 'trending_up';
    if (baisseCount > hausseCount) return 'trending_down';
    return 'trending_flat';
  }

  getAverageConfidence(): string {
    if (this.predictions.length === 0) return '0';
    const avg = this.predictions.reduce((sum, p) => sum + p.probability, 0) / this.predictions.length;
    return (avg * 100).toFixed(1);
  }

  getHaussePercentage(): string {
    const hausseCount = this.predictions.filter(p => p.prediction === 'HAUSSE').length;
    return ((hausseCount / this.predictions.length) * 100).toFixed(0);
  }

  getBaissePercentage(): string {
    const baisseCount = this.predictions.filter(p => p.prediction === 'BAISSE').length;
    return ((baisseCount / this.predictions.length) * 100).toFixed(0);
  }
}
