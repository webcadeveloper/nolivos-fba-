"""
Calculadora de rentabilidad para Amazon FBA.
Calcula fees, profit y ROI basado en datos del producto.
"""
import logging

logging.basicConfig(level=logging.INFO)

class FBACalculator:
    # Fees de Amazon (2024)
    REFERRAL_FEE_DEFAULT = 0.15  # 15%
    REFERRAL_FEE_ELECTRONICS = 0.08  # 8%
    
    # Fulfillment fees por peso (Small Standard Size)
    FULFILLMENT_FEES = [
        {'max_weight': 0.5, 'fee': 3.22},
        {'max_weight': 1.0, 'fee': 3.40},
        {'max_weight': 2.0, 'fee': 4.75},
        {'max_weight': 3.0, 'fee': 5.40},
    ]
    
    # Storage fees por pie cúbico
    STORAGE_FEE_JAN_SEP = 0.87  # $/cu ft
    STORAGE_FEE_OCT_DEC = 2.40  # $/cu ft
    
    def __init__(self, product_data: dict, cost_data: dict):
        """
        product_data: dict con price, weight, dimensions, category
        cost_data: dict con product_cost, shipping_cost, month (1-12)
        """
        self.product_data = product_data
        self.cost_data = cost_data
        self.calculation = {}
        
    def calculate_all(self):
        """Calcula todos los fees y rentabilidad"""
        try:
            selling_price = self.product_data.get('price', 0)
            product_cost = self.cost_data.get('product_cost', 0)
            shipping_cost = self.cost_data.get('shipping_cost', 0)
            
            # Calcular fees
            referral_fee = self._calculate_referral_fee(selling_price)
            fulfillment_fee = self._calculate_fulfillment_fee()
            storage_fee = self._calculate_storage_fee()
            
            # Totales
            total_fees = referral_fee + fulfillment_fee + storage_fee
            total_cost = product_cost + shipping_cost + total_fees
            net_profit = selling_price - total_cost
            
            # ROI
            roi = (net_profit / total_cost * 100) if total_cost > 0 else 0
            
            self.calculation = {
                'selling_price': round(selling_price, 2),
                'product_cost': round(product_cost, 2),
                'shipping_cost': round(shipping_cost, 2),
                'referral_fee': round(referral_fee, 2),
                'fulfillment_fee': round(fulfillment_fee, 2),
                'storage_fee': round(storage_fee, 2),
                'total_fees': round(total_fees, 2),
                'total_cost': round(total_cost, 2),
                'net_profit': round(net_profit, 2),
                'roi_percent': round(roi, 2),
                'margin_percent': round((net_profit / selling_price * 100) if selling_price > 0 else 0, 2)
            }
            
            logging.info(f"FBA calculation completed. Net profit: ${net_profit:.2f}, ROI: {roi:.2f}%")
            return self.calculation
            
        except Exception as e:
            logging.error(f"Error in FBA calculation: {e}")
            return None
    
    def _calculate_referral_fee(self, selling_price):
        """Calcula el referral fee basado en categoría"""
        category = self.product_data.get('category', '').lower()
        
        # Categorías con fee reducido
        if 'electronic' in category or 'computer' in category:
            fee_rate = self.REFERRAL_FEE_ELECTRONICS
        else:
            fee_rate = self.REFERRAL_FEE_DEFAULT
        
        return selling_price * fee_rate
    
    def _calculate_fulfillment_fee(self):
        """Calcula el fulfillment fee basado en peso"""
        weight_data = self.product_data.get('weight', {})
        weight = weight_data.get('value', 0)
        
        # Buscar el fee correspondiente
        for tier in self.FULFILLMENT_FEES:
            if weight <= tier['max_weight']:
                return tier['fee']
        
        # Si es más de 3 lb, calcular fee adicional
        if weight > 3.0:
            base_fee = 5.40
            additional_weight = weight - 3.0
            additional_fee = additional_weight * 0.38
            return base_fee + additional_fee
        
        return 5.40  # Default
    
    def _calculate_storage_fee(self):
        """Calcula el storage fee basado en volumen y mes"""
        dimensions = self.product_data.get('dimensions', {})
        length = dimensions.get('length', 0)
        width = dimensions.get('width', 0)
        height = dimensions.get('height', 0)
        
        # Calcular volumen en pies cúbicos
        volume_cubic_inches = length * width * height
        volume_cubic_feet = volume_cubic_inches / 1728  # 1728 in³ = 1 ft³
        
        # Determinar rate según mes
        month = self.cost_data.get('month', 1)
        # FIXED: Usar AND en lugar de OR
        if month >= 10 and month <= 12:  # Oct-Dic
            rate = self.STORAGE_FEE_OCT_DEC
        else:  # Ene-Sep
            rate = self.STORAGE_FEE_JAN_SEP
        
        return volume_cubic_feet * rate
    
    def get_summary(self):
        """Retorna un resumen en español"""
        if not self.calculation:
            self.calculate_all()
        
        calc = self.calculation
        
        summary = f"""
        === ANÁLISIS DE RENTABILIDAD FBA ===
        
        Precio de Venta: ${calc['selling_price']}
        Costo del Producto: ${calc['product_cost']}
        Costo de Envío: ${calc['shipping_cost']}
        
        --- Fees de Amazon ---
        Referral Fee (15%): ${calc['referral_fee']}
        Fulfillment Fee: ${calc['fulfillment_fee']}
        Storage Fee: ${calc['storage_fee']}
        Total Fees: ${calc['total_fees']}
        
        --- Rentabilidad ---
        Costo Total: ${calc['total_cost']}
        Ganancia Neta: ${calc['net_profit']}
        ROI: {calc['roi_percent']}%
        Margen: {calc['margin_percent']}%
        
        {'✅ PRODUCTO RENTABLE' if calc['net_profit'] > 0 and calc['roi_percent'] > 30 else '⚠️ REVISAR RENTABILIDAD'}
        """
        
        return summary
