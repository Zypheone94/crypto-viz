import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatIconModule } from '@angular/material/icon';
import { StoreService } from '../../../services/store.service';
import { ApiService } from '../../../services/api.service';
import { Subscription } from 'rxjs';

interface CryptoLoser {
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
  selector: 'app-top-losers',
  standalone: true,
  imports: [CommonModule, MatProgressSpinnerModule, MatIconModule],
  templateUrl: './top-losers.html',
  styleUrls: ['./time-series.css'],
})
export class TopLosersComponent implements OnInit, OnDestroy {
  losers: CryptoLoser[] = [];
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
        this.loadShortTermLosers();
      } else if (daysDiff <= 7) {
        this.loadWeeklyLosers();
      } else {
        this.loadLongTermLosers();
      }
      this.isLoading = false;
    }, 500);
  }

  private loadData(): void {
    this.isLoading = true;
    
    this.apiService.getTopLosers(5).subscribe({
      next: (response: any) => {
        // Handle the backend response structure
        if (response && response.response && response.response.data && response.response.data.losers) {
          this.losers = response.response.data.losers.map((item: any) => ({
            symbol: item.symbol,
            name: item.name,
            price: parseFloat(item.price.replace('$', '')),
            change24h: parseFloat(item.change_24h_value) || 0,
            changePercent24h: parseFloat(item.change_24h_value) || 0,
            volume24h: item.market_cap || 0,
            marketCap: item.market_cap || 0
          }));
        } else {
          this.losers = [];
        }
        this.isLoading = false;
      },
      error: (error) => {
        console.error('Error loading top losers:', error);
        this.losers = [];
        this.isLoading = false;
      }
    });
  }

  private loadMockDataOriginal(): void {
    this.losers = [
        {
          symbol: 'DOGE',
          name: 'Dogecoin',
          price: 0.084,
          change24h: -0.0055,
          changePercent24h: -6.15,
          volume24h: 1200000000,
          marketCap: 12100000000
        },
        {
          symbol: 'SHIB',
          name: 'Shiba Inu',
          price: 0.0000145,
          change24h: -0.0000009,
          changePercent24h: -5.84,
          volume24h: 450000000,
          marketCap: 8550000000
        },
        {
          symbol: 'XRP',
          name: 'XRP',
          price: 0.52,
          change24h: -0.031,
          changePercent24h: -5.63,
          volume24h: 1800000000,
          marketCap: 29500000000
        },
        {
          symbol: 'LTC',
          name: 'Litecoin',
          price: 88.5,
          change24h: -5.2,
          changePercent24h: -5.55,
          volume24h: 650000000,
          marketCap: 6580000000
        },
        {
          symbol: 'TRX',
          name: 'TRON',
          price: 0.162,
          change24h: -0.0089,
          changePercent24h: -5.21,
          volume24h: 380000000,
          marketCap: 14000000000
        },
        {
          symbol: 'BCH',
          name: 'Bitcoin Cash',
          price: 485,
          change24h: -26,
          changePercent24h: -5.09,
          volume24h: 420000000,
          marketCap: 9600000000
        },
        {
          symbol: 'UNI',
          name: 'Uniswap',
          price: 9.85,
          change24h: -0.51,
          changePercent24h: -4.93,
          volume24h: 280000000,
          marketCap: 7400000000
        },
        {
          symbol: 'ATOM',
          name: 'Cosmos',
          price: 7.25,
          change24h: -0.37,
          changePercent24h: -4.86,
          volume24h: 220000000,
          marketCap: 2840000000
        }
      ];

  }

  private loadShortTermLosers(): void {
    this.loadData();
  }

  private loadWeeklyLosers(): void {
    this.loadData();
  }

  private loadLongTermLosers(): void {
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
    } else if (price >= 0.01) {
      return price.toFixed(4);
    } else {
      return price.toFixed(8);
    }
  }

  getTotalVolume(): string {
    const total = this.losers.reduce((sum, l) => sum + l.volume24h, 0);
    return this.formatNumber(total);
  }

  getAverageLoss(): string {
    if (this.losers.length === 0) return '0.00';
    const average = this.losers.reduce((sum, l) => sum + l.changePercent24h, 0) / this.losers.length;
    return average.toFixed(2);
  }
}