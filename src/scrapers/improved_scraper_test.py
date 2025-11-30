"""
Test mejorado de scraping con selectores actualizados para Amazon 2024
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from amzscraper import AmazonWebRobot
import logging
import re

logging.basicConfig(level=logging.INFO)

class ImprovedProductScraper(AmazonWebRobot):
    """Scraper mejorado con selectores actualizados"""

    def __init__(self, asin: str):
        super().__init__(enable_stealth=True, session_id=f"product_{asin}")
        self.asin = asin
        self.product_url = f"{self.amazon_link_prefix}/dp/{self.asin}"

    def scrape_product_info(self):
        """Scrape con selectores actualizados 2024"""
        try:
            logging.info(f"🥷 Scraping {self.product_url} with stealth mode")
            soup = self.get_soup(self.product_url)

            if not soup:
                logging.error("No soup returned")
                return None

            # Múltiples métodos para extraer cada dato
            product_data = {
                'asin': self.asin,
                'title': self._get_title_v2(soup),
                'price': self._get_price_v2(soup),
                'rating': self._get_rating_v2(soup),
                'review_count': self._get_review_count_v2(soup),
                'bsr': self._get_bsr_v2(soup),
                'category': self._get_category_v2(soup),
            }

            logging.info(f"✅ Scraped: {product_data['title'][:50]}... | Price: ${product_data['price']}")
            return product_data

        except Exception as e:
            logging.error(f"Error scraping {self.asin}: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _get_title_v2(self, soup):
        """Múltiples selectores para título"""
        try:
            # Método 1: productTitle
            title = soup.find('span', {'id': 'productTitle'})
            if title and title.text.strip():
                return title.text.strip()

            # Método 2: H1
            title = soup.find('h1', {'class': 'a-size-large'})
            if title and title.text.strip():
                return title.text.strip()

            # Método 3: Cualquier H1
            title = soup.find('h1')
            if title and title.text.strip():
                return title.text.strip()

            # Método 4: Buscar en meta tags
            meta_title = soup.find('meta', {'name': 'title'})
            if meta_title and meta_title.get('content'):
                return meta_title.get('content')

            return "Título no disponible"
        except Exception as e:
            logging.warning(f"Error getting title: {e}")
            return "Título no disponible"

    def _get_price_v2(self, soup):
        """Múltiples selectores para precio"""
        try:
            # Método 1: a-price-whole class
            price_whole = soup.find('span', {'class': 'a-price-whole'})
            if price_whole:
                price_text = price_whole.text.strip().replace(',', '').replace('$', '').replace('.', '')
                try:
                    return float(price_text) / 100 if len(price_text) > 2 else float(price_text)
                except:
                    pass

            # Método 2: Buscar en a-price span
            price_spans = soup.find_all('span', {'class': 'a-price'})
            for span in price_spans:
                price_whole = span.find('span', {'class': 'a-price-whole'})
                price_fraction = span.find('span', {'class': 'a-price-fraction'})
                if price_whole:
                    whole = price_whole.text.strip().replace(',', '').replace('$', '')
                    fraction = price_fraction.text.strip() if price_fraction else '00'
                    try:
                        return float(f"{whole}.{fraction}")
                    except:
                        pass

            # Método 3: Regex en todo el HTML
            html_text = str(soup)
            price_patterns = [
                r'\$(\d+\.\d{2})',
                r'"price"\s*:\s*"?\$?(\d+\.\d{2})"?',
                r'"priceAmount"\s*:\s*(\d+\.\d{2})',
            ]
            for pattern in price_patterns:
                match = re.search(pattern, html_text)
                if match:
                    try:
                        return float(match.group(1))
                    except:
                        pass

            return 0.0
        except Exception as e:
            logging.warning(f"Error getting price: {e}")
            return 0.0

    def _get_rating_v2(self, soup):
        """Rating con múltiples métodos"""
        try:
            # Método 1: a-icon-alt
            rating = soup.find('span', {'class': 'a-icon-alt'})
            if rating and 'out of' in rating.text:
                match = re.search(r'(\d+\.?\d*)\s*out of', rating.text)
                if match:
                    return float(match.group(1))

            # Método 2: Buscar en datos JSON
            html_text = str(soup)
            match = re.search(r'"averageStarRating"\s*:\s*"?(\d+\.?\d*)"?', html_text)
            if match:
                return float(match.group(1))

            return 0.0
        except:
            return 0.0

    def _get_review_count_v2(self, soup):
        """Número de reseñas"""
        try:
            # Método 1: acrCustomerReviewText
            count = soup.find('span', {'id': 'acrCustomerReviewText'})
            if count:
                match = re.search(r'([\d,]+)', count.text)
                if match:
                    return int(match.group(1).replace(',', ''))

            # Método 2: Buscar texto con "ratings"
            html_text = str(soup)
            patterns = [
                r'([\d,]+)\s*ratings',
                r'([\d,]+)\s*customer reviews',
                r'"reviewCount"\s*:\s*"?([\d,]+)"?',
            ]
            for pattern in patterns:
                match = re.search(pattern, html_text, re.IGNORECASE)
                if match:
                    try:
                        return int(match.group(1).replace(',', ''))
                    except:
                        pass

            return 0
        except:
            return 0

    def _get_bsr_v2(self, soup):
        """BSR mejorado"""
        try:
            html_text = str(soup)

            # Buscar patrón: #123,456 in Category
            match = re.search(r'#([\d,]+)\s+in\s+([^(<\n]+)', html_text)
            if match:
                rank = int(match.group(1).replace(',', ''))
                category = match.group(2).strip()
                return {'rank': rank, 'category': category}

            return {'rank': 0, 'category': 'Unknown'}
        except:
            return {'rank': 0, 'category': 'Unknown'}

    def _get_category_v2(self, soup):
        """Categoría del producto"""
        try:
            # Método 1: breadcrumbs
            breadcrumbs = soup.find('div', {'id': 'wayfinding-breadcrumbs_feature_div'})
            if breadcrumbs:
                links = breadcrumbs.find_all('a')
                if links:
                    return links[-1].text.strip()

            # Método 2: Desde BSR
            bsr_data = self._get_bsr_v2(soup)
            if bsr_data['category'] != 'Unknown':
                return bsr_data['category']

            return "General"
        except:
            return "General"


# Test
if __name__ == "__main__":
    test_asins = [
        'B09B8V1LZ3',  # Echo Dot (sé que existe)
        'B0B7CPSN8K',  # Air Fryer popular
    ]

    for asin in test_asins:
        print(f"\n{'='*70}")
        print(f"Testing ASIN: {asin}")
        print(f"{'='*70}")

        scraper = ImprovedProductScraper(asin)
        data = scraper.scrape_product_info()

        if data and data['price'] > 0:
            print(f"✅ SUCCESS!")
            print(f"   Title: {data['title'][:60]}...")
            print(f"   Price: ${data['price']}")
            print(f"   Rating: {data['rating']} ({data['review_count']} reviews)")
            print(f"   BSR: {data['bsr']['rank']} in {data['bsr']['category']}")
            print(f"   Category: {data['category']}")
        else:
            print(f"❌ FAILED - No data or price = 0")
