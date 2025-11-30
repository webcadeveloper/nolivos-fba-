"""
Competitor Scraper: Extrae información de competidores desde la página "Other Sellers" de Amazon.
Hereda de AmazonWebRobot para usar Splash + BeautifulSoup.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from amzscraper import AmazonWebRobot
import logging
import re

logging.basicConfig(level=logging.INFO)


class CompetitorAnalyzer(AmazonWebRobot):
    def __init__(self, asin: str):
        """
        Inicializa el analizador de competidores.
        
        Args:
            asin (str): ASIN del producto a analizar
        """
        super().__init__()
        self.asin = asin
        self.offers_url = f"{self.amazon_link_prefix}/gp/offer-listing/{self.asin}"
        self.competitor_data = {}
    
    def get_competitor_data(self):
        """
        Extrae toda la información de competidores desde la página de ofertas.
        
        Returns:
            dict: Contiene:
                - total_sellers (int): Número total de vendedores
                - buy_box_winner (dict): Info del ganador del Buy Box
                - other_sellers (list): Lista de otros vendedores (top 10)
        """
        try:
            soup = self.get_soup(self.offers_url)
            
            # Extraer información
            self.competitor_data = {
                'asin': self.asin,
                'total_sellers': self._get_total_sellers(soup),
                'buy_box_winner': self._get_buy_box_winner(soup),
                'other_sellers': self._get_other_sellers(soup)
            }
            
            logging.info(f"Competitor data scraped successfully for ASIN: {self.asin}")
            return self.competitor_data
            
        except Exception as e:
            logging.error(f"Error scraping competitor data for {self.asin}: {e}")
            return {
                'asin': self.asin,
                'total_sellers': 0,
                'buy_box_winner': {},
                'other_sellers': []
            }
    
    def _get_total_sellers(self, soup):
        """Extrae el número total de vendedores."""
        try:
            # Buscar el texto que indica el número de vendedores
            # Ejemplo: "XX new & used offers from $XX.XX"
            offers_text = soup.find('div', {'id': 'olpOfferList'})
            if offers_text:
                # Buscar en el texto del div o en headers
                header = soup.find('h1')
                if header:
                    text = header.text
                    match = re.search(r'(\d+)\s+(?:new|used|new & used)', text, re.IGNORECASE)
                    if match:
                        return int(match.group(1))
            
            # Método alternativo: contar los divs de ofertas
            offer_rows = soup.find_all('div', {'class': 'olpOffer'})
            if offer_rows:
                return len(offer_rows)
            
            # Último recurso: buscar en el texto de la página
            page_text = soup.get_text()
            match = re.search(r'(\d+)\s+(?:new|used|new & used)', page_text, re.IGNORECASE)
            if match:
                return int(match.group(1))
            
            return 0
        except Exception as e:
            logging.warning(f"Error getting total sellers: {e}")
            return 0
    
    def _get_buy_box_winner(self, soup):
        """Extrae información del ganador del Buy Box."""
        try:
            buy_box = {}
            
            # Buscar el div del Buy Box (normalmente tiene clase especial o está primero)
            buy_box_div = soup.find('div', {'id': 'buybox'})
            if not buy_box_div:
                # Buscar en el primer offer row
                first_offer = soup.find('div', {'class': 'olpOffer'})
                if first_offer:
                    buy_box_div = first_offer
            
            if buy_box_div:
                # Extraer nombre del vendedor
                seller_name = self._extract_seller_name(buy_box_div)
                # Extraer precio
                price = self._extract_price(buy_box_div)
                # Extraer rating
                rating = self._extract_seller_rating(buy_box_div)
                
                buy_box = {
                    'name': seller_name,
                    'price': price,
                    'shipping': 0.0,  # Intentar extraer shipping
                    'rating': rating,
                    'condition': 'New',  # Default
                    'fulfillment_type': 'FBA'  # Default, intentar detectar
                }
                
                # Intentar extraer shipping
                shipping_text = buy_box_div.get_text()
                shipping_match = re.search(r'\+ \$(\d+\.?\d*)\s+shipping', shipping_text, re.IGNORECASE)
                if shipping_match:
                    buy_box['shipping'] = float(shipping_match.group(1))
                
                # Intentar detectar fulfillment type
                if 'fulfilled by amazon' in shipping_text.lower() or 'fba' in shipping_text.lower():
                    buy_box['fulfillment_type'] = 'FBA'
                elif 'merchant' in shipping_text.lower() or 'fbm' in shipping_text.lower():
                    buy_box['fulfillment_type'] = 'FBM'
            
            return buy_box if buy_box else {
                'name': 'No disponible',
                'price': 0.0,
                'shipping': 0.0,
                'rating': 0.0,
                'condition': 'Unknown',
                'fulfillment_type': 'Unknown'
            }
        except Exception as e:
            logging.warning(f"Error getting buy box winner: {e}")
            return {
                'name': 'No disponible',
                'price': 0.0,
                'shipping': 0.0,
                'rating': 0.0,
                'condition': 'Unknown',
                'fulfillment_type': 'Unknown'
            }
    
    def _get_other_sellers(self, soup, limit=10):
        """Extrae lista de otros vendedores (top N)."""
        try:
            sellers = []
            
            # Buscar todos los divs de ofertas
            offer_rows = soup.find_all('div', {'class': 'olpOffer'})
            
            # Si hay más de una oferta, la primera suele ser el Buy Box
            # Empezamos desde el índice 1 (segundo elemento)
            start_index = 1 if len(offer_rows) > 1 else 0
            
            for offer in offer_rows[start_index:limit + 1]:
                try:
                    seller_info = {
                        'name': self._extract_seller_name(offer),
                        'price': self._extract_price(offer),
                        'shipping': self._extract_shipping(offer),
                        'condition': self._extract_condition(offer),
                        'rating': self._extract_seller_rating(offer),
                        'fulfillment_type': self._extract_fulfillment_type(offer)
                    }
                    sellers.append(seller_info)
                except Exception as e:
                    logging.warning(f"Error extracting seller info: {e}")
                    continue
            
            return sellers[:limit]
            
        except Exception as e:
            logging.warning(f"Error getting other sellers: {e}")
            return []
    
    def _extract_seller_name(self, element):
        """Extrae el nombre del vendedor."""
        try:
            # Buscar enlaces o texto del vendedor
            seller_link = element.find('a', {'href': re.compile(r'/gp/help/seller')})
            if seller_link:
                return seller_link.text.strip()
            
            # Buscar por clase específica
            seller_name_elem = element.find('h3', {'class': 'olpSellerName'})
            if seller_name_elem:
                link = seller_name_elem.find('a')
                if link:
                    return link.text.strip()
                return seller_name_elem.text.strip()
            
            # Buscar en el texto general
            text = element.get_text()
            # Intentar encontrar patrón como "Sold by: SellerName"
            match = re.search(r'sold by:?\s*([^\n]+)', text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
            
            return 'Vendedor desconocido'
        except:
            return 'Vendedor desconocido'
    
    def _extract_price(self, element):
        """Extrae el precio."""
        try:
            # Buscar precio principal
            price_elem = element.find('span', {'class': 'a-price-whole'})
            if price_elem:
                price_text = price_elem.text.strip().replace(',', '').replace('$', '')
                cents_elem = element.find('span', {'class': 'a-price-fraction'})
                if cents_elem:
                    price_text += '.' + cents_elem.text.strip()
                return float(price_text)
            
            # Buscar precio en formato alternativo
            price_elem = element.find('span', {'class': re.compile(r'a-price')})
            if price_elem:
                price_symbol = price_elem.find('span', {'class': 'a-price-symbol'})
                price_whole = price_elem.find('span', {'class': 'a-price-whole'})
                if price_whole:
                    price_text = price_whole.text.strip().replace(',', '')
                    price_fraction = price_elem.find('span', {'class': 'a-price-fraction'})
                    if price_fraction:
                        price_text += '.' + price_fraction.text.strip()
                    return float(price_text)
            
            # Buscar en texto
            text = element.get_text()
            price_match = re.search(r'\$(\d+\.?\d*)', text)
            if price_match:
                return float(price_match.group(1))
            
            return 0.0
        except:
            return 0.0
    
    def _extract_shipping(self, element):
        """Extrae el costo de envío."""
        try:
            text = element.get_text()
            shipping_match = re.search(r'\+ \$(\d+\.?\d*)\s+shipping', text, re.IGNORECASE)
            if shipping_match:
                return float(shipping_match.group(1))
            
            # Buscar "FREE Shipping"
            if 'free shipping' in text.lower():
                return 0.0
            
            return 0.0
        except:
            return 0.0
    
    def _extract_condition(self, element):
        """Extrae la condición del producto."""
        try:
            text = element.get_text()
            if re.search(r'\bnew\b', text, re.IGNORECASE):
                return 'New'
            elif re.search(r'\bused\b', text, re.IGNORECASE):
                return 'Used'
            elif re.search(r'\brefurbished\b', text, re.IGNORECASE):
                return 'Refurbished'
            else:
                return 'New'  # Default
        except:
            return 'New'
    
    def _extract_seller_rating(self, element):
        """Extrae el rating del vendedor."""
        try:
            # Buscar rating en estrellas
            rating_elem = element.find('span', {'class': re.compile(r'star')})
            if rating_elem:
                rating_text = rating_elem.get('aria-label', '')
                match = re.search(r'(\d+\.?\d*)', rating_text)
                if match:
                    return float(match.group(1))
            
            # Buscar en el texto
            text = element.get_text()
            rating_match = re.search(r'(\d+\.?\d*)\s*out of 5', text, re.IGNORECASE)
            if rating_match:
                return float(rating_match.group(1))
            
            return 0.0
        except:
            return 0.0
    
    def _extract_fulfillment_type(self, element):
        """Extrae el tipo de fulfillment (FBA/FBM)."""
        try:
            text = element.get_text().lower()
            if 'fulfilled by amazon' in text or 'fba' in text:
                return 'FBA'
            elif 'merchant' in text or 'fbm' in text or 'ships from' in text:
                return 'FBM'
            else:
                return 'Unknown'
        except:
            return 'Unknown'


