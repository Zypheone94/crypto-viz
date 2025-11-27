import { Injectable } from '@angular/core';
import { BehaviorSubject, combineLatest, Observable } from 'rxjs';

export interface DateRange {
  startDate: Date | null;
  endDate: Date | null;
}

export interface NewsStatistics {
  totalCount: number;
  todayCount: number;
  lastUpdateTime: string;
}

export interface NewsFilters {
  section: string;
  dateRange: string;
  searchTerm: string;
}

export interface NewsStatistics {
  totalCount: number;
  todayCount: number;
  lastUpdateTime: string;
}

export interface NewsFilters {
  section: string;
  dateRange: string;
  searchTerm: string;
}

@Injectable({
  providedIn: 'root',
})
export class StoreService {
  private dataA = new BehaviorSubject<any>(null);
  private dataB = new BehaviorSubject<any>(null);
  
  // Date range management
  private dateRange = new BehaviorSubject<DateRange>({
    startDate: null,
    endDate: null
  });

  // News statistics management
  private newsStatistics = new BehaviorSubject<NewsStatistics>({
    totalCount: 0,
    todayCount: 0,
    lastUpdateTime: '--:--'
  });

  // News filters management
  private newsFilters = new BehaviorSubject<NewsFilters>({
    section: 'all',
    dateRange: 'all',
    searchTerm: ''
  });

  combined$ = combineLatest([this.dataA, this.dataB]);
  dateRange$ = this.dateRange.asObservable();
  newsStatistics$ = this.newsStatistics.asObservable();
  newsFilters$ = this.newsFilters.asObservable();

  setData(periode: 'A' | 'B' | 'ALL', data: any) {
    if (periode === 'A') {
      this.dataA.next(data);
    } else if (periode === 'B') {
      this.dataB.next(data);
    } else if (periode === 'ALL') {
      this.dataA.next(null);
      this.dataB.next(null);
    }
  }

  setDateRange(startDate: Date | null, endDate: Date | null) {
    this.dateRange.next({ startDate, endDate });
  }

  getDateRange(): DateRange {
    return this.dateRange.value;
  }

  getCurrentDateRangeISO(): { from: string; to: string } {
    const current = this.dateRange.value;
    const now = new Date();
    const weekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
    
    return {
      from: current.startDate?.toISOString() || weekAgo.toISOString(),
      to: current.endDate?.toISOString() || now.toISOString()
    };
  }

  getDataA(): Observable<any> {
    return this.dataA.asObservable();
  }

  getDataB(): Observable<any> {
    return this.dataB.asObservable();
  }

  // News methods
  setNewsStatistics(statistics: NewsStatistics) {
    this.newsStatistics.next(statistics);
  }

  getNewsStatistics(): NewsStatistics {
    return this.newsStatistics.value;
  }

  setNewsFilters(filters: NewsFilters) {
    this.newsFilters.next(filters);
  }

  getNewsFilters(): NewsFilters {
    return this.newsFilters.value;
  }
}