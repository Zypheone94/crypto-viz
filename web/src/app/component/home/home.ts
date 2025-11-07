import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatIconModule } from '@angular/material/icon';
import { MatCardModule } from '@angular/material/card';
import { RouterModule } from '@angular/router';

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
  imports: [CommonModule, MatIconModule, MatCardModule, RouterModule],
  templateUrl: './home.html',
  styleUrl: './home.css'
})
export class Home implements OnInit {
  
  dashboardStats: DashboardStat[] = [];

  ngOnInit(): void {
    this.loadDashboardStats();
  }

  private loadDashboardStats(): void {
    // Simulate loading dashboard statistics
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
      },
      {
        title: 'Analyses Temps Réel',
        value: '24/7',
        icon: 'analytics',
        color: '#f59e0b',
        description: 'Surveillance continue du marché',
        trend: 'Actif'
      },
      {
        title: 'Tendances Détectées',
        value: '8',
        icon: 'trending_up',
        color: '#ef4444',
        description: 'Signaux importants détectés',
        trend: 'Dernières 6h'
      },
      {
        title: 'Volume Données',
        value: '2.3TB',
        icon: 'storage',
        color: '#8b5cf6',
        description: 'Données historiques stockées',
        trend: '+156GB cette semaine'
      },
      {
        title: 'Uptime Système',
        value: '99.8%',
        icon: 'health_and_safety',
        color: '#06b6d4',
        description: 'Disponibilité des services',
        trend: '30 derniers jours'
      }
    ];
  }
}
