from flask import g, current_app
from werkzeug.security import check_password_hash, generate_password_hash
import sqlite3
from lib.file_utils import *
import datetime
import json
import shutil


def get_db():
	if "db" not in g:
		g.db = sqlite3.connect(
			current_app.config["DATABASE"], detect_types=sqlite3.PARSE_DECLTYPES
		)
		g.db.row_factory = sqlite3.Row
	return g.db


def close_db(e=None):
	db = g.pop("db", None)
	if db is not None:
		db.close()
	

def get_item_by_id(id):
	try:
		db = get_db()
		return db.execute("SELECT * FROM items WHERE id = ?;", (id,)).fetchone()
	except Exception:
		return None


""" Returns list of item with specific id """
def get_items(id_list: list):
	try:
		db = get_db()
		items = []
		for id in id_list:
			item = get_item_by_id(id)
			if not item is None:
				items.append(item)
		return items
	except Exception:
		return None


def get_all_items():

	db = get_db()
	return db.execute("SELECT * FROM items").fetchall()
	


def add_item(data):
	try:
		db = get_db()
		# image data should be base64 string only
		b64_string = data['image']
		filename = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S') + '.png'
		response = upload_file(b64_string, filename)
		if response is None:
			raise db.IntegrityError("invalid base64 string")
		db.execute(
				"INSERT INTO items"
				"(category, sum, creation_date, file_name)"
				"VALUES (?, ?, ?, ?)",
				(data['category'], data["sum"], data["creation_date"], filename)
			)
		db.commit()
		return True
	except db.IntegrityError:
		return None


""" Encode file to base64 string"""
def encode_base64(file_path):
	with open(file_path, "rb") as f:
		return base64.b64encode(f.read()).decode("utf-8")


def update_item(id, data):
	try:
		current_item = get_item_by_id(id)
		if not current_item:
			return None
		
		db = get_db()
		b64_string = data['image']
		current_filename = current_item['file_name']
		storage_path = os.path.join(current_app.root_path, current_app.config['FILE_STORAGE'])
		old_file_path = os.path.join(storage_path, current_filename)

		if encode_base64(old_file_path) != b64_string:
			if os.path.exists(old_file_path):
				items_with_similar_attachment = check_attachment(id, current_filename)
				if items_with_similar_attachment is None:
					return None
				if len(items_with_similar_attachment) == 1:
					print("> removing old file")
					os.remove(old_file_path)
				else:
					print("> keep item`s image | have same attachment :", len(items_with_similar_attachment))

			filename = f"upd_{id}_{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.png"
			if not upload_file(b64_string, filename):
				print("! Error while uploading new image")
				return None
		else:
			filename = current_filename
		
		db.execute(
			"UPDATE items SET category = ?, sum = ?, creation_date = ?, file_name = ? WHERE id = ?",
			(data['category'], data["sum"], data["creation_date"], filename, id)
		)
		db.commit()
		return True
	except Exception as e:
		print(f"Update error: {e}")
		return None



""" check is there are other items using this photo """
def check_attachment(id: int, filename: str):
	try:	
		db = get_db()
		return list(db.execute(
			"SELECT * FROM items WHERE file_name = ?;",
			(filename,)
			).fetchall())
	except Exception as e:
		return None


def delete_item(id):
	try:
		db = get_db()
		filename = dict(get_items([id])[0])["file_name"]
		items_with_similar_attachment = check_attachment(id, filename)
		if items_with_similar_attachment is None:
			return None
		db.execute("DELETE FROM items WHERE id = ?;", (id,))
		db.commit()
		# if we dont have other items using this file, we remove it
		if len(items_with_similar_attachment) == 1:
			os.remove(path = os.path.join(
				current_app.root_path, 
				current_app.config['FILE_STORAGE'], 
				filename
			))
		return True
	except Exception as e:
		return None


def delete_user(username):
	try:
		db = get_db()
		db.execute("DELETE FROM users WHERE username = ?;", (username,))
		db.commit()
		return True
	except Exception:
		return None


def add_user(data):
	try:
		db = get_db()
		if len(db.execute("SELECT * FROM users WHERE username = ?;", (data['username'].strip(),)).fetchall()) != 0:
			return False
		db.execute(
			"INSERT INTO users"
			"(username, password, admin)"
			"VALUES (?, ?, ?)",
			(data['username'].strip(), generate_password_hash(data['password']), data["admin"])
		)
		db.commit()
		return True
	except db.IntegrityError:
		return None


def get_users():
	try:
		db = get_db()
		return db.execute("SELECT username, admin FROM users").fetchall()
	except Exception as e:
		return None

# get open-to-read user data for login response
def get_user_data(username):
	try:
		db = get_db()
		return db.execute("SELECT * FROM users WHERE username = ?;", (username,)).fetchone()
	except Exception:
		return None



def delete_category(id):
	try:
		db = get_db()
		db.execute("DELETE FROM categories WHERE id = ?;", (id,))
		db.commit()
		return True
	except Exception:
		return None


def add_category(data):
	try:
		db = get_db()
		if len(db.execute("SELECT * FROM categories WHERE category = ?;", (data['category'],)).fetchall()) != 0:
			return False
		db.execute(
			"INSERT INTO categories"
			"(category)"
			"VALUES (?)",
			(data['category'],)
		)
		db.commit()
		return True
	except db.IntegrityError:
		return None


def get_categories():
	try:
		db = get_db()
		return db.execute("SELECT * FROM categories").fetchall()
	except Exception as e:
		return None



""" Check login data """
def check_user(username, password):
	try:
		db = get_db()
		user = dict(db.execute(
			"SELECT * FROM users WHERE username = ?;",
			(username,)
			).fetchone())
		return check_password_hash(user['password'], password)
	except Exception:
		return None
	
		


def init_db(conf):
	os.makedirs(os.path.abspath(conf["FILE_STORAGE"]), exist_ok=True)
	db = sqlite3.connect(
		conf["DATABASE"], detect_types=sqlite3.PARSE_DECLTYPES
	)
	cur = db.cursor()
	with open(conf["SCHEMA"]) as schema:
		cur.executescript(schema.read()) 


def init_app(app):
	app.teardown_appcontext(close_db)
	