# Tâche 10 : App Links (Claim / Adopt / Fork)

**Durée estimée** : 4h
**Phase** : 3 — Liens
**Statut** : [ ] À faire
**Dépend de** : 08-app-characters, 04-app-federation

---

## Objectif

Implémenter le système de liens narratifs entre personnages : les modèles `LinkRequest`, `CharacterLink` et `SharedSequence`, le service `CharacterLinkService` (Claim/Adopt/Fork avec `select_for_update`), les vues HTMX pour envoyer/accepter/refuser une demande et co-écrire une séquence, ainsi que l'envoi des activités ActivityPub `Offer`/`Accept`/`Reject` vers les instances distantes.

## User Stories Couvertes

- Domaine 6 — "Être notifié qu'un PNJ intéresse quelqu'un"
- Domaine 6 — "Accepter ou refuser une demande de lien"
- Domaine 6 — "Envoyer une demande d'Adopt sur un PNJ"
- Domaine 6 — "Co-écrire une Séquence Partagée"

## Prérequis

- Tâche 08 complétée (`Character`, `CharacterAppearance` existent)
- Tâche 04 complétée (`deliver_activity`, `FederatedServer`, HTTP Signatures disponibles)

## Fichiers à Créer / Modifier

```
apps/characters/
├── models.py          # Ajouter LinkRequest, CharacterLink, SharedSequence
├── services.py        # CharacterLinkService (Claim/Adopt/Fork) ← CRITIQUE
├── views.py           # Vues HTMX : envoyer, accepter, refuser, séquence
├── urls.py            # Routes links
├── forms.py           # LinkRequestForm, SharedSequenceForm
├── admin.py           # Admin LinkRequest, CharacterLink, SharedSequence
└── activitypub.py     # Sérialisation Offer / Accept / Reject

templates/characters/
├── _link_request_button.html   # Bouton Adopter/Réclamer/Dériver
├── _link_request_modal.html    # Modal HTMX d'envoi de demande
├── _link_request_card.html     # Carte demande reçue (notification)
├── link_request_list.html      # Liste des demandes reçues
└── shared_sequence_edit.html   # Espace co-écriture séquence

tests/contracts/
├── test_claim.py
├── test_adopt.py
└── test_fork.py
```

## Étapes

### 1. Ajouter les modèles dans apps/characters/models.py

Les trois modèles s'ajoutent dans le même fichier que `Character`. Les énumérations sont définies en tête de bloc.

```python
# --- Enumerations ---

class LinkType(models.TextChoices):
    CLAIM = 'CLAIM', 'Claim'
    ADOPT = 'ADOPT', 'Adopt'
    FORK  = 'FORK',  'Fork'


class LinkRequestStatus(models.TextChoices):
    PENDING   = 'PENDING',   'En attente'
    ACCEPTED  = 'ACCEPTED',  'Acceptée'
    REJECTED  = 'REJECTED',  'Refusée'
    CANCELLED = 'CANCELLED', 'Annulée'


# --- LinkRequest ---

class LinkRequest(BaseModel):
    """
    Demande de lien entre personnages — objet ActivityPub de type Offer.

    Contraintes DB importantes :
    - CLAIM : proposed_character obligatoire (CHECK en migration).
    - Un seul PENDING par (target_character, requester) à la fois.
    """

    link_type = models.CharField(max_length=20, choices=LinkType.choices)

    requester = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='link_requests_sent'
    )

    # PNJ visé
    target_character = models.ForeignKey(
        'Character',
        on_delete=models.CASCADE,
        related_name='link_requests_as_target'
    )

    # PJ existant désigné par le demandeur (Claim uniquement)
    proposed_character = models.ForeignKey(
        'Character',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='link_requests_as_proposed'
    )

    # Fork : type de relation narratif ("frère jumeau", "successeur"…)
    relationship = models.CharField(max_length=100, blank=True)

    # Textes libres
    message          = models.TextField(help_text="Proposition narrative du demandeur")
    response_message = models.TextField(blank=True, help_text="Réponse du créateur")

    status     = models.CharField(
        max_length=20,
        choices=LinkRequestStatus.choices,
        default=LinkRequestStatus.PENDING
    )
    resolved_at = models.DateTimeField(null=True, blank=True)

    # ActivityPub (Offer reçu d'une instance distante)
    ap_id = models.URLField(unique=True, null=True, blank=True)

    class Meta:
        db_table = 'characters_linkrequest'
        indexes = [
            models.Index(fields=['status', 'target_character']),
            models.Index(fields=['requester']),
            models.Index(fields=['link_type']),
        ]

    def __str__(self) -> str:
        return f"{self.link_type} — {self.requester} → {self.target_character}"

    def get_absolute_url(self) -> str:
        return reverse('characters:link_request_detail', kwargs={'pk': self.pk})

    def is_pending(self) -> bool:
        return self.status == LinkRequestStatus.PENDING

    def can_be_resolved_by(self, user) -> bool:
        """Seul le créateur du PNJ cible peut accepter/refuser."""
        return self.target_character.creator_id == user.pk and self.is_pending()


# --- CharacterLink ---

class CharacterLink(BaseModel):
    """
    Lien établi entre deux personnages (après acceptation).

    source → PJ du demandeur (ou nouveau PJ créé pour Fork).
    target → PNJ d'origine.
    """

    link_type = models.CharField(max_length=20, choices=LinkType.choices)

    source = models.ForeignKey(
        'Character',
        on_delete=models.CASCADE,
        related_name='links_as_source'
    )
    target = models.ForeignKey(
        'Character',
        on_delete=models.CASCADE,
        related_name='links_as_target'
    )

    link_request = models.OneToOneField(
        'LinkRequest',
        on_delete=models.SET_NULL,
        null=True, blank=True
    )

    description = models.TextField(blank=True)

    class Meta:
        db_table = 'characters_characterlink'
        unique_together = [['source', 'target', 'link_type']]
        indexes = [
            models.Index(fields=['source']),
            models.Index(fields=['target']),
            models.Index(fields=['link_type']),
        ]

    def __str__(self) -> str:
        return f"{self.link_type} : {self.source} ← {self.target}"


# --- SharedSequence ---

class SharedSequence(BaseModel):
    """
    Séquence narrative co-écrite après acceptation d'un Claim/Adopt/Fork.

    MVP : obligatoire — un CharacterLink sans SharedSequence est invalide.
    La séquence justifie narrativement le lien entre les deux personnages.
    """

    character_link = models.OneToOneField(
        'CharacterLink',
        on_delete=models.CASCADE,
        related_name='shared_sequence'
    )

    title   = models.CharField(max_length=255)
    content = models.TextField(help_text="Markdown — la scène narrative co-écrite")
    content_html = models.TextField(blank=True, help_text="Cache HTML rendu")

    initiator = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='initiated_sequences',
        help_text="Joueur qui a proposé le lien"
    )
    acceptor = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='accepted_sequences',
        help_text="Joueur qui a accepté le lien"
    )

    initiator_game = models.ForeignKey(
        'games.Game',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='shared_sequences_as_initiator'
    )
    acceptor_game = models.ForeignKey(
        'games.Game',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='shared_sequences_as_acceptor'
    )

    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'characters_sharedsequence'
        indexes = [
            models.Index(fields=['character_link']),
            models.Index(fields=['initiator']),
            models.Index(fields=['acceptor']),
            models.Index(fields=['is_published', 'published_at']),
        ]

    def __str__(self) -> str:
        return self.title

    def get_absolute_url(self) -> str:
        return reverse('characters:shared_sequence_detail', kwargs={'pk': self.pk})

    def publish(self) -> None:
        """Publie la séquence et met à jour published_at."""
        self.is_published = True
        self.published_at = timezone.now()
        self.save(update_fields=['is_published', 'published_at', 'updated_at'])
```

### 2. Créer apps/characters/services.py

Ce fichier est le coeur métier de l'application. Toutes les mutations d'état sont encapsulées ici. Les vues ne touchent jamais les modèles directement.

Points clés du service :

- `select_for_update()` sur `LinkRequest` et `Character` pour éviter les race conditions (deux demandes simultanées sur le même PNJ).
- Chaque méthode publique est `@transaction.atomic`.
- L'envoi ActivityPub (`deliver_activity`) est appelé **uniquement si le personnage cible est distant** (`not target.local`).
- La création du `SharedSequence` est déclenchée par une méthode séparée, après que les deux joueurs ont confirmé leur intention de co-écrire.

```python
"""
Service pour la gestion des liens narratifs entre personnages.

Logique : Claim / Adopt / Fork.
"""
from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from .models import (
    Character, CharacterStatus,
    CharacterLink, LinkRequest, LinkRequestStatus, LinkType,
    SharedSequence,
)


class LinkRequestError(Exception):
    """Erreur métier lors d'une opération sur un lien."""


class CharacterLinkService:
    """Service de gestion des liens Claim / Adopt / Fork."""

    # --- Envoi de demande ---

    @transaction.atomic
    def send_request(
        self,
        *,
        link_type: str,
        requester,
        target_character: Character,
        message: str,
        proposed_character: Character | None = None,
        relationship: str = '',
    ) -> LinkRequest:
        """
        Crée et enregistre une demande de lien.

        Validations :
        - Le PNJ cible doit être au statut NPC.
        - Pas de demande PENDING déjà ouverte par ce demandeur sur ce PNJ.
        - Claim : proposed_character obligatoire.
        """
        # Verrouillage anti-race condition
        target = (
            Character.objects
            .select_for_update()
            .get(pk=target_character.pk)
        )

        if target.status != CharacterStatus.NPC:
            raise LinkRequestError(
                f"Le personnage '{target.name}' n'est plus disponible (statut : {target.status})."
            )

        already_pending = LinkRequest.objects.filter(
            requester=requester,
            target_character=target,
            status=LinkRequestStatus.PENDING,
        ).exists()
        if already_pending:
            raise LinkRequestError("Une demande est déjà en attente pour ce personnage.")

        if link_type == LinkType.CLAIM and proposed_character is None:
            raise LinkRequestError("Un Claim nécessite un proposed_character.")

        link_request = LinkRequest.objects.create(
            link_type=link_type,
            requester=requester,
            target_character=target,
            proposed_character=proposed_character,
            relationship=relationship,
            message=message,
        )

        # Notification locale au créateur du PNJ
        self._notify_creator(link_request)

        # Activité AP si le personnage est distant
        if not target.local:
            self._deliver_offer(link_request)

        return link_request

    # --- Acceptation ---

    @transaction.atomic
    def accept(
        self,
        *,
        link_request: LinkRequest,
        resolver,
        response_message: str = '',
    ) -> CharacterLink:
        """
        Accepte une demande de lien.

        Effets :
        - Crée le CharacterLink.
        - Met à jour le statut du PNJ (CLAIMED / ADOPTED / FORKED).
        - Pour Fork : crée un nouveau Character PJ pour le demandeur.
        - Clôture la LinkRequest.
        - Notifie le demandeur.
        - Envoie Accept AP si nécessaire.

        Retourne le CharacterLink créé.
        """
        lr = (
            LinkRequest.objects
            .select_for_update()
            .select_related('target_character', 'proposed_character', 'requester')
            .get(pk=link_request.pk)
        )

        if not lr.can_be_resolved_by(resolver):
            raise LinkRequestError("Vous n'êtes pas autorisé à accepter cette demande.")

        # Choisir la méthode selon le type
        if lr.link_type == LinkType.CLAIM:
            character_link = self._accept_claim(lr)
        elif lr.link_type == LinkType.ADOPT:
            character_link = self._accept_adopt(lr)
        elif lr.link_type == LinkType.FORK:
            character_link = self._accept_fork(lr)
        else:
            raise LinkRequestError(f"Type de lien inconnu : {lr.link_type}")

        # Clôturer la demande
        lr.status = LinkRequestStatus.ACCEPTED
        lr.response_message = response_message
        lr.resolved_at = timezone.now()
        lr.save(update_fields=['status', 'response_message', 'resolved_at', 'updated_at'])

        self._notify_requester_accepted(lr)

        if not lr.requester.local:
            self._deliver_accept(lr)

        return character_link

    def _accept_claim(self, lr: LinkRequest) -> CharacterLink:
        """Claim : le PNJ est remplacé par le PJ existant (proposed_character)."""
        target = lr.target_character
        target.status = CharacterStatus.CLAIMED
        target.save(update_fields=['status', 'updated_at'])

        return CharacterLink.objects.create(
            link_type=LinkType.CLAIM,
            source=lr.proposed_character,
            target=target,
            link_request=lr,
        )

    def _accept_adopt(self, lr: LinkRequest) -> CharacterLink:
        """Adopt : le PNJ est transféré au demandeur et devient son PJ."""
        target = lr.target_character
        target.status = CharacterStatus.ADOPTED
        target.owner = lr.requester
        target.save(update_fields=['status', 'owner', 'updated_at'])

        return CharacterLink.objects.create(
            link_type=LinkType.ADOPT,
            source=target,  # Le PNJ devient le PJ source
            target=target,
            link_request=lr,
        )

    def _accept_fork(self, lr: LinkRequest) -> CharacterLink:
        """Fork : un nouveau PJ est créé pour le demandeur, le PNJ reste intact."""
        target = lr.target_character

        # Créer le nouveau PJ dérivé
        new_pc = Character.objects.create(
            name=target.name,
            description=target.description,
            status=CharacterStatus.PC,
            owner=lr.requester,
            creator=lr.requester,
            origin_game=target.origin_game,
            parent=target,
        )

        return CharacterLink.objects.create(
            link_type=LinkType.FORK,
            source=new_pc,
            target=target,
            link_request=lr,
            description=lr.relationship,
        )

    # --- Refus ---

    @transaction.atomic
    def reject(
        self,
        *,
        link_request: LinkRequest,
        resolver,
        response_message: str = '',
    ) -> LinkRequest:
        """
        Refuse une demande de lien.

        Le PNJ reste disponible (statut NPC inchangé).
        """
        lr = (
            LinkRequest.objects
            .select_for_update()
            .get(pk=link_request.pk)
        )

        if not lr.can_be_resolved_by(resolver):
            raise LinkRequestError("Vous n'êtes pas autorisé à refuser cette demande.")

        lr.status = LinkRequestStatus.REJECTED
        lr.response_message = response_message
        lr.resolved_at = timezone.now()
        lr.save(update_fields=['status', 'response_message', 'resolved_at', 'updated_at'])

        self._notify_requester_rejected(lr)

        if not lr.requester.local:
            self._deliver_reject(lr)

        return lr

    # --- SharedSequence ---

    @transaction.atomic
    def create_shared_sequence(
        self,
        *,
        character_link: CharacterLink,
        title: str,
        content: str,
    ) -> SharedSequence:
        """
        Crée la SharedSequence associée à un CharacterLink.

        Appelé après acceptation, quand les deux joueurs ont fourni leur texte.
        La séquence est d'abord un brouillon (is_published=False).
        """
        lr = character_link.link_request

        sequence = SharedSequence.objects.create(
            character_link=character_link,
            title=title,
            content=content,
            initiator=lr.requester,
            acceptor=lr.target_character.creator,
            initiator_game=lr.requester.games.order_by('-created_at').first(),
            acceptor_game=lr.target_character.origin_game,
        )

        return sequence

    # --- Notifications (stubs à connecter aux signaux ou Celery) ---

    def _notify_creator(self, lr: LinkRequest) -> None:
        """Notifie le créateur du PNJ qu'une demande a été reçue."""
        # TODO : créer une Notification dans la table dédiée
        pass

    def _notify_requester_accepted(self, lr: LinkRequest) -> None:
        """Notifie le demandeur que sa demande a été acceptée."""
        pass

    def _notify_requester_rejected(self, lr: LinkRequest) -> None:
        """Notifie le demandeur que sa demande a été refusée."""
        pass

    # --- Livraison ActivityPub (uniquement si remote) ---

    def _deliver_offer(self, lr: LinkRequest) -> None:
        """Envoie une activité Offer vers l'instance du PNJ cible."""
        from apps.federation.activities import build_offer_activity
        from apps.federation.tasks import deliver_activity

        activity = build_offer_activity(lr)
        inbox = lr.target_character.inbox
        if inbox:
            deliver_activity(activity=activity, inbox_url=inbox, sender=lr.requester)

    def _deliver_accept(self, lr: LinkRequest) -> None:
        """Envoie une activité Accept vers l'instance du demandeur."""
        from apps.federation.activities import build_accept_activity
        from apps.federation.tasks import deliver_activity

        activity = build_accept_activity(lr)
        inbox = lr.requester.inbox
        if inbox:
            deliver_activity(
                activity=activity,
                inbox_url=inbox,
                sender=lr.target_character.creator,
            )

    def _deliver_reject(self, lr: LinkRequest) -> None:
        """Envoie une activité Reject vers l'instance du demandeur."""
        from apps.federation.activities import build_reject_activity
        from apps.federation.tasks import deliver_activity

        activity = build_reject_activity(lr)
        inbox = lr.requester.inbox
        if inbox:
            deliver_activity(
                activity=activity,
                inbox_url=inbox,
                sender=lr.target_character.creator,
            )
```

### 3. Créer apps/characters/forms.py (section liens)

```python
"""Formulaires pour les demandes de lien et la séquence partagée."""
from django import forms

from .models import LinkRequest, LinkType, SharedSequence


class LinkRequestForm(forms.ModelForm):
    """Formulaire d'envoi d'une demande de lien."""

    class Meta:
        model = LinkRequest
        fields = ['link_type', 'proposed_character', 'relationship', 'message']
        widgets = {
            'message': forms.Textarea(attrs={
                'rows': 6,
                'placeholder': "Décrivez votre proposition narrative..."
            }),
            'relationship': forms.TextInput(attrs={
                'placeholder': "ex : frère jumeau, successeur, clone..."
            }),
        }

    def __init__(self, *args, requester=None, link_type=None, **kwargs):
        super().__init__(*args, **kwargs)
        # Restreindre proposed_character aux PJs du demandeur (Claim uniquement)
        if requester:
            self.fields['proposed_character'].queryset = (
                requester.characters.filter(status='PC')
            )
        # Pré-sélectionner le type si fourni via l'URL
        if link_type:
            self.fields['link_type'].initial = link_type
        # Masquer relationship si non Fork
        if link_type != LinkType.FORK:
            self.fields['relationship'].required = False

    def clean(self):
        cleaned = super().clean()
        link_type = cleaned.get('link_type')
        proposed = cleaned.get('proposed_character')

        if link_type == LinkType.CLAIM and not proposed:
            self.add_error(
                'proposed_character',
                "Un Claim nécessite de désigner votre PJ existant."
            )
        return cleaned


class LinkResponseForm(forms.Form):
    """Formulaire de réponse (acceptation ou refus)."""

    response_message = forms.CharField(
        label="Message de réponse",
        widget=forms.Textarea(attrs={'rows': 4}),
        required=False,
    )


class SharedSequenceForm(forms.ModelForm):
    """Formulaire de co-écriture de la séquence partagée."""

    class Meta:
        model = SharedSequence
        fields = ['title', 'content']
        widgets = {
            'content': forms.Textarea(attrs={
                'rows': 15,
                'placeholder': "Rédigez la scène narrative en Markdown..."
            }),
        }
```

### 4. Créer apps/characters/views.py (section liens)

Les vues sont organisées en deux blocs : la gestion des demandes, puis l'espace de co-écriture.

```python
"""Vues HTMX pour les liens narratifs."""
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods
from django.views.generic import ListView

from .forms import LinkRequestForm, LinkResponseForm, SharedSequenceForm
from .models import Character, CharacterLink, LinkRequest, LinkRequestStatus, SharedSequence
from .services import CharacterLinkService, LinkRequestError


# --- Envoi d'une demande ---

@login_required
@require_http_methods(["GET", "POST"])
def link_request_send(request, character_slug):
    """
    GET  → Retourne le modal HTMX avec le formulaire.
    POST → Crée la demande et retourne le bouton mis à jour.
    """
    character = get_object_or_404(Character, slug=character_slug)
    link_type = request.GET.get('type') or request.POST.get('link_type')

    form = LinkRequestForm(
        request.POST or None,
        requester=request.user,
        link_type=link_type,
    )

    if request.method == 'POST' and form.is_valid():
        service = CharacterLinkService()
        try:
            service.send_request(
                link_type=form.cleaned_data['link_type'],
                requester=request.user,
                target_character=character,
                message=form.cleaned_data['message'],
                proposed_character=form.cleaned_data.get('proposed_character'),
                relationship=form.cleaned_data.get('relationship', ''),
            )
            # HTMX : retourner le bouton désactivé
            return render(request, 'characters/_link_request_button.html', {
                'character': character,
                'pending': True,
            })
        except LinkRequestError as e:
            form.add_error(None, str(e))

    return render(request, 'characters/_link_request_modal.html', {
        'character': character,
        'form': form,
        'link_type': link_type,
    })


# --- Liste des demandes reçues ---

class LinkRequestListView(LoginRequiredMixin, ListView):
    """Demandes de lien reçues sur les PNJ du joueur connecté."""

    model = LinkRequest
    template_name = 'characters/link_request_list.html'
    context_object_name = 'link_requests'
    paginate_by = 20

    def get_queryset(self):
        return (
            LinkRequest.objects
            .filter(
                target_character__creator=self.request.user,
                status=LinkRequestStatus.PENDING,
            )
            .select_related(
                'requester',
                'target_character',
                'proposed_character',
            )
            .order_by('-created_at')
        )


# --- Acceptation ---

@login_required
@require_http_methods(["POST"])
def link_request_accept(request, pk):
    """Accepte une demande de lien. Retourne la carte mise à jour (HTMX)."""
    link_request = get_object_or_404(LinkRequest, pk=pk)
    form = LinkResponseForm(request.POST)

    if form.is_valid():
        service = CharacterLinkService()
        try:
            service.accept(
                link_request=link_request,
                resolver=request.user,
                response_message=form.cleaned_data.get('response_message', ''),
            )
            return render(request, 'characters/_link_request_card.html', {
                'link_request': link_request,
                'accepted': True,
            })
        except LinkRequestError as e:
            return HttpResponse(str(e), status=403)

    return HttpResponse("Formulaire invalide.", status=400)


# --- Refus ---

@login_required
@require_http_methods(["POST"])
def link_request_reject(request, pk):
    """Refuse une demande de lien. Retourne la carte mise à jour (HTMX)."""
    link_request = get_object_or_404(LinkRequest, pk=pk)
    form = LinkResponseForm(request.POST)

    if form.is_valid():
        service = CharacterLinkService()
        try:
            service.reject(
                link_request=link_request,
                resolver=request.user,
                response_message=form.cleaned_data.get('response_message', ''),
            )
            return render(request, 'characters/_link_request_card.html', {
                'link_request': link_request,
                'rejected': True,
            })
        except LinkRequestError as e:
            return HttpResponse(str(e), status=403)

    return HttpResponse("Formulaire invalide.", status=400)


# --- Co-écriture SharedSequence ---

@login_required
def shared_sequence_edit(request, character_link_pk):
    """Espace de co-écriture de la Séquence Partagée."""
    character_link = get_object_or_404(
        CharacterLink.objects.select_related(
            'link_request__requester',
            'link_request__target_character__creator',
            'source',
            'target',
        ),
        pk=character_link_pk,
    )

    lr = character_link.link_request
    is_participant = request.user in (lr.requester, lr.target_character.creator)
    if not is_participant:
        return HttpResponse(status=403)

    # Récupérer ou initialiser la séquence
    try:
        sequence = character_link.shared_sequence
    except SharedSequence.DoesNotExist:
        sequence = None

    form = SharedSequenceForm(request.POST or None, instance=sequence)

    if request.method == 'POST' and form.is_valid():
        service = CharacterLinkService()
        if sequence is None:
            sequence = service.create_shared_sequence(
                character_link=character_link,
                title=form.cleaned_data['title'],
                content=form.cleaned_data['content'],
            )
        else:
            form.save()

        if request.POST.get('publish'):
            sequence.publish()
            return redirect(sequence.get_absolute_url())

    return render(request, 'characters/shared_sequence_edit.html', {
        'character_link': character_link,
        'sequence': sequence,
        'form': form,
    })
```

### 5. Créer apps/characters/urls.py (section liens)

```python
"""URLs pour les liens narratifs."""
from django.urls import path

from . import views

app_name = 'characters'

urlpatterns = [
    # ... (routes existantes de 08-app-characters) ...

    # Liens
    path(
        '<slug:character_slug>/link/send/',
        views.link_request_send,
        name='link_request_send',
    ),
    path(
        'links/requests/',
        views.LinkRequestListView.as_view(),
        name='link_request_list',
    ),
    path(
        'links/requests/<uuid:pk>/accept/',
        views.link_request_accept,
        name='link_request_accept',
    ),
    path(
        'links/requests/<uuid:pk>/reject/',
        views.link_request_reject,
        name='link_request_reject',
    ),
    path(
        'links/<uuid:character_link_pk>/sequence/',
        views.shared_sequence_edit,
        name='shared_sequence_edit',
    ),
]
```

### 6. Créer les templates HTMX

#### templates/characters/_link_request_button.html

```html
{% if user.is_authenticated and character.status == 'NPC' and character.creator != user %}
    {% if pending %}
        <button disabled class="btn btn-secondary opacity-60 cursor-not-allowed">
            Demande en cours…
        </button>
    {% else %}
        <div class="flex gap-2">
            <button
                hx-get="{% url 'characters:link_request_send' character.slug %}?type=ADOPT"
                hx-target="#modal-container"
                hx-swap="innerHTML"
                class="btn btn-primary">
                Adopter
            </button>
            <button
                hx-get="{% url 'characters:link_request_send' character.slug %}?type=CLAIM"
                hx-target="#modal-container"
                hx-swap="innerHTML"
                class="btn btn-outline">
                Réclamer
            </button>
            <button
                hx-get="{% url 'characters:link_request_send' character.slug %}?type=FORK"
                hx-target="#modal-container"
                hx-swap="innerHTML"
                class="btn btn-ghost">
                Dériver
            </button>
        </div>
    {% endif %}
{% endif %}
```

#### templates/characters/_link_request_modal.html

```html
<div id="link-request-modal" class="modal modal-open">
    <div class="modal-box">
        <h3 class="font-bold text-lg mb-4">
            {% if link_type == 'ADOPT' %}Adopter{% elif link_type == 'CLAIM' %}Réclamer{% else %}Dériver{% endif %}
            {{ character.name }}
        </h3>

        <form
            hx-post="{% url 'characters:link_request_send' character.slug %}"
            hx-target="#link-request-button-{{ character.pk }}"
            hx-swap="outerHTML">
            {% csrf_token %}
            {{ form.as_p }}
            <div class="modal-action">
                <button type="button" onclick="document.getElementById('modal-container').innerHTML=''"
                        class="btn btn-ghost">Annuler</button>
                <button type="submit" class="btn btn-primary">Envoyer la demande</button>
            </div>
        </form>
    </div>
</div>
```

#### templates/characters/_link_request_card.html

```html
<div class="card bg-base-100 shadow-sm border {% if accepted %}border-success{% elif rejected %}border-error{% else %}border-base-300{% endif %}">
    <div class="card-body p-4">
        <div class="flex items-start justify-between">
            <div>
                <span class="badge badge-outline mb-1">{{ link_request.get_link_type_display }}</span>
                <h4 class="font-semibold">{{ link_request.requester.display_name }}</h4>
                <p class="text-sm text-base-content/70">veut {{ link_request.get_link_type_display|lower }} <strong>{{ link_request.target_character.name }}</strong></p>
            </div>
            <span class="text-xs text-base-content/50">{{ link_request.created_at|timesince }}</span>
        </div>
        <p class="text-sm mt-2 italic">{{ link_request.message }}</p>

        {% if not accepted and not rejected %}
        <div class="card-actions justify-end mt-3 gap-2">
            <form hx-post="{% url 'characters:link_request_reject' link_request.pk %}"
                  hx-target="closest .card" hx-swap="outerHTML">
                {% csrf_token %}
                <input type="hidden" name="response_message" value="">
                <button type="submit" class="btn btn-sm btn-ghost">Refuser</button>
            </form>
            <form hx-post="{% url 'characters:link_request_accept' link_request.pk %}"
                  hx-target="closest .card" hx-swap="outerHTML">
                {% csrf_token %}
                <input type="hidden" name="response_message" value="">
                <button type="submit" class="btn btn-sm btn-success">Accepter</button>
            </form>
        </div>
        {% elif accepted %}
        <p class="text-success text-sm mt-2">Demande acceptée. <a href="#" class="link">Co-écrire la séquence partagée</a></p>
        {% elif rejected %}
        <p class="text-error text-sm mt-2">Demande refusée.</p>
        {% endif %}
    </div>
</div>
```

### 7. Créer apps/characters/admin.py (section liens)

```python
"""Admin pour LinkRequest, CharacterLink, SharedSequence."""
from django.contrib import admin

from .models import CharacterLink, LinkRequest, SharedSequence


@admin.register(LinkRequest)
class LinkRequestAdmin(admin.ModelAdmin):
    list_display  = ['link_type', 'requester', 'target_character', 'status', 'created_at']
    list_filter   = ['link_type', 'status']
    search_fields = ['requester__username', 'target_character__name', 'message']
    readonly_fields = ['created_at', 'updated_at', 'resolved_at', 'ap_id']
    ordering = ['-created_at']

    fieldsets = (
        (None, {
            'fields': ('link_type', 'status', 'requester', 'target_character', 'proposed_character')
        }),
        ('Messages', {
            'fields': ('message', 'response_message', 'relationship')
        }),
        ('Résolution', {
            'fields': ('resolved_at',),
            'classes': ('collapse',),
        }),
        ('Fédération', {
            'fields': ('ap_id',),
            'classes': ('collapse',),
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )


@admin.register(CharacterLink)
class CharacterLinkAdmin(admin.ModelAdmin):
    list_display  = ['link_type', 'source', 'target', 'created_at']
    list_filter   = ['link_type']
    search_fields = ['source__name', 'target__name']
    readonly_fields = ['created_at']


@admin.register(SharedSequence)
class SharedSequenceAdmin(admin.ModelAdmin):
    list_display  = ['title', 'initiator', 'acceptor', 'is_published', 'published_at']
    list_filter   = ['is_published']
    search_fields = ['title', 'initiator__username', 'acceptor__username']
    readonly_fields = ['content_html', 'created_at', 'updated_at', 'published_at']
    ordering = ['-created_at']
```

### 8. Sérialisation ActivityPub dans apps/characters/activitypub.py

Ce fichier ajoute les fonctions `build_offer_activity`, `build_accept_activity` et `build_reject_activity`. Elles produisent des dicts conformes à la spec ActivityPub et sont consommées par `apps/federation/tasks.deliver_activity`.

Points clés :
- `Offer.object` est un objet JSON décrivant le lien proposé (type, target, proposed_character).
- `Accept.object` référence l'`ap_id` de l'Offer d'origine.
- `Reject.object` idem.

```python
"""
Sérialisation ActivityPub pour les liens narratifs.

Types utilisés :
  - Offer  : demande Claim/Adopt/Fork
  - Accept : réponse positive
  - Reject : réponse négative
"""
from __future__ import annotations

from django.conf import settings

from .models import LinkRequest, LinkType


def build_offer_activity(lr: LinkRequest) -> dict:
    """Construit l'activité Offer pour une demande de lien."""
    actor_ap_id = lr.requester.get_ap_id()
    target_ap_id = lr.target_character.get_ap_id()

    offer_object: dict = {
        "type": "Offer",
        "linkType": lr.link_type,
        "target": target_ap_id,
        "content": lr.message,
    }

    if lr.link_type == LinkType.CLAIM and lr.proposed_character:
        offer_object["proposed"] = lr.proposed_character.get_ap_id()

    if lr.link_type == LinkType.FORK and lr.relationship:
        offer_object["relationship"] = lr.relationship

    return {
        "@context": "https://www.w3.org/ns/activitystreams",
        "type": "Offer",
        "id": f"https://{settings.DOMAIN}/characters/links/{lr.pk}/offer",
        "actor": actor_ap_id,
        "to": [target_ap_id],
        "object": offer_object,
    }


def build_accept_activity(lr: LinkRequest) -> dict:
    """Construit l'activité Accept suite à une acceptation."""
    actor_ap_id = lr.target_character.creator.get_ap_id()
    offer_ap_id = (
        lr.ap_id
        or f"https://{settings.DOMAIN}/characters/links/{lr.pk}/offer"
    )

    return {
        "@context": "https://www.w3.org/ns/activitystreams",
        "type": "Accept",
        "id": f"https://{settings.DOMAIN}/characters/links/{lr.pk}/accept",
        "actor": actor_ap_id,
        "to": [lr.requester.get_ap_id()],
        "object": offer_ap_id,
    }


def build_reject_activity(lr: LinkRequest) -> dict:
    """Construit l'activité Reject suite à un refus."""
    actor_ap_id = lr.target_character.creator.get_ap_id()
    offer_ap_id = (
        lr.ap_id
        or f"https://{settings.DOMAIN}/characters/links/{lr.pk}/offer"
    )

    return {
        "@context": "https://www.w3.org/ns/activitystreams",
        "type": "Reject",
        "id": f"https://{settings.DOMAIN}/characters/links/{lr.pk}/reject",
        "actor": actor_ap_id,
        "to": [lr.requester.get_ap_id()],
        "object": offer_ap_id,
    }
```

### 9. Ajouter la migration avec les contraintes CHECK

Après `python manage.py makemigrations characters`, ajouter une migration de données pour les contraintes SQL qui ne sont pas exprimables via l'ORM :

```python
# apps/characters/migrations/0003_link_constraints.py
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('characters', '0002_linkrequest_characterlink_sharedsequence'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            ALTER TABLE characters_linkrequest
            ADD CONSTRAINT check_claim_has_proposed
            CHECK (link_type != 'CLAIM' OR proposed_character_id IS NOT NULL);
            """,
            reverse_sql="""
            ALTER TABLE characters_linkrequest
            DROP CONSTRAINT IF EXISTS check_claim_has_proposed;
            """,
        ),
    ]
```

### 10. Créer les tests de contrat

```python
# tests/contracts/test_adopt.py
import pytest
from apps.characters.models import CharacterStatus, LinkRequestStatus, LinkType
from apps.characters.services import CharacterLinkService, LinkRequestError


@pytest.mark.django_db
class TestAdopt:
    """Tests contrat pour le flux Adopt."""

    def test_send_request_creates_linkrequest(self, npc, player):
        service = CharacterLinkService()
        lr = service.send_request(
            link_type=LinkType.ADOPT,
            requester=player,
            target_character=npc,
            message="Je veux adopter ce personnage.",
        )
        assert lr.status == LinkRequestStatus.PENDING
        assert lr.link_type == LinkType.ADOPT

    def test_send_request_fails_if_not_npc(self, adopted_character, player):
        service = CharacterLinkService()
        with pytest.raises(LinkRequestError, match="disponible"):
            service.send_request(
                link_type=LinkType.ADOPT,
                requester=player,
                target_character=adopted_character,
                message="...",
            )

    def test_accept_adopt_changes_status(self, pending_adopt_request, npc_creator):
        service = CharacterLinkService()
        service.accept(link_request=pending_adopt_request, resolver=npc_creator)
        pending_adopt_request.target_character.refresh_from_db()
        assert pending_adopt_request.target_character.status == CharacterStatus.ADOPTED

    def test_accept_adopt_sets_owner(self, pending_adopt_request, npc_creator, player):
        service = CharacterLinkService()
        service.accept(link_request=pending_adopt_request, resolver=npc_creator)
        pending_adopt_request.target_character.refresh_from_db()
        assert pending_adopt_request.target_character.owner == player

    def test_reject_leaves_npc_available(self, pending_adopt_request, npc_creator):
        service = CharacterLinkService()
        service.reject(link_request=pending_adopt_request, resolver=npc_creator)
        pending_adopt_request.target_character.refresh_from_db()
        assert pending_adopt_request.target_character.status == CharacterStatus.NPC

    def test_non_creator_cannot_accept(self, pending_adopt_request, other_user):
        service = CharacterLinkService()
        with pytest.raises(LinkRequestError, match="autorisé"):
            service.accept(link_request=pending_adopt_request, resolver=other_user)
```

```python
# tests/contracts/test_claim.py
import pytest
from apps.characters.models import CharacterStatus, LinkType
from apps.characters.services import CharacterLinkService, LinkRequestError


@pytest.mark.django_db
class TestClaim:
    """Tests contrat pour le flux Claim."""

    def test_claim_requires_proposed_character(self, npc, player):
        service = CharacterLinkService()
        with pytest.raises(LinkRequestError, match="proposed_character"):
            service.send_request(
                link_type=LinkType.CLAIM,
                requester=player,
                target_character=npc,
                message="Rétcon narratif.",
                proposed_character=None,
            )

    def test_accept_claim_sets_claimed_status(
        self, pending_claim_request, npc_creator
    ):
        service = CharacterLinkService()
        link = service.accept(link_request=pending_claim_request, resolver=npc_creator)
        pending_claim_request.target_character.refresh_from_db()
        assert pending_claim_request.target_character.status == CharacterStatus.CLAIMED

    def test_accept_claim_creates_characterlink(self, pending_claim_request, npc_creator):
        service = CharacterLinkService()
        link = service.accept(link_request=pending_claim_request, resolver=npc_creator)
        assert link.link_type == LinkType.CLAIM
        assert link.source == pending_claim_request.proposed_character
        assert link.target == pending_claim_request.target_character
```

```python
# tests/contracts/test_fork.py
import pytest
from apps.characters.models import CharacterStatus, LinkType
from apps.characters.services import CharacterLinkService


@pytest.mark.django_db
class TestFork:
    """Tests contrat pour le flux Fork."""

    def test_accept_fork_creates_new_pc(self, pending_fork_request, npc_creator, player):
        service = CharacterLinkService()
        link = service.accept(link_request=pending_fork_request, resolver=npc_creator)

        assert link.source.owner == player
        assert link.source.status == CharacterStatus.PC
        assert link.source.parent == pending_fork_request.target_character

    def test_accept_fork_npc_status_unchanged(self, pending_fork_request, npc_creator):
        service = CharacterLinkService()
        service.accept(link_request=pending_fork_request, resolver=npc_creator)
        pending_fork_request.target_character.refresh_from_db()
        assert pending_fork_request.target_character.status == CharacterStatus.NPC
```

## Validation

- [ ] `LinkRequest`, `CharacterLink`, `SharedSequence` importables depuis `apps.characters.models`
- [ ] Migration sans erreur (`python manage.py migrate`)
- [ ] Contrainte CHECK `check_claim_has_proposed` présente en base
- [ ] `CharacterLinkService.send_request` lève `LinkRequestError` si le PNJ n'est pas NPC
- [ ] `CharacterLinkService.accept` change le statut du personnage selon le type de lien
- [ ] `CharacterLinkService.reject` laisse le PNJ au statut NPC
- [ ] Les vues HTMX répondent avec les bons partials (200 ou 403)
- [ ] `build_offer_activity` produit un dict avec `@context` et `type: Offer`
- [ ] Tests `test_adopt.py`, `test_claim.py`, `test_fork.py` passent (`pytest tests/contracts/`)
- [ ] Admin accessible pour les trois modèles

## Notes

- `_accept_adopt` affecte à la fois `source` et `target` au même objet `Character`. Cela peut être ajusté si la logique métier évolue (ex : conserver une trace du PNJ historique distinct du PJ actuel).
- Les méthodes `_notify_*` sont des stubs intentionnels. Elles seront branchées sur un système de notifications (Django signals ou table `Notification`) dans une tâche ultérieure.
- `deliver_activity` peut être synchrone ou asynchrone selon que Celery est configuré. Le service ne fait aucune hypothèse à ce sujet — il délègue à `apps/federation/tasks`.
- La SharedSequence est créée en brouillon (`is_published=False`). La publication nécessite l'action explicite des deux joueurs via le formulaire de co-écriture.
- Pour le flux Fork cross-instance, le nouveau `Character` est créé localement. L'instance distante est notifiée via l'Accept, mais ne crée pas de personnage — c'est une décision de conception (chaque instance gère ses propres acteurs).

## Références

- `docs/models/README.md` — LinkRequest, CharacterLink, SharedSequence
- `docs/flows/claim-adopt-fork.md` — diagrammes des trois flux
- `docs/memory-bank/user-stories.md` — Domaine 6
- `docs/memory-bank/CODEBASE_STRUCTURE.md` — modules critiques
