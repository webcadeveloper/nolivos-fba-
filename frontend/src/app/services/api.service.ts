import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { ApiResponse, Opportunity, Stats } from '../models/opportunity';
import { environment } from '../../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class ApiService {
  private apiUrl = environment.apiUrl;

  constructor(private http: HttpClient) { }

  getOpportunities(minRoi: number = 5, minProfit: number = 3): Observable<ApiResponse<{opportunities: Opportunity[], stats: Stats, total_count: number}>> {
    return this.http.get<ApiResponse<any>>(`${this.apiUrl}/opportunities?min_roi=${minRoi}&min_profit=${minProfit}`);
  }

  getStats(): Observable<ApiResponse<Stats>> {
    return this.http.get<ApiResponse<Stats>>(`${this.apiUrl}/stats`);
  }

  startScan(maxProducts: number = 10, maxWorkers: number = 20): Observable<ApiResponse<any>> {
    return this.http.post<ApiResponse<any>>(`${this.apiUrl}/scan/start`, {
      max_products_per_category: maxProducts,
      max_workers: maxWorkers
    });
  }

  getScanProgress(): Observable<ApiResponse<any>> {
    return this.http.get<ApiResponse<any>>(`${this.apiUrl}/scan/progress`);
  }

  getScanLogs(maxLogs: number = 50): Observable<ApiResponse<{logs: string[]}>> {
    return this.http.get<ApiResponse<any>>(`${this.apiUrl}/scan/logs?max_logs=${maxLogs}`);
  }
}
