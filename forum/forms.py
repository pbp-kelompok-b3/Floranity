from django.forms import ModelForm, TextInput, Textarea
from forum.models import Post, Comment

class PostForm(ModelForm):
    class Meta:
        model = Post
        
        fields = [
            "post_title",
            "post_body",
            "tag"
        ]

        labels = {
            "post_title" : "Judul Post",
            "post_body" : "Isi Post",
            "tag" : "Tag Post"
        }

        widgets = {
            "post_title" : TextInput(
                attrs={
                    "placeholder" : "Masukkan judul post",
                }
            ),

            "post_body" : Textarea(
                attrs={
                    "placeholder" : "Tulis pertanyaan atau ceritakan pengalaman terkait dengan perawatan tanaman",
                    "rows" : 8
                }
            )
        }

class CommentForm(ModelForm):
    class Meta:
        model = Comment

        fields = [
            "comment_body",
        ]

        widgets = {
            "comment_body" : Textarea(
                attrs={
                    "placeholder" : "Tulis komentar",
                }
            )
        }