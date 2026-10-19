from django.http import JsonResponse

from .models import Note


def create_note(request):
    note = Note.objects.create(title=request.POST["title"], phone=request.POST.get("phone", ""), secret=request.POST.get("secret", ""))
    return JsonResponse({"id": note.pk})


def edit_note(request, pk):
    note = Note.objects.get(pk=pk)
    for name in ("title", "phone", "secret"):
        if name in request.POST:
            setattr(note, name, request.POST[name])
    note.save()
    return JsonResponse({"id": note.pk})
