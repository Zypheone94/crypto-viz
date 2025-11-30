// Updated - 11/16/2025 21:16:52
import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatIconModule } from '@angular/material/icon';
import { MatCardModule } from '@angular/material/card';
import { RouterModule } from '@angular/router';
import { ApiService } from '../../services/api.service';

interface FeatureTag {
  icon: string;
  label: string;
  value: string;
}

interface StatCard {
  title: string;
  value: string;
  description: string;
  trend?: string;
  trendValue?: number;
  icon: string;
  accent: string;
  iconBg: string;
}

interface MarketMovement {
  symbol: string;
  name: string;
  price: string;
  changeLabel: string;
  changeValue: number;
}

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [CommonModule, MatIconModule, MatCardModule, RouterModule],
  templateUrl: './home.html',
  styleUrl: './home.css'
})
export class Home implements OnInit {
  featureTags: FeatureTag[] = [];
  statCards: StatCard[] = [];
  topGainers: MarketMovement[] = [];
  topLosers: MarketMovement[] = [];
  isOverviewLoading = true;
  isMoversLoading = true;
  overviewError = '';
  moversError = '';
  dataTimestamp = '';

  quickActions = [
    { route: '/analytics', icon: 'leaderboard', title: 'Explorer les métriques', description: 'Visualisez les séries temporelles, tendances et RSI' },
    { route: '/health-check', icon: 'health_and_safety', title: 'État du pipeline', description: 'Surveillez l\'ingestion et les jobs programmés' }
    // News removed - not needed
  ];

  constructor(private apiService: ApiService) {}

  ngOnInit(): void {
    this.loadHomeData();
  }

  loadHomeData(): void {
    this.isOverviewLoading = true;
    this.isMoversLoading = true;
    this.overviewError = '';
    this.moversError = '';

    console.log('🔄 Loading home dashboard data...');
    const startTime = performance.now();

    this.apiService.getHomeDashboard(5).subscribe({
      next: (dashboard) => {
        const loadTime = performance.now() - startTime;
        console.log(`✅ Home dashboard loaded in ${loadTime.toFixed(0)}ms`);

        if (!dashboard) {
          this.overviewError = 'Aucune donnée disponible.';
          this.moversError = 'Aucune donnée disponible.';
          this.isOverviewLoading = false;
          this.isMoversLoading = false;
          return;
        }

        const overviewData = dashboard.overview || {};
        const statsData = dashboard.stats || {};

        this.featureTags = this.buildFeatureTags(overviewData, statsData);
        this.statCards = this.buildStatCards(statsData);
        this.dataTimestamp = overviewData.last_updated || statsData.last_updated || dashboard.metadata?.generated_at || '';

        this.topGainers = this.mapMovements(dashboard.gainers);
        this.topLosers = this.mapMovements(dashboard.losers);

        if (!this.topGainers.length) {
          this.moversError = 'Aucun gainer disponible pour l\'instant.';
        }
        if (!this.topLosers.length) {
          this.moversError = this.moversError || 'Aucun loser disponible pour l\'instant.';
        }

        this.isOverviewLoading = false;
        this.isMoversLoading = false;
      },
      error: (error) => {
        const loadTime = performance.now() - startTime;
        console.error(`❌ Home dashboard failed after ${loadTime.toFixed(0)}ms`, error);
        
        // Provide more specific error messages
        if (error.status === 0) {
          this.overviewError = 'Impossible de se connecter au serveur. Vérifiez votre connexion.';
          this.moversError = 'Impossible de se connecter au serveur.';
        } else if (error.status >= 500) {
          this.overviewError = 'Erreur serveur. Les services sont peut-être en cours de démarrage...';
          this.moversError = 'Erreur serveur. Réessayez dans quelques instants.';
        } else {
        this.overviewError = 'Impossible de charger les données du tableau de bord.';
        this.moversError = 'Impossible de charger les variations du marché.';
        }
        
        this.isOverviewLoading = false;
        this.isMoversLoading = false;
      }
    });
  }

  private buildFeatureTags(overviewData: any, statsData: any): FeatureTag[] {
    return [
      {
        icon: 'paid',
        label: 'Capitalisation totale',
        value: overviewData?.total_market_cap || '--'
      },
      {
        icon: 'trending_up',
        label: 'Variation 24h',
        value: overviewData?.market_cap_change || '--'
      },
      {
        icon: 'article',
        label: 'Articles collectés aujourd’hui',
        value: statsData?.daily_articles?.count?.toString() || '--'
      },
      {
        icon: 'library_books',
        label: 'Articles cumulés',
        value: statsData?.totals?.articles?.toLocaleString('fr-FR') || '--'
      },
      {
        icon: 'token',
        label: 'Symboles suivis',
        value: statsData?.totals?.symbols?.toLocaleString('fr-FR') || '--'
      }
    ].filter((tag) => tag.value !== '--');
  }

  private buildStatCards(statsData: any): StatCard[] {
    const cards: StatCard[] = [];

    if (statsData?.totals?.articles !== undefined) {
      cards.push({
        title: 'Articles (total pipeline)',
        value: statsData.totals.articles.toLocaleString('fr-FR'),
        description: 'Nombre d’articles agrégés',
        trend: '',
        trendValue: 0,
        icon: 'library_books',
        accent: '#4ade80',
        iconBg: 'rgba(74, 222, 128, 0.15)'
      });
    }

    if (statsData?.totals?.symbols !== undefined) {
      cards.push({
        title: 'Symboles suivis',
        value: statsData.totals.symbols.toLocaleString('fr-FR'),
        description: 'Univers d’actifs détectés',
        trend: '',
        trendValue: 0,
        icon: 'token',
        accent: '#facc15',
        iconBg: 'rgba(250, 204, 21, 0.15)'
      });
    }

    if (statsData?.daily_articles) {
      cards.push({
        title: 'Articles collectés aujourd’hui',
        value: statsData.daily_articles.count?.toString() || '0',
        description: 'Activité du pipeline d’actualités',
        trend: statsData.daily_articles.change_yesterday || '',
        trendValue: statsData.daily_articles.change_yesterday_value || 0,
        icon: 'feed',
        accent: '#3b82f6',
        iconBg: 'rgba(59, 130, 246, 0.15)'
      });
    }

    if (statsData?.crypto_sources) {
      cards.push({
        title: 'Sources surveillées',
        value: statsData.crypto_sources.count?.toString() || '0',
        description: statsData.crypto_sources.description || 'Flux suivis',
        trend: statsData.crypto_sources.change_month || '',
        trendValue: Number((statsData.crypto_sources.change_month || '0').replace('+', '')) || 0,
        icon: 'hub',
        accent: '#f97316',
        iconBg: 'rgba(249, 115, 22, 0.15)'
      });
    }

    return cards;
  }

  private mapMovements(items: any[] = []): MarketMovement[] {
    if (!Array.isArray(items)) {
      return [];
    }

    return items.map((item: any) => {
      const changeValue = Number(item.change_24h_value ?? item.changePercent24h ?? 0);
      return {
        symbol: item.symbol,
        name: item.name || item.symbol,
        price: item.price || this.formatPrice(item.current_price),
        changeLabel: item.change_24h || this.formatPercent(changeValue),
        changeValue
      };
    });
  }

  private formatPrice(value: number | string | undefined): string {
    if (typeof value === 'string' && value.trim().length > 0) {
      return value;
    }
    const num = Number(value ?? 0);
    if (!Number.isFinite(num)) {
      return '$0.00';
    }
    return num >= 1 ? `$${num.toFixed(2)}` : `$${num.toFixed(4)}`;
  }

  private formatPercent(value: number): string {
    if (!Number.isFinite(value)) {
      return '0%';
    }
    const formatted = value >= 0 ? `+${value.toFixed(2)}%` : `${value.toFixed(2)}%`;
    return formatted;
  }
}
