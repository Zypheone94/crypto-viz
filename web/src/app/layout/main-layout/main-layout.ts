import { Component, OnInit } from '@angular/core';
import { Router, NavigationEnd } from '@angular/router';
import { filter } from 'rxjs/operators';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { StoreService } from '../../services/store.service';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MatInputModule } from '@angular/material/input';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatNativeDateModule } from '@angular/material/core';
import { MatIconModule } from '@angular/material/icon';
import { MatSelectModule } from '@angular/material/select';
import { MatButtonModule } from '@angular/material/button';

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
    MatButtonModule
  ],
  templateUrl: './main-layout.html',
  styleUrls: ['./main-layout.css'],
})
export class MainLayoutComponent implements OnInit {
  selectedTab: string = 'home';

  navItems = [
    { route: 'home', icon: 'home', label: 'Accueil' },
    { route: 'analytics', icon: 'analytics', label: 'Analytics' },
    { route: 'health-check', icon: 'health_and_safety', label: 'Health Check' },
    { route: 'news', icon: 'newspaper', label: 'News' },
  ];

  // Simplified filter system with single date picker and time range
  selectedDate: Date = new Date();
  selectedTimeRange: string = '24h';
  
  timeRanges = [
    { value: '1h', label: 'Dernière heure' },
    { value: '24h', label: 'Dernier jour' },
    { value: '7d', label: 'Dernière semaine' },
    { value: '30d', label: 'Dernier mois' }
  ];

  constructor(
    private router: Router,
    private storeService: StoreService,
  ) {}

  ngOnInit() {
    // Écouter les changements de route
    this.router.events
      .pipe(filter((event) => event instanceof NavigationEnd))
      .subscribe((event: NavigationEnd) => {
        this.updateSelectedTab(event.url);
      });

    this.updateSelectedTab(this.router.url);
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

  onDateChange(date: Date): void {
    this.selectedDate = date;
    this.updateAnalyticsFilters();
  }

  onTimeRangeChange(range: string): void {
    this.selectedTimeRange = range;
    this.updateAnalyticsFilters();
  }

  private updateAnalyticsFilters(): void {
    const filterData = {
      date: this.selectedDate,
      timeRange: this.selectedTimeRange,
      timestamp: new Date().getTime()
    };
    
    this.storeService.setData('ALL', filterData);
  }

  resetFilters(): void {
    this.selectedDate = new Date();
    this.selectedTimeRange = '24h';
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
}
