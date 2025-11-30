"""
PPC Keyword Harvester - Extrae keywords de competidores y sugiere negative keywords
Nivel Helium 10
"""
import sys
import os
import re
import logging
from typing import List, Dict, Optional
from collections import Counter

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from amzscraper import AmazonWebRobot
from src.scrapers.product_info import ProductInfoScraper
from src.analyzers.keyword_research import KeywordResearcher

logging.basicConfig(level=logging.INFO)


class PPCKeywordHarvester(AmazonWebRobot):
    """Harvest keywords de competidores y productos relacionados"""

    def __init__(self):
        super().__init__()
        self.keyword_researcher = KeywordResearcher()

    def harvest_from_competitors(self, asin: str, max_competitors: int = 10) -> Dict:
        """
        Harvest keywords de productos relacionados y competidores
        
        Args:
            asin: ASIN del producto objetivo
            max_competitors: Número máximo de competidores a analizar
        
        Returns:
            dict con keywords extraídas y su metadata
        """
        try:
            # Obtener información del producto objetivo
            target_scraper = ProductInfoScraper(asin)
            target_data = target_scraper.scrape_product_info()
            
            if not target_data:
                return {
                    'error': 'Could not scrape target product',
                    'keywords': []
                }
            
            target_title = target_data.get('title', '')
            target_category = target_data.get('category', '')
            
            # Keywords extraídas
            all_keywords = set()
            
            # 1. Extraer keywords del título y bullets del producto objetivo
            target_keywords = self._extract_keywords_from_text(target_title)
            all_keywords.update(target_keywords)
            logging.info(f"Extracted {len(target_keywords)} keywords from target product")
            
            # 2. Buscar productos patrocinados (Sponsored Products) relacionados
            sponsored_keywords = self._harvest_from_sponsored_products(asin, target_category)
            all_keywords.update(sponsored_keywords)
            logging.info(f"Extracted {len(sponsored_keywords)} keywords from sponsored products")
            
            # 3. Buscar en "Frequently Bought Together" y "Customers Also Bought"
            related_keywords = self._harvest_from_related_products(asin)
            all_keywords.update(related_keywords)
            logging.info(f"Extracted {len(related_keywords)} keywords from related products")
            
            # 4. Buscar competidores directos (misma categoría, similar BSR)
            competitor_keywords = self._harvest_from_competitors(asin, target_category, max_competitors)
            all_keywords.update(competitor_keywords)
            logging.info(f"Extracted {len(competitor_keywords)} keywords from competitors")
            
            # 5. Analizar cada keyword y obtener metadata
            keywords_with_metadata = []
            for keyword in all_keywords:
                if len(keyword.strip()) > 2:  # Filtrar keywords muy cortas
                    metadata = self._analyze_keyword(keyword, target_category)
                    if metadata:
                        keywords_with_metadata.append(metadata)
            
            # Ordenar por relevancia/potencial
            keywords_with_metadata.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
            
            return {
                'asin': asin,
                'target_product': target_title,
                'total_keywords_found': len(keywords_with_metadata),
                'keywords': keywords_with_metadata[:100],  # Top 100
                'harvested_from': {
                    'target_product': len(target_keywords),
                    'sponsored_products': len(sponsored_keywords),
                    'related_products': len(related_keywords),
                    'competitors': len(competitor_keywords)
                }
            }
            
        except Exception as e:
            logging.error(f"Error harvesting keywords for {asin}: {e}")
            return {
                'error': str(e),
                'keywords': []
            }

    def _extract_keywords_from_text(self, text: str) -> List[str]:
        """Extrae keywords relevantes de un texto (título, bullets, etc.)"""
        if not text:
            return []
        
        keywords = set()
        
        # Dividir en palabras
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        
        # Remover stopwords comunes
        stopwords = {'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had', 'was', 
                    'one', 'our', 'out', 'day', 'get', 'has', 'him', 'his', 'how', 'its', 'may', 
                    'new', 'now', 'old', 'see', 'two', 'who', 'way', 'use', 'her', 'she', 'many',
                    'some', 'time', 'very', 'when', 'come', 'here', 'just', 'like', 'long', 'make',
                    'over', 'such', 'take', 'than', 'them', 'well', 'were', 'what', 'with', 'your'}
        
        # Extraer 1-word keywords (palabras importantes)
        important_words = [w for w in words if w not in stopwords and len(w) > 3]
        keywords.update(important_words)
        
        # Extraer 2-word phrases (bigrams)
        for i in range(len(words) - 1):
            if words[i] not in stopwords and words[i+1] not in stopwords:
                bigram = f"{words[i]} {words[i+1]}"
                if len(bigram) > 5:  # Filtrar frases muy cortas
                    keywords.add(bigram)
        
        # Extraer 3-word phrases (trigrams) para long-tail
        for i in range(len(words) - 2):
            if words[i] not in stopwords and words[i+1] not in stopwords and words[i+2] not in stopwords:
                trigram = f"{words[i]} {words[i+1]} {words[i+2]}"
                if len(trigram) > 8:
                    keywords.add(trigram)
        
        return list(keywords)

    def _harvest_from_sponsored_products(self, asin: str, category: str) -> List[str]:
        """Extrae keywords de productos patrocinados en búsquedas relacionadas"""
        keywords = set()
        
        try:
            # Buscar productos patrocinados en la página del producto
            product_url = f"{self.amazon_link_prefix}/dp/{asin}"
            soup = self.get_soup(product_url)
            
            # Buscar secciones de productos patrocinados
            sponsored_sections = soup.find_all('div', {'data-component-type': 's-impression-logger'})
            
            for section in sponsored_sections:
                # Extraer títulos de productos patrocinados
                titles = section.find_all('span', {'class': re.compile(r'text-normal|a-text-normal', re.I)})
                for title in titles:
                    title_text = title.text.strip()
                    if title_text:
                        extracted = self._extract_keywords_from_text(title_text)
                        keywords.update(extracted)
            
        except Exception as e:
            logging.warning(f"Error harvesting from sponsored products: {e}")
        
        return list(keywords)

    def _harvest_from_related_products(self, asin: str) -> List[str]:
        """Extrae keywords de productos relacionados (Frequently Bought Together, etc.)"""
        keywords = set()
        
        try:
            product_url = f"{self.amazon_link_prefix}/dp/{asin}"
            soup = self.get_soup(product_url)
            
            # Buscar "Frequently Bought Together"
            fbt_section = soup.find('div', {'id': re.compile(r'fbt|frequently-bought', re.I)})
            if fbt_section:
                titles = fbt_section.find_all('span', {'class': re.compile(r'title|product', re.I)})
                for title in titles:
                    title_text = title.text.strip()
                    if title_text:
                        keywords.update(self._extract_keywords_from_text(title_text))
            
            # Buscar "Customers Also Bought"
            cab_section = soup.find('div', {'id': re.compile(r'also-bought|customers', re.I)})
            if cab_section:
                titles = cab_section.find_all('a', {'class': re.compile(r'link|product', re.I)})
                for title in titles:
                    title_text = title.get('title', '') or title.text.strip()
                    if title_text:
                        keywords.update(self._extract_keywords_from_text(title_text))
            
        except Exception as e:
            logging.warning(f"Error harvesting from related products: {e}")
        
        return list(keywords)

    def _harvest_from_competitors(self, asin: str, category: str, max_competitors: int) -> List[str]:
        """Extrae keywords de competidores directos"""
        keywords = set()
        
        try:
            # Obtener producto objetivo para buscar similares
            target_scraper = ProductInfoScraper(asin)
            target_data = target_scraper.scrape_product_info()
            
            if not target_data:
                return []
            
            target_title = target_data.get('title', '')
            target_keywords = target_title.split()[:5]  # Primeras 5 palabras del título
            
            # Buscar productos similares
            search_query = ' '.join(target_keywords)
            search_url = f"{self.amazon_link_prefix}/s?k={search_query.replace(' ', '+')}"
            soup = self.get_soup(search_url)
            
            # Extraer ASINs de competidores
            products = soup.find_all('div', {'data-component-type': 's-search-result'})[:max_competitors]
            
            for product in products:
                # Extraer ASIN
                asin_link = product.find('a', {'class': re.compile(r'link|product', re.I)})
                if asin_link and 'href' in asin_link.attrs:
                    href = asin_link['href']
                    match = re.search(r'/dp/([A-Z0-9]{10})', href)
                    if match:
                        comp_asin = match.group(1)
                        if comp_asin != asin:  # No incluir el producto objetivo
                            # Extraer título del competidor
                            title_elem = product.find('span', {'class': re.compile(r'text-normal|title', re.I)})
                            if title_elem:
                                comp_title = title_elem.text.strip()
                                keywords.update(self._extract_keywords_from_text(comp_title))
            
        except Exception as e:
            logging.warning(f"Error harvesting from competitors: {e}")
        
        return list(keywords)

    def _analyze_keyword(self, keyword: str, category: str) -> Optional[Dict]:
        """Analiza una keyword y retorna metadata"""
        try:
            # Analizar competencia de la keyword
            analysis = self.keyword_researcher.analyze_keyword_competition(keyword)
            
            if not analysis:
                return None
            
            # Calcular relevancia score
            relevance_score = 50  # Base
            
            # Menos competencia = más relevante
            comp_score = analysis.get('competition_score', 50)
            if comp_score < 30:
                relevance_score += 30
            elif comp_score < 50:
                relevance_score += 15
            
            # Más reviews promedio = más popular
            avg_reviews = analysis.get('avg_reviews', 0)
            if avg_reviews > 1000:
                relevance_score += 10
            elif avg_reviews > 500:
                relevance_score += 5
            
            return {
                'keyword': keyword,
                'competition_level': analysis.get('competition_level', 'Unknown'),
                'competition_score': comp_score,
                'avg_reviews': avg_reviews,
                'total_results': analysis.get('total_results', 0),
                'sponsored_ads': analysis.get('sponsored_ads', 0),
                'relevance_score': min(relevance_score, 100),
                'recommendation': 'Use' if relevance_score >= 60 else 'Evaluate'
            }
            
        except Exception as e:
            logging.warning(f"Error analyzing keyword {keyword}: {e}")
            return None

    def get_negative_keywords(self, keyword_list: List[Dict], min_ctr: float = 0.01,
                            min_clicks: int = 10) -> Dict:
        """
        Sugiere negative keywords basado en CTR bajo y performance
        
        Args:
            keyword_list: Lista de keywords con performance data:
                [
                    {
                        'keyword': 'product name',
                        'clicks': 100,
                        'impressions': 10000,
                        'ctr': 0.01,
                        'conversions': 0,
                        'acos': 50.0
                    },
                    ...
                ]
            min_ctr: CTR mínimo aceptable (default 0.01 = 1%)
            min_clicks: Clicks mínimos para considerar (default 10)
        
        Returns:
            dict con negative keywords sugeridas
        """
        negative_keywords = []
        potential_negatives = []
        
        for kw_data in keyword_list:
            keyword = kw_data.get('keyword', '')
            clicks = kw_data.get('clicks', 0)
            impressions = kw_data.get('impressions', 0)
            ctr = kw_data.get('ctr', 0)
            conversions = kw_data.get('conversions', 0)
            acos = kw_data.get('acos', 100)
            
            # Calcular CTR real si no está disponible
            if ctr == 0 and impressions > 0:
                ctr = clicks / impressions
            
            # Criterios para negative keywords
            reasons = []
            
            # 1. CTR muy bajo
            if clicks >= min_clicks and ctr < min_ctr:
                reasons.append(f'CTR bajo: {ctr*100:.2f}% < {min_ctr*100:.1f}%')
            
            # 2. Sin conversiones con muchos clicks
            if clicks >= min_clicks * 2 and conversions == 0:
                reasons.append('Sin conversiones con clicks suficientes')
            
            # 3. ACOS muy alto (no rentable)
            if acos > 100 and clicks >= min_clicks:
                reasons.append(f'ACOS muy alto: {acos:.1f}%')
            
            # 4. Muchas impresiones, pocos clicks
            if impressions >= min_clicks * 100 and clicks < min_clicks:
                reasons.append(f'Muy pocos clicks ({clicks}) para {impressions} impresiones')
            
            if reasons:
                negative_data = {
                    'keyword': keyword,
                    'type': 'exact' if ' ' not in keyword else 'phrase',
                    'reasons': reasons,
                    'performance': {
                        'clicks': clicks,
                        'impressions': impressions,
                        'ctr': round(ctr * 100, 2),
                        'conversions': conversions,
                        'acos': round(acos, 2)
                    },
                    'priority': 'high' if len(reasons) >= 3 else 'medium'
                }
                
                if negative_data['priority'] == 'high':
                    negative_keywords.append(negative_data)
                else:
                    potential_negatives.append(negative_data)
        
        # Agrupar por patrón (para sugerir broad negatives)
        patterns = self._identify_patterns([kw['keyword'] for kw in negative_keywords + potential_negatives])
        
        return {
            'negative_keywords': negative_keywords,
            'potential_negatives': potential_negatives,
            'total_negative': len(negative_keywords),
            'total_potential': len(potential_negatives),
            'patterns': patterns,
            'recommendations': self._get_negative_recommendations(negative_keywords, potential_negatives)
        }

    def _identify_patterns(self, keywords: List[str]) -> Dict:
        """Identifica patrones comunes en negative keywords"""
        patterns = {
            'brands': set(),
            'colors': set(),
            'sizes': set(),
            'common_words': Counter()
        }
        
        color_words = {'red', 'blue', 'green', 'black', 'white', 'yellow', 'pink', 'purple', 'orange'}
        size_words = {'small', 'large', 'medium', 'xl', 'xxl', 'xs', 'big', 'tiny', 'huge'}
        
        for keyword in keywords:
            words = keyword.lower().split()
            
            for word in words:
                if word in color_words:
                    patterns['colors'].add(word)
                elif word in size_words:
                    patterns['sizes'].add(word)
                elif len(word) > 4:
                    patterns['common_words'][word] += 1
        
        return {
            'colors': list(patterns['colors']),
            'sizes': list(patterns['sizes']),
            'common_words': dict(patterns['common_words'].most_common(10))
        }

    def _get_negative_recommendations(self, negatives: List, potential: List) -> List[Dict]:
        """Genera recomendaciones para negative keywords"""
        recommendations = []
        
        if negatives:
            recommendations.append({
                'type': 'immediate',
                'message': f'Agregar {len(negatives)} negative keywords inmediatamente',
                'keywords': [kw['keyword'] for kw in negatives[:5]]
            })
        
        if potential:
            recommendations.append({
                'type': 'review',
                'message': f'Revisar {len(potential)} keywords potencialmente negativas',
                'keywords': [kw['keyword'] for kw in potential[:5]]
            })
        
        return recommendations

