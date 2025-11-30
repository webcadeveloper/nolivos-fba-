"""
Product Discovery Scanner - Encuentra oportunidades de arbitraje automáticamente
Escanea Best Sellers de Amazon diariamente y compara precios con proveedores
"""
import logging
import sqlite3
import time
import json
from datetime import datetime
from src.scrapers.product_info import ProductInfoScraper
from src.scrapers.supplier_scraper import SupplierScraper, SupplierPriceEstimator
from src.analyzers.fba_calculator import FBACalculator
from src.analyzers.sales_estimator import estimate_monthly_sales
from src.api.n8n_webhooks import n8n_webhooks
from src.utils.fba_rules_checker import FBARulesChecker

logging.basicConfig(level=logging.INFO)


class OpportunityDatabase:
    """Maneja la base de datos de oportunidades de arbitraje"""

    def __init__(self, db_path='opportunities.db'):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """Crea las tablas necesarias"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS opportunities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                asin TEXT UNIQUE NOT NULL,
                product_name TEXT,
                category TEXT,

                -- Amazon data
                amazon_price REAL,
                bsr INTEGER,
                estimated_monthly_sales INTEGER,

                -- Supplier data
                supplier_name TEXT,
                supplier_price REAL,
                supplier_url TEXT,
                supplier_moq INTEGER,

                -- Profit analysis
                total_cost REAL,
                amazon_fees REAL,
                net_profit REAL,
                roi_percent REAL,
                margin_percent REAL,
                competitiveness_score INTEGER,
                competitiveness_level TEXT,

                -- FBA Compliance data
                fba_compliant BOOLEAN,
                fba_warnings TEXT,
                fba_size_tier TEXT,
                product_length REAL,
                product_width REAL,
                product_height REAL,
                product_weight REAL,
                product_rating REAL,
                review_count INTEGER,

                -- Metadata
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                scan_date DATE,
                is_active BOOLEAN DEFAULT 1,
                amazon_url TEXT,
                image_url TEXT,
                supplier_image_url TEXT
            )
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_roi ON opportunities(roi_percent DESC)
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_profit ON opportunities(net_profit DESC)
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_scan_date ON opportunities(scan_date DESC)
        ''')

        conn.commit()
        conn.close()
        logging.info("Database initialized successfully")

    def save_opportunity(self, opportunity_data):
        """Guarda o actualiza una oportunidad"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT OR REPLACE INTO opportunities
            (asin, product_name, category, amazon_price, bsr, estimated_monthly_sales,
             supplier_name, supplier_price, supplier_url, supplier_moq,
             total_cost, amazon_fees, net_profit, roi_percent, margin_percent,
             competitiveness_score, competitiveness_level, scan_date, last_updated,
             amazon_url, image_url, supplier_image_url,
             fba_compliant, fba_warnings, fba_size_tier,
             product_length, product_width, product_height, product_weight,
             product_rating, review_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            opportunity_data['asin'],
            opportunity_data['product_name'],
            opportunity_data['category'],
            opportunity_data['amazon_price'],
            opportunity_data['bsr'],
            opportunity_data['estimated_monthly_sales'],
            opportunity_data['supplier_name'],
            opportunity_data['supplier_price'],
            opportunity_data['supplier_url'],
            opportunity_data['supplier_moq'],
            opportunity_data['total_cost'],
            opportunity_data['amazon_fees'],
            opportunity_data['net_profit'],
            opportunity_data['roi_percent'],
            opportunity_data['margin_percent'],
            opportunity_data['competitiveness_score'],
            opportunity_data['competitiveness_level'],
            opportunity_data['scan_date'],
            opportunity_data.get('amazon_url'),
            opportunity_data.get('image_url'),
            opportunity_data.get('supplier_image_url'),
            opportunity_data.get('fba_compliant'),
            opportunity_data.get('fba_warnings'),
            opportunity_data.get('fba_size_tier'),
            opportunity_data.get('product_length'),
            opportunity_data.get('product_width'),
            opportunity_data.get('product_height'),
            opportunity_data.get('product_weight'),
            opportunity_data.get('product_rating'),
            opportunity_data.get('review_count')
        ))

        conn.commit()
        conn.close()

    def get_opportunities(self, min_roi=0, min_profit=0, limit=100):
        """Obtiene las mejores oportunidades"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM opportunities
            WHERE roi_percent >= ? AND net_profit >= ? AND is_active = 1
            ORDER BY roi_percent DESC, net_profit DESC
            LIMIT ?
        ''', (min_roi, min_profit, limit))

        opportunities = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return opportunities

    def get_stats(self):
        """Obtiene estadísticas generales"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT
                COUNT(*) as total,
                AVG(roi_percent) as avg_roi,
                AVG(net_profit) as avg_profit,
                MAX(roi_percent) as max_roi,
                MAX(net_profit) as max_profit
            FROM opportunities
            WHERE is_active = 1
        ''')

        stats = cursor.fetchone()
        conn.close()

        return {
            'total_opportunities': stats[0] if stats[0] else 0,
            'avg_roi': round(stats[1], 2) if stats[1] else 0,
            'avg_profit': round(stats[2], 2) if stats[2] else 0,
            'max_roi': round(stats[3], 2) if stats[3] else 0,
            'max_profit': round(stats[4], 2) if stats[4] else 0
        }


class ProductDiscoveryScanner:
    """
    Escanea Amazon Best Sellers y encuentra oportunidades de arbitraje
    """

    # Categorías principales de Amazon Best Sellers
    BEST_SELLER_CATEGORIES = {
        'electronics': 'https://www.amazon.com/Best-Sellers-Electronics/zgbs/electronics',
        'home-kitchen': 'https://www.amazon.com/Best-Sellers-Home-Kitchen/zgbs/home-garden',
        'toys': 'https://www.amazon.com/Best-Sellers-Toys-Games/zgbs/toys-and-games',
        'sports': 'https://www.amazon.com/Best-Sellers-Sports-Outdoors/zgbs/sporting-goods',
        'health': 'https://www.amazon.com/Best-Sellers-Health-Personal-Care/zgbs/hpc',
        'beauty': 'https://www.amazon.com/Best-Sellers-Beauty/zgbs/beauty',
        'pet-supplies': 'https://www.amazon.com/Best-Sellers-Pet-Supplies/zgbs/pet-supplies',
        'office': 'https://www.amazon.com/Best-Sellers-Office-Products/zgbs/office-products',
    }

    def __init__(self):
        self.db = OpportunityDatabase()
        self.splash_url = 'http://localhost:8050/render.html'

    def scan_best_sellers(self, max_products_per_category=20):
        """
        Escanea todas las categorías de Best Sellers

        Args:
            max_products_per_category: Máximo de productos a analizar por categoría

        Returns:
            dict con estadísticas del escaneo
        """
        logging.info(f"🚀 Iniciando escaneo de Best Sellers - {datetime.now()}")

        total_scanned = 0
        total_opportunities = 0
        scan_date = datetime.now().date().isoformat()

        for category_name, category_url in self.BEST_SELLER_CATEGORIES.items():
            logging.info(f"\n📦 Escaneando categoría: {category_name}")

            try:
                # Extraer ASINs de la página de Best Sellers
                asins = self._extract_best_seller_asins(category_url, max_products_per_category)
                logging.info(f"Encontrados {len(asins)} productos en {category_name}")

                # Analizar cada producto
                for idx, asin in enumerate(asins, 1):
                    logging.info(f"\n📦 [{idx}/{len(asins)}] ASIN: {asin} | Categoría: {category_name}")

                    try:
                        opportunity = self._analyze_product(asin, category_name, scan_date)

                        if opportunity:
                            # Guardar TODOS los productos encontrados (no filtrar por ROI)
                            self.db.save_opportunity(opportunity)
                            total_opportunities += 1

                            roi = opportunity['roi_percent']
                            profit = opportunity['net_profit']

                            if roi > 20:
                                logging.info(f"✅ EXCELENTE - Ganancia: ${profit:.2f} | ROI: {roi:.1f}% | Proveedor: {opportunity['supplier_name']}")
                                # 🔥 WEBHOOK: Enviar notificación de oportunidad encontrada
                                try:
                                    n8n_webhooks.trigger_opportunity_found(opportunity)
                                except Exception as webhook_error:
                                    logging.warning(f"Error enviando webhook: {webhook_error}")
                            elif roi > 0:
                                logging.info(f"💰 BUENO - Ganancia: ${profit:.2f} | ROI: {roi:.1f}% | Proveedor: {opportunity['supplier_name']}")
                            else:
                                logging.info(f"📊 GUARDADO - ROI: {roi:.1f}% | Proveedor: {opportunity['supplier_name']}")
                        else:
                            logging.info(f"❌ Sin datos válidos para {asin}")

                        total_scanned += 1

                        # Rate limiting reducido (2s en lugar de 3s)
                        time.sleep(2)

                    except Exception as e:
                        logging.error(f"    ❌ Error analizando {asin}: {e}")
                        continue

            except Exception as e:
                logging.error(f"Error escaneando categoría {category_name}: {e}")
                continue

        stats = {
            'total_scanned': total_scanned,
            'total_opportunities': total_opportunities,
            'scan_date': scan_date,
            'completion_time': datetime.now().isoformat()
        }

        logging.info(f"\n✅ Escaneo completado!")
        logging.info(f"   Productos analizados: {total_scanned}")
        logging.info(f"   Oportunidades encontradas: {total_opportunities}")

        # 🔥 WEBHOOK: Enviar notificación de escaneo completado
        try:
            top_opportunities = self.db.get_opportunities(min_roi=10, min_profit=5, limit=10)
            n8n_webhooks.trigger_daily_scan_completed(stats, top_opportunities)
        except Exception as webhook_error:
            logging.warning(f"Error enviando webhook de escaneo completado: {webhook_error}")

        return stats

    def _extract_best_seller_asins(self, category_url, max_products=20):
        """Extrae ASINs de una página de Best Sellers usando Splash"""
        import re
        from amzscraper import AmazonWebRobot

        try:
            # Usar Splash básico (funciona mejor que stealth mode por ahora)
            logging.info(f"📡 Extrayendo ASINs de Best Sellers: {category_url}")
            robot = AmazonWebRobot(enable_stealth=False)

            # Obtener HTML
            soup = robot.get_soup(category_url)

            if not soup:
                logging.error(f"No se pudo obtener HTML de: {category_url}")
                return []

            # Buscar ASINs en la página
            asins = []

            # Método 1: data-asin attribute
            asin_elements = soup.find_all(attrs={'data-asin': True})
            for elem in asin_elements:
                asin = elem.get('data-asin')
                if asin and len(asin) == 10 and asin not in asins:
                    asins.append(asin)
                    if len(asins) >= max_products:
                        break

            # Método 2: links /dp/
            if len(asins) < max_products:
                links = soup.find_all('a', href=True)
                for link in links:
                    href = link['href']
                    match = re.search(r'/dp/([A-Z0-9]{10})', href)
                    if match:
                        asin = match.group(1)
                        if asin not in asins:
                            asins.append(asin)
                            if len(asins) >= max_products:
                                break

            return asins[:max_products]

        except Exception as e:
            logging.error(f"Error extrayendo ASINs: {e}")
            return []

    def _analyze_product(self, asin, category, scan_date):
        """
        Analiza un producto individual para determinar si es una oportunidad

        Returns:
            dict con datos de oportunidad o None si no es rentable
        """
        try:
            # 1. Obtener información del producto Amazon
            product_scraper = ProductInfoScraper(asin)
            product_data = product_scraper.scrape_product_info()

            if not product_data or not product_data.get('price'):
                logging.warning(f"No se pudo obtener precio para {asin}")
                return None

            amazon_price = product_data.get('price', 0)
            # BSR puede ser un diccionario o un número
            bsr_data = product_data.get('bsr', 999999)
            if isinstance(bsr_data, dict):
                bsr = bsr_data.get('rank', 999999) if bsr_data.get('rank', 0) > 0 else 999999
            else:
                bsr = bsr_data if bsr_data > 0 else 999999
            product_name = product_data.get('title', f'Product {asin}')

            # Estimar ventas mensuales
            sales_data = estimate_monthly_sales(bsr, category, amazon_price)
            estimated_sales = sales_data.get('estimated_units', 0) if sales_data else 0

            # 1.5. Validar cumplimiento FBA
            checker = FBARulesChecker()
            fba_check = checker.check_product(
                product_name=product_name,
                category=category,
                price=amazon_price,
                weight_lbs=product_data.get('weight', {}).get('value', 0),
                dimensions=product_data.get('dimensions', {}),
                bsr=bsr,
                review_count=product_data.get('review_count', 0)
            )

            # Obtener size tier del check de FBA
            size_check = checker._check_size_limits(
                product_data.get('weight', {}).get('value', 0),
                product_data.get('dimensions', {})
            )
            fba_size_tier = size_check.get('tier', 'Unknown')

            # Log FBA compliance
            if not fba_check['is_compliant']:
                logging.warning(f"FBA Compliance: Producto tiene {len(fba_check['violations'])} violaciones")
                for violation in fba_check['violations']:
                    logging.warning(f"  - {violation['message']}")
            if fba_check.get('warnings'):
                logging.info(f"FBA Warnings: {len(fba_check['warnings'])} advertencias")
                for warning in fba_check['warnings']:
                    logging.info(f"  - {warning['message']}")

            # 2. Buscar en proveedores (versión RÁPIDA para escaneo automático)
            supplier_scraper = SupplierScraper(product_name, asin)
            supplier_results = supplier_scraper.get_best_supplier_price_fast()  # Usa búsqueda rápida

            # Generar URLs de búsqueda para TODOS los proveedores
            search_query = product_name.replace(' ', '+')
            all_supplier_urls = {
                'aliexpress': {
                    'name': 'AliExpress',
                    'url': f"https://www.aliexpress.com/wholesale?SearchText={search_query}",
                    'icon': '🇨🇳'
                },
                'ebay': {
                    'name': 'eBay',
                    'url': f"https://www.ebay.com/sch/i.html?_nkw={search_query}",
                    'icon': '🛒'
                },
                'walmart': {
                    'name': 'Walmart',
                    'url': f"https://www.walmart.com/search?q={search_query}",
                    'icon': '🏪'
                },
                'target': {
                    'name': 'Target',
                    'url': f"https://www.target.com/s?searchTerm={search_query}",
                    'icon': '🎯'
                }
            }

            # Si no hay resultados reales, usar estimación
            if not supplier_results or not supplier_results.get('best_option'):
                estimator = SupplierPriceEstimator()
                estimation = estimator.estimate_supplier_price(amazon_price)
                supplier_price = estimation['total_estimated']

                supplier_info = {
                    'supplier': 'Estimado (AliExpress)',
                    'price': estimation['estimated_price'],
                    'shipping': estimation['estimated_shipping'],
                    'total': supplier_price,
                    'url': all_supplier_urls['aliexpress']['url'],  # URL de búsqueda en AliExpress
                    'moq': 1
                }
            else:
                best = supplier_results['best_option']
                supplier_price = best.get('total', 0)
                supplier_info = best

            # Si el precio de proveedor es 0 o >= precio Amazon, no es oportunidad
            if supplier_price == 0 or supplier_price >= amazon_price:
                return None

            # 3. Calcular FBA fees y ganancia
            cost_data = {
                'product_cost': supplier_info.get('price', supplier_price * 0.85),
                'shipping_cost': supplier_info.get('shipping', supplier_price * 0.15),
                'month': 1
            }

            calculator = FBACalculator(product_data, cost_data)
            fba_calculation = calculator.calculate_all()

            net_profit = fba_calculation['net_profit']
            roi_percent = fba_calculation['roi_percent']
            margin_percent = fba_calculation['margin_percent']

            # 4. Calcular competitividad
            competitiveness = self._calculate_competitiveness_score(
                roi_percent,
                net_profit,
                supplier_price / amazon_price if amazon_price > 0 else 1
            )

            # 5. Preparar datos de oportunidad
            opportunity = {
                'asin': asin,
                'product_name': product_name[:200],  # Limitar longitud
                'category': category,
                'amazon_price': amazon_price,
                'bsr': bsr,
                'estimated_monthly_sales': estimated_sales,
                'supplier_name': supplier_info.get('supplier', 'Unknown'),
                'supplier_price': supplier_price,
                'supplier_url': supplier_info.get('url', ''),
                'supplier_moq': supplier_info.get('moq', 1),
                'all_supplier_urls': json.dumps(all_supplier_urls),  # URLs de los 4 proveedores
                'total_cost': fba_calculation['total_cost'],
                'amazon_fees': fba_calculation['total_fees'],
                'net_profit': net_profit,
                'roi_percent': roi_percent,
                'margin_percent': margin_percent,
                'competitiveness_score': competitiveness['score'],
                'competitiveness_level': competitiveness['level'],
                'scan_date': scan_date,
                'amazon_url': product_data.get('product_url'),
                'image_url': product_data.get('image_url'),
                'supplier_image_url': supplier_info.get('image_url'),
                # FBA Compliance fields
                'fba_compliant': fba_check['is_compliant'],
                'fba_warnings': json.dumps(fba_check.get('violations', []) + fba_check.get('warnings', [])),
                'fba_size_tier': fba_size_tier,
                'product_length': product_data.get('dimensions', {}).get('length', 0),
                'product_width': product_data.get('dimensions', {}).get('width', 0),
                'product_height': product_data.get('dimensions', {}).get('height', 0),
                'product_weight': product_data.get('weight', {}).get('value', 0),
                'product_rating': product_data.get('rating', 0),
                'review_count': product_data.get('review_count', 0)
            }

            return opportunity

        except Exception as e:
            logging.error(f"Error analizando producto {asin}: {e}")
            return None

    def _calculate_competitiveness_score(self, roi, profit, supplier_ratio):
        """Calcula score de competitividad 0-100"""
        score = 0

        # ROI (40 puntos)
        if roi >= 50:
            score += 40
        elif roi >= 30:
            score += 30
        elif roi >= 15:
            score += 20
        else:
            score += 5

        # Profit (30 puntos)
        if profit >= 15:
            score += 30
        elif profit >= 10:
            score += 20
        elif profit >= 5:
            score += 10

        # Supplier ratio (30 puntos)
        if supplier_ratio <= 0.30:
            score += 30
        elif supplier_ratio <= 0.40:
            score += 20
        elif supplier_ratio <= 0.50:
            score += 10

        # Nivel
        if score >= 80:
            level = '🟢 EXCELENTE'
        elif score >= 60:
            level = '🟡 BUENO'
        elif score >= 40:
            level = '🟠 REGULAR'
        else:
            level = '🔴 BAJO'

        return {'score': score, 'level': level}

    def get_opportunities_dashboard(self, min_roi=5, min_profit=3):
        """Obtiene dashboard de oportunidades"""
        opportunities = self.db.get_opportunities(min_roi=min_roi, min_profit=min_profit)
        stats = self.db.get_stats()

        return {
            'opportunities': opportunities,
            'stats': stats
        }


def run_daily_scan():
    """Función para ejecutar el escaneo diario (llamada por scheduler)"""
    logging.info("🔄 Ejecutando escaneo diario programado...")

    scanner = ProductDiscoveryScanner()
    results = scanner.scan_best_sellers(max_products_per_category=20)

    logging.info(f"✅ Escaneo diario completado: {results}")
    return results
