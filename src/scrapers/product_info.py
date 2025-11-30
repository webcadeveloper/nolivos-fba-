"""
Scraper de información de productos de Amazon para análisis FBA.
Hereda de AmazonWebRobot para usar Splash.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from amzscraper import AmazonWebRobot
import logging
import re

logging.basicConfig(level=logging.INFO)

class ProductInfoScraper(AmazonWebRobot):
    def __init__(self, asin: str):
        # IMPORTANTE: Desactivar stealth mode por ahora - usar Splash básico que SÍ funciona
        super().__init__(enable_stealth=False)
        self.asin = asin
        self.product_url = f"{self.amazon_link_prefix}/dp/{self.asin}"
        self.product_data = {}
        
    def scrape_product_info(self):
        """Extrae toda la información del producto"""
        try:
            soup = self.get_soup(self.product_url)

            images = self._get_images(soup)

            self.product_data = {
                'asin': self.asin,
                'title': self._get_title(soup),
                'price': self._get_price(soup),
                'rating': self._get_rating(soup),
                'review_count': self._get_review_count(soup),
                'bsr': self._get_bsr(soup),
                'category': self._get_category(soup),
                'seller_info': self._get_seller_info(soup),
                'dimensions': self._get_dimensions(soup),
                'weight': self._get_weight(soup),
                'images': images,
                'product_url': self.product_url,  # URL del producto en Amazon
                'image_url': images[0] if images else None  # Primera imagen como principal
            }

            logging.info(f"Product info scraped successfully for ASIN: {self.asin}")
            return self.product_data

        except Exception as e:
            logging.error(f"Error scraping product info for {self.asin}: {e}")
            return None
    
    def _get_title(self, soup):
        """Extrae el título del producto"""
        try:
            title = soup.find('span', {'id': 'productTitle'})
            return title.text.strip() if title else "Título no disponible"
        except:
            return "Título no disponible"
    
    def _get_price(self, soup):
        """Extrae el precio actual - MEJORADO con múltiples métodos"""
        try:
            # Método 1: a-price-whole + a-price-fraction
            price_whole = soup.find('span', {'class': 'a-price-whole'})
            if price_whole:
                whole_text = price_whole.text.strip().replace(',', '').replace('$', '').replace('.', '')
                # Buscar fracción
                price_fraction = soup.find('span', {'class': 'a-price-fraction'})
                if price_fraction:
                    fraction_text = price_fraction.text.strip()
                    try:
                        return float(f"{whole_text}.{fraction_text}")
                    except:
                        pass
                # Sin fracción, asumir .00
                try:
                    return float(whole_text) if len(whole_text) < 3 else float(whole_text) / 100
                except:
                    pass

            # Método 2: priceblock_ourprice
            price = soup.find('span', {'id': 'priceblock_ourprice'})
            if price:
                price_text = price.text.strip().replace(',', '').replace('$', '')
                try:
                    return float(price_text)
                except:
                    pass

            # Método 3: Buscar en spans con texto que contenga $
            all_spans = soup.find_all('span')
            for span in all_spans:
                text = span.text.strip()
                if '$' in text and len(text) < 20:  # Evitar textos largos
                    # Extraer número del formato $XX.XX
                    match = re.search(r'\$?(\d+(?:,\d{3})*(?:\.\d{2})?)', text)
                    if match:
                        try:
                            price_val = float(match.group(1).replace(',', ''))
                            if 1 < price_val < 10000:  # Rango razonable
                                return price_val
                        except:
                            pass

            return 0.0
        except Exception as e:
            logging.error(f"Error extracting price: {e}")
            return 0.0
    
    def _get_rating(self, soup):
        """Extrae el rating promedio"""
        try:
            rating = soup.find('span', {'class': 'a-icon-alt'})
            if rating:
                rating_text = rating.text.strip()
                match = re.search(r'(\d+\.?\d*)', rating_text)
                if match:
                    return float(match.group(1))
            return 0.0
        except:
            return 0.0
    
    def _get_review_count(self, soup):
        """Extrae el número de reseñas"""
        try:
            count = soup.find('span', {'id': 'acrCustomerReviewText'})
            if count:
                count_text = count.text.strip()
                match = re.search(r'([\d,]+)', count_text)
                if match:
                    return int(match.group(1).replace(',', ''))
            return 0
        except:
            return 0
    
    def _get_bsr(self, soup):
        """Extrae el Best Sellers Rank"""
        try:
            # Buscar en la tabla de detalles del producto
            details = soup.find('div', {'id': 'detailBulletsWrapper_feature_div'})
            if details:
                bsr_text = details.text
                match = re.search(r'#([\d,]+)\s+in\s+([^(]+)', bsr_text)
                if match:
                    rank = int(match.group(1).replace(',', ''))
                    return {'rank': rank, 'category': match.group(2).strip()}
            
            # Fallback: buscar en otra ubicación
            bsr_section = soup.find('th', text=re.compile('Best Sellers Rank'))
            if bsr_section:
                bsr_value = bsr_section.find_next('td')
                if bsr_value:
                    match = re.search(r'#([\d,]+)', bsr_value.text)
                    if match:
                        return {'rank': int(match.group(1).replace(',', '')), 'category': 'Unknown'}
            
            return {'rank': 0, 'category': 'Unknown'}
        except:
            return {'rank': 0, 'category': 'Unknown'}
    
    def _get_category(self, soup):
        """Extrae la categoría principal"""
        try:
            breadcrumbs = soup.find('div', {'id': 'wayfinding-breadcrumbs_feature_div'})
            if breadcrumbs:
                categories = breadcrumbs.find_all('a', {'class': 'a-link-normal'})
                if categories:
                    return categories[-1].text.strip()
            return "Sin categoría"
        except:
            return "Sin categoría"
    
    def _get_seller_info(self, soup):
        """Determina si es FBA o FBM"""
        try:
            seller_section = soup.find('div', {'id': 'merchant-info'})
            if seller_section:
                text = seller_section.text.lower()
                if 'amazon' in text or 'fulfillment by amazon' in text:
                    return {'type': 'FBA', 'seller': 'Amazon'}
                else:
                    return {'type': 'FBM', 'seller': 'Third Party'}
            return {'type': 'Unknown', 'seller': 'Unknown'}
        except:
            return {'type': 'Unknown', 'seller': 'Unknown'}
    
    def _get_dimensions(self, soup):
        """Extrae dimensiones del producto (L x W x H en pulgadas)"""
        try:
            # Buscar en la tabla de detalles
            details = soup.find('div', {'id': 'detailBulletsWrapper_feature_div'})
            if details:
                dim_text = details.text
                # Buscar patrón: X x Y x Z inches
                match = re.search(r'(\d+\.?\d*)\s*x\s*(\d+\.?\d*)\s*x\s*(\d+\.?\d*)\s*inches', dim_text, re.IGNORECASE)
                if match:
                    return {
                        'length': float(match.group(1)),
                        'width': float(match.group(2)),
                        'height': float(match.group(3)),
                        'unit': 'inches'
                    }
            return {'length': 0, 'width': 0, 'height': 0, 'unit': 'inches'}
        except:
            return {'length': 0, 'width': 0, 'height': 0, 'unit': 'inches'}
    
    def _get_weight(self, soup):
        """Extrae el peso del producto"""
        try:
            details = soup.find('div', {'id': 'detailBulletsWrapper_feature_div'})
            if details:
                weight_text = details.text
                # Buscar patrón: X pounds o X ounces
                match = re.search(r'(\d+\.?\d*)\s*(pounds?|ounces?|lbs?|oz)', weight_text, re.IGNORECASE)
                if match:
                    value = float(match.group(1))
                    unit = match.group(2).lower()
                    
                    # Convertir todo a pounds
                    if 'oz' in unit or 'ounce' in unit:
                        value = value / 16  # 16 oz = 1 lb
                    
                    return {'value': value, 'unit': 'pounds'}
            return {'value': 0, 'unit': 'pounds'}
        except:
            return {'value': 0, 'unit': 'pounds'}
    
    def _get_images(self, soup):
        """Extrae URLs de imágenes del producto (máximo 5)"""
        try:
            images = []
            img_elements = soup.find_all('img', {'class': 'a-dynamic-image'})
            
            for img in img_elements[:5]:  # Máximo 5 imágenes
                if 'src' in img.attrs:
                    images.append(img['src'])
            
            return images if images else []
        except:
            return []
