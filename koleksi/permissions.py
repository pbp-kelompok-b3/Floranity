from rest_framework.permissions import BasePermission


class IsPlantOwner(BasePermission):
    """Hanya mengizinkan pengguna login yang merupakan pemilik tanaman."""

    message = "Hanya pemilik tanaman yang dapat mengakses atau mengubah data ini."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        return obj.pemilik_id == request.user.id
