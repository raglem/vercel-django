from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework import serializers
from .models import Note, PickupGame, PickupPlayer, PickupTeam, Membership, Notification

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "password"]
        extra_kwargs = {"password": {"write_only": True}}

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        Membership.objects.create(user=user, name=user.username)
        return user
    
class NoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Note
        fields = ["id", "title", "content", "created_at", "author"]
        extra_kwargs = {"author": {"read_only": True}}

class MembershipSerializer(serializers.ModelSerializer):    
    friends = serializers.SerializerMethodField()
    sent_requests = serializers.SerializerMethodField()
    received_requests = serializers.SerializerMethodField()
    pickup_games = serializers.PrimaryKeyRelatedField(queryset=PickupGame.objects.all(), many=True)

    class Meta:
        model = Membership
        fields = ['id', 'user', 'name', 
                  'friends', 'friend_id', 'sent_requests', 'received_requests',
                  'pickup_games'
                  ]

    def get_friends(self, obj):
        return list(obj.friends.values('id', 'name', 'friend_id').order_by('name'))
    
    def get_sent_requests(self, obj):
        return list(obj.sent_requests.values('name', 'friend_id').order_by('name'))
    def get_received_requests(self, obj):
        return list(obj.received_requests.values('name', 'friend_id').order_by('name'))
    
class PickupGameDetailSerializer(serializers.ModelSerializer):
    player_team = serializers.SerializerMethodField()
    class Meta:
        model = PickupGame
        fields = ['id', 'join_code', 'format', 'location', 'date', 'ringers_score', 'ballers_score', 'winner', 'player_team']

    def get_player_team(self, obj):
        id = self.context.get('id')
        if not id:
            return None
        ringers = obj.teams.get(name="Ringers")
        return 'Ringers' if id in ringers.players.values_list('member_id', flat=True) else 'Ballers'


class PlayerCardSerializer(serializers.ModelSerializer):
    upcoming_games = serializers.SerializerMethodField()
    recent_games = serializers.SerializerMethodField()
    class Meta:
        model = Membership
        fields = ['id', 'name',
                  'wins_3v3', 'losses_3v3',
                  'wins_4v4', 'losses_4v4',
                  'wins_5v5', 'losses_5v5',
                  'pickup_wins', 'pickup_losses',
                  'upcoming_games', 'recent_games',
                  ]
        
    def get_upcoming_games(self, obj):
        current = timezone.now().date()
        upcoming_games = obj.pickup_games.filter(status=1, date__gt=current).order_by('date')[:3]
        return PickupGameDetailSerializer(upcoming_games, many=True, context={'id': obj.id}).data
    def get_recent_games(self, obj):
        current = timezone.now().date()
        recent_games = obj.pickup_games.filter(status=2).order_by('-date')[:3]
        return PickupGameDetailSerializer(recent_games, many=True, context={'id': obj.id}).data

class PlayerPageSerializer(serializers.ModelSerializer):
    upcoming_games = serializers.SerializerMethodField()
    recent_games = serializers.SerializerMethodField()
    mutual_friends = serializers.SerializerMethodField()
    class Meta:
        model = Membership
        fields = ['id', 'name', 'friend_id', 'mutual_friends',
                  'wins_3v3', 'losses_3v3',
                  'wins_4v4', 'losses_4v4',
                  'wins_5v5', 'losses_5v5',
                  'pickup_wins', 'pickup_losses',
                  'upcoming_games', 'recent_games',
                  ]
        
    def get_upcoming_games(self, obj):
        current = timezone.now().date()
        upcoming_games = obj.pickup_games.filter(status=1, date__gt=current).order_by('date')
        return PickupGameDetailSerializer(upcoming_games, many=True, context={'id': obj.id}).data
    def get_recent_games(self, obj):
        current = timezone.now().date()
        recent_games = obj.pickup_games.filter(status=2).order_by('-date')
        return PickupGameDetailSerializer(recent_games, many=True, context={'id': obj.id}).data
    def get_mutual_friends(self, obj):
        current_member = Membership.objects.get(id=self.context.get('member_id'))
        mutual_friends = current_member.friends.filter(id__in=obj.friends.values_list('id', flat=True))
        return mutual_friends.values('id', 'name')
    
class PlayerDetailSerializer(serializers.ModelSerializer):
    member_id = serializers.PrimaryKeyRelatedField(queryset=Membership.objects.all())
    class Meta:
        model = PickupPlayer
        fields = ['id', 'name', 'member_id']

class TeamDetailSerializer(serializers.ModelSerializer):
    players = PlayerDetailSerializer(many=True, read_only=True)
    class Meta:
        model = PickupTeam
        fields = ['id', 'name', 'players']

class PickupGameSerializer(serializers.ModelSerializer):
    owner = UserSerializer(read_only=True)

    assigned_players = PlayerDetailSerializer(many=True, read_only=True)
    unassigned_players = PlayerDetailSerializer(many=True, read_only=True)
    pending_players = PlayerDetailSerializer(many=True, read_only=True)
    requesting_players = PlayerDetailSerializer(many=True, read_only=True)
    teams = TeamDetailSerializer(many=True, read_only=True)
    player_team = serializers.SerializerMethodField()

    class Meta:
        model = PickupGame
        fields = [
            'id', 'owner', 'format', 'location', 'date', 'join_code', 'status',
            'all_members', 'teams', 
            'assigned_players', 'unassigned_players', 'pending_players', 'requesting_players',
            'status', 'ringers_score', 'ballers_score', 'winner', 'player_team'
        ]
        extra_kwargs = {
            'teams': {'required': False},
            'all_members': {'required': False},
            'assigned_players': {'required': False},
            'unassigned_players': {'required': False},
            'pending_players': {'required': False},
            'requesting_players': {'required': False},
        }

    def get_player_team(self, obj):
        id = self.context.get('id')
        if not id:
            return None
        ringers = obj.teams.get(name="Ringers")
        print(ringers.players)
        return 'Ringers' if id in ringers.players.values_list('member_id', flat=True) else 'Ballers'

    def create(self, validated_data):
        validated_data['status'] = 1

        invited_players_data = self.initial_data.get('all_players', [])
        validated_data.pop('teams', None)
        
        pickup_game = super().create(validated_data)
        if invited_players_data:
            invited_player_ids = [player for player in invited_players_data]
            print(invited_player_ids)
            members = Membership.objects.filter(id__in=invited_player_ids)
            players = []
            for member in members:
                player_data = {
                    'member_id': member.id,
                    'name': member.name,
                    'game': pickup_game
                }
                player = PickupPlayer.objects.create(**player_data)
                players.append(player.id)
                pickup_game.all_members.add(member)

            pickup_game.all_players.set(players)
            pickup_game.pending_players.set(players)
        
        ringers = PickupTeam.objects.create(
            is_ringers = True, 
            game = pickup_game
        )
        ballers = PickupTeam.objects.create(
            is_ringers = False, 
            game = pickup_game
        )
        pickup_game.teams.add(ringers, ballers)
        return pickup_game


class PickupTeamSerializer(serializers.ModelSerializer):
    players = serializers.SerializerMethodField()
    game = serializers.PrimaryKeyRelatedField(queryset=PickupGame.objects.all())
    class Meta:
        model = PickupTeam
        fields = ['id', 'game', 'is_ringers', 'players']
        extra_kwargs = {
            'players': {'required': False}
        }

    def get_players(self, obj):
        if(obj.players):
            return list(obj.players.values('id', 'name'))
        return None
    

class PickupPlayerSerializer(serializers.ModelSerializer):
    team_details = serializers.SerializerMethodField()
    game = serializers.PrimaryKeyRelatedField(queryset=PickupGame.objects.all())
    member_id = serializers.PrimaryKeyRelatedField(queryset=Membership.objects.all())

    class Meta:
        model = PickupPlayer
        fields = ['id', 'member_id', 'name', 'team_details', 'game']
        extra_kwargs = {
            'team_details': {'required': False}
        }
    
    def get_team_details(self, obj):
        if obj.team:
            return {
                'id': obj.team.id,
                'is_ringers': obj.team.is_ringers,
            }
        return None

class NotificationSerializer(serializers.ModelSerializer):
    member = serializers.SerializerMethodField()
    friend = serializers.SerializerMethodField()
    game = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = ['member', 'friend', 'game', 'message']

    def get_member(self, obj):
        return {
            'id': obj.member.id,
            'name': obj.member.name
        }
    
    def get_friend(self, obj):
        if(obj.friend is None):
            return None
        return {
            'id': obj.friend.id,
            'name': obj.friend.name
        }
    
    def get_game(self, obj):
        if(obj.game is None):
            return None
        return {
            'id': obj.game.id,
            'owner': obj.game.owner.username,
            'date': obj.game.date,
            'title': str(obj.game)
        }
    
    







    

