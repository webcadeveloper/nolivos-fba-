export interface SupplierUrl {
  name: string;
  url: string;
  icon: string;
}

export interface Opportunity {
  id?: number;
  product_name: string;
  asin: string;
  amazon_price: number;
  supplier_price: number;
  supplier_name: string;
  net_profit: number;
  roi_percent: number;
  category: string;
  bsr?: number;
  all_supplier_urls?: string;
  image_url?: string;
  amazon_url?: string;
  total_cost?: number;
  margin_percent?: number;
  competitiveness_level?: string;
  fba_compliant?: number;
  fba_size_tier?: string;
  fba_warnings?: string;
  product_length?: number;
  product_width?: number;
  product_height?: number;
  product_weight?: number;
  product_rating?: number;
  review_count?: number;
}

export interface Stats {
  total_opportunities: number;
  avg_roi: number;
  avg_profit: number;
  max_roi: number;
  max_profit: number;
}

export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
}
