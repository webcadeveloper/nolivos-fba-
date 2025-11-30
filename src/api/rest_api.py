"""
REST API - Endpoints completos para integraciones con n8n, Zapier, Make, etc.
Proporciona acceso programático a todas las funcionalidades
"""
from flask import Blueprint, jsonify, request
import logging
from functools import wraps
import secrets
import sqlite3
from datetime import datetime

logging.basicConfig(level=logging.INFO)

# Blueprint para la API
api_bp = Blueprint('api', __name__, url_prefix='/api/v1')


# ==================== AUTENTICACIÓN ====================

def init_api_keys_db(db_path='api_keys.db'):
    """Inicializa base de datos de API keys"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS api_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            api_key TEXT UNIQUE NOT NULL,
            name TEXT,
            permissions TEXT DEFAULT 'read',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_used TIMESTAMP,
            is_active BOOLEAN DEFAULT 1
        )
    ''')

    # Crear API key por defecto si no existe
    cursor.execute("SELECT COUNT(*) FROM api_keys")
    if cursor.fetchone()[0] == 0:
        default_key = secrets.token_urlsafe(32)
        cursor.execute('''
            INSERT INTO api_keys (api_key, name, permissions)
            VALUES (?, ?, ?)
        ''', (default_key, 'Default Key', 'read,write'))
        logging.info(f"🔑 API Key creada: {default_key}")
        print(f"\n{'='*60}")
        print(f"🔑 TU API KEY (GUÁRDALA): {default_key}")
        print(f"{'='*60}\n")

    conn.commit()
    conn.close()


def require_api_key(f):
    """Decorator para validar API key"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key') or request.args.get('api_key')

        if not api_key:
            return jsonify({'error': 'API key requerida'}), 401

        # Validar API key
        conn = sqlite3.connect('api_keys.db')
        cursor = conn.cursor()
        cursor.execute('''
            SELECT permissions FROM api_keys
            WHERE api_key = ? AND is_active = 1
        ''', (api_key,))

        result = cursor.fetchone()

        if not result:
            conn.close()
            return jsonify({'error': 'API key inválida'}), 401

        # Actualizar last_used
        cursor.execute('''
            UPDATE api_keys SET last_used = CURRENT_TIMESTAMP
            WHERE api_key = ?
        ''', (api_key,))
        conn.commit()
        conn.close()

        return f(*args, **kwargs)

    return decorated_function


# ==================== ENDPOINTS ====================

@api_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'version': '1.0.0',
        'timestamp': datetime.now().isoformat()
    })


@api_bp.route('/opportunities', methods=['GET'])
@require_api_key
def get_opportunities_api():
    """
    GET /api/v1/opportunities

    Query params:
        - min_roi: ROI mínimo (default: 5)
        - min_profit: Ganancia mínima (default: 3)
        - limit: Número de resultados (default: 100)
        - category: Filtrar por categoría
    """
    from src.analyzers.product_discovery import OpportunityDatabase

    min_roi = float(request.args.get('min_roi', 5))
    min_profit = float(request.args.get('min_profit', 3))
    limit = int(request.args.get('limit', 100))
    category = request.args.get('category')

    db = OpportunityDatabase()
    opportunities = db.get_opportunities(min_roi=min_roi, min_profit=min_profit, limit=limit)

    # Filtrar por categoría si se especifica
    if category:
        opportunities = [o for o in opportunities if o.get('category') == category]

    return jsonify({
        'success': True,
        'count': len(opportunities),
        'data': opportunities,
        'filters': {
            'min_roi': min_roi,
            'min_profit': min_profit,
            'category': category
        }
    })


@api_bp.route('/opportunities/<string:asin>', methods=['GET'])
@require_api_key
def get_opportunity_by_asin(asin):
    """GET /api/v1/opportunities/{asin}"""
    from src.analyzers.product_discovery import OpportunityDatabase

    db = OpportunityDatabase()
    opps = db.get_opportunities(min_roi=0, min_profit=0, limit=1000)

    opportunity = next((o for o in opps if o['asin'] == asin), None)

    if opportunity:
        return jsonify({
            'success': True,
            'data': opportunity
        })
    else:
        return jsonify({
            'success': False,
            'error': 'Oportunidad no encontrada'
        }), 404


@api_bp.route('/alerts', methods=['GET'])
@require_api_key
def get_alerts_api():
    """
    GET /api/v1/alerts

    Query params:
        - unread_only: Solo no leídas (default: true)
        - severity: Filtrar por severidad (high/medium/low)
        - limit: Número de resultados
    """
    from src.utils.alert_system import AlertSystem

    unread_only = request.args.get('unread_only', 'true').lower() == 'true'
    severity = request.args.get('severity')
    limit = int(request.args.get('limit', 50))

    alert_system = AlertSystem()

    if unread_only:
        alerts = alert_system.get_unread_alerts(limit=limit)
    else:
        # Obtener todas (implementar en alert_system si es necesario)
        alerts = alert_system.get_unread_alerts(limit=limit)

    # Filtrar por severity
    if severity:
        alerts = [a for a in alerts if a.get('severity') == severity]

    return jsonify({
        'success': True,
        'count': len(alerts),
        'data': alerts
    })


@api_bp.route('/trends', methods=['GET'])
@require_api_key
def get_trends_api():
    """GET /api/v1/trends - Productos en tendencia"""
    from src.utils.bsr_tracker import BSRTracker

    limit = int(request.args.get('limit', 20))

    bsr_tracker = BSRTracker()
    trending = bsr_tracker.get_trending_products(limit=limit)

    return jsonify({
        'success': True,
        'count': len(trending),
        'data': trending
    })


@api_bp.route('/categories/hot', methods=['GET'])
@require_api_key
def get_hot_categories_api():
    """GET /api/v1/categories/hot - Categorías más calientes"""
    from src.utils.bsr_tracker import BSRTracker

    bsr_tracker = BSRTracker()
    hot_categories = bsr_tracker.get_hot_categories()

    return jsonify({
        'success': True,
        'count': len(hot_categories),
        'data': hot_categories
    })


@api_bp.route('/scan/manual', methods=['POST'])
@require_api_key
def trigger_manual_scan():
    """
    POST /api/v1/scan/manual

    Body:
        {
            "max_products_per_category": 10
        }
    """
    from src.analyzers.product_discovery import ProductDiscoveryScanner

    data = request.get_json() or {}
    max_products = data.get('max_products_per_category', 10)

    scanner = ProductDiscoveryScanner()

    # Ejecutar en background (implementar con threading si es necesario)
    try:
        results = scanner.scan_best_sellers(max_products_per_category=max_products)

        return jsonify({
            'success': True,
            'message': 'Escaneo completado',
            'results': results
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/analyze', methods=['POST'])
@require_api_key
def analyze_product_api():
    """
    POST /api/v1/analyze

    Body:
        {
            "asin": "B08XYZ123",
            "url": "https://amazon.com/dp/B08XYZ123"  (opcional)
        }
    """
    from src.scrapers.product_info import ProductInfoScraper
    from src.analyzers.profit_analyzer import ProfitAnalyzer

    data = request.get_json()

    if not data or 'asin' not in data:
        return jsonify({'success': False, 'error': 'ASIN requerido'}), 400

    asin = data['asin']

    try:
        # Scrape product info
        scraper = ProductInfoScraper(asin)
        product_data = scraper.scrape_product_info()

        if not product_data:
            return jsonify({
                'success': False,
                'error': 'No se pudo obtener información del producto'
            }), 404

        # Analyze profitability
        profit_analyzer = ProfitAnalyzer(asin, product_data.get('title'))
        analysis = profit_analyzer.analyze_full_profit()

        return jsonify({
            'success': True,
            'data': analysis
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/stats', methods=['GET'])
@require_api_key
def get_stats_api():
    """GET /api/v1/stats - Estadísticas generales"""
    from src.analyzers.product_discovery import OpportunityDatabase
    from src.utils.alert_system import AlertSystem

    opp_db = OpportunityDatabase()
    alert_system = AlertSystem()

    opp_stats = opp_db.get_stats()
    alert_summary = alert_system.get_alert_summary()

    return jsonify({
        'success': True,
        'data': {
            'opportunities': opp_stats,
            'alerts': alert_summary,
            'timestamp': datetime.now().isoformat()
        }
    })


@api_bp.route('/export/opportunities', methods=['GET'])
@require_api_key
def export_opportunities_api():
    """
    GET /api/v1/export/opportunities?format=csv

    Query params:
        - format: csv, json (default: json)
        - min_roi: Filtro ROI
        - min_profit: Filtro ganancia
    """
    from src.analyzers.product_discovery import OpportunityDatabase
    import csv
    import io
    from flask import make_response

    format_type = request.args.get('format', 'json').lower()
    min_roi = float(request.args.get('min_roi', 5))
    min_profit = float(request.args.get('min_profit', 3))

    db = OpportunityDatabase()
    opportunities = db.get_opportunities(min_roi=min_roi, min_profit=min_profit)

    if format_type == 'csv':
        # Generate CSV
        output = io.StringIO()

        if opportunities:
            fieldnames = opportunities[0].keys()
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(opportunities)

        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'text/csv'
        response.headers['Content-Disposition'] = f'attachment; filename=opportunities_{datetime.now().strftime("%Y%m%d")}.csv'

        return response

    else:
        # Return JSON
        return jsonify({
            'success': True,
            'count': len(opportunities),
            'data': opportunities
        })


# ==================== WEBHOOKS ====================

@api_bp.route('/webhooks/register', methods=['POST'])
@require_api_key
def register_webhook():
    """
    POST /api/v1/webhooks/register

    Body:
        {
            "url": "https://n8n.ejemplo.com/webhook/xxx",
            "events": ["opportunity_found", "price_alert", "bsr_change"],
            "name": "n8n Production"
        }
    """
    data = request.get_json()

    if not data or 'url' not in data:
        return jsonify({'success': False, 'error': 'URL requerida'}), 400

    # Guardar webhook en DB
    conn = sqlite3.connect('webhooks.db')
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS webhooks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT NOT NULL,
            events TEXT,
            name TEXT,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        INSERT INTO webhooks (url, events, name)
        VALUES (?, ?, ?)
    ''', (
        data['url'],
        ','.join(data.get('events', [])),
        data.get('name', 'Webhook')
    ))

    webhook_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return jsonify({
        'success': True,
        'webhook_id': webhook_id,
        'message': 'Webhook registrado exitosamente'
    })


@api_bp.route('/webhooks', methods=['GET'])
@require_api_key
def list_webhooks():
    """GET /api/v1/webhooks - Lista webhooks registrados"""
    conn = sqlite3.connect('webhooks.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        cursor.execute('SELECT * FROM webhooks WHERE is_active = 1')
        webhooks = [dict(row) for row in cursor.fetchall()]
    except:
        webhooks = []

    conn.close()

    return jsonify({
        'success': True,
        'count': len(webhooks),
        'data': webhooks
    })


# Inicializar DB de API keys al importar
init_api_keys_db()
