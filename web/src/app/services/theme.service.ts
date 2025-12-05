import { Injectable, signal, effect, PLATFORM_ID, Inject } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';

export type Theme = 'light' | 'dark' | 'auto';

@Injectable({
  providedIn: 'root'
})
export class ThemeService {
  // Use Angular signals for reactive theme management
  private readonly THEME_STORAGE_KEY = 'cryptoviz-theme';
  public currentTheme = signal<Theme>(this.getSavedTheme());
  public isDark = signal<boolean>(false);
  private isBrowser: boolean;

  constructor(@Inject(PLATFORM_ID) private platformId: object) {
    this.isBrowser = isPlatformBrowser(this.platformId);
    
    // Only run browser-specific code if we're in the browser
    if (this.isBrowser) {
      // Initialize theme on service creation
      this.applyTheme(this.currentTheme());
      
      // Watch for theme changes
      effect(() => {
        const theme = this.currentTheme();
        this.applyTheme(theme);
        if (typeof localStorage !== 'undefined') {
          localStorage.setItem(this.THEME_STORAGE_KEY, theme);
        }
      });

      // Listen for system theme changes when in auto mode
      if (typeof window !== 'undefined' && window.matchMedia) {
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
          if (this.currentTheme() === 'auto') {
            this.isDark.set(e.matches);
            this.updateDocumentTheme(e.matches);
          }
        });
      }
    }
  }

  /**
   * Toggle between light and dark themes
   */
  toggleTheme(): void {
    const current = this.currentTheme();
    if (current === 'auto') {
      this.currentTheme.set('light');
    } else if (current === 'light') {
      this.currentTheme.set('dark');
    } else {
      this.currentTheme.set('auto');
    }
  }

  /**
   * Set a specific theme
   */
  setTheme(theme: Theme): void {
    this.currentTheme.set(theme);
  }

  /**
   * Get the currently active theme from localStorage or default to 'auto'
   * Safe for SSR - returns 'auto' if localStorage is not available
   */
  private getSavedTheme(): Theme {
    if (typeof localStorage === 'undefined') {
      return 'auto';
    }
    const saved = localStorage.getItem(this.THEME_STORAGE_KEY);
    return (saved === 'light' || saved === 'dark' || saved === 'auto') ? saved : 'auto';
  }

  /**
   * Apply the theme to the document
   * Safe for SSR - only runs in browser
   */
  private applyTheme(theme: Theme): void {
    if (!this.isBrowser) {
      return;
    }

    let shouldBeDark = false;

    if (theme === 'auto') {
      shouldBeDark = typeof window !== 'undefined' && window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
    } else {
      shouldBeDark = theme === 'dark';
    }

    this.isDark.set(shouldBeDark);
    this.updateDocumentTheme(shouldBeDark);
  }

  /**
   * Update the document's theme class
   * Safe for SSR - only runs in browser
   */
  private updateDocumentTheme(dark: boolean): void {
    if (!this.isBrowser || typeof document === 'undefined') {
      return;
    }

    const root = document.documentElement;
    
    if (dark) {
      root.classList.add('dark-theme');
      root.classList.remove('light-theme');
      // Update meta theme-color for mobile browsers
      this.updateMetaThemeColor('#0f172a');
    } else {
      root.classList.add('light-theme');
      root.classList.remove('dark-theme');
      this.updateMetaThemeColor('#ffffff');
    }
  }

  private updateMetaThemeColor(color: string): void {
    if (!this.isBrowser || typeof document === 'undefined') {
      return;
    }

    let metaThemeColor = document.querySelector('meta[name="theme-color"]');
    if (!metaThemeColor) {
      metaThemeColor = document.createElement('meta');
      metaThemeColor.setAttribute('name', 'theme-color');
      document.head.appendChild(metaThemeColor);
    }
    metaThemeColor.setAttribute('content', color);
  }

  /**
   * Get theme icon based on current theme
   */
  getThemeIcon(): string {
    const theme = this.currentTheme();
    if (theme === 'dark') return 'dark_mode';
    if (theme === 'light') return 'light_mode';
    return 'brightness_auto';
  }

  /**
   * Get theme label based on current theme
   */
  getThemeLabel(): string {
    const theme = this.currentTheme();
    if (theme === 'dark') return 'Mode sombre';
    if (theme === 'light') return 'Mode clair';
    return 'Automatique';
  }
}

