from flask import Flask
from flask_jwt_extended import JWTManager
import routing
import db
from lib import logging_manager
import config_module
import os


def create_app():
	app = Flask(__name__)
	app.config.from_object(config_module.Config())
	app.register_blueprint(routing.router)
	app.add_url_rule("/", endpoint="index")

	""" Custom logs work badly with gunicorn. instead you can use gunicorn logger to stdout """
	# logging_manager.set_logging(
	# 	config_path=app.config["LOGGING_CONFIG"],
	# 	logs_path=app.config["LOGS"]
	# 	)

	if not os.path.exists(app.config["DATABASE"]):
		db.init_db(conf=app.config)
		
	db.init_app(app)

	jwt = JWTManager(app)
	
	return app