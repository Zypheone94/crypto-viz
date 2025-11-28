import { Component, OnInit } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'app-correlation',
  templateUrl: './correlation.html',
  styleUrls: ['./correlation.css'],
  imports: [FormsModule],
})
export class Correlation implements OnInit {
  symbols = ['2Z', 'ETH', 'BTC'];
  symbol1: string | null = null;
  symbol2: string | null = null;
  timespan: 'hour' | 'day' = 'day';

  correlation: any = null;
  loading = false;
  errorMsg = '';

  constructor(private http: HttpClient) {}

  ngOnInit() {
    this.tryLoadCorrelation();
  }

  onSelectionChange() {
    this.tryLoadCorrelation();
  }

  tryLoadCorrelation() {
    if (!this.symbol1 || !this.symbol2) {
      return;
    }

    this.loading = true;
    this.errorMsg = '';
    this.correlation = null;

    const params = new HttpParams()
      .set('symbol1', this.symbol1)
      .set('symbol2', this.symbol2)
      .set('timespan', this.timespan);

    this.http.get('/correlation', { params }).subscribe({
      next: (res) => {
        this.correlation = res;
        this.loading = false;
      },
      error: (err) => {
        console.error(err);
        this.errorMsg = 'Erreur lors de la récupération des données';
        this.loading = false;
      },
    });
  }
}
