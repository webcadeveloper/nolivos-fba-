import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { ApiService } from '../../services/api.service';
import { Opportunity, Stats } from '../../models/opportunity';

@Component({
  selector: 'app-dashboard',
  imports: [CommonModule, RouterModule],
  templateUrl: './dashboard.html',
  styleUrl: './dashboard.scss',
  standalone: true
})
export class Dashboard implements OnInit {
  stats: Stats | null = null;
  topOpportunities: Opportunity[] = [];
  loading = false;
  error = '';
  lastUpdate = '';

  constructor(private apiService: ApiService) {}

  ngOnInit() {
    this.loadDashboardData();
    this.updateLastUpdateTime();
  }

  loadDashboardData() {
    this.loading = true;
    this.error = '';

    this.apiService.getOpportunities(0, 0).subscribe({
      next: (response) => {
        if (response.success && response.data) {
          this.stats = response.data.stats;
          // Get top 5 opportunities sorted by ROI
          this.topOpportunities = response.data.opportunities
            .sort((a, b) => b.roi_percent - a.roi_percent)
            .slice(0, 5);
        } else {
          this.error = response.error || 'Error al cargar dashboard';
        }
        this.loading = false;
      },
      error: (err) => {
        this.error = 'Error de conexión con el backend';
        this.loading = false;
        console.error('Error:', err);
      }
    });
  }

  startQuickScan() {
    this.loading = true;
    this.error = '';

    this.apiService.startScan(5, 20).subscribe({
      next: (response) => {
        if (response.success) {
          alert('Escaneo rápido iniciado! Actualizando en 20 segundos...');
          setTimeout(() => this.loadDashboardData(), 20000);
        } else {
          this.error = response.error || 'Error al iniciar escaneo';
        }
        this.loading = false;
      },
      error: (err) => {
        this.error = 'Error al iniciar escaneo';
        this.loading = false;
        console.error('Error:', err);
      }
    });
  }

  exportData() {
    window.open('http://localhost:5000/api/export/opportunities/excel?min_roi=0&min_profit=0', '_blank');
  }

  updateLastUpdateTime() {
    const now = new Date();
    this.lastUpdate = now.toLocaleTimeString('es-ES', {
      hour: '2-digit',
      minute: '2-digit'
    });
  }
}
