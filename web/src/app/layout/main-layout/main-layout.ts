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
    dateRange: 'last-7-days',
    startDate: '',
    endDate: '',
    category: 'all',
  };

  constructor(
    private router: Router,
    private storeService: StoreService,
  ) {}

  ngOnInit() {
    console.log('🔍 URL au démarrage:', this.router.url);

    // Écouter les changements de route
    this.router.events
      .pipe(filter((event) => event instanceof NavigationEnd))
      .subscribe((event: NavigationEnd) => {
        console.log('🔍 Navigation détectée:', event.url);
        this.updateSelectedTab(event.url);
      });

    this.updateSelectedTab(this.router.url);
    this.sendData();
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

  updateFilter(filterName: string, value: any) {
    (this.filterValues as any)[filterName] = value;
  }

  resetFilters() {
    this.filterValues = {
      dateRange: 'last-7-days',
      startDate: '',
      endDate: '',
      category: 'all',
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

  sendData() {
    this.storeService.setData('Hello from MainLayoutComponent');
  }
}
