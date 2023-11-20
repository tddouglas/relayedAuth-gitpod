import logging

from Adyen.util import is_valid_hmac_notification
from flask import Flask, render_template, send_from_directory, request, abort

from main.sessions import adyen_sessions
from main.config import *


def create_app():
    logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
    logging.getLogger('werkzeug').setLevel(logging.ERROR)

    app = Flask('app')

    # Register 404 handler
    app.register_error_handler(404, page_not_found)

    # Routes:
    @app.route('/')
    def home():
        return render_template('home.html')

    # Process incoming webhook notifications
    @app.route('/api/webhooks/notifications', methods=['POST'])
    def webhook_notifications():
        """
        Receives outcome of each payment
        :return:
        """
        notifications = request.json['notificationItems']
        # fetch first( and only) NotificationRequestItem
        notification = notifications[0]

        if is_valid_hmac_notification(notification['NotificationRequestItem'], get_adyen_hmac_key()):
            # consume event asynchronously
            consume_event(notification)
        else:
            # invalid hmac: do not send [accepted] response
            raise Exception("Invalid HMAC signature")

        return '[accepted]'

    @app.route('/api/webhooks/relayedAuth', methods=['POST'])
    def relayedAuth_notification():
        """
        Receives outcome of each payment
        :return:
        """
        APPROVE = {
            "authorisationDecision": {
                "status": "Authorised"
            },
            "reference": "myBalancePlatformPayment_12345",
            "metadata": {
                "customId": "your-own-custom-field-12345"
            }
        }

        DECLINE = {
            "authorisationDecision": {
                "status": "Refused"
            },
            "reference": "myBalancePlatformPayment_12345",
            "metadata": {
                "customId": "your-own-custom-field-12345"
            }
        }
        relayed_auth = request.get_json()
        print(relayed_auth)

        return APPROVE

    @app.route('/favicon.ico')
    def favicon():
        return send_from_directory(os.path.join(app.root_path, 'static'),
                                   'img/favicon.ico')

    return app


#  process payload asynchronously
def consume_event(notification):
    print(f"consume_event merchantReference: {notification['NotificationRequestItem']['merchantReference']} "
          f"result? {notification['NotificationRequestItem']['success']}")

    # add item to DB, queue or run in a different thread


def page_not_found(error):
    return render_template('error.html'), 404


if __name__ == '__main__':
    web_app = create_app()

    logging.info(f"Running on http://localhost:{get_port()}")
    web_app.run(debug=True, port=get_port(), host='0.0.0.0')
