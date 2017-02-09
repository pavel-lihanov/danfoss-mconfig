import openpyxl
import pickle
import zipfile

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
        
class VEDACachedPriceList(PriceList):
    def __init__(self, cached_path):
        with zipfile.open(cached_path) as zip:
            with zip.open('price.bin') as f:
                self.prices = pickle.loads(f.read())
            
    @staticmethod
    def create_cache(pricelist_path, cached_path):
        cache = {}
        wb = openpyxl.load_workbook(pricelist_path)
        pricelist = wb.active
        for row in pricelist.iter_rows(min_row=1):
            try:
                #make code from row
                try:                    
                    #code = '{0}-{1}{2}{3}{4}{5}{6}{7}{8:3.0f}{9}{10}A{11}B{12}C{13}D{14}{15}E{16}{17}'.format(
                    code = '{0}-{1}{2}{3}{4}{5}{6}{7}{8:03.0f}{9}{10}A{11}B{12}C{13}D{14}E{15}{16}'.format(
                                           row[NAME_COLUMN].value,                                       
                                           row[POWER_COLUMN].value,     #power
                                           row[VOLTAGE_COLUMN].value,   #voltage
                                           row[5].value,                #frequency
                                           row[6].value,                #protection
                                           row[7].value,                #motor type
                                           row[8].value,                #control mode                                       
                                           row[9].value,                #braking
                                           row[10].value,               #power cell current
                                           row[11].value,               #cooling
                                           row[12].value,               #power cell bypass
                                           row[13].value,               #A
                                           row[14].value,               #B
                                           row[15].value,               #C
                                           row[16].value,               #D
                                           row[17].value,               #mains location
                                           row[18].value,               #E
                                           row[19].value,               #service access
                                           )                    
                except TypeError:
                    raise
                supp_price = float(row[SUPPLIER_PRICE_COLUMN].value)
                sale_price = float(row[SALE_PRICE_COLUMN].value)            
                cache[code] = (supp_price, sale_price)
            except (TypeError, ValueError) as ex:
                #print('Failed to convert row ', code, row[SUPPLIER_PRICE_COLUMN].value, row[SALE_PRICE_COLUMN].value)
                pass
        
        with zipfile.ZipFile(cached_path, 'w', compression=zipfile.ZIP_BZIP2) as zip:
            zip.writestr('price.bin', pickle.dumps(cache))
        
    def get_price(self, package):
        order_code = package.order_code
        if order_code in self.prices:
            p = Price()
            p.supplier_price, p.sale_price = self.prices[order_code]
            return p
        else:
            raise NotInPricelist('{0}: not found in pricelist'.format(package.name))
    
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