import threading
import uuid
import json
import sys
import signal
from typing import Optional
import pika

from messaging import build_connection, configure_channel_for_consume, declare_queue, RPC_GATEWAY_QUEUE

SERVICE_QUEUE_PREFIX = "service."

def forward_request_to_service(original_props, body: bytes):
    try:
        payload = json.loads(body.decode())
        service = payload.get("service")
        action = payload.get("action")
        params = payload.get("params", {})

        print(f"[gateway] Encaminhando para serviço '{service}' ação '{action}'")

        if not service:
            response_body = json.dumps({"error": "serviço não especificado"})
            with build_connection() as conn_publish:
                ch_pub = conn_publish.channel()
                ch_pub.basic_publish(
                    exchange="",
                    routing_key=original_props.reply_to,
                    properties=pika.BasicProperties(correlation_id=original_props.correlation_id),
                    body=response_body,
                )
            return

        service_queue = SERVICE_QUEUE_PREFIX + service

        conn_service = build_connection()
        ch_service = conn_service.channel()

        callback_result = ch_service.queue_declare(queue="", exclusive=True)
        callback_queue = callback_result.method.queue

        response_container = {"response": None}
        corr_id = str(uuid.uuid4())

        def on_service_response(_ch, _method, props, body):
            if props.correlation_id == corr_id:
                response_container["response"] = body
                _ch.basic_ack(delivery_tag=_method.delivery_tag)

        ch_service.basic_consume(queue=callback_queue, on_message_callback=on_service_response, auto_ack=False)

        ch_service.basic_publish(
            exchange="",
            routing_key=service_queue,
            properties=pika.BasicProperties(
                reply_to=callback_queue,
                correlation_id=corr_id,
            ),
            body=json.dumps({"action": action, "params": params}),
        )

        import time
        timeout_seconds = 15
        waited = 0.0
        while response_container["response"] is None and waited < timeout_seconds:
            conn_service.process_data_events(time_limit=1)
            waited += 1

        conn_service.close()

        if response_container["response"] is None:
            response_body = json.dumps({"error": f"serviço '{service}' não respondeu (timeout)"})
        else:
            response_body = response_container["response"]

        conn_pub = build_connection()
        ch_pub = conn_pub.channel()
        ch_pub.basic_publish(
            exchange="",
            routing_key=original_props.reply_to,
            properties=pika.BasicProperties(correlation_id=original_props.correlation_id),
            body=response_body,
        )
        conn_pub.close()

    except Exception as exc:
        import traceback
        traceback.print_exc()
        try:
            conn_pub = build_connection()
            ch_pub = conn_pub.channel()
            ch_pub.basic_publish(
                exchange="",
                routing_key=original_props.reply_to,
                properties=pika.BasicProperties(correlation_id=original_props.correlation_id),
                body=json.dumps({"error": str(exc)}),
            )
            conn_pub.close()
        except Exception:
            pass


def on_gateway_request(ch, method, props, body):
    print(f"[gateway] Requisição recebida corr_id={props.correlation_id}")
    t = threading.Thread(target=forward_request_to_service, args=(props, body), daemon=True)
    t.start()
    ch.basic_ack(delivery_tag=method.delivery_tag)


def main():
    connection: Optional[object] = None
    try:
        connection = build_connection()
        channel = configure_channel_for_consume(connection)
        declare_queue(channel, RPC_GATEWAY_QUEUE)
        channel.basic_consume(queue=RPC_GATEWAY_QUEUE, on_message_callback=on_gateway_request)
        print(f"[gateway] Aguardando requisições na fila '{RPC_GATEWAY_QUEUE}' (CTRL+C para sair)")
        signal.signal(signal.SIGINT, lambda *_: sys.exit(0))
        channel.start_consuming()
    except KeyboardInterrupt:
        print("\n[gateway] Encerrando...")
    finally:
        if connection and not connection.is_closed:
            connection.close()


if __name__ == "__main__":
    main()