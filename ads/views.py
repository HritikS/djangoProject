from operator import itemgetter

from django.contrib.humanize.templatetags.humanize import naturaltime
from django.db import IntegrityError
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from .forms import CreateForm, CommentForm
from .owner import *
from .models import *


class AdListView(OwnerListView):
    model = Ad
    template_name = 'ads/ad_list.html'

    def get(self, request):
        search = request.GET.get('search', False)
        ads = Ad.objects.all() if not search else Ad.objects.filter(Q(title__icontains=search) | Q(text__icontains=search)).select_related()

        for ad in ads:
            ad.natural_updated = naturaltime(ad.updated_at)

        print(ads)
        return render(request, self.template_name,
                      {'ad_list': ads,
                        'favourites': map(itemgetter('id'), request.user.fav_set.values('id')) if request.user.is_authenticated else []})


class AdDetailView(OwnerDetailView):
    model = Ad

    def get(self, request, pk):
        ad = get_object_or_404(Ad, id=pk)
        return render(request, 'ads/ad_detail.html', {'ad': ad, 'comments': ad.comment_set.order_by('-updated_at'), 'comment_form': CommentForm()})


class AdCreateView(LoginRequiredMixin, View):
    template_name = 'ads/ad_form.html'
    success_url = reverse_lazy('ads:all')

    def get(self, request):
        return render(request, self.template_name, {'form': CreateForm()})

    def post(self, request):
        form = CreateForm(request.POST, request.FILES or None)

        if not form.is_valid():
            return render(request, self.template_name, {'form': form})

        ad = form.save(commit=False)
        ad.owner = self.request.user
        ad.save()
        return redirect(self.success_url)


class AdUpdateView(LoginRequiredMixin, View):
    template_name = 'ads/ad_form.html'
    success_url = reverse_lazy('ads:all')

    def get(self, request, pk):
        return render(request, self.template_name, {'form': CreateForm(instance=get_object_or_404(Ad, id=pk, owner=self.request.user))})

    def post(self, request, pk):
        form = CreateForm(request.POST, request.FILES or None, instance=get_object_or_404(Ad, id=pk, owner=self.request.user))

        if not form.is_valid():
            return render(request, self.template_name, {'form': form})

        _ = form.save()
        return redirect(self.success_url)


class AdDeleteView(OwnerDeleteView):
    model = Ad


def stream_file(request, pk):
    ad = get_object_or_404(Ad, id=pk)
    response = HttpResponse()
    response['Content-Type'] = ad.content_type
    response['Content-Length'] = len(ad.picture)
    response.write(ad.picture)
    return response


class CommentCreateView(LoginRequiredMixin, View):
    def post(self, request, pk):
        Comment(text=request.POST['comment'], ad=get_object_or_404(Ad, id=pk), owner=request.user).save()
        return redirect(reverse('ads:ad_detail', args=[pk]))


class CommentDeleteView(OwnerDeleteView):
    model = Comment
    template_name = 'ads/comment_delete.html'

    def get_success_url(self):
        return reverse('ads:ad_detail', args=[self.object.ad.id])


@method_decorator(csrf_exempt, name='dispatch')
class AddFavoriteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        try:
            Fav(ad=get_object_or_404(Ad, id=pk), user=request.user).save()
        except IntegrityError:
            pass
        return HttpResponse()


@method_decorator(csrf_exempt, name='dispatch')
class DeleteFavoriteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        try:
            _ = Fav.objects.get(ad=get_object_or_404(Ad, id=pk), user=request.user).delete()
        except Fav.DoesNotExist:
            pass
        return HttpResponse()
