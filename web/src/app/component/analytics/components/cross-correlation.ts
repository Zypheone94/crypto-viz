import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { ApiService } from '../../../services/api.service';

interface CorrelationResult {
    symbol: string;
    optimal_lag: number;
    max_correlation: number;
    interpretation: string;
    strength: string;
    correlations: { [key: string]: number };
    data_points: number;
}

interface SymbolInfo {
    symbol: string;
    data_points: number;
}

@Component({
    selector: 'app-cross-correlation',
    standalone: true,
    imports: [CommonModule, FormsModule],
    templateUrl: './cross-correlation.html',
    styleUrls: ['./cross-correlation.css']
})
export class CrossCorrelationComponent implements OnInit {
    symbols: SymbolInfo[] = [];
    selectedSymbol: string = '';
    maxLag: number = 12;
    result: CorrelationResult | null = null;
    loading: boolean = false;
    loadingSymbols: boolean = false;
    error: string | null = null;

    // Chart data
    chartData: { lag: number; correlation: number }[] = [];
    maxCorrelationValue: number = 1;

    constructor(private apiService: ApiService, private http: HttpClient) { }

    ngOnInit(): void {
        this.loadSymbols();
    }

    loadSymbols(): void {
        this.loadingSymbols = true;
        this.http.get<any>(`${this.apiService.baseUrl}/data/cross-correlation/symbols`)
            .subscribe({
                next: (response: any) => {
                    if (response.response?.symbols) {
                        this.symbols = response.response.symbols;
                        if (this.symbols.length > 0 && !this.selectedSymbol) {
                            this.selectedSymbol = this.symbols[0].symbol;
                        }
                    }
                    this.loadingSymbols = false;
                },
                error: (err: any) => {
                    console.error('Error loading symbols:', err);
                    // Fallback symbols if API fails
                    this.symbols = [
                        { symbol: 'BTC', data_points: 0 },
                        { symbol: 'ETH', data_points: 0 },
                        { symbol: 'SOL', data_points: 0 }
                    ];
                    this.selectedSymbol = 'BTC';
                    this.loadingSymbols = false;
                }
            });
    }

    analyze(): void {
        if (!this.selectedSymbol) return;

        this.loading = true;
        this.error = null;
        this.result = null;

        const url = `${this.apiService.baseUrl}/data/cross-correlation?symbol=${this.selectedSymbol}&max_lag=${this.maxLag}`;

        this.http.get<any>(url).subscribe({
            next: (response: any) => {
                if (response.response) {
                    this.result = response.response;
                    this.prepareChartData();
                } else if (response.response?.error) {
                    this.error = response.response.error;
                }
                this.loading = false;
            },
            error: (err: any) => {
                this.error = 'Erreur lors de l\'analyse. Vérifiez que la base de données contient des données.';
                console.error('Analysis error:', err);
                this.loading = false;
            }
        });
    }

    prepareChartData(): void {
        if (!this.result?.correlations) {
            this.chartData = [];
            return;
        }

        this.chartData = Object.entries(this.result.correlations)
            .map(([lag, corr]) => ({
                lag: parseInt(lag),
                correlation: corr as number
            }))
            .sort((a, b) => a.lag - b.lag);

        this.maxCorrelationValue = Math.max(
            ...this.chartData.map(d => Math.abs(d.correlation)),
            0.1
        );
    }

    getBarHeight(correlation: number): number {
        return (Math.abs(correlation) / this.maxCorrelationValue) * 100;
    }

    getBarColor(correlation: number): string {
        if (correlation > 0.3) return '#10b981'; // Green
        if (correlation > 0) return '#6ee7b7';   // Light green
        if (correlation > -0.3) return '#fca5a5'; // Light red
        return '#ef4444'; // Red
    }

    getStrengthClass(strength: string): string {
        switch (strength?.toLowerCase()) {
            case 'strong': return 'strength-strong';
            case 'moderate': return 'strength-moderate';
            case 'weak': return 'strength-weak';
            default: return 'strength-none';
        }
    }
}
