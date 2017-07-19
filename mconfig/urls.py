from django.conf.urls import url, include

from django.conf import settings
from django.conf.urls.static import static
import django.contrib.auth.views

from . import views

app_name = 'mconfig'

#url('^', include('django.contrib.auth.urls')),    

urlpatterns = [    
    url(r'^orders/$', views.OrderView.as_view(), name='orders'),
    url(r'^login/$', django.contrib.auth.views.login, {'template_name': 'mconfig/login.html'}, name='login'),
    url(r'^password_change/$', django.contrib.auth.views.password_change, 
        {'template_name': 'mconfig/password_change_form.html', 'post_change_redirect':'mconfig/password_change_done'}, name='password_change'),
    url(r'^.*?/password_change_done/$', django.contrib.auth.views.password_change_done, 
        {'template_name': 'mconfig/password_change_done.html'}, name='password_change_done'),
    url(r'^logout/$', views.logout, name='logout'),
    url(r'^start/$', views.config_start, name='config_start'),
    url(r'^start/([0-9]+)/questions/next$', views.next_question, name='next_question'),
    url(r'^start/([0-9]+)/questions/prev$', views.prev_question, name='prev_question'),
    url(r'^start/([0-9]+)/questions/update$', views.update_question, name='update_question'),
    url(r'^start/([0-9]+)/questions/$', views.question, name='question'),
    url(r'^start/([0-9]+)/questions/refresh/$', views.question_refresh, name='refresh_question'),
    url(r'^start/([0-9]+)/questions/fields/?$', views.field, name='field'),
    url(r'^start/([0-9]+)/questions/download/$', views.download, name='download'),
     url(r'^start/([0-9]+)/questions/send_mail/$', views.send_mail, name='send_mail'),
    #
    url(r'^create_user/(do)?$', views.create_user, name='create_user'),
    url(r'^request_access/(do)?$', views.request_access, name='request_access'),
    url(r'^upload_price/(do)?$', views.upload_price, name='upload_price'),
]  + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

