import operator

import sys

import json

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from wizard import *
from rules import *

class Settings:
    pass
    
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
        return [devices[0]]
        
    def select_choice(self, devices, choice):
        return choice.get_valid_choices(devices)
    
settings = Settings()
decider = Decider(settings)
        

def print_filt(prefix, ds):
    print(prefix)
    print([d for d in ds])
        
class ComboBoxMixin:
    def __init__(self, field, **kwargs):
        self.field = field
        
    def update_widget(self, devs=None):
        #print('ComboBoxMixin.update_widget()')
        #don't react on change signals during widgets update
        try:
            self.widget.currentIndexChanged.disconnect()
        except TypeError:
            pass

        self.widget.clear()
        i=0
        self.vis_choices = {}
        
        if devs is not None:
            #print('Updating choices', devs)
            self.field.update(devs)
            #print(self.choices)
            
        for name, choice in self.field.choices.items():
            if choice.enabled:
                self.widget.addItem(choice.text)
                self.vis_choices[choice.text] = i
                i += 1
                                
        #print(vis_choices)
        
        #print('Selected:', self.selected)
        
        if self.field.selected is not None:
            if self.vis_choices[self.field.selected.text]!=self.widget.currentText():
                self.widget.setCurrentIndex(self.vis_choices[self.field.selected.text])
                
        self.old_value = self.field.selected
        
        #ugly       
        self.widget.currentIndexChanged.connect(self.on_choice_changed)
        
    def on_choice_changed(self):
        self.page.on_choice_changed(self)
        
    def undo(self): 
        try:
            self.widget.currentIndexChanged.disconnect()
        except TypeError:
            pass

        self.field.selected = self.old_value
        if self.field.selected is not None:
            if self.vis_choices[self.field.selected.text]!=self.widget.currentText():
                self.widget.setCurrentIndex(self.vis_choices[self.field.selected.text])
                
        self.widget.currentIndexChanged.connect(self.on_choice_changed)
    
    def make_widget(self, page):
        self.layout = QHBoxLayout()
        
        self.label = QLabel(self.field.name)
        self.widget = QComboBox()
        
        self.layout.addWidget(self.label)
        self.layout.addWidget(self.widget)
        
        self.page = page
        self.update_widget()            
        #self.widget.currentIndexChanged.connect(page.on_choice_changed)
        
        return self.widget
        
    def get_selected(self):
        return self.widget.currentText()
                
class EditMixin:
    def __init__(self, field, **kwargs):
        self.field = field
        
    def update_widget(self, devs=None):             
        if self.field.value is not None:
            self.widget.clear()
            if self.widget.text() != str(self.field.value):
                self.widget.setText(str(self.field.value))
        
        self.old_value = self.widget.text()

    def undo(self):
        print('Edit.undo()')
        self.widget.setText(self.old_value)     
        
    def make_widget(self, page):
        self.old_value = ''
        self.page = page
        
        self.layout = QHBoxLayout()
        
        self.label = QLabel(self.field.name)
        self.widget = QLineEdit()
        self.button = QPushButton()
        self.button.setText('Set')
        
        self.layout.addWidget(self.label)
        self.layout.addWidget(self.widget)
        self.layout.addWidget(self.button)

        self.update_widget()
        
        self.button.clicked.connect(self.on_choice_changed)
        
        return self.widget
                
    def get_selected(self):
        return self.widget.text()
        
    def on_choice_changed(self):
        self.page.on_choice_changed(self)           
    
class HTMLChoiceMixin:
    def __init__(self, field, **kwargs):        
        self.field = field
        #print(self.field, type(self.field))
        self.template = "mconfig/choice.html"
        
    def as_json(self):
        return json.dumps({'type': 'Choice',
                           'enabled': self.field.enabled,
                            'data': {'name': self.field.name, 
                                        'value': self.field.value, 
                                        'choices':  [   {'id': c.name + '_' + c.text, 
                                                        'value': c.text, 
                                                        'enabled': c.enabled} for c in self.field.choices
                                                    ]
                                    }
                          }
                        )        

class HTMLSearchChoiceMixin:
    def __init__(self, field, **kwargs):        
        self.field = field
        #print(self.field, type(self.field))
        self.template = "mconfig/searchchoice.html"
        
class HTMLEditMixin:
    def __init__(self, field, **kwargs):
        self.field = field
        #print(self.field)
        self.template = "mconfig/edit.html"

class HTMLStreetAddressMixin:
    def __init__(self, field, **kwargs):
        self.field = field
        #print(self.field)
        self.template = "mconfig/streetaddress.html"

        
class HTMLOneOfManyMixin:
    def __init__(self, field, **kwargs):
        self.field = field
        #print(self.field)
        self.template = "mconfig/oneofmany.html"
        
class HTMLCompoundMixin:
    def __init__(self, field, **kwargs):
        self.field = field        
        self.template = "mconfig/compound.html"        
        
class HTMLQuestion:
    def __init__(self, question):
        self.question = question
        question.view = self
                    
class HTMLWizard(Wizard):
    def __init__(self, devices, questions):
        views = {
                    ChoiceField: HTMLChoiceMixin, 
                    ValueField: HTMLEditMixin,
                    CompoundField: HTMLCompoundMixin,
                    OneOfManyField: HTMLOneOfManyMixin,
                }
                
        Wizard.__init__(self, devices)
        for question in questions:
            #self.append_screen(HTMLQuestion(question), views=views)
            self.append_screen(question, views=views)
                
def run_in_text_mode(): 
    wizard = Wizard(device_base)
    wizard.append_screen(ApplicationQuestion(device_base))
    wizard.append_screen(OptionsQuestion(device_base))
    wizard.append_screen(Result())
    wizard.start()
    while True:
        wizard.main()


def run_in_batch_mode():
    options = {'a': 2, 'b': 1}
    ds = device_base    
    for on, ov in options.items():
        ds = [d for d in filter(OptionRule(on, ov).apply, ds)]
        ds = [d for d in filter(OptionRule(on, ov).apply, ds)]

    ds = [d for d in filter(CurrentGreater(lambda: 7).apply, ds)]
    
    ds = decider.select_devices(ds)

    sel_prices = [o.package(options) for o in ds]
    
    sel_prices = sorted(sel_prices, key=Device.price)
    
    for i in sel_prices:
        print('Device {1}\nTotal {0}\n\n'.format(i.price(), i))
        

def run_in_gui_mode():
    class DriveConfigPage(QWizardPage):
        def __init__(self, title, caption, question):
            QWizardPage.__init__(self)
            self.question = question
            self.setTitle(title)
            self.layout = QVBoxLayout()
            label = QLabel(caption)
            self.layout.addWidget(label)
            
            for field in question.fields:
                field.view.make_widget(self)
                self.layout.addLayout(field.view.layout)

            self.setLayout(self.layout)
            
        def initializePage(self, devs):
            print('DriveConfigPage.initializePage()', self)
            #print(len(devs))
            #for field in self.question.fields:
            #   field.update_widget(devs)
            
            devs = wizard.apply_filters(self.question)
            
            if devs:
                for field in self.question.fields:
                    field.view.update_widget(devs)
                
        def on_choice_changed(self, view):
            wizard = self.question.wizard
            devs = wizard.devs
            
            try:
                view.field.select(view.get_selected(), devs)
            except AssertionError:
                msg = QMessageBox()
                msg.setText('Sorry, no suitable device available')
                msg.exec()
                view.undo()
                return
                
            devs = wizard.apply_filters(self.question.next, exclude=[view.field.get_rule()])
            
            if devs:
                for f in self.question.fields:
                    devs = wizard.apply_filters(self.question.next, exclude=[f.get_rule()])
                    f.view.update_widget(devs)          
            else:
                msg = QMessageBox()
                msg.setText('Sorry, no suitable device available')
                msg.exec()

                #invalid user input: undo changes
                for field in self.question.fields:
                    field.view.undo()
                                    
    class DriveConfigWizard(QWizard, Wizard):
        def __init__(self, **kwds):     
            super().__init__(**kwds)
            self.currentIdChanged.connect(self.change_screen)
            self.setOption(QWizard.IndependentPages, False)
            #void QWizard::currentIdChanged(int id)
            
        def append_screen(self, title, caption, screen):
            Wizard.append_screen(self, screen)
            self.addPage(DriveConfigPage(title, caption, screen))
                    
        def nextId(self):
            #print('DriveConfigWizard.nextId({0})'.format(self.currentId()))
            next = self.next_question()
            
            #print(next)
            return self.screens.index(next) if next is not None else -1
            
        def change_screen(self, id):
            print('Changing screen to ', id)
            self.current_screen = self.screens[id]
            
        def initializePage(self, id):
            self.page(id).initializePage(self.devs)
    
    import questions
    import devices
    
    app = QApplication(sys.argv)    
    
    views  ={
                ChoiceField: ComboBoxMixin, 
                ValueField: EditMixin,
            }
    
    wizard = DriveConfigWizard(devices = devices.devices)
    wizard.append_screen(
                            'Basic parameters', 
                            'Select basic application parameters', 
                            questions.ApplicationQuestion(devices.devices, views)
                        )
                            
    wizard.append_screen(
                            'Options', 
                            'Select drive options',
                            questions.OptionsQuestion(devices.devices, views)
                        )

    #wizard.append_screen('Drive', 'Your drive is:',Result())
    wizard.start()

    wizard.show()
    
    app.exec()
        
if __name__ == '__main__':  
    '''
    Device('dev2', {'current': 10}, {'a': (2, 3, 4, 5), 'b': (0, ), 'c': (0, 1, 2)}, ),
    Device('dev3', {'current': 20}, {'a': (2, 3, 4, 5), 'b': (0, 1, 2), 'c': (0, 1, 2)}, ),
    '''
    
    prices = {'dev{0}'.format(i) : 100 *i for i in range(2000)}
            
    """
                'dev1': 100, 
                'dev2': 150,
                'dev3': 250,
    """

    option_prices = {
                        'a':{1: 10, 2: 20, 3:30, 4:40, 5:50},
                        'b':{0: 0, 1: 20, 2:40},
                        'c':{0: 0, 1: 40, 2:80},
                    }
                    
    run_in_gui_mode()