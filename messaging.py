import os
import pika
from typing import Optional

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RPC_GATEWAY_QUEUE = os.getenv("RABBITMQ_GATEWAY_QUEUE", "rpc_gateway")

def build_connection(host: str = RABBITMQ_HOST) -> pika.BlockingConnection:
    params = pika.ConnectionParameters(host=host)
    return pika.BlockingConnection(params)

def configure_channel_for_consume(connection: pika.BlockingConnection, prefetch_count: int = 1) -> pika.channel.Channel:
    ch = connection.channel()
    ch.basic_qos(prefetch_count=prefetch_count)
    return ch

def declare_queue(channel: pika.channel.Channel, queue_name: str, durable: bool = False) -> str:
    channel.queue_declare(queue=queue_name, durable=durable)
    return queue_name

def publish_message(channel: pika.channel.Channel, queue_name: str, message: str, 
                   properties: Optional[pika.BasicProperties] = None):
    channel.basic_publish(
        exchange="",
        routing_key=queue_name,
        body=message,
        properties=properties or pika.BasicProperties()
    )