from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import JournalLogForm


def journal_log_create(request):
    """Display and save a journal entry for the current user."""
    if request.method == "POST":
        form = JournalLogForm(request.POST, request.FILES)
        if form.is_valid():
            form.save_for_owner(request.user)
            return redirect("journal:create")
    else:
        form = JournalLogForm()

    return render(request, "journal/journal_log_form.html", {"form": form})
