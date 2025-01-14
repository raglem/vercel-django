from django.urls import path, include
from . import views

urlpatterns = [
    path("notes/", views.NoteListCreate.as_view(), name="note-list"),
    path("notes/delete/<int:pk>/", views.NoteDelete.as_view(), name='delete-note'),
    path("membership/", views.MembershipView.as_view()),
    path("add-friend/", views.AddFriendView.as_view()),
    path("accept-friend/", views.AcceptFriendView.as_view()),
    path("delete-friend/", views.DeleteFriendView.as_view()),
    path("cancel-friend-request/", views.CancelFriendRequest.as_view()),
    path("members/", views.AllMembersView.as_view()),
    path("membership/cards/", views.PickupGameMembershipFriendsAPIView.as_view()),
    path("membership/page/", views.PickupGameMembershipPageAPIView.as_view()),

    path("membership/notifications/", views.MembershipNotificationsAPIView.as_view()),
    path("membership/notifications/clear/", views.MembershipNotificationsClearAll.as_view()),
    path("membership/notifications/clear/game/", views.MembershipNotificationsClearGameAPIView.as_view()),
    path("membership/notifications/clear/friends/", views.MembershipNotificationsClearFriendsAPIView.as_view()),

    path("pickup-games/all/", views.PickupGameListAPIView.as_view()),
    path("pickup-game/", views.PickupGameAPIView.as_view()),
    path("pickup-games/", views.PickupGameMembershipAPIView.as_view()),
    path("pickup-games/create/", views.PickupGameCreateAPIView.as_view()),
    path("pickup-games/invite/", views.PickupGameInviteAPIView.as_view()),
    path("pickup-games/delete/", views.PickupGameDeleteAPIView.as_view()),
    path("pickup-games/update-details/", views.PickupGameUpdateDetailsAPIView.as_view()),

    path("pickup-games/remove-player/", views.PickupGameRemoveByPlayerAPIView.as_view()),
    path("pickup-games/remove-user/", views.PickupGameRemoveByUserAPIView.as_view()),
    path("pickup-games/accept/", views.PickupGameMembershipAcceptAPIView.as_view()),
    path("pickup-games/reject/", views.PickupGameMembershipRejectAPIView.as_view()),
    path("pickup-games/request/", views.PickupGameMembershipRequestAPIView.as_view()),
    path("pickup-games/request/accept/", views.PickupGameAcceptPlayerRequest.as_view()),
    path("pickup-games/request/reject/", views.PickupGameRejectPlayerRequest.as_view()),
    path("pickup-games/team/assign/", views.PickupGameTeamAssignmentAPIView.as_view()),
    path("pickup-games/team/reassign/", views.PickupGameTeamReassignAPIView.as_view()),
    path("pickup-games/team/remove/", views.PickupGameTeamRemoveAPIView.as_view()),
    path("pickup-games/score/", views.PickupGameFinalizeScoreAPIView.as_view()),
    path("pickup-games/score/revert/", views.PickupGameRevertStatus.as_view()),
]