import sys
from django.test import RequestFactory
from software.views.pre_financiamiento import registrar_pre_financiamiento
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.messages.middleware import MessageMiddleware

try:
    factory = RequestFactory()
    request = factory.get('/pre-financiamiento/registrar/')
    
    # Add session
    middleware = SessionMiddleware(lambda r: None)
    middleware.process_request(request)
    request.session.save()
    request.session['idtipousuario'] = 1 # Fake session
    
    # Add messages
    middleware = MessageMiddleware(lambda r: None)
    middleware.process_request(request)
    
    response = registrar_pre_financiamiento(request)
    if response.status_code == 500:
        print("Response returned 500 directly")
    print(response.content.decode('utf-8')[:100])
except Exception as e:
    import traceback
    traceback.print_exc()
