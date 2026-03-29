from flask import Flask, render_template, request, redirect, session
from flask_sqlalchemy import SQLAlchemy
from models.user import User, db
from datetime import date
from sqlalchemy import text
import math
import os

app = Flask(__name__)
app.secret_key = "fitnessbuddysecret"

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    "DATABASE_URL",
    "mysql+pymysql://root:golu1109@localhost/fitness_buddy"
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)   # ✅ attach directly

# ✅ create tables
with app.app_context():
    db.create_all()

@app.route("/")
def home():
    return render_template("home.html")


@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]

        new_user = User(name=name, email=email, password=password)

        db.session.add(new_user)
        db.session.commit()

        return redirect("/")

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        user = User.query.filter_by(email=email).first()

        if user and user.password == password:

            session["user_id"] = user.id
            session["user_name"] = user.name

            return redirect(f"/dashboard/{user.id}")

        else:
            return "Invalid email or password"

    return render_template("login.html")

@app.route("/dashboard/<int:user_id>")
def dashboard(user_id):

    if "user_id" not in session:
        return redirect("/login")

    user = User.query.get(user_id)

    totals = db.session.execute(text("""
        SELECT
            SUM((f.calories / 100) * fl.quantity) AS calories,
            SUM((f.protein / 100) * fl.quantity) AS protein,
            SUM((f.carbs / 100) * fl.quantity) AS carbs,
            SUM((f.fat / 100) * fl.quantity) AS fat
        FROM food_logs fl
        JOIN foods f ON fl.food_id = f.id
        WHERE fl.user_id = :user_id
        AND fl.log_date = CURDATE()
    """), {"user_id": user_id}).fetchone()


    # ✅ ADD THIS QUERY
    food_logs = db.session.execute(text("""
        SELECT f.food_name, fl.quantity
        FROM food_logs fl
        JOIN foods f ON fl.food_id = f.id
        WHERE fl.user_id = :user_id
        AND fl.log_date = CURDATE()
        ORDER BY fl.id DESC
    """), {"user_id": user_id}).fetchall()


    calories = round(totals.calories or 0)
    protein = round(totals.protein or 0)
    carbs = round(totals.carbs or 0)
    fat = round(totals.fat or 0)

    goal = user.maintenance_calories or 0

    return render_template(
        "dashboard.html",
        user=user,
        calories=calories,
        protein=protein,
        carbs=carbs,
        fat=fat,
        goal=goal,
        food_logs=food_logs   # ✅ ADD THIS
    )
@app.route("/add_food/<int:user_id>", methods=["GET","POST"])
def add_food(user_id):

    if "user_id" not in session:
        return redirect("/login")

    if request.method == "POST":

        food_name = request.form["food_name"]
        quantity = int(request.form["quantity"])

        # find the food in foods table
        food = db.session.execute(
            text("SELECT * FROM foods WHERE food_name = :name"),
            {"name": food_name}
        ).fetchone()

        if food:

            db.session.execute(text("""
                INSERT INTO food_logs (user_id, food_id, quantity, log_date)
                VALUES (:user_id, :food_id, :quantity, :date)
            """), {
                "user_id": user_id,
                "food_id": food.id,
                "quantity": quantity,
                "date": date.today()
            })

            db.session.commit()

        return redirect(f"/dashboard/{user_id}")

    return render_template("add_food.html")

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")

@app.route("/workouts")
def workouts():

    if "user_id" not in session:
        return redirect("/login")

    return render_template("workouts.html")

@app.route("/recipes")
def recipes():

    if "user_id" not in session:
        return redirect("/login")

    return render_template("recipes.html")

@app.route("/recipe/<name>")
def recipe_detail(name):

    recipes = {

        # 🥦 VEG
        "paneer": {
            "name": "Paneer Protein Bowl",
            "description": "High-protein vegetarian meal",
            "image": "paneer.jpg",
            "calories": 450, "protein": 25, "carbs": 20, "fat": 25,
            "ingredients": [
                "200g paneer", "Mixed vegetables", "Olive oil", "Spices"
            ],
            "steps": [
                "Heat oil", "Cook paneer", "Add veggies", "Cook 5–7 min"
            ],
            "tips": "Use low-fat paneer for better macros"
        },

        "dal": {
            "name": "Dal Tadka",
            "description": "Protein-rich lentil curry",
            "image": "dal.jpg",
            "calories": 300, "protein": 18, "carbs": 40, "fat": 8,
            "ingredients": [
                "1 cup lentils", "Garlic", "Spices", "Oil"
            ],
            "steps": [
                "Boil dal", "Prepare tadka", "Mix together", "Serve hot"
            ],
            "tips": "Add ghee for better taste"
        },

        "chickpea": {
            "name": "Chickpea Salad",
            "description": "Healthy high-protein salad",
            "image": "chickpea.jpg",
            "calories": 280, "protein": 20, "carbs": 35, "fat": 6,
            "ingredients": [
                "Boiled chickpeas", "Onion", "Tomato", "Lemon"
            ],
            "steps": [
                "Mix all ingredients", "Add salt & lemon", "Serve fresh"
            ],
            "tips": "Add cucumber for crunch"
        },

        # 🍗 NON-VEG
        "chicken": {
            "name": "Grilled Chicken",
            "description": "Lean protein meal",
            "image": "chicken.jpg",
            "calories": 350, "protein": 35, "carbs": 5, "fat": 15,
            "ingredients": [
                "Chicken breast", "Spices", "Olive oil"
            ],
            "steps": [
                "Marinate chicken", "Grill 6–8 min each side", "Serve"
            ],
            "tips": "Do not overcook"
        },

        "eggs": {
            "name": "Boiled Eggs",
            "description": "Quick protein snack",
            "image": "eggs.jpg",
            "calories": 150, "protein": 12, "carbs": 1, "fat": 10,
            "ingredients": [
                "Eggs", "Salt"
            ],
            "steps": [
                "Boil eggs 8–10 min", "Peel", "Serve"
            ],
            "tips": "Eat with black pepper"
        },

        "fish": {
            "name": "Grilled Fish",
            "description": "High protein + omega 3",
            "image": "fish.jpg",
            "calories": 320, "protein": 30, "carbs": 0, "fat": 18,
            "ingredients": [
                "Fish fillet", "Spices", "Oil"
            ],
            "steps": [
                "Season fish", "Grill both sides", "Serve hot"
            ],
            "tips": "Use lemon for flavor"
        },

        # 🌱 VEGAN
        "tofu": {
            "name": "Tofu Stir Fry",
            "description": "Vegan protein meal",
            "image": "tofu.jpg",
            "calories": 300, "protein": 22, "carbs": 18, "fat": 12,
            "ingredients": [
                "Tofu", "Vegetables", "Soy sauce"
            ],
            "steps": [
                "Fry tofu", "Add veggies", "Add sauce", "Cook 5 min"
            ],
            "tips": "Use firm tofu"
        },

        "quinoa": {
            "name": "Quinoa Bowl",
            "description": "Complete protein meal",
            "image": "quinoa.jpg",
            "calories": 280, "protein": 18, "carbs": 35, "fat": 8,
            "ingredients": [
                "Quinoa", "Vegetables", "Olive oil"
            ],
            "steps": [
                "Cook quinoa", "Add veggies", "Mix well"
            ],
            "tips": "Add avocado for healthy fats"
        },

        "peanut": {
            "name": "Peanut Salad",
            "description": "Protein + healthy fats",
            "image": "peanut.jpg",
            "calories": 260, "protein": 15, "carbs": 20, "fat": 16,
            "ingredients": [
                "Peanuts", "Onion", "Tomato", "Lemon"
            ],
            "steps": [
                "Mix ingredients", "Add lemon", "Serve fresh"
            ],
            "tips": "Roast peanuts for better taste"
        }
    }

    recipe = recipes.get(name)

    if not recipe:
        return "Recipe not found"

    return render_template("recipe_detail.html", recipe=recipe)

@app.route("/bmi", methods=["GET","POST"])
def bmi():

    bmi = None

    if request.method == "POST":

        weight = float(request.form["weight"])
        height = float(request.form["height"])

        bmi = round(weight / ((height/100) ** 2), 2)

    return render_template("bmi.html", bmi=bmi)


import math

@app.route("/bodyfat", methods=["GET","POST"])
def bodyfat():

    bodyfat = None

    if request.method == "POST":

        gender = request.form["gender"]
        height = float(request.form["height"])
        neck = float(request.form["neck"])
        waist = float(request.form["waist"])
        hip = request.form.get("hip")

        if gender == "male":

            bodyfat = 86.010 * math.log10(waist - neck) - 70.041 * math.log10(height) + 36.76

        else:

            hip = float(hip)

            bodyfat = 163.205 * math.log10(waist + hip - neck) - 97.684 * math.log10(height) - 78.387

        bodyfat = round(bodyfat, 2)

    return render_template("bodyfat.html", bodyfat=bodyfat)

@app.route("/calorie_calculator", methods=["GET","POST"])
def calorie_calculator():

    bmr = None
    calories = None

    if request.method == "POST":

        age = int(request.form["age"])
        gender = request.form["gender"]
        weight = float(request.form["weight"])
        height = float(request.form["height"])
        activity = float(request.form["activity"])

        if gender == "male":
            bmr = 10*weight + 6.25*height - 5*age + 5
        else:
            bmr = 10*weight + 6.25*height - 5*age - 161

        bmr = round(bmr)
        calories = round(bmr * activity)

        # save to database if logged in
        if "user_id" in session:
            db.session.execute(text("""
                UPDATE users
                SET maintenance_calories = :calories
                WHERE id = :user_id
            """), {
                "calories": calories,
                "user_id": session["user_id"]
            })
            db.session.commit()

    return render_template(
        "calorie_calculator.html",
        bmr=bmr,
        calories=calories
    )

@app.route("/search_food")
def search_food():

    query = request.args.get("q")

    foods = db.session.execute(text("""
        SELECT food_name
        FROM foods
        WHERE food_name LIKE :query
        LIMIT 5
    """), {"query": f"%{query}%"}).fetchall()

    return {"foods": [food.food_name for food in foods]}

@app.route("/profile", methods=["GET", "POST"])
def profile():

    if "user_id" not in session:
        return redirect("/login")

    user = User.query.get(session["user_id"])

    if request.method == "POST":

        user.age = request.form["age"]
        user.weight = request.form["weight"]
        user.height = request.form["height"]
        user.gender = request.form["gender"]

        db.session.commit()

    return render_template("profile.html", user=user)

@app.route("/workout/ppl")
def ppl():
    return render_template("ppl.html")

@app.route("/workout/upper-lower")
def upper_lower():
    return render_template("upper_lower.html")

@app.route("/workout/bro-split")
def bro_split():
    return render_template("bro_split.html")

@app.route("/workout/hiit")
def hiit():
    return render_template("hiit.html")

if __name__ == "__main__":

 if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

print(os.environ.get("DATABASE_URL"))