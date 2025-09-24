import { Routes } from '@angular/router';
import { Home } from './home/home';
import { Analytics } from './analytics/analytics';
import { HealthCheck } from './health-check/health-check';

export const routes: Routes = [
    {path: "", redirectTo: "/home", pathMatch: "full"},
    {path: "home", component: Home, title: "Crypto-Viz"},
    {path: "analytics", component: Analytics, title: "Analytics"},
    {path: "health-check", component: HealthCheck, title: "Health Check"},
    {path: "**", redirectTo: "/home", pathMatch: "full"}
];
