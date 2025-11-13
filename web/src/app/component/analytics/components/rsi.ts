import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';

@Component({
  selector: 'app-rsi',
  standalone: true,
  imports: [CommonModule, MatCardModule, MatIconModule],
  template: `
    <div class="rsi-container">
      <mat-card class="rsi-card">
        <mat-card-header>
          <mat-card-title class="chart-title">
            <mat-icon class="title-icon">show_chart</mat-icon>
            RSI (Relative Strength Index)
          </mat-card-title>
          <mat-card-subtitle>
            Indicateur de momentum pour identifier les conditions de surachat/survente
          </mat-card-subtitle>
        </mat-card-header>
        
        <mat-card-content>
          <div class="coming-soon">
            <mat-icon class="coming-soon-icon">show_chart</mat-icon>
            <h3>RSI Analysis</h3>
          </div>
        </mat-card-content>
      </mat-card>
    </div>
  `,
  styles: [`
    .rsi-container {
      padding: 1rem;
    }

    .rsi-card {
      border-radius: 12px;
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
    }

    .chart-title {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      font-size: 1.25rem;
      font-weight: 600;
    }

    .title-icon {
      color: #2196F3;
    }

    .coming-soon {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 4rem 2rem;
      text-align: center;
    }

    .coming-soon-icon {
      font-size: 4rem;
      width: 4rem;
      height: 4rem;
      color: #FF9800;
      margin-bottom: 1rem;
    }

    .coming-soon h3 {
      color: #333;
      margin: 0 0 1rem 0;
      font-size: 1.5rem;
    }

    .coming-soon p {
      color: #666;
      margin: 0;
      max-width: 300px;
    }
  `]
})
export class RsiComponent {
}