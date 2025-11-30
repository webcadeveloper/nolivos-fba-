import { Routes } from '@angular/router';
import { Dashboard } from './components/dashboard/dashboard';
import { Opportunities } from './components/opportunities/opportunities';
import { Scanner } from './components/scanner/scanner';

export const routes: Routes = [
  { path: '', redirectTo: '/dashboard', pathMatch: 'full' },
  { path: 'dashboard', component: Dashboard },
  { path: 'opportunities', component: Opportunities },
  { path: 'scanner', component: Scanner }
];
