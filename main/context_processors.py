def current_role(request):
    """
    Expose the simulated role to all templates.

    Usage in templates: {{ current_role }}
    """

    return {"current_role": request.session.get("role", "guest")}
