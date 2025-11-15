import { Component, OnInit, OnDestroy } from '@angular/core';
import { Router, NavigationEnd } from '@angular/router';
import { filter } from 'rxjs/operators';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { StoreService, NewsStatistics, NewsFilters } from '../../services/store.service';
import { ApiService } from '../../services/api.service';
import { Subscription } from 'rxjs';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MatInputModule } from '@angular/material/input';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatNativeDateModule } from '@angular/material/core';
import { MatIconModule } from '@angular/material/icon';
import { MatSelectModule } from '@angular/material/select';
import { MatButtonModule } from '@angular/material/button';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';

interface MarketData {
  symbol: string;
  name: string;
  price: number;
  change24h: number;
  changePercent24h: number;
}

interface MarketOverview {
  bitcoin: MarketData;
  ethereum: MarketData;
  totalMarketCap: {
    value: string;
    change: number;
  };
}

@Component({
  selector: 'app-main-layout',
  standalone: true,
  imports: [
    MatExpansionModule, 
    CommonModule, 
    RouterModule, 
    FormsModule,
    MatDatepickerModule,
    MatInputModule,
    MatFormFieldModule,
    MatNativeDateModule,
    MatIconModule,
    MatSelectModule,
    MatButtonModule,
    MatSlideToggleModule
  ],
  templateUrl: './main-layout.html',
  styleUrls: ['./main-layout.css'],
})
export class MainLayoutComponent implements OnInit, OnDestroy {
  selectedTab: string = 'home';
  private statisticsSubscription: Subscription = new Subscription();

  navItems = [
    { route: 'home', icon: 'home', label: 'Accueil' },
    { route: 'analytics', icon: 'analytics', label: 'Analytics' },
    { route: 'health-check', icon: 'health_and_safety', label: 'Health Check' },
    { route: 'news', icon: 'newspaper', label: 'News' },
  ];

  // Date range filter system - Period A
  startDate: Date = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000); // 7 days ago
  endDate: Date = new Date(); // today
  selectedPreset: string = '7d';

  // Date range filter system - Period B
  startDateB: Date = new Date(Date.now() - 14 * 24 * 60 * 60 * 1000); // 14 days ago
  endDateB: Date = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000); // 7 days ago
  selectedPresetB: string = '7d';

  // News filters
  newsFilters: NewsFilters = {
    section: 'all',
    dateRange: 'all',
    searchTerm: ''
  };

  // News statistics
  totalNewsCount = 0;
  todayNewsCount = 0;
  lastUpdateTime = '--:--';

  // Market data
  marketOverview: MarketOverview = {
    bitcoin: {
      symbol: 'BTC',
      name: 'Bitcoin',
      price: 42350,
      change24h: 1035,
      changePercent24h: 2.5
    },
    ethereum: {
      symbol: 'ETH',
      name: 'Ethereum',
      price: 2680,
      change24h: -32.6,
      changePercent24h: -1.2
    },
    totalMarketCap: {
      value: '$1.85T',
      change: 0.8
    }
  };

  constructor(
    private router: Router,
    private storeService: StoreService,
    private apiService: ApiService
  ) {}

  ngOnInit() {
    // Écouter les changements de route
    this.router.events
      .pipe(filter((event) => event instanceof NavigationEnd))
      .subscribe((event: NavigationEnd) => {
        this.updateSelectedTab(event.url);
      });

    this.updateSelectedTab(this.router.url);

    // Subscribe to news statistics
    this.statisticsSubscription = this.storeService.newsStatistics$.subscribe((stats) => {
      this.totalNewsCount = stats.totalCount;
      this.todayNewsCount = stats.todayCount;
      this.lastUpdateTime = stats.lastUpdateTime;
    });

    // Load market data
    this.loadMarketData();
  }

  ngOnDestroy() {
    this.statisticsSubscription.unsubscribe();
  }

  private updateSelectedTab(url: string) {
    const segments = url.split('/').filter((segment) => segment);

    if (segments.length === 0) {
      this.selectedTab = 'home';
    } else {
      this.selectedTab = segments[segments.length - 1];
    }
  }

  isActiveRoute(route: string): boolean {
    const isActive = this.selectedTab === route;
    return isActive;
  }

  onNavClick(route: string) {
    this.selectedTab = route;
  }

  onStartDateChange(date: Date): void {
    this.startDate = date;
    this.selectedPreset = 'custom'; // Reset preset when manual date is selected
    this.updateAnalyticsFilters();
  }

  onEndDateChange(date: Date): void {
    this.endDate = date;
    this.selectedPreset = 'custom'; // Reset preset when manual date is selected
    this.updateAnalyticsFilters();
  }

  onStartDateBChange(date: Date): void {
    this.startDateB = date;
    this.selectedPresetB = 'custom'; // Reset preset when manual date is selected
    this.updateAnalyticsFilters();
  }

  onEndDateBChange(date: Date): void {
    this.endDateB = date;
    this.selectedPresetB = 'custom'; // Reset preset when manual date is selected
    this.updateAnalyticsFilters();
  }

  setQuickRange(preset: string): void {
    this.selectedPreset = preset;
    const now = new Date();
    
    switch (preset) {
      case '24h':
        this.startDate = new Date(now.getTime() - 24 * 60 * 60 * 1000);
        this.endDate = new Date(now);
        break;
      case '7d':
        this.startDate = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
        this.endDate = new Date(now);
        break;
      case '30d':
        this.startDate = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
        this.endDate = new Date(now);
        break;
      case '90d':
        this.startDate = new Date(now.getTime() - 90 * 24 * 60 * 60 * 1000);
        this.endDate = new Date(now);
        break;
      default:
        break;
    }
    
    this.updateAnalyticsFilters();
  }

  setQuickRangeB(preset: string): void {
    this.selectedPresetB = preset;
    const now = new Date();
    
    switch (preset) {
      case '24h':
        this.startDateB = new Date(now.getTime() - 48 * 60 * 60 * 1000); // 48h ago
        this.endDateB = new Date(now.getTime() - 24 * 60 * 60 * 1000); // 24h ago
        break;
      case '7d':
        this.startDateB = new Date(now.getTime() - 14 * 24 * 60 * 60 * 1000); // 14 days ago
        this.endDateB = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000); // 7 days ago
        break;
      case '30d':
        this.startDateB = new Date(now.getTime() - 60 * 24 * 60 * 60 * 1000); // 60 days ago
        this.endDateB = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000); // 30 days ago
        break;
      case '90d':
        this.startDateB = new Date(now.getTime() - 180 * 24 * 60 * 60 * 1000); // 180 days ago
        this.endDateB = new Date(now.getTime() - 90 * 24 * 60 * 60 * 1000); // 90 days ago
        break;
      default:
        break;
    }
    
    this.updateAnalyticsFilters();
  }

  private updateAnalyticsFilters(): void {
    const filterData = {
      periodA: {
        startDate: this.startDate,
        endDate: this.endDate,
        preset: this.selectedPreset
      },
      periodB: {
        startDate: this.startDateB,
        endDate: this.endDateB,
        preset: this.selectedPresetB
      },
      timestamp: new Date().getTime()
    };
    
    // Update date range in store service (keeping Period A as primary)
    this.storeService.setDateRange(this.startDate, this.endDate);
    this.storeService.setData('ALL', filterData);
  }

  resetFilters(): void {
    // Reset Period A
    this.startDate = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000);
    this.endDate = new Date();
    this.selectedPreset = '7d';
    
    // Reset Period B
    this.startDateB = new Date(Date.now() - 14 * 24 * 60 * 60 * 1000);
    this.endDateB = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000);
    this.selectedPresetB = '7d';
    
    this.updateAnalyticsFilters();
  }

  getPageTitle(): string {
    const titles: { [key: string]: string } = {
      home: 'Accueil',
      analytics: 'Analytics', 
      'health-check': 'Health Check',
      news: 'News'
    };
    return titles[this.selectedTab] || 'CryptoViz';
  }

  getPageDescription(): string {
    const descriptions: { [key: string]: string } = {
      home: "Bienvenue sur la page d'accueil",
      analytics: 'Analyses détaillées et statistiques',
      'health-check': 'État du système et performances',
      news: 'Actualités crypto et tendances du marché'
    };
    return descriptions[this.selectedTab] || '';
  }

  // News filter methods
  onNewsFilterChange() {
    console.log('News filters changed:', this.newsFilters);
    this.storeService.setNewsFilters(this.newsFilters);
  }

  resetNewsFilters() {
    this.newsFilters = {
      section: 'all',
      dateRange: 'all',
      searchTerm: ''
    };
    this.storeService.setNewsFilters(this.newsFilters);
  }

  refreshNews() {
    console.log('Refreshing news...');
    // This would trigger a refresh of the news data
    // You could emit an event that the news component listens to
  }

  private loadMarketData(): void {
    // Fetch market overview data from API
    this.apiService.getMarketOverview().subscribe({
      next: (data) => {
        this.marketOverview = data;
      },
      error: (error) => {
        console.error('Error loading market data:', error);
        // Fallback to mock data if API fails
        this.marketOverview = {
          bitcoin: {
            symbol: 'BTC',
            name: 'Bitcoin',
            price: 42350,
            change24h: 1035,
            changePercent24h: 2.5
          },
          ethereum: {
            symbol: 'ETH',
            name: 'Ethereum',
            price: 2680,
            change24h: -32.6,
            changePercent24h: -1.2
          },
          totalMarketCap: {
            value: '$1.85T',
            change: 0.8
          }
        };
      }
    });
  }

  formatPrice(price: number): string {
    return new Intl.NumberFormat('en-US', {
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(price);
  }
}
