
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mysite.settings")

import django
django.setup()
import wizard
import questions
import devices
from django.utils.translation import ugettext as _





if __name__=="__main__":

    #from mconfig.views import Decider

    #import mysite.settings as settings 
    class Decider:
        def __init__(self, settings):
            self.select_option = self.select_option_first
            #self.select_option = self.select_option_most_expensive
            
        def select_option_first(self, device, option):
            #select first available option
            return device.options[option][0]

        def select_option_most_expensive(self, device, option):
            #select most expensive option
            avail = device.options[option]
            ops = option_prices[option]
            prices = sorted([(o, p) for o,p in ops.items() if o in avail], key=operator.itemgetter(1), reverse=True)
            return prices[0][0]     
            
        def select_devices(self, devices):
            def get_nom_current(device):
                return device.attributes['nom_current']
            return [list(sorted(devices, key=get_nom_current))[0]]
            
        def select_choice(self, devices, choice):
            return choice.get_valid_choices(devices)
            
        def filter_devices(self, devices):
            return self.select_devices(devices)
            
    class Settings:
        pass

    class View:
        pass    
        
    settings = Settings()
    decider = Decider(settings)
   
    qs = [
        questions.LoadQuestion(devices.devices, {}, view=View()),
        questions.PlacementQuestion(devices.devices, {}, view=View()),
        wizard.Result(decider, view=View())
        ]
        
    #wiz = wizard.Wizard(devices.devices)
    
    #for question in qs:            
    #    wiz.append_screen(question)
        
    #wiz.start()
    #print(wiz.current_screen)
    #print(wiz.current_screen.fields)
    
   
    def test_case(mot_volt,num_cur,drive_vol,cab_len):
        #settings = Settings()
        #decider = Decider(settings)    
        #qs = [
        #questions.LoadQuestion(devices.devices, {}, view=View()),
        #questions.PlacementQuestion(devices.devices, {}, view=View()),
        #wizard.Result(decider, view=View())
        #]
        wiz = wizard.Wizard(devices.devices)
        for question in qs:            
            wiz.append_screen(question)
        wiz.start()
        field = wiz.current_screen.get_field('select_motor_voltage')
        wiz.update(wiz.current_screen, field, _(mot_volt) )
        field1=wiz.current_screen.get_field('input_nom_current')
        wiz.update(wiz.current_screen,field1,_(num_cur) )
        wiz.go_forward(decider)
        field2=wiz.current_screen.get_field('select_drive_voltage')
        wiz.update(wiz.current_screen,field2,_(drive_vol))
        field3=wiz.current_screen.get_field('input_cable_len')
        wiz.update(wiz.current_screen,field3,_(cab_len))
        wiz.go_forward(decider)
        wiz.current_screen.select()
        code=wiz.current_screen.packages[0].order_code()
        return code
    '''
    
    field = wiz.current_screen.get_field('select_motor_voltage')
    #field = question.find_field('')
    wiz.update(wiz.current_screen, field, _('10kV') )
    field1=wiz.current_screen.get_field('input_nom_current')
    
    wiz.update(wiz.current_screen,field1,_('90') )

    wiz.go_forward(decider)
    field2=wiz.current_screen.get_field('select_drive_voltage')
    wiz.update(wiz.current_screen,field2,_('6kV  50Hz'))
    field3=wiz.current_screen.get_field('input_cable_len')
    wiz.update(wiz.current_screen,field3,_('50'))
    wiz.go_forward(decider)
    wiz.current_screen.select()
    code=wiz.current_screen.packages[0].order_code()
    print(code)
    if code=='VD-P1000U1F530ASX096AXAX1BXCXDX11EXD':
        print ('test1 passed')
    else:
         print ('test1 not passed')
    '''
    
    k=[]
    #P1000U1
    code=test_case('6kV','90','6kV  50Hz','50')
    print(code)
    if code=='VD-P1000U1F530ASX096AXAX1BXCXDX11EXD':
        res='test1 passed' 
        k.append(res)
    else:
        res='test1 not passed' 
        k.append(res)
    

    
    #P1000U3
    code=test_case('10kV','90','6kV  50Hz','50')
    print(code)
    if code=='VD-P1600U3F530ASX096AXAX1BXC3DX11EXD':
        res='test2 passed' 
        k.append(res)
    else: 
        res='test2 not passed'
        k.append(res)
         
         
    #P1000U1
    code=test_case('6kV','90','10kV 50Hz','50')
    print(code)
    if code=='VD-P1000U1F530ASX096AXAX1BXC1DX11EXD':
        res='test3 passed' 
        k.append(res)
    else:
        res='test3 not passed'
        k.append(res)
         
         
    #P1600U3
    code=test_case('10kV','90','10kV 50Hz','50')
    print(code)
    if code=='VD-P1600U3F530ASX096AXAX1BXCXDX11EXD':
        res='test4 passed' 
        k.append(res)
    else:
        res='test4 not passed'
        k.append(res)
    
    #P400KU1
    code=test_case('6kV','40','6kV  50Hz','50')
    print(code)
    if code=='VD-P400KU1F530ASX040AXAX1BXCXDX11EXD':
        res='test5 passed' 
        k.append(res)
    else:
        res='test5 not passed'
        k.append(res)
    
    #P315KU1
    code=test_case('6kV','31','6kV  50Hz','50')
    print(code)
    if code=='VD-P315KU1F530ASX031AXAX1BXCXDX11EXD':
        res='test6 passed' 
        k.append(res)
    else:
        res='test6 not passed'
        k.append(res)
    print (k)
    
    
    #P500KU1
    code=test_case('6kV','48','6kV  50Hz','50')
    print(code)
    if code=='VD-P500KU1F530ASX048AXAX1BXCXDX11EXD':
        res='test7 passed' 
        k.append(res)
    else:
        res='test7 not passed'
        k.append(res)
        
        
    #P630KU1
    code=test_case('6kV','61','6kV  50Hz','50')
    print(code)
    if code=='VD-P630KU1F530ASX061AXAX1BXCXDX11EXD':
        res='test8 passed' 
        k.append(res)
    else:
        res='test8 not passed'
        k.append(res)
        
        
    #PP800KU1
    code=test_case('6kV','77','6kV  50Hz','50')
    print(code)
    if code=='VD-P800KU1F530ASX077AXAX1BXCXDX11EXD':
        res='test9 passed' 
        k.append(res)
    else:
        res='test9 not passed'
        k.append(res)
        
        
        
    #P1250U1    
    code=test_case('6kV','130','6kV  50Hz','50')
    print(code)
    if code=='VD-P1250U1F530ASX130AXAX1BXCXDX11EXD':
        res='test10 passed' 
        k.append(res)
    else:
        res='test10 not passed'
        k.append(res)
    
    #P7900U1    
    code=test_case('6kV','750','6kV  50Hz','50')
    print(code)
    if code=='VD-P7900U1F530ASX750AXAX1BXCXDX11EXD':
        res='test11 passed' 
        k.append(res)
    else:
        res='test11 not passed'
        k.append(res)
    
    
    
    print (k)
    
    
    
    