import price
import functools
import collections
import operator
import openpyxl
import codecs
import types
import delivery

#import docx
#from docx.oxml.shared import qn

from django.utils.translation import ugettext as _

'''
class PriceNotSpecified(Exception):
    pass

class NotInPricelist(Exception):
    pass
'''

'''
def get_bookmark_par_element(document, bookmark_name):
    """
    Return the named bookmark element
    """
    #doc_element = document._document_part._element
    doc_element = document._element
    bookmarks_list = doc_element.findall('.//' + qn('w:bookmarkStart'))
    for bookmark in bookmarks_list:
        name = bookmark.get(qn('w:name'))
        if name == bookmark_name:
            print (bookmark, type(bookmark))
            #test
            return bookmark
            par = bookmark.getparent()
            if not isinstance(par, docx.oxml.CT_P): 
                raise ValueError('Unexpected parent type', par, type(par))
            else:
                return par
    raise KeyError('Bookmark not found', bookmark_name)
'''

'''    
def insert_text(par, text):            
    tmp_doc = docx.Document()
    tmp_doc.add_paragraph(text)
    bookmark_par_parent = par.getparent()
    index = bookmark_par_parent.index(par) + 1
    for child in tmp_doc._element.body:
        bookmark_par_parent.insert(index, child)
        index = index + 1
    #bookmark_par_parent.remove(par)
'''

class Device:
    '''
    generic device
    subclass to customize price calculation, typecode generation and so on
    '''
    def __init__(self, name, attributes, options, package=False):
        self.name = name
        self.options = dict(options)
        self.attributes = dict(attributes)
        self.is_package = package
        self.template = "mconfig/package.html"
        self.price = None        
        
    def package(self, options, decider):
        new_options = {on: ov for on, ov in options.items()}
        for on, ov in self.options.items():
            if on not in options:               
                #option not specified - select default
                #default selection logic may be altered by user!                
                new_options[on] = decider.select_option(self, on)
                
        return Device(self.name, self.attributes, new_options, package=True)
                    
    def price(self):
        if not self.is_package:     
            raise ValueError('Can only calculate price for packages')
        pr = price.prices[self.name]
        print(self.options)
        pr += sum([price.option_prices[on][ov] for on, ov in self.options.items()])
        return pr
        
    def __repr__(self):
        return 'Device: {0}\n\tattrs{1}\n\toptions{2}\n'.format(self.name, self.attributes, self.options)
        
    def typecode(self):
        return ''
        
class VEDADrive(Device):
    def __init__(self, name, attributes, options=None, package=False):
        Device.__init__(self, name, {}, {}, package)
        self._attrs = attributes
        self.attributes = VEDAAttrs(self)
        self.template = "mconfig/VEDADrive.html"
        
        if options:
            self.options = VEDAOpts(**options)
        else:
            self.options = VEDAOpts()
            
    def order_code(self):
        assert(self.is_package)
        fields = [(0, self.name), (17, '{0:03}'.format(self.attributes['nom_current']))] \
            + [(self.options._opts[n].code_pos, self.options._opts[n].choices_to_codes[v]) for n,v in self.options.items() if n in self.options._opts]
        return ''.join([f[1] for f in sorted(fields, key=operator.itemgetter(0))])

    def package(self, options, decider):
        #check if we need power transformer                    
        options = dict(options)
        drive_voltage = self.attributes['voltage']
        if 'motor_voltage' in options:
            print('Drive voltage:', drive_voltage)
            print('Motor voltage:', options['motor_voltage'])
            if self.attributes['voltage'] != options['motor_voltage']:
                motor_voltage = options['motor_voltage']
                options['transformer'] =  str(drive_voltage) + '-' + str(motor_voltage)                
        else:
            raise KeyError('Motor voltage is not specified')
        
        new_options = collections.OrderedDict()
        
        for on in self.options._opts:                
            if on not in options:
                #option not specified - select default
                #default selection logic may be altered by user!                
                new_options[on] = decider.select_option(self, on)
            else:
                new_options[on] = options[on]
                
        for n,v in options.items():
            if n not in new_options:
                new_options[n] = v
                
        return VEDADrive(self.name, self.attributes, new_options, package=True)
       
    def calculate_price(self):
        assert(self.is_package)
        pricelist = price.price_lists['VEDADrive']
        self.price = pricelist.get_price(self)
        _, self.price.delivery_cost, _ = delivery.get_delivery_details(self)
        #calculate delivery costs        
                
    def make_offer_template(self, path):            
        assert(self.is_package)
        assert(self.price)
        '''
        doc = docx.Document('offer_template.docx')
        par = get_bookmark_par_element(doc, "order_code")
        insert_text(par, self.order_code())
                
        par = get_bookmark_par_element(doc, "price")
        insert_text(par, self.price.sale_price)
        
        doc.save(path)
        '''
        
    def short_descr(self):
        return _('VEDADRIVE {0}kV, {1} kVA, {2}, {3} {4}').format(self.attributes['voltage']//1000, self.attributes['kVA'], _('Air-cooled') if self.options['cooling']=='Air' else __('Liquid_cooled') ,self.options['enclosure'], self.options['Service access'])

    #do not use, use PriceList.package_matches_pricelist()
    def matches_pricelist(self, row):
        price_name = '{0}-{1}{2}'.format(row[1].value, row[2].value, row[4].value)
        if self.name != price_name:
            return False
            
        for name,val in self.options._opts.items():
            if not val.matches_pricelist(self.options[name], row):
                return False
            
        return True
        
    def delivery_items(self):
        #TODO: get weight (and mb size) of drive components
        assert(self.is_package)
        return [15, ]
        
        
class VEDAAttrs:
    def __init__(self, drive):
        self.drive = drive
        
    def __getitem__(self, key):
        if key == 'overload_current':
            return self.drive._attrs['nom_current'] * 1.2
        else:
            return self.drive._attrs[key]
            
class VEDAOption:
    def __init__(self, name, choices, codes, code_pos, display_names=None, display_choices=None, price_field=None, price_getter=None):
        self.name = name
        self.choices = choices
        self.codes = codes
        self.code_pos = code_pos
        self.choices_to_codes = dict(zip(choices, codes))
        self.codes_to_choices = dict(zip(codes, choices))
        self.price_field = price_field
        self.price_getter = price_getter
           
    def matches_pricelist(self, option_value, row):        
        '''
        TODO: should be def matches_pricelist(self, option_value, entry):
            return entry.get_option(self.name) == option_value
        '''
        if self.price_getter is not None:            
            price_opt = self.price_getter(self, row[self.price_field].value)
            return price_opt == option_value                
        else:
            return True        
        
    def generic_getter(self, value):
        return self.codes_to_choices[str(value)]
        
    def letter_getter (self, value):
        prefix = self.codes[0][0]
        try:
            value = value.replace('Х', 'X')
            return self.codes_to_choices[prefix + str(value)]
        except KeyError:
            print ('Unknown option code', prefix + str(value))
            print (codecs.encode(prefix + str(value), 'unicode_escape'))
            print ('Have', self.codes_to_choices)
            raise
        
    def mains_getter(self, value):
        return self.codes_to_choices[str(value)[0]]
        
    def motor_getter(self, value):
        return self.codes_to_choices[str(value)[1]]
        
    def poweropt_getter(self, value):
        if value=='XX':
            return self.codes_to_choices['AX']
        else:
            return self.codes_to_choices['A'+str(value)[0]]
            
class VEDAOpts:
    def __init__(self, **args):
        self._opts = collections.OrderedDict()
        for o in (
                    VEDAOption('motor_type', ('Induction', 'PM'), ('A', 'S'), 14, price_field=7, price_getter=VEDAOption.generic_getter),
                    VEDAOption('input_freq', (50, 60), ('F5', 'F6'), 10, price_field=5, price_getter=VEDAOption.generic_getter),
                    VEDAOption('enclosure', ('IP30', 'IP31', 'IP41', 'IP42', 'IP54'), ('30', '31', '41', '42', '54'), 12, price_field=6, price_getter=VEDAOption.generic_getter),
                    VEDAOption('control_mode', ('U/f', 'Vector control'), ('S', 'V'), 15, price_field=8, price_getter=VEDAOption.generic_getter),
                    VEDAOption('brake_mode', ('Coast', 'Dynamic', 'Recuperation'), ('X', 'B', 'R'), 16, price_field=9, price_getter=VEDAOption.generic_getter),
                    VEDAOption('cooling', ('Air', 'Liquid'), ('A', 'L'), 20, price_field=11, price_getter=VEDAOption.generic_getter),
                    VEDAOption('power_cell_autobypass', ('No', 'Yes'), ('X', 'C'), 21, price_field=12, price_getter=VEDAOption.generic_getter),
                    VEDAOption('power_option', ('None', 'Manual bypass', 'Autobypass', 'Multistart', 'Interchange'), ('AX', 'A2', 'A1', 'A3', 'A4'), 22, price_field=13, price_getter=VEDAOption.poweropt_getter),
                    VEDAOption('multi_motors', (1, 2, 3, 4), ('1', '2', '3', '4'), 24, price_field=13, price_getter=None),
                    VEDAOption('fieldbus', ('None', 'Encoder', 'EtherNet IP', 'ProfiBus DP', 'Modbus TCP/IP'), ('BX', 'B1', 'B2', 'B3', 'B4'), 25, price_field=14, price_getter=VEDAOption.letter_getter),
                    VEDAOption('transformer', ('None', '10000-6000', '10000-6600', '6000-10000', '6600-10000'), ('CX', 'C1', 'C2', 'C3', 'C4'), 27, price_field=15, price_getter=VEDAOption.letter_getter),
                    VEDAOption('PMSM exciter', ('No', 'Yes'), ('DX', 'D1'), 29, price_field=16, price_getter=VEDAOption.letter_getter),
                    VEDAOption('Input mains location', ('Top', 'Bottom'), ('2', '1'), 31, price_field=17, price_getter=VEDAOption.mains_getter),
                    VEDAOption('Motor cable location', ('Top', 'Bottom'), ('2', '1'), 32, price_field=17, price_getter=VEDAOption.motor_getter),
                    VEDAOption('Output reactor', ('No', 'Yes'), ('EX', 'E1'), 33, price_field=18, price_getter=VEDAOption.letter_getter),
                    VEDAOption('Service access', ('Front', 'Front and back'), ('S', 'D'), 35, price_field=19, price_getter=VEDAOption.generic_getter),                    
                    VEDAOption('motor_voltage', (6000, 10000), ('', ''), 0),
                ):
            self._opts[o.name] = o        
        
        self.opts = collections.OrderedDict()
        for on, ov in self._opts.items():
                self.opts[on] = ov.choices
                
        self.opts.update(args)

    def __getitem__(self, key):
        return self.opts[key]
        
        
    def infos(self):
        return self._opts.items()
        
    def items(self):
        #print(self.opts)
        #print(list(self.opts.items()))
        return self.opts.items()

devices = [
    VEDADrive('VD-P315KU1', attributes={'voltage': 6000, 'nom_current': 31, 'kVA': 315}),
    VEDADrive('VD-P400KU1', attributes={'voltage': 6000, 'nom_current': 40, 'kVA': 400}),
    VEDADrive('VD-P500KU1', attributes={'voltage': 6000, 'nom_current': 48, 'kVA': 500}),
    VEDADrive('VD-P630KU1', attributes={'voltage': 6000, 'nom_current': 61, 'kVA': 630}),
    VEDADrive('VD-P800KU1', attributes={'voltage': 6000, 'nom_current': 77, 'kVA': 800}),
    VEDADrive('VD-P1000U1', attributes={'voltage': 6000, 'nom_current': 96, 'kVA': 1000}),
    VEDADrive('VD-P1250U1', attributes={'voltage': 6000, 'nom_current': 130, 'kVA': 1250}),
    VEDADrive('VD-P1600U1', attributes={'voltage': 6000, 'nom_current': 154, 'kVA': 1600}),
    VEDADrive('VD-P1800U1', attributes={'voltage': 6000, 'nom_current': 173, 'kVA': 1800}),
    VEDADrive('VD-P2000U1', attributes={'voltage': 6000, 'nom_current': 192, 'kVA': 2000}),
    VEDADrive('VD-P2250U1', attributes={'voltage': 6000, 'nom_current': 230, 'kVA': 2250}),
    VEDADrive('VD-P2500U1', attributes={'voltage': 6000, 'nom_current': 243, 'kVA': 2500}),
    VEDADrive('VD-P2800U1', attributes={'voltage': 6000, 'nom_current': 275, 'kVA': 2800}),
    VEDADrive('VD-P3200U1', attributes={'voltage': 6000, 'nom_current': 304, 'kVA': 3200}),
    VEDADrive('VD-P3500U1', attributes={'voltage': 6000, 'nom_current': 340, 'kVA': 3500}),
    VEDADrive('VD-P4000U1', attributes={'voltage': 6000, 'nom_current': 400, 'kVA': 4000}),
    VEDADrive('VD-P4500U1', attributes={'voltage': 6000, 'nom_current': 425, 'kVA': 4500}),
    VEDADrive('VD-P5000U1', attributes={'voltage': 6000, 'nom_current': 500, 'kVA': 5000}),
    VEDADrive('VD-P6300U1', attributes={'voltage': 6000, 'nom_current': 600, 'kVA': 6300}),
    VEDADrive('VD-P7000U1', attributes={'voltage': 6000, 'nom_current': 660, 'kVA': 7000}),
    VEDADrive('VD-P7900U1', attributes={'voltage': 6000, 'nom_current': 750, 'kVA': 7900}),
    VEDADrive('VD-P8250U1', attributes={'voltage': 6000, 'nom_current': 800, 'kVA': 8250}),
    
    VEDADrive('VD-P500KU3', attributes={'voltage': 10000, 'nom_current': 31, 'kVA': 500}),
    VEDADrive('VD-P630KU3', attributes={'voltage': 10000, 'nom_current': 40, 'kVA': 630}),
    VEDADrive('VD-P800KU3', attributes={'voltage': 10000, 'nom_current': 48, 'kVA': 800}),
    VEDADrive('VD-P1000U3', attributes={'voltage': 10000, 'nom_current': 61, 'kVA': 1000}),
    VEDADrive('VD-P1250U3', attributes={'voltage': 10000, 'nom_current': 77, 'kVA': 1250}),
    VEDADrive('VD-P1600U3', attributes={'voltage': 10000, 'nom_current': 96, 'kVA': 1600}),
    VEDADrive('VD-P1800U3', attributes={'voltage': 10000, 'nom_current': 104, 'kVA': 1800}),
    VEDADrive('VD-P2000U3', attributes={'voltage': 10000, 'nom_current': 115, 'kVA': 2000}),
    VEDADrive('VD-P2250U3', attributes={'voltage': 10000, 'nom_current': 130, 'kVA': 2250}),
    VEDADrive('VD-P2500U3', attributes={'voltage': 10000, 'nom_current': 154, 'kVA': 2500}),
    VEDADrive('VD-P2800U3', attributes={'voltage': 10000, 'nom_current': 165, 'kVA': 2800}),
    VEDADrive('VD-P3150U3', attributes={'voltage': 10000, 'nom_current': 192, 'kVA': 3150}),
    VEDADrive('VD-P3500U3', attributes={'voltage': 10000, 'nom_current': 205, 'kVA': 3500}),
    VEDADrive('VD-P4000U3', attributes={'voltage': 10000, 'nom_current': 243, 'kVA': 4000}),
    VEDADrive('VD-P4500U3', attributes={'voltage': 10000, 'nom_current': 260, 'kVA': 4500}),
    VEDADrive('VD-P5000U3', attributes={'voltage': 10000, 'nom_current': 304, 'kVA': 5000}),
    VEDADrive('VD-P5630U3', attributes={'voltage': 10000, 'nom_current': 325, 'kVA': 5630}),
    VEDADrive('VD-P6300U3', attributes={'voltage': 10000, 'nom_current': 364, 'kVA': 6300}),
    VEDADrive('VD-P7000U3', attributes={'voltage': 10000, 'nom_current': 400, 'kVA': 7000}),
    VEDADrive('VD-P7900U3', attributes={'voltage': 10000, 'nom_current': 462, 'kVA': 7900}),
    VEDADrive('VD-P8900U3', attributes={'voltage': 10000, 'nom_current': 500, 'kVA': 8900}),
    VEDADrive('VD-P10M0U3', attributes={'voltage': 10000, 'nom_current': 600, 'kVA': 10000}),
    VEDADrive('VD-P12M5U3', attributes={'voltage': 10000, 'nom_current': 800, 'kVA': 12500}),
]
