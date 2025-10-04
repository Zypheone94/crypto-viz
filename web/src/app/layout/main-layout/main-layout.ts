import { Component, OnInit } from '@angular/core';
import { Router, NavigationEnd } from '@angular/router';
import { filter } from 'rxjs/operators';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { StoreService } from '../../services/store.service';

@Component({
  selector: 'app-main-layout',
  standalone: true,
  imports: [CommonModule, RouterModule, FormsModule],
  templateUrl: './main-layout.html',
  styleUrls: ['./main-layout.css'],
})
export class MainLayoutComponent implements OnInit {
  selectedTab: string = 'home';

  navItems = [
    { route: 'home', icon: '🏠', label: 'Accueil' },
    { route: 'analytics', icon: '📊', label: 'Analytics' },
    { route: 'health-check', icon: '🔍', label: 'Health Check' },
  ];

  filterValues = {
    from: '',
    to: '',
    bucket: '',
  };

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

  substractTime(date: Date, value: number, unit: 'hour' | 'day'): string {
    const msPerHour = 60 * 60 * 1000;
    const msPerDay = 24 * msPerHour;

    const ms = unit === 'hour' ? value * msPerHour : value * msPerDay;
    return new Date(date.getTime() - ms).toISOString();
  }

  updateFilter(value: any) {
    const now = new Date();

    const periods: Record<string, { value: number; unit: 'hour' | 'day' }> = {
      '1h': { value: 1, unit: 'hour' },
      '1d': { value: 1, unit: 'day' },
      '3d': { value: 3, unit: 'day' },
    };

    const period = periods[value];
    if (period) {
      this.filterValues.from = this.substractTime(now, period.value, period.unit);
      this.filterValues.to = now.toISOString();
      this.filterValues.bucket = period.unit;
    }

    this.sendData(this.filterValues);
  }

  resetFilters() {
    this.filterValues = {
      from: '',
      to: '',
      bucket: '',
    };
  }

  getPageTitle(): string {
    const titles: { [key: string]: string } = {
      home: 'Accueil',
      analytics: 'Analytics',
      'health-check': 'Health Check',
    };
    return titles[this.selectedTab] || 'Mon App';
  }

  getPageDescription(): string {
    const descriptions: { [key: string]: string } = {
      home: "Bienvenue sur la page d'accueil",
      analytics: 'Analyses détaillées et statistiques',
      'health-check': 'État du système et performances',
    };
    return descriptions[this.selectedTab] || '';
  }

  sendData(data: any) {
    this.storeService.setData(data);
  }
}
