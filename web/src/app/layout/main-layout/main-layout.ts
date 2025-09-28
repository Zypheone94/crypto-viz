import { Component, OnInit } from '@angular/core';
import { Router, NavigationEnd } from '@angular/router';
import { filter } from 'rxjs/operators';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { FormsModule } from '@angular/forms';

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

  constructor(private router: Router) {}

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
  }

  private updateSelectedTab(url: string) {
    console.log('🔍 URL reçue pour mise à jour:', url);

    const segments = url.split('/').filter((segment) => segment);
    console.log('🔍 Segments extraits:', segments);

    if (segments.length === 0) {
      this.selectedTab = 'home';
    } else {
      this.selectedTab = segments[segments.length - 1];
    }

    console.log('✅ Selected tab mis à jour:', this.selectedTab);
  }

  isActiveRoute(route: string): boolean {
    const isActive = this.selectedTab === route;
    console.log(`🔍 Route ${route} active?`, isActive, '(selectedTab:', this.selectedTab, ')');
    return isActive;
  }

  onNavClick(route: string) {
    console.log('👆 Clic sur navigation:', route);
    this.selectedTab = route;
  }

  updateFilter(filterName: string, value: any) {
    (this.filterValues as any)[filterName] = value;
    console.log('🎛️ Filtre mis à jour:', filterName, value);
  }

  resetFilters() {
    this.filterValues = {
      dateRange: 'last-7-days',
      startDate: '',
      endDate: '',
      category: 'all',
    };
    console.log('🔄 Filtres réinitialisés');
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
}
