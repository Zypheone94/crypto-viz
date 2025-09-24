import { bootstrapApplication } from '@angular/platform-browser';
import 'zone.js'
import { App } from './app/app';
import { provideRouter } from '@angular/router';
import { provideHttpClient } from '@angular/common/http';
import { routes } from './app/app.routes';

bootstrapApplication(App, {
  providers: [provideRouter(routes), provideHttpClient()]
})