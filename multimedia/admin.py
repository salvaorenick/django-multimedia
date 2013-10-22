from django.contrib import admin, messages
from models import Video, Audio
from forms import VideoAdminForm, AudioAdminForm


class MediaAdmin(admin.ModelAdmin):
    list_display = ('title', 'encoding', 'encoded', 'uploaded', 'created', 'modified')
    prepopulated_fields = {'slug': ('title',)}
    list_filter = ('encoded', 'uploaded', 'encoding',)

    def save_model(self, request, obj, form, change):
        if not change:
            obj.owner = request.user
        obj.save()
        if not obj.encoded:
            messages.success(request, "Your file is being encoded and uploaded.  An email notification will be sent when complete.")

    def encode_again(self, request, queryset):
        for media in queryset:
            media.encoded = False
            media.save()
        if len(queryset) == 1:
            message_bit = "Your file is"
        else:
            message_bit = "Your files are"

        messages.success(request, "%s being encoded and uploaded.  An email notification will be sent when complete." % message_bit)

    encode_again.short_description = "Re-encode and upload media"
    actions = [encode_again]


class VideoAdmin(MediaAdmin):
    form = VideoAdminForm
    list_display = ('title', 'encoding', 'encoded', 'uploaded', 'created', 'modified', 'admin_thumbnail',)

    class Meta:
        model = Video


class AudioAdmin(MediaAdmin):
    form = AudioAdminForm

    class Meta:
        model = Audio

admin.site.register(Video, VideoAdmin)
admin.site.register(Audio, AudioAdmin)
