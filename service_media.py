import json
import time
import pika
from common.rpc_utils import build_connection

QUEUE_NAME = "service.media"

def handle_request(ch, method, props, body):
    try:
        payload = json.loads(body.decode())
        params = payload.get("params", {})
        numbers = params.get("numbers", [])
        print(f"[service_media] calculando média de {numbers} (corr_id={props.correlation_id})")
        time.sleep(1.5)
        if not numbers:
            raise ValueError("lista vazia")
        result = sum(numbers) / len(numbers)
        response = json.dumps({"result": result})
    except Exception as e:
        response = json.dumps({"error": str(e)})

    ch.basic_publish(
        exchange="",
        routing_key=props.reply_to,
        properties=pika.BasicProperties(correlation_id=props.correlation_id),
        body=response,
    )
    ch.basic_ack(delivery_tag=method.delivery_tag)


def main():
    conn = build_connection()
    ch = conn.channel()
    ch.queue_declare(queue=QUEUE_NAME)
    ch.basic_qos(prefetch_count=1)
    ch.basic_consume(queue=QUEUE_NAME, on_message_callback=handle_request)
    print(f"[service_media] aguardando requisições na fila '{QUEUE_NAME}'")
    try:
        ch.start_consuming()
    except KeyboardInterrupt:
        print("Encerrando service_media...")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
