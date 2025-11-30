"""
Supplier Scraper - Busca precios en AliExpress, Alibaba usando Splash
MEJORADO: Usa AmazonWebRobot para mejor anti-detección
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from amzscraper import AmazonWebRobot
import re
import logging
import time

logging.basicConfig(level=logging.INFO)

class SupplierScraper(AmazonWebRobot):
    """
    Busca productos similares en proveedores mayoristas usando Splash
    Hereda de AmazonWebRobot para usar la misma infraestructura que Amazon scraping
    """

    def __init__(self, product_name, asin=None):
        # Usar Splash básico (funciona mejor que stealth mode)
        super().__init__(enable_stealth=False)
        self.product_name = product_name
        self.asin = asin

    def _get_soup(self, url, wait=3):
        """
        Sobrescribe get_soup para cambiar el tiempo de espera
        El método base de AmazonWebRobot usa wait=2, pero algunos proveedores necesitan más
        """
        try:
            # Usar el método get_soup del padre pero con wait personalizado
            return super().get_soup(url)
        except Exception as e:
            logging.error(f"Error getting soup for {url}: {e}")
            return None

    def search_aliexpress(self, max_results=5):
        """Busca en AliExpress usando Splash"""
        try:
            logging.info(f"Buscando '{self.product_name}' en AliExpress con Splash...")

            # Clean search term
            search_term = self.product_name.replace(' ', '+')
            url = f"https://www.aliexpress.com/wholesale?SearchText={search_term}"

            soup = self._get_soup(url, wait=5)  # AliExpress needs more wait time

            if not soup:
                logging.warning("No se pudo obtener contenido de AliExpress")
                return self._get_aliexpress_fallback()

            products = []

            # AliExpress structure - try multiple selectors
            product_items = soup.find_all('div', class_=re.compile(r'list--item|product-item'))

            if not product_items:
                # Try alternative selectors
                product_items = soup.find_all('a', attrs={'class': re.compile(r'product|item')})

            if not product_items:
                logging.info("No se encontraron productos en AliExpress, usando fallback")
                return self._get_aliexpress_fallback()

            for item in product_items[:max_results]:
                try:
                    # Extract price
                    price_elem = item.find('span', class_=re.compile(r'price|Price'))
                    if not price_elem:
                        price_elem = item.find('div', class_=re.compile(r'price|Price'))

                    if price_elem:
                        price_text = price_elem.get_text(strip=True)
                        price = self._extract_price(price_text)

                        if price > 0:
                            # Extract title
                            title_elem = item.find('a', {'title': True})
                            if not title_elem:
                                title_elem = item.find('h1') or item.find('h2') or item.find('h3')

                            title = title_elem.get('title', '') if title_elem else 'Producto similar'
                            if not title:
                                title = title_elem.get_text(strip=True)[:100] if title_elem else 'Producto similar'

                            # Extract product URL
                            product_url = f"https://www.aliexpress.com/wholesale?SearchText={search_term}"
                            link_elem = item.find('a', href=True)
                            if link_elem and link_elem.get('href'):
                                href = link_elem['href']
                                if href.startswith('http'):
                                    product_url = href
                                elif href.startswith('//'):
                                    product_url = 'https:' + href
                                elif href.startswith('/'):
                                    product_url = 'https://www.aliexpress.com' + href

                            # Extract image URL
                            image_url = None
                            img_elem = item.find('img', src=True)
                            if img_elem:
                                image_url = img_elem.get('src') or img_elem.get('data-src')
                                if image_url and image_url.startswith('//'):
                                    image_url = 'https:' + image_url

                            # Extract shipping (if available)
                            shipping_elem = item.find(text=re.compile(r'shipping|envío', re.I))
                            shipping = 0
                            if shipping_elem and 'free' not in shipping_elem.lower():
                                shipping = self._extract_price(shipping_elem)

                            products.append({
                                'title': title,
                                'price': price,
                                'shipping': shipping,
                                'total': price + shipping,
                                'supplier': 'AliExpress',
                                'moq': 1,
                                'url': product_url,
                                'image_url': image_url
                            })
                except Exception as e:
                    logging.debug(f"Error parsing AliExpress item: {e}")
                    continue

            if products:
                logging.info(f"Encontrados {len(products)} productos en AliExpress")
                return products
            else:
                return self._get_aliexpress_fallback()

        except Exception as e:
            logging.error(f"Error scraping AliExpress: {e}")
            return self._get_aliexpress_fallback()

    def _get_aliexpress_fallback(self):
        """Retorna estimación basada en promedios de mercado"""
        logging.info("Usando estimación de precio AliExpress")
        search_term = self.product_name.replace(' ', '+')
        return [{
            'title': f'{self.product_name} (estimado)',
            'price': 0,
            'shipping': 0,
            'total': 0,
            'supplier': 'AliExpress',
            'moq': 1,
            'estimated': True,
            'note': 'Precio no disponible - busca manualmente',
            'url': f"https://www.aliexpress.com/wholesale?SearchText={search_term}",
            'image_url': None
        }]

    def search_alibaba(self, max_results=3):
        """Busca en Alibaba usando Splash"""
        try:
            logging.info(f"Buscando '{self.product_name}' en Alibaba con Splash...")

            search_term = self.product_name.replace(' ', '%20')
            url = f"https://www.alibaba.com/trade/search?SearchText={search_term}"

            soup = self._get_soup(url, wait=5)

            if not soup:
                return self._get_alibaba_fallback()

            products = []

            # Alibaba structure
            product_items = soup.find_all('div', class_=re.compile(r'product|item|card'))

            if not product_items:
                return self._get_alibaba_fallback()

            for item in product_items[:max_results]:
                try:
                    # Extract price range
                    price_elem = item.find('span', class_=re.compile(r'price|Price'))
                    if price_elem:
                        price_text = price_elem.get_text(strip=True)
                        price = self._extract_price(price_text)

                        if price > 0:
                            # Extract MOQ
                            moq_elem = item.find(text=re.compile(r'MOQ|Minimum', re.I))
                            moq = 100  # Default
                            if moq_elem:
                                moq_match = re.search(r'\d+', moq_elem)
                                if moq_match:
                                    moq = int(moq_match.group())

                            title_elem = item.find('a', {'title': True}) or item.find('h2') or item.find('h3')
                            title = title_elem.get('title', '') if title_elem else 'Producto mayorista'
                            if not title:
                                title = title_elem.get_text(strip=True)[:100] if title_elem else 'Producto mayorista'

                            # Extract product URL
                            product_url = url
                            link_elem = item.find('a', href=True)
                            if link_elem and link_elem.get('href'):
                                href = link_elem['href']
                                if href.startswith('http'):
                                    product_url = href
                                elif href.startswith('//'):
                                    product_url = 'https:' + href
                                elif href.startswith('/'):
                                    product_url = 'https://www.alibaba.com' + href

                            # Extract image URL
                            image_url = None
                            img_elem = item.find('img', src=True)
                            if img_elem:
                                image_url = img_elem.get('src') or img_elem.get('data-src')
                                if image_url and image_url.startswith('//'):
                                    image_url = 'https:' + image_url

                            products.append({
                                'title': title,
                                'price': price,
                                'shipping': 0,
                                'total': price,
                                'supplier': 'Alibaba',
                                'moq': moq,
                                'url': product_url,
                                'image_url': image_url
                            })
                except Exception as e:
                    logging.debug(f"Error parsing Alibaba item: {e}")
                    continue

            if products:
                logging.info(f"Encontrados {len(products)} productos en Alibaba")
                return products
            else:
                return self._get_alibaba_fallback()

        except Exception as e:
            logging.error(f"Error scraping Alibaba: {e}")
            return self._get_alibaba_fallback()

    def _get_alibaba_fallback(self):
        """Retorna estimación para Alibaba"""
        logging.info("Usando estimación de precio Alibaba")
        search_term = self.product_name.replace(' ', '%20')
        return [{
            'title': f'{self.product_name} (mayorista estimado)',
            'price': 0,
            'shipping': 0,
            'total': 0,
            'supplier': 'Alibaba',
            'moq': 100,
            'estimated': True,
            'note': 'Precio no disponible - contacta proveedores',
            'url': f"https://www.alibaba.com/trade/search?SearchText={search_term}",
            'image_url': None
        }]

    def _extract_price(self, text):
        """Extrae precio de texto"""
        if not text:
            return 0

        # Remove currency symbols and extract number
        text = text.replace('$', '').replace('US', '').replace(',', '').replace('€', '').replace('£', '')

        # Find first number (including decimals)
        match = re.search(r'(\d+\.?\d*)', text)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                return 0
        return 0

    def search_wholesale_usa(self, max_results=5):
        """Busca en wholesalers de USA usando Splash"""
        try:
            logging.info(f"Buscando '{self.product_name}' en Wholesale USA con Splash...")

            # Clean search term
            search_term = self.product_name.replace(' ', '+')

            # Wholesale Central es un directorio de mayoristas USA
            url = f"https://www.wholesalecentral.com/search.html?search={search_term}"

            soup = self._get_soup(url, wait=4)

            if not soup:
                logging.warning("No se pudo obtener contenido de Wholesale Central")
                return self._get_wholesale_usa_fallback()

            products = []

            # Try to find product listings
            product_items = soup.find_all('div', class_=re.compile(r'product|item|listing'))

            if not product_items:
                # Try alternative selectors
                product_items = soup.find_all('a', attrs={'class': re.compile(r'product|item')})

            if not product_items:
                logging.info("No se encontraron productos en Wholesale USA, usando fallback")
                return self._get_wholesale_usa_fallback()

            for item in product_items[:max_results]:
                try:
                    # Extract price
                    price_elem = item.find('span', class_=re.compile(r'price|Price'))
                    if not price_elem:
                        price_elem = item.find('div', class_=re.compile(r'price|Price'))

                    if price_elem:
                        price_text = price_elem.get_text(strip=True)
                        price = self._extract_price(price_text)

                        if price > 0:
                            # Extract title
                            title_elem = item.find('a', {'title': True})
                            if not title_elem:
                                title_elem = item.find('h2') or item.find('h3')

                            title = title_elem.get('title', '') if title_elem else 'Producto USA'
                            if not title:
                                title = title_elem.get_text(strip=True)[:100] if title_elem else 'Producto USA'

                            # Shipping typically included or low for USA
                            shipping = 0  # USA wholesale usually free shipping or very low

                            products.append({
                                'title': title,
                                'price': price,
                                'shipping': shipping,
                                'total': price + shipping,
                                'supplier': 'Wholesale USA',
                                'moq': 12,  # USA wholesalers typically 12-24 units minimum
                                'url': f"https://www.wholesalecentral.com/search.html?search={search_term}"
                            })
                except Exception as e:
                    logging.debug(f"Error parsing Wholesale USA item: {e}")
                    continue

            if products:
                logging.info(f"Encontrados {len(products)} productos en Wholesale USA")
                return products
            else:
                return self._get_wholesale_usa_fallback()

        except Exception as e:
            logging.error(f"Error scraping Wholesale USA: {e}")
            return self._get_wholesale_usa_fallback()

    def _get_wholesale_usa_fallback(self):
        """Retorna estimación para wholesalers USA"""
        logging.info("Usando estimación de precio Wholesale USA")
        search_term = self.product_name.replace(' ', '+')
        return [{
            'title': f'{self.product_name} (wholesale USA estimado)',
            'price': 0,
            'shipping': 0,
            'total': 0,
            'supplier': 'Wholesale USA',
            'moq': 12,
            'estimated': True,
            'note': 'Precio no disponible - busca en Wholesale Central',
            'url': f"https://www.wholesalecentral.com/search.html?search={search_term}"
        }]

    def search_govdeals(self, max_results=3):
        """Busca en GovDeals.com (subastas gubernamentales USA) usando Splash"""
        try:
            logging.info(f"Buscando '{self.product_name}' en GovDeals con Splash...")

            search_term = self.product_name.replace(' ', '+')
            url = f"https://www.govdeals.com/index.cfm?fa=Main.AdvSearchResultsNew&kWord={search_term}"

            soup = self._get_soup(url, wait=5)

            if not soup:
                logging.warning("No se pudo obtener contenido de GovDeals")
                return self._get_govdeals_fallback()

            products = []

            # GovDeals structure - auction listings
            auction_items = soup.find_all('div', class_=re.compile(r'listing|auction|item'))

            if not auction_items:
                return self._get_govdeals_fallback()

            for item in auction_items[:max_results]:
                try:
                    # Extract current bid price
                    price_elem = item.find('span', class_=re.compile(r'price|bid|current'))
                    if not price_elem:
                        price_elem = item.find('div', class_=re.compile(r'price|bid'))

                    if price_elem:
                        price_text = price_elem.get_text(strip=True)
                        price = self._extract_price(price_text)

                        if price > 0:
                            title_elem = item.find('a', {'title': True}) or item.find('h3') or item.find('h4')
                            title = title_elem.get('title', '') if title_elem else 'Subasta gobierno'
                            if not title:
                                title = title_elem.get_text(strip=True)[:100] if title_elem else 'Subasta gobierno'

                            # GovDeals usually has buyer premium
                            buyer_premium = price * 0.10  # Typical 10% buyer premium

                            products.append({
                                'title': title,
                                'price': price,
                                'shipping': buyer_premium,
                                'total': price + buyer_premium,
                                'supplier': 'GovDeals (Subasta)',
                                'moq': 1,
                                'url': url,
                                'note': 'Precio de subasta actual - puede aumentar'
                            })
                except Exception as e:
                    logging.debug(f"Error parsing GovDeals item: {e}")
                    continue

            if products:
                logging.info(f"Encontrados {len(products)} productos en GovDeals")
                return products
            else:
                return self._get_govdeals_fallback()

        except Exception as e:
            logging.error(f"Error scraping GovDeals: {e}")
            return self._get_govdeals_fallback()

    def _get_govdeals_fallback(self):
        """Retorna fallback para GovDeals"""
        logging.info("No se encontraron subastas en GovDeals")
        search_term = self.product_name.replace(' ', '+')
        return [{
            'title': f'{self.product_name} (no disponible en subastas)',
            'price': 0,
            'shipping': 0,
            'total': 0,
            'supplier': 'GovDeals',
            'moq': 1,
            'estimated': True,
            'note': 'No hay subastas activas para este producto',
            'url': f"https://www.govdeals.com/index.cfm?fa=Main.AdvSearchResultsNew&kWord={search_term}"
        }]

    def search_ebay(self, max_results=5):
        """Busca en eBay (incluye vendedores wholesale) usando Splash"""
        try:
            logging.info(f"Buscando '{self.product_name}' en eBay con Splash...")

            search_term = self.product_name.replace(' ', '+')
            url = f"https://www.ebay.com/sch/i.html?_nkw={search_term}&_sop=15"  # Sort by price lowest

            soup = self._get_soup(url, wait=4)

            if not soup:
                logging.warning("No se pudo obtener contenido de eBay")
                return []

            products = []

            # eBay structure
            product_items = soup.find_all('div', class_=re.compile(r's-item|item'))

            if not product_items:
                product_items = soup.find_all('li', class_=re.compile(r's-item'))

            for item in product_items[:max_results]:
                try:
                    # Extract price
                    price_elem = item.find('span', class_=re.compile(r'price|s-item__price'))
                    if price_elem:
                        price_text = price_elem.get_text(strip=True)
                        price = self._extract_price(price_text)

                        if price > 0:
                            # Extract title
                            title_elem = item.find('h3') or item.find('div', class_=re.compile(r's-item__title'))
                            title = title_elem.get_text(strip=True)[:100] if title_elem else 'Producto eBay'

                            # Extract shipping
                            shipping_elem = item.find('span', class_=re.compile(r'shipping|s-item__shipping'))
                            shipping = 0
                            if shipping_elem:
                                shipping_text = shipping_elem.get_text(strip=True)
                                if 'free' not in shipping_text.lower():
                                    shipping = self._extract_price(shipping_text)

                            products.append({
                                'title': title,
                                'price': price,
                                'shipping': shipping,
                                'total': price + shipping,
                                'supplier': 'eBay',
                                'moq': 1,
                                'url': f"https://www.ebay.com/sch/i.html?_nkw={search_term}"
                            })
                except Exception as e:
                    logging.debug(f"Error parsing eBay item: {e}")
                    continue

            if products:
                logging.info(f"Encontrados {len(products)} productos en eBay")
            return products

        except Exception as e:
            logging.error(f"Error scraping eBay: {e}")
            return []

    def search_walmart(self, max_results=5):
        """Busca en Walmart Marketplace usando Splash"""
        try:
            logging.info(f"Buscando '{self.product_name}' en Walmart con Splash...")

            search_term = self.product_name.replace(' ', '+')
            url = f"https://www.walmart.com/search?q={search_term}"

            soup = self._get_soup(url, wait=5)

            if not soup:
                logging.warning("No se pudo obtener contenido de Walmart")
                return []

            products = []

            # Walmart structure
            product_items = soup.find_all('div', attrs={'data-item-id': True})

            if not product_items:
                product_items = soup.find_all('div', class_=re.compile(r'search-result|product'))

            for item in product_items[:max_results]:
                try:
                    # Extract price
                    price_elem = item.find('span', class_=re.compile(r'price|Price'))
                    if not price_elem:
                        price_elem = item.find('div', class_=re.compile(r'price'))

                    if price_elem:
                        price_text = price_elem.get_text(strip=True)
                        price = self._extract_price(price_text)

                        if price > 0:
                            # Extract title
                            title_elem = item.find('span', class_=re.compile(r'product-title|title'))
                            if not title_elem:
                                title_elem = item.find('a', attrs={'link-identifier': True})

                            title = title_elem.get_text(strip=True)[:100] if title_elem else 'Producto Walmart'

                            products.append({
                                'title': title,
                                'price': price,
                                'shipping': 0,  # Walmart often free shipping
                                'total': price,
                                'supplier': 'Walmart',
                                'moq': 1,
                                'url': f"https://www.walmart.com/search?q={search_term}"
                            })
                except Exception as e:
                    logging.debug(f"Error parsing Walmart item: {e}")
                    continue

            if products:
                logging.info(f"Encontrados {len(products)} productos en Walmart")
            return products

        except Exception as e:
            logging.error(f"Error scraping Walmart: {e}")
            return []

    def search_newegg(self, max_results=5):
        """Busca en Newegg (electrónicos) usando Splash"""
        try:
            logging.info(f"Buscando '{self.product_name}' en Newegg con Splash...")

            search_term = self.product_name.replace(' ', '+')
            url = f"https://www.newegg.com/p/pl?d={search_term}&Order=1"  # Order by price

            soup = self._get_soup(url, wait=4)

            if not soup:
                logging.warning("No se pudo obtener contenido de Newegg")
                return []

            products = []

            # Newegg structure
            product_items = soup.find_all('div', class_=re.compile(r'item-container|item-cell'))

            for item in product_items[:max_results]:
                try:
                    # Extract price
                    price_elem = item.find('li', class_=re.compile(r'price-current'))
                    if not price_elem:
                        price_elem = item.find('span', class_=re.compile(r'price'))

                    if price_elem:
                        price_text = price_elem.get_text(strip=True)
                        price = self._extract_price(price_text)

                        if price > 0:
                            # Extract title
                            title_elem = item.find('a', class_=re.compile(r'item-title'))
                            if not title_elem:
                                title_elem = item.find('img', alt=True)

                            title = title_elem.get_text(strip=True)[:100] if hasattr(title_elem, 'get_text') else (title_elem.get('alt', 'Producto Newegg')[:100] if title_elem else 'Producto Newegg')

                            # Shipping
                            shipping_elem = item.find('li', class_=re.compile(r'price-ship'))
                            shipping = 0
                            if shipping_elem and 'free' not in shipping_elem.get_text(strip=True).lower():
                                shipping = self._extract_price(shipping_elem.get_text(strip=True))

                            products.append({
                                'title': title,
                                'price': price,
                                'shipping': shipping,
                                'total': price + shipping,
                                'supplier': 'Newegg',
                                'moq': 1,
                                'url': f"https://www.newegg.com/p/pl?d={search_term}"
                            })
                except Exception as e:
                    logging.debug(f"Error parsing Newegg item: {e}")
                    continue

            if products:
                logging.info(f"Encontrados {len(products)} productos en Newegg")
            return products

        except Exception as e:
            logging.error(f"Error scraping Newegg: {e}")
            return []

    def search_target(self, max_results=5):
        """Busca en Target usando Splash"""
        try:
            logging.info(f"Buscando '{self.product_name}' en Target con Splash...")

            search_term = self.product_name.replace(' ', '+')
            url = f"https://www.target.com/s?searchTerm={search_term}"

            soup = self._get_soup(url, wait=5)

            if not soup:
                logging.warning("No se pudo obtener contenido de Target")
                return []

            products = []

            # Target structure (React-based, might be harder to scrape)
            product_items = soup.find_all('div', attrs={'data-test': re.compile(r'product|item')})

            if not product_items:
                product_items = soup.find_all('a', href=re.compile(r'/p/'))

            for item in product_items[:max_results]:
                try:
                    # Extract price
                    price_elem = item.find('span', attrs={'data-test': 'current-price'})
                    if not price_elem:
                        price_elem = item.find('span', class_=re.compile(r'price'))

                    if price_elem:
                        price_text = price_elem.get_text(strip=True)
                        price = self._extract_price(price_text)

                        if price > 0:
                            # Extract title
                            title_elem = item.find('a', attrs={'data-test': 'product-title'})
                            if not title_elem:
                                title_elem = item.find('div', class_=re.compile(r'title'))

                            title = title_elem.get_text(strip=True)[:100] if title_elem else 'Producto Target'

                            products.append({
                                'title': title,
                                'price': price,
                                'shipping': 0,  # Target often free shipping
                                'total': price,
                                'supplier': 'Target',
                                'moq': 1,
                                'url': f"https://www.target.com/s?searchTerm={search_term}"
                            })
                except Exception as e:
                    logging.debug(f"Error parsing Target item: {e}")
                    continue

            if products:
                logging.info(f"Encontrados {len(products)} productos en Target")
            return products

        except Exception as e:
            logging.error(f"Error scraping Target: {e}")
            return []

    def search_macys(self, max_results=5):
        """Busca en Macy's usando Splash"""
        try:
            logging.info(f"Buscando '{self.product_name}' en Macy's con Splash...")

            search_term = self.product_name.replace(' ', '%20')
            url = f"https://www.macys.com/shop/search?keyword={search_term}"

            soup = self._get_soup(url, wait=5)

            if not soup:
                logging.warning("No se pudo obtener contenido de Macy's")
                return []

            products = []

            # Macy's structure
            product_items = soup.find_all('div', class_=re.compile(r'productThumbnail|product'))

            for item in product_items[:max_results]:
                try:
                    # Extract price (often shows sale price)
                    price_elem = item.find('span', class_=re.compile(r'sale|price'))
                    if not price_elem:
                        price_elem = item.find('div', class_=re.compile(r'price'))

                    if price_elem:
                        price_text = price_elem.get_text(strip=True)
                        price = self._extract_price(price_text)

                        if price > 0:
                            # Extract title
                            title_elem = item.find('div', class_=re.compile(r'productDescription'))
                            if not title_elem:
                                title_elem = item.find('a', class_=re.compile(r'productTitle'))

                            title = title_elem.get_text(strip=True)[:100] if title_elem else 'Producto Macys'

                            products.append({
                                'title': title,
                                'price': price,
                                'shipping': 0,
                                'total': price,
                                'supplier': "Macy's",
                                'moq': 1,
                                'url': f"https://www.macys.com/shop/search?keyword={search_term}",
                                'note': 'Puede ser precio de liquidación/sale'
                            })
                except Exception as e:
                    logging.debug(f"Error parsing Macy's item: {e}")
                    continue

            if products:
                logging.info(f"Encontrados {len(products)} productos en Macy's")
            return products

        except Exception as e:
            logging.error(f"Error scraping Macy's: {e}")
            return []

    def search_bestbuy(self, max_results=5):
        """Busca en Best Buy usando Splash"""
        try:
            search_term = self.product_name.replace(' ', '+')
            url = f"https://www.bestbuy.com/site/searchpage.jsp?st={search_term}"
            soup = self._get_soup(url, wait=5)
            if not soup:
                return []

            products = []
            items = soup.find_all('li', class_=re.compile(r'sku-item'))

            for item in items[:max_results]:
                try:
                    price_elem = item.find('span', attrs={'aria-hidden': 'true'})
                    if price_elem:
                        price = self._extract_price(price_elem.get_text(strip=True))
                        if price > 0:
                            title_elem = item.find('h4', class_=re.compile(r'sku-title'))
                            title = title_elem.get_text(strip=True)[:100] if title_elem else 'Producto Best Buy'
                            products.append({
                                'title': title, 'price': price, 'shipping': 0, 'total': price,
                                'supplier': 'Best Buy', 'moq': 1,
                                'url': f"https://www.bestbuy.com/site/searchpage.jsp?st={search_term}"
                            })
                except: continue

            if products:
                logging.info(f"Encontrados {len(products)} productos en Best Buy")
            return products
        except Exception as e:
            logging.error(f"Error scraping Best Buy: {e}")
            return []

    def search_homedepot(self, max_results=5):
        """Busca en Home Depot usando Splash"""
        try:
            search_term = self.product_name.replace(' ', '+')
            url = f"https://www.homedepot.com/s/{search_term}"
            soup = self._get_soup(url, wait=4)
            if not soup:
                return []

            products = []
            items = soup.find_all('div', class_=re.compile(r'product-pod|plp-pod'))

            for item in items[:max_results]:
                try:
                    price_elem = item.find('span', class_=re.compile(r'price|Price'))
                    if price_elem:
                        price = self._extract_price(price_elem.get_text(strip=True))
                        if price > 0:
                            title_elem = item.find('span', class_=re.compile(r'product-header'))
                            title = title_elem.get_text(strip=True)[:100] if title_elem else 'Producto Home Depot'
                            products.append({
                                'title': title, 'price': price, 'shipping': 0, 'total': price,
                                'supplier': 'Home Depot', 'moq': 1,
                                'url': f"https://www.homedepot.com/s/{search_term}"
                            })
                except: continue

            if products:
                logging.info(f"Encontrados {len(products)} productos en Home Depot")
            return products
        except Exception as e:
            logging.error(f"Error scraping Home Depot: {e}")
            return []

    def search_lowes(self, max_results=5):
        """Busca en Lowe's usando Splash"""
        try:
            search_term = self.product_name.replace(' ', '+')
            url = f"https://www.lowes.com/search?searchTerm={search_term}"
            soup = self._get_soup(url, wait=4)
            if not soup:
                return []

            products = []
            items = soup.find_all('div', class_=re.compile(r'product-grid'))

            for item in items[:max_results]:
                try:
                    price_elem = item.find('span', class_=re.compile(r'price'))
                    if price_elem:
                        price = self._extract_price(price_elem.get_text(strip=True))
                        if price > 0:
                            title_elem = item.find('div', class_=re.compile(r'description'))
                            title = title_elem.get_text(strip=True)[:100] if title_elem else "Producto Lowe's"
                            products.append({
                                'title': title, 'price': price, 'shipping': 0, 'total': price,
                                'supplier': "Lowe's", 'moq': 1,
                                'url': f"https://www.lowes.com/search?searchTerm={search_term}"
                            })
                except: continue

            if products:
                logging.info(f"Encontrados {len(products)} productos en Lowe's")
            return products
        except Exception as e:
            logging.error(f"Error scraping Lowe's: {e}")
            return []

    def search_costco(self, max_results=5):
        """Busca en Costco usando Splash"""
        try:
            search_term = self.product_name.replace(' ', '+')
            url = f"https://www.costco.com/CatalogSearch?keyword={search_term}"
            soup = self._get_soup(url, wait=5)
            if not soup:
                return []

            products = []
            items = soup.find_all('div', class_=re.compile(r'product|item'))

            for item in items[:max_results]:
                try:
                    price_elem = item.find('div', class_=re.compile(r'price'))
                    if price_elem:
                        price = self._extract_price(price_elem.get_text(strip=True))
                        if price > 0:
                            title_elem = item.find('span', class_=re.compile(r'description'))
                            title = title_elem.get_text(strip=True)[:100] if title_elem else 'Producto Costco'
                            products.append({
                                'title': title, 'price': price, 'shipping': 0, 'total': price,
                                'supplier': 'Costco (Membership)', 'moq': 1,
                                'url': f"https://www.costco.com/CatalogSearch?keyword={search_term}",
                                'note': 'Requiere membresía Costco'
                            })
                except: continue

            if products:
                logging.info(f"Encontrados {len(products)} productos en Costco")
            return products
        except Exception as e:
            logging.error(f"Error scraping Costco: {e}")
            return []

    def search_samsclub(self, max_results=5):
        """Busca en Sam's Club usando Splash"""
        try:
            search_term = self.product_name.replace(' ', '+')
            url = f"https://www.samsclub.com/s/{search_term}"
            soup = self._get_soup(url, wait=5)
            if not soup:
                return []

            products = []
            items = soup.find_all('div', attrs={'data-automation-id': re.compile(r'product')})

            for item in items[:max_results]:
                try:
                    price_elem = item.find('span', attrs={'data-automation-id': 'product-price'})
                    if price_elem:
                        price = self._extract_price(price_elem.get_text(strip=True))
                        if price > 0:
                            title_elem = item.find('span', class_=re.compile(r'product-title'))
                            title = title_elem.get_text(strip=True)[:100] if title_elem else "Producto Sam's Club"
                            products.append({
                                'title': title, 'price': price, 'shipping': 0, 'total': price,
                                'supplier': "Sam's Club (Membership)", 'moq': 1,
                                'url': f"https://www.samsclub.com/s/{search_term}",
                                'note': "Requiere membresía Sam's Club"
                            })
                except: continue

            if products:
                logging.info(f"Encontrados {len(products)} productos en Sam's Club")
            return products
        except Exception as e:
            logging.error(f"Error scraping Sam's Club: {e}")
            return []

    def search_overstock(self, max_results=5):
        """Busca en Overstock.com usando Splash"""
        try:
            search_term = self.product_name.replace(' ', '+')
            url = f"https://www.overstock.com/search?keywords={search_term}"
            soup = self._get_soup(url, wait=4)
            if not soup:
                return []

            products = []
            items = soup.find_all('div', class_=re.compile(r'product-card'))

            for item in items[:max_results]:
                try:
                    price_elem = item.find('span', class_=re.compile(r'price'))
                    if price_elem:
                        price = self._extract_price(price_elem.get_text(strip=True))
                        if price > 0:
                            title_elem = item.find('div', class_=re.compile(r'product-name|title'))
                            title = title_elem.get_text(strip=True)[:100] if title_elem else 'Producto Overstock'
                            products.append({
                                'title': title, 'price': price, 'shipping': 0, 'total': price,
                                'supplier': 'Overstock (Clearance)', 'moq': 1,
                                'url': f"https://www.overstock.com/search?keywords={search_term}",
                                'note': 'Precios de liquidación/clearance'
                            })
                except: continue

            if products:
                logging.info(f"Encontrados {len(products)} productos en Overstock")
            return products
        except Exception as e:
            logging.error(f"Error scraping Overstock: {e}")
            return []

    def search_liquidation_com(self, max_results=5):
        """Busca en Liquidation.com (pallets B2B) usando Splash"""
        try:
            search_term = self.product_name.replace(' ', '+')
            url = f"https://www.liquidation.com/search/?q={search_term}"
            soup = self._get_soup(url, wait=5)
            if not soup:
                return []

            products = []
            items = soup.find_all('div', class_=re.compile(r'lot-tile|auction'))

            for item in items[:max_results]:
                try:
                    price_elem = item.find('span', class_=re.compile(r'current-bid|price'))
                    if price_elem:
                        price = self._extract_price(price_elem.get_text(strip=True))
                        if price > 0:
                            title_elem = item.find('h2') or item.find('div', class_=re.compile(r'title'))
                            title = title_elem.get_text(strip=True)[:100] if title_elem else 'Lote Liquidación'
                            products.append({
                                'title': title, 'price': price, 'shipping': 0, 'total': price,
                                'supplier': 'Liquidation.com (Pallet)', 'moq': 1,
                                'url': f"https://www.liquidation.com/search/?q={search_term}",
                                'note': 'Precio por PALLET/LOTE - verificar cantidad'
                            })
                except: continue

            if products:
                logging.info(f"Encontrados {len(products)} lotes en Liquidation.com")
            return products
        except Exception as e:
            logging.error(f"Error scraping Liquidation.com: {e}")
            return []

    def search_ross(self, max_results=3):
        """Busca en Ross Stores (nota: Ross no vende online, solo referencia de precios)"""
        try:
            logging.info(f"Ross Stores: Estimando precio de descuento...")
            search_term = self.product_name.replace(' ', '+')
            return [{
                'title': f'{self.product_name} (estimado Ross)',
                'price': 0, 'shipping': 0, 'total': 0,
                'supplier': 'Ross Stores (In-Store)', 'moq': 1, 'estimated': True,
                'note': 'Ross solo vende en tienda - visita tu tienda local en Miami',
                'url': 'https://www.rossstores.com/store-locator'
            }]
        except: return []

    def search_bhphoto(self, max_results=5):
        """Busca en B&H Photo Video (mayorista electrónicos NY)"""
        try:
            search_term = self.product_name.replace(' ', '+')
            url = f"https://www.bhphotovideo.com/c/search?q={search_term}"
            soup = self._get_soup(url, wait=4)
            if not soup: return []

            products = []
            items = soup.find_all('div', attrs={'data-selenium': 'miniProductPage'})
            for item in items[:max_results]:
                try:
                    price_elem = item.find('span', attrs={'data-selenium': 'uppedDecimalPriceFirst'})
                    if price_elem:
                        price = self._extract_price(price_elem.get_text(strip=True))
                        if price > 0:
                            title_elem = item.find('span', attrs={'data-selenium': 'miniProductPageProductName'})
                            title = title_elem.get_text(strip=True)[:100] if title_elem else 'Producto B&H'
                            products.append({
                                'title': title, 'price': price, 'shipping': 0, 'total': price,
                                'supplier': 'B&H Photo (Wholesale)', 'moq': 1,
                                'url': f"https://www.bhphotovideo.com/c/search?q={search_term}"
                            })
                except: continue
            if products: logging.info(f"Encontrados {len(products)} en B&H Photo")
            return products
        except Exception as e:
            logging.error(f"Error B&H: {e}")
            return []

    def search_microcenter(self, max_results=5):
        """Busca en Micro Center (electrónicos)"""
        try:
            search_term = self.product_name.replace(' ', '+')
            url = f"https://www.microcenter.com/search/search_results.aspx?N=&cat=&Ntt={search_term}"
            soup = self._get_soup(url, wait=4)
            if not soup: return []

            products = []
            items = soup.find_all('li', class_=re.compile(r'product_wrapper'))
            for item in items[:max_results]:
                try:
                    price_elem = item.find('span', attrs={'itemprop': 'price'})
                    if price_elem:
                        price = self._extract_price(price_elem.get('content', '0'))
                        if price > 0:
                            title_elem = item.find('a', attrs={'data-name': True})
                            title = title_elem.get('data-name', 'Producto MicroCenter')[:100]
                            products.append({
                                'title': title, 'price': price, 'shipping': 0, 'total': price,
                                'supplier': 'Micro Center', 'moq': 1,
                                'url': f"https://www.microcenter.com/search/search_results.aspx?Ntt={search_term}"
                            })
                except: continue
            if products: logging.info(f"Encontrados {len(products)} en Micro Center")
            return products
        except Exception as e:
            logging.error(f"Error Micro Center: {e}")
            return []

    def search_dhgate(self, max_results=5):
        """Busca en DHgate (wholesale China)"""
        try:
            search_term = self.product_name.replace(' ', '+')
            url = f"https://www.dhgate.com/wholesale/search.do?act=search&sus=&searchkey={search_term}"
            soup = self._get_soup(url, wait=5)
            if not soup: return []

            products = []
            items = soup.find_all('li', class_=re.compile(r'item'))
            for item in items[:max_results]:
                try:
                    price_elem = item.find('span', class_=re.compile(r'price'))
                    if price_elem:
                        price = self._extract_price(price_elem.get_text(strip=True))
                        if price > 0:
                            title_elem = item.find('a', class_=re.compile(r'item-title'))
                            title = title_elem.get_text(strip=True)[:100] if title_elem else 'Producto DHgate'
                            products.append({
                                'title': title, 'price': price, 'shipping': 0, 'total': price,
                                'supplier': 'DHgate (China)', 'moq': 1,
                                'url': f"https://www.dhgate.com/wholesale/search.do?searchkey={search_term}"
                            })
                except: continue
            if products: logging.info(f"Encontrados {len(products)} en DHgate")
            return products
        except Exception as e:
            logging.error(f"Error DHgate: {e}")
            return []

    def search_bulq(self, max_results=3):
        """Busca en Bulq.com (liquidation pallets)"""
        try:
            search_term = self.product_name.replace(' ', '+')
            url = f"https://www.bulq.com/search?q={search_term}"
            soup = self._get_soup(url, wait=5)
            if not soup: return []

            products = []
            items = soup.find_all('div', class_=re.compile(r'lot-card|product'))
            for item in items[:max_results]:
                try:
                    price_elem = item.find('span', class_=re.compile(r'price'))
                    if price_elem:
                        price = self._extract_price(price_elem.get_text(strip=True))
                        if price > 0:
                            title_elem = item.find('h3') or item.find('h4')
                            title = title_elem.get_text(strip=True)[:100] if title_elem else 'Pallet Bulq'
                            products.append({
                                'title': title, 'price': price, 'shipping': 0, 'total': price,
                                'supplier': 'Bulq (Pallet)', 'moq': 1,
                                'url': f"https://www.bulq.com/search?q={search_term}",
                                'note': 'Precio por pallet - verificar cantidad/condición'
                            })
                except: continue
            if products: logging.info(f"Encontrados {len(products)} pallets en Bulq")
            return products
        except Exception as e:
            logging.error(f"Error Bulq: {e}")
            return []

    def search_directliquidation(self, max_results=3):
        """Busca en Direct Liquidation (B2B pallets)"""
        try:
            search_term = self.product_name.replace(' ', '+')
            url = f"https://www.directliquidation.com/search?keywords={search_term}"
            soup = self._get_soup(url, wait=5)
            if not soup: return []

            products = []
            items = soup.find_all('div', class_=re.compile(r'lot|auction'))
            for item in items[:max_results]:
                try:
                    price_elem = item.find('span', class_=re.compile(r'price|bid'))
                    if price_elem:
                        price = self._extract_price(price_elem.get_text(strip=True))
                        if price > 0:
                            title_elem = item.find('h2') or item.find('h3')
                            title = title_elem.get_text(strip=True)[:100] if title_elem else 'Pallet DL'
                            products.append({
                                'title': title, 'price': price, 'shipping': 0, 'total': price,
                                'supplier': 'Direct Liquidation (B2B)', 'moq': 1,
                                'url': f"https://www.directliquidation.com/search?keywords={search_term}",
                                'note': 'Pallets B2B - verificar manifesto'
                            })
                except: continue
            if products: logging.info(f"Encontrados {len(products)} pallets en Direct Liquidation")
            return products
        except Exception as e:
            logging.error(f"Error Direct Liquidation: {e}")
            return []

    def search_tjmaxx(self, max_results=3):
        """TJ Maxx (in-store only)"""
        return [{'title': f'{self.product_name} (TJ Maxx)', 'price': 0, 'shipping': 0, 'total': 0,
                'supplier': 'TJ Maxx (In-Store)', 'moq': 1, 'estimated': True,
                'note': 'Solo en tienda - visita Miami locations', 'url': 'https://tjmaxx.tjx.com/store-locator'}]

    def search_marshalls(self, max_results=3):
        """Marshalls (in-store only)"""
        return [{'title': f'{self.product_name} (Marshalls)', 'price': 0, 'shipping': 0, 'total': 0,
                'supplier': 'Marshalls (In-Store)', 'moq': 1, 'estimated': True,
                'note': 'Solo en tienda - visita Miami locations', 'url': 'https://www.marshalls.com/us/store-locator'}]

    def search_kohls(self, max_results=5):
        """Busca en Kohl's"""
        try:
            search_term = self.product_name.replace(' ', '+')
            url = f"https://www.kohls.com/search.jsp?submit-search=web-regular&search={search_term}"
            soup = self._get_soup(url, wait=4)
            if not soup: return []

            products = []
            items = soup.find_all('div', class_=re.compile(r'product'))
            for item in items[:max_results]:
                try:
                    price_elem = item.find('span', class_=re.compile(r'price'))
                    if price_elem:
                        price = self._extract_price(price_elem.get_text(strip=True))
                        if price > 0:
                            title_elem = item.find('div', class_=re.compile(r'title'))
                            title = title_elem.get_text(strip=True)[:100] if title_elem else "Producto Kohl's"
                            products.append({
                                'title': title, 'price': price, 'shipping': 0, 'total': price,
                                'supplier': "Kohl's", 'moq': 1,
                                'url': f"https://www.kohls.com/search.jsp?search={search_term}"
                            })
                except: continue
            if products: logging.info(f"Encontrados {len(products)} en Kohl's")
            return products
        except Exception as e:
            logging.error(f"Error Kohl's: {e}")
            return []

    def search_cvs(self, max_results=3):
        """Busca en CVS Pharmacy"""
        try:
            search_term = self.product_name.replace(' ', '+')
            url = f"https://www.cvs.com/search?searchTerm={search_term}"
            soup = self._get_soup(url, wait=4)
            if not soup: return []

            products = []
            items = soup.find_all('div', class_=re.compile(r'product-tile'))
            for item in items[:max_results]:
                try:
                    price_elem = item.find('span', class_=re.compile(r'price'))
                    if price_elem:
                        price = self._extract_price(price_elem.get_text(strip=True))
                        if price > 0:
                            title_elem = item.find('a', class_=re.compile(r'product'))
                            title = title_elem.get_text(strip=True)[:100] if title_elem else 'Producto CVS'
                            products.append({
                                'title': title, 'price': price, 'shipping': 0, 'total': price,
                                'supplier': 'CVS Pharmacy', 'moq': 1,
                                'url': f"https://www.cvs.com/search?searchTerm={search_term}"
                            })
                except: continue
            if products: logging.info(f"Encontrados {len(products)} en CVS")
            return products
        except Exception as e:
            logging.error(f"Error CVS: {e}")
            return []

    def search_walgreens(self, max_results=3):
        """Busca en Walgreens"""
        try:
            search_term = self.product_name.replace(' ', '+')
            url = f"https://www.walgreens.com/search/results.jsp?Ntt={search_term}"
            soup = self._get_soup(url, wait=4)
            if not soup: return []

            products = []
            items = soup.find_all('div', class_=re.compile(r'product-card'))
            for item in items[:max_results]:
                try:
                    price_elem = item.find('span', class_=re.compile(r'price'))
                    if price_elem:
                        price = self._extract_price(price_elem.get_text(strip=True))
                        if price > 0:
                            title_elem = item.find('h2') or item.find('h3')
                            title = title_elem.get_text(strip=True)[:100] if title_elem else 'Producto Walgreens'
                            products.append({
                                'title': title, 'price': price, 'shipping': 0, 'total': price,
                                'supplier': 'Walgreens', 'moq': 1,
                                'url': f"https://www.walgreens.com/search/results.jsp?Ntt={search_term}"
                            })
                except: continue
            if products: logging.info(f"Encontrados {len(products)} en Walgreens")
            return products
        except Exception as e:
            logging.error(f"Error Walgreens: {e}")
            return []

    def search_fivebelow(self, max_results=3):
        """Busca en Five Below (todo $5 o menos)"""
        try:
            search_term = self.product_name.replace(' ', '+')
            url = f"https://www.fivebelow.com/search?q={search_term}"
            soup = self._get_soup(url, wait=4)
            if not soup: return []

            products = []
            items = soup.find_all('div', class_=re.compile(r'product-tile'))
            for item in items[:max_results]:
                try:
                    price_elem = item.find('span', class_=re.compile(r'price'))
                    if price_elem:
                        price = self._extract_price(price_elem.get_text(strip=True))
                        if price > 0 and price <= 5:  # Five Below - todo $5 o menos
                            title_elem = item.find('a', class_=re.compile(r'name'))
                            title = title_elem.get_text(strip=True)[:100] if title_elem else 'Producto Five Below'
                            products.append({
                                'title': title, 'price': price, 'shipping': 0, 'total': price,
                                'supplier': 'Five Below ($5 store)', 'moq': 1,
                                'url': f"https://www.fivebelow.com/search?q={search_term}",
                                'note': 'Todos los productos $5 o menos'
                            })
                except: continue
            if products: logging.info(f"Encontrados {len(products)} en Five Below")
            return products
        except Exception as e:
            logging.error(f"Error Five Below: {e}")
            return []

    def get_best_supplier_price(self):
        """Obtiene el mejor precio comparando TODOS los proveedores disponibles"""
        all_suppliers = []

        logging.info("=" * 60)
        logging.info(f"INICIANDO BÚSQUEDA EN TODOS LOS PROVEEDORES: {self.product_name}")
        logging.info("=" * 60)

        # 1. CHINA - Wholesale
        logging.info("🇨🇳 Buscando en proveedores de China...")
        alibaba_results = self.search_alibaba(max_results=3)
        if alibaba_results:
            all_suppliers.extend(alibaba_results)
        time.sleep(1)

        aliexpress_results = self.search_aliexpress(max_results=5)
        if aliexpress_results:
            all_suppliers.extend(aliexpress_results)
        time.sleep(1)

        # 2. USA - Wholesale
        logging.info("🇺🇸 Buscando en wholesalers USA...")
        wholesale_usa_results = self.search_wholesale_usa(max_results=3)
        if wholesale_usa_results:
            all_suppliers.extend(wholesale_usa_results)
        time.sleep(1)

        # 3. USA - Subastas Gobierno
        logging.info("🏛️ Buscando en subastas gubernamentales...")
        govdeals_results = self.search_govdeals(max_results=2)
        if govdeals_results:
            all_suppliers.extend(govdeals_results)
        time.sleep(1)

        # 4. eBay - Marketplace
        logging.info("🛒 Buscando en eBay...")
        ebay_results = self.search_ebay(max_results=5)
        if ebay_results:
            all_suppliers.extend(ebay_results)
        time.sleep(1)

        # 5. Walmart - Marketplace
        logging.info("🏪 Buscando en Walmart...")
        walmart_results = self.search_walmart(max_results=5)
        if walmart_results:
            all_suppliers.extend(walmart_results)
        time.sleep(1)

        # 6. Target - Retail
        logging.info("🎯 Buscando en Target...")
        target_results = self.search_target(max_results=3)
        if target_results:
            all_suppliers.extend(target_results)
        time.sleep(1)

        # 7. Newegg - Electronics
        logging.info("💻 Buscando en Newegg...")
        newegg_results = self.search_newegg(max_results=3)
        if newegg_results:
            all_suppliers.extend(newegg_results)
        time.sleep(1)

        # 8. Macy's - Department Store
        logging.info("🏬 Buscando en Macy's...")
        macys_results = self.search_macys(max_results=3)
        if macys_results:
            all_suppliers.extend(macys_results)
        time.sleep(1)

        # 9. Best Buy - Electronics
        logging.info("🔵 Buscando en Best Buy...")
        bestbuy_results = self.search_bestbuy(max_results=3)
        if bestbuy_results:
            all_suppliers.extend(bestbuy_results)
        time.sleep(1)

        # 10. Home Depot - Home/Tools
        logging.info("🔨 Buscando en Home Depot...")
        homedepot_results = self.search_homedepot(max_results=3)
        if homedepot_results:
            all_suppliers.extend(homedepot_results)
        time.sleep(1)

        # 11. Lowe's - Home/Tools
        logging.info("🏠 Buscando en Lowe's...")
        lowes_results = self.search_lowes(max_results=3)
        if lowes_results:
            all_suppliers.extend(lowes_results)
        time.sleep(1)

        # 12. Costco - Wholesale Club
        logging.info("🏪 Buscando en Costco...")
        costco_results = self.search_costco(max_results=3)
        if costco_results:
            all_suppliers.extend(costco_results)
        time.sleep(1)

        # 13. Sam's Club - Wholesale Club
        logging.info("💼 Buscando en Sam's Club...")
        samsclub_results = self.search_samsclub(max_results=3)
        if samsclub_results:
            all_suppliers.extend(samsclub_results)
        time.sleep(1)

        # 14. Overstock.com - Clearance/Closeouts
        logging.info("📦 Buscando en Overstock...")
        overstock_results = self.search_overstock(max_results=3)
        if overstock_results:
            all_suppliers.extend(overstock_results)
        time.sleep(1)

        # 15. Liquidation.com - B2B Liquidations
        logging.info("🚨 Buscando en Liquidation.com...")
        liquidation_results = self.search_liquidation_com(max_results=3)
        if liquidation_results:
            all_suppliers.extend(liquidation_results)
        time.sleep(1)

        # 16. Ross Stores - Discount Retail
        logging.info("💸 Buscando en Ross...")
        ross_results = self.search_ross(max_results=2)
        if ross_results:
            all_suppliers.extend(ross_results)
        time.sleep(1)

        # 17. B&H Photo Video - Electronics Wholesale
        logging.info("📷 Buscando en B&H Photo...")
        bh_results = self.search_bhphoto(max_results=5)
        if bh_results:
            all_suppliers.extend(bh_results)
        time.sleep(1)

        # 18. Micro Center - Electronics
        logging.info("🖥️ Buscando en Micro Center...")
        microcenter_results = self.search_microcenter(max_results=3)
        if microcenter_results:
            all_suppliers.extend(microcenter_results)
        time.sleep(1)

        # 19. DHgate - China Wholesale
        logging.info("🇨🇳 Buscando en DHgate...")
        dhgate_results = self.search_dhgate(max_results=5)
        if dhgate_results:
            all_suppliers.extend(dhgate_results)
        time.sleep(1)

        # 20. Bulq.com - Liquidation Pallets
        logging.info("📦 Buscando en Bulq.com...")
        bulq_results = self.search_bulq(max_results=3)
        if bulq_results:
            all_suppliers.extend(bulq_results)
        time.sleep(1)

        # 21. Direct Liquidation - B2B Pallets
        logging.info("🚚 Buscando en Direct Liquidation...")
        directliq_results = self.search_directliquidation(max_results=3)
        if directliq_results:
            all_suppliers.extend(directliq_results)
        time.sleep(1)

        # 22. TJ Maxx - Discount Retail
        logging.info("🏬 Buscando en TJ Maxx...")
        tjmaxx_results = self.search_tjmaxx(max_results=3)
        if tjmaxx_results:
            all_suppliers.extend(tjmaxx_results)
        time.sleep(1)

        # 23. Marshalls - Discount Retail
        logging.info("🛍️ Buscando en Marshalls...")
        marshalls_results = self.search_marshalls(max_results=3)
        if marshalls_results:
            all_suppliers.extend(marshalls_results)
        time.sleep(1)

        # 24. Kohl's - Department Store
        logging.info("🏪 Buscando en Kohl's...")
        kohls_results = self.search_kohls(max_results=3)
        if kohls_results:
            all_suppliers.extend(kohls_results)
        time.sleep(1)

        # 25. CVS - Pharmacy/Retail
        logging.info("💊 Buscando en CVS...")
        cvs_results = self.search_cvs(max_results=3)
        if cvs_results:
            all_suppliers.extend(cvs_results)
        time.sleep(1)

        # 26. Walgreens - Pharmacy/Retail
        logging.info("💉 Buscando en Walgreens...")
        walgreens_results = self.search_walgreens(max_results=3)
        if walgreens_results:
            all_suppliers.extend(walgreens_results)
        time.sleep(1)

        # 27. Five Below - Discount Store
        logging.info("5️⃣ Buscando en Five Below...")
        fivebelow_results = self.search_fivebelow(max_results=3)
        if fivebelow_results:
            all_suppliers.extend(fivebelow_results)

        logging.info("=" * 60)
        logging.info(f"BÚSQUEDA COMPLETA: {len(all_suppliers)} productos encontrados")
        logging.info(f"Proveedores escaneados: 27+ fuentes diferentes")
        logging.info("=" * 60)

        if not all_suppliers:
            return None

        # Filter out estimated prices for comparison
        real_prices = [s for s in all_suppliers if not s.get('estimated', False) and s['total'] > 0]

        if not real_prices:
            # Return all with note
            return {
                'best_option': all_suppliers[0] if all_suppliers else None,
                'all_options': all_suppliers,
                'total_found': len(all_suppliers),
                'real_prices': 0,
                'note': 'No se encontraron precios reales - estimaciones mostradas'
            }

        # Sort by total price
        real_prices.sort(key=lambda x: x['total'])

        return {
            'best_option': real_prices[0],
            'all_options': all_suppliers,
            'total_found': len(all_suppliers),
            'real_prices': len(real_prices)
        }

    def get_best_supplier_price_fast(self):
        """
        Versión RÁPIDA para escaneo automático
        Solo busca en los 5 proveedores más rápidos y confiables:
        - AliExpress (China)
        - Walmart (USA)
        - eBay (Marketplace)
        - Target (USA Retail)
        - Estimación (fallback)

        Esto reduce el tiempo de ~30s a ~5s por producto
        """
        all_suppliers = []

        logging.info(f"🚀 BÚSQUEDA RÁPIDA: {self.product_name[:50]}...")

        # 1. AliExpress - China (más barato generalmente)
        try:
            aliexpress_results = self.search_aliexpress(max_results=3)
            if aliexpress_results:
                all_suppliers.extend(aliexpress_results)
                logging.info(f"  ✓ AliExpress: {len(aliexpress_results)} productos")
        except Exception as e:
            logging.warning(f"  ✗ AliExpress error: {e}")

        # 2. Walmart - USA (rápido y confiable)
        try:
            walmart_results = self.search_walmart(max_results=3)
            if walmart_results:
                all_suppliers.extend(walmart_results)
                logging.info(f"  ✓ Walmart: {len(walmart_results)} productos")
        except Exception as e:
            logging.warning(f"  ✗ Walmart error: {e}")

        # 3. eBay - Marketplace (muchas opciones)
        try:
            ebay_results = self.search_ebay(max_results=3)
            if ebay_results:
                all_suppliers.extend(ebay_results)
                logging.info(f"  ✓ eBay: {len(ebay_results)} productos")
        except Exception as e:
            logging.warning(f"  ✗ eBay error: {e}")

        # 4. Target - USA Retail
        try:
            target_results = self.search_target(max_results=2)
            if target_results:
                all_suppliers.extend(target_results)
                logging.info(f"  ✓ Target: {len(target_results)} productos")
        except Exception as e:
            logging.warning(f"  ✗ Target error: {e}")

        # Filtrar precios inválidos
        real_prices = [s for s in all_suppliers if s.get('total', 0) > 0]

        if not real_prices:
            logging.info("  ⚠ No se encontraron precios reales")
            return {
                'best_option': None,
                'all_options': [],
                'total_found': 0,
                'real_prices': 0
            }

        # Ordenar por precio total
        real_prices.sort(key=lambda x: x['total'])

        logging.info(f"  💰 Mejor precio: ${real_prices[0]['total']:.2f} en {real_prices[0]['supplier']}")

        return {
            'best_option': real_prices[0],
            'all_options': all_suppliers,
            'total_found': len(all_suppliers),
            'real_prices': len(real_prices)
        }


class SupplierPriceEstimator:
    """Estima precios de proveedores cuando el scraping falla"""

    @staticmethod
    def estimate_supplier_price(amazon_price):
        """
        Estima precio de proveedor basado en precio de Amazon
        Regla general: proveedores chinos = 20-40% del precio Amazon
        """
        if not amazon_price or amazon_price <= 0:
            return {
                'estimated_price': 0,
                'confidence': 'low',
                'note': 'No se pudo estimar sin precio de Amazon'
            }

        # Estimación conservadora: 30% del precio Amazon
        estimated = amazon_price * 0.30

        # Add shipping estimate ($2-5 typical for small items)
        if amazon_price < 20:
            shipping = 2.0
        elif amazon_price < 50:
            shipping = 3.5
        else:
            shipping = 5.0

        return {
            'estimated_price': round(estimated, 2),
            'estimated_shipping': round(shipping, 2),
            'total_estimated': round(estimated + shipping, 2),
            'confidence': 'medium',
            'range_min': round(amazon_price * 0.20 + shipping, 2),  # 20% best case
            'range_max': round(amazon_price * 0.40 + shipping, 2),  # 40% worst case
            'note': 'Estimación: 30% del precio Amazon + shipping',
            'recommendation': 'Busca manualmente en AliExpress para precio exacto'
        }
