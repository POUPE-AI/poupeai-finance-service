import pika
import json
import uuid
import structlog
from datetime import datetime
from django.conf import settings
from pika.exceptions import AMQPConnectionError

log = structlog.get_logger(__name__)

class RabbitMQProducer:
    def __init__(self):
        self.rabbitmq_url = settings.RABBITMQ_URL
        self.exchange_name = settings.RABBITMQ_EXCHANGE_MAIN
        self.routing_key = settings.RABBITMQ_ROUTING_KEY
        self._connection = None
        self._channel = None

    def _connect(self):
        try:
            self._connection = pika.BlockingConnection(pika.URLParameters(self.rabbitmq_url))
            self._channel = self._connection.channel()
            self._channel.exchange_declare(exchange=self.exchange_name, exchange_type='direct', durable=True)
            log.debug("RabbitMQ producer connected successfully.")
        except AMQPConnectionError as e:
            log.error("Failed to connect to RabbitMQ", error=str(e), exc_info=e)
            raise

    def _close(self):
        if self._connection and self._connection.is_open:
            self._connection.close()
            log.debug("RabbitMQ producer connection closed.")

    def publish(self, event_type: str, payload: dict, recipient: dict, correlation_id: str, trigger_type: str = "user_interaction"):
        message_id = str(uuid.uuid4())
        envelope = {
            "message_id": message_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "trigger_type": trigger_type,
            "event_type": event_type,
            "recipient": recipient,
            "payload": payload,
        }
        body = json.dumps(envelope)

        try:
            self._connect()
            properties = pika.BasicProperties(
                correlation_id=correlation_id,
                content_type='application/json',
                delivery_mode=pika.DeliveryMode.Persistent,
                message_id=message_id
            )
            self._channel.basic_publish(
                exchange=self.exchange_name,
                routing_key=self.routing_key,
                body=body,
                properties=properties
            )
            log.info(
                "Event published to RabbitMQ",
                event_type=event_type,
                message_id=message_id,
                correlation_id=correlation_id,
                exchange=self.exchange_name,
                routing_key=self.routing_key,
            )
        except Exception as e:
            log.error(
                "Failed to publish event",
                event_type=event_type,
                correlation_id=correlation_id,
                error=str(e),
                exc_info=e
            )
            raise
        finally:
            self._close()

rabbitmq_producer = RabbitMQProducer()