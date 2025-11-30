"""
Amazon Seller Partner API (SP-API) Client.
Implementa OAuth 2.0, rate limiting, y cache para obtener datos reales de Amazon.
"""
import os
import json
import time
import logging
import sqlite3
from datetime import datetime, timedelta
import requests
from requests.auth import HTTPBasicAuth
import hashlib

logging.basicConfig(level=logging.INFO)

class SPAPIClient:
    def __init__(self, config_path='config/sp_api_config.json'):
        self.config = self._load_config(config_path)
        self.access_token = None
        self.token_expires_at = None
        self.db_path = 'data/sp_api_cache.db'
        self._init_database()
        self._init_rate_limiters()
        
    def _load_config(self, config_path):
        """Carga configuración desde archivo o variables de entorno"""
        try:
            # Intentar cargar desde archivo
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    logging.info("SP-API config loaded from file")
                    return config
        except Exception as e:
            logging.warning(f"Could not load config file: {e}")
        
        # Fallback a variables de entorno
        config = {
            'lwa_app_id': os.getenv('SP_API_LWA_APP_ID'),
            'lwa_client_secret': os.getenv('SP_API_LWA_CLIENT_SECRET'),
            'refresh_token': os.getenv('SP_API_REFRESH_TOKEN'),
            'aws_access_key': os.getenv('SP_API_AWS_ACCESS_KEY'),
            'aws_secret_key': os.getenv('SP_API_AWS_SECRET_KEY'),
            'role_arn': os.getenv('SP_API_ROLE_ARN'),
            'marketplace_id': os.getenv('SP_API_MARKETPLACE_ID', 'ATVPDKIKX0DER'),
            'region': os.getenv('SP_API_REGION', 'us-east-1'),
            'endpoints': {
                'na': 'https://sellingpartnerapi-na.amazon.com'
            }
        }
        
        logging.info("SP-API config loaded from environment variables")
        return config
    
    def _init_database(self):
        """Inicializa cache de SP-API"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sp_api_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cache_key TEXT UNIQUE NOT NULL,
                asin TEXT,
                data_type TEXT,
                data_json TEXT,
                fetched_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                expires_at DATETIME
            )
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_cache_key ON sp_api_cache(cache_key)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_asin ON sp_api_cache(asin)
        ''')
        
        conn.commit()
        conn.close()
        logging.info(f"SP-API cache database initialized at {self.db_path}")
    
    def _init_rate_limiters(self):
        """Inicializa rate limiters por endpoint"""
        self.last_request_time = {}
        self.rate_limits = self.config.get('rate_limits', {
            'orders': 0.0167,  # 1 request per 60 seconds
            'catalog': 2.0,     # 2 requests per second
            'fees': 1.0,        # 1 request per second
            'advertising': 1.0
        })
    
    def _get_access_token(self):
        """Obtiene access token usando refresh token (OAuth 2.0)"""
        # Si tenemos token válido, retornarlo
        if self.access_token and self.token_expires_at:
            if datetime.now() < self.token_expires_at:
                return self.access_token
        
        # Obtener nuevo token
        try:
            url = 'https://api.amazon.com/auth/o2/token'
            
            data = {
                'grant_type': 'refresh_token',
                'refresh_token': self.config['refresh_token'],
                'client_id': self.config['lwa_app_id'],
                'client_secret': self.config['lwa_client_secret']
            }
            
            response = requests.post(url, data=data, timeout=30)
            response.raise_for_status()
            
            token_data = response.json()
            self.access_token = token_data['access_token']
            
            # Token expira en 1 hora, renovar 5 min antes
            expires_in = token_data.get('expires_in', 3600)
            self.token_expires_at = datetime.now() + timedelta(seconds=expires_in - 300)
            
            logging.info("SP-API access token refreshed successfully")
            return self.access_token
            
        except Exception as e:
            logging.error(f"Error getting SP-API access token: {e}")
            raise Exception(f"SP-API authentication failed: {e}")
    
    def _wait_for_rate_limit(self, endpoint_type):
        """Implementa rate limiting con backoff"""
        rate_limit = self.rate_limits.get(endpoint_type, 1.0)
        min_interval = 1.0 / rate_limit if rate_limit > 0 else 1.0
        
        last_time = self.last_request_time.get(endpoint_type, 0)
        elapsed = time.time() - last_time
        
        if elapsed < min_interval:
            sleep_time = min_interval - elapsed
            logging.debug(f"Rate limiting: sleeping {sleep_time:.2f}s for {endpoint_type}")
            time.sleep(sleep_time)
        
        self.last_request_time[endpoint_type] = time.time()
    
    def _make_request(self, method, path, endpoint_type='default', params=None, data=None, use_cache=True, cache_ttl=3600):
        """Hace request a SP-API con rate limiting y cache"""
        # Generar cache key
        cache_key = hashlib.md5(f"{method}:{path}:{json.dumps(params or {})}".encode()).hexdigest()
        
        # Intentar obtener de cache
        if use_cache and method == 'GET':
            cached_data = self._get_from_cache(cache_key)
            if cached_data:
                logging.info(f"SP-API cache hit for {path}")
                return cached_data
        
        # Rate limiting
        self._wait_for_rate_limit(endpoint_type)
        
        # Obtener access token
        access_token = self._get_access_token()
        
        # Construir URL
        base_url = self.config['endpoints'].get('na', 'https://sellingpartnerapi-na.amazon.com')
        url = f"{base_url}{path}"
        
        # Headers
        headers = {
            'x-amz-access-token': access_token,
            'Content-Type': 'application/json'
        }
        
        # Hacer request con retry
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.request(
                    method=method,
                    url=url,
                    headers=headers,
                    params=params,
                    json=data,
                    timeout=30
                )
                
                # Rate limit exceeded - exponential backoff
                if response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', 5))
                    logging.warning(f"Rate limit exceeded, retrying after {retry_after}s")
                    time.sleep(retry_after * (2 ** attempt))
                    continue
                
                response.raise_for_status()
                result = response.json()
                
                # Guardar en cache
                if use_cache and method == 'GET':
                    self._save_to_cache(cache_key, result, cache_ttl)
                
                return result
                
            except requests.exceptions.RequestException as e:
                logging.error(f"SP-API request error (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt == max_retries - 1:
                    raise
                time.sleep(2 ** attempt)
        
        raise Exception("SP-API request failed after retries")
    
    def _get_from_cache(self, cache_key):
        """Obtiene datos del cache si no han expirado"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT data_json, expires_at FROM sp_api_cache
                WHERE cache_key = ?
            ''', (cache_key,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                data_json, expires_at = row
                if datetime.now() < datetime.fromisoformat(expires_at):
                    return json.loads(data_json)
            
            return None
            
        except Exception as e:
            logging.error(f"Error getting from cache: {e}")
            return None
    
    def _save_to_cache(self, cache_key, data, ttl=3600):
        """Guarda datos en cache"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            expires_at = datetime.now() + timedelta(seconds=ttl)
            
            cursor.execute('''
                INSERT OR REPLACE INTO sp_api_cache 
                (cache_key, data_json, expires_at)
                VALUES (?, ?, ?)
            ''', (cache_key, json.dumps(data), expires_at))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logging.error(f"Error saving to cache: {e}")
    
    # ==================== API METHODS ====================
    
    def get_orders(self, start_date, end_date, marketplace_ids=None):
        """Obtiene órdenes del seller (Orders API)"""
        if not marketplace_ids:
            marketplace_ids = [self.config['marketplace_id']]
        
        params = {
            'MarketplaceIds': ','.join(marketplace_ids),
            'CreatedAfter': start_date.isoformat(),
            'CreatedBefore': end_date.isoformat()
        }
        
        return self._make_request(
            'GET',
            '/orders/v0/orders',
            endpoint_type='orders',
            params=params,
            cache_ttl=1800  # 30 min cache
        )
    
    def get_product_fees(self, asin, price, is_fba=True):
        """Obtiene fees oficiales para un producto (Product Fees API)"""
        data = {
            'FeesEstimateRequest': {
                'MarketplaceId': self.config['marketplace_id'],
                'IsAmazonFulfilled': is_fba,
                'PriceToEstimateFees': {
                    'ListingPrice': {
                        'CurrencyCode': 'USD',
                        'Amount': price
                    }
                },
                'Identifier': asin
            }
        }
        
        return self._make_request(
            'POST',
            f'/products/fees/v0/items/{asin}/feesEstimate',
            endpoint_type='fees',
            data=data,
            use_cache=True,
            cache_ttl=86400  # 24 hours cache
        )
    
    def get_catalog_item(self, asin, marketplace_ids=None):
        """Obtiene información del catálogo (Catalog Items API)"""
        if not marketplace_ids:
            marketplace_ids = [self.config['marketplace_id']]
        
        params = {
            'marketplaceIds': ','.join(marketplace_ids),
            'includedData': 'attributes,dimensions,images,productTypes,salesRanks'
        }
        
        return self._make_request(
            'GET',
            f'/catalog/2022-04-01/items/{asin}',
            endpoint_type='catalog',
            params=params,
            cache_ttl=86400  # 24 hours cache
        )
    
    def get_advertising_campaigns(self):
        """Obtiene campañas de advertising (Advertising API)"""
        # Nota: Advertising API requiere diferentes credenciales
        # Este es un placeholder para implementación futura
        logging.warning("Advertising API not fully implemented yet")
        return {
            'campaigns': [],
            'message': 'Advertising API requires additional setup'
        }
    
    def is_configured(self):
        """Verifica si SP-API está configurado correctamente"""
        required_fields = ['lwa_app_id', 'lwa_client_secret', 'refresh_token']
        return all(self.config.get(field) for field in required_fields)
