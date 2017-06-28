#!/usr/bin/python
'''
rules for configurator
'''
import traceback
import functools

class TrueRule:
    def apply(self, device, transform, options):
        return True

class OptionRule:
    def __init__(self, name, value):
        self.name = name
        self.value = value
        
    def apply(self, device, transform, options):
        if self.value in device.options[self.name]:
            pass
        else:
            print('OptionRule.apply: False', self.value, device.options[self.name])
        return self.value in device.options[self.name]

class AttributeRule:
    def __init__(self, name, value):
        self.name = name
        self.value = value
        
    def apply(self, device, transform, options):
        #print('AttributeRule.apply() on ', device)
        #print(self.value, transform(device.attributes, self.name))
        return self.value == transform(device.attributes, self.name)
        
class ValueRule:
    def __init__(self, name, valuegetter):
        self.name = name
        self.valuegetter = valuegetter
        
class Transform:
    def __init__(self):
        self.transformers = {}
        
    def __call__(self, source, key):
        if key in self.transformers:
            return self.transformers[key](source[key])
        else:
            return source[key]
            
class CurrentGreater(ValueRule):
    def __init__(self, valuegetter=None):
        ValueRule.__init__(self, 'current', valuegetter)
                
    def apply(self, device, transform, options):
        if self.valuegetter is None:
            print('CurrentGreater: WARNING: no way to get value')
            return True
        #print('CurrentGreater.apply()')
        #print('Mod current', self.transform, self.transform(device.attributes['current']))
        #print(transform(device.attributes, 'current'), '>=?', self.valuegetter())
        #return self.transform(device.attributes['current']) >= self.valuegetter()
        return transform(device.attributes, 'current') >= self.valuegetter()

#TODO: not really sure if it works
class Wrapper:
    def __init__(self, f, wrapped):
        self.wrapped = wrapped
        self.f = f
        
    def __call__(self, *args):
        return self.f(self.wrapped(*args))

#functions for making partials
#partial will capture first arg 
def sub(a,b):
    return b-a
    
def div(a, b):
    return b/a
    
class CurrentMultRule:
    '''
    it works with CurrentGreater rule
    '''
    def __init__(self, curr_rule, mult):
        self.mult = mult
        self.curr_rule = curr_rule      
            
    def apply(self, device, transform, options):
        #print('CurrentMultRule.apply()')
        if 'current' not in transform.transformers:
            #print('no transform')
            #transform.transformers['current'] = lambda c: c / self.mult
            transform.transformers['current'] = functools.partial(div, self.mult)
        else:
            #print('transform')
            #check if it will work with lambdas
            transform.transformers['current'] = Wrapper(functools.partial(div, self.mult), transform.transformers['current'])

        #print('apply transform', self, self.mult)
        return self.curr_rule.apply(device, transform)


class CurrentAddRule:
    '''
    it works with CurrentGreater rule
    '''
    def __init__(self, curr_rule, mult):
        self.mult = mult
        self.curr_rule = curr_rule      
            
    def apply(self, device, transform, options):        
        if 'current' not in transform.transformers:
            transform.transformers['current'] = functools.partial(sub, self.mult)
        else:
            #check if it will work with lambdas
            transform.transformers['current'] = Wrapper(functools.partial(sub, self.mult), transform.transformers['current'])

        #print('apply transform', self, self.mult)
        return self.curr_rule.apply(device, transform)
        
class OverloadRule:
    def __init__(self, k, curr_getter):
        self.k = k
        self.curr_getter = curr_getter
        
    def apply(self, device, transform, options):
        overload = device.attributes['overload_current']
        req = self.k * self.curr_getter()
        return overload > req
        
class VariableOverloadRule:
    def __init__(self, k_getter, curr_getter):
        self.k_getter = k_getter
        self.curr_getter = curr_getter
        
    def apply(self, device, transform, options):
        overload = device.attributes['overload_current']
        req = self.k_getter() * self.curr_getter()
        return overload > req
    
class CurrentRule:
    def __init__(self, curr_getter):
        self.curr_getter = curr_getter
        
    def apply(self, device, transform, options):
        my_cur = device.attributes['nom_current']
        req_cur = self.curr_getter()        
        #TODO - do not oversize, should be checked by devices
        if req_cur > 0:
            return my_cur >= req_cur * 0.9999 and my_cur < req_cur * 1.3
        else:
            return True

class CurrentLesserRule:
    def __init__(self, curr_getter):
        self.curr_getter = curr_getter
        
    def apply(self, device, transform, options):        
        return device.attributes['nom_current'] < self.curr_getter()

        
class CanSeeDeliveryRule:
    def __init__(self, user_getter):
        self.user_getter = user_getter
        
    def apply(self, device, transform, options):
        user = self.user_getter()
        if user is not None:
            allowed = user.has_perm('mconfig.view_delivery')
            return allowed
        else:
            return True
            
class CanUseBypassRule:
    def __init__(self, **args):
        pass
        
    def apply(self, device, transform, options):
        #print('CanUseBypassRule.apply()')
        if 'motor_voltage' in options:
            #print(device.attributes['voltage'], options['motor_voltage'], type(device.attributes['voltage']), type(options['motor_voltage']))
            #print(device.attributes['voltage'] == options['motor_voltage'])
            #if device.attributes['voltage'] != options['motor_voltage']:
            #    print('CanUseBypassRule.apply(): False', device.attributes['voltage'], '!=', options['motor_voltage'])
            return device.attributes['voltage'] == options['motor_voltage']
        else:
            #print('CanUseBypassRule.apply(): False (no motor_voltage)')
            return False
    
class OptionIfGreater:
    def __init__(self, getter, value, option, values):
        self.getter = getter
        self.value = value
        self.option = option
        self.values = values
        
    def apply(self, device, transform, options):
        val = self.getter()
        if val <= self.value:
            return self.values[0] in device.options[self.option]
        else:
            return self.values[1] in device.options[self.option]
        
class RuleAndChain:
    def __init__(self, *rules):
        self.rules = rules[:]
        
    def apply(self, device, transform, options):
        for rule in self.rules:
            res = rule.apply(device, transform, options)
            #print('RuleAndChain: applied ', rule, ':', res)
            if not res:
                #print('RuleAndChain.apply()', rule, 'False')
                return False
        return True
                
class RuleOrChain:
    def __init__(self, *rules):
        self.rules = rules[:]
        
    def apply(self, device, transform, options):
        for rule in self.rules:
            if rule.apply(device, transform, options):
                return True
        return False
