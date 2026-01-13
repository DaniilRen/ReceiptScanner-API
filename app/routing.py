from flask import abort, Blueprint, request, current_app, send_from_directory, jsonify, make_response, after_this_request

from flask_jwt_extended import create_access_token
from flask_jwt_extended import get_jwt
from flask_jwt_extended import get_jwt_identity
from flask_jwt_extended import jwt_required
from flask_jwt_extended import JWTManager
from flask_jwt_extended import set_access_cookies
from flask_jwt_extended import unset_jwt_cookies

from lib.report import create_pdf
import db
import os
import datetime


router = Blueprint('routing', __name__)

""" Using an `after_request` callback, refresh any token that is within 30 """
@router.after_request
def refresh_expiring_jwts(response):
	try:
		exp_timestamp = get_jwt()["exp"]
		now = datetime.datetime.now(datetime.timezone.utc)
		target_timestamp = datetime.datetime.timestamp(now + datetime.timedelta(minutes=60))
		if target_timestamp > exp_timestamp:
			access_token = create_access_token(identity=get_jwt_identity())
			set_access_cookies(response, access_token)
		return response
	except (RuntimeError, KeyError):
		# Case where there is not a valid JWT. Just return the original response
		return response


""" Auth to get JWT token with password"""
@router.route('/login', methods=("GET", "POST"))
def login():
	username = request.json.get("username", None)
	password = request.json.get("password", None)

	if not db.check_user(username, password):
		return jsonify({'error': 'invalid login data'}), 404

	jwt_token = create_access_token(identity=username)
	# _username_ and _admin_ values
	user_data = dict(db.get_user_data(username))
	return make_response(jsonify({'access_token': jwt_token, 'user_data': user_data}), 200)


""" Index page, does not accept any requests """
@router.route('/', methods=("GET", "POST"))
def index():
	return abort(400)


""" Add item and save image to storage """
@router.route('/add-item', methods=("POST",))
@jwt_required()
def add_item():
	data = request.get_json()
	if not data or 'image' not in data:
		return jsonify({'error': 'some data is missing'}), 404

	response = db.add_item(data)
	if response is None:
		jsonify({'error': 'item already exists or data is corrupted'}), 404
	return '', 204


@router.route('/update-item', methods=("POST",))
@jwt_required()
def update_item():
	data = request.get_json()
	if not data or 'image' not in data:
		return jsonify({'error': 'some data is missing'}), 404

	item_id = data.get('id')
	response = db.update_item(item_id, data)
	if response is None:
		jsonify({'error': 'item already exists or data is corrupted'}), 404
	return '', 204


@router.route('/delete-item/<id>', methods=("DELETE",))
@jwt_required()
def delete_item(id):
	try:
		id = int(id)
		res = db.delete_item(id)
		if res is None:
			raise Exception
		else:
			return '', 204
	except Exception:
		return jsonify({'error': f"Invalid id: {id}"}), 404


""" 
Get item by its id or list of all available items 
id=all - list of all items; 
id=<id:int> - only one item with unique id
"""
@router.route('/item/<id>', methods=("GET",))
@jwt_required()
def get_item(id):
	if str(id) == "all":
		items = db.get_all_items()
		if items is None:
			return jsonify({'error': f"error while loading items"}), 404
		return jsonify([dict(item) for item in items]), 200

	item = db.get_items([id])[0]
	if item is None: 
		return jsonify({'error': f"invalid id: {id}"}), 404
	return jsonify(dict(item)), 200


""" Get item image """
@router.route('/files/<int:id>', methods=("GET",))
@jwt_required()
def download(id):
	item = db.get_items([id])[0]
	if item is None:
		return jsonify({'error': 'invalid id'}), 404
	storage_path = os.path.join(current_app.root_path, current_app.config['FILE_STORAGE'])
	return send_from_directory(storage_path, item["file_name"])


""" Get all available categories """
@router.route('/categories', methods=("GET",))
@jwt_required()
def categories():
	categories = db.get_categories()
	if categories is None:
		return jsonify({'error': 'cannot load categories from database'}), 404 
	return jsonify([dict(category) for category in categories]), 200


@router.route('/delete-category/<id>', methods=("DELETE",))
@jwt_required()
def delete_category(id):
	try:
		id = int(id)
		res = db.delete_category(id)
		if res is None:
			raise Exception
		else:
			return '', 204
	except Exception:
		return jsonify({'error': f"Invalid id: {id}"}), 404


@router.route('/add-category', methods=("POST",))
@jwt_required()
def add_category():
	data = request.get_json()
	if not data:
		return jsonify({'error': 'category data is missing'}), 404

	res = db.add_category(data)
	if res == False:
		return jsonify({'error': 'category already exists'}), 404
	elif res is None:
		return jsonify({'error': 'cannot add category to database because of internal errors'}), 404
	return '', 204


""" Get all users available data """
@router.route('/users', methods=("GET",))
@jwt_required()
def usernames():
	users = db.get_users()
	if users is None:
		return jsonify({'error': 'cannot load usernames from database'}), 404 
	return jsonify([dict(user) for user in users]), 200


@router.route('/delete-user/<username>', methods=("DELETE",))
@jwt_required()
def delete_user(username):
	try:
		res = db.delete_user(username)
		if res is None:
			raise Exception
		else:
			return '', 204
	except Exception:
		return jsonify({'error': f"user does not exist: {username}"}), 404


@router.route('/add-user', methods=("POST",))
@jwt_required()
def add_user():
	data = request.get_json()
	if not data:
		return jsonify({'error': 'user data is missing'}), 404

	res = db.add_user(data)
	if res == False:
		return jsonify({'error': 'user already exists'}), 404
	elif res is None:
		return jsonify({'error': 'cannot add user to database because of internal errors'}), 404
	return '', 204


""" Generate report """
@router.route('/report', methods=("GET",))
@jwt_required()
def report():
	filename = "report " + datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S') + '.pdf'
	items = db.get_items(request.json.get("id_list", None))
	if items is None:
		return jsonify({'error': 'invalid id'}), 404
	resp = create_pdf(
		os.path.join(current_app.root_path, current_app.config['FILE_STORAGE']),
		os.path.join(current_app.root_path, current_app.config['FILE_STORAGE'], filename),
		items
	)
	storage_path = os.path.join(current_app.root_path, current_app.config['FILE_STORAGE'])

	@after_this_request
	def remove_file(response):
		try:
			os.remove(os.path.join(storage_path, filename))
		except Exception as e:
			pass
		return response

	return send_from_directory(storage_path, filename)

