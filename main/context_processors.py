def current_role(request):
    allowed_roles = {"guest", "admin", "organizer", "customer"}
    role = str(request.session.get("role", "guest")).strip().lower()

    if role not in allowed_roles:
        role = "guest"

    return {
        "current_role": role,
        "role": role,
        "current_username": request.session.get("username", ""),
        "current_display_name": request.session.get("display_name", ""),
    }
