import openpyxl

SALE_PRICE_COLUMN = 21
SUPPLIER_PRICE_COLUMN = 20
NAME_COLUMN = 1
POWER_COLUMN = 2
VOLTAGE_COLUMN = 4 

class PriceNotSpecified(Exception):
    pass

class NotInPricelist(Exception):
    pass
    
class PricingError(Exception):
    pass
    
class Price:
    #price struct contains price details
    supplier_price = 0.0
    sale_price = 0.0
    delivery_cost = 0.0
    def __init__(self):
        pass
        
    @property
    def total(self):
        total = self.sale_price + self.delivery_cost
        return total
    
class PriceList:    
    def get_price(self, package):
        raise PricingError('Abstract method')
        
class VEDAXLPriceList(PriceList):
    def __init__(self, pricelist_path):
        self.wb = openpyxl.load_workbook(pricelist_path)
        #TODO: store version in xls file
        self.version = '0.0'
        
    def get_price(self, package):
        pricelist = self.wb.active
        for r in pricelist.iter_rows(min_row=1):
            if self.package_matches_pricelist(r, package):
                price_cell = r[SALE_PRICE_COLUMN]
                supp_price_cell = r[SUPPLIER_PRICE_COLUMN]
                if type(price_cell.value) is float:
                    p = Price()
                    p.sale_price = price_cell.value
                    p.supplier_price = supp_price_cell.value
                    return p
                    #return '{0:.2f}'.format(price_cell.value)                    
                else:
                    raise PriceNotSpecified('Unexpected price value:', price_cell.value)
                    
        raise NotInPricelist('{0}: not found in pricelist'.format(package.name))
        
    def package_matches_pricelist(self, row, package):                
        price_name = '{0}-{1}{2}'.format(row[NAME_COLUMN].value, row[POWER_COLUMN].value, row[VOLTAGE_COLUMN].value)
        if package.name != price_name:
            return False
            
        for name,val in package.options.infos():
            if not val.matches_pricelist(package.options[name], row):
                return False
        
        return True
                
price_lists = {}