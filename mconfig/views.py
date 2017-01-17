from django.shortcuts import render

# Create your views here.

from django.http import HttpResponse, HttpResponseNotFound, HttpResponseRedirect, HttpResponseServerError
from django.template import loader

from django.utils.translation import activate, check_for_language, get_language
from django.utils.translation import ugettext as _

from django.views.static import serve
from django.views import generic

from django.contrib.auth import views as auth_views
import django.contrib.auth
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import PermissionRequiredMixin, AccessMixin
from django.contrib.auth.models import User, Permission
from django.contrib.contenttypes.models import ContentType

from django.urls import reverse
#from django.core.urlresolvers import reverse

from mconfig.models import Order, Profile

from field_views import HTMLChoiceMixin, HTMLEditMixin, HTMLCompoundMixin, HTMLOneOfManyMixin, HTMLSearchChoiceMixin, HTMLStreetAddressMixin
import price

price.price_lists['VEDADrive'] = price.VEDAXLPriceList('prices.xlsm')

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import threading
import datetime

import devices
import questions
import wizard
import time
import traceback

import locale

import os
import os.path

import json

#import rpdb2
#rpdb2.start_embedded_debugger('123qwe')

#locale.setlocale(locale.LC_ALL, 'ru')

#wizard instances are stored here
sessions = {}
last_id = 0
lock = threading.Lock()


def send_mail(server, from_, to, subject, html, text):
    msg = MIMEMultipart('alternative')
    html = html

    msg['Subject'] = subject
    msg['From'] = from_
    msg['To'] = to

    part1 = MIMEText(text, 'plain')
    part2 = MIMEText(html, 'html')

    msg.attach(part1)
    msg.attach(part2)

    s = smtplib.SMTP(server)
    s.sendmail(from_, to, msg.as_string())
    s.quit()

class Reaper(threading.Thread):    
    #deletes inactive sessions after 1 day
    def __init__(self):
        threading.Thread.__init__(self)
        self.daemon = True
        
    def run(self):      
        try:
            while True:
                time.sleep(600)
                #print('Reaper: checking sessions')
                to_reap = []
                with lock:
                    for k,v in sessions.items():                    
                            if (datetime.datetime.now() - v.last_activity).days >= 1:
                                print('Reaper: session {0} will be reaped'.format(k))
                                to_reap.append(k)
                                #del sessions[k]
                            else:
                                pass
                                #print('Let it leave, last active at {0}'.format(v.last_activity))
                    for k in to_reap:
                        del sessions[k]
        except:
            traceback.print_exc()
                    
#reaper = Reaper()
#reaper.start()

if check_for_language('ru'):
    print('Has Russian')
    activate('ru')
else:
    print('No Russian, sorry')
    
#print(get_language())
print(_('Hello'))
#todo: move to separate module
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
        def get_nom_current(device):
            return device.attributes['nom_current']
        return [list(sorted(devices, key=get_nom_current))[0]]
        
    def select_choice(self, devices, choice):
        return choice.get_valid_choices(devices)

settings = Settings()
decider = Decider(settings)

#test_dev = devices.VEDADrive.from_order_code('VD-P2000U1F531SSX192ACA21B2CXDX21E1S')
#print(test_dev)

class HTMLQuestion:
    template = "mconfig/question.html"

    def as_json(self):       
        return json.dumps({ 'name': self.question.header, 
                            'error': self.question.last_error, 
                            'next_enabled': self.question.can_proceed(),
                            'prev_enabled': self.question.previous is not None,
                            'fields': [f.view.as_json() for f in self.question.get_fields()]
                            })

class VEDADriveView:
    _template = "VEDADrive.html"
    @property
    def template(self):
        return self._template
    
    def as_json(self):                
        return {    
                    'name': self.package.name,
                    'order_code': self.package.order_code(),
                    'short_descr': self.package.short_descr(),
                    'options': {option : value for option,value in self.package.options.items()}
                }
        
class PriceView:
    _template = "price.html"
    @property
    def template(self):
        return self._template

    def as_json(self):                
        dv = PriceDetailsView()
        dv.price = self.price
        return {'total': self.price.total, 'details': dv.as_json()}
        
class PriceDetailsView:
    _template = "price.html"                            
    def template(self):
        return self._template

    def as_json(self):                
        return {'supplier_price': self.price.supplier_price,
                'delivery_cost': self.price.delivery_cost,
                'sale_price': self.price.sale_price}
                            
class HTMLResult:
    _template = "mconfig/result.html"
    _unpriced_template = "mconfig/result_unpriced.html"

    @property
    def template(self):
        return self._template
    
    #TODO: view should tell if current user has appropriate access level
    def as_json(self):        
        package = self.question.packages[0]        
        package.view = VEDADriveView()
        package.view.package = package
        try:
            package.calculate_price()
            package.price.view = PriceView()
            package.price.view.price = package.price
            return json.dumps({'package': package.view.as_json(),
                                'price': package.price.view.as_json(),
                                })            
        except price.NotInPricelist:
            return json.dumps({'package': package.view.as_json(),
                                'price': None,
                                })
        
class HTMLWizard(wizard.Wizard):
    def __init__(self, devices, questions):
        views = {}        
        wizard.Wizard.__init__(self, devices)
        for question in questions:
            #self.append_screen(HTMLQuestion(question), views=views)
            self.append_screen(question, views=views)

def add_wizard_instance(request):
    session = request.session
    global sessions, last_id
    #html mixins just provide template names
    views = {
                wizard.SearchChoiceField: HTMLSearchChoiceMixin, 
                wizard.ChoiceField: HTMLChoiceMixin, 
                wizard.ValueField: HTMLEditMixin,
                wizard.CompoundField: HTMLCompoundMixin,
                wizard.OneOfManyField: HTMLOneOfManyMixin,
                wizard.StreetAddressField:HTMLStreetAddressMixin,
            }
            
    qs = [
        questions.LoadQuestion(devices.devices, views, view=HTMLQuestion()),
        questions.PlacementQuestion(devices.devices, views, view=HTMLQuestion()),
        questions.OptionsQuestion(devices.devices, views, view=HTMLQuestion()),
        questions.DeliveryQuestion(devices.devices, views, view=HTMLQuestion(), user_getter = lambda: request.user),
        wizard.Result(decider, view=HTMLResult())
        ]
        
    wiz = HTMLWizard(devices.devices, qs)
    wiz.last_activity = datetime.datetime.now()
    
    with lock:
        cur_id = last_id
        sessions[last_id] = wiz
        session['wizard'] = last_id
        last_id += 1
        
    wiz.start()
    return cur_id
    
def is_superuser(user):
    return user.is_superuser
    
class OrderView(PermissionRequiredMixin, AccessMixin, generic.ListView):
    template_name = 'mconfig/order.html'
    context_object_name = 'orders'
    permission_required = 'mconfig.view_all_orders'
    login_url = '/mconfig/login/'

    def get_queryset(self):
        """Return the last five published questions."""
        return Order.objects.all()        
    
def request_access(request, action):
    if request.method == 'GET':
        template = loader.get_template('mconfig/request_access.html')
        context={}
        return HttpResponse(template.render(context, request))
    elif request.method == 'POST':
        access_level = 2
        user = User.objects.filter(username=request.POST['email'])        
        user = user[0] if user else None
            
        profile = Profile.objects.filter(email=request.POST['email'])
        profile = profile[0] if profile else None
        
        if user is None and profile is None:
            user = User.objects.create_user(request.POST['email'], request.POST['email'], 'danfoss')
            profile = Profile(first_name=request.POST['first_name'], last_name = request.POST['last_name'], organization=request.POST['organization'], email=request.POST['email'], role=access_level, registered=False)
            user.is_active = False
            user.profile = profile
            profile.user = user
            profile.save()        
            user.save()
            
            msg = '''\
<html>
  <head></head>
  <body>
    Hello
    {0} {1} from {2} has asked for VEDADrive configurator access.
    To grant it please follow the <a href="http://pc0149941:8000/mconfig/create_user?email={3}">link</a> and click "Submit"
  </body>
</html>
'''.format(request.POST['first_name'], request.POST['last_name'], request.POST['organization'], request.POST['email'])

            text = '{0} {1} from {2} has asked for VEDADrive configurator access.\n To grant it go to http://pc0149941:8000/mconfig/create_user?email={3} and click "Submit"'.format(request.POST['first_name'], request.POST['last_name'], request.POST['organization'], request.POST['email'])                       
            send_mail('localhost', 'pl@mydomain.org', 'manager@myconfirm.org', 'Mconfig registration request', msg, text)
            return HttpResponse('Registration request created, await confirmation email')
        else:
            return HttpResponse('Email already registered')            
    
@user_passes_test(is_superuser, login_url='/mconfig/login/')
def create_user(request, action):
    if request.method == 'GET':
        template = loader.get_template('mconfig/create_user.html')
        if 'email' in request.GET:
            profile = Profile.objects.get(email=request.GET['email'])
            context = {'profile': profile}
        else:
            context = {}
        return HttpResponse(template.render(context, request))
    elif request.method == 'POST':
        print(request.POST['email'], request.POST['password'])
        access_level = int(request.POST['role'])
        
        try:
            user = User.objects.get(username=request.POST['email'])        
        except User.DoesNotExist:
            user = None
            
        try:
            profile = Profile.objects.get(email=request.POST['email'])
        except Profile.DoesNotExist:
            user = None
        
        
        if user is None:
            if access_level > 0:
                user = User.objects.create_user(request.POST['email'], request.POST['email'], 'danfoss')
            else:
                user = User.objects.create_superuser(request.POST['email'], request.POST['email'], 'danfoss')
        else:
            user.first_name = request.POST['first_name']
            user.last_name = request.POST['last_name']
            user.is_active = True
            
        if profile is None:
            profile = Profile(first_name=request.POST['first_name'], last_name = request.POST['last_name'], organization=request.POST['organization'], email=request.POST['email'], role=access_level, registered=True)
        else:
            profile.first_name = request.POST['first_name']
            profile.last_name = request.POST['last_name']
            profile.role = access_level
            
        user.profile = profile
        profile.user = user
        
        if access_level > 0:                               
            user.user_permissions.clear()
            if access_level == 1:
                content_type = ContentType.objects.get_for_model(Order)    
                permission = Permission.objects.get(content_type=content_type, codename='view_price') 
                user.user_permissions.add(permission)
                permission = Permission.objects.get(content_type=content_type, codename='view_delivery')
                user.user_permissions.add(permission)
            elif access_level == 2:
                content_type = ContentType.objects.get_for_model(Order)    
                permission = Permission.objects.get(content_type=content_type, codename='view_price')                 
                user.user_permissions.add(permission)
                permission = Permission.objects.get(content_type=content_type, codename='view_delivery')
                user.user_permissions.add(permission)
                
        profile.save()        
        user.save()
        msg = '''\
<html>
  <head></head>
  <body>
    Hello
    You have been given access to VEDADrive configurator. To access extended functions please follow the <a href="http://pc0149941:8000/mconfig/login">link</a>, use your email as login and "danfoss" as password.
  </body>
</html>
'''

        text = '''Hello
        You have been given access to VEDADrive configurator. To access extended functions please go to http://pc0149941:8000/mconfig/login, use your email as login and "danfoss" as password.'''
        send_mail('localhost', 'manager@myconfirm.org', request.POST['email'], 'Mconfig registration confirmation', msg, text)            
        
        return HttpResponse('User created OK')
    
def login(request):
    print('login')
    template_response = views.login(request)
    # Do something with `template_response`
    return template_response
    
def logout(request):
    django.contrib.auth.logout(request)
    return HttpResponseRedirect('/mconfig/login/')

def index(request):
    print('mconfig start page')
    template = loader.get_template('mconfig/index.html')
    context = {}
    return HttpResponse(template.render(context, request))

#@login_required(login_url='/mconfig/login/')
def config_start(request):
    print('config_start')       
    id = add_wizard_instance(request)   
    template = loader.get_template('mconfig/start.html')
    return HttpResponseRedirect('/mconfig/start/{0}/questions'.format(id))
    
def download(request, session):
    wiz = sessions[int(session)]
    print (session, wiz)
    package = wiz.screens[-1].packages[0]
    filepath = 'C:\\Users\\u327397\\Desktop\\Projects\\HV\\configurator\\mysite\\test.docx'
    path = os.path.join(os.path.dirname(filepath), '{0}.{1}'.format(session, 'docx'))
    package.make_offer_template(path)    
    '''
    date = models.DateField(auto_now_add=True)
    price_version = models.CharField(max_length=60)
    typecode = models.CharField(max_length=60)
    price = models.DecimalField(max_digits=12, decimal_places=3)
    user = models.ForeignKey(User)
    '''    
    user = request.user
    try:
        profile = Profile.objects.get(email=user.email)    
        order = Order(date = datetime.date.today(), price_version = '0.0', typecode = package.order_code(), price=package.price.sale_price, user=user)
        order.save()
    except Profile.DoesNotExist:
        pass
    
    return serve(request, os.path.basename(path), os.path.dirname(path))

def field(request, session):
    try:
        wiz = sessions[int(session)]    
    except KeyError:
        return HttpResponse('Session not found or expired (field): {0}, have sessions {1}'.format(int(session), list(sessions.keys())))
    context = {}
    wiz.last_activity = datetime.datetime.now()
    
    question = wiz.current_screen
    
    field = request.GET['field']
    #print(request.GET)
    print('requested field', field)
    try:
        f = question.get_field(field)
        
        template = loader.get_template(f.view.template)
        
        context['field'] = f    
        context['as_xml'] = True
        res = HttpResponse(template.render(context, request), content_type="text/xml")
        return res    
    except KeyError:
        return HttpResponseNotFound('Field not found')
    
def question_refresh(request, session, _context={}, error=''):
    #TODO: check user permissions - can be Result!!!
    try:
        wiz = sessions[int(session)]    
    except KeyError:
        return HttpResponse('Session not found or expired (refresh): {0}, have sessions {1}'.format(int(session), list(sessions.keys())))
    context = dict(_context)
    wiz.last_activity = datetime.datetime.now()
    
    question = wiz.current_screen
    question.last_error = error
    
    data = question.view.as_json()
    return HttpResponse(data, content_type="application/json")    
    
def show_question(session, request, wiz, context):   
    question = wiz.current_screen     
    template = loader.get_template(question.view.template)
    context['question'] = wiz.current_screen
    #context['devices'] = [decider.select_devices(wiz.apply_filters_nosave(question.next, options=opts))]
    #context['options'] = wiz.get_options(question)                          

    res = HttpResponseRedirect(reverse('mconfig:question', args=(session, )))
    return res                                
    
def next_question(request, session):
    try:
        wiz = sessions[int(session)]    
    except KeyError:
        return HttpResponse('Session not found or expired (next): {0}, have sessions {1}'.format(int(session), list(sessions.keys())))
    context = {}
    wiz.last_activity = datetime.datetime.now()

    try:
        wiz.go_forward()
    except wizard.ValidationError as ex:
        print('ValidationError', ex.message)
        context['error_message'] = ex.message        
        #context['devices'] = [decider.select_devices(wiz.apply_filters_nosave(question.next))]
        #context['options'] = wiz.get_options(question)      
                
    return show_question(session, request, wiz, context)

def prev_question(request, session):
    user = request.user
    try:
        wiz = sessions[int(session)]    
    except KeyError:
        return HttpResponse('Session not found or expired (prev): {0}, have sessions {1}'.format(int(session), list(sessions.keys())))
    context = {}
    wiz.last_activity = datetime.datetime.now()
    wiz.go_back()
    return show_question(session, request, wiz, context)
    
def update_question(request, session):
    #updates all fields, should be triggered on any field change
    user = request.user
    try:
        wiz = sessions[int(session)]    
    except KeyError:
        return HttpResponse('Session not found or expired(update): {0}, have sessions {1}'.format(int(session), list(sessions.keys())))
    context = {}
    wiz.last_activity = datetime.datetime.now()

    question = wiz.current_screen
    try:
        field = question.find_field(request.POST['Current_field'])
        try:
            wiz.update(question, field, request.POST[field.name])
        except wizard.NoMatches:
            #no devices for this value, this may happen if user sets value in edit that filters out all devices
            error = _('No device matches value {0} for field {1}').format(request.POST[field.name], field.name)                              
            return question_refresh(request, session, context, error)
        except ValueError:
            #invalid value
            error = _('Invalid value {0} for field {1}').format(request.POST[field.name], field.name)                    
            return question_refresh(request, session, context, error)
    except KeyError:
        print('KeyError', request.POST['Current_field'])
    
    #opts = wiz.get_options(question)  
    #prev_devs = wiz.apply_filters_nosave(question, options=opts)
        
    #for field in question.fields:
    #    field.update(prev_devs, opts)
    
    #return show_question(session, request, wiz, context)
    return question_refresh(request, session, context, '')
    
def question(request, session):
    start_time = datetime.datetime.now()
    try:
        wiz = sessions[int(session)]    
    except KeyError:
        return HttpResponse('Session not found or expired (question): {0}, have sessions {1}'.format(int(session), list(sessions.keys())))
        
    context = {}
    wiz.last_activity = datetime.datetime.now()
    if request.method == 'GET':    
        question = wiz.current_screen
        question.select()
        print(type(question), question.view.template)
        opts = wiz.get_options(question)  
        all_devs = wiz.apply_filters_nosave(question.next, options=opts)
        devs = decider.select_devices(all_devs)
        template = loader.get_template(question.view.template)
        
        for field in question.fields:
            wiz.refresh_field(question, field)

        #prev_devs = wiz.apply_filters_nosave(question, options=opts)
        #for field in question.fields:
        #    field.update(prev_devs, opts)
        
        question.last_error = ''
        context['user'] = request.user
        context['question'] = question
        #context['devices'] = wiz.devs
        context['devices'] = devs
        context['options'] = opts
        context['full'] = True
        
        res = HttpResponse(template.render(context, request))
        end_time = datetime.datetime.now()
        print('Request took {0}'.format(end_time-start_time))
        return res
    