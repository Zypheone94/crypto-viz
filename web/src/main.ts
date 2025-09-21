import { bootstrapApplication } from '@angular/platform-browser';
import 'zone.js'
import { App } from './app/app';
import { Home } from './app/home/home';
import { Analytics } from './app/analytics/analytics';
import { provideRouter, Routes } from '@angular/router';

  const routes: Routes = [
    { path: "", redirectTo: "/home", pathMatch: 'full' },
    { path: "home", component: Home, title: "Crypto-Viz"},
    { path: "analytics", component: Analytics, title: "Analytics"},
    { path: "**", redirectTo: "/home", pathMatch: 'full'}
  ];

bootstrapApplication(App, {
  providers: [provideRouter(routes)]
})