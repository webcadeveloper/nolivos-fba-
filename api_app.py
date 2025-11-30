"""
NOLIVOS FBA - REST API Backend
==============================
Pure REST API for Angular Frontend

Author: Hector Nolivos
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import logging
import os
import sys

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s:%(levelname)s:%(message)s",
)

# Añadir src al path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.analyzers.product_discovery import ProductDiscoveryScanner, OpportunityDatabase

app = Flask(__name__)

# Configurar CORS - Permitir peticiones desde Angular (WSL + Windows)
CORS(app, resources={
    r"/api/*": {
        "origins": ["http://localhost:4200", "http://localhost:4994", "http://127.0.0.1:4200"],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

# ==================== API ENDPOINTS ====================

@app.route("/api/health", methods=["GET"])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "NOLIVOS FBA API",
        "version": "2.0.0"
    })


@app.route("/api/opportunities", methods=["GET"])
def get_opportunities():
    """Get all opportunities with optional filters"""
    try:
        min_roi = float(request.args.get("min_roi", 5))
        min_profit = float(request.args.get("min_profit", 3))
        limit = int(request.args.get("limit", 100))

        scanner = ProductDiscoveryScanner()
        dashboard_data = scanner.get_opportunities_dashboard(
            min_roi=min_roi,
            min_profit=min_profit
        )

        # Limitar resultados
        opportunities = dashboard_data['opportunities'][:limit]

        return jsonify({
            "success": True,
            "data": {
                "opportunities": opportunities,
                "stats": dashboard_data['stats'],
                "total_count": len(opportunities)
            }
        })

    except Exception as e:
        logging.error(f"Error en /api/opportunities: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/opportunities/<int:opportunity_id>", methods=["GET"])
def get_opportunity_by_id(opportunity_id):
    """Get single opportunity by ID"""
    try:
        db = OpportunityDatabase()
        # TODO: Implementar get_opportunity_by_id en OpportunityDatabase
        return jsonify({
            "success": True,
            "data": {
                "id": opportunity_id,
                "message": "Single opportunity endpoint - TODO"
            }
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/stats", methods=["GET"])
def get_stats():
    """Get dashboard statistics"""
    try:
        db = OpportunityDatabase()
        stats = db.get_stats()

        return jsonify({
            "success": True,
            "data": stats
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/scan/start", methods=["POST"])
def start_scan():
    """Start product scanning process"""
    from threading import Thread
    from src.analyzers.parallel_product_scanner import get_global_scanner

    try:
        data = request.get_json() or {}
        max_products = int(data.get("max_products_per_category", 10))
        max_workers = int(data.get("max_workers", 20))

        scanner = get_global_scanner(max_workers=max_workers)

        def run_scan():
            try:
                scanner.scan_best_sellers_parallel(
                    max_products_per_category=max_products
                )
            except Exception as e:
                logging.error(f"Error en background scan: {e}")

        scan_thread = Thread(target=run_scan, daemon=True)
        scan_thread.start()

        return jsonify({
            "success": True,
            "message": "Scan started in background",
            "params": {
                "max_products_per_category": max_products,
                "max_workers": max_workers
            }
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/scan/progress", methods=["GET"])
def get_scan_progress():
    """Get current scan progress"""
    from src.analyzers.parallel_product_scanner import get_global_scanner

    try:
        scanner = get_global_scanner()
        stats = scanner.get_progress_stats()

        return jsonify({
            "success": True,
            "data": stats
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "data": {
                "total_products": 0,
                "products_scanned": 0,
                "opportunities_found": 0,
                "errors": 0,
                "progress_percent": 0
            }
        })


@app.route("/api/scan/logs", methods=["GET"])
def get_scan_logs():
    """Get recent scan logs"""
    from src.analyzers.parallel_product_scanner import get_global_scanner

    try:
        max_logs = int(request.args.get("max_logs", 50))
        scanner = get_global_scanner()
        logs = scanner.get_recent_logs(max_logs=max_logs)

        return jsonify({
            "success": True,
            "data": {
                "logs": logs
            }
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "data": {
                "logs": []
            }
        })


@app.route("/api/export/opportunities/csv", methods=["GET"])
def export_opportunities_csv():
    """Export opportunities to CSV"""
    try:
        from src.utils.export_manager import ExportManager
        from datetime import datetime

        min_roi = float(request.args.get('min_roi', 5))
        min_profit = float(request.args.get('min_profit', 3))

        db = OpportunityDatabase()
        opportunities = db.get_opportunities(min_roi=min_roi, min_profit=min_profit)

        csv_content = ExportManager.export_opportunities_to_csv(opportunities)

        return ExportManager.create_download_response(
            csv_content,
            f"oportunidades_{datetime.now().strftime('%Y%m%d')}.csv"
        )

    except Exception as e:
        logging.error(f"Error en export CSV: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/export/opportunities/excel", methods=["GET"])
def export_opportunities_excel():
    """Export opportunities to Excel"""
    try:
        from src.utils.export_manager import ExportManager
        from datetime import datetime
        import tempfile
        import os

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


if __name__ == "__main__":
    print("=" * 70)
    print("NOLIVOS FBA - REST API Backend")
    print("=" * 70)
    print()
    print("API running on: http://localhost:5000")
    print("Angular frontend should run on: http://localhost:4200")
    print()
    print("Available endpoints:")
    print("  GET  /api/health")
    print("  GET  /api/opportunities")
    print("  GET  /api/stats")
    print("  POST /api/scan/start")
    print("  GET  /api/scan/progress")
    print("  GET  /api/scan/logs")
    print("  GET  /api/export/opportunities/csv")
    print("  GET  /api/export/opportunities/excel")
    print()
    print("=" * 70)

    app.run(debug=True, port=5000, host='0.0.0.0')
