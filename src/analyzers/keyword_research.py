"""
Keyword Research - Analiza keywords y volumen de búsqueda
"""
import requests
from bs4 import BeautifulSoup
import re
import logging

logging.basicConfig(level=logging.INFO)


class KeywordResearcher:
    """Investiga keywords de Amazon y su potencial"""

    def __init__(self):
        self.splash_url = 'http://localhost:8050/render.html'

    def get_amazon_suggestions(self, keyword):
        """
        Obtiene sugerencias de Amazon autocomplete

        Args:
            keyword: Keyword base

        Returns:
            list de sugerencias
        """
        url = f"https://completion.amazon.com/api/2017/suggestions?mid=ATVPDKIKX0DER&alias=aps&prefix={keyword}"

        try:
            response = requests.get(url, timeout=10)

            if response.status_code == 200:
                data = response.json()
                suggestions = [item['value'] for item in data.get('suggestions', [])]
                return suggestions[:20]

        except Exception as e:
            logging.error(f"Error obteniendo sugerencias: {e}")

        return []

    def analyze_keyword_competition(self, keyword):
        """
        Analiza competencia de un keyword

        Returns:
            dict con análisis
        """
        search_url = f"https://www.amazon.com/s?k={keyword.replace(' ', '+')}"

        try:
            response = requests.get(
                self.splash_url,
                params={'url': search_url, 'wait': 3},
                timeout=60
            )

            soup = BeautifulSoup(response.content, 'html.parser')

            # Contar resultados
            results_text = soup.find('span', class_=re.compile(r'results'))
            total_results = 0

            if results_text:
                match = re.search(r'([\d,]+)', results_text.get_text())
                if match:
                    total_results = int(match.group(1).replace(',', ''))

            # Analizar primeros productos
            products = soup.find_all('div', {'data-component-type': 's-search-result'})[:10]

            avg_reviews = 0
            avg_rating = 0
            sponsored_count = 0

            for product in products:
                # Reviews
                reviews_elem = product.find('span', class_=re.compile(r'reviews'))
                if reviews_elem:
                    match = re.search(r'([\d,]+)', reviews_elem.get_text())
                    if match:
                        avg_reviews += int(match.group(1).replace(',', ''))

                # Rating
                rating_elem = product.find('span', class_=re.compile(r'rating'))
                if rating_elem:
                    match = re.search(r'([\d.]+)', rating_elem.get_text())
                    if match:
                        avg_rating += float(match.group(1))

                # Sponsored
                if 'Sponsored' in product.get_text():
                    sponsored_count += 1

            avg_reviews = avg_reviews // len(products) if products else 0
            avg_rating = avg_rating / len(products) if products else 0

            # Calcular score de competencia
            competition_score = 0

            if total_results > 10000:
                competition_score += 30
            elif total_results > 5000:
                competition_score += 20
            elif total_results > 1000:
                competition_score += 10

            if avg_reviews > 1000:
                competition_score += 25
            elif avg_reviews > 500:
                competition_score += 15

            if sponsored_count >= 5:
                competition_score += 20

            if competition_score >= 60:
                level = '🔴 ALTA'
            elif competition_score >= 40:
                level = '🟡 MEDIA'
            else:
                level = '🟢 BAJA'

            return {
                'keyword': keyword,
                'total_results': total_results,
                'avg_reviews': avg_reviews,
                'avg_rating': round(avg_rating, 1),
                'sponsored_ads': sponsored_count,
                'competition_score': competition_score,
                'competition_level': level,
                'recommendation': 'ATACAR' if competition_score < 40 else 'DIFÍCIL'
            }

        except Exception as e:
            logging.error(f"Error analizando keyword: {e}")
            return None

    def find_long_tail_keywords(self, base_keyword):
        """Encuentra long-tail keywords (menos competencia)"""
        suggestions = self.get_amazon_suggestions(base_keyword)

        long_tail = []

        for suggestion in suggestions:
            word_count = len(suggestion.split())

            # Long-tail = 3+ palabras
            if word_count >= 3:
                long_tail.append(suggestion)

        return long_tail

    def keyword_opportunity_score(self, keyword_analysis, product_data=None):
        """
        Calcula score de oportunidad para un keyword

        Args:
            keyword_analysis: Resultado de analyze_keyword_competition
            product_data: Datos del producto (opcional)

        Returns:
            Score 0-100
        """
        if not keyword_analysis:
            return 0

        score = 50  # Base

        # Baja competencia = bueno
        comp_score = keyword_analysis.get('competition_score', 50)
        if comp_score < 30:
            score += 30
        elif comp_score < 50:
            score += 15

        # Pocos reviews promedio = más fácil competir
        avg_reviews = keyword_analysis.get('avg_reviews', 0)
        if avg_reviews < 100:
            score += 20
        elif avg_reviews < 500:
            score += 10

        return min(100, score)
