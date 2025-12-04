import { Component, OnInit, OnDestroy } from '@angular/core';
import { Router, NavigationEnd } from '@angular/router';
import { filter } from 'rxjs/operators';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { StoreService } from '../../services/store.service';
import { ThemeService } from '../../services/theme.service';
import type { NewsStatistics, NewsFilters } from '../../services/store.service';
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
import { MatTooltipModule } from '@angular/material/tooltip';

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
    MatSlideToggleModule,
    MatTooltipModule
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
    // { route: 'news', icon: 'newspaper', label: 'News' }, // Removed
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

  // Market data - will be loaded from backend
  marketOverview: MarketOverview = {
    bitcoin: {
      symbol: 'BTC',
      name: 'Bitcoin',
      price: 0,
      change24h: 0,
      changePercent24h: 0
    },
    ethereum: {
      symbol: 'ETH',
      name: 'Ethereum',
      price: 0,
      change24h: 0,
      changePercent24h: 0
    },
    totalMarketCap: {
      value: '$0.00T',
      change: 0
    }
  };

  constructor(
    private router: Router,
    private storeService: StoreService,
    private apiService: ApiService,
    public themeService: ThemeService
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
    this.statisticsSubscription = this.storeService.newsStatistics$.subscribe((stats: NewsStatistics) => {
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
      next: (data: any) => {
        if (data) {
          const cryptos = data.major_cryptos || [];
          
          const btcData = cryptos.find((crypto: any) => crypto.symbol === 'BTC');
          const ethData = cryptos.find((crypto: any) => crypto.symbol === 'ETH');
          
          this.marketOverview = {
            bitcoin: {
              symbol: btcData?.symbol || 'BTC',
              name: btcData?.name || 'Bitcoin',
              price: btcData ? parseFloat(String(btcData.price).replace(/[$,]/g, '')) : 0,
              change24h: btcData?.change_24h_value || 0,
              changePercent24h: btcData?.change_24h_value || 0
            },
            ethereum: {
              symbol: ethData?.symbol || 'ETH',
              name: ethData?.name || 'Ethereum',
              price: ethData ? parseFloat(String(ethData.price).replace(/[$,]/g, '')) : 0,
              change24h: ethData?.change_24h_value || 0,
              changePercent24h: ethData?.change_24h_value || 0
            },
            totalMarketCap: {
              value: data.total_market_cap || '$0.00T',
              change: data.market_cap_change_value || 0
            }
          };
        } else {
          this.marketOverview = this.getEmptyMarketOverview();
        }
      },
      error: (error: any) => {
        console.error('Error loading market data:', error);
        this.marketOverview = this.getEmptyMarketOverview();
      }
    });
  }

  private getEmptyMarketOverview(): MarketOverview {
    return {
      bitcoin: {
        symbol: 'BTC',
        name: 'Bitcoin',
        price: 0,
        change24h: 0,
        changePercent24h: 0
      },
      ethereum: {
        symbol: 'ETH',
        name: 'Ethereum',
        price: 0,
        change24h: 0,
        changePercent24h: 0
      },
      totalMarketCap: {
        value: '$0.00T',
        change: 0
      }
    };
  }

  formatPrice(price: number): string {
    return new Intl.NumberFormat('en-US', {
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(price);
  }

  toggleTheme(): void {
    this.themeService.toggleTheme();
  }

  getThemeIcon(): string {
    return this.themeService.getThemeIcon();
  }

  getThemeLabel(): string {
    return this.themeService.getThemeLabel();
  }
}