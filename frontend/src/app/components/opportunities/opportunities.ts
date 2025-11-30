import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../services/api.service';
import { Opportunity, Stats } from '../../models/opportunity';

@Component({
  selector: 'app-opportunities',
  imports: [CommonModule, FormsModule],
  templateUrl: './opportunities.html',
  styleUrl: './opportunities.scss',
  standalone: true
})
export class Opportunities implements OnInit {
  opportunities: Opportunity[] = [];
  filteredOpportunities: Opportunity[] = [];
  stats: Stats | null = null;
  loading = false;
  error = '';

  // Filters
  minRoi: number = 5;
  minProfit: number = 3;
  fbaSafeOnly: boolean = false;

  constructor(private apiService: ApiService) {}

  ngOnInit() {
    this.loadOpportunities();
  }

  loadOpportunities() {
    this.loading = true;
    this.error = '';

    this.apiService.getOpportunities(this.minRoi, this.minProfit).subscribe({
      next: (response) => {
        if (response.success && response.data) {
          this.opportunities = response.data.opportunities;
          this.stats = response.data.stats;
          this.applyClientFilters();
        } else {
          this.error = response.error || 'Error al cargar oportunidades';
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

  applyFilters() {
    this.loadOpportunities();
  }

  applyClientFilters() {
    this.filteredOpportunities = this.opportunities.filter(opp => {
      if (this.fbaSafeOnly && opp.fba_compliant !== 1) {
        return false;
      }
      return true;
    });
  }

  filterFbaSafe() {
    this.applyClientFilters();
  }

  startScan() {
    this.loading = true;
    this.error = '';

    this.apiService.startScan(10, 20).subscribe({
      next: (response) => {
        if (response.success) {
          alert('Escaneo iniciado! Los resultados aparecerán en unos minutos.');
          // Recargar después de 30 segundos
          setTimeout(() => this.loadOpportunities(), 30000);
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

  getSupplierUrls(opportunity: Opportunity): {name: string, url: string, icon: string}[] {
    if (!opportunity.all_supplier_urls) return [];

    try {
      const parsed = JSON.parse(opportunity.all_supplier_urls);
      return [
        { name: 'AliEx', url: parsed.aliexpress?.url || '', icon: parsed.aliexpress?.icon || '🇨🇳' },
        { name: 'eBay', url: parsed.ebay?.url || '', icon: parsed.ebay?.icon || '🛒' },
        { name: 'Walmart', url: parsed.walmart?.url || '', icon: parsed.walmart?.icon || '🏪' },
        { name: 'Target', url: parsed.target?.url || '', icon: parsed.target?.icon || '🎯' }
      ].filter(s => s.url);
    } catch {
      return [];
    }
  }

  getCompetitivenessClass(level: string | undefined): string {
    if (!level) return 'badge badge-low';

    if (level.includes('🟢') || level.includes('EXCELENTE')) {
      return 'badge badge-excellent';
    } else if (level.includes('🟡') || level.includes('BUENO')) {
      return 'badge badge-good';
    } else if (level.includes('🟠') || level.includes('REGULAR')) {
      return 'badge badge-regular';
    } else {
      return 'badge badge-low';
    }
  }
}
