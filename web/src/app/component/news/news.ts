import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatChipsModule } from '@angular/material/chips';
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
  imports: [CommonModule, FormsModule, MatCardModule, MatIconModule, MatProgressSpinnerModule, MatSelectModule, MatFormFieldModule, MatInputModule, MatButtonModule, MatChipsModule],
  templateUrl: './news.html',
  styleUrls: ['./news.css']
})
export class NewsComponent implements OnInit, OnDestroy {
  articles: NewsArticle[] = [];
  isLoading = true;
  private dateRangeSubscription: Subscription = new Subscription();
  private filtersSubscription: Subscription = new Subscription();
  private allArticles: NewsArticle[] = [];
  
  // Filter properties
  availableSections: string[] = [];
  currentFilters = {
    section: 'all',
    dateRange: 'all',
    searchTerm: ''
  };

  constructor(
    private http: HttpClient,
    private apiService: ApiService,
    private storeService: StoreService
  ) {}

  ngOnInit() {
    // Load news immediately
    this.loadNews();
    
    // Subscribe to filter changes
    this.filtersSubscription = this.storeService.newsFilters$.subscribe(filters => {
      if (this.allArticles.length > 0) {
        this.applyFilters(filters);
      }
    });
    
    // Subscribe to date range changes
    this.dateRangeSubscription = this.storeService.dateRange$.subscribe(dateRange => {
      if (this.allArticles.length > 0 && dateRange.startDate && dateRange.endDate) {
        this.filterArticlesByDateRange(dateRange.startDate, dateRange.endDate);
      }
    });
  }

  ngOnDestroy() {
    this.dateRangeSubscription.unsubscribe();
    this.filtersSubscription.unsubscribe();
  }

  loadNews() {
    console.log('Loading news from API...');
    this.isLoading = true;
    
    // Load news from API endpoint
    this.loadFromAPI();
  }

  private loadFromAPI() {
    console.log('Loading news from API endpoint...');
    this.apiService.getNews(50).subscribe({
      next: (response: any) => {
        if (response && response.response && Array.isArray(response.response.articles)) {
          const articles = response.response.articles;
          
          console.log('News data loaded from API:', articles.length, 'articles');
          this.allArticles = articles;
          this.articles = this.allArticles;
          this.extractAvailableSections();
          this.updateStatistics();
          
          // Apply current filters if any
          const currentFilters = this.storeService.getNewsFilters();
          this.currentFilters = { ...currentFilters };
          if (currentFilters.section !== 'all' || currentFilters.dateRange !== 'all' || currentFilters.searchTerm) {
            this.applyFilters(currentFilters);
          }
        } else {
          console.error('Invalid news data format from API:', response);
          this.articles = [];
          this.allArticles = [];
        }
        this.isLoading = false;
      },
      error: (error: any) => {
        console.error('Error loading news from API:', error);
        this.articles = [];
        this.allArticles = [];
        this.isLoading = false;
      }
    });
  }

  private updateStatistics() {
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    
    const todayCount = this.articles.filter(article => {
      const articleDate = new Date(article.scraped_at || article.timestamp);
      return articleDate >= today;
    }).length;
    
    const statistics = {
      totalCount: this.articles.length,
      todayCount: todayCount,
      lastUpdateTime: now.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })
    };
    
    this.storeService.setNewsStatistics(statistics);
    console.log(`Updated statistics: ${statistics.totalCount} total, ${statistics.todayCount} today`);
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
    switch (section.toLowerCase()) {
      case 'latest-crypto-news':
        return 'newspaper';
      case 'markets':
        return 'trending_up';
      case 'business':
        return 'business_center';
      case 'coindesk':
        return 'article';
      case 'crypto':
        return 'currency_bitcoin';
      default:
        return 'article';
    }
  }

  getSectionColor(section: string): string {
    switch (section.toLowerCase()) {
      case 'latest-crypto-news':
        return '#2196F3';
      case 'markets':
        return '#4CAF50';
      case 'business':
        return '#FF9800';
      case 'coindesk':
        return '#9C27B0';
      case 'crypto':
        return '#FF5722';
      default:
        return '#9E9E9E';
    }
  }

  truncateContent(content: string, maxLength: number = 150): string {
    if (content.length <= maxLength) return content;
    return content.substring(0, maxLength) + '...';
  }
  
  // Filter methods
  onSectionFilterChange(section: string) {
    this.currentFilters.section = section;
    this.storeService.setNewsFilters(this.currentFilters);
  }
  
  onDateRangeFilterChange(dateRange: string) {
    this.currentFilters.dateRange = dateRange;
    this.storeService.setNewsFilters(this.currentFilters);
  }
  
  onSearchTermChange(searchTerm: string) {
    this.currentFilters.searchTerm = searchTerm;
    this.storeService.setNewsFilters(this.currentFilters);
  }
  
  clearFilters() {
    this.currentFilters = {
      section: 'all',
      dateRange: 'all',
      searchTerm: ''
    };
    this.storeService.setNewsFilters(this.currentFilters);
  }
  
  private extractAvailableSections() {
    const sections = [...new Set(this.allArticles.map(article => article.section))];
    this.availableSections = sections.sort();
  }
}