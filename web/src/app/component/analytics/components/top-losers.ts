import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatIconModule } from '@angular/material/icon';
import { StoreService } from '../../../services/store.service';
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
        this.loadShortTermLosers();
      } else if (daysDiff <= 7) {
        this.loadWeeklyLosers();
      } else {
        this.loadLongTermLosers();
      }
      this.isLoading = false;
    }, 500);
  }

  private loadMockData(): void {
    this.isLoading = true;
    
    // Simulate API call delay
    setTimeout(() => {
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

      this.isLoading = false;
    }, 800);
  }

  private loadShortTermLosers(): void {
    // Data for 24h or less - more volatile losers
    this.losers = [
      {
        symbol: 'LUNA',
        name: 'Terra Luna Classic',
        price: 0.00018,
        change24h: -0.000085,
        changePercent24h: -32.1,
        volume24h: 850000000,
        marketCap: 1200000000
      },
      {
        symbol: 'FTT',
        name: 'FTX Token',
        price: 2.8,
        change24h: -1.2,
        changePercent24h: -30.0,
        volume24h: 420000000,
        marketCap: 920000000
      },
      {
        symbol: 'SAFEMOON',
        name: 'SafeMoon',
        price: 0.00035,
        change24h: -0.00015,
        changePercent24h: -30.0,
        volume24h: 180000000,
        marketCap: 210000000
      }
    ];
  }

  private loadWeeklyLosers(): void {
    // Data for 7 days - moderate losers
    this.losers = [
      {
        symbol: 'XRP',
        name: 'Ripple',
        price: 0.52,
        change24h: -0.045,
        changePercent24h: -8.0,
        volume24h: 1200000000,
        marketCap: 29000000000
      },
      {
        symbol: 'ADA',
        name: 'Cardano',
        price: 0.61,
        change24h: -0.041,
        changePercent24h: -6.3,
        volume24h: 750000000,
        marketCap: 21500000000
      },
      {
        symbol: 'DOGE',
        name: 'Dogecoin',
        price: 0.078,
        change24h: -0.005,
        changePercent24h: -6.0,
        volume24h: 1100000000,
        marketCap: 11200000000
      }
    ];
  }

  private loadLongTermLosers(): void {
    // Data for 30+ days - stable decliners
    this.losers = [
      {
        symbol: 'ETH',
        name: 'Ethereum',
        price: 3650,
        change24h: -45,
        changePercent24h: -1.2,
        volume24h: 25000000000,
        marketCap: 438000000000
      },
      {
        symbol: 'BNB',
        name: 'BNB',
        price: 620,
        change24h: -8.5,
        changePercent24h: -1.4,
        volume24h: 1900000000,
        marketCap: 90000000000
      },
      {
        symbol: 'SOL',
        name: 'Solana',
        price: 235,
        change24h: -4.2,
        changePercent24h: -1.8,
        volume24h: 7800000000,
        marketCap: 110000000000
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