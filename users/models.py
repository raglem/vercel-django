import uuid
from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.timezone import make_aware, is_naive

class Note(models.Model):
    title = models.CharField(max_length=100)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notes")

    def __str__(self):
        return self.title

class PickupGame(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="owned_games", null=True)
    all_members = models.ManyToManyField("Membership", related_name="pickup_games", blank=True)
    all_players = models.ManyToManyField("PickupPlayer", related_name="invited_games", blank=True)
    assigned_players = models.ManyToManyField("PickupPlayer", related_name="assigned", blank=True)
    unassigned_players = models.ManyToManyField("PickupPlayer", related_name="unassigned_games", blank=True)
    pending_players = models.ManyToManyField("PickupPlayer", related_name="pending_games", blank=True)
    requesting_players = models.ManyToManyField("PickupPlayer", related_name="requested_games", blank=True)
    
    location = models.CharField(max_length=50)
    date = models.DateTimeField()
    join_code = models.CharField(max_length=8, unique=True, blank=True)
    ringers_score = models.PositiveSmallIntegerField(default=0, blank=True, null=True)
    ballers_score = models.PositiveSmallIntegerField(default=0, blank=True, null=True)
    FORMAT_CHOICES = [
        (2, "2v2"),
        (3, "3v3"),
        (4, "4v4"),
        (5, "5v5"),
    ]
    STATUS_CHOICES = [
        (1, "Pending"),
        (2, "Completed"),
        (3, "Canceled"),
    ]
    format = models.PositiveSmallIntegerField(choices=FORMAT_CHOICES)
    status = models.PositiveSmallIntegerField(choices=STATUS_CHOICES, default=1)

    def __str__(self):
        human_readable_date = self.date.strftime('%B %d, %Y at %I:%M %p UTC')
        return f"Game at {self.location} on {human_readable_date}"
    
    def clean(self):
        super().clean()

        all_players = set(self.all_players.all())
        assigned_players = set(self.assigned_players.all())
        unassigned_players = set(self.assigned_players.all())
        pending_players = set(self.pending_players.all())
        requesting_players = set(self.requesting_players.all())
        combined_players = assigned_players | unassigned_players | pending_players | requesting_players

        if(combined_players != all_players):
            raise ValidationError("Assigned, unassigned, pending, and requesting players must sum up to all players")

        if(not assigned_players.issubset(all_players)):
            raise ValidationError("All assigned players must be invited players")
        if(not unassigned_players.issubset(all_players)):
            raise ValidationError("All unassigned players must be invited players") 
        if(not pending_players.issubset(all_players)):
            raise ValidationError("All pending players must be invited players") 
        
        if(assigned_players & unassigned_players):
            raise ValidationError("Assigned and unassigned players cannot overlap")
        if(assigned_players & pending_players):
            raise ValidationError("Assigned and pending players cannot overlap")
        if(unassigned_players & pending_players):
            raise ValidationError("Unassigned and pending players cannot overlap")
        if(assigned_players & requesting_players):
            raise ValidationError("Assigned and requesting players cannot overlap")
        if(unassigned_players & requesting_players):
            raise ValidationError("Unassigned players and requesting players cannot overlap")
        if(pending_players & requesting_players):
            raise ValidationError("Assigned and requesting players cannot overlap")
        
        all_team_players = set()
        for team in self.teams.all():
            team_players = set(team.players.all())

            if(all_team_players & team_players):
                raise ValidationError("A player may only belong to one team in the same pickup game")
            
            all_team_players.update(team_players)

        

    def create(self, *args, **kwargs):
        self.join_code = self.generate_join_code()
        super().save(*args, **kwargs)

    def save(self, *args, **kwargs):
        if is_naive(self.date):
            self.date = make_aware(self.date)
        if not self.join_code:
            while True:
                temp_id = self.generate_join_code()
                if not PickupGame.objects.filter(join_code=temp_id).exists():
                    self.join_code=temp_id
                    break
        if self.status == 2:
            if self.winner is None:
                raise ValueError("A game is marked as completed but has no winner. Ties are not allowed")
            for team in self.teams.all():
                if team.players.count() < self.format:
                    raise ValueError("Both teams must have the minimum of the players required for the given format")
        super().save(*args, **kwargs)

    @staticmethod
    def generate_join_code():
        return uuid.uuid4().hex[:8].upper()
    
    @property
    def winner(self):
        if self.ringers_score > self.ballers_score:
            return "Ringers"
        elif self.ballers_score > self.ringers_score:
            return "Ballers"
        return None

class Membership(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="member")
    name = models.CharField(max_length=50)
    friends = models.ManyToManyField('self', symmetrical=True, blank=True)
    sent_requests = models.ManyToManyField('self', related_name='received_requests', symmetrical=False, blank=True)
    friend_id = models.CharField(max_length=8, unique=True, blank=True, null=True)
    pickup_wins = models.PositiveSmallIntegerField(default=0)
    pickup_losses = models.PositiveSmallIntegerField(default=0)

    wins_3v3 = models.PositiveSmallIntegerField(default=0, blank=True)
    losses_3v3 = models.PositiveSmallIntegerField(default=0, blank=True)
    wins_4v4 = models.PositiveSmallIntegerField(default=0, blank=True)
    losses_4v4 = models.PositiveSmallIntegerField(default=0, blank=True)
    wins_5v5 = models.PositiveSmallIntegerField(default=0, blank=True)
    losses_5v5= models.PositiveSmallIntegerField(default=0, blank=True)

    def save(self, *args, **kwargs):
        if not self.friend_id:
            while True:
                temp_id = self.generate_friend_id()
                if not Membership.objects.filter(friend_id=temp_id).exists():
                    self.friend_id = temp_id
                    break
        super().save(*args, **kwargs)

    @staticmethod
    def generate_friend_id():
        return uuid.uuid4().hex[:8].upper()

class PickupTeam(models.Model):
    name = models.CharField(max_length=50, blank=True)
    game = models.ForeignKey(PickupGame, on_delete=models.CASCADE, related_name="teams")
    is_ringers = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        self.name = 'Ringers' if self.is_ringers else 'Ballers'
        super().save(*args, **kwargs)


class PickupPlayer(models.Model):
    member = models.ForeignKey(Membership, on_delete=models.CASCADE)
    name = models.CharField(max_length=50)
    game = models.ForeignKey(PickupGame, on_delete=models.CASCADE, related_name="players")
    team = models.ForeignKey(PickupTeam, on_delete=models.CASCADE, related_name="players", blank=True, null=True)

class Notification(models.Model):
    member = models.ForeignKey(Membership, on_delete=models.CASCADE, related_name="notifications")
    friend = models.ForeignKey(Membership, on_delete=models.CASCADE, related_name="friend_notifications", blank=True, null=True)
    game = models.ForeignKey(PickupGame, on_delete=models.CASCADE, related_name="member_notifications", blank=True, null=True)
    message = models.CharField(max_length=200)

    def save(self, *args, **kwargs):
        if(self.friend is None and self.game is None):
            raise ValidationError("A notification must be bound to another member or a game.")
        if(self.friend and self.game):
            raise ValidationError("A notification cannot be bound to both another member or a game.")
        super().save(*args, **kwargs)
