from django.shortcuts import render
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import generics
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from .serializers import UserSerializer, NoteSerializer, MembershipSerializer, PlayerCardSerializer, PlayerPageSerializer, PickupGameSerializer, NotificationSerializer
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import Note, PickupGame, PickupPlayer, PickupTeam, Membership, Notification


class NoteListCreate(generics.ListCreateAPIView):
    serializer_class = NoteSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Note.objects.filter(author=user)

    def perform_create(self, serializer):
        if serializer.is_valid():
            serializer.save(author=self.request.user)
        else:
            print(serializer.errors)


class NoteDelete(generics.DestroyAPIView):
    serializer_class = NoteSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Note.objects.filter(author=user)


class CreateUserView(generics.ListCreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [AllowAny]

class AllMembersView(generics.ListAPIView):
    queryset = Membership.objects.all()
    serializer_class = MembershipSerializer
    permission_classes = [AllowAny]

class MembershipView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        member = get_object_or_404(Membership, user=request.user)
        serialized = MembershipSerializer(member)
        return Response(serialized.data)
    
# FRIEND LIST

class AddFriendView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, *args, **kwargs):
        member = get_object_or_404(Membership, user=request.user)
        friend_id = request.data.get('friend_id')

        if not friend_id:
            return Response({'error': 'friend_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            friend_member = Membership.objects.get(friend_id=friend_id)
        except Membership.DoesNotExist:
            return Response({'error': f'Player not found. Please make sure the provided id is correct'}, status=status.HTTP_400_BAD_REQUEST)
        except:
            return Response({'error': f'Someting went wrong'})

        if member == friend_member:
            return Response({'error': 'You cannot add yourself as a friend'}, status=status.HTTP_400_BAD_REQUEST)
        if friend_member in member.friends.all():
            return Response({'error': f'{friend_member.name} is already your friend'}, status=status.HTTP_400_BAD_REQUEST)
        if friend_member in member.sent_requests.all():
            return Response({'error': 'Friend request already sent'}, status=status.HTTP_400_BAD_REQUEST)

        member.sent_requests.add(friend_member)
        friend_member.received_requests.add(member)

        notification_message = f'{member.name} has sent you a friend request'
        Notification.objects.create(member=friend_member, friend=member, message=notification_message)

        return Response({'message': f'{friend_member.name} has received your friend request'}, status=status.HTTP_200_OK)
    
class AcceptFriendView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, *args, **kwargs):
        member = get_object_or_404(Membership, user=request.user)
        friend_id = request.data.get('friend_id')
        friend_member = get_object_or_404(Membership, friend_id=friend_id)

        if(member == friend_member):
            return Response({'error': 'You cannot add yourself as a friend'}, status=status.HTTP_400_BAD_REQUEST)
        if(friend_member not in member.received_requests.all()):
            return Response({'error': f'{friend_member.name} did not request to add you as a friend'}, status=status.HTTP_400_BAD_REQUEST)
        
        friend_member.sent_requests.remove(member)
        friend_member.sent_requests.remove(member)

        member.friends.add(friend_member)
        friend_member.friends.add(member)

        notification_message = f'{member.name} accepted your friend request'
        Notification.objects.create(member=friend_member, friend=member, message=notification_message)

        return Response({'message': f'{friend_member.name} has been successfully added as a friend'}, status=status.HTTP_200_OK)
    
class DeleteFriendView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, *args, **kwargs):
        member = get_object_or_404(Membership, user=request.user)
        friend_id = request.data.get('friend_id')
        friend_member = get_object_or_404(Membership, friend_id=friend_id)

        if(member == friend_member):
            return Response({'error': 'You cannot remove yourself as a friend'}, status=status.HTTP_400_BAD_REQUEST)
        if(friend_member not in member.friends.all()):
            return Response({'error': f'{friend_member.name} is not in your friend list'}, status=status.HTTP_400_BAD_REQUEST)
        
        member.friends.remove(friend_member)
        
        return Response({'message': f'{friend_member.name} has been successfully removed as a friend'}, status=status.HTTP_200_OK)
    
class RejectFriendView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, *args, **kwargs):
        member = get_object_or_404(Membership, user=request.user)
        friend_id = request.data.get('friend_id')
        friend_member = get_object_or_404(Membership, friend_id=friend_id)

        if(friend_member not in member.received_requests.all()):
            return Response({'error': "f{friend_member.name} is not in your received friend requests"})
        
        member.received_requests.remove(friend_member)
        friend_member.sent_requests.remove(member)

        notification_message = f'{member.name} has declined your friend request'
        Notification.objects.create(member=friend_member, friend=member, message=notification_message)
        return Response({'message': f'Friend request from {friend_member.name} successfully declined'})

class CancelFriendRequest(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, *args, **kwargs):
        member = get_object_or_404(Membership, user=request.user)
        friend_id = request.data.get('friend_id')
        friend_member = get_object_or_404(Membership, friend_id=friend_id)

        if(friend_member not in member.sent_requests.all()):
            return Response({'error': "f{friend_member.name} is not in your sent friend requests"})
        
        member.sent_requests.remove(friend_member)
        friend_member.received_requests.remove(member)

        notification_message = f'{member.name} has rescinded their friend request'
        Notification.objects.create(member=friend_member, friend=member, message=notification_message)
        return Response({'message': f'Friend invite to {friend_member.name} successfully canceled'})

            
# PICKUP GAME
class PickupGameAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, *args, **kwargs):
        game = get_object_or_404(PickupGame, id=request.data.get('game_id'))
        game_serializer = PickupGameSerializer(game)
        return Response(game_serializer.data, status=status.HTTP_200_OK)

class PickupGameListAPIView(generics.ListAPIView):
    queryset = PickupGame.objects.all()
    serializer_class = PickupGameSerializer
    permission_classes = [AllowAny]

class PickupGameCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        data = request.data.copy()
        
        user_data = UserSerializer(request.user).data
        data['owner'] = user_data  # Set the owner field to the serialized user data

        serializer = PickupGameSerializer(data=data)
        if serializer.is_valid():
            serializer.save(owner=request.user)
            pickup_game = serializer.save()
            return Response({'game': PickupGameSerializer(pickup_game).data,
                             'message': f'{pickup_game} successfully created'}, 
                             status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class PickupGameInviteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        game_id = request.data.get('id')
        user = request.user
        game = get_object_or_404(PickupGame, id=game_id)

        if(game.owner != user):
            return Response({'error': 'You are not the owner of this pickup game'}, status=status.HTTP_401_UNAUTHORIZED)
        
        invited_member_ids = request.data.get('invited_member_ids')
        if(not isinstance(invited_member_ids, list) or not all(isinstance(x, int) for x in invited_member_ids)):
            return Response({'error': 'Invited players must be in a list of integers'}, status=status.HTTP_400_BAD_REQUEST)
        
        valid_member_ids = Membership.objects.filter(id__in=invited_member_ids)
        invalid_member_ids = set(invited_member_ids) - set(valid_member_ids.values_list('id', flat=True))

        all_invited_member_ids = game.all_players.values_list('member_id', flat=True)
        
        already_invited_member_ids = set(valid_member_ids.values_list('id', flat=True)) & set(all_invited_member_ids)
        already_invited_players = game.all_players.all().filter(member_id__in=already_invited_member_ids).values_list('name', flat=True)

        newly_invited_member_ids = set(valid_member_ids.values_list('id', flat=True)) - set(all_invited_member_ids)
        all_members = Membership.objects.filter(id__in=newly_invited_member_ids)
        newly_invited_players = [
            PickupPlayer(member=Membership.objects.get(id=member_id), 
                     name=Membership.objects.get(id=member_id).name, 
                     game=game)
            for member_id in newly_invited_member_ids
        ]
        PickupPlayer.objects.bulk_create(newly_invited_players)

        game.all_players.add(*newly_invited_players)
        game.pending_players.add(*newly_invited_players)
        game.all_members.add(*all_members)

        newly_invited_players_names = Membership.objects.filter(id__in=newly_invited_member_ids).values_list('name', flat=True)
        already_invited_players_names = Membership.objects.filter(id__in=already_invited_member_ids).values_list('name', flat=True)

        name_output = ",".join(list(newly_invited_players_names))

        for member_id in newly_invited_member_ids:
            member = Membership.objects.get(id=member_id)
            notification_message = f'{user.username} has invited you for {game}'
            Notification.objects.create(member=member, game=game, message=notification_message)

        return Response({'message': f'{name_output} successfully invited to {game}',
                        'invited_players': list(newly_invited_players_names),
                         'already_invited_players': list(already_invited_players_names),
                         'invalid_ids': list(invalid_member_ids),
                        }, status=status.HTTP_200_OK)

class PickupGameUpdateDetailsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user = request.user
        game = PickupGame.objects.get(id=request.data.get('game_id'))

        if user != game.owner:
            return Response({'error': f'{user.username} is the not the owner of this game'}, status=status.HTTP_403_FORBIDDEN)
        
        if not (request.data.get('format') and request.data.get('location') and request.data.get('date')):
            return Response({'error': 'Updated data is not formatted properly'}, status=status.HTTP_400_BAD_REQUEST)
       
        game.format = request.data.get('format')
        game.location = request.data.get('location')
        game.date = parse_datetime(request.data.get('date'))
        game.save()
        
        return Response({'message': f'{game} successfully updated'}, status=status.HTTP_200_OK)


class PickupGameDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user = request.user
        game = PickupGame.objects.get(id=request.data.get('game_id'))

        if user != game.owner:
            return Response({'error': f'{user.username} is the not the owner of this game'}, status=status.HTTP_403_FORBIDDEN)
        
        name = str(game)
        game.delete()
        return Response({'message': f'{name} was successfully deleted'}, status=status.HTTP_200_OK)

class PickupGameMembershipAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        member = Membership.objects.get(user=request.user.id)
 
        upcoming_games = []
        invited_games = []
        completed_games = []
        pending_games = []
        requesting_games = []

        owned_games = user.owned_games.filter(status=1, date__gt=timezone.now()).order_by('date')
        owned_games_unupdated = user.owned_games.filter(status=1, date__lt=timezone.now()).order_by('date')
        owned_games_serialized = PickupGameSerializer(owned_games, many=True)
        owned_unupdated_games_serialized = PickupGameSerializer(owned_games_unupdated, many=True)

        for pickup_game in member.pickup_games.order_by('date'):
            pickup_game_serializer = PickupGameSerializer(pickup_game, context={'id': member.id})

            if pickup_game.status == 1:
                pending_games.append(pickup_game_serializer.data)

                if member.id in pickup_game.assigned_players.all().values_list('member_id', flat=True):
                    upcoming_games.append(pickup_game_serializer.data)
                elif member.id in pickup_game.unassigned_players.all().values_list('member_id', flat=True):
                    upcoming_games.append(pickup_game_serializer.data)
                elif member.id in pickup_game.pending_players.all().values_list('member_id', flat=True):
                    invited_games.append(pickup_game_serializer.data)
                elif member.id in pickup_game.requesting_players.all().values_list('member_id', flat=True):
                    requesting_games.append(pickup_game_serializer.data)
            elif pickup_game.status == 2:
                completed_games.append(pickup_game_serializer.data)
        
        response_data = {
            "owned_games": owned_games_serialized.data,
            "owned_unupdated_games": owned_unupdated_games_serialized.data,
            'upcoming_games': upcoming_games,
            'invited_games': invited_games,
            'completed_games': completed_games,
            'pending_games': pending_games,
            'requesting_games': requesting_games,
        }

        return Response(response_data, status=status.HTTP_200_OK)
    
class PickupGameMembershipFriendsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        member = Membership.objects.get(user=request.user)
        member_card = PlayerCardSerializer(member)
        friends_card = PlayerCardSerializer(member.friends.order_by('name'), many=True)
        response = {'friends': friends_card.data,
                    'member': member_card.data}
        return Response(response, status=status.HTTP_200_OK)
    
class PickupGameMembershipPageAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        current_member = Membership.objects.get(user=request.user)
        try:
            member = Membership.objects.get(id=request.GET.get('member_id'))
        except Membership.DoesNotExist:
            return Response({'error': 'Player not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': f'An unexpected error occurred: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        member_serializer = PlayerPageSerializer(member, context={'member_id': current_member.id})
        return Response(member_serializer.data, status=status.HTTP_200_OK)
    
class PickupGameMembershipAcceptAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user = request.user
        member = Membership.objects.get(user=user)
        game_id = request.data.get('game_id')
        game = get_object_or_404(PickupGame, id=game_id)
        if (member not in game.all_members.all()):
            return Response({'error': f'{member.name} was not invited'})
        
        player = game.pending_players.get(member_id=member.id)

        if(player not in game.all_players.all()):
            return Response({'error': f'{player.name} was not invited or not successfully added to the game'})
        if(player in game.assigned_players.all() or player in game.unassigned_players.all()):
            return Response({'error': f'{player.name} already accepted the invite'})
        if(player not in game.pending_players.all()):
            return Response({'error': f'{player.name} already accepted the invite'})
        
        game.pending_players.remove(player)
        game.unassigned_players.add(player)

        notification_message = f'{member.name} has accepted your game invite for {game}'
        game_owner_member = Membership.objects.get(user=game.owner)
        Notification.objects.create(member=game_owner_member, game=game, message=notification_message)

        return Response({'message': f'You have been successfully added to {game}'})
    
class PickupGameMembershipRejectAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user = request.user
        member = Membership.objects.get(user=user)
        game_id = request.data.get('game_id')
        game = get_object_or_404(PickupGame, id=game_id)
        if (member not in game.all_members.all()):
            return Response({'error': f'{member.name} was not invited'})
        
        player = game.pending_players.get(member_id=member.id)

        if(player not in game.all_players.all()):
            return Response({'error': f'{player.name} was not invited or successfully added to the game'})
        if(player in game.assigned_players.all() or player in game.unassigned_players.all()):
            return Response({'error': f'{player.name} already accepted the invite'})
        if(player not in game.pending_players.all()):
            return Response({'error': f'{player.name} already accepted the invite'})
        
        game.pending_players.remove(player)
        game.all_players.remove(player)
        game.all_members.remove(member)

        notification_message = f'{member.name} has rejected your game invite for {game}'
        game_owner_member = Membership.objects.get(user=game.owner)
        Notification.objects.create(member=game_owner_member, game=game, message=notification_message)

        return Response({'message': f'You have been successfully removed from {game}'})
    
class PickupGameMembershipRequestAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user = request.user
        member = Membership.objects.get(user=user)
        
        try:
            game = PickupGame.objects.get(join_code=request.data.get('game_code'))
        except PickupGame.DoesNotExist:
            return Response({'error': 'Invalid game code. Game not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': f'An unexpected error occurred: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if (member in game.all_members.all()):
            return Response({'error': f'You already requested or were added to {game}'}, status=status.HTTP_400_BAD_REQUEST)
        
        player_data = {
            'member_id': member.id,
            'name': member.name,
            'game': game
        }
        player = PickupPlayer.objects.create(**player_data)
        game.all_members.add(member)
        game.all_players.add(player)
        game.requesting_players.add(player)

        notification_message = f'{member.name} has requested acceptance for {game}'
        game_owner_member = Membership.objects.get(user=game.owner)
        Notification.objects.create(member=game_owner_member, game=game, message=notification_message)

        return Response({'message': f'You successfully requested acceptance into {game}. The game owner will review your request.'}, status=status.HTTP_200_OK)
    
class PickupGameTeamAssignmentAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        game_id = request.data.get('game_id')
        game = get_object_or_404(PickupGame, id=game_id)
        ringers_player_ids = request.data.get('ringers_player_ids')
        ballers_player_ids = request.data.get('ballers_player_ids')

        if(not isinstance(ringers_player_ids, list) or not all(isinstance(x, int) for x in ringers_player_ids)):
            return Response({'error': 'Ringers player ids must be in a list of integers'}, status=status.HTTP_400_BAD_REQUEST)
        if(not isinstance(ballers_player_ids, list) or not all(isinstance(x, int) for x in ballers_player_ids)):
            return Response({'error': 'Ballers player ids must be in a list of integers'}, status=status.HTTP_400_BAD_REQUEST)

        ringers_players = game.unassigned_players.filter(id__in=ringers_player_ids)
        ballers_players = game.unassigned_players.filter(id__in=ballers_player_ids)
        
        valid_ringers_ids = set(ringers_players.values_list('id', flat=True))
        valid_ballers_ids = set(ballers_players.values_list('id', flat=True))

        invalid_ringers_ids = set(ringers_player_ids) - valid_ringers_ids
        invalid_ballers_ids = set(ballers_player_ids) - valid_ballers_ids
        invalid_ids = invalid_ringers_ids | invalid_ballers_ids

        ringers = game.teams.get(name="Ringers")
        ballers = game.teams.get(name="Ballers")
        ringers_names = list(ringers_players.values_list('name', flat=True))
        ballers_names = list(ballers_players.values_list('name', flat=True))

        ringers.players.add(*ringers_players)
        ballers.players.add(*ballers_players)

        game.assigned_players.add(*ringers_players, *ballers_players)
        game.unassigned_players.remove(*ringers_players, *ballers_players)

        ringers_message = ",".join(ringers_names) if len(ringers_names) > 0 else 'None'
        ballers_message = ",".join(ballers_names) if len(ballers_names) > 0 else 'None'

        return Response({
            'message': f'Players successfully assigned to teams in {game}. \n Ringers additions: {ringers_message} \n Ballers additions: {ballers_message}',
            'added Ringers players': list(ringers_names),
            'added Ballers players': list(ballers_names),
            'invalid_ids': list(invalid_ids)
        })
    
class PickupGameTeamReassignAPIView(APIView):
    def post(self, request, *args, **kwargs):
        user = request.user
        game = get_object_or_404(PickupGame, id=request.data.get('game_id'))

        if game.owner != user:
            return Response({'error': f'{user.username} is not the owner of this game'}, status=status.HTTP_401_UNAUTHORIZED)
        
        player_id = request.data.get('player_id')
        player = get_object_or_404(PickupPlayer, id=player_id)

        if player not in game.assigned_players.all():
            return Response({'error': f'{player.name} was not previously assigned to a team'}, status=status.HTTP_200_OK)
        
        if(player.team.name == 'Ringers'):
            player.team = game.teams.get(name='Ballers')
            player.save()
        elif(player.team.name == 'Ballers'):
            player.team = game.teams.get(name='Ringers')
            player.save()
        
        return Response({'message': f'{player.name} assigned to {player.team.name}'}, status=status.HTTP_200_OK)
    
class PickupGameTeamRemoveAPIView(APIView):
    def post(self, request, *args, **kwargs):
        user = request.user
        game = get_object_or_404(PickupGame, id=request.data.get('game_id'))

        if game.owner != user:
            return Response({'error': f'{user.username} is not the owner of this game'}, status=status.HTTP_401_UNAUTHORIZED)
        
        player_id = request.data.get('player_id')
        player = get_object_or_404(PickupPlayer, id=player_id)

        if player not in game.assigned_players.all():
            return Response({'error': f'{player.name} was not previously assigned to a team'}, status=status.HTTP_200_OK)
        
        team = player.team
        player.team = None
        player.save()

        game.unassigned_players.add(player)
        game.assigned_players.remove(player)
        
        return Response({'message': f'{player.name} removed from {team.name} \nMoved to unassigned in {game}'}, status=status.HTTP_200_OK)
    
class PickupGameAcceptPlayerRequest(APIView):
    def post(self, request, *args, **kwargs):
        user = request.user
        game = get_object_or_404(PickupGame, id=request.data.get('game_id'))

        if(user != game.owner):
            return Response({'error': f'{user.username} is not the owner of {game}'}, status=status.HTTP_403_FORBIDDEN)

        try:
            player = game.requesting_players.get(id=request.data.get('player_id'))
            if not player:
                return Response({'error': 'Player not found'}, status=status.HTTP_404_NOT_FOUND)
        except game.requesting_players.model.DoesNotExist:
            return Response({'error': 'Player not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': f'An unexpected error occurred: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        game.requesting_players.remove(player)
        game.unassigned_players.add(player)

        member = Membership.objects.get(id=player.member_id)
        notification_message = f'{user.username} has accepted your join request for {game}'
        Notification.objects.create(member=member, game=game, message=notification_message)

        return Response({'message': f'{player.name} was successfully accepted into {game}'}, status=status.HTTP_200_OK)
    
class PickupGameRejectPlayerRequest(APIView):
    def post(self, request, *args, **kwargs):
        user = request.user
        game = get_object_or_404(PickupGame, id=request.data.get('game_id'))

        if(user != game.owner):
            return Response({'error': f'{user.username} is not the owner of {game}'}, status=status.HTTP_403_FORBIDDEN)

        try:
            player = game.requesting_players.get(id=request.data.get('player_id'))
            if not player:
                return Response({'error': 'Player not found'}, status=status.HTTP_404_NOT_FOUND)
        except game.requesting_players.model.DoesNotExist:
            return Response({'error': 'Player not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': f'An unexpected error occurred: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        member = game.all_members.get(id=player.member_id)
        name = player.name

        player.delete()
        game.all_members.remove(member)

        notification_message = f'{user.username} has rejected your join request for {game}'
        Notification.objects.create(member=member, game=game, message=notification_message)
        return Response({'message': f'{name} was successfully rejected from {game}'}, status=status.HTTP_200_OK)

class PickupGameRemoveByPlayerAPIView(APIView):
    def post(self, request, *args, **kwargs):
        user = request.user
        game = get_object_or_404(PickupGame, id=request.data.get('game_id'))

        if(user != game.owner):
            return Response({'error': f'{user.username} is not the owner of {game}'}, status=status.HTTP_403_FORBIDDEN)
        
        player_id = request.data.get('player_id')
        player = get_object_or_404(game.all_players, id=player_id)
        member = player.member

        name = player.name
        player.delete()
        game.all_members.remove(member)

        notification_message = f'{user.username} has removed you from {game}'
        Notification.objects.create(member=member, game=game, message=notification_message)
        
        return Response({'message': f'{name} successfully removed from {game}'}, status=status.HTTP_200_OK)
    
class PickupGameRemoveByUserAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, *args, **kwargs):
        user = request.user
        game = get_object_or_404(PickupGame, id=request.data.get('game_id'))
        
        member = user.member
        player = game.all_players.get(member_id=member.id)

        player.delete()
        game.all_members.remove(member)

        notification_message = f'{user.username} has left {game}'
        game_owner_member = Membership.objects.get(user=game.owner)
        Notification.objects.create(member=game_owner_member, game=game, message=notification_message)
        
        return Response({'message': f'You have been successfully removed from {game}'}, status=status.HTTP_200_OK)
    
class PickupGameFinalizeScoreAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, *args, **kwargs):
        user = request.user
        game = get_object_or_404(PickupGame, id=request.data.get('game_id'))

        if(user != game.owner):
            return Response({'error': f'{user.username} is not the owner of {game}'}, status=status.HTTP_403_FORBIDDEN)
        if(game.status!=1):
            return Response({'error': 'Game must be pending'}, status=status.HTTP_400_BAD_REQUEST)
        if(game.unassigned_players.count()!=0):
            return Response({'error': 'You still have players in the game who are unassigned. Please add them to a team or remove them from the game to finalize the score.'},
                            status=status.HTTP_400_BAD_REQUEST)
        
        for team in game.teams.all():
            if team.players.count() < game.status:
                return Response({'error': f'Both teams must have at least {game.format} players for the game score to be finalized'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            ringers_score = request.data.get('ringers_score')
            ballers_score = request.data.get('ballers_score')
        except:
            return Response({'error': 'Score for both Ringers and Ballers must be provided'}, status=status.HTTP_400_BAD_REQUEST)
        
        game.status=2
        game.ringers_score = ringers_score
        game.ballers_score = ballers_score
        game.save()

        winner = None
        loser = None
        if game.winner == "ringers":
            winner = game.teams.get(name="Ringers")
            loser = game.teams.get(name="Ballers")
        else:
            winner = game.teams.get(name="Ballers")
            loser = game.teams.get(name="Ringers")

        for player_data in winner.players.all():
            member = Membership.objects.get(id=player_data.member_id)
            member.pickup_wins += 1
            if game.format==3:
                member.wins_3v3 += 1
            if game.format==4:
                member.wins_4v4 += 1
            if game.format==5:
                member.wins_5v5 += 1
            member.save()

        for player_data in loser.players.all():
            member = Membership.objects.get(id=player_data.member_id)
            member.pickup_losses += 1
            if game.format==3:
                member.losses_3v3 += 1
            if game.format==4:
                member.losses_4v4 += 1
            if game.format==5:
                member.losses_5v5 += 1
            member.save()

        return Response({'message': f'Game score has has been set. {game} status has been set to completed'})
    
class PickupGameRevertStatus(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, *args, **kwargs):
        user = request.user
        game = get_object_or_404(PickupGame, id=request.data.get('game_id'))

        if(user != game.owner):
            return Response({'error': f'{user.username} is not the owner of {game}'}, status=status.HTTP_403_FORBIDDEN)
        if(game.status!=2):
            return Response({'error': 'Game must be completed'}, status=status.HTTP_400_BAD_REQUEST)
        
        
        game.status=1
        game.save()

        winner = None
        loser = None
        if game.winner == "ringers":
            winner = game.teams.get(name="Ringers")
            loser = game.teams.get(name="Ballers")
        else:
            winner = game.teams.get(name="Ballers")
            loser = game.teams.get(name="Ringers")

        for player_data in winner.players.all():
            member = Membership.objects.get(id=player_data.member_id)
            member.pickup_wins -= 1
            if game.format==3:
                member.wins_3v3 -= 1
            if game.format==4:
                member.wins_4v4 -= 1
            if game.format==5:
                member.wins_5v5 -= 1
            member.save()

        for player_data in loser.players.all():
            member = Membership.objects.get(id=player_data.member_id)
            member.pickup_losses -= 1
            if game.format==3:
                member.losses_3v3 -= 1
            if game.format==4:
                member.losses_4v4 -= 1
            if game.format==5:
                member.losses_5v5 -= 1
            member.save()

        return Response({'message': f'{game} status has been reverted to pending'})


class MembershipNotificationsAPIView(APIView):
    def get(self, request):
        member = Membership.objects.get(user=request.user)
        notifications = Notification.objects.filter(member=member)

        game_notifications = {}
        friend_notifications = []

        for notification in notifications.order_by('-id'):
            notification_serialized = NotificationSerializer(notification)
            if notification.game:
                if notification.game.id not in game_notifications:
                    game_notifications[notification.game.id] = {
                        "game": notification.game,
                        "notifications": []
                    }
                game_notifications[notification.game.id]["notifications"].append(notification)
            if notification.friend:
                friend_notifications.append(notification_serialized.data)

        ordered_games = sorted(
            game_notifications.items(),
            key=lambda item: item[1]["game"].date,
        )

        games_response = []

        for game_id, notification_data in ordered_games:
            game = PickupGame.objects.get(id=game_id)
            messages = [notif.message for notif in notification_data["notifications"]]
            games_response.append({
                'id': game.id,
                'title': str(game),
                'messages': messages,
            })

        response_data = {
            "games": games_response,
            "friends": friend_notifications
        }

        return Response(response_data, status=status.HTTP_200_OK)
    
class MembershipNotificationsClearGameAPIView(APIView):
    def post(self, request, *args, **kwargs):
        member = Membership.objects.get(user=request.user)
        try:
            game = PickupGame.objects.get(id=request.data.get('game_id'))
        except PickupGame.DoesNotExist:
            return Response({'error': f'Game not found'}, status=status.HTTP_400_BAD_REQUEST)
        except:
            return Response({'error': f'Someting went wrong'})
        
        notifications = member.notifications
        game_notifications = notifications.filter(game=game)
        game_notifications.delete()
        return Response({'message': f'Notifications of {game} cleared'}, status=status.HTTP_200_OK)
    
class MembershipNotificationsClearFriendsAPIView(APIView):
    def post(self, request, *args, **kwargs):
        member = Membership.objects.get(user=request.user)
        notifications = member.notifications
        friend_notifications = notifications.filter(friend__isnull=False)
        friend_notifications.delete()
        return Response({'message': f'Friend notifications cleared'}, status=status.HTTP_200_OK)
    
class MembershipNotificationsClearAll(APIView):
    def post(self, request, *args, **kwargs):
        member = Membership.objects.get(user=request.user)
        notifications = member.notifications
        notifications.delete()
        return Response({'message': f'All notifications cleared'}, status=status.HTTP_200_OK)
