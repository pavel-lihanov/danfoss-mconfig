import json

class HTMLHeaderMixin:
    def __init__(self, field, **kwargs):        
        self.field = field
        #print(self.field, type(self.field))
        self.template = "mconfig/textheader.html"
        
    def as_json(self):
        return {}


class HTMLChoiceMixin:
    def __init__(self, field, **kwargs):        
        self.field = field
        #print(self.field, type(self.field))
        self.template = "mconfig/choice.html"
        
    def as_json(self):
        return {'type': 'Choice',
                           'enabled': self.field.enabled,
                            'data': {'name': self.field.name,                   
                                     'internal_name': self.field.internal_name,
                                        'value': self.field.selected.text if self.field.selected else '',
                                        'choices':  [   {'id': self.field.name + '_' + c.text, 
                                                        'value': c.text, 
                                                        'enabled': c.enabled
                                                        } for c in self.field.choices.values()
                                                    ]
                                    }
                          }

class HTMLSearchChoiceMixin:
    def __init__(self, field, **kwargs):        
        self.field = field
        #print(self.field, type(self.field))
        self.template = "mconfig/searchchoice.html"
    def as_json(self):
        return {'type': 'SearchChoice',
                           'enabled': self.field.enabled,
                            'data': {   'name': self.field.name, 
                                        'internal_name': self.field.internal_name, 
                                        'value': self.field.selected.text if self.field.selected else '', 
                                        'choices':  [   {'id': self.field.name + '_' + c.text, 
                                                        'value': c.text, 
                                                        'enabled': c.enabled} for c in self.field.choices.values()
                                                    ]
                                    }
                          }
        
class HTMLEditMixin:
    def __init__(self, field, **kwargs):
        self.field = field
        #print(self.field)
        self.template = "mconfig/edit.html"
    def as_json(self):
        return {'type': 'Edit',
                           'enabled': True,
                            'data': {   'name': self.field.name, 
                                        'internal_name': self.field.internal_name, 
                                        'value': self.field.value, 
                                    }
                          }                        

class HTMLStreetAddressMixin:
    def __init__(self, field, **kwargs):
        self.field = field
        #print(self.field)
        self.template = "mconfig/streetaddress.html"
        
    def as_json(self):
        loc = None if self.field.location is None else {'lat':self.field.location[0], 'lng': self.field.location[1]}
        return {'type': 'StreetAddress',
                           'enabled': True,
                            'data': {   'name': self.field.name, 
                                        'internal_name': self.field.internal_name, 
                                        'value': self.field.value, 
                                        'location': loc
                                    }
                          }                              

        
class HTMLOneOfManyMixin:
    def __init__(self, field, **kwargs):
        self.field = field
        #print(self.field)
        self.template = "mconfig/oneofmany.html"
        
    def as_json(self):
        return {'type': 'OneOfMany',
                           'enabled': True,
                            'data': {   'name': self.field.name,
                                        'internal_name': self.field.internal_name, 
                                        'fields': [{'name':f[0].name, 'enabled':f[1]} for f in self.field.fields]
                            }
                            }
        
class HTMLCompoundMixin:
    def __init__(self, field, **kwargs):
        self.field = field        
        self.template = "mconfig/compound.html"        
        
    def as_json(self):
        return {'type': 'Compound',
                           'enabled': True,
                            'data': {   'name': self.field.name, 
                                        'internal_name': self.field.internal_name, 
                                    }
                            }

                            
class VEDADriveMixin:
    def __init__(self, package, **kwargs):
        self.package = package
    
    def as_json(self):
        return {'name': self.package.name, 
                'order_code':self.package.order_code(), 
                'options':[{'name': n, 'value': v} for n,v in self.package.options.items()]}
                
class PriceMixin:
    def __init__(self, price, **kwargs):
        self.price = price
        
    def as_json(self, detailed=False):
        if detailed:
            return {'total': self.price.total()}
        else:
            return {'total': self.price.total()}