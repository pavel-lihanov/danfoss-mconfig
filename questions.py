import wizard
import rules
import devices
import functools
import django.core.exceptions
import settings

'''
TODO: rules can be created from database table
table fields:
id (int)
name (string)
class (id, questions classes should also be in DB)
init params
'''


#from django.utils.translation import ugettext as _

_ = settings._

all_rules = {}
            
class OptionChoice(wizard.Choice):
    def __init__(self, text, option, value):
        wizard.Choice.__init__(self, text, rules.OptionRule(option, value), {option: value})        
            
class LoadQuestion(wizard.Question):
    class ApplicationField(wizard.SearchChoiceField):
        def __init__(self, current_getter, devs, views, **kwargs):
            self.custom_app = wizard.Choice(_('Custom'), rules.TrueRule())
            self.apps = (   
                            ('1.1', wizard.Choice(_('Fan (k=1.1)'), rules.OverloadRule(1.1, current_getter))),
                            ('1.5', wizard.Choice(_('Smoke extractor (k=1.5)'), rules.OverloadRule(1.5, current_getter))),
                            ('1.15', wizard.Choice(_('Compressor (k=1.15)'), rules.OverloadRule(1.15, current_getter))),
                            ('2.0', wizard.Choice(_('2-piston compressor (k=2)'), rules.OverloadRule(2.0, current_getter))),
                            ('1.6', wizard.Choice(_('4-piston compressor (k=1.6)'), rules.OverloadRule(1.6, current_getter))),
                            ('1.5', wizard.Choice(_('6-piston compressor (k=1.5)'), rules.OverloadRule(1.5, current_getter))),
                            ('1.6', wizard.Choice(_('Piston pump (k=1.6)'), rules.OverloadRule(1.6, current_getter))),
                            ('1.1', wizard.Choice(_('Centr. pump (k=1.1)'), rules.OverloadRule(1.1, current_getter))),
                            ('1.3', wizard.Choice(_('Submer. pump (pulp) (k=1.3)'), rules.OverloadRule(1.3, current_getter))),
                            ('1.3', wizard.Choice(_('Submer. pump (wastewater) (k=1.3)'), rules.OverloadRule(1.3, current_getter))),
                            ('1.1', wizard.Choice(_('Fan (k=1.1)'), rules.OverloadRule(1.1, current_getter))),
                            ('1.5', wizard.Choice(_('Smoke extractor (k=1.5)'), rules.OverloadRule(1.5, current_getter))),
                            ('2.0', wizard.Choice(_('Grinder (k=2)'), rules.OverloadRule(2.0, current_getter))),
                            ('1.4', wizard.Choice(_('Autogenous mill (k=1.4)'), rules.OverloadRule(1.4, current_getter))),
                            ('1.8', wizard.Choice(_('Ball mill (k=1.8)'), rules.OverloadRule(1.8, current_getter))),
                            ('1.2', wizard.Choice(_('Processing machine, light load (k=1.2)'), rules.OverloadRule(1.2, current_getter))),
                            ('1.5', wizard.Choice(_('Processing machine, medium load (k=1.5)'), rules.OverloadRule(1.5, current_getter))),
                            ('2.0', wizard.Choice(_('Processing machine, heavy load (k=2)'), rules.OverloadRule(2.0, current_getter))),
                            ('1.4', wizard.Choice(_('Conveyour, light load (k=1.4)'), rules.OverloadRule(1.4, current_getter))),
                            ('1.8', wizard.Choice(_('Conveyour, heavy load (k=1.8)'), rules.OverloadRule(1.8, current_getter))),  
                            ('0.0', self.custom_app),
                    )
            
            wizard.SearchChoiceField.__init__(self, _('Select application'), 'select_application', 
                    [a[1] for a in self.apps], devs, views, hint='', **kwargs)
        
        def set_custom_overload(self, sender):
            self._force_select(self.custom_app)
            
        def get_selected_overload(self):
            return [a[0] for a in self.apps if self.selected == a[1]][0]
            
    class OverloadField(wizard.ValueField):
        def __init__(self, overload_getter, current_getter, views, **kwargs):
            wizard.ValueField.__init__(self, _('Input overload factor'), 'input_overload',
                                                    rules.VariableOverloadRule(overload_getter, current_getter), 
                                                    views, required=True, hint='mconfig/hints/overload.html', **kwargs)
                                                    
        def set_overload(self, sender):
            ov = sender.get_selected_overload()
            self._force_select(ov)
                    
    def __init__(self, devs, views, **kwargs):
        wizard.Question.__init__(self, kwargs['view'])      
        self.header = _("Choose basic application parameters")        
        self.application_field = LoadQuestion.ApplicationField(self.get_nom_current ,devs, views, **kwargs)
        self.overload_field = LoadQuestion.OverloadField(self.get_overload, self.get_nom_current, views, **kwargs)
        
        self.application_field.on_changed.append(self.overload_field.set_overload)
        self.overload_field.on_changed.append(self.application_field.set_custom_overload)
        self.overload_field.set_overload(self.application_field)
        
        self.motor_type_field = wizard.ChoiceField(_('Select motor type'), 'select_motor_type',
                                                        (   wizard.Choice(_('Induction'), rules.OptionRule('motor_type', 'Induction'), options = {'motor_type': 'Induction', 'PMSM exciter': 'No'}), 
                                                            wizard.Choice(_('PMSM'), rules.OptionRule('motor_type', 'PM'), options = {'motor_type': 'PM'}), 
                                                        ),                                                        
                                                        devs, views, hint='', **kwargs)        

        self.motor_voltage_field = wizard.ChoiceField(_('Select motor voltage'), 'select_motor_voltage',
                                        (   wizard.Choice('', rules.TrueRule(), mean=False),
                                            wizard.Choice(_('6kV'), rules.AttributeRule('voltage', 6000)), #),
                                            wizard.Choice(_('10kV'), rules.AttributeRule('voltage', 10000)),#),                                        
                                            #wizard.Choice(_('6kV'), rules.AttributeRule('voltage', 6000), options = {'motor_voltage': 6000}), #),
                                            #wizard.Choice(_('10kV'), rules.AttributeRule('voltage', 10000), options = {'motor_voltage': 10000}),#),
                                        ), 
                                                        devs, views, required=True, hint='',**kwargs
                                    )
                                    
        self.exciter_field = wizard.ChoiceField(_('Select SM exciter'), 'select_sm_exciter', (    
                                                                    wizard.Choice(_('None/External'), rules.OptionRule('PMSM exciter', 'No'), options = {'PMSM exciter': 'No'}), 
                                                                    wizard.Choice(_('Built-in'), rules.OptionRule('PMSM exciter', 'Yes'), options = {'PMSM exciter': 'Yes', 'motor_type': 'PM'}), 
                                                        ), 
                                                        devs, views, hint='', **kwargs)
                                                        
        self.nominal_current_field = wizard.ValueField(_('Input nominal current'), 'input_nom_current', rules.CurrentRule(self.get_nom_current), views, required=True, hint='', **kwargs)
        
        self.fields = [ 
                        self.application_field,
                        self.overload_field,
                        
                        wizard.TextHeader(_('Motor data'), views),                        
                        self.motor_type_field,                                                        
                        self.nominal_current_field,                                                                       
                        self.motor_voltage_field,
                        self.exciter_field,                                                                       
                        
                        wizard.TextHeader(_('Control data'), views),                        
                        wizard.ChoiceField(_('Select control mode'), 'select_control_mode',
                                        (   #wizard.Choice('', rules.TrueRule(), mean=False),
                                            wizard.Choice(_('U/f control'), rules.OptionRule('control_mode', 'U/f'), options = {'control_mode': 'U/f'}), 
                                            wizard.Choice(_('Vector control'), rules.OptionRule('control_mode', 'Vector control'), options = {'control_mode': 'Vector control'}),
                                        ),                                                         
                                                       devs, views, required=True, hint='',**kwargs),

                        wizard.ChoiceField(_('Select braking mode'), 'select_braking_mode',
                                        (   wizard.Choice(_('Coasting stop'), rules.OptionRule('brake_mode', 'Coast'), options = {'brake_mode': 'Coast'}),
                                            #wizard.Choice(_('Dynamic braking'), rules.OptionRule('brake_mode', 'Dynamic'), options = {'brake_mode': 'Dynamic'}),
                                            wizard.Choice(_('Recuperation'), rules.OptionRule('brake_mode', 'Recuperation'), options = {'brake_mode': 'Recuperation', 'Service access':'Front and back'}),
                                        ), 
                                    devs, views, hint='',**kwargs
                                    ),
                                    
                        wizard.ChoiceField(_('Select multimotor mode'), 'select_multimotor_mode',
                                        (   wizard.Choice(_('No multimotor'), rules.TrueRule(), options = {'multi_motors': 1}),  #if no multimotor user can select autobypass
                                            wizard.Choice(_('Multistart, 2 motors'), rules.OptionRule('power_option', 'Multistart'), options = {'power_option': 'Multistart', 'multi_motors':2, 'Output reactor':'Yes'}),
                                            wizard.Choice(_('Multistart, 3 motors'), rules.OptionRule('power_option', 'Multistart'), options = {'power_option': 'Multistart', 'multi_motors':3, 'Output reactor':'Yes'}),
                                            wizard.Choice(_('Multistart, 4 motors'), rules.OptionRule('power_option', 'Multistart'), options = {'power_option': 'Multistart', 'multi_motors':4, 'Output reactor':'Yes'}),
                                            #wizard.Choice(_('Interchange, 2 motors'), rules.OptionRule('power_option', 'Interchange'), options = {'power_option': 'Interchange', 'multi_motors':2}),
                                            #wizard.Choice(_('Interchange, 3 motor'), rules.OptionRule('power_option', 'Interchange'), options = {'power_option': 'Interchange', 'multi_motors':3}),
                                            #wizard.Choice(_('Interchange, 4 motor'), rules.OptionRule('power_option', 'Interchange'), options = {'power_option': 'Interchange', 'multi_motors':4}),

                                        ), 
                                    devs, views, hint='',**kwargs
                                    )                                                            
                                    
                                    ]
    def select(self):
        pass
        
    def get_nom_current(self):
        #print(self.fields)
        if not self.fields:
            return 0.0
        return self.nominal_current_field.value if self.nominal_current_field.value is not None else 0.0
        
    def get_overload(self):        
        if not self.fields:
            return 0.0
        v = self.overload_field.value
        return v if v is not None else 0.0
        '''
        v = self.fields[0].fields[1][0].fields[0].value
        return v if v is not None else 0.0
        '''
         
            
class MotorCableLenField(wizard.ValueField):
    def get_option(self):
        if self.value is not None:        
            return {'Output reactor': 'Yes' if float(self.value) > 800 else 'No'}
        else:
            return {}
            
        

class PlacementQuestion(wizard.Question):
    def __init__(self, devs, views, **kwargs):
        wizard.Question.__init__(self, kwargs['view'])      
        self.header = _("Choose installation parameters")
        self.fields = None      
        self.fields = [ wizard.ChoiceField(_('Select drive voltage'), 'select_drive_voltage',
                                        (   wizard.Choice('', rules.TrueRule(), mean=False),
                                            wizard.Choice(_('6kV  50Hz'), rules.TrueRule(), options = {'input_freq': 50, 'mains_voltage':6000}),
                                            wizard.Choice(_('10kV 50Hz'), rules.TrueRule(), options = {'input_freq': 50, 'mains_voltage':10000}),
                                        ), 
                                    devs, views, required = True, hint='mconfig/hints/drive_voltage.html',**kwargs
                                    ),
        
                        wizard.ChoiceField(_('Select enclosure'), 'select_enclosure', (   
                                                            OptionChoice(_('IP30'), 'enclosure', 'IP30'),
                                                            OptionChoice(_('IP31'), 'enclosure', 'IP31'),
                                                            OptionChoice(_('IP41'), 'enclosure', 'IP41'),
                                                            #OptionChoice(_('IP42'), 'enclosure', 'IP42'),
                                                            #OptionChoice(_('IP54'), 'enclosure', 'IP54'),                                                            
                                                        ), 
                                                        devs, views, hint='mconfig/hints/enclosure.html',**kwargs),
                                                                                                                                                      
                        wizard.ChoiceField(_('Select drive cooling'), 'select_cooling',
                                        (                                               
                                            wizard.Choice(_('Air cooling'),                                                 
                                                rules.OptionRule('cooling', 'Air'),                                                                                                         
                                                options = {'cooling':'Air'}),
                                            wizard.Choice(_('Liquid cooling'), 
                                                rules.OptionRule('cooling', 'Liquid'),
                                                options = {'cooling':'Liquid', 'Service access' : 'Front and back'}
                                            ),
                                        ), 
                                    devs, views, hint='mconfig/hints/cooling.html', **kwargs
                                    ),
                                    
                        wizard.ChoiceField(_('Select power mains location'), 'select_power_mains',
                                        (                                               
                                            OptionChoice(_('Bottom'), 'Input mains location', 'Bottom'),
                                            OptionChoice(_('Top'), 'Input mains location', 'Top'),
                                        ), 
                                    devs, views, hint='mconfig/hints/power_mains.html',**kwargs
                                    ),
                        
                        wizard.ChoiceField(_('Select motor mains location'), 'select_motor_mains',
                                        (                                               
                                            OptionChoice(_('Bottom'), 'Motor cable location', 'Bottom'),
                                            OptionChoice(_('Top'), 'Motor cable location', 'Top'),
                                        ), 
                                    devs, views,hint='mconfig/hints/motor_mains.html', **kwargs
                                    ),

                        wizard.ChoiceField(_('Select service access'), 'select_service_access',
                                        (                                               
                                            OptionChoice(_('Front and back'), 'Service access', 'Front and back'),
                                            OptionChoice(_('Front'), 'Service access', 'Front'),
                                        ), 
                                    devs, views, hint='mconfig/hints/service_access.html', **kwargs
                                    ),
                                    
                        MotorCableLenField(_('Input motor cable len'), 'input_cable_len', rules.OptionIfGreater(self.get_cable_len, 800, 'Output reactor', ('No', 'Yes')), 
                                    views, required=True, hint='mconfig/hints/cable_len.html', **kwargs),
                                    
                        wizard.TextHeader(_('Options'), views),
                        
                        wizard.ChoiceField(_('Select fieldbus option'), 'select_b',(
                                                            wizard.Choice('None', rules.TrueRule(), options={'fieldbus':'None'}),
                                                            #wizard.Choice(_('Encoder board'), rules.OptionRule('fieldbus', 'Encoder'), options={'fieldbus':'Encoder'}),
                                                            wizard.Choice(_('EtherNet IP'), rules.OptionRule('fieldbus', 'EtherNet IP'), options={'fieldbus':'EtherNet IP'}),
                                                            wizard.Choice(_('ProfiBus DP'), rules.OptionRule('fieldbus', 'ProfiBus DP'), options={'fieldbus':'ProfiBus DP'}),
                                                            wizard.Choice(_('Modbus TCP/IP'), rules.OptionRule('fieldbus', 'Modbus TCP/IP'), options={'fieldbus':'Modbus TCP/IP'}),
                                                        ), 
                                                        devs, views, hint='mconfig/hints/fieldbus.html', **kwargs),
                                                        
                        wizard.ChoiceField(_('Select power cell count'), 'select_power_cells',
                                        (                                               
                                            wizard.Choice(_('5'), rules.OptionRule('power_cells', 5), options = {'power_cells': 5, 'motor_type':'Induction'}),
                                            wizard.Choice(_('6'), rules.OptionRule('power_cells', 6), options = {'power_cells': 6}),
                                            wizard.Choice(_('8'), rules.OptionRule('power_cells', 8), options = {'power_cells': 8, 'motor_type':'Induction'}),
                                            wizard.Choice(_('9'), rules.OptionRule('power_cells', 9), options = {'power_cells': 9}),
                                        ), 
                                    devs, views, hint='mconfig/hints/power_cells.html',**kwargs
                                    ),
                                                        
                        wizard.ChoiceField(_('Select drive bypass'), 'select_c',
                                        (   
                                            wizard.Choice(_('None'),   rules.OptionRule('power_option', 'None'), options = {'power_option': 'None'}),
                                            wizard.Choice(_('Manual'), rules.RuleAndChain(
                                                                            rules.CanUseBypassRule(), 
                                                                            rules.OptionRule('power_option', 'Manual bypass')
                                                                            ), 
                                                                       options = {'power_option': 'Manual bypass'}),
                                            wizard.Choice(_('Auto'),   rules.RuleAndChain(
                                                                            rules.CanUseBypassRule(), 
                                                                            rules.OptionRule('power_option', 'Autobypass'),
                                                                            ),
                                                                       options = {'power_option': 'Autobypass'}),
                                            wizard.Choice(_('N/A'), rules.TrueRule()),
                                        ), 
                                    devs, views, hint='mconfig/hints/drive_bypass.html',**kwargs
                                    ),
                                                                                                               
                        wizard.ChoiceField(_('Select power cell bypass'), 'select_d',
                                        (   
                                            OptionChoice(_('None'), 'power_cell_autobypass', 'No'),
                                            wizard.Choice(_('Autobypass'), 
                                                            rules.OptionRule('power_cell_autobypass', 'Yes'), 
                                                            options = { 'power_cell_autobypass': 'Yes', 
                                                                        'motor_type':'Induction',
                                                                        'cooling':'Air'}
                                                            ),
                                            #OptionChoice(_('Autobypass'), 'power_cell_autobypass', 'Yes'),
                                        ), 
                                    devs, views, hint='mconfig/hints/power_cell_bypass.html',**kwargs
                                    ),                        
                                    
                                    ]        
        
    def get_cable_len(self):
        return self.fields[6].value if self.fields[6].value is not None else 0.0
         
class OptionsQuestion(wizard.Question):
    def __init__(self, devs, views, **kwargs):
        wizard.Question.__init__(self, kwargs['view'])      
        self.header = _("Choose installation parameters")
        self.fields = None      
        self.fields = [ wizard.ChoiceField(_('Select fieldbus option'), 'select_b',(
                                                            wizard.Choice('None', rules.TrueRule(), options={'fieldbus':'None'}),
                                                            #wizard.Choice(_('Encoder board'), rules.OptionRule('fieldbus', 'Encoder'), options={'fieldbus':'Encoder'}),
                                                            wizard.Choice(_('EtherNet IP'), rules.OptionRule('fieldbus', 'EtherNet IP'), options={'fieldbus':'EtherNet IP'}),
                                                            wizard.Choice(_('ProfiBus DP'), rules.OptionRule('fieldbus', 'ProfiBus DP'), options={'fieldbus':'ProfiBus DP'}),
                                                            wizard.Choice(_('Modbus TCP/IP'), rules.OptionRule('fieldbus', 'Modbus TCP/IP'), options={'fieldbus':'Modbus TCP/IP'}),
                                                        ), 
                                                        devs, views, hint='mconfig/hints/fieldbus.html', **kwargs),
                                                        
                        wizard.ChoiceField(_('Select drive bypass'), 'select_c',
                                        (   
                                            wizard.Choice(_('None'),   rules.OptionRule('power_option', 'None'), options = {'power_option': 'None'}),
                                            wizard.Choice(_('Manual'), rules.RuleAndChain(
                                                                            rules.CanUseBypassRule(), 
                                                                            rules.OptionRule('power_option', 'Manual bypass')
                                                                            ), 
                                                                       options = {'power_option': 'Manual bypass'}),                                                                            
                                            wizard.Choice(_('Auto'),   rules.RuleAndChain(
                                                                            rules.CanUseBypassRule(), 
                                                                            rules.OptionRule('power_option', 'Autobypass'),
                                                                            ),
                                                                       options = {'power_option': 'Autobypass'}),
                                            wizard.Choice(_('N/A'), rules.TrueRule()),
                                        ), 
                                    devs, views, hint='mconfig/hints/drive_bypass.html',**kwargs
                                    ),
                                                                                                               
                        wizard.ChoiceField(_('Select power cell bypass'), 'select_d',
                                        (   
                                            OptionChoice(_('None'), 'power_cell_autobypass', 'No'),
                                            OptionChoice(_('Autobypass'), 'power_cell_autobypass', 'Yes'),
                                        ), 
                                    devs, views, hint='mconfig/hints/power_cell_bypass.html',**kwargs
                                    ),                                    
                                    ]        

class DeliveryQuestion(wizard.Question):
    def __init__(self, devs, views, **kwargs):
        wizard.Question.__init__(self, kwargs['view'])      
        self.header = _("Choose delivery")
        self.fields = None      
        self.fields = [ wizard.ChoiceField(_('Select delivery method'), 'select_delivery_method', (
                            wizard.Choice(_('N/A'), rules.TrueRule()),
                            wizard.Choice(_('Sea'), rules.CanSeeDeliveryRule(kwargs['user_getter']), options={'delivery_method':'ship'}),
                            wizard.Choice(_('Air'), rules.CanSeeDeliveryRule(kwargs['user_getter']), options={'delivery_method':'plane'}),
                            wizard.Choice(_('Truck'), rules.CanSeeDeliveryRule(kwargs['user_getter']), options={'delivery_method':'truck'}),
                            wizard.Choice(_('Rail'), rules.CanSeeDeliveryRule(kwargs['user_getter']), options={'delivery_method':'train'}),
                           ),
                           devs, views, hint='mconfig/hints/delivery_type.html', **kwargs),
                        wizard.StreetAddressField(_('Enter delivery address'), 'select_delivery_address', rules.CanSeeDeliveryRule(kwargs['user_getter']), 
                           views, required=True, hint='mconfig/hints/delivery_address.html', **kwargs),
                       ]