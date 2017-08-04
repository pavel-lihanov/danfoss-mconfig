#delivery time and price calculator
#abstract class for delivery provider and method
from django.utils.translation import ugettext as _
import devices
from mconfig.models import Order, Profile,Option_prices,Base_price
import openpyxl
import pickle
import zipfile

class Delivery:
    def get_delivery_info(self, package, dest):
        pass
        
class Provider:    
    def __init__(self):
        pass
        
    def have_method(self, meth):        
        return meth in methods and issubclass(type(self), methods[meth])
    
class RailProvider(Provider):
    pass
    
class TruckProvider(Provider):
    pass
    
class SeaProvider(Provider):
    pass

class MyProvider(Provider):
    pass
    
methods = {'truck': TruckProvider, 'rail': RailProvider, 'sea': SeaProvider, 'my': MyProvider}
    

def calculate_capacities(delivery_items, capacities):
    #TODO: calculate optimal number of trucks given capacities and costs
    assert 20 in capacities
    return {20 : len(delivery_items)}
        
class CMA_CGM(TruckProvider):    
    #def __init__(self, price_path):
    def __init__(self, package):
        #TODO: load from xls
        
              
        self.prices = {'Moscow': 6990}
        self.times = {'Moscow': 18}
        
    
    def truck_capacities(self, dest):
        return {20: {self.prices['Moscow']}}
       
    def get_closest_sorting_point(self, dest):
        return 'Moscow'
        
    def get_delivery_info(self, trucks, sorting_point):
        assert len(trucks) == 1 and 20 in trucks
        return self.prices[sorting_point] * trucks[20], self.times[sorting_point]
        
    def get_local_delivery_info(self, trucks, sorting_point, dest):
        return 0.0, 0
        
    def delivery(self, meth):
        if meth == 'truck':
            return TruckDelivery(self)
        else:
            raise KeyError('Method not supported')
        
class TruckDelivery(Delivery):
    def __init__(self, provider):
        self.provider = provider
        
    def get_delivery_info(self, package, dest):
        #get gross weight to determine the number of trucks required
        delivery_items = package.delivery_items()
        capacities = self.provider.truck_capacities(dest) #{5:Costs(dest), 10:Costs(dest), 20:Costs(dest)}
        #find truck combination with lowest price
        trucks = calculate_capacities(delivery_items, capacities)
        sorting_point = self.provider.get_closest_sorting_point(dest)
        price, time = self.provider.get_delivery_info(trucks, sorting_point)
        local_price, local_time = self.provider.get_local_delivery_info(trucks, sorting_point, dest)
        return price + local_price, time + local_time
        
class DanfossLogistics(MyProvider):
    def delivery(self, meth):
        if meth == 'my':
            return MyDelivery(self)
        else:
            raise KeyError('Method not supported')
    
        
class MyDelivery(Delivery):
    def __init__(self, provider):
        self.provider = provider

    def get_delivery_info(self, package, dest):
        '''
        nom_cur=Base_price.objects.filter(nom_voltage=package.attributes['voltage']/1000,current=package.attributes['nom_current']).values('current')    
        for i in nom_cur:
            cur=i['current']

        opt=Option_prices.objects.filter(option_value=package.options['Service access']).values('option_value')
        for i in opt:
            service=i['option_value']
 
        if cur<=61:# and service='Front':
            prices = {'Moscow': 8000}
        elif cur<=61: #and service='Front and back':
            prices = {'Moscow': 14000}
        '''
        
        time = 10
        corp=package.get_frame()
        nom_cur=Base_price.objects.filter(nom_voltage=package.attributes['voltage']/1000,current=package.attributes['nom_current']).values('current')    
        for i in nom_cur:
            cur=i['current']
            print('cur=')
            print(cur)
        if corp.name=='SA01':
            price=8000
        elif cur>61 and cur <96 and corp.name=='SA02':
            price=8000
        elif cur>96 and cur <130 and corp.name=='SA02':
            price=10000
        elif corp.name=='SA03':
            price=10000
        elif corp.name=='DA01':
            price=14000
        elif cur>77 and cur<96 and corp.name=='DA02':
            price=8000
        elif cur>96 and cur<130 and corp.name=='DA02':
            price=10000
        elif corp.name=='DA03':
            price=10000
        else:
            price=_('Ask the manager for more information')
        print('corp=')
        print(corp)
        return price, time        
        
providers = [CMA_CGM(''), DanfossLogistics()]

class SimpleDeliveryDecider:
    def select_delivery(self, details):
        return details[0]
       
    def default_delivery_method(self, package):
        #return 'truck'
        return 'my'
        
    def default_delivery_destination(self, package):
        return 'Moscow'
        
def get_delivery_details(package, decider=SimpleDeliveryDecider()):    
    try:
        meth = package.options['delivery_method']
    except KeyError:
        meth = decider.default_delivery_method(package)
    try:    
        dest = package.options['delivery_address']
    except KeyError:
        dest = decider.default_delivery_destination(package)
         
    provs = [p.delivery(meth) for p in providers if p.have_method(meth)]
    details = [(p.provider, *p.get_delivery_info(package, dest)) for p in provs]
    return decider.select_delivery(details)    
    