import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatIconModule } from '@angular/material/icon';
import { StoreService } from '../../../services/store.service';
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

  constructor(private storeService: StoreService) {}

  ngOnInit(): void {
    // Subscribe to date range changes
    this.dateRangeSubscription = this.storeService.dateRange$.subscribe((dateRange) => {
      if (dateRange.startDate && dateRange.endDate) {
        this.loadDataForDateRange(dateRange.startDate, dateRange.endDate);
      } else {
        this.loadMockData();
      }
    });
    
    this.loadMockData();
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

  private loadMockData(): void {
    this.isLoading = true;
    
    // Simulate API call delay
    setTimeout(() => {
      this.gainers = [
        {
          symbol: 'BTC',
          name: 'Bitcoin',
          price: 67500,
          change24h: 3250,
          changePercent24h: 5.06,
          volume24h: 45000000000,
          marketCap: 1330000000000
        },
        {
          symbol: 'ETH',
          name: 'Ethereum',
          price: 3800,
          change24h: 180,
          changePercent24h: 4.97,
          volume24h: 25000000000,
          marketCap: 456000000000
        },
        {
          symbol: 'SOL',
          name: 'Solana',
          price: 195,
          change24h: 8.5,
          changePercent24h: 4.56,
          volume24h: 3500000000,
          marketCap: 91000000000
        },
        {
          symbol: 'ADA',
          name: 'Cardano',
          price: 0.68,
          change24h: 0.028,
          changePercent24h: 4.29,
          volume24h: 750000000,
          marketCap: 24000000000
        },
        {
          symbol: 'AVAX',
          name: 'Avalanche',
          price: 42.5,
          change24h: 1.7,
          changePercent24h: 4.17,
          volume24h: 650000000,
          marketCap: 16500000000
        },
        {
          symbol: 'DOT',
          name: 'Polkadot',
          price: 8.95,
          change24h: 0.35,
          changePercent24h: 4.07,
          volume24h: 420000000,
          marketCap: 11800000000
        },
        {
          symbol: 'MATIC',
          name: 'Polygon',
          price: 1.15,
          change24h: 0.044,
          changePercent24h: 3.98,
          volume24h: 380000000,
          marketCap: 11300000000
        },
        {
          symbol: 'LINK',
          name: 'Chainlink',
          price: 18.5,
          change24h: 0.68,
          changePercent24h: 3.82,
          volume24h: 950000000,
          marketCap: 11200000000
        }
      ];

      this.isLoading = false;
    }, 800);
  }

  private loadShortTermData(): void {
    // Data for 24h or less - more volatile gainers
    this.gainers = [
      {
        symbol: 'DOGE',
        name: 'Dogecoin',
        price: 0.42,
        change24h: 0.08,
        changePercent24h: 23.5,
        volume24h: 12000000000,
        marketCap: 62000000000
      },
      {
        symbol: 'SHIB',
        name: 'Shiba Inu',
        price: 0.000035,
        change24h: 0.000006,
        changePercent24h: 20.7,
        volume24h: 3200000000,
        marketCap: 20600000000
      },
      {
        symbol: 'PEPE',
        name: 'Pepe',
        price: 0.00002,
        change24h: 0.000003,
        changePercent24h: 18.2,
        volume24h: 1800000000,
        marketCap: 8400000000
      }
    ];
  }

  private loadWeeklyData(): void {
    // Data for 7 days - moderate gainers
    this.gainers = [
      {
        symbol: 'SOL',
        name: 'Solana',
        price: 245,
        change24h: 18,
        changePercent24h: 7.9,
        volume24h: 8500000000,
        marketCap: 115000000000
      },
      {
        symbol: 'AVAX',
        name: 'Avalanche',
        price: 42.5,
        change24h: 2.8,
        changePercent24h: 7.1,
        volume24h: 850000000,
        marketCap: 16500000000
      },
      {
        symbol: 'ATOM',
        name: 'Cosmos',
        price: 12.4,
        change24h: 0.75,
        changePercent24h: 6.4,
        volume24h: 420000000,
        marketCap: 4800000000
      }
    ];
  }

  private loadLongTermData(): void {
    // Data for 30+ days - stable gainers
    this.gainers = [
      {
        symbol: 'BTC',
        name: 'Bitcoin',
        price: 67500,
        change24h: 1200,
        changePercent24h: 1.8,
        volume24h: 45000000000,
        marketCap: 1330000000000
      },
      {
        symbol: 'ETH',
        name: 'Ethereum',
        price: 3800,
        change24h: 45,
        changePercent24h: 1.2,
        volume24h: 28000000000,
        marketCap: 456000000000
      },
      {
        symbol: 'BNB',
        name: 'BNB',
        price: 635,
        change24h: 5.5,
        changePercent24h: 0.9,
        volume24h: 2100000000,
        marketCap: 92000000000
      }
    ];
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