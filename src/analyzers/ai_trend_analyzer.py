"""
AI Trend Analyzer - Usa IA (codex) para predecir tendencias y dar recomendaciones
Similar a Jungle Scout's AI features
"""
import subprocess
import logging
import json

logging.basicConfig(level=logging.INFO)


class AITrendAnalyzer:
    """Usa IA local (codex) para analizar tendencias y predecir oportunidades"""

    def __init__(self):
        self.codex_cmd = '/home/hector/.nvm/versions/node/v20.19.4/bin/codex'
        self.cwd = '/mnt/c/Users/Admin/OneDrive - Nolivos Law/Aplicaciones/AMAZON/amz-review-analyzer'

    def _call_codex(self, prompt):
        """Llama a codex exec con un prompt"""
        try:
            result = subprocess.run(
                ['sudo', '-u', 'hector', self.codex_cmd, 'exec', prompt],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=self.cwd
            )

            if result.returncode == 0:
                output_lines = result.stdout.strip().split('\n')
                response = output_lines[-1] if output_lines else ""
                return response
            else:
                logging.error(f"Codex error: {result.stderr}")
                return None

        except subprocess.TimeoutExpired:
            logging.error("Codex timeout")
            return None
        except Exception as e:
            logging.error(f"Error calling codex: {e}")
            return None

    def analyze_product_trend(self, trend_data):
        """
        Analiza tendencias del producto y da recomendación con IA

        Args:
            trend_data: dict con datos de tendencias del producto

        Returns:
            dict con análisis de IA
        """
        prompt = f"""Eres experto en Amazon FBA. Analiza este producto y da recomendación:

PRODUCTO: {trend_data.get('product_name', 'Unknown')[:100]}
CATEGORÍA: {trend_data.get('category', 'Unknown')}

TENDENCIAS (últimos 30 días):
- BSR actual: {trend_data.get('current_bsr', 'N/A')}
- Cambio BSR: {trend_data.get('bsr_change_30d', 0)} ({"MEJOR" if trend_data.get('bsr_change_30d', 0) > 0 else "PEOR"})
- Tendencia demanda: {trend_data.get('demand_trend', 'N/A')}
- Precio actual: ${trend_data.get('current_price', 0)}
- Cambio precio: ${trend_data.get('price_change_30d', 0)}
- Sellers actuales: {trend_data.get('current_sellers', 0)}
- Cambio sellers: {trend_data.get('seller_change_30d', 0)}

¿DEBO VENDER ESTE PRODUCTO? Responde en JSON:
{{
  "recommendation": "COMPRAR / EVITAR / OBSERVAR",
  "confidence": 0-100,
  "reason": "explicación breve",
  "alerts": ["alerta1", "alerta2"]
}}"""

        response = self._call_codex(prompt)

        if not response:
            return {
                'recommendation': 'OBSERVAR',
                'confidence': 50,
                'reason': 'No se pudo obtener análisis de IA',
                'alerts': []
            }

        # Parsear respuesta JSON
        try:
            # Intentar extraer JSON de la respuesta
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                ai_analysis = json.loads(json_match.group())
                return ai_analysis
            else:
                # Fallback manual
                return {
                    'recommendation': 'OBSERVAR',
                    'confidence': 60,
                    'reason': response[:200],
                    'alerts': []
                }
        except Exception as e:
            logging.error(f"Error parsing AI response: {e}")
            return {
                'recommendation': 'OBSERVAR',
                'confidence': 50,
                'reason': 'Error analizando respuesta de IA',
                'alerts': []
            }

    def analyze_category_trends(self, category_data):
        """
        Analiza qué categorías están HOT en Amazon ahora

        Args:
            category_data: lista de categorías con métricas

        Returns:
            dict con análisis de categorías
        """
        categories_summary = "\n".join([
            f"- {cat['category']}: {cat['trending_products']} productos en alza, BSR mejora promedio: {cat['avg_bsr_improvement']}"
            for cat in category_data[:5]
        ])

        prompt = f"""Eres experto en Amazon FBA. Analiza estas categorías y recomienda dónde invertir:

CATEGORÍAS MÁS CALIENTES (últimos 30 días):
{categories_summary}

¿En qué categoría debo buscar productos? Responde en JSON:
{{
  "top_category": "nombre",
  "reason": "por qué es la mejor",
  "avoid": "categoría a evitar",
  "seasonal_alert": "alerta estacional si aplica"
}}"""

        response = self._call_codex(prompt)

        if not response:
            return {
                'top_category': category_data[0]['category'] if category_data else 'Unknown',
                'reason': 'No se pudo obtener análisis',
                'avoid': '',
                'seasonal_alert': ''
            }

        try:
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                return {
                    'top_category': category_data[0]['category'] if category_data else 'Unknown',
                    'reason': response[:200],
                    'avoid': '',
                    'seasonal_alert': ''
                }
        except:
            return {
                'top_category': category_data[0]['category'] if category_data else 'Unknown',
                'reason': 'Error analizando categorías',
                'avoid': '',
                'seasonal_alert': ''
            }

    def predict_opportunity(self, product_data, supplier_price):
        """
        Predice si un producto será buena oportunidad en los próximos 30 días

        Args:
            product_data: datos actuales del producto
            supplier_price: precio de proveedor

        Returns:
            dict con predicción
        """
        bsr = product_data.get('bsr', 999999)
        amazon_price = product_data.get('price', 0)
        category = product_data.get('category', 'Unknown')

        prompt = f"""Eres experto en Amazon FBA. Predice si este producto será rentable:

PRODUCTO:
- BSR: {bsr}
- Categoría: {category}
- Precio Amazon: ${amazon_price}
- Precio proveedor: ${supplier_price}
- Margen bruto: ${amazon_price - supplier_price}

¿Será buena oportunidad en 30 días? Responde en JSON:
{{
  "prediction": "EXCELENTE / BUENO / REGULAR / MALO",
  "confidence": 0-100,
  "expected_roi": 0-100,
  "risk_level": "BAJO / MEDIO / ALTO",
  "key_factor": "factor más importante"
}}"""

        response = self._call_codex(prompt)

        if not response:
            # Fallback a análisis simple
            margin_percent = ((amazon_price - supplier_price) / supplier_price * 100) if supplier_price > 0 else 0

            if margin_percent > 100:
                prediction = "EXCELENTE"
            elif margin_percent > 50:
                prediction = "BUENO"
            elif margin_percent > 25:
                prediction = "REGULAR"
            else:
                prediction = "MALO"

            return {
                'prediction': prediction,
                'confidence': 60,
                'expected_roi': min(100, margin_percent),
                'risk_level': 'MEDIO',
                'key_factor': f'Margen: {margin_percent:.1f}%'
            }

        try:
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                return {
                    'prediction': 'REGULAR',
                    'confidence': 50,
                    'expected_roi': 30,
                    'risk_level': 'MEDIO',
                    'key_factor': response[:100]
                }
        except:
            return {
                'prediction': 'REGULAR',
                'confidence': 50,
                'expected_roi': 30,
                'risk_level': 'MEDIO',
                'key_factor': 'Error en predicción'
            }

    def analyze_competition(self, seller_data):
        """
        Analiza nivel de competencia y saturación

        Args:
            seller_data: dict con datos de sellers

        Returns:
            dict con análisis de competencia
        """
        seller_count = seller_data.get('seller_count', 0)
        avg_price = seller_data.get('avg_price', 0)
        price_variance = seller_data.get('price_variance', 0)

        prompt = f"""Analiza la competencia para este producto Amazon:

COMPETENCIA:
- Total sellers: {seller_count}
- Precio promedio: ${avg_price}
- Varianza precios: ${price_variance}

¿Está saturado? Responde en JSON:
{{
  "saturation": "BAJO / MEDIO / ALTO / EXTREMO",
  "can_compete": true/false,
  "recommended_price": número,
  "strategy": "estrategia recomendada"
}}"""

        response = self._call_codex(prompt)

        if not response or seller_count == 0:
            # Análisis simple sin IA
            if seller_count < 10:
                saturation = "BAJO"
                can_compete = True
            elif seller_count < 30:
                saturation = "MEDIO"
                can_compete = True
            elif seller_count < 100:
                saturation = "ALTO"
                can_compete = False
            else:
                saturation = "EXTREMO"
                can_compete = False

            return {
                'saturation': saturation,
                'can_compete': can_compete,
                'recommended_price': avg_price * 0.95 if avg_price > 0 else 0,
                'strategy': 'Análisis básico - sin IA'
            }

        try:
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except:
            pass

        return {
            'saturation': 'MEDIO',
            'can_compete': True,
            'recommended_price': avg_price,
            'strategy': 'Error en análisis'
        }
