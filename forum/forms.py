from django.forms import ModelForm, TextInput, Textarea
from forum.models import Post

class PostForum(ModelForm):
    class Meta:
        model = Post
        
        fields = [
            "post_title",
            "post_body",
        ]

        labels = {
            "post_title" : "Judul Post",
            "post_body" : "Isi Post"
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