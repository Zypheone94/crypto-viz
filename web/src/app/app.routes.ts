import { Routes } from '@angular/router';
import { Home } from './home/home';
import { Analytics } from './analytics/analytics';

export const routes: Routes = [
    {path: "", redirectTo: "/home", pathMatch: "full"},
    {path: "home", component: Home, title: "Crypto-Viz"},
    {path: "analytics", component: Analytics, title: "Analytics"},
    {path: "**", redirectTo: "/home", pathMatch: "full"}
];
