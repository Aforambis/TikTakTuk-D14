from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt


def login_page(request):
    return redirect("/login/")


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
            username = request.POST.get("username").strip()
            registered_accounts = request.session.get("registered_accounts", {})
            registered_accounts[username] = {
                "password": request.POST.get("password"),
                "role": "customer",
                "name": request.POST.get("full_name").strip() or username,
            }
            request.session["registered_accounts"] = registered_accounts
            request.session.modified = True

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
            username = request.POST.get("username").strip()
            registered_accounts = request.session.get("registered_accounts", {})
            registered_accounts[username] = {
                "password": request.POST.get("password"),
                "role": "organizer",
                "name": request.POST.get("full_name").strip() or username,
            }
            request.session["registered_accounts"] = registered_accounts
            request.session.modified = True

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
            username = request.POST.get("username").strip()
            registered_accounts = request.session.get("registered_accounts", {})
            registered_accounts[username] = {
                "password": request.POST.get("password"),
                "role": "admin",
                "name": username, 
            }
            request.session["registered_accounts"] = registered_accounts
            request.session.modified = True

            return redirect('/auth/login/')
    return render(request, 'authentication/register_admin.html', context)