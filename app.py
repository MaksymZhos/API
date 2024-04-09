import os
from pathlib import Path
from models import Customer, Product, Order, ProductsOrder
from flask import Flask, render_template, jsonify, request, abort, redirect, url_for
from db import db
from datetime import datetime

app = Flask(__name__)
# This will make Flask use a 'sqlite' database with the filename provided
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///i_copy_pasted_this.db"
# This will make Flask store the database file in the path provided
app.instance_path = Path(".").resolve()
# Adjust to your needs / liking. Most likely, you want to use "." for your instance
#path. You may also use "data".
db.init_app(app)

@app.route("/")
def home():
    return render_template("home.html", title="Main Page")

@app.route("/customers")
def customers():
    customers = Customer.query.all()  # get all customers from the database
    return render_template("customers.html", title="Customer List", customers=customers)

@app.route("/products")
def products():
    products = Product.query.all()  # get all products from the database
    return render_template("products.html", title="Product List", products=products)

@app.route("/api/customers")
def customers_json():
    statement = db.select(Customer).order_by(Customer.name)
    results = db.session.execute(statement)
    customers = [] # output variable
    for customer in results.scalars():
        json_record = {
            "id": customer.id,
            "name": customer.name,
            "phone": customer.phone,
            "balance": customer.balance,
        }
        customers.append(json_record)

    return jsonify(customers)

@app.route("/api/customers/<int:customer_id>")
def customer_detail_json(customer_id):
    statement = db.select(Customer).where(Customer.id == customer_id)
    result = db.session.execute(statement)
    customer = result.scalar()
    if customer is None:
        return jsonify({"error": "Customer not found"}), 404

    json_record = {
        "id": customer.id,
        "name": customer.name,
        "phone": customer.phone,
        "balance": customer.balance,
    }

    return jsonify(json_record)
@app.route("/api/customers/<int:customer_id>", methods=["DELETE"])
def delete_customer(customer_id):
    customer = Customer.query.filter_by(id=customer_id).first()
    if customer is None:
        return "Customer not found", 404
    db.session.delete(customer)
    db.session.commit()
    return "", 204

 
@app.route("/api/customers", methods=["POST"])
def create_customer():
    data = request.json
    if "name" not in data or "phone" not in data:
        return "Invalid request", 400
    customer = Customer(name=data["name"], phone=data["phone"])
    db.session.add(customer)
    db.session.commit()
    return jsonify(customer.id), 201

@app.route("/api/customers/<int:customer_id>", methods=["PUT"])
def update_customer(customer_id):
    data = request.json
    if "balance" not in data:
        return "Invalid request", 400
    balance = data["balance"]
    if not isinstance(balance, (int, float)):
        return "Invalid request: balance", 400
    customer = Customer.query.get_or_404(customer_id)
    customer.balance = balance
    db.session.commit()
    return "", 204

@app.route("/api/products", methods=["POST"])
def create_product():
    data = request.json
    if "name" not in data or "price" not in data:
        return "Invalid request", 400
    product = Product(name=data["name"], price=data["price"])
    db.session.add(product)
    db.session.commit()
    return jsonify(product.id), 201

@app.route("/api/products/<int:product_id>", methods=["PUT"])
def update_product(product_id):
    data = request.json
    if "name" not in data and "price" not in data:
        return "Invalid request", 400
    product = Product.query.get_or_404(product_id)
    if "name" in data:
        product.name = data["name"]
    if "price" in data:
        product.price = data["price"]
    db.session.commit()
    return "", 204

@app.route("/api/products/<int:product_id>", methods=["DELETE"])
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    if product is None:
        return "Product not found", 404
    db.session.delete(product)
    db.session.commit()
    return "", 204

@app.route("/customer/<int:customer_id>")
def customer_orders(customer_id):
    customer = Customer.query.get_or_404(customer_id)
    orders = Order.query.filter_by(customer_id=customer_id).all()
    for order in orders:
        total_price = sum(item.product.price * item.quantity for item in order.items)
        order.total_price = round(total_price, 2)
        for item in order.items:
            item.product.price = round(item.product.price, 2)
            item.total_price = round(item.product.price * item.quantity, 2)
    return render_template("customer_orders.html", title="Customer Orders", customer=customer, orders=orders, now=datetime.utcnow())




@app.route("/api/orders", methods=["POST"])
def make_order():
    data = request.json
    
    # Validate JSON data
    if not data or "customer_id" not in data or "items" not in data:
        return jsonify({"error": "Invalid request. Missing customer_id or items."}), 400

    customer_id = data["customer_id"]
    items = data["items"]

    # Check if customer exists
    customer = Customer.query.get(customer_id)
    if customer is None:
        return jsonify({"error": f"Customer with ID {customer_id} not found."}), 404

    # Validate items
    for item in items:
        name = item.get("name")
        quantity = item.get("quantity")

        if not name or not quantity or quantity <= 0:
            return jsonify({"error": "Invalid item. Each item must have a name and a positive quantity."}), 400

        product = Product.query.filter_by(name=name).first()
        if product is None:
            continue  # Ignore items with non-existing products

        if product.available < quantity:
            return jsonify({"error": f"Not enough stock for product: {name}."}), 400

    # Process the order
    order = Order(customer_id=customer_id)
    db.session.add(order)

    for item in items:
        name = item["name"]
        quantity = item["quantity"]
        product = Product.query.filter_by(name=name).first()
        
        if product is not None:
            association = ProductsOrder(order=order, product=product, quantity=quantity)
            db.session.add(association)
            product.available -= quantity

    db.session.commit()

    return jsonify({"message": "Order placed successfully."}), 200


@app.route('/orders/<int:order_id>/delete', methods=['POST'])
def order_delete(order_id):
    order = Order.query.get(order_id)
    if order:
        if order.processed:
            return 'Cannot delete processed order', 400
        # Delete the associated products orders first
        ProductsOrder.query.filter_by(order_id=order_id).delete()
        
        # Then delete the order
        db.session.delete(order)
        db.session.commit()
        return redirect(url_for("all_orders"))
    else:
        return 'Order not found', 404
    
@app.route("/orders")
def all_orders():
    orders = Order.query.all()
    for order in orders:
        total_price = sum(item.product.price * item.quantity for item in order.items)
        order.total_price = round(total_price, 2)
        for item in order.items:
            item.product.price = round(item.product.price, 2)
            item.total_price = round(item.product.price * item.quantity, 2)
    return render_template("all_orders.html", title="All Orders", orders=orders)



@app.route("/orders/<int:order_id>")
def order_details(order_id):
    order = Order.query.get_or_404(order_id)
    customer = Customer.query.get_or_404(order.customer_id)
    total_price = sum(item.product.price * item.quantity for item in order.items)
    order.total_price = round(total_price, 2)
    for item in order.items:
        item.product.price = round(item.product.price, 2)
        item.total_price = round(item.product.price * item.quantity, 2)
    return render_template("order_details.html", title="Order Details", customer=customer, orders=[order])

@app.route("/api/orders/<int:order_id>", methods=["POST"])
def update_order(order_id):
    data = request.json
    
    # Check if 'process' key exists in the JSON payload
    if "process" not in data:
        return jsonify({"error": "Invalid request. Missing 'process' key."}), 400
    
    process = data["process"]
    
    # Check if 'process' value is a boolean
    if not isinstance(process, bool):
        return jsonify({"error": "Invalid request. 'process' value must be a boolean."}), 400
    
    # Check if 'strategy' key exists and is valid
    strategy = data.get("strategy", "adjust")
    valid_strategies = ["adjust", "reject", "ignore"]
    if strategy not in valid_strategies:
        return jsonify({"error": f"Invalid strategy. Must be one of: {', '.join(valid_strategies)}"}), 400
    
    # Process the order based on the strategy
    if process:
        
        return jsonify({"message": f"Order {order_id} processed successfully with strategy: {strategy}"}), 200
    else:
        return jsonify({"message": f"Order {order_id} not processed."}), 200



if __name__ == "__main__":
    app.run(debug=True, port=8888)