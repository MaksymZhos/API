import csv
import random
from flask import Flask
from sqlalchemy.sql import func
from app import app
from models import Customer, Product, Order, ProductsOrder, db  # assuming you have these models and db instance

def drop_all():
    with app.app_context():
        db.drop_all()

def create_all():
    with app.app_context():
        db.create_all()

def import_data(filename, model):
    with open("static/data/" + filename, 'r') as file:
        reader = csv.reader(file)
        headers = next(reader)
        data = [dict(zip(headers, row)) for row in reader]

    with app.app_context():
        for item in data:
            if model == Customer:
                # For Customer model, simply create an instance
                instance = model(**item)
            elif model == Product:
                # For Product model, generate a random quantity
                rand_qty = random.randint(10, 30)
                item['available'] = rand_qty
                instance = model(**item)
            else:
                raise ValueError("Unsupported model")

            db.session.add(instance)

        db.session.commit()

def create_random_orders(num_orders):
    with app.app_context():
        for _ in range(num_orders):
            # Find a random customer
            cust_stmt = db.session.query(Customer).order_by(func.random()).limit(1)
            customer = cust_stmt.first()

            # Make an order
            order = Order(customer=customer)
            db.session.add(order)
            db.session.commit()  # Commit the order to get its ID

            # Choose a random number of items (2-3)
            num_items = random.randint(1, 3)

            # Find random products and add them to the order
            for _ in range(num_items):
                prod_stmt = db.session.query(Product).order_by(func.random()).limit(1)
                product = prod_stmt.first()
                rand_qty = random.randint(10, 20)
                
                # Ensure order exists before creating ProductsOrder association
                if order is not None and product is not None:
                    # Ensure order_id is assigned correctly
                    order_id = order.id
                    association = ProductsOrder(order_id=order_id, product=product, quantity=rand_qty)
                    db.session.add(association)
                    db.session.commit()

if __name__ == "__main__":
    # Drop all existing tables
    drop_all()

    # Create new tables
    create_all()

    # Import data from CSV files
    import_data('customers.csv', Customer)
    import_data('products.csv', Product)

    # Create random orders
    create_random_orders(100)  # create 100 random orders
