"""
Competition Analyzer - Analiza número de sellers, saturación del mercado
Similar a Helium 10's X-Ray
"""
import requests
from bs4 import BeautifulSoup
import re
import logging
import statistics
from src.api.n8n_webhooks import n8n_webhooks

logging.basicConfig(level=logging.INFO)


class CompetitionAnalyzer:
    """Analiza competencia y saturación del mercado para un producto"""

    def __init__(self, asin):
        self.asin = asin
        self.splash_url = 'http://localhost:8050/render.html'

    def _get_soup(self, url, wait=3):
        """Obtiene BeautifulSoup usando Splash"""
        try:
            response = requests.get(
                self.splash_url,
                params={'url': url, 'wait': wait},
                timeout=60
            )

            if response.status_code == 200:
                return BeautifulSoup(response.content, 'html.parser')
            else:
                logging.warning(f"Splash returned {response.status_code}")
                return None
        except Exception as e:
            logging.error(f"Error with Splash: {e}")
            return None

    def count_sellers(self):
        """
        Cuenta número de sellers ofreciendo el producto

        Returns:
            dict con datos de sellers
        """
        url = f"https://www.amazon.com/gp/offer-listing/{self.asin}"
        soup = self._get_soup(url, wait=5)

        if not soup:
            logging.warning(f"No se pudo obtener página de sellers para {self.asin}")
            return {
                'seller_count': 0,
                'prices': [],
                'avg_price': 0,
                'min_price': 0,
                'max_price': 0,
                'price_variance': 0,
                'fba_count': 0,
                'fbm_count': 0
            }

        sellers = []
        prices = []
        fba_count = 0
        fbm_count = 0

        # Buscar ofertas en la página
        offer_rows = soup.find_all('div', class_=re.compile(r'offer|listing'))

        if not offer_rows:
            # Intenta estructura alternativa
            offer_rows = soup.find_all('div', attrs={'id': re.compile(r'aod-offer')})

        for offer in offer_rows:
            try:
                # Extraer precio
                price_elem = offer.find('span', class_=re.compile(r'price|offer-price'))
                if price_elem:
                    price_text = price_elem.get_text(strip=True)
                    price_match = re.search(r'\$?([\d,]+\.?\d*)', price_text)
                    if price_match:
                        price = float(price_match.group(1).replace(',', ''))
                        prices.append(price)

                # Detectar FBA vs FBM
                fulfillment_text = offer.get_text().lower()
                if 'fulfilled by amazon' in fulfillment_text or 'prime' in fulfillment_text:
                    fba_count += 1
                else:
                    fbm_count += 1

            except Exception as e:
                continue

        seller_count = len(prices)

        if not prices:
            logging.info(f"No se encontraron sellers para {self.asin}, usando datos del producto principal")
            return {
                'seller_count': 1,  # Al menos Amazon
                'prices': [],
                'avg_price': 0,
                'min_price': 0,
                'max_price': 0,
                'price_variance': 0,
                'fba_count': 1,
                'fbm_count': 0
            }

        avg_price = statistics.mean(prices)
        min_price = min(prices)
        max_price = max(prices)
        price_variance = max_price - min_price if len(prices) > 1 else 0

        result = {
            'seller_count': seller_count,
            'prices': prices,
            'avg_price': round(avg_price, 2),
            'min_price': round(min_price, 2),
            'max_price': round(max_price, 2),
            'price_variance': round(price_variance, 2),
            'fba_count': fba_count,
            'fbm_count': fbm_count
        }

        logging.info(f"Sellers para {self.asin}: {seller_count} total, {fba_count} FBA, {fbm_count} FBM")

        return result

    def analyze_reviews_distribution(self):
        """
        Analiza distribución de reviews (detecta productos saturados)

        Returns:
            dict con análisis de reviews
        """
        url = f"https://www.amazon.com/dp/{self.asin}"
        soup = self._get_soup(url, wait=4)

        if not soup:
            return {
                'total_reviews': 0,
                'rating': 0,
                'recent_reviews_30d': 0,
                'review_velocity': 0  # reviews/día
            }

        # Total reviews
        review_count_elem = soup.find('span', attrs={'data-hook': 'total-review-count'})
        if not review_count_elem:
            review_count_elem = soup.find('span', {'id': 'acrCustomerReviewText'})

        total_reviews = 0
        if review_count_elem:
            review_text = review_count_elem.get_text(strip=True)
            match = re.search(r'([\d,]+)', review_text)
            if match:
                total_reviews = int(match.group(1).replace(',', ''))

        # Rating
        rating_elem = soup.find('span', class_=re.compile(r'a-icon-alt'))
        rating = 0
        if rating_elem:
            rating_text = rating_elem.get_text(strip=True)
            match = re.search(r'([\d.]+)', rating_text)
            if match:
                rating = float(match.group(1))

        # Estimación de review velocity (aproximada)
        # Productos con muchos reviews = saturados
        review_velocity = total_reviews / 365 if total_reviews > 0 else 0

        return {
            'total_reviews': total_reviews,
            'rating': rating,
            'review_velocity': round(review_velocity, 2)
        }

    def detect_saturation(self):
        """
        Detecta nivel de saturación del mercado

        Returns:
            dict con análisis completo de competencia
        """
        logging.info(f"🔍 Analizando competencia para {self.asin}...")

        # 1. Contar sellers
        seller_data = self.count_sellers()

        # 2. Analizar reviews
        review_data = self.analyze_reviews_distribution()

        # 3. Calcular saturation score (0-100)
        saturation_score = 0

        # Factor 1: Número de sellers (max 40 puntos)
        seller_count = seller_data['seller_count']
        if seller_count > 100:
            saturation_score += 40
        elif seller_count > 50:
            saturation_score += 35
        elif seller_count > 20:
            saturation_score += 25
        elif seller_count > 10:
            saturation_score += 15
        else:
            saturation_score += 5

        # Factor 2: Review velocity (max 30 puntos)
        review_velocity = review_data['review_velocity']
        if review_velocity > 10:  # >10 reviews/día = muy saturado
            saturation_score += 30
        elif review_velocity > 5:
            saturation_score += 20
        elif review_velocity > 1:
            saturation_score += 10
        else:
            saturation_score += 0

        # Factor 3: Price war (max 30 puntos)
        price_variance_percent = (seller_data['price_variance'] / seller_data['avg_price'] * 100) if seller_data['avg_price'] > 0 else 0
        if price_variance_percent > 20:  # Guerra de precios
            saturation_score += 30
        elif price_variance_percent > 10:
            saturation_score += 20
        else:
            saturation_score += 5

        # Determinar nivel de saturación
        if saturation_score >= 80:
            saturation_level = '🔴 EXTREMO'
            recommendation = 'EVITAR - Mercado extremadamente saturado'
        elif saturation_score >= 60:
            saturation_level = '🟠 ALTO'
            recommendation = 'PRECAUCIÓN - Alta competencia, difícil competir'
        elif saturation_score >= 40:
            saturation_level = '🟡 MEDIO'
            recommendation = 'EVALUAR - Competencia moderada, posible con ventaja'
        else:
            saturation_level = '🟢 BAJO'
            recommendation = 'BUENA OPORTUNIDAD - Baja competencia'

        result = {
            'asin': self.asin,
            'saturation_level': saturation_level,
            'saturation_score': saturation_score,
            'recommendation': recommendation,

            # Sellers
            'seller_count': seller_count,
            'fba_sellers': seller_data['fba_count'],
            'fbm_sellers': seller_data['fbm_count'],
            'avg_price': seller_data['avg_price'],
            'price_range': f"${seller_data['min_price']} - ${seller_data['max_price']}",
            'price_variance': seller_data['price_variance'],

            # Reviews
            'total_reviews': review_data['total_reviews'],
            'rating': review_data['rating'],
            'review_velocity': review_data['review_velocity'],

            # Insights
            'is_saturated': saturation_score >= 60,
            'has_price_war': price_variance_percent > 15,
            'dominated_by_fba': seller_data['fba_count'] > seller_data['fbm_count'],
        }

        logging.info(f"  Saturación: {saturation_level} (score: {saturation_score})")
        logging.info(f"  Sellers: {seller_count} total ({seller_data['fba_count']} FBA)")
        logging.info(f"  Reviews: {review_data['total_reviews']} ({review_data['rating']}★)")

        # 🔥 WEBHOOKS: Notificar oportunidades de baja competencia
        try:
            # Detectar baja competencia (menos de 10 sellers)
            if seller_count < 10 and saturation_score < 40:
                # Para triggear low_competition, necesitamos datos de opportunity
                # Este webhook se llamará desde product_discovery cuando pase la oportunidad completa
                pass

            # Detectar spike de reviews negativas
            if review_data['rating'] < 3.5 and review_data['total_reviews'] > 100:
                n8n_webhooks.trigger_error(
                    'review_quality_alert',
                    f"ASIN {self.asin} tiene rating bajo ({review_data['rating']}★) con {review_data['total_reviews']} reviews",
                    {'asin': self.asin, 'rating': review_data['rating'], 'reviews': review_data['total_reviews']}
                )

        except Exception as webhook_error:
            logging.warning(f"Error enviando webhooks de competencia: {webhook_error}")

        return result

    def get_buybox_info(self):
        """Obtiene información del seller que tiene el Buy Box"""
        url = f"https://www.amazon.com/dp/{self.asin}"
        soup = self._get_soup(url, wait=3)

        if not soup:
            return None

        # Precio del Buy Box
        buybox_price_elem = soup.find('span', class_='a-price-whole')
        buybox_price = 0
        if buybox_price_elem:
            price_text = buybox_price_elem.get_text(strip=True)
            match = re.search(r'([\d,]+)', price_text)
            if match:
                buybox_price = float(match.group(1).replace(',', ''))

        # Seller del Buy Box
        seller_elem = soup.find('a', {'id': 'sellerProfileTriggerId'})
        seller_name = seller_elem.get_text(strip=True) if seller_elem else 'Amazon'

        return {
            'buybox_price': buybox_price,
            'buybox_seller': seller_name,
            'is_amazon': seller_name.lower() == 'amazon' or 'amazon' in seller_name.lower()
        }
