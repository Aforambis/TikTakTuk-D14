from django.shortcuts import redirect


def login_page(request):
    return redirect("/login/")


def register_role(request):
    return redirect("/register/")


def register_customer(request):
    return redirect("/register/?role=customer")


def register_organizer(request):
    return redirect("/register/?role=organizer")


def register_admin(request):
    return redirect("/register/?role=admin")
