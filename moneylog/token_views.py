from django.contrib import admin, messages
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.views.decorators.http import require_http_methods
from rest_framework.authtoken.models import Token


@require_http_methods(["GET", "POST"])
def api_token_view(request):
    """Personal page to show, (re)generate or revoke the user's API token."""
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "generate":
            Token.objects.filter(user=request.user).delete()
            Token.objects.create(user=request.user)
            messages.success(request, "Nuovo token generato. Il token precedente non è più valido.")
        elif action == "revoke":
            Token.objects.filter(user=request.user).delete()
            messages.success(request, "Token revocato.")
        return redirect("api_token")

    context = {
        **admin.site.each_context(request),
        "title": "Token API",
        "subtitle": "Gestisci il token per l'accesso alle API REST",
        "token": Token.objects.filter(user=request.user).first(),
    }
    return TemplateResponse(request, "admin/api_token.html", context)
