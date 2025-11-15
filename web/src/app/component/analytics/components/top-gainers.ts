import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatIconModule } from '@angular/material/icon';
import { StoreService } from '../../../services/store.service';
import { ApiService } from '../../../services/api.service';
import { Subscription } from 'rxjs';

interface CryptoGainer {
  symbol: string;
  name: string;
  price: number;
  change24h: number;
  changePercent24h: number;
  volume24h: number;
  marketCap: number;
  image?: string;
}

@Component({
  selector: 'app-top-gainers',
  standalone: true,
  imports: [CommonModule, MatProgressSpinnerModule, MatIconModule],
  templateUrl: './top-gainers.html',
  styleUrls: ['./time-series.css'],
})
export class TopGainersComponent implements OnInit, OnDestroy {
  gainers: CryptoGainer[] = [];
  isLoading = false;
  private dateRangeSubscription: Subscription = new Subscription();

  constructor(
    private storeService: StoreService,
    private apiService: ApiService
  ) {}

  ngOnInit(): void {
    // Subscribe to date range changes
    this.dateRangeSubscription = this.storeService.dateRange$.subscribe((dateRange) => {
      if (dateRange.startDate && dateRange.endDate) {
        this.loadDataForDateRange(dateRange.startDate, dateRange.endDate);
      } else {
        this.loadData();
      }
    });
    
    this.loadData();
  }

  ngOnDestroy(): void {
    this.dateRangeSubscription.unsubscribe();
  }

  private loadDataForDateRange(startDate: Date, endDate: Date): void {
    this.isLoading = true;
    
    // Simulate different data based on date range
    const daysDiff = Math.ceil((endDate.getTime() - startDate.getTime()) / (1000 * 60 * 60 * 24));
    
    setTimeout(() => {
      if (daysDiff <= 1) {
        this.loadShortTermData();
      } else if (daysDiff <= 7) {
        this.loadWeeklyData();
      } else {
        this.loadLongTermData();
      }
      this.isLoading = false;
    }, 500);
  }

  private loadData(): void {
    this.isLoading = true;
    
    this.apiService.getTopGainers(5).subscribe({
      next: (data) => {
        this.gainers = data;
        this.isLoading = false;
      },
      error: (error) => {
        console.error('Error loading top gainers:', error);
        this.isLoading = false;
      }
    });
  }

  private loadShortTermData(): void {
    this.loadData();
  }

  private loadWeeklyData(): void {
    this.loadData();
  }

  private loadLongTermData(): void {
    this.loadData();
  }

  formatNumber(value: number): string {
    if (value >= 1e12) {
      return (value / 1e12).toFixed(2) + 'T';
    } else if (value >= 1e9) {
      return (value / 1e9).toFixed(2) + 'B';
    } else if (value >= 1e6) {
      return (value / 1e6).toFixed(2) + 'M';
    } else if (value >= 1e3) {
      return (value / 1e3).toFixed(2) + 'K';
    }
    return value.toFixed(2);
  }

  formatPrice(price: number): string {
    if (price >= 1) {
      return price.toFixed(2);
    } else {
      return price.toFixed(4);
    }
  }

  getTotalVolume(): string {
    const total = this.gainers.reduce((sum, g) => sum + g.volume24h, 0);
    return this.formatNumber(total);
  }

  getAverageGain(): string {
    if (this.gainers.length === 0) return '0.00';
    const average = this.gainers.reduce((sum, g) => sum + g.changePercent24h, 0) / this.gainers.length;
    return average.toFixed(2);
  }
}