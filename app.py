"""
NOLIVOS FBA - Amazon Product Research Tool
===========================================

Author: Hector Nolivos
Email: hector@nolivos.cloud
Website: https://nolivos.cloud
Domain: https://fba.nolivos.cloud

Copyright (c) 2024 Hector Nolivos
Licensed under MIT License

Nolivos Law & Technology
"""

from flask import Flask, render_template, request, jsonify, send_file, url_for, redirect
import amzscraper as amz_scraper
import openaianalyzer as review_analyzer
import os
import sys
import re
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s:%(levelname)s:%(message)s",
)

# Añadir src al path para imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.scrapers.product_info import ProductInfoScraper
from src.scrapers.competitor_scraper import CompetitorAnalyzer
from src.scrapers.buybox_scraper import BuyBoxScraper
from src.monitors.review_monitor import ReviewMonitor
from src.monitors.listing_monitor import ListingMonitor
from src.api.sp_api_client import SPAPIClient
from src.analyzers.fba_calculator import FBACalculator
from src.analyzers.sales_estimator import estimate_monthly_sales
from src.analyzers.profit_analyzer import ProfitAnalyzer
from src.utils.price_tracker import PriceTracker
from src.utils.scheduler import PriceScheduler
from src.analyzers.product_discovery import ProductDiscoveryScanner
from src.utils.bsr_tracker import BSRTracker
from src.analyzers.ai_trend_analyzer import AITrendAnalyzer
from src.utils.alert_system import AlertSystem
from src.utils.export_manager import ExportManager
from src.analyzers.keyword_research import KeywordResearcher
from src.analyzers.ppc_calculator import PPCCalculator
from src.analyzers.ppc_keyword_harvester import PPCKeywordHarvester
from src.analyzers.ppc_bid_optimizer import PPCBidOptimizer
from src.analyzers.ppc_campaign_manager import PPCCampaignManager
from src.monitors.stock_monitor import StockMonitor
from src.trackers.rank_tracker import RankTracker


# FIXED: Robust ASIN parser
def get_asin(url):
    """Extrae ASIN de URL de Amazon - maneja múltiples formatos"""

    # Log para debugging
    logging.info(f"Intentando extraer ASIN de URL: {url}")

    # Limpiar URL (remover espacios, etc.)
    url = url.strip()

    # Patrones regex para diferentes formatos de Amazon
    patterns = [
        r'/dp/([A-Z0-9]{10})',           # amazon.com/dp/B07XXXXX
        r'/gp/product/([A-Z0-9]{10})',   # amazon.com/gp/product/B07XXXXX
        r'/ASIN/([A-Z0-9]{10})',         # amazon.com/ASIN/B07XXXXX
        r'product/([A-Z0-9]{10})',       # amazon.com/product/B07XXXXX
        r'/d/([A-Z0-9]{10})',            # amazon.com/d/B07XXXXX
        r'amazon\.[a-z.]+/[^/]+/dp/([A-Z0-9]{10})',  # Con nombre de producto
        r'www\.amazon\.[a-z.]+/.*/([A-Z0-9]{10})',   # Cualquier formato con ASIN
        r'([A-Z0-9]{10})',               # Solo el ASIN si lo pegaron directo
    ]

    for pattern in patterns:
        match = re.search(pattern, url, re.IGNORECASE)
        if match:
            asin = match.group(1)
            # Validar que sea formato ASIN válido (10 caracteres alfanuméricos)
            if len(asin) == 10 and asin.isalnum():
                logging.info(f"ASIN extraído exitosamente: {asin}")
                return asin

    # Si no hay match, mostrar error con más contexto
    logging.error(f"No se pudo extraer ASIN de URL: {url}")
    raise ValueError(
        f"URL inválida: {url}\n\n"
        "Formatos válidos:\n"
        "- https://www.amazon.com/dp/B07XXXXXX\n"
        "- https://www.amazon.com/Product-Name/dp/B07XXXXXX\n"
        "- https://www.amazon.com/gp/product/B07XXXXXX\n"
        "- O simplemente pega el ASIN: B07XXXXXX"
    )


# check if the json file exists given asin
def is_json(asin):
    # check if the json file exists
    if os.path.exists(f"{asin}-reviews.json"):
        return True
    else:
        return False


def get_competitor_and_sales_data(asin):
    """
    Obtiene información de competidores y estimación de ventas para un producto.
    
    Args:
        asin (str): ASIN del producto
    
    Returns:
        tuple: (competitors_dict, sales_dict) o (None, None) en caso de error
    """
    competitors_data = None
    sales_data = None
    
    try:
        # Obtener información del producto (incluye BSR y precio)
        product_scraper = ProductInfoScraper(asin)
        product_data = product_scraper.scrape_product_info()
        
        # Si tenemos información del producto, calcular estimación de ventas
        if product_data and product_data.get('bsr'):
            bsr = product_data.get('bsr')
            category = product_data.get('category')
            price = product_data.get('price', 0.0)
            
            # Estimar ventas mensuales
            sales_data = estimate_monthly_sales(bsr, category, price)
        
        # Obtener información de competidores
        try:
            competitor_analyzer = CompetitorAnalyzer(asin)
            competitors_data = competitor_analyzer.get_competitor_data()
        except Exception as e:
            print(f"Error obteniendo datos de competidores: {e}")
            competitors_data = None
        
    except Exception as e:
        print(f"Error en get_competitor_and_sales_data: {e}")
    
    return competitors_data, sales_data


app = Flask(__name__)

# Registrar API REST
from src.api.rest_api import api_bp
app.register_blueprint(api_bp)


@app.route("/back", methods=["GET", "POST"])
def back():
    return render_template("home.html")


@app.route("/search", methods=["GET", "POST"])
def search():
    if request.method == "POST":
        search_term = request.form["product_name"]
        # Search Amazon with the search term
        searcher = amz_scraper.AmazonSearch(search_term)
        product_list = searcher.get_products()

        return render_template(
            "search.html", product_list=product_list, search_term=search_term
        )

    else:
        return render_template("home.html")


@app.route("/review-search/<string:asin>", methods=["POST"])
def review_search(asin):
    if request.method == "POST":

        product_asin = asin
        # check if the json file exists if not, scrape the reviews
        if not is_json(product_asin):
            # Scrape Amazon reviews
            scraper = amz_scraper.AmazonReviewScraper(product_asin, max_pages=2)
            scraper.get_all_reviews()
            # save the reviews to a json file as a copy
            scraper.save_to_json()
        else:
            print("File already exists")

        # Analyze reviews
        analyzer = review_analyzer.ReviewAnalyzer(product_asin)
        analyzer.load_reviews()
        summary = analyzer.generate_summary()
        pros_cons = analyzer.generate_pro_cons()
        buy_together = analyzer.generate_buy_together()

        recommendation = analyzer.generate_recommendation()

        # Obtener datos de competencia y ventas estimadas
        competitors, sales = get_competitor_and_sales_data(product_asin)

        # Obtener historial de precios si está disponible
        price_history_data = None
        try:
            price_history = tracker.get_price_history(product_asin, days=30)
            if price_history:
                price_history_data = {
                    'dates': [item['timestamp'] for item in price_history],
                    'prices': [item['price'] for item in price_history],
                    'bsr': [item['bsr'] for item in price_history]
                }
        except Exception as e:
            print(f"Error obteniendo historial de precios: {e}")

        # Análisis de rentabilidad (proveedores vs Amazon)
        profit_analysis = None
        try:
            profit_analyzer = ProfitAnalyzer(product_asin, analyzer.product_name)
            profit_analysis = profit_analyzer.analyze_full_profit()
            if not profit_analysis.get('success'):
                print(f"Error en profit analysis: {profit_analysis.get('error')}")
                profit_analysis = None
        except Exception as e:
            print(f"Error obteniendo análisis de rentabilidad: {e}")
            profit_analysis = None

        # Obtener estado de stock actual
        stock_status = None
        try:
            stock_status = stock_monitor.get_current_stock_status(product_asin)
        except Exception as e:
            logging.warning(f"Error obteniendo estado de stock: {e}")

        return render_template(
            "result.html",
            product_url="https://www.amazon.com/dp/" + asin,
            asin=asin,
            summary=summary,
            pros_cons=pros_cons,
            recommendation=recommendation,
            buy_together=buy_together,
            competitors=competitors,
            sales=sales,
            price_history=price_history_data,
            profit_analysis=profit_analysis,
            stock_status=stock_status,
        )

    else:
        return render_template("home.html")


@app.route("/analyze", methods=["GET", "POST"])
def analyze():
    if request.method == "POST":
        product_url = request.form["product_url"]
        # From url, get the asin (product identifier)
        product_asin = get_asin(product_url)

        # Show loading page with message that analysis takes 1-2 minutes
        return render_template("loading_simple.html", asin=product_asin, product_url=product_url)

    # GET request - redirect to home
    return redirect(url_for('home'))

@app.route("/result", methods=["GET"])
def analyze_result():
    """Route that actually does the analysis after loading page"""
    product_asin = request.args.get("asin")
    product_url = request.args.get("url", f"https://www.amazon.com/dp/{product_asin}")

    if not product_asin:
        return render_template("home.html", error="ASIN no proporcionado")

    # check if the json file exists if not, scrape the reviews
    if not is_json(product_asin):
        # Scrape Amazon reviews
        scraper = amz_scraper.AmazonReviewScraper(product_asin, max_pages=2)
        scraper.get_all_reviews()
        # save the reviews to a json file as a copy
        scraper.save_to_json()
    else:
        print("File already exists")

    # Analyze reviews
    analyzer = review_analyzer.ReviewAnalyzer(product_asin)
    analyzer.load_reviews()
    summary = analyzer.generate_summary()
    pros_cons = analyzer.generate_pro_cons()
    buy_together = analyzer.generate_buy_together()

    recommendation = analyzer.generate_recommendation()

    # Obtener datos de competencia y ventas estimadas
    competitors, sales = get_competitor_and_sales_data(product_asin)

    # Obtener historial de precios si está disponible
    price_history_data = None
    try:
        price_history = tracker.get_price_history(product_asin, days=30)
        if price_history:
            price_history_data = {
                'dates': [item['timestamp'] for item in price_history],
                'prices': [item['price'] for item in price_history],
                'bsr': [item['bsr'] for item in price_history]
            }
    except Exception as e:
        print(f"Error obteniendo historial de precios: {e}")

    # Análisis de rentabilidad (proveedores vs Amazon)
    profit_analysis = None
    try:
        profit_analyzer = ProfitAnalyzer(product_asin, analyzer.product_name)
        profit_analysis = profit_analyzer.analyze_full_profit()
        if not profit_analysis.get('success'):
            print(f"Error en profit analysis: {profit_analysis.get('error')}")
            profit_analysis = None
    except Exception as e:
        print(f"Error obteniendo análisis de rentabilidad: {e}")
        profit_analysis = None

    # Obtener estado de stock actual
    stock_status = None
    try:
        stock_status = stock_monitor.get_current_stock_status(product_asin)
    except Exception as e:
        logging.warning(f"Error obteniendo estado de stock: {e}")

    return render_template(
        "result.html",
        product_url=product_url,
        asin=product_asin,
        summary=summary,
        pros_cons=pros_cons,
        recommendation=recommendation,
        buy_together=buy_together,
        competitors=competitors,
        sales=sales,
        price_history=price_history_data,
        profit_analysis=profit_analysis,
        stock_status=stock_status,
    )


@app.route("/")
def home():
    return render_template("home.html")


@app.route("/product-info/<string:asin>", methods=["GET"])
def product_info(asin):
    """Obtiene información del producto para análisis FBA"""
    try:
        scraper = ProductInfoScraper(asin)
        data = scraper.scrape_product_info()
        
        if data:
            return jsonify(data)
        else:
            return jsonify({"error": "No se pudo obtener información del producto"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/calculate-fba", methods=["POST"])
def calculate_fba():
    """Calcula rentabilidad FBA"""
    try:
        # Obtener datos del formulario
        asin = request.form.get("asin")
        product_cost = float(request.form.get("product_cost", 0))
        shipping_cost = float(request.form.get("shipping_cost", 0))
        month = int(request.form.get("month", 1))
        
        # Scrape product info
        scraper = ProductInfoScraper(asin)
        product_data = scraper.scrape_product_info()
        
        if not product_data:
            return render_template("error.html", message="No se pudo obtener información del producto")
        
        # Calcular FBA
        cost_data = {
            "product_cost": product_cost,
            "shipping_cost": shipping_cost,
            "month": month
        }
        
        calculator = FBACalculator(product_data, cost_data)
        calculation = calculator.calculate_all()
        
        return render_template(
            "fba_result.html",
            product_data=product_data,
            calculation=calculation,
            summary=calculator.get_summary()
        )
        
    except Exception as e:
        return render_template("error.html", message=f"Error en cálculo FBA: {str(e)}")



# Inicializar tracker, scheduler, bsr_tracker, ai_analyzer, alert_system, stock_monitor
tracker = PriceTracker()
scheduler = PriceScheduler()
bsr_tracker = BSRTracker()
ai_analyzer = AITrendAnalyzer()
alert_system = AlertSystem()
stock_monitor = StockMonitor()


@app.route("/track-product/<string:asin>", methods=["POST"])
def track_product(asin):
    """Añade un producto al tracking de precios"""
    try:
        product_name = request.form.get("product_name", f"Product {asin}")
        tracker.track_product(asin, product_name)
        tracker.update_price(asin)  # Primera actualización inmediata
        return jsonify({"success": True, "message": f"Producto {asin} añadido al tracking"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/price-history/<string:asin>", methods=["GET"])
def price_history(asin):
    """Obtiene el historial de precios de un producto"""
    try:
        days = int(request.args.get("days", 30))
        history = tracker.get_price_history(asin, days)
        return jsonify(history)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/tracked-products", methods=["GET"])
def tracked_products():
    """Lista todos los productos trackeados"""
    try:
        products = tracker.get_tracked_products()
        return jsonify(products)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/opportunities", methods=["GET"])
def opportunities():
    """Muestra el dashboard de oportunidades de arbitraje"""
    try:
        min_roi = float(request.args.get("min_roi", 5))  # Reducido de 15% a 5%
        min_profit = float(request.args.get("min_profit", 3))  # Reducido de $5 a $3

        scanner = ProductDiscoveryScanner()
        dashboard_data = scanner.get_opportunities_dashboard(min_roi=min_roi, min_profit=min_profit)

        # Obtener fecha del último escaneo
        from datetime import datetime
        last_scan = None
        if dashboard_data['opportunities']:
            last_scan = dashboard_data['opportunities'][0].get('scan_date', 'Desconocido')

        response = app.make_response(render_template(
            "opportunities.html",
            opportunities=dashboard_data['opportunities'],
            stats=dashboard_data['stats'],
            last_scan_date=last_scan
        ))

        # Deshabilitar cache para siempre mostrar los datos más recientes
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'

        return response
    except Exception as e:
        logging.error(f"Error en opportunities: {e}")
        return render_template("opportunities.html", opportunities=[], stats={
            'total_opportunities': 0,
            'avg_roi': 0,
            'avg_profit': 0,
            'max_roi': 0,
            'max_profit': 0
        }, last_scan_date=None)


@app.route("/scan-products", methods=["GET"])
def scan_products():
    """Redirige a la página de escaneo con logs en tiempo real"""
    return render_template("scanning.html")


@app.route("/scan-products/start", methods=["POST"])
def start_scan():
    """Inicia un escaneo paralelo en background"""
    from threading import Thread
    from src.analyzers.parallel_product_scanner import get_global_scanner

    try:
        max_products = int(request.json.get("max_products_per_category", 10))
        max_workers = int(request.json.get("max_workers", 20))

        scanner = get_global_scanner(max_workers=max_workers)

        # Ejecutar escaneo en background thread
        def run_scan():
            try:
                scanner.scan_best_sellers_parallel(max_products_per_category=max_products)
            except Exception as e:
                logging.error(f"Error en background scan: {e}")

        scan_thread = Thread(target=run_scan, daemon=True)
        scan_thread.start()

        return jsonify({
            "success": True,
            "message": "Escaneo iniciado en background"
        })

    except Exception as e:
        logging.error(f"Error iniciando scan: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/scan-products/progress", methods=["GET"])
def scan_progress():
    """Obtiene el progreso actual del escaneo"""
    from src.analyzers.parallel_product_scanner import get_global_scanner

    try:
        scanner = get_global_scanner()
        stats = scanner.get_progress_stats()
        return jsonify(stats)
    except Exception as e:
        return jsonify({
            "total_products": 0,
            "products_scanned": 0,
            "opportunities_found": 0,
            "errors": 0,
            "progress_percent": 0,
            "elapsed_seconds": 0,
            "products_per_second": 0
        })


@app.route("/scan-products/logs", methods=["GET"])
def scan_logs():
    """Obtiene los logs recientes del escaneo"""
    from src.analyzers.parallel_product_scanner import get_global_scanner

    try:
        max_logs = int(request.args.get("max_logs", 50))
        scanner = get_global_scanner()
        logs = scanner.get_recent_logs(max_logs=max_logs)
        return jsonify({"logs": logs})
    except Exception as e:
        return jsonify({"logs": []})


@app.route("/trends", methods=["GET"])
def trends():
    """Dashboard de tendencias del mercado"""
    try:
        # Usar datos de opportunities en lugar de product_history que está vacío
        from src.analyzers.product_discovery import OpportunityDatabase

        opp_db = OpportunityDatabase()

        # Obtener mejores oportunidades como "trending products"
        opportunities = opp_db.get_opportunities(min_roi=0, min_profit=0, limit=20)

        # Convertir opportunities a formato esperado por template
        trending_products = []
        for opp in opportunities:
            trending_products.append({
                'product_name': opp.get('product_name', 'Producto'),
                'asin': opp.get('asin'),
                'category': opp.get('category', 'Sin categoría'),
                'current_price': opp.get('amazon_price', 0),
                'current_bsr': opp.get('bsr', 'N/A'),
                'bsr_trend': '↑ Improving',
                'demand_trend': 'High' if opp.get('roi_percent', 0) > 20 else 'Medium',
                'bsr_change_30d': f"{opp.get('roi_percent', 0):.1f}%",
                'opportunity_score': min(100, int(opp.get('roi_percent', 0) * 1.5)),
                'supplier_url': opp.get('supplier_url', ''),
                'supplier_name': opp.get('supplier_name', 'Ver proveedor'),
                'supplier_price': opp.get('supplier_price', 0)
            })

        # Agrupar por categorías
        categories = {}
        for opp in opportunities:
            cat = opp.get('category', 'Sin categoría')
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(opp)

        # Crear hot_categories
        hot_categories = []
        for cat, opps in categories.items():
            if opps:
                avg_roi = sum(o.get('roi_percent', 0) for o in opps) / len(opps)
                hot_categories.append({
                    'category': cat,
                    'trending_products': len(opps),
                    'avg_bsr_improvement': f"{avg_roi:.1f}%",
                    'avg_score': min(100, int(avg_roi * 1.5))
                })

        # Ordenar por score
        hot_categories.sort(key=lambda x: x['avg_score'], reverse=True)
        hot_categories = hot_categories[:10]  # Top 10

        # AI insights básicos
        ai_insights = None
        if hot_categories:
            top_cat = hot_categories[0]
            ai_insights = {
                'top_category': top_cat['category'],
                'reason': f"Esta categoría tiene {top_cat['trending_products']} oportunidades con un ROI promedio de {top_cat['avg_bsr_improvement']}",
                'seasonal_alert': 'Datos basados en oportunidades recientes del scanner'
            }

        return render_template(
            "trends.html",
            trending_products=trending_products,
            hot_categories=hot_categories,
            ai_insights=ai_insights
        )
    except Exception as e:
        logging.error(f"Error en trends: {e}")
        import traceback
        traceback.print_exc()
        return render_template(
            "trends.html",
            trending_products=[],
            hot_categories=[],
            ai_insights=None
        )


@app.route("/alerts", methods=["GET"])
def alerts():
    """Dashboard de alertas"""
    try:
        unread_alerts = alert_system.get_unread_alerts(limit=50)
        summary = alert_system.get_alert_summary()

        return render_template(
            "alerts.html",
            alerts=unread_alerts,
            summary=summary
        )
    except Exception as e:
        logging.error(f"Error en alerts: {e}")
        return render_template(
            "alerts.html",
            alerts=[],
            summary={
                'total_unread': 0,
                'high_priority': 0,
                'medium_priority': 0,
                'low_priority': 0
            }
        )


@app.route("/export/opportunities/csv", methods=["GET"])
def export_opportunities_csv():
    """Exporta oportunidades a CSV"""
    from src.analyzers.product_discovery import OpportunityDatabase

    min_roi = float(request.args.get('min_roi', 5))
    min_profit = float(request.args.get('min_profit', 3))

    db = OpportunityDatabase()
    opportunities = db.get_opportunities(min_roi=min_roi, min_profit=min_profit)

    csv_content = ExportManager.export_opportunities_to_csv(opportunities)

    return ExportManager.create_download_response(
        csv_content,
        f"oportunidades_{datetime.now().strftime('%Y%m%d')}.csv"
    )


@app.route("/export/opportunities/excel", methods=["GET"])
def export_opportunities_excel():
    """Exporta oportunidades a Excel con formato profesional"""
    from src.analyzers.product_discovery import OpportunityDatabase
    import tempfile
    import os

    try:
        min_roi = float(request.args.get('min_roi', 5))
        min_profit = float(request.args.get('min_profit', 3))

        db = OpportunityDatabase()
        opportunities = db.get_opportunities(min_roi=min_roi, min_profit=min_profit)

        if not opportunities:
            return jsonify({
                'success': False,
                'error': 'No hay oportunidades para exportar'
            }), 404

        # Crear archivo temporal
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx')
        temp_file.close()

        # Generar Excel profesional
        success = ExportManager.export_opportunities_to_excel(opportunities, temp_file.name)

        if success:
            filename = f"oportunidades_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
            response = ExportManager.create_excel_download_response(temp_file.name, filename)

            # Limpiar archivo temporal después de enviar
            @response.call_on_close
            def cleanup():
                try:
                    os.unlink(temp_file.name)
                except:
                    pass

            return response
        else:
            return jsonify({
                'success': False,
                'error': 'Error generando Excel. Verifica que openpyxl esté instalado.'
            }), 500

    except Exception as e:
        logging.error(f"Error en export excel: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route("/export/alerts/csv", methods=["GET"])
def export_alerts_csv():
    """Exporta alertas a CSV"""
    alerts = alert_system.get_unread_alerts(limit=1000)
    csv_content = ExportManager.export_alerts_to_csv(alerts)

    return ExportManager.create_download_response(
        csv_content,
        f"alertas_{datetime.now().strftime('%Y%m%d')}.csv"
    )


@app.route("/keywords/research", methods=["POST"])
def keyword_research():
    """Investiga keyword"""
    data = request.get_json()

    if not data or 'keyword' not in data:
        return jsonify({'error': 'Keyword requerido'}), 400

    keyword = data['keyword']

    researcher = KeywordResearcher()
    analysis = researcher.analyze_keyword_competition(keyword)
    suggestions = researcher.get_amazon_suggestions(keyword)
    long_tail = researcher.find_long_tail_keywords(keyword)

    return jsonify({
        'success': True,
        'keyword': keyword,
        'analysis': analysis,
        'suggestions': suggestions,
        'long_tail': long_tail
    })


@app.route("/ppc/calculate", methods=["POST"])
def calculate_ppc():
    """Calcula PPC"""
    data = request.get_json()

    if not data:
        return jsonify({'error': 'Datos requeridos'}), 400

    price = float(data.get('price', 0))
    cost = float(data.get('cost', 0))
    category = data.get('category', 'default')
    target_sales = int(data.get('target_sales_per_day', 10))
    conversion_rate = float(data.get('conversion_rate', 0.10))

    calculator = PPCCalculator(price, cost, category)
    analysis = calculator.full_ppc_analysis(target_sales, conversion_rate)

    return jsonify({
        'success': True,
        'analysis': analysis
    })


# ==================== WEBHOOKS MANAGEMENT ====================

@app.route("/webhooks", methods=["GET"])
def webhooks_dashboard():
    """Dashboard de webhooks"""
    import sqlite3

    conn = sqlite3.connect('webhooks.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM webhooks ORDER BY created_at DESC')
    webhooks = [dict(row) for row in cursor.fetchall()]

    cursor.execute('SELECT * FROM webhook_logs ORDER BY timestamp DESC LIMIT 50')
    logs = [dict(row) for row in cursor.fetchall()]

    conn.close()

    from src.api.n8n_webhooks import n8n_webhooks
    available_events = n8n_webhooks.get_all_events()

    return render_template(
        "webhooks.html",
        webhooks=webhooks,
        logs=logs,
        available_events=available_events
    )


@app.route("/webhooks/test/<int:webhook_id>", methods=["POST"])
def test_webhook(webhook_id):
    """Prueba un webhook enviando evento de prueba"""
    import sqlite3

    conn = sqlite3.connect('webhooks.db')
    cursor = conn.cursor()

    cursor.execute('SELECT url FROM webhooks WHERE id = ?', (webhook_id,))
    result = cursor.fetchone()
    conn.close()

    if not result:
        return jsonify({'error': 'Webhook no encontrado'}), 404

    webhook_url = result[0]

    from src.api.n8n_webhooks import n8n_webhooks
    test_result = n8n_webhooks.test_webhook(webhook_url)

    return jsonify(test_result)


@app.route("/webhooks/delete/<int:webhook_id>", methods=["DELETE"])
def delete_webhook(webhook_id):
    """Elimina un webhook"""
    import sqlite3

    conn = sqlite3.connect('webhooks.db')
    cursor = conn.cursor()

    cursor.execute('DELETE FROM webhooks WHERE id = ?', (webhook_id,))
    conn.commit()
    conn.close()

    return jsonify({'success': True, 'message': 'Webhook eliminado'})


@app.route("/webhooks/trigger-manual", methods=["POST"])
def trigger_manual_webhook():
    """Dispara manualmente un webhook de prueba"""
    data = request.get_json()

    if not data or 'event_type' not in data:
        return jsonify({'error': 'event_type requerido'}), 400

    event_type = data['event_type']

    # Datos de prueba según el tipo de evento
    test_data = {
        'opportunity_found': {
            'asin': 'B08TEST123',
            'product_name': 'Producto de Prueba',
            'amazon_price': 29.99,
            'supplier_price': 10.00,
            'supplier_name': 'AliExpress',
            'roi_percent': 75.5,
            'net_profit': 8.50,
            'category': 'test',
            'competitiveness_level': '🟢 EXCELENTE'
        },
        'high_roi_opportunity': {
            'asin': 'B08TEST123',
            'product_name': 'Producto de Prueba - ROI Alto',
            'roi_percent': 65.0,
            'net_profit': 12.00,
            'amazon_price': 39.99,
            'supplier_price': 15.00,
            'urgency': 'HIGH',
            'action_required': 'REVISAR INMEDIATAMENTE'
        },
        'price_drop': {
            'asin': 'B08TEST123',
            'product_name': 'Producto de Prueba',
            'source': 'amazon',
            'old_price': 29.99,
            'new_price': 24.99,
            'change_amount': 5.00,
            'change_percent': 16.7,
            'urgency': 'MEDIUM'
        }
    }

    # Obtener datos de prueba
    payload = test_data.get(event_type, {'test': True, 'message': f'Test event: {event_type}'})

    # Enviar evento
    from src.api.webhook_sender import webhook_sender
    webhook_sender.send_event(event_type, payload)

    return jsonify({
        'success': True,
        'message': f'Webhook {event_type} disparado',
        'payload': payload
    })


@app.route("/buybox/<string:asin>", methods=["GET"])
def get_buybox(asin):
    """Obtiene información actual del Buy Box para un ASIN"""
    try:
        scraper = BuyBoxScraper(asin)
        buybox_data = scraper.get_buybox_winner()
        
        if buybox_data:
            return jsonify({
                'success': True,
                'data': {
                    'asin': buybox_data['asin'],
                    'seller_name': buybox_data['seller_name'],
                    'price': buybox_data['price'],
                    'fulfillment': buybox_data['fulfillment'],
                    'availability': buybox_data['availability'],
                    'timestamp': buybox_data['timestamp'].isoformat()
                }
            })
        else:
            return jsonify({
                'success': False,
                'error': 'No se pudo obtener información del Buy Box'
            }), 404
            
    except Exception as e:
        logging.error(f"Error en /buybox/{asin}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route("/buybox/<string:asin>/history", methods=["GET"])
def get_buybox_history(asin):
    """Obtiene el historial de Buy Box para un ASIN"""
    try:
        days = int(request.args.get('days', 30))
        
        scraper = BuyBoxScraper(asin)
        history = scraper.get_buybox_history(days=days)
        
        return jsonify({
            'success': True,
            'asin': asin,
            'history': history,
            'count': len(history)
        })
        
    except Exception as e:
        logging.error(f"Error en /buybox/{asin}/history: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route("/reviews/<string:asin>", methods=["GET"])
def get_reviews(asin):
    """Obtiene reviews recientes de un producto"""
    try:
        monitor = ReviewMonitor(asin)
        
        # Scrape reviews recientes
        recent_reviews = monitor.scrape_recent_reviews(max_reviews=10)
        
        # Obtener stats
        stats = monitor.get_review_stats()
        
        # Obtener historial
        history = monitor.get_recent_reviews(limit=20)
        
        return jsonify({
            'success': True,
            'asin': asin,
            'recent_reviews': recent_reviews,
            'stats': stats,
            'history': history
        })
        
    except Exception as e:
        logging.error(f"Error en /reviews/{asin}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route("/reviews/<string:asin>/monitor", methods=["POST"])
def monitor_reviews(asin):
    """Ejecuta monitoreo de reviews y detecta alertas"""
    try:
        monitor = ReviewMonitor(asin)
        
        # Scrape y analizar
        reviews = monitor.scrape_recent_reviews(max_reviews=10)
        
        # Obtener stats actualizados
        stats = monitor.get_review_stats()
        
        # Guardar snapshot de rating
        if stats['total_reviews'] > 0:
            monitor.save_rating_snapshot(stats['avg_rating'], stats['total_reviews'])
        
        return jsonify({
            'success': True,
            'message': 'Monitoreo completado',
            'reviews_scraped': len(reviews),
            'stats': stats
        })
        
    except Exception as e:
        logging.error(f"Error en /reviews/{asin}/monitor: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route("/listing/<string:asin>/track", methods=["POST"])
def track_listing(asin):
    """Trackea cambios en el listing de un producto"""
    try:
        monitor = ListingMonitor(asin)
        result = monitor.track_listing_changes()
        
        if result:
            return jsonify({
                'success': True,
                'asin': result['asin'],
                'changes_detected': result['changes_detected'],
                'changes': result['changes']
            })
        else:
            return jsonify({
                'success': False,
                'error': 'No se pudo trackear el listing'
            }), 404
            
    except Exception as e:
        logging.error(f"Error en /listing/{asin}/track: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route("/listing-changes", methods=["GET"])
def listing_changes_dashboard():
    """Dashboard de cambios en listings"""
    try:
        # Obtener ASINs trackeados
        import sqlite3
        conn = sqlite3.connect('data/listing_snapshots.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT DISTINCT asin FROM listing_changes
            ORDER BY timestamp DESC
            LIMIT 50
        ''')
        
        asins = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        # Obtener cambios recientes para cada ASIN
        all_changes = []
        for asin in asins:
            monitor = ListingMonitor(asin)
            changes = monitor.get_change_history(days=7)
            
            for change in changes[:5]:  # Últimos 5 cambios por ASIN
                change['asin'] = asin
                all_changes.append(change)
        
        # Ordenar por timestamp
        all_changes.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return render_template(
            "listing_changes.html",
            changes=all_changes[:50]  # Mostrar últimos 50 cambios
        )
        
    except Exception as e:
        logging.error(f"Error en /listing-changes: {e}")
        return render_template("listing_changes.html", changes=[])


@app.route("/listing/<string:asin>/history", methods=["GET"])
def get_listing_history(asin):
    """Obtiene el historial de cambios de un listing"""
    try:
        days = int(request.args.get('days', 30))
        
        monitor = ListingMonitor(asin)
        history = monitor.get_change_history(days=days)
        
        return jsonify({
            'success': True,
            'asin': asin,
            'history': history,
            'count': len(history)
        })
        
    except Exception as e:
        logging.error(f"Error en /listing/{asin}/history: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ==================== SP-API ROUTES ====================

# Inicializar SP-API client (lazy loading)
sp_api_client = None

def get_sp_api_client():
    """Obtiene instancia de SP-API client (singleton)"""
    global sp_api_client
    if sp_api_client is None:
        sp_api_client = SPAPIClient()
    return sp_api_client


@app.route("/sp-api/status", methods=["GET"])
def sp_api_status():
    """Verifica si SP-API está configurado"""
    try:
        client = get_sp_api_client()
        is_configured = client.is_configured()
        
        return jsonify({
            'success': True,
            'configured': is_configured,
            'message': 'SP-API is configured' if is_configured else 'SP-API not configured. Add credentials to config/sp_api_config.json'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'configured': False,
            'error': str(e)
        })


@app.route("/sp-api/orders", methods=["GET"])
def sp_api_orders():
    """Obtiene órdenes del seller"""
    try:
        client = get_sp_api_client()
        
        if not client.is_configured():
            return jsonify({
                'success': False,
                'error': 'SP-API not configured'
            }), 400
        
        # Parámetros de fecha
        from datetime import datetime, timedelta
        end_date = datetime.now()
        start_date = end_date - timedelta(days=int(request.args.get('days', 7)))
        
        orders = client.get_orders(start_date, end_date)
        
        return jsonify({
            'success': True,
            'orders': orders
        })
        
    except Exception as e:
        logging.error(f"Error en /sp-api/orders: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route("/sp-api/fees/<string:asin>", methods=["GET"])
def sp_api_fees(asin):
    """Obtiene fees oficiales de Amazon para un ASIN"""
    try:
        client = get_sp_api_client()
        
        if not client.is_configured():
            return jsonify({
                'success': False,
                'error': 'SP-API not configured'
            }), 400
        
        price = float(request.args.get('price', 20.0))
        is_fba = request.args.get('is_fba', 'true').lower() == 'true'
        
        fees_data = client.get_product_fees(asin, price, is_fba)
        
        return jsonify({
            'success': True,
            'asin': asin,
            'fees': fees_data
        })
        
    except Exception as e:
        logging.error(f"Error en /sp-api/fees/{asin}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route("/sp-api/catalog/<string:asin>", methods=["GET"])
def sp_api_catalog(asin):
    """Obtiene información del catálogo de Amazon"""
    try:
        client = get_sp_api_client()
        
        if not client.is_configured():
            return jsonify({
                'success': False,
                'error': 'SP-API not configured'
            }), 400
        
        catalog_data = client.get_catalog_item(asin)
        
        return jsonify({
            'success': True,
            'asin': asin,
            'catalog': catalog_data
        })
        
    except Exception as e:
        logging.error(f"Error en /sp-api/catalog/{asin}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500



# ==================== RANK TRACKER ROUTES ====================

rank_tracker = RankTracker()

@app.route("/rank-tracker", methods=["GET"])
def rank_tracker_dashboard():
    """Dashboard de rank tracking"""
    try:
        # Obtener todas las keywords trackeadas
        tracked = rank_tracker.get_tracked_keywords()
        
        return render_template(
            "rank_tracker.html",
            tracked_keywords=tracked
        )
    except Exception as e:
        logging.error(f"Error en /rank-tracker: {e}")
        return render_template("rank_tracker.html", tracked_keywords=[])


@app.route("/rank-tracker/add", methods=["POST"])
def add_rank_tracking():
    """Añade una keyword para tracking"""
    try:
        data = request.get_json() if request.is_json else request.form
        
        asin = data.get('asin')
        keyword = data.get('keyword')
        
        if not asin or not keyword:
            return jsonify({
                'success': False,
                'error': 'ASIN and keyword are required'
            }), 400
        
        success = rank_tracker.add_keyword_to_track(asin, keyword)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Keyword "{keyword}" added for tracking'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to add keyword'
            }), 500
            
    except Exception as e:
        logging.error(f"Error en /rank-tracker/add: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route("/rank-tracker/<string:asin>", methods=["GET"])
def get_rank_tracker_asin(asin):
    """Obtiene ranks de un ASIN específico"""
    try:
        keywords = rank_tracker.get_tracked_keywords(asin=asin)
        
        return jsonify({
            'success': True,
            'asin': asin,
            'keywords': keywords
        })
        
    except Exception as e:
        logging.error(f"Error en /rank-tracker/{asin}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route("/rank-tracker/check/<string:asin>/<path:keyword>", methods=["POST"])
def check_rank_now(asin, keyword):
    """Checkea rank inmediatamente (manual)"""
    try:
        result = rank_tracker.track_keyword_rank(asin, keyword)
        
        if result:
            return jsonify({
                'success': True,
                'result': result
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to check rank'
            }), 500
            
    except Exception as e:
        logging.error(f"Error en /rank-tracker/check: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route("/rank-tracker/remove", methods=["DELETE"])
def remove_rank_tracking():
    """Remueve una keyword del tracking"""
    try:
        data = request.get_json()
        
        asin = data.get('asin')
        keyword = data.get('keyword')
        
        if not asin or not keyword:
            return jsonify({
                'success': False,
                'error': 'ASIN and keyword are required'
            }), 400
        
        success = rank_tracker.remove_keyword(asin, keyword)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Keyword "{keyword}" removed'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to remove keyword'
            }), 500
            
    except Exception as e:
        logging.error(f"Error en /rank-tracker/remove: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route("/rank-tracker/history/<string:asin>/<path:keyword>", methods=["GET"])
def get_rank_history(asin, keyword):
    """Obtiene historial de ranks para una keyword"""
    try:
        days = int(request.args.get('days', 30))
        
        history = rank_tracker.get_rank_history(asin, keyword, days=days)
        
        return jsonify({
            'success': True,
            'asin': asin,
            'keyword': keyword,
            'history': history
        })
        
    except Exception as e:
        logging.error(f"Error en /rank-tracker/history: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route("/bsr-chart/<string:asin>", methods=["GET"])
def bsr_chart(asin):
    """Muestra gráfico histórico de BSR y precio para un ASIN"""
    try:
        days = int(request.args.get('days', 30))
        
        # Obtener histórico de BSR
        bsr_history = bsr_tracker.get_history(asin, days=days)
        
        # Preparar datos para el template
        chart_data = {
            'dates': [],
            'bsr': [],
            'prices': []
        }
        
        product_name = 'Producto'
        
        if bsr_history:
            # Ordenar por fecha (más antiguo primero para el gráfico)
            sorted_history = sorted(bsr_history, key=lambda x: x.get('date', x.get('timestamp', '')))
            
            for entry in sorted_history:
                date_val = entry.get('date') or entry.get('timestamp', '')
                if date_val:
                    chart_data['dates'].append(date_val)
                    chart_data['bsr'].append(entry.get('bsr'))
                    chart_data['prices'].append(entry.get('amazon_price'))
            
            # Obtener nombre del producto del último registro
            if bsr_history:
                product_name = bsr_history[0].get('product_name', f'Producto {asin}')
        
        return render_template(
            'bsr_chart.html',
            asin=asin,
            product_name=product_name,
            chart_data=chart_data,
            days=days,
            has_data=len(bsr_history) > 0
        )
        
    except Exception as e:
        logging.error(f"Error en /bsr-chart/{asin}: {e}")
        return render_template(
            'bsr_chart.html',
            asin=asin,
            product_name=f'Producto {asin}',
            chart_data={'dates': [], 'bsr': [], 'prices': []},
            days=30,
            has_data=False,
            error=str(e)
        )


@app.route("/stock-history/<string:asin>", methods=["GET"])
def stock_history(asin):
    """Obtiene el historial de stock de un producto"""
    try:
        days = int(request.args.get('days', 30))
        history = stock_monitor.get_stock_history(asin, days=days)
        
        # Obtener estado actual
        current_status = stock_monitor.get_current_stock_status(asin)
        
        return jsonify({
            'success': True,
            'asin': asin,
            'current_status': current_status,
            'history': history,
            'count': len(history)
        })
        
    except Exception as e:
        logging.error(f"Error en /stock-history/{asin}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route("/check-stock/<string:asin>", methods=["POST"])
def check_stock(asin):
    """Verifica stock de un producto y guarda snapshot"""
    try:
        product_name = request.form.get("product_name", None)
        result = stock_monitor.check_stock_availability(asin, product_name)
        
        if result:
            return jsonify({
                'success': True,
                'status': result['status'],
                'quantity': result['quantity'],
                'message': f"Stock checked: {result['status']}"
            })
        else:
            return jsonify({
                'success': False,
                'error': 'No se pudo verificar el stock'
            }), 500
            
    except Exception as e:
        logging.error(f"Error checking stock for {asin}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ==================== PPC SUITE ROUTES ====================

# Inicializar PPC managers
ppc_campaign_manager = PPCCampaignManager()
ppc_keyword_harvester = PPCKeywordHarvester()
ppc_bid_optimizer = PPCBidOptimizer()


@app.route("/ppc/dashboard", methods=["GET"])
def ppc_dashboard():
    """Dashboard principal de PPC"""
    try:
        campaigns = ppc_campaign_manager.get_all_campaigns()
        
        # Calcular métricas totales
        total_spend = sum(c.get('total_spend', 0) for c in campaigns)
        total_revenue = sum(c.get('total_revenue', 0) for c in campaigns)
        total_sales = sum(c.get('total_sales', 0) for c in campaigns)
        
        overall_acos = (total_spend / total_revenue * 100) if total_revenue > 0 else 0
        overall_roas = (total_revenue / total_spend) if total_spend > 0 else 0
        
        return render_template(
            'ppc_dashboard.html',
            campaigns=campaigns,
            total_campaigns=len(campaigns),
            total_spend=round(total_spend, 2),
            total_revenue=round(total_revenue, 2),
            total_sales=total_sales,
            overall_acos=round(overall_acos, 2),
            overall_roas=round(overall_roas, 2)
        )
        
    except Exception as e:
        logging.error(f"Error en /ppc/dashboard: {e}")
        return render_template(
            'ppc_dashboard.html',
            campaigns=[],
            total_campaigns=0,
            total_spend=0,
            total_revenue=0,
            total_sales=0,
            overall_acos=0,
            overall_roas=0,
            error=str(e)
        )


@app.route("/ppc/harvest/<string:asin>", methods=["POST"])
def ppc_harvest_keywords(asin):
    """Harvest keywords de competidores para un ASIN"""
    try:
        max_competitors = int(request.form.get('max_competitors', 10))
        
        result = ppc_keyword_harvester.harvest_from_competitors(asin, max_competitors)
        
        if result.get('error'):
            return jsonify({
                'success': False,
                'error': result['error']
            }), 500
        
        return jsonify({
            'success': True,
            'asin': asin,
            'keywords_found': result['total_keywords_found'],
            'keywords': result['keywords'][:50],  # Top 50
            'harvested_from': result['harvested_from']
        })
        
    except Exception as e:
        logging.error(f"Error harvesting keywords for {asin}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route("/ppc/optimize", methods=["POST"])
def ppc_optimize_bids():
    """Optimiza bids de una campaña"""
    try:
        data = request.get_json()
        
        if not data or 'campaign_data' not in data:
            return jsonify({
                'success': False,
                'error': 'campaign_data is required'
            }), 400
        
        result = ppc_bid_optimizer.optimize_bids(data['campaign_data'])
        
        return jsonify({
            'success': True,
            'optimization': result
        })
        
    except Exception as e:
        logging.error(f"Error optimizing bids: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route("/ppc/keyword-suggestions", methods=["GET"])
def ppc_keyword_suggestions():
    """Obtiene sugerencias de keywords"""
    try:
        asin = request.args.get('asin')
        base_keyword = request.args.get('keyword')
        
        if not base_keyword:
            return jsonify({
                'success': False,
                'error': 'keyword parameter is required'
            }), 400
        
        # Usar KeywordResearcher para obtener sugerencias
        researcher = KeywordResearcher()
        suggestions = researcher.get_amazon_suggestions(base_keyword)
        long_tail = researcher.find_long_tail_keywords(base_keyword)
        
        # Analizar competencia
        analyzed = []
        for kw in suggestions[:10]:  # Analizar top 10
            analysis = researcher.analyze_keyword_competition(kw)
            if analysis:
                analyzed.append(analysis)
        
        return jsonify({
            'success': True,
            'base_keyword': base_keyword,
            'suggestions': suggestions[:20],
            'long_tail_keywords': long_tail[:10],
            'competition_analysis': analyzed
        })
        
    except Exception as e:
        logging.error(f"Error getting keyword suggestions: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route("/ppc/negative-keywords", methods=["POST"])
def ppc_negative_keywords():
    """Sugiere negative keywords basado en performance"""
    try:
        data = request.get_json()
        
        if not data or 'keywords' not in data:
            return jsonify({
                'success': False,
                'error': 'keywords list is required'
            }), 400
        
        min_ctr = float(data.get('min_ctr', 0.01))
        min_clicks = int(data.get('min_clicks', 10))
        
        result = ppc_keyword_harvester.get_negative_keywords(
            data['keywords'], min_ctr, min_clicks
        )
        
        return jsonify({
            'success': True,
            'negative_keywords': result
        })
        
    except Exception as e:
        logging.error(f"Error getting negative keywords: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route("/ppc/simulate", methods=["POST"])
def ppc_simulate_campaign():
    """Simula una campaña PPC"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'Campaign data is required'
            }), 400
        
        budget = float(data.get('budget', 100))
        target_acos = float(data.get('target_acos', 30))
        keywords = data.get('keywords', [])
        conversion_rate = float(data.get('conversion_rate', 0.10))
        product_price = float(data.get('product_price', 0))
        product_cost = float(data.get('product_cost', 0))
        category = data.get('category', 'default')
        
        if not product_price or not keywords:
            return jsonify({
                'success': False,
                'error': 'product_price and keywords are required'
            }), 400
        
        # Crear calculator y simular
        calculator = PPCCalculator(product_price, product_cost, category)
        result = calculator.simulate_campaign(budget, target_acos, keywords, conversion_rate)
        
        return jsonify({
            'success': True,
            'simulation': result
        })
        
    except Exception as e:
        logging.error(f"Error simulating campaign: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route("/ppc/campaign/<string:campaign_id>", methods=["GET"])
def ppc_get_campaign(campaign_id):
    """Obtiene datos de una campaña específica"""
    try:
        campaign = ppc_campaign_manager.get_campaign(campaign_id)
        keywords = ppc_campaign_manager.get_campaign_keywords(campaign_id)
        
        if not campaign:
            return jsonify({
                'success': False,
                'error': 'Campaign not found'
            }), 404
        
        return jsonify({
            'success': True,
            'campaign': campaign,
            'keywords': keywords
        })
        
    except Exception as e:
        logging.error(f"Error getting campaign {campaign_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


if __name__ == "__main__":
    # Iniciar scheduler en background
    scheduler.start()
    app.run(debug=True, port=4994)


