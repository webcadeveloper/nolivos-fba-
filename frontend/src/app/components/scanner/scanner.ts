import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { ApiService } from '../../services/api.service';

@Component({
  selector: 'app-scanner',
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './scanner.html',
  styleUrl: './scanner.scss',
  standalone: true
})
export class Scanner implements OnInit, OnDestroy {
  maxProducts = 10;
  maxWorkers = 20;
  scanRunning = false;
  error = '';
  logs: string[] = [];
  progress = {
    total_products: 0,
    products_scanned: 0,
    opportunities_found: 0,
    errors: 0,
    progress_percent: 0
  };

  private progressInterval: any;

  constructor(private apiService: ApiService) {}

  ngOnInit() {
    this.checkScanStatus();
  }

  ngOnDestroy() {
    if (this.progressInterval) {
      clearInterval(this.progressInterval);
    }
  }

  setPreset(type: 'quick' | 'balanced' | 'deep') {
    switch (type) {
      case 'quick':
        this.maxProducts = 5;
        this.maxWorkers = 20;
        break;
      case 'balanced':
        this.maxProducts = 15;
        this.maxWorkers = 25;
        break;
      case 'deep':
        this.maxProducts = 50;
        this.maxWorkers = 30;
        break;
    }
  }

  startScan() {
    this.scanRunning = true;
    this.error = '';
    this.logs = [];

    this.apiService.startScan(this.maxProducts, this.maxWorkers).subscribe({
      next: (response) => {
        if (response.success) {
          alert(`Escaneo iniciado! Configuración: ${this.maxProducts} productos por categoría, ${this.maxWorkers} workers`);
          this.startProgressMonitoring();
        } else {
          this.error = response.error || 'Error al iniciar escaneo';
          this.scanRunning = false;
        }
      },
      error: (err) => {
        this.error = 'Error al iniciar escaneo';
        this.scanRunning = false;
        console.error('Error:', err);
      }
    });
  }

  checkScanStatus() {
    this.apiService.getScanProgress().subscribe({
      next: (response) => {
        if (response.success && response.data) {
          this.progress = response.data;
          if (this.progress.progress_percent > 0 && this.progress.progress_percent < 100) {
            this.scanRunning = true;
            this.startProgressMonitoring();
          }
        }
      },
      error: (err) => {
        console.error('Error checking scan status:', err);
      }
    });
  }

  startProgressMonitoring() {
    if (this.progressInterval) {
      clearInterval(this.progressInterval);
    }

    this.progressInterval = setInterval(() => {
      this.updateProgress();
      this.refreshLogs();
    }, 5000);
  }

  updateProgress() {
    this.apiService.getScanProgress().subscribe({
      next: (response) => {
        if (response.success && response.data) {
          this.progress = response.data;

          if (this.progress.progress_percent >= 100) {
            this.scanRunning = false;
            if (this.progressInterval) {
              clearInterval(this.progressInterval);
            }
            alert('Escaneo completado!');
          }
        }
      },
      error: (err) => {
        console.error('Error updating progress:', err);
      }
    });
  }

  refreshLogs() {
    this.apiService.getScanLogs(50).subscribe({
      next: (response) => {
        if (response.success && response.data) {
          this.logs = response.data.logs || [];
        }
      },
      error: (err) => {
        console.error('Error fetching logs:', err);
      }
    });
  }
}
