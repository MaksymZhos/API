from sqlalchemy import Boolean, Float, Numeric, ForeignKey, Integer, String, DECIMAL, DateTime
from sqlalchemy.orm import mapped_column, relationship
from sqlalchemy.sql import func
from db import db
from datetime import datetime

class Order(db.Model):
    id = mapped_column(Integer, primary_key=True)
    customer_id = mapped_column(Integer, ForeignKey('customer.id'), nullable=False)
    total = mapped_column(DECIMAL(18, 2), nullable=False, default=0)
    created = mapped_column(DateTime, nullable=False, default=func.now())
    processed = mapped_column(DateTime, nullable=True, default=None)
    customer = relationship("Customer", back_populates="orders")
    items = relationship("ProductsOrder", back_populates="order", cascade="all, delete-orphan")

    def to_json(self):
        items_json = []
        for item in self.items:
            product = item.product
            item_json = {"name": product.name, "quantity": item.quantity}
            items_json.append(item_json)

        return {
            "id": self.id,
            "customer_id": self.customer_id,
            "total": self.total,
            "items": items_json,
            "created": self.created,
            "processed": self.processed
        }

    def process(self, strategy="adjust"):
        if self.processed:
            return False, "Order already processed"
        
        if self.customer.balance < self.total:
            return False, "Insufficient balance"

        for item in self.items:
            product = item.product
            quantity_ordered = item.quantity

            if quantity_ordered > product.available:
                if strategy == 'reject':
                    return False, "Order cannot be processed due to insufficient stock"
                elif strategy == 'ignore':
                    item.quantity = 0
                else:  
                    item.quantity = product.available

            item_price = item.quantity * product.price
            product.available -= item.quantity
            self.total += item_price

        self.customer.balance -= self.total
        self.processed = datetime.now()
        db.session.commit()

        return True, "Order processed successfully"


class Customer(db.Model):
    id = mapped_column(Integer, primary_key=True)
    name = mapped_column(String(200), nullable=False, unique=True)
    phone = mapped_column(String(20), nullable=False)
    balance = mapped_column(Numeric, nullable=False, default=0)
    orders = relationship("Order", back_populates="customer", cascade="all, delete-orphan")


class Product(db.Model):
    id = mapped_column(Integer, primary_key=True)
    name = mapped_column(String(200), nullable=False, unique=True)
    price = mapped_column(Numeric, nullable=False)
    available = mapped_column(Integer, nullable=False, default=0)
    orders = relationship('ProductsOrder', back_populates='product', cascade="all, delete-orphan")


class ProductsOrder(db.Model):
    id = mapped_column(Integer, primary_key=True)
    order_id = mapped_column(Integer, ForeignKey('order.id'), nullable=False)
    product_id = mapped_column(Integer, ForeignKey('product.id'), nullable=False)
    quantity = mapped_column(Integer, nullable=False)
    
    order = relationship('Order', back_populates='items')
    product = relationship('Product', back_populates='orders')



