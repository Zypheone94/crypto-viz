import { bootstrapApplication } from '@angular/platform-browser';
import 'zone.js'
import { App } from './app/app';
import { provideRouter } from '@angular/router';
import { provideHttpClient } from '@angular/common/http';
import { routes } from './app/app.routes';
import { provideCharts, withDefaultRegisterables } from 'ng2-charts';

bootstrapApplication(App, {
  providers: [provideRouter(routes), provideHttpClient(), provideCharts(withDefaultRegisterables())]
})