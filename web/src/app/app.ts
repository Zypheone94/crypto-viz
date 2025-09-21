import { Component } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, RouterLink, RouterLinkActive],
  template: `
  <nav>
      <a routerLink="/home" 
         routerLinkActive="active">Accueil</a>
      <a routerLink="/analytics" 
         routerLinkActive="active">Analytics</a>
    </nav>
    
    <router-outlet></router-outlet>
  `,
  styles: [`
    .active { 
      font-weight: bold; 
      color: #007acc; 
    }
  `]
})

export class App {}
