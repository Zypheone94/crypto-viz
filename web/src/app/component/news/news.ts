import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { HttpClient } from '@angular/common/http';
import { ApiService } from '../../services/api.service';
import { StoreService } from '../../services/store.service';
import { Subscription } from 'rxjs';

interface NewsArticle {
  title: string;
  link: string;
  section: string;
  timestamp: string;
  scraped_at: string;
  content: string;
  has_content: boolean;
}

@Component({
  selector: 'app-news',
  standalone: true,
  imports: [CommonModule, MatCardModule, MatIconModule, MatProgressSpinnerModule],
  templateUrl: './news.html',
  styleUrls: ['./news.css']
})
export class NewsComponent implements OnInit, OnDestroy {
  articles: NewsArticle[] = [];
  isLoading = true;
  private dateRangeSubscription: Subscription = new Subscription();
  private filtersSubscription: Subscription = new Subscription();
  private allArticles: NewsArticle[] = [];

  constructor(
    private http: HttpClient,
    private apiService: ApiService
  ) {}

  ngOnInit() {
    // Load news immediately
    this.loadNews();
  }

  ngOnDestroy() {
    this.dateRangeSubscription.unsubscribe();
    this.filtersSubscription.unsubscribe();
  }

  loadNews() {
    console.log('Loading news from assets...');
    this.isLoading = true;
    
    // Load directly from assets since API can't access the data folder
    this.loadFromAssets();
  }

  private loadFromAssets() {
    // Fallback to load from assets using HttpClient
    console.log('Loading news from assets/data/news.json...');
    this.http.get<NewsArticle[]>('assets/data/news.json').subscribe({
      next: (articles) => {
        if (Array.isArray(articles)) {
          // Filter articles with content
          const articlesWithContent = articles.filter(article => article.has_content);
          
          console.log('News data loaded from assets:', articlesWithContent.length, 'articles');
          this.allArticles = articlesWithContent;
          this.articles = this.allArticles;
          
          // Show all articles for now
          this.articles = this.allArticles;
        } else {
          console.error('Invalid news data format in assets');
          this.articles = [];
          this.allArticles = [];
        }
        this.isLoading = false;
      },
      error: (error) => {
        console.error('Error loading news from assets:', error);
        this.articles = [];
        this.allArticles = [];
        this.isLoading = false;
      }
    });
  }

  private updateStatistics() {
    // Simplified statistics for now
    console.log(`Loaded ${this.articles.length} articles`);
  }

  private applyFilters(filters: any) {
    let filteredArticles = [...this.allArticles];

    // Section filter
    if (filters.section !== 'all') {
      filteredArticles = filteredArticles.filter(article => article.section === filters.section);
    }

    // Date range filter
    if (filters.dateRange !== 'all') {
      const now = new Date();
      let startDate = new Date();

      switch (filters.dateRange) {
        case 'today':
          startDate.setHours(0, 0, 0, 0);
          break;
        case 'week':
          startDate.setDate(now.getDate() - 7);
          break;
        case 'month':
          startDate.setMonth(now.getMonth() - 1);
          break;
      }

      filteredArticles = filteredArticles.filter(article => {
        const articleDate = new Date(article.scraped_at || article.timestamp);
        return articleDate >= startDate;
      });
    }

    // Search term filter
    if (filters.searchTerm.trim()) {
      const searchTerm = filters.searchTerm.toLowerCase();
      filteredArticles = filteredArticles.filter(article => 
        article.title.toLowerCase().includes(searchTerm) ||
        article.content.toLowerCase().includes(searchTerm)
      );
    }

    this.articles = filteredArticles;
    this.updateStatistics();
  }

  private filterArticlesByDateRange(startDate: Date, endDate: Date): void {
    console.log('Filtering articles by date range:', startDate, 'to', endDate);
    
    if (!this.allArticles || this.allArticles.length === 0) {
      console.warn('No articles to filter');
      return;
    }
    
    this.articles = this.allArticles.filter(article => {
      try {
        // Parse the article timestamp - try scraped_at first, then timestamp
        const timestampStr = article.scraped_at || article.timestamp;
        if (!timestampStr) {
          console.warn('Article has no timestamp:', article.title);
          return true; // Include articles without timestamps
        }
        
        const articleDate = new Date(timestampStr);
        
        // Check if the date is valid
        if (isNaN(articleDate.getTime())) {
          console.warn('Invalid date for article:', article.title, timestampStr);
          return true; // Include articles with invalid dates
        }
        
        // Extend end date to end of day to be more inclusive
        const endOfDay = new Date(endDate);
        endOfDay.setHours(23, 59, 59, 999);
        
        const isInRange = articleDate >= startDate && articleDate <= endOfDay;
        
        if (!isInRange) {
          console.log('Article filtered out:', article.title, 'Date:', articleDate);
        }
        
        return isInRange;
      } catch (error) {
        console.error('Error filtering article:', article.title, error);
        return true; // Include articles that cause errors
      }
    });
    
    console.log('Filtered results:', this.articles.length, 'out of', this.allArticles.length, 'articles');
  }

  formatDate(timestamp: string): string {
    const date = new Date(timestamp);
    return date.toLocaleDateString('fr-FR', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  }

  getSectionIcon(section: string): string {
    switch (section) {
      case 'latest-crypto-news':
        return 'newspaper';
      case 'markets':
        return 'trending_up';
      case 'business':
        return 'business_center';
      default:
        return 'article';
    }
  }

  getSectionColor(section: string): string {
    switch (section) {
      case 'latest-crypto-news':
        return '#2196F3';
      case 'markets':
        return '#4CAF50';
      case 'business':
        return '#FF9800';
      default:
        return '#9E9E9E';
    }
  }

  truncateContent(content: string, maxLength: number = 150): string {
    if (content.length <= maxLength) return content;
    return content.substring(0, maxLength) + '...';
  }
}