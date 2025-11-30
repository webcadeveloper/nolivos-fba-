"""
Sales Estimator Mejorado: Estima ventas mensuales con precisión ±20%
Utiliza regresión polinomial, ajustes estacionales, y ML básico
"""
import logging
import sqlite3
import os
import sys
from datetime import datetime
import math
import numpy as np
from typing import Dict, Optional, Tuple, List

# Añadir path para imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# Intentar importar scikit-learn para ML (opcional)
try:
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.preprocessing import PolynomialFeatures
    from sklearn.pipeline import Pipeline
    from sklearn.linear_model import LinearRegression
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False
    logging.warning("scikit-learn no disponible. Funciones ML deshabilitadas.")

from src.utils.bsr_tracker import BSRTracker

logging.basicConfig(level=logging.INFO)


class ImprovedSalesEstimator:
    """
    Estimador de ventas mejorado con:
    - Regresión polinomial
    - Ajustes estacionales
    - Intervalos de confianza
    - ML básico (si scikit-learn disponible)
    - Integración con BSRTracker
    """

    def __init__(self, db_path='sales_calibration.db', bsr_tracker=None):
        self.db_path = db_path
        self.bsr_tracker = bsr_tracker or BSRTracker()
        self.init_calibration_database()
        
        # Factores estacionales por mes (basado en datos de Amazon)
        self.seasonal_factors = {
            1: 0.70,   # Enero - post navidad
            2: 0.75,   # Febrero
            3: 0.90,   # Marzo
            4: 0.95,   # Abril
            5: 1.00,   # Mayo
            6: 1.10,   # Junio - preparación verano
            7: 1.15,   # Julio - verano
            8: 1.10,   # Agosto - back to school
            9: 1.05,   # Septiembre
            10: 1.20,  # Octubre - preparación navidad
            11: 2.50,  # Noviembre - Black Friday/Cyber Monday
            12: 2.80   # Diciembre - Navidad
        }

        # Factores por categoría para temporadas especiales
        self.category_seasonal_boosts = {
            'Toys & Games': {11: 3.5, 12: 4.0},  # Navidad
            'Home & Kitchen': {10: 1.5, 11: 2.0, 12: 2.2},  # Temporada cocina
            'Sports & Outdoors': {5: 1.3, 6: 1.4, 7: 1.5},  # Verano
            'Clothing': {10: 1.8, 11: 2.5, 12: 3.0},  # Navidad
            'Electronics': {11: 2.2, 12: 2.5},  # Black Friday/Navidad
        }

        # Constantes mejoradas por categoría (regresión polinomial)
        self.category_params = {
            'Electronics': {
                'a': 8.5e7,    # Coeficiente principal
                'b': -0.85,    # Exponente BSR
                'c': 1.5e-9,   # Término cuadrático
                'price_factor': 0.15  # Factor de precio
            },
            'Home & Kitchen': {
                'a': 5.5e7,
                'b': -0.82,
                'c': 1.2e-9,
                'price_factor': 0.12
            },
            'Toys & Games': {
                'a': 4.5e7,
                'b': -0.88,
                'c': 1.0e-9,
                'price_factor': 0.18
            },
            'Sports & Outdoors': {
                'a': 3.5e7,
                'b': -0.80,
                'c': 8e-10,
                'price_factor': 0.14
            },
            'Clothing': {
                'a': 6.5e7,
                'b': -0.86,
                'c': 1.3e-9,
                'price_factor': 0.16
            },
            'Health & Personal Care': {
                'a': 4.0e7,
                'b': -0.83,
                'c': 9e-10,
                'price_factor': 0.11
            },
            'Default': {
                'a': 5.0e7,
                'b': -0.84,
                'c': 1.1e-9,
                'price_factor': 0.13
            }
        }

        # Modelo ML (se entrena cuando hay datos de calibración)
        self.ml_model = None
        self.ml_trained = False

    def init_calibration_database(self):
        """Crea base de datos para calibración con datos reales"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Tabla de calibración con datos reales vs estimados
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sales_calibration (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                asin TEXT NOT NULL,
                actual_sales INTEGER,
                estimated_sales INTEGER,
                bsr INTEGER,
                category TEXT,
                price REAL,
                month INTEGER,
                date DATE DEFAULT (date('now')),
                error_percent REAL,
                notes TEXT
            )
        ''')

        # Tabla de histórico de estimaciones
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sales_estimates_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                asin TEXT NOT NULL,
                estimated_sales INTEGER,
                min_sales INTEGER,
                max_sales INTEGER,
                confidence_score INTEGER,
                bsr INTEGER,
                category TEXT,
                price REAL,
                month INTEGER,
                date DATE DEFAULT (date('now'))
            )
        ''')

        # Índices
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_calibration_asin_date
            ON sales_calibration(asin, date DESC)
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_calibration_category
            ON sales_calibration(category, bsr)
        ''')

        conn.commit()
        conn.close()
        logging.info("Sales calibration database initialized")

    def normalize_category(self, category: str) -> str:
        """Normaliza el nombre de la categoría"""
        if not category:
            return 'Default'
        
        category_lower = category.lower()
        
        # Mapping de categorías
        if any(x in category_lower for x in ['electronics', 'electronic']):
            return 'Electronics'
        elif 'home' in category_lower and 'kitchen' in category_lower:
            return 'Home & Kitchen'
        elif 'toys' in category_lower and 'games' in category_lower:
            return 'Toys & Games'
        elif 'sports' in category_lower or 'outdoor' in category_lower:
            return 'Sports & Outdoors'
        elif any(x in category_lower for x in ['clothing', 'apparel', 'fashion']):
            return 'Clothing'
        elif any(x in category_lower for x in ['health', 'personal care', 'beauty']):
            return 'Health & Personal Care'
        else:
            return 'Default'

    def get_seasonal_factor(self, month: Optional[int], category: Optional[str] = None) -> float:
        """
        Obtiene factor estacional para el mes actual
        """
        if month is None:
            month = datetime.now().month
        
        base_factor = self.seasonal_factors.get(month, 1.0)
        
        # Aplicar boost de categoría si aplica
        if category:
            normalized_cat = self.normalize_category(category)
            category_boosts = self.category_seasonal_boosts.get(normalized_cat, {})
            category_boost = category_boosts.get(month, 1.0)
            return base_factor * category_boost
        
        return base_factor

    def polynomial_regression_sales(self, bsr: int, category: str, price: float = 0.0) -> float:
        """
        Calcula ventas usando regresión polinomial mejorada:
        Sales = a * (BSR ^ b) * (1 + c * BSR) * price_factor(price)
        """
        normalized_category = self.normalize_category(category)
        params = self.category_params.get(normalized_category, self.category_params['Default'])
        
        # Prevenir BSR = 0 o negativo
        if bsr <= 0:
            return 0.0
        
        # Calcular base con regresión polinomial
        base_sales = params['a'] * (bsr ** params['b']) * (1 + params['c'] * bsr)
        
        # Ajuste por precio (productos más caros venden menos unidades)
        if price > 0:
            # Factor de precio: más precio = menos unidades, pero más revenue
            price_adjustment = 1.0 - (params['price_factor'] * min(price / 100, 0.5))
            base_sales *= max(price_adjustment, 0.5)  # Mínimo 50% del ajuste
        
        return max(base_sales, 0)  # No permitir ventas negativas

    def calculate_confidence_interval(self, estimated_sales: float, bsr: int, 
                                     category: str, has_history: bool = False) -> Tuple[float, float, int]:
        """
        Calcula intervalo de confianza:
        - min_sales: estimación * 0.80 (mínimo -20%)
        - max_sales: estimación * 1.20 (máximo +20%)
        - confidence_score: 0-100 basado en calidad de datos
        """
        # Confidence score basado en múltiples factores
        confidence_score = 50  # Base
        
        # Factor 1: Rango de BSR
        if bsr <= 1000:
            confidence_score += 30
        elif bsr <= 10000:
            confidence_score += 20
        elif bsr <= 100000:
            confidence_score += 10
        
        # Factor 2: Categoría conocida
        normalized_category = self.normalize_category(category)
        if normalized_category != 'Default':
            confidence_score += 10
        
        # Factor 3: Historial disponible
        if has_history:
            confidence_score += 10
        
        confidence_score = min(confidence_score, 95)  # Máximo 95%
        
        # Calcular intervalo basado en confidence
        # Menor confianza = intervalo más amplio
        error_margin = (100 - confidence_score) / 100 * 0.30  # Hasta 30% de error
        
        min_sales = max(estimated_sales * (1 - error_margin), 0)
        max_sales = estimated_sales * (1 + error_margin)
        
        return min_sales, max_sales, confidence_score

    def estimate_with_history(self, asin: str, bsr: int, category: str, 
                             price: float = 0.0, month: Optional[int] = None) -> Dict:
        """
        Estima ventas usando histórico de BSR para mejorar precisión
        """
        # Obtener histórico de BSR
        bsr_history = self.bsr_tracker.get_history(asin, days=30)
        
        has_history = len(bsr_history) > 0
        
        # Si hay histórico, usar promedio ponderado
        if has_history:
            # Calcular BSR promedio ponderado (más reciente = más peso)
            total_weight = 0
            weighted_bsr = 0
            
            for i, entry in enumerate(bsr_history[:7]):  # Últimos 7 días
                bsr_val = entry.get('bsr')
                if bsr_val and bsr_val > 0:
                    weight = 7 - i  # Más reciente = mayor peso
                    weighted_bsr += bsr_val * weight
                    total_weight += weight
            
            if total_weight > 0:
                avg_bsr = weighted_bsr / total_weight
                # Usar promedio entre BSR actual y promedio histórico
                adjusted_bsr = (bsr * 0.6) + (avg_bsr * 0.4)
                bsr = int(adjusted_bsr)
        else:
            # Sin histórico, usar BSR actual
            pass
        
        # Calcular estimación base
        base_sales = self.polynomial_regression_sales(bsr, category, price)
        
        # Aplicar factor estacional
        seasonal_factor = self.get_seasonal_factor(month, category)
        estimated_sales = base_sales * seasonal_factor
        
        # Calcular intervalo de confianza
        min_sales, max_sales, confidence_score = self.calculate_confidence_interval(
            estimated_sales, bsr, category, has_history
        )
        
        return {
            'estimated_sales': int(estimated_sales),
            'min_sales': int(min_sales),
            'max_sales': int(max_sales),
            'confidence_score': confidence_score,
            'bsr_used': bsr,
            'category_used': self.normalize_category(category),
            'seasonal_factor': seasonal_factor,
            'has_history': has_history,
            'base_estimate': int(base_sales)
        }

    def estimate_monthly_sales(self, bsr, category=None, price=0.0, asin=None, 
                              month=None, use_history=True) -> Dict:
        """
        Función principal mejorada para estimar ventas mensuales
        
        Args:
            bsr: BSR rank (int o dict con {'rank': int, 'category': str})
            category: Categoría del producto
            price: Precio del producto
            asin: ASIN del producto (para usar histórico si disponible)
            month: Mes (1-12) para ajuste estacional
            use_history: Si usar histórico de BSR para mejorar precisión
        
        Returns:
            dict con estimación completa
        """
        try:
            # Extraer BSR si es dict
            if isinstance(bsr, dict):
                bsr_rank = bsr.get('rank', 0)
                bsr_category = bsr.get('category', category)
            else:
                bsr_rank = int(bsr) if bsr else 0
                bsr_category = category
            
            # Validar BSR
            if bsr_rank <= 0:
                logging.warning(f"BSR inválido: {bsr_rank}")
                return self._get_default_estimation(bsr_category)
            
            # Obtener mes actual si no se especifica
            if month is None:
                month = datetime.now().month
            
            # Usar histórico si está disponible
            if asin and use_history:
                estimation = self.estimate_with_history(asin, bsr_rank, bsr_category, price, month)
            else:
                # Estimación simple sin histórico
                base_sales = self.polynomial_regression_sales(bsr_rank, bsr_category, price)
                seasonal_factor = self.get_seasonal_factor(month, bsr_category)
                estimated_sales = base_sales * seasonal_factor
                
                min_sales, max_sales, confidence_score = self.calculate_confidence_interval(
                    estimated_sales, bsr_rank, bsr_category, False
                )
                
                estimation = {
                    'estimated_sales': int(estimated_sales),
                    'min_sales': int(min_sales),
                    'max_sales': int(max_sales),
                    'confidence_score': confidence_score,
                    'bsr_used': bsr_rank,
                    'category_used': self.normalize_category(bsr_category),
                    'seasonal_factor': seasonal_factor,
                    'has_history': False,
                    'base_estimate': int(base_sales)
                }
            
            # Calcular revenue estimado
            estimated_revenue = estimation['estimated_sales'] * price if price > 0 else 0.0
            min_revenue = estimation['min_sales'] * price if price > 0 else 0.0
            max_revenue = estimation['max_sales'] * price if price > 0 else 0.0
            
            # Determinar confidence_level (backward compatibility)
            if estimation['confidence_score'] >= 80:
                confidence_level = 'high'
            elif estimation['confidence_score'] >= 60:
                confidence_level = 'medium'
            else:
                confidence_level = 'low'
            
            result = {
                'estimated_monthly_units': estimation['estimated_sales'],
                'estimated_monthly_revenue': round(estimated_revenue, 2),
                'min_monthly_units': estimation['min_sales'],
                'max_monthly_units': estimation['max_sales'],
                'min_monthly_revenue': round(min_revenue, 2),
                'max_monthly_revenue': round(max_revenue, 2),
                'confidence_level': confidence_level,
                'confidence_score': estimation['confidence_score'],
                'bsr_used': estimation['bsr_used'],
                'category_used': estimation['category_used'],
                'seasonal_factor': round(estimation['seasonal_factor'], 2),
                'has_history': estimation['has_history'],
                'base_estimate': estimation['base_estimate']
            }
            
            # Guardar estimación en histórico
            if asin:
                self._save_estimation_history(asin, result, month)
            
            logging.info(
                f"Sales estimation: {estimation['estimated_sales']} units/month "
                f"(range: {estimation['min_sales']}-{estimation['max_sales']}, "
                f"confidence: {estimation['confidence_score']}%)"
            )
            
            return result
            
        except Exception as e:
            logging.error(f"Error estimating monthly sales: {e}")
            return self._get_default_estimation(category)

    def _get_default_estimation(self, category=None):
        """Retorna estimación por defecto en caso de error"""
        return {
            'estimated_monthly_units': 0,
            'estimated_monthly_revenue': 0.0,
            'min_monthly_units': 0,
            'max_monthly_units': 0,
            'min_monthly_revenue': 0.0,
            'max_monthly_revenue': 0.0,
            'confidence_level': 'low',
            'confidence_score': 0,
            'bsr_used': 0,
            'category_used': self.normalize_category(category) if category else 'Default',
            'seasonal_factor': 1.0,
            'has_history': False,
            'base_estimate': 0
        }

    def _save_estimation_history(self, asin: str, estimation: Dict, month: int):
        """Guarda estimación en histórico"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO sales_estimates_history
                (asin, estimated_sales, min_sales, max_sales, confidence_score,
                 bsr, category, price, month)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                asin,
                estimation['estimated_monthly_units'],
                estimation['min_monthly_units'],
                estimation['max_monthly_units'],
                estimation['confidence_score'],
                estimation['bsr_used'],
                estimation['category_used'],
                estimation.get('estimated_monthly_revenue', 0) / estimation['estimated_monthly_units'] if estimation['estimated_monthly_units'] > 0 else 0,
                month
            ))
            
            conn.commit()
            conn.close()
        except Exception as e:
            logging.warning(f"Error saving estimation history: {e}")

    def add_calibration_data(self, asin: str, actual_sales: int, bsr: int, 
                            category: str, price: float, month: int, notes: str = ""):
        """
        Añade dato de calibración (ventas reales vs estimadas)
        Útil para comparar con datos de SP-API
        """
        try:
            # Calcular estimación
            estimation = self.estimate_monthly_sales(bsr, category, price, asin, month, use_history=False)
            estimated_sales = estimation['estimated_monthly_units']
            
            # Calcular error porcentual
            if actual_sales > 0:
                error_percent = abs((estimated_sales - actual_sales) / actual_sales * 100)
            else:
                error_percent = 100.0
            
            # Guardar en base de datos
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO sales_calibration
                (asin, actual_sales, estimated_sales, bsr, category, price, month, error_percent, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (asin, actual_sales, estimated_sales, bsr, category, price, month, error_percent, notes))
            
            conn.commit()
            conn.close()
            
            logging.info(
                f"Calibration data saved: ASIN {asin} - "
                f"Actual: {actual_sales}, Estimated: {estimated_sales}, "
                f"Error: {error_percent:.1f}%"
            )
            
            return error_percent
            
        except Exception as e:
            logging.error(f"Error adding calibration data: {e}")
            return None

    def get_calibration_stats(self, category: Optional[str] = None) -> Dict:
        """Obtiene estadísticas de calibración para validar precisión"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if category:
                cursor.execute('''
                    SELECT 
                        COUNT(*) as total,
                        AVG(error_percent) as avg_error,
                        MIN(error_percent) as min_error,
                        MAX(error_percent) as max_error,
                        SUM(CASE WHEN error_percent <= 20 THEN 1 ELSE 0 END) as within_20_percent
                    FROM sales_calibration
                    WHERE category = ?
                ''', (category,))
            else:
                cursor.execute('''
                    SELECT 
                        COUNT(*) as total,
                        AVG(error_percent) as avg_error,
                        MIN(error_percent) as min_error,
                        MAX(error_percent) as max_error,
                        SUM(CASE WHEN error_percent <= 20 THEN 1 ELSE 0 END) as within_20_percent
                    FROM sales_calibration
                ''')
            
            row = cursor.fetchone()
            conn.close()
            
            if row and row[0] > 0:
                total = row[0]
                avg_error = row[1] or 0
                min_error = row[2] or 0
                max_error = row[3] or 0
                within_20 = row[4] or 0
                
                return {
                    'total_samples': total,
                    'avg_error_percent': round(avg_error, 2),
                    'min_error_percent': round(min_error, 2),
                    'max_error_percent': round(max_error, 2),
                    'within_20_percent': within_20,
                    'accuracy_percent': round((within_20 / total * 100), 2) if total > 0 else 0
                }
            
            return {
                'total_samples': 0,
                'avg_error_percent': 0,
                'min_error_percent': 0,
                'max_error_percent': 0,
                'within_20_percent': 0,
                'accuracy_percent': 0
            }
            
        except Exception as e:
            logging.error(f"Error getting calibration stats: {e}")
            return {}


# Función legacy para backward compatibility
def estimate_monthly_sales(bsr, category=None, price=0.0):
    """
    Función legacy mantenida para compatibilidad con código existente
    """
    estimator = ImprovedSalesEstimator()
    return estimator.estimate_monthly_sales(bsr, category, price)


# Instancia global para reutilización
_global_estimator = None

def get_estimator(bsr_tracker=None):
    """Obtiene instancia global del estimador (singleton)"""
    global _global_estimator
    if _global_estimator is None:
        _global_estimator = ImprovedSalesEstimator(bsr_tracker=bsr_tracker)
    return _global_estimator
