import os
import sqlite3
import math
from datetime import datetime, date, timedelta
from flask import (
    Flask, render_template, request, redirect, url_for, flash, session, jsonify, g
)
from werkzeug.security import generate_password_hash, check_password_hash
import functools

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'fittrack_secret_key_super_red_black_2026')
DATABASE = os.path.join(app.root_path, 'fitness.db')

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(exception):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    db = sqlite3.connect(DATABASE)
    cursor = db.cursor()

    # Users Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            age INTEGER DEFAULT 25,
            gender TEXT DEFAULT 'Male',
            height REAL DEFAULT 175,
            weight REAL DEFAULT 70,
            activity_level TEXT DEFAULT 'Moderate',
            goal TEXT DEFAULT 'Weight Loss',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Foods Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS foods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            calories REAL NOT NULL,
            protein REAL NOT NULL,
            carbs REAL NOT NULL,
            fat REAL NOT NULL,
            fiber REAL NOT NULL,
            serving TEXT NOT NULL,
            is_per_item INTEGER DEFAULT 0
        )
    ''')

    # Food Logs Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS food_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            food_id INTEGER NOT NULL,
            food_name TEXT NOT NULL,
            quantity REAL NOT NULL,
            unit TEXT NOT NULL,
            calories REAL NOT NULL,
            protein REAL NOT NULL,
            carbs REAL NOT NULL,
            fat REAL NOT NULL,
            fiber REAL NOT NULL,
            meal_type TEXT NOT NULL,
            date TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    # Recipes Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS recipes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            calories REAL NOT NULL,
            protein REAL NOT NULL,
            carbs REAL NOT NULL,
            fat REAL NOT NULL,
            fiber REAL NOT NULL,
            preparation_time INTEGER NOT NULL,
            difficulty TEXT NOT NULL,
            instructions TEXT NOT NULL,
            ingredients_json TEXT NOT NULL,
            image_url TEXT
        )
    ''')

    # Workout Plans Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS workout_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER DEFAULT 0,
            name TEXT NOT NULL,
            category TEXT DEFAULT 'Custom',
            tagline TEXT NOT NULL,
            description TEXT NOT NULL,
            experience_level TEXT DEFAULT 'Intermediate',
            location TEXT DEFAULT 'Home + Gym',
            equipment_json TEXT,
            is_active INTEGER DEFAULT 1,
            is_saved INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Workout Days Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS workout_days (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plan_id INTEGER NOT NULL,
            day_name TEXT NOT NULL,
            day_number INTEGER NOT NULL,
            day_type TEXT DEFAULT 'Workout',
            workout_name TEXT NOT NULL,
            muscle_groups TEXT NOT NULL,
            FOREIGN KEY (plan_id) REFERENCES workout_plans (id) ON DELETE CASCADE
        )
    ''')

    # Workout Exercises Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS workout_exercises (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            workout_day_id INTEGER NOT NULL,
            exercise_name TEXT NOT NULL,
            sets INTEGER NOT NULL,
            reps TEXT NOT NULL,
            rest_seconds INTEGER DEFAULT 90,
            duration_seconds INTEGER DEFAULT 0,
            calories_burned REAL DEFAULT 50.0,
            instructions TEXT,
            notes TEXT,
            order_idx INTEGER DEFAULT 0,
            FOREIGN KEY (workout_day_id) REFERENCES workout_days (id) ON DELETE CASCADE
        )
    ''')

    # Master Exercise Catalog Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS master_exercises (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            category TEXT NOT NULL,
            muscle_group TEXT NOT NULL,
            equipment TEXT NOT NULL,
            location TEXT DEFAULT 'Home + Gym',
            difficulty TEXT DEFAULT 'Beginner',
            default_sets INTEGER DEFAULT 3,
            default_reps TEXT DEFAULT '10 reps',
            default_rest INTEGER DEFAULT 60,
            cals_per_min REAL DEFAULT 8.0,
            instructions TEXT
        )
    ''')

    # User Workout Preferences Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_workout_preferences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            experience TEXT DEFAULT 'Beginner',
            location TEXT DEFAULT 'Home',
            equipment_json TEXT DEFAULT '["No Equipment"]',
            workout_days_json TEXT DEFAULT '["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"]',
            duration_minutes INTEGER DEFAULT 30,
            preferred_exercises TEXT,
            avoid_exercises TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    # Workout Progress Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS workout_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            workout_day_id INTEGER NOT NULL,
            exercise_id INTEGER,
            completed INTEGER DEFAULT 0,
            date TEXT NOT NULL,
            completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    # Legacy Workouts Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS workouts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            difficulty TEXT NOT NULL,
            duration INTEGER NOT NULL,
            description TEXT
        )
    ''')

    # Workout Logs Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS workout_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            workout_id INTEGER,
            workout_name TEXT NOT NULL,
            date TEXT NOT NULL,
            duration_minutes INTEGER NOT NULL,
            calories_burned REAL NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    # Schema Column Check Migrations
    cursor.execute("PRAGMA table_info(workout_days)")
    day_cols = [row[1] for row in cursor.fetchall()]
    if 'day_type' not in day_cols:
        cursor.execute("ALTER TABLE workout_days ADD COLUMN day_type TEXT DEFAULT 'Workout'")

    cursor.execute("PRAGMA table_info(workout_exercises)")
    ex_cols = [row[1] for row in cursor.fetchall()]
    if 'duration_seconds' not in ex_cols:
        cursor.execute("ALTER TABLE workout_exercises ADD COLUMN duration_seconds INTEGER DEFAULT 0")
    if 'calories_burned' not in ex_cols:
        cursor.execute("ALTER TABLE workout_exercises ADD COLUMN calories_burned REAL DEFAULT 50.0")
    if 'instructions' not in ex_cols:
        cursor.execute("ALTER TABLE workout_exercises ADD COLUMN instructions TEXT")
    if 'notes' not in ex_cols:
        cursor.execute("ALTER TABLE workout_exercises ADD COLUMN notes TEXT")
    if 'order_idx' not in ex_cols:
        cursor.execute("ALTER TABLE workout_exercises ADD COLUMN order_idx INTEGER DEFAULT 0")

    cursor.execute("PRAGMA table_info(workout_plans)")
    plan_cols = [row[1] for row in cursor.fetchall()]
    if 'user_id' not in plan_cols:
        cursor.execute("ALTER TABLE workout_plans ADD COLUMN user_id INTEGER DEFAULT 0")
    if 'category' not in plan_cols:
        cursor.execute("ALTER TABLE workout_plans ADD COLUMN category TEXT DEFAULT 'Custom'")
    if 'experience_level' not in plan_cols:
        cursor.execute("ALTER TABLE workout_plans ADD COLUMN experience_level TEXT DEFAULT 'Intermediate'")
    if 'location' not in plan_cols:
        cursor.execute("ALTER TABLE workout_plans ADD COLUMN location TEXT DEFAULT 'Home + Gym'")
    if 'equipment_json' not in plan_cols:
        cursor.execute("ALTER TABLE workout_plans ADD COLUMN equipment_json TEXT")
    if 'is_active' not in plan_cols:
        cursor.execute("ALTER TABLE workout_plans ADD COLUMN is_active INTEGER DEFAULT 1")
    if 'is_saved' not in plan_cols:
        cursor.execute("ALTER TABLE workout_plans ADD COLUMN is_saved INTEGER DEFAULT 1")

    # Weight Logs Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS weight_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            weight REAL NOT NULL,
            date TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    # Water Logs Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS water_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            date TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    db.commit()

    # Seed Default Foods if Empty
    cursor.execute('SELECT COUNT(*) FROM foods')
    if cursor.fetchone()[0] == 0:
        default_foods = [
            ('Egg', 'High Protein', 70, 6.0, 0.6, 5.0, 0.0, '1 Large Egg', 1),
            ('Chicken Breast', 'High Protein', 165, 31.0, 0.0, 3.6, 0.0, '100 g', 0),
            ('Paneer', 'High Protein', 265, 18.0, 3.4, 20.0, 0.0, '100 g', 0),
            ('Greek Yogurt', 'High Protein', 59, 10.0, 3.6, 0.4, 0.0, '100 g', 0),
            ('Oats', 'High Fiber', 389, 16.9, 66.0, 6.9, 10.6, '100 g', 0),
            ('Chia Seeds', 'High Fiber', 486, 16.5, 42.0, 30.7, 34.4, '100 g', 0),
            ('Lentils', 'High Protein', 116, 9.0, 20.0, 0.4, 7.9, '100 g', 0),
            ('Chickpeas', 'High Fiber', 164, 8.9, 27.0, 2.6, 7.6, '100 g', 0),
            ('Almonds', 'Healthy Fats', 579, 21.0, 21.6, 49.9, 12.5, '100 g', 0),
            ('Walnuts', 'Healthy Fats', 654, 15.2, 13.7, 65.2, 6.7, '100 g', 0),
            ('Peanut Butter', 'Healthy Fats', 588, 25.0, 20.0, 50.0, 6.0, '100 g', 0),
            ('Avocado', 'Healthy Fats', 160, 2.0, 8.5, 15.0, 6.7, '100 g', 0),
            ('Banana', 'Fruits', 89, 1.1, 23.0, 0.3, 2.6, '1 Medium Banana', 1),
            ('Apple', 'Fruits', 52, 0.3, 14.0, 0.2, 2.4, '1 Medium Apple', 1),
            ('Brown Rice', 'Carbohydrates', 111, 2.6, 23.0, 0.9, 1.8, '100 g cooked', 0),
            ('Sweet Potato', 'Carbohydrates', 86, 1.6, 20.0, 0.1, 3.0, '100 g', 0)
        ]
        cursor.executemany('''
            INSERT INTO foods (name, category, calories, protein, carbs, fat, fiber, serving, is_per_item)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', default_foods)
        db.commit()

    # Seed Default Recipes if Empty
    cursor.execute('SELECT COUNT(*) FROM recipes')
    if cursor.fetchone()[0] == 0:
        default_recipes = [
            ('High Protein Omelette', 'High Protein', 320, 26, 4, 22, 1.5, 12, 'Easy', 
             '1. Beat 3 large eggs with pinch of salt and black pepper.\n2. Heat skillet with olive oil.\n3. Add diced bell peppers, spinach, and grated paneer.\n4. Cook until golden and serve hot.',
             '[{"food":"Egg","qty":3,"unit":"item"},{"food":"Paneer","qty":30,"unit":"g"}]',
             'https://images.unsplash.com/photo-1525351484163-7529414344d8?w=500&auto=format&fit=crop'),
            ('Chicken Rice Bowl', 'Muscle Gain', 540, 48, 52, 10, 5.0, 25, 'Medium', 
             '1. Season chicken breast with paprika, garlic powder, and olive oil.\n2. Grill chicken for 6-8 mins per side until done.\n3. Serve over steaming brown rice with steamed veggies.',
             '[{"food":"Chicken Breast","qty":200,"unit":"g"},{"food":"Brown Rice","qty":200,"unit":"g"}]',
             'https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=500&auto=format&fit=crop'),
            ('Paneer Protein Bowl', 'High Protein', 420, 28, 24, 24, 6.0, 20, 'Easy', 
             '1. Cube paneer and sauté with spices.\n2. Mix cooked lentils, diced cucumber, and tomatoes.\n3. Top with sautéed paneer and fresh lemon dressing.',
             '[{"food":"Paneer","qty":120,"unit":"g"},{"food":"Lentils","qty":150,"unit":"g"}]',
             'https://images.unsplash.com/photo-1512621776951-a57141f2eefd?w=500&auto=format&fit=crop'),
            ('Greek Yogurt Oat Bowl', 'Breakfast', 360, 24, 48, 6, 8.0, 10, 'Easy', 
             '1. Mix Greek yogurt with raw oats.\n2. Add sliced banana, chia seeds, and honey.\n3. Serve fresh or chill for 30 minutes.',
             '[{"food":"Greek Yogurt","qty":150,"unit":"g"},{"food":"Oats","qty":40,"unit":"g"},{"food":"Banana","qty":1,"unit":"item"}]',
             'https://images.unsplash.com/photo-1488477181946-6428a0291777?w=500&auto=format&fit=crop'),
            ('Overnight Chia Oats', 'High Fiber', 380, 16, 54, 12, 14.0, 5, 'Easy', 
             '1. In a glass jar, mix oats, chia seeds, almond milk, and peanut butter.\n2. Seal jar and refrigerate overnight.\n3. Top with sliced apple before eating.',
             '[{"food":"Oats","qty":50,"unit":"g"},{"food":"Chia Seeds","qty":15,"unit":"g"},{"food":"Peanut Butter","qty":15,"unit":"g"}]',
             'https://images.unsplash.com/photo-1517673400267-0251440c45dc?w=500&auto=format&fit=crop'),
            ('Chickpea Salad', 'Weight Loss', 290, 14, 38, 7, 11.0, 15, 'Easy', 
             '1. Rinse boiled chickpeas.\n2. Toss with chopped cucumber, avocado, lemon juice, and cilantro.\n3. Season with black pepper and cumin powder.',
             '[{"food":"Chickpeas","qty":150,"unit":"g"},{"food":"Avocado","qty":50,"unit":"g"}]',
             'https://images.unsplash.com/photo-1540420773420-3366772f4999?w=500&auto=format&fit=crop')
        ]
        cursor.executemany('''
            INSERT INTO recipes (name, category, calories, protein, carbs, fat, fiber, preparation_time, difficulty, instructions, ingredients_json, image_url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', default_recipes)
        db.commit()

    # Seed 3 Workout Plans if empty
    cursor.execute('SELECT COUNT(*) FROM workout_plans')
    if cursor.fetchone()[0] == 0:
        seed_workout_plans(cursor, db)
    else:
        cursor.execute("UPDATE workout_plans SET tagline = 'PUSH / PULL SPLIT' WHERE id = 1")
        cursor.execute("UPDATE workout_plans SET tagline = 'SINGLE MUSCLE SPLIT' WHERE id = 2")
        cursor.execute("UPDATE workout_plans SET tagline = 'DOUBLE MUSCLE SPLIT' WHERE id = 3")
        db.commit()

def seed_workout_plans(cursor, db):
    plans = [
        (1, 'Push / Pull Split', 'PUSH / PULL SPLIT', 'A weekly workout plan alternating between Push and Pull workouts.'),
        (2, 'Single Muscle Split', 'SINGLE MUSCLE SPLIT', 'Only ONE major muscle group is trained each day.'),
        (3, 'Double Muscle Split', 'DOUBLE MUSCLE SPLIT', 'Two muscle groups are trained together each day.')
    ]
    cursor.executemany('INSERT INTO workout_plans (id, name, tagline, description) VALUES (?, ?, ?, ?)', plans)

    # --- PLAN 1: PUSH / PULL SPLIT ---
    p1_days = [
        (1, 1, 'Monday', 1, 'PUSH', 'Chest + Shoulders + Triceps'),
        (2, 1, 'Tuesday', 2, 'PULL', 'Back + Biceps'),
        (3, 1, 'Wednesday', 3, 'PUSH', 'Chest + Shoulders + Triceps'),
        (4, 1, 'Thursday', 4, 'PULL', 'Back + Biceps'),
        (5, 1, 'Friday', 5, 'PUSH', 'Chest + Shoulders + Triceps'),
        (6, 1, 'Saturday', 6, 'PULL', 'Back + Biceps'),
        (7, 1, 'Sunday', 7, 'REST / RECOVERY', 'Rest & Recovery')
    ]
    cursor.executemany('INSERT INTO workout_days (id, plan_id, day_name, day_number, workout_name, muscle_groups) VALUES (?, ?, ?, ?, ?, ?)', p1_days)

    p1_ex = [
        # Monday Push
        (1, 'Barbell Bench Press', 4, '8–12 reps', 90),
        (1, 'Incline Dumbbell Press', 3, '10 reps', 90),
        (1, 'Shoulder Press', 3, '10 reps', 90),
        (1, 'Dumbbell Lateral Raise', 3, '12–15 reps', 60),
        (1, 'Tricep Pushdown', 3, '12 reps', 60),
        (1, 'Overhead Tricep Extension', 3, '10 reps', 60),
        # Tuesday Pull
        (2, 'Lat Pulldown', 4, '10 reps', 90),
        (2, 'Barbell Row', 4, '8–10 reps', 90),
        (2, 'Seated Cable Row', 3, '10 reps', 90),
        (2, 'Face Pull', 3, '15 reps', 60),
        (2, 'Barbell Curl', 3, '10 reps', 60),
        (2, 'Hammer Curl', 3, '12 reps', 60),
        # Wednesday Push
        (3, 'Incline Barbell Bench Press', 4, '8–10 reps', 90),
        (3, 'Dumbbell Bench Press', 3, '10 reps', 90),
        (3, 'Arnold Press', 3, '10 reps', 90),
        (3, 'Cable Lateral Raise', 3, '12–15 reps', 60),
        (3, 'Skull Crushers', 3, '10 reps', 60),
        (3, 'Rope Tricep Pushdown', 3, '12 reps', 60),
        # Thursday Pull
        (4, 'Pull-Ups / Assisted Pull-Ups', 4, '8–12 reps', 90),
        (4, 'One-Arm Dumbbell Row', 3, '10 reps', 90),
        (4, 'Close-Grip Lat Pulldown', 3, '10 reps', 90),
        (4, 'Rear Delt Fly', 3, '15 reps', 60),
        (4, 'Dumbbell Curl', 3, '10 reps', 60),
        (4, 'Preacher Curl', 3, '12 reps', 60),
        # Friday Push
        (5, 'Flat Dumbbell Press', 4, '10 reps', 90),
        (5, 'Incline Dumbbell Press', 3, '10 reps', 90),
        (5, 'Machine Shoulder Press', 3, '10 reps', 90),
        (5, 'Dumbbell Lateral Raise', 3, '15 reps', 60),
        (5, 'Dips / Assisted Dips', 3, '10 reps', 60),
        (5, 'Cable Tricep Extension', 3, '12 reps', 60),
        # Saturday Pull
        (6, 'Deadlift', 3, '6–8 reps', 120),
        (6, 'Lat Pulldown', 3, '10 reps', 90),
        (6, 'Seated Cable Row', 3, '10 reps', 90),
        (6, 'Straight-Arm Pulldown', 3, '12 reps', 60),
        (6, 'EZ-Bar Curl', 3, '10 reps', 60),
        (6, 'Hammer Curl', 3, '12 reps', 60),
        # Sunday Rest
        (7, 'Light Stretching / Yoga', 1, '20 mins', 0),
        (7, 'Foam Rolling', 1, '15 mins', 0)
    ]
    cursor.executemany('INSERT INTO workout_exercises (workout_day_id, exercise_name, sets, reps, rest_seconds) VALUES (?, ?, ?, ?, ?)', p1_ex)

    # --- PLAN 2: SINGLE MUSCLE SPLIT ---
    p2_days = [
        (8, 2, 'Monday', 1, 'CHEST', 'Chest'),
        (9, 2, 'Tuesday', 2, 'BACK', 'Back'),
        (10, 2, 'Wednesday', 3, 'SHOULDERS', 'Shoulders'),
        (11, 2, 'Thursday', 4, 'LEGS', 'Legs'),
        (12, 2, 'Friday', 5, 'BICEPS', 'Biceps'),
        (13, 2, 'Saturday', 6, 'TRICEPS', 'Triceps'),
        (14, 2, 'Sunday', 7, 'REST / RECOVERY', 'Rest & Recovery')
    ]
    cursor.executemany('INSERT INTO workout_days (id, plan_id, day_name, day_number, workout_name, muscle_groups) VALUES (?, ?, ?, ?, ?, ?)', p2_days)

    p2_ex = [
        # Monday Chest
        (8, 'Barbell Bench Press', 4, '8–12 reps', 90),
        (8, 'Incline Dumbbell Press', 4, '10 reps', 90),
        (8, 'Machine Chest Press', 3, '10 reps', 90),
        (8, 'Cable Fly', 3, '12 reps', 60),
        (8, 'Pec Deck', 3, '12–15 reps', 60),
        # Tuesday Back
        (9, 'Lat Pulldown', 4, '10 reps', 90),
        (9, 'Barbell Row', 4, '8–10 reps', 90),
        (9, 'Seated Cable Row', 3, '10 reps', 90),
        (9, 'One-Arm Dumbbell Row', 3, '10 reps', 90),
        (9, 'Straight-Arm Pulldown', 3, '12 reps', 60),
        # Wednesday Shoulders
        (10, 'Overhead Press', 4, '8–10 reps', 90),
        (10, 'Dumbbell Shoulder Press', 3, '10 reps', 90),
        (10, 'Lateral Raise', 4, '12–15 reps', 60),
        (10, 'Rear Delt Fly', 3, '15 reps', 60),
        (10, 'Face Pull', 3, '15 reps', 60),
        # Thursday Legs
        (11, 'Barbell Squat', 4, '8–10 reps', 120),
        (11, 'Leg Press', 3, '10 reps', 90),
        (11, 'Romanian Deadlift', 3, '10 reps', 90),
        (11, 'Leg Extension', 3, '12 reps', 60),
        (11, 'Leg Curl', 3, '12 reps', 60),
        (11, 'Standing Calf Raise', 4, '15 reps', 60),
        # Friday Biceps
        (12, 'Barbell Curl', 4, '10 reps', 60),
        (12, 'Incline Dumbbell Curl', 3, '10 reps', 60),
        (12, 'Hammer Curl', 3, '12 reps', 60),
        (12, 'Preacher Curl', 3, '12 reps', 60),
        (12, 'Cable Curl', 3, '12 reps', 60),
        # Saturday Triceps
        (13, 'Close-Grip Bench Press', 4, '8–10 reps', 90),
        (13, 'Tricep Pushdown', 3, '12 reps', 60),
        (13, 'Overhead Tricep Extension', 3, '10 reps', 60),
        (13, 'Skull Crushers', 3, '10 reps', 60),
        (13, 'Bench Dips / Assisted Dips', 3, '12 reps', 60),
        # Sunday Rest
        (14, 'Light Mobility & Stretching', 1, '20 mins', 0)
    ]
    cursor.executemany('INSERT INTO workout_exercises (workout_day_id, exercise_name, sets, reps, rest_seconds) VALUES (?, ?, ?, ?, ?)', p2_ex)

    # --- PLAN 3: DOUBLE MUSCLE SPLIT ---
    p3_days = [
        (15, 3, 'Monday', 1, 'CHEST + TRICEPS', 'Chest + Triceps'),
        (16, 3, 'Tuesday', 2, 'BACK + BICEPS', 'Back + Biceps'),
        (17, 3, 'Wednesday', 3, 'SHOULDERS + ABS', 'Shoulders + Abs'),
        (18, 3, 'Thursday', 4, 'LEGS + CALVES', 'Legs + Calves'),
        (19, 3, 'Friday', 5, 'CHEST + SHOULDERS', 'Chest + Shoulders'),
        (20, 3, 'Saturday', 6, 'BICEPS + TRICEPS', 'Biceps + Triceps'),
        (21, 3, 'Sunday', 7, 'REST / RECOVERY', 'Rest & Recovery')
    ]
    cursor.executemany('INSERT INTO workout_days (id, plan_id, day_name, day_number, workout_name, muscle_groups) VALUES (?, ?, ?, ?, ?, ?)', p3_days)

    p3_ex = [
        # Monday Chest + Triceps
        (15, 'Barbell Bench Press', 4, '8–12 reps', 90),
        (15, 'Incline Dumbbell Press', 3, '10 reps', 90),
        (15, 'Cable Fly', 3, '12 reps', 60),
        (15, 'Tricep Pushdown', 3, '12 reps', 60),
        (15, 'Overhead Tricep Extension', 3, '10 reps', 60),
        (15, 'Skull Crushers', 3, '10 reps', 60),
        # Tuesday Back + Biceps
        (16, 'Lat Pulldown', 4, '10 reps', 90),
        (16, 'Barbell Row', 3, '8–10 reps', 90),
        (16, 'Seated Cable Row', 3, '10 reps', 90),
        (16, 'Barbell Curl', 3, '10 reps', 60),
        (16, 'Hammer Curl', 3, '12 reps', 60),
        (16, 'Preacher Curl', 3, '12 reps', 60),
        # Wednesday Shoulders + Abs
        (17, 'Overhead Press', 4, '8–10 reps', 90),
        (17, 'Dumbbell Lateral Raise', 4, '12–15 reps', 60),
        (17, 'Rear Delt Fly', 3, '15 reps', 60),
        (17, 'Face Pull', 3, '15 reps', 60),
        (17, 'Crunches', 3, '15 reps', 45),
        (17, 'Leg Raises', 3, '12 reps', 45),
        (17, 'Plank', 3, '30–60 seconds', 45),
        # Thursday Legs + Calves
        (18, 'Barbell Squat', 4, '8–10 reps', 120),
        (18, 'Leg Press', 3, '10 reps', 90),
        (18, 'Romanian Deadlift', 3, '10 reps', 90),
        (18, 'Leg Extension', 3, '12 reps', 60),
        (18, 'Leg Curl', 3, '12 reps', 60),
        (18, 'Standing Calf Raise', 4, '15 reps', 45),
        (18, 'Seated Calf Raise', 3, '15 reps', 45),
        # Friday Chest + Shoulders
        (19, 'Incline Bench Press', 4, '8–10 reps', 90),
        (19, 'Dumbbell Bench Press', 3, '10 reps', 90),
        (19, 'Cable Fly', 3, '12 reps', 60),
        (19, 'Shoulder Press', 3, '10 reps', 90),
        (19, 'Lateral Raise', 3, '15 reps', 60),
        (19, 'Rear Delt Fly', 3, '15 reps', 60),
        # Saturday Biceps + Triceps
        (20, 'Barbell Curl', 4, '10 reps', 60),
        (20, 'Incline Dumbbell Curl', 3, '10 reps', 60),
        (20, 'Hammer Curl', 3, '12 reps', 60),
        (20, 'Close-Grip Bench Press', 3, '8–10 reps', 90),
        (20, 'Tricep Pushdown', 3, '12 reps', 60),
        (20, 'Overhead Tricep Extension', 3, '12 reps', 60),
        # Sunday Rest
        (21, 'Full Body Foam Rolling & Stretch', 1, '20 mins', 0)
    ]
    db.commit()

    db.close()

# Initialize DB on start
init_db()

# Target Calculator Helpers
def calculate_user_targets(user):
    if not user:
        return {
            'bmr': 1600, 'tdee': 2200, 'calorie_target': 2000, 
            'protein_target': 140, 'fiber_target': 30, 'fat_target': 65, 
            'carbs_target': 220, 'water_target': 3.0, 'bmi': 22.5
        }
    w = float(user['weight'] or 70)
    h = float(user['height'] or 175)
    a = int(user['age'] or 25)
    gender = user['gender'] or 'Male'
    act = user['activity_level'] or 'Moderate'
    goal = user['goal'] or 'Weight Loss'

    # Mifflin-St Jeor Equation
    if gender.lower() == 'female':
        bmr = 10 * w + 6.25 * h - 5 * a - 161
    else:
        bmr = 10 * w + 6.25 * h - 5 * a + 5

    act_multipliers = {
        'Sedentary': 1.2,
        'Light': 1.375,
        'Moderate': 1.55,
        'Active': 1.725
    }
    tdee = bmr * act_multipliers.get(act, 1.55)

    if goal == 'Weight Loss':
        calorie_target = tdee - 500
        protein_multiplier = 2.2
    elif goal == 'Muscle Gain':
        calorie_target = tdee + 350
        protein_multiplier = 2.0
    elif goal == 'Strength':
        calorie_target = tdee + 200
        protein_multiplier = 2.2
    else: # Maintain Weight
        calorie_target = tdee
        protein_multiplier = 1.8

    calorie_target = round(max(calorie_target, 1200))
    protein_target = round(w * protein_multiplier)
    fiber_target = 30
    fat_target = round((calorie_target * 0.25) / 9)
    carbs_target = round((calorie_target - (protein_target * 4 + fat_target * 9)) / 4)
    water_target = 3.0 # Liters

    bmi = round(w / ((h / 100) ** 2), 1)

    return {
        'bmr': round(bmr),
        'tdee': round(tdee),
        'calorie_target': calorie_target,
        'protein_target': protein_target,
        'fiber_target': fiber_target,
        'fat_target': fat_target,
        'carbs_target': max(carbs_target, 50),
        'water_target': water_target,
        'bmi': bmi
    }

# Auth Decorator
def login_required(f):
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Dynamic AI Recommendation Engine
def generate_ai_recommendation(totals, targets):
    cal_pct = (totals['calories'] / targets['calorie_target']) * 100 if targets['calorie_target'] else 0
    prot_pct = (totals['protein'] / targets['protein_target']) * 100 if targets['protein_target'] else 0
    fib_pct = (totals['fiber'] / targets['fiber_target']) * 100 if targets['fiber_target'] else 0
    fat_pct = (totals['fat'] / targets['fat_target']) * 100 if targets['fat_target'] else 0

    recs = []
    if prot_pct < 60:
        recs.append("Your protein intake is below target today. Try adding Greek yogurt, eggs, chicken breast, or paneer to your next meal.")
    elif prot_pct >= 100:
        recs.append("Great job hitting your protein goal! Keep staying hydrated to support optimal recovery.")

    if fib_pct < 50:
        recs.append("Your fiber intake is low today. Consider adding oats, chia seeds, lentils, or fresh apples.")

    if cal_pct > 105:
        recs.append("You have exceeded your daily calorie target. Focus on light salads or green tea for the rest of the day.")
    elif cal_pct < 40 and totals['calories'] > 0:
        recs.append("You're currently under-fueled. Ensure you consume adequate complex carbs and healthy fats for sustained energy.")
    
    if not recs:
        recs.append("Your nutrition macro balance is looking solid today! Maintain your current hydration and stay active.")

    return recs[0]

# --- ROUTES ---

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        age = request.form.get('age', 25, type=int)
        gender = request.form.get('gender', 'Male')
        height = request.form.get('height', 175.0, type=float)
        weight = request.form.get('weight', 70.0, type=float)
        activity_level = request.form.get('activity_level', 'Moderate')
        goal = request.form.get('goal', 'Weight Loss')

        if not name or not email or not password:
            flash('Name, email, and password are required.', 'danger')
            return render_template('register.html')

        db = get_db()
        cursor = db.cursor()
        cursor.execute('SELECT id FROM users WHERE email = ?', (email,))
        if cursor.fetchone():
            flash('Email is already registered. Please login.', 'danger')
            return render_template('register.html')

        hashed_pw = generate_password_hash(password)
        cursor.execute('''
            INSERT INTO users (name, email, password, age, gender, height, weight, activity_level, goal)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (name, email, hashed_pw, age, gender, height, weight, activity_level, goal))
        db.commit()
        new_id = cursor.lastrowid

        # Initial weight log
        today_str = date.today().isoformat()
        cursor.execute('INSERT INTO weight_logs (user_id, weight, date) VALUES (?, ?, ?)', (new_id, weight, today_str))
        db.commit()

        session['user_id'] = new_id
        session['user_name'] = name
        flash('Account created successfully! Welcome to FitTrack AI.', 'success')
        return redirect(url_for('dashboard'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        db = get_db()
        cursor = db.cursor()
        cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
        user = cursor.fetchone()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            flash('Logged in successfully.', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password.', 'danger')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],))
    user = cursor.fetchone()

    targets = calculate_user_targets(user)
    today_str = date.today().isoformat()

    # Get Today's Food Logs
    cursor.execute('SELECT * FROM food_logs WHERE user_id = ? AND date = ?', (session['user_id'], today_str))
    logs = cursor.fetchall()

    totals = {'calories': 0, 'protein': 0, 'carbs': 0, 'fat': 0, 'fiber': 0}
    meals = {'Breakfast': [], 'Lunch': [], 'Snack': [], 'Dinner': []}

    for log in logs:
        totals['calories'] += log['calories']
        totals['protein'] += log['protein']
        totals['carbs'] += log['carbs']
        totals['fat'] += log['fat']
        totals['fiber'] += log['fiber']
        if log['meal_type'] in meals:
            meals[log['meal_type']].append(log)

    for k in totals:
        totals[k] = round(totals[k], 1)

    # Get Today's Water
    cursor.execute('SELECT SUM(amount) FROM water_logs WHERE user_id = ? AND date = ?', (session['user_id'], today_str))
    water_row = cursor.fetchone()
    water_today = round(water_row[0] or 0.0, 2)

    # Get Today's Workout Log
    cursor.execute('SELECT * FROM workout_logs WHERE user_id = ? AND date = ? ORDER BY id DESC LIMIT 1', (session['user_id'], today_str))
    today_workout = cursor.fetchone()

    # Generate Smart Recommendation
    ai_recommendation = generate_ai_recommendation(totals, targets)

    return render_template(
        'dashboard.html',
        user=user,
        targets=targets,
        totals=totals,
        meals=meals,
        water_today=water_today,
        today_workout=today_workout,
        ai_recommendation=ai_recommendation,
        today_str=today_str
    )

@app.route('/food')
@login_required
def food_explorer():
    db = get_db()
    cursor = db.cursor()
    
    cat = request.args.get('category', 'All')
    q = request.args.get('q', '').strip().lower()

    sql = 'SELECT * FROM foods'
    params = []
    conditions = []

    if cat and cat != 'All':
        conditions.append('category = ?')
        params.append(cat)

    if q:
        conditions.append('LOWER(name) LIKE ?')
        params.append(f'%{q}%')

    if conditions:
        sql += ' WHERE ' + ' AND '.join(conditions)

    sql += ' ORDER BY name ASC'
    cursor.execute(sql, params)
    foods = cursor.fetchall()

    # Fetch today's food log for view
    today_str = date.today().isoformat()
    cursor.execute('SELECT * FROM food_logs WHERE user_id = ? AND date = ? ORDER BY id DESC', (session['user_id'], today_str))
    today_logs = cursor.fetchall()

    return render_template('food.html', foods=foods, selected_category=cat, search_query=q, today_logs=today_logs)

@app.route('/api/log-food', methods=['POST'])
@login_required
def api_log_food():
    food_id = request.form.get('food_id', type=int)
    quantity = request.form.get('quantity', 100.0, type=float)
    meal_type = request.form.get('meal_type', 'Breakfast')
    log_date = request.form.get('date', date.today().isoformat())

    if not food_id or quantity <= 0:
        return jsonify({'success': False, 'message': 'Invalid food or quantity.'}), 400

    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM foods WHERE id = ?', (food_id,))
    food = cursor.fetchone()

    if not food:
        return jsonify({'success': False, 'message': 'Food not found.'}), 440

    if food['is_per_item'] == 1:
        multiplier = quantity
        unit = 'item(s)'
    else:
        multiplier = quantity / 100.0
        unit = 'g'

    cal = round(food['calories'] * multiplier, 1)
    prot = round(food['protein'] * multiplier, 1)
    carbs = round(food['carbs'] * multiplier, 1)
    fat = round(food['fat'] * multiplier, 1)
    fiber = round(food['fiber'] * multiplier, 1)

    cursor.execute('''
        INSERT INTO food_logs (user_id, food_id, food_name, quantity, unit, calories, protein, carbs, fat, fiber, meal_type, date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (session['user_id'], food['id'], food['name'], quantity, unit, cal, prot, carbs, fat, fiber, meal_type, log_date))
    db.commit()

    return jsonify({
        'success': True,
        'message': f'Added {food["name"]} to {meal_type}!',
        'log': {
            'food_name': food['name'],
            'calories': cal,
            'protein': prot,
            'meal_type': meal_type
        }
    })

@app.route('/api/delete-food-log', methods=['POST'])
@login_required
def api_delete_food_log():
    log_id = request.form.get('log_id', type=int)
    db = get_db()
    cursor = db.cursor()
    cursor.execute('DELETE FROM food_logs WHERE id = ? AND user_id = ?', (log_id, session['user_id']))
    db.commit()

    return jsonify({'success': True, 'message': 'Food log deleted successfully.'})

@app.route('/recipes')
@login_required
def recipes():
    db = get_db()
    cursor = db.cursor()
    cat = request.args.get('category', 'All')

    if cat and cat != 'All':
        cursor.execute('SELECT * FROM recipes WHERE category = ? ORDER BY id DESC', (cat,))
    else:
        cursor.execute('SELECT * FROM recipes ORDER BY id DESC')
    
    recipes_list = [dict(r) for r in cursor.fetchall()]
    return render_template('recipes.html', recipes=recipes_list, selected_category=cat)

@app.route('/api/add-recipe', methods=['POST'])
@login_required
def api_add_recipe():
    name = request.form.get('name', '').strip()
    category = request.form.get('category', 'High Protein')
    calories = request.form.get('calories', 0.0, type=float)
    protein = request.form.get('protein', 0.0, type=float)
    carbs = request.form.get('carbs', 0.0, type=float)
    fat = request.form.get('fat', 0.0, type=float)
    fiber = request.form.get('fiber', 0.0, type=float)
    prep_time = request.form.get('preparation_time', 15, type=int)
    difficulty = request.form.get('difficulty', 'Easy')
    instructions = request.form.get('instructions', '').strip()
    image_url = request.form.get('image_url', '').strip() or 'https://images.unsplash.com/photo-1498837167922-ddd27525d352?w=500&auto=format&fit=crop'

    if not name or not instructions:
        return jsonify({'success': False, 'message': 'Recipe name and instructions are required.'}), 400

    db = get_db()
    cursor = db.cursor()
    cursor.execute('''
        INSERT INTO recipes (name, category, calories, protein, carbs, fat, fiber, preparation_time, difficulty, instructions, ingredients_json, image_url)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '[]', ?)
    ''', (name, category, calories, protein, carbs, fat, fiber, prep_time, difficulty, instructions, image_url))
    db.commit()

    return jsonify({'success': True, 'message': f'Recipe "{name}" added successfully!'})

@app.route('/api/edit-recipe', methods=['POST'])
@login_required
def api_edit_recipe():
    recipe_id = request.form.get('recipe_id', type=int)
    name = request.form.get('name', '').strip()
    category = request.form.get('category', 'High Protein')
    calories = request.form.get('calories', 0.0, type=float)
    protein = request.form.get('protein', 0.0, type=float)
    carbs = request.form.get('carbs', 0.0, type=float)
    fat = request.form.get('fat', 0.0, type=float)
    fiber = request.form.get('fiber', 0.0, type=float)
    prep_time = request.form.get('preparation_time', 15, type=int)
    difficulty = request.form.get('difficulty', 'Easy')
    instructions = request.form.get('instructions', '').strip()
    image_url = request.form.get('image_url', '').strip()

    if not recipe_id or not name or not instructions:
        return jsonify({'success': False, 'message': 'Recipe ID, name, and instructions are required.'}), 400

    db = get_db()
    cursor = db.cursor()

    if image_url:
        cursor.execute('''
            UPDATE recipes SET name = ?, category = ?, calories = ?, protein = ?, carbs = ?, fat = ?, fiber = ?, preparation_time = ?, difficulty = ?, instructions = ?, image_url = ?
            WHERE id = ?
        ''', (name, category, calories, protein, carbs, fat, fiber, prep_time, difficulty, instructions, image_url, recipe_id))
    else:
        cursor.execute('''
            UPDATE recipes SET name = ?, category = ?, calories = ?, protein = ?, carbs = ?, fat = ?, fiber = ?, preparation_time = ?, difficulty = ?, instructions = ?
            WHERE id = ?
        ''', (name, category, calories, protein, carbs, fat, fiber, prep_time, difficulty, instructions, recipe_id))
    
    db.commit()

    return jsonify({'success': True, 'message': f'Recipe "{name}" updated successfully!'})

@app.route('/api/delete-recipe', methods=['POST'])
@login_required
def api_delete_recipe():
    recipe_id = request.form.get('recipe_id', type=int)
    if not recipe_id:
        return jsonify({'success': False, 'message': 'Invalid recipe ID.'}), 400

    db = get_db()
    cursor = db.cursor()
    cursor.execute('DELETE FROM recipes WHERE id = ?', (recipe_id,))
    db.commit()

    return jsonify({'success': True, 'message': 'Recipe deleted successfully.'})

@app.route('/workout')
@app.route('/workout-planner')
@login_required
def workout():
    db = get_db()
    cursor = db.cursor()
    user_id = session['user_id']
    
    cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    user = dict(cursor.fetchone() or {})
    
    # 1. Fetch available plans for user (including shared plans)
    cursor.execute('SELECT * FROM workout_plans WHERE user_id = ? OR user_id = 0 ORDER BY is_active DESC, id DESC', (user_id,))
    plans = [dict(p) for p in cursor.fetchall()]
    
    selected_plan_id = request.args.get('plan_id', type=int)
    if selected_plan_id:
        cursor.execute('SELECT * FROM workout_plans WHERE id = ? AND (user_id = ? OR user_id = 0)', (selected_plan_id, user_id))
        active_plan_row = cursor.fetchone()
        active_plan = dict(active_plan_row) if active_plan_row else (plans[0] if plans else None)
    else:
        active_plan = plans[0] if plans else None
        selected_plan_id = active_plan['id'] if active_plan else 1

    # 2. Fetch days for active plan
    days_data = []
    total_week_exercises = 0
    completed_week_exercises = 0
    today_str = date.today().isoformat()
    today_day_number = datetime.today().isoweekday()

    if active_plan:
        cursor.execute('SELECT * FROM workout_days WHERE plan_id = ? ORDER BY day_number ASC', (active_plan['id'],))
        days_list = [dict(d) for d in cursor.fetchall()]

        for d in days_list:
            cursor.execute('SELECT * FROM workout_exercises WHERE workout_day_id = ? ORDER BY order_idx ASC, id ASC', (d['id'],))
            exercises = [dict(ex) for ex in cursor.fetchall()]
            
            cursor.execute('''
                SELECT exercise_id FROM workout_progress 
                WHERE user_id = ? AND workout_day_id = ? AND date = ? AND completed = 1
            ''', (user_id, d['id'], today_str))
            completed_ex_ids = set(row[0] for row in cursor.fetchall() if row[0])

            for ex in exercises:
                ex['completed'] = 1 if ex['id'] in completed_ex_ids else 0
                total_week_exercises += 1
                if ex['completed']:
                    completed_week_exercises += 1

            cursor.execute('''
                SELECT COUNT(*) FROM workout_progress 
                WHERE user_id = ? AND workout_day_id = ? AND date = ? AND exercise_id IS NULL AND completed = 1
            ''', (user_id, d['id'], today_str))
            day_completed = cursor.fetchone()[0] > 0

            days_data.append({
                'info': d,
                'exercises': exercises,
                'completed': day_completed,
                'is_today': (d['day_number'] == today_day_number)
            })

    weekly_pct = round((completed_week_exercises / total_week_exercises * 100)) if total_week_exercises > 0 else 0

    cursor.execute('SELECT DISTINCT date FROM workout_logs WHERE user_id = ? ORDER BY date DESC', (user_id,))
    log_dates = [row[0] for row in cursor.fetchall()]
    
    streak = 0
    check_date = date.today()
    while check_date.isoformat() in log_dates or (check_date == date.today() and (check_date - timedelta(days=1)).isoformat() in log_dates):
        if check_date.isoformat() in log_dates:
            streak += 1
            check_date -= timedelta(days=1)
        elif check_date == date.today():
            check_date -= timedelta(days=1)
        else:
            break

    cursor.execute('SELECT * FROM workout_logs WHERE user_id = ? ORDER BY id DESC LIMIT 10', (user_id,))
    history = [dict(h) for h in cursor.fetchall()]

    # Fetch master exercise catalog for select dropdowns
    cursor.execute('SELECT * FROM master_exercises ORDER BY category ASC, name ASC')
    master_ex = [dict(ex) for ex in cursor.fetchall()]

    # Fetch user workout preferences
    cursor.execute('SELECT * FROM user_workout_preferences WHERE user_id = ?', (user_id,))
    pref_row = cursor.fetchone()
    preferences = dict(pref_row) if pref_row else {
        'experience': 'Beginner',
        'location': 'Home',
        'equipment_json': '["No Equipment"]',
        'duration_minutes': 30
    }

    return render_template(
        'workout.html',
        user=user,
        plans=plans,
        active_plan=active_plan,
        days_data=days_data,
        weekly_pct=weekly_pct,
        completed_count=completed_week_exercises,
        total_count=total_week_exercises,
        streak=streak,
        history=history,
        master_exercises=master_ex,
        preferences=preferences,
        today_day_number=today_day_number
    )

@app.route('/my-workouts')
@login_required
def my_workouts():
    db = get_db()
    cursor = db.cursor()
    user_id = session['user_id']
    cursor.execute('SELECT * FROM workout_plans WHERE user_id = ? OR user_id = 0 ORDER BY id DESC', (user_id,))
    plans = [dict(p) for p in cursor.fetchall()]
    return render_template('my_workouts.html', plans=plans)

@app.route('/workout-history')
@login_required
def workout_history():
    db = get_db()
    cursor = db.cursor()
    user_id = session['user_id']
    cursor.execute('SELECT * FROM workout_logs WHERE user_id = ? ORDER BY id DESC', (user_id,))
    history = [dict(h) for h in cursor.fetchall()]
    return render_template('workout_history.html', history=history)

@app.route('/api/workout/select-category', methods=['POST'])
@login_required
def api_workout_select_category():
    user_id = session['user_id']
    category = request.form.get('category', 'Weight Loss').strip()
    
    db = get_db()
    cursor = db.cursor()

    # Look for existing plan in this category for user
    cursor.execute('SELECT id FROM workout_plans WHERE (user_id = ? OR user_id = 0) AND category = ? LIMIT 1', (user_id, category))
    row = cursor.fetchone()
    
    if row:
        plan_id = row['id']
        cursor.execute('UPDATE workout_plans SET is_active = 0 WHERE user_id = ?', (user_id,))
        cursor.execute('UPDATE workout_plans SET is_active = 1 WHERE id = ?', (plan_id,))
        db.commit()
        return jsonify({'success': True, 'plan_id': plan_id, 'message': f'Switched to {category} workout plan!'})

    # Otherwise create default category plan
    cursor.execute('UPDATE workout_plans SET is_active = 0 WHERE user_id = ?', (user_id,))
    cursor.execute('''
        INSERT INTO workout_plans (user_id, name, category, tagline, description, is_active, is_saved)
        VALUES (?, ?, ?, ?, ?, 1, 1)
    ''', (user_id, f'{category} Program', category, f'{category.upper()} FOCUS', f'Structured program focused on {category}.'))
    plan_id = cursor.lastrowid

    # Create 7 default days for this category
    days_def = [
        ('Monday', 1, 'Workout', f'{category} Day 1', 'Full Body'),
        ('Tuesday', 2, 'Workout', f'{category} Day 2', 'Core & Stamina'),
        ('Wednesday', 3, 'Workout', f'{category} Day 3', 'Upper Body'),
        ('Thursday', 4, 'Workout', f'{category} Day 4', 'Lower Body'),
        ('Friday', 5, 'Workout', f'{category} Day 5', 'HIIT Circuit'),
        ('Saturday', 6, 'Workout', f'{category} Day 6', 'Challenge Day'),
        ('Sunday', 7, 'Rest', 'Rest & Recovery', 'Rest')
    ]
    for name, num, dtype, wname, muscle in days_def:
        cursor.execute('''
            INSERT INTO workout_days (plan_id, day_name, day_number, day_type, workout_name, muscle_groups)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (plan_id, name, num, dtype, wname, muscle))
        day_id = cursor.lastrowid
        if dtype == 'Workout':
            # Add sample exercises matching category from master_exercises
            cursor.execute('SELECT name, default_sets, default_reps, default_rest FROM master_exercises WHERE category = ? LIMIT 3', (category,))
            sampled_ex = cursor.fetchall()
            if not sampled_ex:
                cursor.execute('SELECT name, default_sets, default_reps, default_rest FROM master_exercises LIMIT 3')
                sampled_ex = cursor.fetchall()
            
            for ex_name, ex_sets, ex_reps, ex_rest in sampled_ex:
                cursor.execute('''
                    INSERT INTO workout_exercises (workout_day_id, exercise_name, sets, reps, rest_seconds)
                    VALUES (?, ?, ?, ?, ?)
                ''', (day_id, ex_name, ex_sets, ex_reps, ex_rest))

    db.commit()
    return jsonify({'success': True, 'plan_id': plan_id, 'message': f'Created new {category} workout plan!'})

@app.route('/api/workout/get-replacements', methods=['POST'])
@login_required
def api_workout_get_replacements():
    payload = request.get_json(silent=True) or request.form
    target_muscle = (payload.get('target_muscle') or 'Full Body').strip()
    current_name = (payload.get('exercise_name') or '').strip()
    
    db = get_db()
    cursor = db.cursor()

    cursor.execute('''
        SELECT * FROM master_exercises 
        WHERE name != ? AND (muscle_group LIKE ? OR category LIKE ?)
        ORDER BY id ASC LIMIT 10
    ''', (current_name, f"%{target_muscle}%", f"%{target_muscle}%"))
    
    reps = [dict(r) for r in cursor.fetchall()]
    if not reps:
        cursor.execute('SELECT * FROM master_exercises WHERE name != ? LIMIT 10', (current_name,))
        reps = [dict(r) for r in cursor.fetchall()]

    return jsonify({'success': True, 'replacements': reps})

@app.route('/api/workout/replace-exercise', methods=['POST'])
@login_required
def api_workout_replace_exercise():
    exercise_id = request.form.get('exercise_id', type=int)
    new_name = request.form.get('new_exercise_name', '').strip()
    sets = request.form.get('sets', 3, type=int)
    reps = request.form.get('reps', '10 reps').strip()
    rest_seconds = request.form.get('rest_seconds', 60, type=int)

    if not exercise_id or not new_name:
        return jsonify({'success': False, 'message': 'Invalid exercise replacement parameters.'}), 400

    db = get_db()
    cursor = db.cursor()
    cursor.execute('''
        UPDATE workout_exercises 
        SET exercise_name = ?, sets = ?, reps = ?, rest_seconds = ?
        WHERE id = ?
    ''', (new_name, sets, reps, rest_seconds, exercise_id))
    db.commit()

    return jsonify({'success': True, 'message': f'Swapped exercise to "{new_name}"!'})

@app.route('/api/workout/edit-day', methods=['POST'])
@login_required
def api_workout_edit_day():
    day_id = request.form.get('day_id', type=int)
    day_type = request.form.get('day_type', 'Workout').strip()
    workout_name = request.form.get('workout_name', '').strip()
    target_muscle = request.form.get('muscle_groups', '').strip()

    if not day_id or not workout_name:
        return jsonify({'success': False, 'message': 'Day ID and workout title are required.'}), 400

    db = get_db()
    cursor = db.cursor()
    cursor.execute('''
        UPDATE workout_days 
        SET day_type = ?, workout_name = ?, muscle_groups = ?
        WHERE id = ?
    ''', (day_type, workout_name, target_muscle, day_id))
    db.commit()

    return jsonify({'success': True, 'message': 'Updated day configuration successfully.'})

@app.route('/api/workout/generate-ai-plan', methods=['POST'])
@login_required
def api_workout_generate_ai_plan():
    user_id = session['user_id']
    payload = request.get_json(silent=True) or request.form
    user_prompt = (payload.get('prompt') or payload.get('message') or '').strip()

    if not user_prompt:
        return jsonify({'success': False, 'message': 'Please enter a description for your AI workout plan.'}), 400

    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    user = dict(cursor.fetchone() or {})

    gemini_key = os.environ.get('GEMINI_API_KEY')
    if gemini_key:
        try:
            from google import genai
            client = genai.Client(api_key=gemini_key)
            prompt = f"""
You are an expert AI Strength & Conditioning Coach.
Create a personalized 7-day weekly workout plan (Monday to Sunday) based on this request:
"{user_prompt}"

User Context:
- Age: {user.get('age', 25)}, Gender: {user.get('gender', 'Male')}, Weight: {user.get('weight', 70)}kg, Height: {user.get('height', 175)}cm, Goal: {user.get('goal', 'Fitness')}

Return ONLY valid JSON matching this exact structure:
{{
  "title": "Custom AI Workout Plan",
  "category": "Personalized",
  "tagline": "AI GENERATED",
  "description": "Tailored plan generated based on your specifications.",
  "days": [
    {{
      "day_name": "Monday",
      "day_number": 1,
      "day_type": "Workout",
      "workout_name": "Upper Body Push",
      "muscle_groups": "Chest & Shoulders",
      "exercises": [
        {{"name": "Push-ups", "sets": 3, "reps": "12 reps", "rest_seconds": 60, "instructions": "Keep core tight."}}
      ]
    }}
  ]
}}
"""
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt
            )
            raw_text = response.text.strip()
            if raw_text.startswith("```"):
                raw_text = raw_text.split("\n", 1)[1]
                if raw_text.endswith("```"):
                    raw_text = raw_text.rsplit("```", 1)[0]
                raw_text = raw_text.strip()

            import json
            plan_data = json.loads(raw_text)

            cursor.execute('UPDATE workout_plans SET is_active = 0 WHERE user_id = ?', (user_id,))
            cursor.execute('''
                INSERT INTO workout_plans (user_id, name, category, tagline, description, is_active, is_saved)
                VALUES (?, ?, ?, ?, ?, 1, 1)
            ''', (user_id, plan_data.get('title', 'AI Workout Plan'), plan_data.get('category', 'Personalized'), plan_data.get('tagline', 'AI GENERATED'), plan_data.get('description', 'Custom AI Plan')))
            plan_id = cursor.lastrowid

            for day_idx, d in enumerate(plan_data.get('days', [])):
                cursor.execute('''
                    INSERT INTO workout_days (plan_id, day_name, day_number, day_type, workout_name, muscle_groups)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (plan_id, d.get('day_name', f'Day {day_idx+1}'), day_idx + 1, d.get('day_type', 'Workout'), d.get('workout_name', 'Workout'), d.get('muscle_groups', 'Full Body')))
                day_id = cursor.lastrowid

                for ex_idx, ex in enumerate(d.get('exercises', [])):
                    cursor.execute('''
                        INSERT INTO workout_exercises (workout_day_id, exercise_name, sets, reps, rest_seconds, instructions, order_idx)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (day_id, ex.get('name', 'Exercise'), ex.get('sets', 3), str(ex.get('reps', '10 reps')), ex.get('rest_seconds', 60), ex.get('instructions', ''), ex_idx))

            db.commit()
            return jsonify({'success': True, 'message': '✨ AI Workout Plan generated & activated successfully!', 'plan_id': plan_id})
        except Exception as e:
            print("Gemini AI Workout Plan Generator Warning:", str(e))

    # Rule-Based Fallback
    cursor.execute('UPDATE workout_plans SET is_active = 0 WHERE user_id = ?', (user_id,))
    cursor.execute('''
        INSERT INTO workout_plans (user_id, name, category, tagline, description, is_active, is_saved)
        VALUES (?, 'Custom Tailored Plan', 'Personalized', 'SMART PLAN', 'Plan generated based on your requirements.', 1, 1)
    ''', (user_id,))
    plan_id = cursor.lastrowid

    default_days = [
        ('Monday', 1, 'Workout', 'Upper Body Power', 'Chest & Back'),
        ('Tuesday', 2, 'Workout', 'Lower Body & Core', 'Legs & Abs'),
        ('Wednesday', 3, 'Active Recovery', 'Stretching & Mobility', 'Recovery'),
        ('Thursday', 4, 'Workout', 'Push Focus', 'Chest & Shoulders'),
        ('Friday', 5, 'Workout', 'Pull Focus', 'Back & Biceps'),
        ('Saturday', 6, 'Workout', 'Cardio & Abs', 'Full Body'),
        ('Sunday', 7, 'Rest', 'Rest Day', 'Rest')
    ]
    for name, num, dtype, wname, muscle in default_days:
        cursor.execute('''
            INSERT INTO workout_days (plan_id, day_name, day_number, day_type, workout_name, muscle_groups)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (plan_id, name, num, dtype, wname, muscle))
        day_id = cursor.lastrowid
        if dtype == 'Workout':
            cursor.execute('''
                INSERT INTO workout_exercises (workout_day_id, exercise_name, sets, reps, rest_seconds, instructions)
                VALUES (?, 'Push-ups', 3, '12 reps', 60, 'Keep core engaged.')
            ''', (day_id,))
            cursor.execute('''
                INSERT INTO workout_exercises (workout_day_id, exercise_name, sets, reps, rest_seconds, instructions)
                VALUES (?, 'Squats', 3, '15 reps', 60, 'Squat to parallel.')
            ''', (day_id,))

    db.commit()
    return jsonify({'success': True, 'message': 'Generated customized workout plan!', 'plan_id': plan_id})

@app.route('/api/workout-toggle-exercise', methods=['POST'])
@login_required
def api_workout_toggle_exercise():
    workout_day_id = request.form.get('workout_day_id', type=int)
    exercise_id = request.form.get('exercise_id', type=int)
    completed = request.form.get('completed', 0, type=int)
    today_str = date.today().isoformat()

    if not workout_day_id or not exercise_id:
        return jsonify({'success': False, 'message': 'Invalid parameters.'}), 400

    db = get_db()
    cursor = db.cursor()
    
    if completed == 1:
        cursor.execute('''
            INSERT INTO workout_progress (user_id, workout_day_id, exercise_id, completed, date)
            VALUES (?, ?, ?, 1, ?)
        ''', (session['user_id'], workout_day_id, exercise_id, today_str))
    else:
        cursor.execute('''
            DELETE FROM workout_progress 
            WHERE user_id = ? AND workout_day_id = ? AND exercise_id = ? AND date = ?
        ''', (session['user_id'], workout_day_id, exercise_id, today_str))

    db.commit()
    return jsonify({'success': True, 'completed': completed})

@app.route('/api/workout-complete-day', methods=['POST'])
@login_required
def api_workout_complete_day():
    workout_day_id = request.form.get('workout_day_id', type=int)
    workout_name = request.form.get('workout_name', 'Workout Routine')
    today_str = date.today().isoformat()

    if not workout_day_id:
        return jsonify({'success': False, 'message': 'Invalid workout day ID.'}), 400

    db = get_db()
    cursor = db.cursor()

    cursor.execute('''
        INSERT INTO workout_progress (user_id, workout_day_id, exercise_id, completed, date)
        VALUES (?, ?, NULL, 1, ?)
    ''', (session['user_id'], workout_day_id, today_str))

    cursor.execute('''
        INSERT INTO workout_logs (user_id, workout_id, workout_name, date, duration_minutes, calories_burned)
        VALUES (?, ?, ?, ?, 45, 320.0)
    ''', (session['user_id'], workout_day_id, workout_name, today_str))

    db.commit()
    return jsonify({'success': True, 'message': f'🎉 "{workout_name}" marked complete for today!'})

@app.route('/api/add-workout-exercise', methods=['POST'])
@login_required
def api_add_workout_exercise():
    workout_day_id = request.form.get('workout_day_id', type=int)
    exercise_name = request.form.get('exercise_name', '').strip()
    sets = request.form.get('sets', 3, type=int)
    reps = request.form.get('reps', '10 reps').strip()
    rest_seconds = request.form.get('rest_seconds', 90, type=int)

    if not workout_day_id or not exercise_name:
        return jsonify({'success': False, 'message': 'Exercise name is required.'}), 400

    db = get_db()
    cursor = db.cursor()
    cursor.execute('''
        INSERT INTO workout_exercises (workout_day_id, exercise_name, sets, reps, rest_seconds)
        VALUES (?, ?, ?, ?, ?)
    ''', (workout_day_id, exercise_name, sets, reps, rest_seconds))
    db.commit()

    return jsonify({'success': True, 'message': f'Exercise "{exercise_name}" added successfully!'})

@app.route('/api/edit-workout-exercise', methods=['POST'])
@login_required
def api_edit_workout_exercise():
    exercise_id = request.form.get('exercise_id', type=int)
    exercise_name = request.form.get('exercise_name', '').strip()
    sets = request.form.get('sets', 3, type=int)
    reps = request.form.get('reps', '10 reps').strip()
    rest_seconds = request.form.get('rest_seconds', 90, type=int)

    if not exercise_id or not exercise_name:
        return jsonify({'success': False, 'message': 'Exercise ID and name are required.'}), 400

    db = get_db()
    cursor = db.cursor()
    cursor.execute('''
        UPDATE workout_exercises SET exercise_name = ?, sets = ?, reps = ?, rest_seconds = ?
        WHERE id = ?
    ''', (exercise_name, sets, reps, rest_seconds, exercise_id))
    db.commit()

    return jsonify({'success': True, 'message': f'Exercise "{exercise_name}" updated successfully!'})

@app.route('/api/delete-workout-exercise', methods=['POST'])
@login_required
def api_delete_workout_exercise():
    exercise_id = request.form.get('exercise_id', type=int)
    if not exercise_id:
        return jsonify({'success': False, 'message': 'Invalid exercise ID.'}), 400

    db = get_db()
    cursor = db.cursor()
    cursor.execute('DELETE FROM workout_exercises WHERE id = ?', (exercise_id,))
    db.commit()

    return jsonify({'success': True, 'message': 'Exercise deleted successfully.'})

@app.route('/api/log-workout', methods=['POST'])
@login_required
def api_log_workout():
    workout_id = request.form.get('workout_id', type=int)
    duration = request.form.get('duration', 30, type=int)
    workout_name = request.form.get('workout_name', 'Custom Workout')
    
    # Estimate burned calories (~ 7-10 kcal per minute depending on duration)
    calories_burned = round(duration * 8.5)
    today_str = date.today().isoformat()

    db = get_db()
    cursor = db.cursor()
    cursor.execute('''
        INSERT INTO workout_logs (user_id, workout_id, workout_name, date, duration_minutes, calories_burned)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (session['user_id'], workout_id, workout_name, today_str, duration, calories_burned))
    db.commit()

    return jsonify({
        'success': True,
        'message': f'Workout "{workout_name}" saved successfully! 🔥 {calories_burned} kcal burned.',
        'calories_burned': calories_burned,
        'duration': duration
    })

@app.route('/progress')
@login_required
def progress():
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],))
    user = cursor.fetchone()
    targets = calculate_user_targets(user)

    # Weight history
    cursor.execute('SELECT * FROM weight_logs WHERE user_id = ? ORDER BY date ASC', (session['user_id'],))
    weight_logs = cursor.fetchall()

    start_weight = weight_logs[0]['weight'] if weight_logs else user['weight']
    current_weight = weight_logs[-1]['weight'] if weight_logs else user['weight']
    weight_change = round(current_weight - start_weight, 1)

    return render_template(
        'progress.html',
        user=user,
        targets=targets,
        start_weight=start_weight,
        current_weight=current_weight,
        weight_change=weight_change
    )

@app.route('/api/progress-data')
@login_required
def api_progress_data():
    db = get_db()
    cursor = db.cursor()
    uid = session['user_id']

    # Last 7 Days dates
    today = date.today()
    dates = [(today - timedelta(days=i)).isoformat() for i in range(6, -1, -1)]

    weight_data = []
    calorie_data = []
    protein_data = []
    workout_data = []

    for d in dates:
        # Weight
        cursor.execute('SELECT weight FROM weight_logs WHERE user_id = ? AND date <= ? ORDER BY date DESC LIMIT 1', (uid, d))
        w = cursor.fetchone()
        weight_data.append(w['weight'] if w else None)

        # Calories & Protein
        cursor.execute('SELECT SUM(calories), SUM(protein) FROM food_logs WHERE user_id = ? AND date = ?', (uid, d))
        f = cursor.fetchone()
        calorie_data.append(round(f[0] or 0.0, 1))
        protein_data.append(round(f[1] or 0.0, 1))

        # Workout minutes
        cursor.execute('SELECT SUM(duration_minutes) FROM workout_logs WHERE user_id = ? AND date = ?', (uid, d))
        wr = cursor.fetchone()
        workout_data.append(wr[0] or 0)

    # Format labels (e.g. "Mon 09", "Tue 10")
    formatted_dates = [datetime.strptime(d, '%Y-%m-%d').strftime('%b %d') for d in dates]

    return jsonify({
        'labels': formatted_dates,
        'weight': weight_data,
        'calories': calorie_data,
        'protein': protein_data,
        'workouts': workout_data
    })

@app.route('/api/log-weight', methods=['POST'])
@login_required
def api_log_weight():
    weight = request.form.get('weight', type=float)
    if not weight or weight <= 0:
        return jsonify({'success': False, 'message': 'Invalid weight value.'}), 400

    today_str = date.today().isoformat()
    db = get_db()
    cursor = db.cursor()
    cursor.execute('INSERT INTO weight_logs (user_id, weight, date) VALUES (?, ?, ?)', (session['user_id'], weight, today_str))
    cursor.execute('UPDATE users SET weight = ? WHERE id = ?', (weight, session['user_id']))
    db.commit()

    return jsonify({'success': True, 'message': f'Updated current weight to {weight} kg.'})

@app.route('/water')
@login_required
def water():
    db = get_db()
    cursor = db.cursor()
    today_str = date.today().isoformat()
    
    cursor.execute('SELECT SUM(amount) FROM water_logs WHERE user_id = ? AND date = ?', (session['user_id'], today_str))
    water_row = cursor.fetchone()
    water_today = round(water_row[0] or 0.0, 2)

    cursor.execute('SELECT * FROM water_logs WHERE user_id = ? AND date = ? ORDER BY id DESC', (session['user_id'], today_str))
    today_water_logs = cursor.fetchall()

    return render_template('water.html', water_today=water_today, target=3.0, logs=today_water_logs)

@app.route('/api/log-water', methods=['POST'])
@login_required
def api_log_water():
    amount = request.form.get('amount', 0.25, type=float) # In liters
    if amount <= 0:
        return jsonify({'success': False, 'message': 'Invalid water amount.'}), 400

    today_str = date.today().isoformat()
    db = get_db()
    cursor = db.cursor()
    cursor.execute('INSERT INTO water_logs (user_id, amount, date) VALUES (?, ?, ?)', (session['user_id'], amount, today_str))
    db.commit()

    cursor.execute('SELECT SUM(amount) FROM water_logs WHERE user_id = ? AND date = ?', (session['user_id'], today_str))
    total_water = round(cursor.fetchone()[0] or 0.0, 2)

    return jsonify({'success': True, 'message': f'Added +{amount * 1000:.0f} ml of water! 💧', 'total': total_water})

@app.route('/ai-coach')
@login_required
def ai_coach():
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],))
    user = cursor.fetchone()
    return render_template('ai_coach.html', user=user)

@app.route('/api/ai-assistant', methods=['POST'])
@app.route('/api/ai-coach', methods=['POST'])
def api_ai_assistant_query():
    payload = request.get_json(silent=True) or {}
    user_message = (payload.get('prompt') or payload.get('message') or payload.get('query') or '').strip()

    # Basic request validation & prevent empty requests
    if not user_message:
        return jsonify({
            'success': False,
            'error': 'Please enter a valid request or question before submitting.',
            'reply': 'Please enter a valid request or question before submitting.'
        }), 400

    # User profile context if logged in
    user = None
    targets = {}
    cals, prot, fib = 0.0, 0.0, 0.0
    if 'user_id' in session:
        try:
            db = get_db()
            cursor = db.cursor()
            cursor.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],))
            user = cursor.fetchone()
            if user:
                targets = calculate_user_targets(user)
                today_str = date.today().isoformat()
                cursor.execute('SELECT SUM(calories), SUM(protein), SUM(fiber) FROM food_logs WHERE user_id = ? AND date = ?', (session['user_id'], today_str))
                totals_row = cursor.fetchone()
                cals = round(totals_row[0] or 0.0, 1)
                prot = round(totals_row[1] or 0.0, 1)
                fib = round(totals_row[2] or 0.0, 1)
        except Exception as e:
            print("User context fetch warning:", str(e))

    # Read GEMINI_API_KEY from environment variable
    gemini_key = os.environ.get('GEMINI_API_KEY')
    if gemini_key:
        try:
            from google import genai
            client = genai.Client(api_key=gemini_key)
            
            profile_context = ""
            if user:
                profile_context = f"""
User Profile Context:
- Name: {user['name']}
- Age: {user['age']}
- Gender: {user['gender']}
- Height: {user['height']} cm
- Weight: {user['weight']} kg
- Goal: {user['goal']}
- Activity Level: {user['activity_level']}
- Daily Targets: {targets.get('calorie_target', 'N/A')} kcal, {targets.get('protein_target', 'N/A')}g protein
- Logged Today: {cals} kcal, {prot}g protein, {fib}g fiber
"""
            else:
                profile_context = "User: Guest User\n"

            system_prompt = f"""
You are FitTrack AI Assistant, an expert AI fitness trainer and certified sports nutritionist.
{profile_context}
User Question/Request: "{user_message}"

Provide a direct, concise, highly actionable, encouraging response tailored to their fitness and nutrition targets. Use clear formatting with bullet points and bold headers where applicable. End with a brief wellness disclaimer.
"""
            # Use Gemini 2.5 Flash model available on free tier
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=system_prompt
            )
            if response and hasattr(response, 'text') and response.text:
                return jsonify({
                    'success': True,
                    'reply': response.text,
                    'response': response.text
                })
            else:
                raise Exception("Empty response received from Gemini API.")
        except Exception as e:
            err_str = str(e)
            print("Gemini API request failed:", err_str)
            
            # Friendly error handling for rate limit or API error
            if '429' in err_str or 'RESOURCE_EXHAUSTED' in err_str or 'quota' in err_str.lower() or 'limit' in err_str.lower():
                return jsonify({
                    'success': False,
                    'error': 'The Google Gemini API free-tier limit or rate limit has been reached. Please wait a few moments and try again.',
                    'reply': 'The Google Gemini API free-tier limit or rate limit has been reached. Please wait a few moments and try again.'
                }), 429
            else:
                return jsonify({
                    'success': False,
                    'error': f'Gemini API request failed: {err_str}',
                    'reply': f'The AI Assistant encountered an issue: {err_str}'
                }), 500

    # Smart Rule-Based Engine Fallback if GEMINI_API_KEY is not configured
    msg_lower = user_message.lower()
    user_name = user['name'] if user else 'there'
    
    if 'protein' in msg_lower:
        reply = f"Hi {user_name}! Great question about protein. Top high-protein sources include chicken breast, eggs, paneer, Greek yogurt, lentils, and whey protein."
    elif 'breakfast' in msg_lower or 'morning' in msg_lower:
        reply = f"Hi {user_name}! A high-protein breakfast idea: Greek yogurt bowl with oats, banana, chia seeds, and berries."
    elif 'workout' in msg_lower or 'exercise' in msg_lower:
        reply = f"Hi {user_name}! Aim for 3-4 sets of compound exercises (squats, bench press/push-ups, lunges) with 60-90s rest."
    else:
        reply = f"Hello {user_name}! Your AI request has been received. Configure `GEMINI_API_KEY` in `.env` to enable live Gemini AI generation."

    reply += "\n\n*(Note: Set GEMINI_API_KEY in .env to connect live Gemini 2.5 Flash model)*"
    return jsonify({'success': True, 'reply': reply, 'response': reply})

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    db = get_db()
    cursor = db.cursor()

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        age = request.form.get('age', type=int)
        gender = request.form.get('gender')
        height = request.form.get('height', type=float)
        weight = request.form.get('weight', type=float)
        activity_level = request.form.get('activity_level')
        goal = request.form.get('goal')

        cursor.execute('''
            UPDATE users SET name = ?, age = ?, gender = ?, height = ?, weight = ?, activity_level = ?, goal = ?
            WHERE id = ?
        ''', (name, age, gender, height, weight, activity_level, goal, session['user_id']))
        db.commit()

        # Update session name
        session['user_name'] = name

        # Also add a new weight entry if weight changed
        today_str = date.today().isoformat()
        cursor.execute('INSERT INTO weight_logs (user_id, weight, date) VALUES (?, ?, ?)', (session['user_id'], weight, today_str))
        db.commit()

        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile'))

    cursor.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],))
    user = cursor.fetchone()
    targets = calculate_user_targets(user)

    return render_template('profile.html', user=user, targets=targets)

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    db = get_db()
    cursor = db.cursor()

    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'change_password':
            old_pw = request.form.get('old_password')
            new_pw = request.form.get('new_password')

            cursor.execute('SELECT password FROM users WHERE id = ?', (session['user_id'],))
            user_pw = cursor.fetchone()['password']

            if check_password_hash(user_pw, old_pw):
                hashed_new = generate_password_hash(new_pw)
                cursor.execute('UPDATE users SET password = ? WHERE id = ?', (hashed_new, session['user_id']))
                db.commit()
                flash('Password changed successfully!', 'success')
            else:
                flash('Incorrect current password.', 'danger')

        elif action == 'clear_logs':
            cursor.execute('DELETE FROM food_logs WHERE user_id = ?', (session['user_id'],))
            cursor.execute('DELETE FROM workout_logs WHERE user_id = ?', (session['user_id'],))
            cursor.execute('DELETE FROM water_logs WHERE user_id = ?', (session['user_id'],))
            db.commit()
            flash('All personal tracking logs cleared.', 'info')

        return redirect(url_for('settings'))

    cursor.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],))
    user = cursor.fetchone()
    return render_template('settings.html', user=user)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
