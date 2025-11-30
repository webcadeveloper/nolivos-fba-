-- ============================================================================
-- QUERIES ÚTILES PARA ANÁLISIS FBA
-- ============================================================================

-- 1. PRODUCTOS FBA COMPLIANT CON ALTA RENTABILIDAD
-- Encuentra productos que cumplen FBA y tienen buen ROI/profit
-- ============================================================================
SELECT
    asin,
    product_name,
    amazon_price,
    supplier_price,
    roi_percent,
    net_profit,
    fba_size_tier,
    product_weight,
    review_count,
    product_rating
FROM opportunities
WHERE fba_compliant = 1
  AND roi_percent > 30
  AND net_profit > 10
ORDER BY roi_percent DESC, net_profit DESC
LIMIT 20;

-- ============================================================================
-- 2. PRODUCTOS CON VIOLACIONES FBA
-- Identifica productos que NO cumplen con FBA (para evitarlos)
-- ============================================================================
SELECT
    asin,
    product_name,
    amazon_price,
    fba_compliant,
    fba_warnings,
    fba_size_tier
FROM opportunities
WHERE fba_compliant = 0
ORDER BY last_updated DESC;

-- ============================================================================
-- 3. PRODUCTOS STANDARD-SIZE (más rentables)
-- Filtra solo productos con size tier "standard" para maximizar profit
-- ============================================================================
SELECT
    asin,
    product_name,
    amazon_price,
    roi_percent,
    net_profit,
    fba_size_tier,
    product_length,
    product_width,
    product_height,
    product_weight
FROM opportunities
WHERE fba_size_tier = 'standard'
  AND fba_compliant = 1
  AND roi_percent > 25
ORDER BY roi_percent DESC
LIMIT 50;

-- ============================================================================
-- 4. PRODUCTOS LIGEROS Y COMPACTOS (IDEALES)
-- Encuentra productos pequeños y ligeros (fees más bajos)
-- ============================================================================
SELECT
    asin,
    product_name,
    amazon_price,
    roi_percent,
    net_profit,
    product_weight,
    product_length,
    product_width,
    product_height,
    review_count,
    product_rating
FROM opportunities
WHERE product_weight > 0
  AND product_weight < 1.0  -- Menos de 1 lb
  AND fba_compliant = 1
  AND roi_percent > 20
ORDER BY net_profit DESC
LIMIT 30;

-- ============================================================================
-- 5. PRODUCTOS CON ALTA DEMANDA (reviews)
-- Filtra productos validados por el mercado (muchas reviews)
-- ============================================================================
SELECT
    asin,
    product_name,
    amazon_price,
    review_count,
    product_rating,
    roi_percent,
    net_profit,
    fba_compliant,
    fba_size_tier
FROM opportunities
WHERE review_count > 1000
  AND product_rating >= 4.0
  AND fba_compliant = 1
  AND roi_percent > 15
ORDER BY review_count DESC, net_profit DESC;

-- ============================================================================
-- 6. ANÁLISIS DE ADVERTENCIAS FBA
-- Cuenta cuántos productos tienen cada tipo de advertencia
-- ============================================================================
SELECT
    fba_compliant,
    fba_size_tier,
    COUNT(*) as total_products,
    ROUND(AVG(roi_percent), 2) as avg_roi,
    ROUND(AVG(net_profit), 2) as avg_profit
FROM opportunities
WHERE fba_size_tier IS NOT NULL
GROUP BY fba_compliant, fba_size_tier
ORDER BY fba_compliant DESC, avg_roi DESC;

-- ============================================================================
-- 7. TOP PRODUCTOS IDEALES PARA FBA
-- Combina múltiples criterios FBA para encontrar los mejores
-- ============================================================================
SELECT
    asin,
    product_name,
    amazon_price,
    roi_percent,
    net_profit,
    fba_size_tier,
    product_weight,
    review_count,
    product_rating,
    competitiveness_level
FROM opportunities
WHERE fba_compliant = 1
  AND fba_size_tier = 'standard'
  AND product_weight > 0 AND product_weight < 2.0
  AND review_count > 500
  AND product_rating >= 4.0
  AND roi_percent > 25
  AND net_profit > 8
ORDER BY
    roi_percent DESC,
    net_profit DESC,
    review_count DESC
LIMIT 10;

-- ============================================================================
-- 8. PRODUCTOS POR SIZE TIER
-- Compara rentabilidad entre diferentes size tiers
-- ============================================================================
SELECT
    fba_size_tier,
    COUNT(*) as total_products,
    ROUND(AVG(amazon_price), 2) as avg_price,
    ROUND(AVG(product_weight), 2) as avg_weight,
    ROUND(AVG(roi_percent), 2) as avg_roi,
    ROUND(AVG(net_profit), 2) as avg_profit,
    ROUND(AVG(amazon_fees), 2) as avg_fees
FROM opportunities
WHERE fba_size_tier IS NOT NULL
  AND fba_size_tier != 'Unknown'
GROUP BY fba_size_tier
ORDER BY avg_roi DESC;

-- ============================================================================
-- 9. PRODUCTOS CON MEJOR RATING Y BUENA RENTABILIDAD
-- Productos probados por el mercado + rentables
-- ============================================================================
SELECT
    asin,
    product_name,
    amazon_price,
    product_rating,
    review_count,
    roi_percent,
    net_profit,
    fba_size_tier,
    competitiveness_level
FROM opportunities
WHERE product_rating >= 4.5
  AND review_count >= 100
  AND fba_compliant = 1
  AND roi_percent > 20
ORDER BY product_rating DESC, review_count DESC
LIMIT 25;

-- ============================================================================
-- 10. DASHBOARD COMPLETO DE OPORTUNIDADES FBA
-- Vista comprensiva de las mejores oportunidades
-- ============================================================================
SELECT
    asin,
    SUBSTR(product_name, 1, 50) || '...' as product_name_short,
    '$' || ROUND(amazon_price, 2) as price,
    ROUND(roi_percent, 1) || '%' as roi,
    '$' || ROUND(net_profit, 2) as profit,
    CASE fba_compliant
        WHEN 1 THEN '✅'
        ELSE '❌'
    END as fba_ok,
    fba_size_tier as tier,
    ROUND(product_weight, 2) || ' lbs' as weight,
    product_rating || '⭐' as rating,
    review_count as reviews,
    competitiveness_level as level
FROM opportunities
WHERE fba_compliant = 1
  AND roi_percent > 20
  AND net_profit > 5
ORDER BY roi_percent DESC
LIMIT 50;

-- ============================================================================
-- 11. ESTADÍSTICAS GENERALES FBA
-- Overview de todos los productos por cumplimiento FBA
-- ============================================================================
SELECT
    'FBA Compliant' as category,
    COUNT(*) as total_products,
    ROUND(AVG(roi_percent), 2) as avg_roi,
    ROUND(AVG(net_profit), 2) as avg_profit,
    ROUND(MIN(roi_percent), 2) as min_roi,
    ROUND(MAX(roi_percent), 2) as max_roi
FROM opportunities
WHERE fba_compliant = 1

UNION ALL

SELECT
    'NOT FBA Compliant' as category,
    COUNT(*) as total_products,
    ROUND(AVG(roi_percent), 2) as avg_roi,
    ROUND(AVG(net_profit), 2) as avg_profit,
    ROUND(MIN(roi_percent), 2) as min_roi,
    ROUND(MAX(roi_percent), 2) as max_roi
FROM opportunities
WHERE fba_compliant = 0 OR fba_compliant IS NULL;

-- ============================================================================
-- 12. PRODUCTOS PARA INVESTIGAR MÁS
-- Productos con warning pero aún rentables
-- ============================================================================
SELECT
    asin,
    product_name,
    amazon_price,
    roi_percent,
    net_profit,
    fba_warnings,
    fba_size_tier
FROM opportunities
WHERE fba_compliant = 1
  AND fba_warnings != '[]'
  AND roi_percent > 30
ORDER BY roi_percent DESC
LIMIT 20;
