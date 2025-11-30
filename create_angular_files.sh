#!/bin/bash

BASE="/mnt/c/Users/Admin/OneDrive - Nolivos Law/Aplicaciones/AMAZON/amz-review-analyzer/frontend/src/app"

# opportunities.html
cat > "$BASE/components/opportunities/opportunities.html" <<'EOF'
<div class="opportunities-container">
  <h1>Oportunidades FBA</h1>
  @if (loading) {<div class="loading">Cargando...</div>}
  @if (error) {<div class="error">{{ error }}</div>}
  @if (stats) {
    <div class="stats-summary">
      <div class="stat-card"><div class="stat-value">{{ stats.total_opportunities }}</div><div class="stat-label">Total</div></div>
      <div class="stat-card"><div class="stat-value">{{ stats.avg_roi | number:'1.1-1' }}%</div><div class="stat-label">ROI Promedio</div></div>
      <div class="stat-card"><div class="stat-value">\${{ stats.avg_profit | number:'1.2-2' }}</div><div class="stat-label">Ganancia Promedio</div></div>
    </div>
  }
  @if (opportunities.length > 0) {
    <table class="table">
      <thead><tr><th>Producto</th><th>ASIN</th><th>Amazon</th><th>Proveedor</th><th>Ganancia</th><th>ROI</th></tr></thead>
      <tbody>
        @for (opp of opportunities; track opp.asin) {
          <tr>
            <td>{{ opp.product_name }}</td>
            <td><code>{{ opp.asin }}</code></td>
            <td>\${{ opp.amazon_price | number:'1.2-2' }}</td>
            <td>\${{ opp.supplier_price | number:'1.2-2' }}</td>
            <td class="profit">\${{ opp.net_profit | number:'1.2-2' }}</td>
            <td class="roi">{{ opp.roi_percent | number:'1.1-1' }}%</td>
          </tr>
        }
      </tbody>
    </table>
  }
</div>
EOF

# app.routes.ts
cat > "$BASE/app.routes.ts" <<'EOF'
import { Routes } from '@angular/router';
import { Opportunities } from './components/opportunities/opportunities';

export const routes: Routes = [
  { path: '', redirectTo: '/opportunities', pathMatch: 'full' },
  { path: 'opportunities', component: Opportunities }
];
EOF

echo "✅ Archivos Angular creados"
