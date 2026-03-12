import json
from channels.generic.websocket import AsyncWebsocketConsumer


# Group name for broadcasting new incident alerts to all dashboards (RESCOM, CDC, RCDG, etc.)
INCIDENT_ALERTS_GROUP = 'incident_alerts'


class IncidentAlertConsumer(AsyncWebsocketConsumer):
    """Consumer for real-time new-incident alerts. All dashboards subscribe and play alarm when a reservist submits."""

    async def connect(self):
        await self.channel_layer.group_add(INCIDENT_ALERTS_GROUP, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(INCIDENT_ALERTS_GROUP, self.channel_name)

    async def receive(self, text_data):
        pass

    async def new_incident_alert(self, event):
        """Send new incident payload to client so it can play alarm and optionally refresh map."""
        await self.send(text_data=json.dumps({
            'type': 'new_incident_alert',
            'incident_id': event.get('incident_id'),
            'title': event.get('title'),
            'incident_type': event.get('incident_type'),
            'reservist_id': event.get('reservist_id'),
        }))


class IncidentTrackingConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.incident_id = self.scope['url_route']['kwargs']['incident_id']
        self.room_group_name = f'incident_tracking_{self.incident_id}'

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    # Receive message from WebSocket
    async def receive(self, text_data):
        # In a typical scenario, clients just listen, but we can handle messages if needed
        pass

    # Receive message from room group
    async def tracking_message(self, event):
        await self.send(text_data=json.dumps({
            'type': event.get('type'),
            'data': event.get('data')
        }))

    async def responder_stopped(self, event):
        """Broadcast so all map clients remove this responder's marker."""
        await self.send(text_data=json.dumps({
            'type': 'responder_stopped',
            'data': {'reservist_id': event.get('reservist_id')}
        }))
