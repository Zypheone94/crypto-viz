import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet],
  template: ` <router-outlet></router-outlet> `,
  styles: [
    `
      .active {
        font-weight: bold;
        color: #007acc;
      }
    `,
  ],
})
export class App {}
