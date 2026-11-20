from django.contrib.auth.forms import AuthenticationForm
from rest_framework import serializers

from .forms import AccountRemovalForm, ProfileForm, RegisterForm
from .models import Profile


def form_errors(form):
    return {field: list(errors) for field, errors in form.errors.items()}


class PublicProfileSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(read_only=True)
    avatar_url = serializers.SerializerMethodField()
    initials = serializers.CharField(read_only=True)
    joined_at = serializers.DateTimeField(source='user.date_joined', read_only=True)

    class Meta:
        model = Profile
        fields = ['id', 'user_id', 'display_name', 'bio', 'avatar_url', 'initials', 'joined_at']
        read_only_fields = fields

    def get_avatar_url(self, profile):
        url = profile.avatar_url
        request = self.context.get('request')
        return request.build_absolute_uri(url) if request and url else url


class ProfileSerializer(PublicProfileSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    photo = serializers.FileField(write_only=True, required=False)
    remove_photo = serializers.BooleanField(write_only=True, required=False, default=False)

    class Meta(PublicProfileSerializer.Meta):
        fields = PublicProfileSerializer.Meta.fields + ['username', 'email', 'photo', 'remove_photo']
        read_only_fields = ['id', 'user_id', 'avatar_url', 'initials', 'joined_at', 'username', 'email']

    def validate(self, attrs):
        profile = self.instance
        data = {
            'display_name': attrs.get('display_name', profile.display_name),
            'bio': attrs.get('bio', profile.bio if self.partial else ''),
            'remove_photo': attrs.get('remove_photo', False),
        }
        files = {'photo': attrs['photo']} if 'photo' in attrs else None
        self.profile_form = ProfileForm(data=data, files=files, instance=profile)
        if not self.profile_form.is_valid():
            raise serializers.ValidationError(form_errors(self.profile_form))
        return attrs

    def update(self, instance, validated_data):
        # Keep image validation, re-encoding and deletion identical to the web.
        return self.profile_form.save()


class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password1 = serializers.CharField(write_only=True, trim_whitespace=False)
    password2 = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs):
        self.register_form = RegisterForm(data=attrs)
        if not self.register_form.is_valid():
            raise serializers.ValidationError(form_errors(self.register_form))
        return attrs

    def create(self, validated_data):
        return self.register_form.save()


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs):
        form = AuthenticationForm(request=self.context['request']._request, data=attrs)
        if not form.is_valid():
            raise serializers.ValidationError(form_errors(form))
        self.user = form.get_user()
        return attrs


class AccountRemovalSerializer(serializers.Serializer):
    confirmation = serializers.CharField(max_length=100)

    def validate(self, attrs):
        form = AccountRemovalForm(data=attrs, profile=self.context['profile'])
        if not form.is_valid():
            raise serializers.ValidationError(form_errors(form))
        return attrs
