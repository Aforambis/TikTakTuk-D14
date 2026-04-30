def current_role(request):
    role = request.session.get("role", "guest")
    return {
        "current_role": role,
        "role": role,
    }