import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatIconModule } from '@angular/material/icon';

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
export class TopLosersComponent implements OnInit {
  losers: CryptoLoser[] = [];
  isLoading = false;



  ngOnInit(): void {
    this.loadMockData();
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