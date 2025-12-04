import { Routes } from '@angular/router';
import { Home } from './component/home/home';
import { Analytics } from './component/analytics/analytics';
import { HealthCheck } from './component/health-check/health-check';
import { NewsComponent } from './component/news/news';
import { MainLayoutComponent } from './layout/main-layout/main-layout';
import { Correlation } from './component/correlation/correlation';

export const routes: Routes = [
  {
    path: '',
    component: MainLayoutComponent,
    children: [
      { path: '', redirectTo: 'home', pathMatch: 'full' }, // Redirection par défaut
      { path: 'home', component: Home, title: 'Home' },
      { path: 'analytics', component: Analytics, title: 'Analytics' },
      { path: 'health-check', component: HealthCheck, title: 'Health Check' },
      { path: 'news', component: NewsComponent, title: 'News' },
      { path: 'correlation', component: Correlation, title: 'Correlation' },
    ],
  },
  { path: '**', redirectTo: '', pathMatch: 'full' }, // Redirection vers la racine
];
