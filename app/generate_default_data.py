import sqlite3
import config_module
from lib.file_utils import *
from werkzeug.security import generate_password_hash
from random import *
import os
import datetime
import shutil


conf = config_module.Config()


def generate_default_categories(db):
	try:
		for cat in conf.DB_CATEGORIES:
			db.execute(
				"INSERT INTO categories"
				"(category)"
				"VALUES (?)",
				(cat,)
			)
			db.commit()
		print("<== Default categories inserted")
	except sqlite3.IntegrityError:
		print("Skipping generation: Categories table is not empty")


def generate_default_users(db):
	try:
		users = [{"username": f"usr1", "password": generate_password_hash("pasw1"), "admin": False}, {"username": "admin", "password": generate_password_hash("admin"), "admin": True}]
		for req in users:
			db.execute(
				"INSERT INTO users"
				"(username, password, admin)"
				"VALUES (?, ?, ?)",
				(list(req.values()))
			)
			db.commit()
		print("<== Default users inserted")
	except sqlite3.IntegrityError:
		print("Skipping generation: Users table is not empty")


def generate_default_items(db, count=5):
	try:
		# skip generation if table already has default items - needed because item table has no unique fields
		if len(db.execute("SELECT * FROM items").fetchall()) > 0:
			raise sqlite3.IntegrityError

		categories = ["ГСМ топливо", "Товары", "Услуги"]
		dates = ["2025-07-"+f"{day}".zfill(2) for day in range(1, 31)]
		images = ["sample.png" for _ in range(count)]
		items = [
			{"category": choice(categories), "sum": randint(100, 4242), "creation_date": choice(dates), "file_name": images[i]} for i in range(count)
		]
		for item in items:
			db.execute(
				"INSERT INTO items"
				"(category, sum, creation_date, file_name)"
				"VALUES (?, ?, ?, ?)",
				(list(item.values()))
			)
			db.commit()
		print("<== Default items inserted")
	except sqlite3.IntegrityError:
		print("Skipping generation: Item table is not empty")


def generate_defaults():
	db = sqlite3.connect(
		conf.DATABASE, detect_types=sqlite3.PARSE_DECLTYPES
	)
	cur = db.cursor()
	with open(conf.SCHEMA) as schema:
		cur.executescript(schema.read()) 

	generate_default_users(db)
	generate_default_items(db)
	generate_default_categories(db)
	print("Complete !")


if __name__ == "__main__":
	print("This script resets existing database file / creates new one, then fills inserts test data.")

	if os.path.exists(conf.DATABASE):
		confirm = input("Database file exists. Do you want to rewrite it ? (y / n): ").strip().lower()
		try:
			if confirm[0] == 'y':
				os.remove(conf.DATABASE)
				print(f"Removed db file: {conf.DATABASE}")
				generate_defaults()
			else:
				raise Exception
		except Exception:
			print("Cancelling operation")
	else:
		generate_defaults()