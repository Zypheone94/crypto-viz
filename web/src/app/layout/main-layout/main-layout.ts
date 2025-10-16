import { Component, OnInit } from '@angular/core';
import { Router, NavigationEnd } from '@angular/router';
import { filter } from 'rxjs/operators';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { StoreService } from '../../services/store.service';
import { MatExpansionModule } from '@angular/material/expansion';

type PeriodKey = 'A' | 'B';

interface Period {
  key: PeriodKey;
  label: string;
}

@Component({
  selector: 'app-main-layout',
  standalone: true,
  imports: [MatExpansionModule, CommonModule, RouterModule, FormsModule],
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

  periods: Period[] = [
    { key: 'A', label: 'Période A' },
    { key: 'B', label: 'Période B' },
  ];

  displayCustomFields: Record<PeriodKey, boolean> = {
    A: false,
    B: false,
  };

  filterValues: Record<PeriodKey, { from: string; to: string; bucket: string }> = {
    A: { from: '', to: '', bucket: '' },
    B: { from: '', to: '', bucket: '' },
  };

  customDateValues: Record<PeriodKey, { from: string; to: string }> = {
    A: { from: '', to: '' },
    B: { from: '', to: '' },
  };

  private lastCustomFilterKey = '';
  displayCustomFieldsA: boolean = false;
  displayCustomFieldsB: boolean = false;

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

  updateFilter(periode: PeriodKey, value: any) {
    const now = new Date();

    this.displayCustomFields[periode] = false;

    if (periode === 'A') {
      this.displayCustomFieldsA = false;
    } else if (periode === 'B') {
      this.displayCustomFieldsB = false;
    }
    // Réinitialiser seulement les dates de la période concernée
    this.customDateValues[periode] = { from: '', to: '' };

    const periods: Record<string, { value: number; unit: 'hour' | 'day' }> = {
      '1h': { value: 1, unit: 'hour' },
      '1d': { value: 1, unit: 'day' },
      '3d': { value: 3, unit: 'day' },
    };

    const period = periods[value];
    if (period) {
      const filter = this.filterValues[periode];
      filter.from = this.substractTime(now, period.value, period.unit);
      filter.to = now.toISOString();
      filter.bucket = period.unit;

      this.sendData(periode, filter);
    }
  }

  updateCustomFilter(periode: PeriodKey) {
    if (this.customDateValues[periode].from && this.customDateValues[periode].to) {
      const filterKey = `${this.customDateValues[periode].from}|${this.customDateValues[periode].to}`;

      if (this.lastCustomFilterKey === filterKey) {
        console.log('⏭️ Même filtre, skip');
        return;
      }

      const filter = this.filterValues[periode];
      filter.from = new Date(this.customDateValues[periode].from).toISOString();
      filter.to = new Date(this.customDateValues[periode].to).toISOString();
      filter.bucket = 'day'; // Default set to day because you choose two dates
      this.sendData(periode, filter);
    }
  }

  resetFilters() {
    this.filterValues = {
      A: { from: '', to: '', bucket: '' },
      B: { from: '', to: '', bucket: '' },
    };
    this.sendData('ALL', null);
  }

  handleDisplayCustomFields(period: PeriodKey) {
    this.displayCustomFields[period] = !this.displayCustomFields[period];
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

  sendData(periode: 'A' | 'B' | 'ALL', data: any) {
    this.storeService.setData(periode, data);
  }
}
