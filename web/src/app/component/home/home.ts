import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatIconModule } from '@angular/material/icon';
import { MatCardModule } from '@angular/material/card';
import { RouterModule } from '@angular/router';
import { TopGainersComponent } from '../analytics/components/top-gainers';
import { TopLosersComponent } from '../analytics/components/top-losers';

interface DashboardStat {
  title: string;
  value: string;
  icon: string;
  color: string;
  description: string;
  trend?: string;
}

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [CommonModule, MatIconModule, MatCardModule, RouterModule, TopGainersComponent, TopLosersComponent],
  templateUrl: './home.html',
  styleUrl: './home.css'
})
export class Home implements OnInit {
  
  dashboardStats: DashboardStat[] = [];

  ngOnInit(): void {
    this.loadDashboardStats();
  }

  private loadDashboardStats(): void {
    // Load only basic dashboard statistics
    this.dashboardStats = [
      {
        title: 'Sources Crypto',
        value: '12',
        icon: 'business',
        color: '#3b82f6',
        description: 'Plateformes et médias surveillés',
        trend: '+2 ce mois'
      },
      {
        title: 'Articles Quotidiens',
        value: '157',
        icon: 'article',
        color: '#10b981',
        description: 'Nouvelles collectées aujourd\'hui',
        trend: '+23% vs hier'
      }
    ];
  }
}
