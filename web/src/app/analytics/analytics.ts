import { CommonModule } from '@angular/common';
import { Component, OnDestroy, OnInit } from '@angular/core';
import { interval, Subscription } from 'rxjs';

@Component({
  selector: 'app-analytics',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './analytics.html',
  styleUrls: ['./analytics.css']
})
export class Analytics implements OnInit, OnDestroy{

  // Subscription to manage the interval
  private intervalSubscription: Subscription = new Subscription();
  // Interval duration in milliseconds
  private intervalDuration: number = 5000; 

  ngOnInit() {
    this.intervalSubscription = interval(this.intervalDuration).subscribe(n => {
      console.log('tick', n);
    });
  }

  ngOnDestroy(): void {
    this.intervalSubscription.unsubscribe();
    console.log("Composant démonté");
  }

}
