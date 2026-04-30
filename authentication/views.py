from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def login_page(request):
    context = {}
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        if not username or not password:
            context['error'] = 'Harap mengisi semua field.'
        else:
            role = 'customer'
            if username.lower() == 'admin': role = 'admin'
            elif username.lower() == 'organizer': role = 'organizer'
            request.session['active_role'] = role
            return redirect('/dashboard')
            
    return render(request, 'authentication/login.html', context)

@csrf_exempt
def register_role(request):
    return render(request, 'authentication/register_role.html')

def validate_registration(request, required_fields):
    data = {field: request.POST.get(field) for field in required_fields}
    password = request.POST.get('password')
    confirm_password = request.POST.get('confirm_password')
    terms = request.POST.get('terms')

    if any(not val for val in data.values()) or not password or not confirm_password:
        return 'Harap mengisi semua field.'
    if password != confirm_password:
        return 'Konfirmasi password tidak sesuai.'
    if not terms:
        return 'Anda harus menyetujui Syarat & Ketentuan.'
    return None

@csrf_exempt
def register_customer(request):
    context = {}
    if request.method == 'POST':
        error = validate_registration(request, ['full_name', 'email', 'phone_number', 'username'])
        if error:
            context['error'] = error
        else:
            return redirect('/auth/login/')
    return render(request, 'authentication/register_customer.html', context)

@csrf_exempt
def register_organizer(request):
    context = {}
    if request.method == 'POST':
        error = validate_registration(request, ['full_name', 'email', 'phone_number', 'username'])
        if error:
            context['error'] = error
        else:
            return redirect('/auth/login/')
    return render(request, 'authentication/register_organizer.html', context)

@csrf_exempt
def register_admin(request):
    context = {}
    if request.method == 'POST':
        error = validate_registration(request, ['username'])
        if error:
            context['error'] = error
        else:
            return redirect('/auth/login/')
    return render(request, 'authentication/register_admin.html', context)