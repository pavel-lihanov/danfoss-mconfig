#!/usr/bin/python
'''
simple text-based wizard
'''
import rules
import collections
import locale
import itertools
from typing import Sequence, Any
import devices
import price

from django.utils.translation import ugettext as _
from mconfig.models import User, Order

class ValidationError(Exception):
    '''
    raised to notify wizard that it should not proceed with current selections
    '''
    def __init__(self, msg: str) -> None:
        Exception.__init__(self, msg)
        self.message = msg
        
class NoMatches(Exception):
    pass
    
class InvalidView:
    def __init__(self, **kwargs):
        print('Warning: no view was provided')
        print(self, kwargs)

class Field:
    '''
    base class for field
    override 
    def select(self, choice, devs, opts):
        sets value choice if any of devs matches it, raise exception otherwise, remember old value
    
    def undo(self):
        restore previous value
            
    def filter(self, devs):
        return subset of devs that matches currently set value
                        
    def get_rules(self):
        return currently active rules     
        
    def is_valid(self, devs):
        return True if the current value is valid for any of devs 
        
    def get_option(self):
        return options associated with current value
        
    def update(self, devs, opts):
        update state based on devs and opts
        
    def validate(self):
        raise exception if wizard should not proceed with current value (e. g. required field with empty selection)
    
    '''
    def __init__(self, name: str, internal_name: str, required: bool = False, **kwargs) -> None:
        self.name = name
        self.required = required
        self.internal_name = internal_name
        if 'hint' in kwargs:
            self.hint = kwargs['hint']
        else:
            self.hint = ''
            
        self.on_changing = []
        self.on_changed = []

            
    def init_view(self, views: Sequence[Any], **kwargs):
        '''
        creates view for field, expects dict of view factories
        '''
        if self.__class__ in views:
            #print(self, 'has view', views[self.__class__])
            #views[self.__class__].__init__(self, **kwargs)
            #print(views[self.__class__])
            self.view = views[self.__class__](self, **kwargs)
        else:
            print('Warning: no view for ', self.__class__)
            self.view = InvalidView(self, **kwargs)
            
    def get_fields(self):
        '''
        should return list of active child fields + this field
        '''
        return [self]
        
class Choice:
    '''
    predefined value for choice field
    each choice has a rule and a set of options
    '''
    #NOTE: options act as additional filter, choices with options not containing already selected options will be disabled
    #e.g.:  field1 has choices f1c1(options {'a': 1}), f1c2(options {'a': 2}), 
    #       field 2 has options f2c1(options{'b': 2, 'a': 2}), f2c2(options{})
    #       then if f1c1 is selected in f1 only f2c2 will be available in c2
    #       if f1c2 is selected both f2c1 and f2c2 will be available
    def __init__(self, text: str, rule: Any, options = {}, mean: bool = True) -> None:
        self.enabled = True
        self.text = text
        self.rule = rule
        self.options = dict(options)
        self.mean = mean
        
    def __repr__(self):
        return ('+' if self.enabled else '-') + self.text
        
    def validate(self):
        pass
        
class ChoiceField(Field):
    '''
    field that allows selection from a list of predefined values
    '''
    def __init__(self, name, internal_name, choices, devs, views, **kwargs):
        Field.__init__(self, name, internal_name, **kwargs)
        #self.choices = {c.text: c for c in choices}
        self.choices = collections.OrderedDict()
        for c in choices:
            self.choices[c.text] = c
            
        self.selected = None
        self.update(devs)
        self.init_view(views, **kwargs)
        self.enabled = True
        
    def is_valid(self, devs):
        res = 0
        self.update(devs)
        for choice in self.choices.values():
            if choice.enabled:
                #print('Choice enabled', choice)
                res +=1
            else:
                pass
                #print('Choice disabled', choice)

        assert(res >= 1)
        return res > 1
                
    def get_valid_choices(self, devs, opts):
        valid_choices = []
        devs = [(d, rules.Transform()) for d in devs]
        for choice in self.choices.values():
            #newdevs = [d for d in filter(choice.rule.apply, devs)]
            newdevs = [d for d,t in devs if choice.rule.apply(d, transform, opts)]
            if len(newdevs) > 0:
                valid_choices.append(choice)                

        return valid_choices
        

    def update(self, devs, opts={}):
        #print(self.choices)
        #check what choices are valid for subset of devices     
        for choice in self.choices.values():
            #newdevs = [d for d in filter(choice.rule.apply, devs)]
            #NOTE: choices should not save their transforms
            #ds = [(d, rules.Transform()) for d in devs]
            #newdevs = [d for d,t in ds if choice.rule.apply(d, t)]
            #print('Update: choice', choice, 'was', choice.enabled)
            if not devs:
                print('Will surely be disabled (no devs)', choice, choice.rule, opts)
            newdevs = self.filter(devs, choice.rule, opts)
            choice.enabled = len(newdevs) > 0
            if not choice.enabled:
                print('Disabled (no devs)', choice, choice.rule, opts)
                
            #print('Update: choice', choice, choice.enabled)            
            #print(choice.options)
            for opt,val in opts.items():
                if opt in choice.options:                    
                    if val == choice.options[opt]:
                        pass
                    elif isinstance(choice.options[opt], collections.Iterable) and val in choice.options[opt]:
                        pass
                    else:
                        #print('Disabled', self, opt, opts)
                        choice.enabled = False            
                
        valid_choices = [c for c in self.choices.values() if c.enabled]
                
        if not valid_choices:
            print('Field', self.name, 'no valid choices!')
            print([c for c in self.choices.values()])
            raise ValidationError(self.name)        
        
        mean_choices = [c for c in valid_choices if c.mean]     

        if len(mean_choices) == 1:
            self.selected = mean_choices[0]
                    
        if self.selected is None or self.selected not in valid_choices:
            #TODO: let user customize the logic of selecting valid choice
            self.selected = valid_choices[0]
                                
        self.enabled = len(mean_choices) > 1
        #print(self.name, 'Enabled' if self.enabled else 'Disabled')
            
    def validate(self):
        #option with empty text is considered unspecified
        if self.required and (self.selected is None or self.selected.text == ''):
            raise ValidationError(_('Field {0} is required').format(self.name))
             
    def _force_select(self, choice):
        self.selected = choice
        
    def select(self, choice, devs, opts):
        #if not choice:
        #   choice = decider.select_option()
        #transform = rules.Transform()
        self.old = self.selected
        if choice in self.choices:
            #print(choice, "in choices")
            choice = self.choices[choice]
            #print(choice, choice.rule)
            #ds = [(d, rules.Transform()) for d in devs]
            #newdevs = [d for d,t in ds if choice.rule.apply(d, t)]
            newdevs = self.filter(devs, choice.rule, opts)
            #newdevs = [d for d in filter(choice.rule.apply, devs)]
            #assert(newdevs)
            if not newdevs:
                raise NoMatches('No device matches choice {0} in {1}'.format(choice, self))
            self.selected = choice
            self.update(newdevs, opts)
            #print(choice, "selected in ", self)
            for s in self.on_changed:
                s(self)
            return newdevs
        else:
            print("Warning, ", choice, "not in choices of ", self)              
            raise ValueError('{0} is not a valid choice of {1}'.format(choice, self))
                    
            
    def undo(self):
        self.selected = self.old
            
            
    def filter(self, devs, rule, opts):
        #newdevs = [d for d in filter(self.selected.rule.apply, devs)]
        #transform = rules.Transform()
        ds = [(d, rules.Transform()) for d in devs]
        newdevs = [d for d,t in ds if rule.apply(d, t, opts)]
        return newdevs
            
    def __repr__(self):
        return '{0}: {1} ({2})'.format(self.name, self.selected if self.selected else '', ' '.join([c.text for c in self.choices.values()]))
    
    def hint(self):
        valid_choices = [c for c in self.choices.values() if c.enabled]
        return ', '.join([c.text for c in valid_choices])
        
    '''
    def get_rule(self):
        return None if self.selected is None else self.selected.rule
    '''
    
    def get_rules(self):
        return [] if self.selected is None else [self.selected.rule]
        
    def get_option(self):
        return self.selected.options
        
#TODO: move to views
class SearchChoiceField(ChoiceField):
    '''
    the same as ChoiceField, to distinguish which templcate should be used
    '''
    pass
        
class ValueField(Field):
    '''
    field that allows to enter a numerical value
    '''
    def __init__(self, name, internal_name, rule, views, **kwargs):
        Field.__init__(self, name, internal_name, **kwargs)
        self.rule = rule
        self.value = None
        self.init_view(views, **kwargs)
        self.min = 0
        self.max = 0
        
    def _force_select(self, choice):
        self.value = locale.atof(choice)
        
    def select(self, choice, devs, opts):
        #print('ValueField.select() from', len(devs), 'devices')
        self.old = self.value
        try:
            self.value = locale.atof(choice)
            #self.value = float(choice)
            #print('{0} selected in {1}'.format(self.value, self))
        except ValueError:
            print('Invalid value: {0}'.format(choice))
            raise
            #return devs
        
        #newdevs = [d for d in filter(self.rule.apply, devs)]
        #transform = rules.Transform()
        #newdevs = [d for d in devs if self.rule.apply(d, transform)]
        newdevs = self.filter(devs, opts)
        if newdevs:
            for s in self.on_changed:
                s(self)        
            return newdevs
        else:
            self.value = self.old
            raise NoMatches('') 

    def undo(self):
        self.value = self.old
        print('ValueField.undo(): value is now', self.old)
            
    def filter(self, devs, opts):
        ds = [(d, rules.Transform()) for d in devs]
        #valuefield has only 1 rule
        newdevs = [d for d,t in ds if self.rule.apply(d, t, opts)]
        return newdevs
                        
    def get_rules(self):
        return [self.rule]
    
    def __repr__(self):
        return '{0}: {1}'.format(self.name, self.value)
        
    def hint(self):
        return ''
        
    def is_valid(self, devs):
        return True
        
    def get_option(self):
        return {}
        
    def update(self, devs, opts):
        pass
        
    def validate(self):
        if self.required and self.value is None:
            raise ValidationError(_('Field {0} is required').format(self.name))

#NOTE: it may be helpful to filter and check validity with different rules
class StreetAddressField(Field):
    '''
    field for specifying delivery address
    stores coordinates (lat, lng) and region
    '''
    def __init__(self, name, internal_name, rule, views, **kwargs):
        Field.__init__(self, name, internal_name, **kwargs)
        self.rule = rule
        #human-readable region 
        self.value = None
        #coordinates
        self.location = None
        self.init_view(views, **kwargs)
 
    def select(self, choice, devs, opts):
        print('StreetAddressField: selected', choice)
        self.value, loc = choice.split('/')        
        lat, lng = loc[1: -1].split(',')
        self.location = (lat.strip(), lng.strip())
        
    def undo(self):
        pass
            
    def filter(self, devs):
        return devs
        
    def get_rules(self):
        return []
    
    def __repr__(self):
        return '{0}: {1}'.format(self.name, self.value)
        
    def hint(self):
        return ''
        
    def is_valid(self, devs):
        if devs:
            return self.rule.apply(devs[0], rules.Transform(), {})
        else:
            self.rule.apply(None, rules.Transform(), {})
            #raise ValueError('No devices in StreetAddressField.is_valid()')
        
    def get_option(self):       
        #todo: different option names for streetaddress!
        return {'delivery_address': self.value}
        
    def update(self, devs, opts):
        pass

    def validate(self):
        if self.required and self.value is None:
            raise ValidationError(_('Field {0} is required').format(self.name))
        
class CompoundField(Field):
    '''
    group of fields
    '''
    def __init__(self, name, internal_name, fields, views, **kwargs):
        Field.__init__(self, name, internal_name, **kwargs)
        self.fields = fields[:]
        self.init_view(views, **kwargs)
    
    '''
    def get_rule(self):
        return rules.RuleAndChain(*[f.get_rule() for f in self.fields])
    '''
        
    def get_rules(self):
        return list(itertools.chain.from_iterable(f.get_rules() for f in self.fields))
        
    def select(self, choice, devs, opts):
        #should never happen
        return devs

    def get_fields(self):
        return list(itertools.chain.from_iterable(f.get_fields() for f in self.fields))
        
    def validate(self):
        #internal fields will be checked elsewhere
        pass
        
    def get_option(self):
        return {}   
        
    def is_valid(self, devs):
        return True
        
class OneOfManyField(Field):
    '''
    allows to select one field to fill
    '''
    def __init__(self, name, internal_name, fields, views, **kwargs):
        #consists of several fields, only one is active at a time
        Field.__init__(self, name, internal_name, **kwargs)
        self.fields = [[f, i==0] for i,f in enumerate(fields)]
        self.init_view(views, **kwargs)

    '''
    def get_rule(self):
        return rules.RuleAndChain(*[f.get_rule() for f,e in self.fields if e])
    '''
        
    def get_rules(self):
        return list(itertools.chain.from_iterable(f.get_rules() for f,e in self.fields if e))
        
    def select(self, choice, devs, opts):
        print('OneOfManyField.select()', choice)
        for f in self.fields:
            f[1] = False
        fs = {f[0].name:i for i,f in enumerate(self.fields)} 
        assert(choice in fs)
        self.fields[fs[choice]][1] = True
        return devs
        
    def update(self, devs, opts={}):
        pass

    def get_fields(self):
        return [self] + list(itertools.chain.from_iterable(f.get_fields() for f,e in self.fields if e))

    def validate(self):
        #internal fields will be checked elsewhere
        pass

    def get_option(self):
        return {}
        
    def is_valid(self, devs):
        return True

        
class Screen:       
    def select(self):
        pass
        
#TODO: move all logic related to django models and views to separate class
class Result(Screen):
    '''
    shows result, may not contain fields
    '''
    def __init__(self, decider, view):
        #self._template = "mconfig/result.html"
        #self._unpriced_template = "mconfig/result_unpriced.html"
        self.fields = []
        self.decider = decider
        self.packages = []
        self.view = view
        self.view.question = self
        
    def select(self):
        opts = self.wizard.get_options() 
        devs = self.wizard.apply_filters(options=opts)        
        print('Wizard options:', opts)
        devs = self.decider.select_devices(devs)        
        self.packages = [d.package(opts, self.decider) for d in devs]
        #print(self.packages)
    
    def show(self):
        #print('Result.show()')
        for p in self.packages:
            print(p, p.price)
            
    def is_valid(self, devs):
        return True
        
    def run(self):
        input()
        return self
        
    def get_fields(self):
        return []
        
    @property
    def template(self):
        try:
            for p in self.packages:
                p.calculate_price()
            return self.view._template
        except price.NotInPricelist:
            return self.view._unpriced_template
            
    def validate(self):
        pass
    
class Question(Screen):
    '''
    generic screen with fields
    '''
    def __init__(self, view):
        #self.template = "mconfig/question.html"
        self.fields = []
        self.last_error = ''
        self.view = view
        self.view.question = self
        
    def get_fields(self):
        return list(itertools.chain.from_iterable(f.get_fields() for f in self.fields))

    def get_field(self, name):        
        all_fields = self.get_fields()
        for f in all_fields:
            if f.internal_name == name:
                return f
        raise KeyError(name)
        
    def find_field(self, name):
        sel_fields = [f for f in self.get_fields() if f.name == name]
        if sel_fields:
            return sel_fields[0]
        else:
            raise KeyError(name)
        
    def show(self):
        return
        for i, f in enumerate(self.get_fields()):
            print('{0}. {1}'.format(i, f))
            
    def run(self):
        a = input('Select field (n - next question), (p - previous question)')
        if a == 'n':
            return self.wizard.next_question()
        elif a == 'p':
            return self.wizard.previous_question()
        else:
            self.edit_field(self.fields[int(a)])
            return self
        
    def edit_field(self, field):        
        a = input(field.hint())
        field.select(a, self.wizard.devs)
        
    def is_valid(self, devs):
        res = False
        for f in self.get_fields():
            valid = f.is_valid(devs)
            #print('Field', f, valid) 
            res = res or valid
        return res
        
    def validate(self):
        #print('Validating', self)
        for f in self.get_fields():
            #print('\tValidating', f)
            f.validate()
            
    def can_proceed(self):
        try:
            self.validate()
            return True
        except (ValueError, ValidationError):
            return False
                
class Wizard:
    def __init__(self, devices):
        print('Wizard.__init__()')
        #self.user = user
        self.screens = []
        self.current_screen = None
        self.device_base = devices
        #current wizard state
        self.devs = devices[:]
        
    def append_screen(self, screen, views={}):
        if self.screens:
            self.screens[-1].next = screen
            screen.previous = self.screens[-1]
        else:
            screen.previous = None
        screen.next = None
        screen.wizard = self
        self.screens.append(screen)
        
    def previous_question(self):        
        cur = self.current_screen.previous
        opts = self.get_options(cur)
        while cur is not None:
            self.apply_filters(cur, options=opts)
            #self.current_screen = cur
            if not cur.is_valid(self.devs):
                cur = cur.previous
                opts = self.get_options(cur)
            else:
                return cur
        
    def next_question(self):
        try:
            cur = self.current_screen.next
            opts = self.get_options(cur)
            #print('Next:', cur, opts)
            while cur is not None:
                self.apply_filters(cur, options=opts)
                if not cur.is_valid(self.devs):                    
                    print('Question skipped(not valid)', cur)
                    cur = cur.next      
                    opts = self.get_options(cur)
                else:
                    #self.current_screen = cur
                    #print('New cur is', cur)
                    return cur
        except:
            print('Exception in wizard.next_question()')
            raise
        
    def apply_filters_nosave(self, last = None, exclude=[], options={}):
        #print('apply_filters_nosave() to ', last)
        #print('excluding', exclude)        
        applied = exclude[:]        
        #transform is per-device, not global!
        #note: better do not use transforms at all
        ds = [(d, rules.Transform()) for d in self.device_base]     
        #print('Before filters', devs)
        cur = self.screens[0]
        while cur!=last:            
            for f in cur.get_fields():            
                rs = f.get_rules()
                for r in rs:
                    if r not in applied:
                        try:
                            ds = [(d,t) for d,t in ds if r.apply(d, t, options)]
                            applied.append(r)
                            #print('After apply', r, len(ds))
                            if len(ds)==0:
                                #print('All filtered', cur, options)
                                #import traceback
                                #traceback.print_stack()
                                pass
                        except:
                            print('Exception in apply()', r, d)
                            raise
            cur = cur.next
        #print('After filters:', len(ds))
        return [d for d,t in ds]
        
    def apply_filters(self, last = None, exclude=[], options={}):
        self.devs = self.apply_filters_nosave(last, exclude, options)
        return self.devs
        
    def get_options(self, last_screen=None, exclude=()):
        opts = {}
        cur = self.screens[0]
        while cur != last_screen:       
            for field in cur.get_fields():
                #TODO: check 
                #note: field may have several options
                if field not in exclude:
                    opts.update(field.get_option())
            cur = cur.next
        return opts
        
    def refresh_field(self, question, field):
        devs = self.devs        
        opts = self.get_options(question)
            
        devs = self.apply_filters_nosave(question.next, exclude=field.get_rules(), options=opts)        
        if devs:                
            for f in question.get_fields():
                opts = self.get_options(question.next, exclude=(f, ))
                devs = self.apply_filters_nosave(question.next, exclude=f.get_rules(), options=opts)
                f.update(devs, opts)
        else:
            #should not happen
            print('WARNING: refresh_field(): empty devs')
            #field.undo()
            #question.last_error = _('No device matches current selection')
            #raise _('No device matches current selection')
        
        
    def update(self, question, field, value):
        question = self.current_screen
        devs = self.devs        
        opts = self.get_options(question)
        try:                
            opts = self.get_options(question)                
            field.select(value, devs, opts)
        except NoMatches:
            raise
        except ValueError:
            raise
            
        devs = self.apply_filters_nosave(question.next, exclude=field.get_rules(), options=opts)        
        #opts = self.get_options(question.next, exclude=(field, ))
        if devs:                
            for f in question.get_fields():
                opts = self.get_options(question.next, exclude=(f, ))
                devs = self.apply_filters_nosave(question.next, exclude=f.get_rules(), options=opts)
                f.update(devs, opts)
        else:
            field.undo()
            question.last_error = _('No device matches current selection')
            raise NoMatches(_('No device matches current selection'))
        
    def go_forward(self):
        question = self.current_screen
        try:
            question.validate()
        except ValidationError as ex:                
            question.last_error = ex.message
            raise            
        question = self.next_question()
        self.current_screen = question         
        
    def go_back(self):
        question = self.previous_question()
        self.current_screen = question 
        
    def start(self):
        self.current_screen = self.screens[0]
            
    def main(self):
        while True:
            self.current_screen.show()
            new_scr = self.current_screen.run()
            if new_scr != self.current_screen:
                #print('new screen', new_scr)
                new_scr.select()
                self.current_screen = new_scr
