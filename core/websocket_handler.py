"""
WebSocket handler for real-time chat features and collaboration.
"""

import asyncio
import json
import logging
import time
from collections import defaultdict
from typing import Any

try:
    import websockets
    from websockets.server import WebSocketServerProtocol
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    WebSocketServerProtocol = Any

logger = logging.getLogger(__name__)


class ChatWebSocketHandler:
    """
    WebSocket handler for real-time chat features including:
    - Live typing indicators
    - Real-time message updates
    - File processing notifications
    - Multi-user collaboration
    """

    def __init__(self):
        self.active_connections: dict[str, WebSocketServerProtocol] = {}
        self.chat_rooms: dict[str, set[str]] = defaultdict(set)
        self.user_status: dict[str, dict[str, Any]] = {}
        self.typing_status: dict[str, dict[str, float]] = defaultdict(dict)
        self._cleanup_task = None

    async def start_cleanup_task(self):
        """Start background cleanup task for expired typing indicators."""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_expired_typing())

    async def stop_cleanup_task(self):
        """Stop background cleanup task."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None

    async def handle_connection(self, websocket: WebSocketServerProtocol, user_id: str, chat_room: str = "default"):
        """
        Handle new WebSocket connection.
        """
        if not WEBSOCKETS_AVAILABLE:
            logger.error("WebSockets not available")
            return

        logger.info(f"User {user_id} connected to room {chat_room}")

        # Store connection
        self.active_connections[user_id] = websocket
        self.chat_rooms[chat_room].add(user_id)
        self.user_status[user_id] = {
            'room': chat_room,
            'connected_at': time.time(),
            'last_seen': time.time()
        }

        # Notify other users in room
        await self.broadcast_user_event(chat_room, {
            'type': 'user_joined',
            'user_id': user_id,
            'timestamp': time.time()
        }, exclude_user=user_id)

        try:
            async for message in websocket:
                await self.handle_message(user_id, chat_room, message)
                self.user_status[user_id]['last_seen'] = time.time()

        except websockets.exceptions.ConnectionClosed:
            logger.info(f"User {user_id} disconnected")
        except Exception as e:
            logger.error(f"WebSocket error for user {user_id}: {e}")
        finally:
            await self.disconnect_user(user_id, chat_room)

    async def handle_message(self, user_id: str, chat_room: str, message: str):
        """
        Handle incoming WebSocket message.
        """
        try:
            data = json.loads(message)
            message_type = data.get('type')

            if message_type == 'chat_message':
                await self.handle_chat_message(user_id, chat_room, data)
            elif message_type == 'typing_start':
                await self.handle_typing_start(user_id, chat_room)
            elif message_type == 'typing_stop':
                await self.handle_typing_stop(user_id, chat_room)
            elif message_type == 'ping':
                await self.send_to_user(user_id, {'type': 'pong', 'timestamp': time.time()})
            else:
                logger.warning(f"Unknown message type: {message_type}")

        except json.JSONDecodeError:
            logger.error(f"Invalid JSON from user {user_id}: {message}")
        except Exception as e:
            logger.error(f"Error handling message from {user_id}: {e}")

    async def handle_chat_message(self, user_id: str, chat_room: str, data: dict[str, Any]):
        """
        Handle chat message and broadcast to room.
        """
        message_data = {
            'type': 'chat_message',
            'user_id': user_id,
            'message': data.get('message', ''),
            'timestamp': time.time(),
            'message_id': data.get('message_id')
        }

        await self.broadcast_message(chat_room, message_data, sender_id=user_id)

    async def handle_typing_start(self, user_id: str, chat_room: str):
        """
        Handle typing start indicator.
        """
        self.typing_status[chat_room][user_id] = time.time()

        await self.broadcast_message(chat_room, {
            'type': 'typing_start',
            'user_id': user_id,
            'timestamp': time.time()
        }, exclude_user=user_id)

    async def handle_typing_stop(self, user_id: str, chat_room: str):
        """
        Handle typing stop indicator.
        """
        self.typing_status[chat_room].pop(user_id, None)

        await self.broadcast_message(chat_room, {
            'type': 'typing_stop',
            'user_id': user_id,
            'timestamp': time.time()
        }, exclude_user=user_id)

    async def broadcast_message(self, chat_room: str, message: dict[str, Any], sender_id: str = None, exclude_user: str = None):
        """
        Broadcast message to all users in chat room.
        """
        if chat_room not in self.chat_rooms:
            return

        disconnected_users = []

        for user_id in self.chat_rooms[chat_room]:
            if exclude_user and user_id == exclude_user:
                continue

            if user_id in self.active_connections:
                try:
                    await self.send_to_user(user_id, message)
                except Exception as e:
                    logger.warning(f"Failed to send message to {user_id}: {e}")
                    disconnected_users.append(user_id)

        # Clean up disconnected users
        for user_id in disconnected_users:
            await self.disconnect_user(user_id, chat_room)

    async def broadcast_user_event(self, chat_room: str, event: dict[str, Any], exclude_user: str = None):
        """
        Broadcast user event (join/leave) to room.
        """
        await self.broadcast_message(chat_room, event, exclude_user=exclude_user)

    async def send_to_user(self, user_id: str, message: dict[str, Any]):
        """
        Send message to specific user.
        """
        if user_id not in self.active_connections:
            return False

        websocket = self.active_connections[user_id]
        try:
            await websocket.send(json.dumps(message))
            return True
        except Exception as e:
            logger.warning(f"Failed to send to user {user_id}: {e}")
            return False

    async def disconnect_user(self, user_id: str, chat_room: str):
        """
        Handle user disconnection.
        """
        # Remove from connections
        self.active_connections.pop(user_id, None)

        # Remove from chat room
        if chat_room in self.chat_rooms:
            self.chat_rooms[chat_room].discard(user_id)

            # Remove empty rooms
            if not self.chat_rooms[chat_room]:
                del self.chat_rooms[chat_room]

        # Remove typing status
        if chat_room in self.typing_status:
            self.typing_status[chat_room].pop(user_id, None)

        # Remove user status
        self.user_status.pop(user_id, None)

        # Notify other users
        await self.broadcast_user_event(chat_room, {
            'type': 'user_left',
            'user_id': user_id,
            'timestamp': time.time()
        })

    async def notify_file_processing(self, user_id: str, filename: str, status: str, progress: int = None, error: str = None):
        """
        Notify user about file processing status.
        """
        message = {
            'type': 'file_processing',
            'filename': filename,
            'status': status,
            'timestamp': time.time()
        }

        if progress is not None:
            message['progress'] = progress

        if error:
            message['error'] = error

        await self.send_to_user(user_id, message)

    async def notify_ai_response_stream(self, user_id: str, response_chunk: str, is_complete: bool = False):
        """
        Stream AI response chunks to user.
        """
        message = {
            'type': 'ai_response_stream',
            'chunk': response_chunk,
            'is_complete': is_complete,
            'timestamp': time.time()
        }

        await self.send_to_user(user_id, message)

    async def get_room_users(self, chat_room: str) -> list[dict[str, Any]]:
        """
        Get list of users in chat room with their status.
        """
        if chat_room not in self.chat_rooms:
            return []

        users = []
        for user_id in self.chat_rooms[chat_room]:
            user_info = {
                'user_id': user_id,
                'connected': user_id in self.active_connections,
                'typing': user_id in self.typing_status.get(chat_room, {}),
            }

            if user_id in self.user_status:
                user_info.update(self.user_status[user_id])

            users.append(user_info)

        return users

    async def get_statistics(self) -> dict[str, Any]:
        """
        Get WebSocket handler statistics.
        """
        total_connections = len(self.active_connections)
        total_rooms = len(self.chat_rooms)
        total_typing = sum(len(users) for users in self.typing_status.values())

        return {
            'total_connections': total_connections,
            'total_rooms': total_rooms,
            'total_typing_users': total_typing,
            'rooms': {
                room: len(users) for room, users in self.chat_rooms.items()
            }
        }

    async def _cleanup_expired_typing(self):
        """
        Background task to cleanup expired typing indicators.
        """
        while True:
            try:
                current_time = time.time()
                expired_typing = []

                # Find expired typing indicators (older than 5 seconds)
                for room, users in self.typing_status.items():
                    for user_id, start_time in users.items():
                        if current_time - start_time > 5:
                            expired_typing.append((room, user_id))

                # Remove expired typing indicators
                for room, user_id in expired_typing:
                    self.typing_status[room].pop(user_id, None)
                    await self.broadcast_message(room, {
                        'type': 'typing_stop',
                        'user_id': user_id,
                        'timestamp': current_time,
                        'reason': 'timeout'
                    }, exclude_user=user_id)

                # Sleep for 2 seconds before next cleanup
                await asyncio.sleep(2)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in typing cleanup task: {e}")
                await asyncio.sleep(5)


# Global WebSocket handler instance
_websocket_handler = None

def get_websocket_handler() -> ChatWebSocketHandler:
    """Get or create global WebSocket handler instance."""
    global _websocket_handler
    if _websocket_handler is None:
        _websocket_handler = ChatWebSocketHandler()
    return _websocket_handler

async def cleanup_websocket_handler():
    """Cleanup global WebSocket handler."""
    global _websocket_handler
    if _websocket_handler:
        await _websocket_handler.stop_cleanup_task()
        _websocket_handler = None
