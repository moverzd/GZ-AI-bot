from sqlalchemy import Column, Integer, String, Text, ForeignKey, TIMESTAMP, Enum, Boolean
from sqlalchemy.orm import relationship
from src.database.connection import Base

"""
Database model representing files associated with products
"""

class ProductGroup(Base):
    __tablename__ = 'product_groups'
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, unique=True)

class Category(Base):
    __tablename__ = 'categories'  # Match actual DB table name (lowercase)
    id = Column(Integer, primary_key = True)
    name = Column(String(255), nullable = False)
    # creates connection Category - Product: category.products
    products = relationship('Product', back_populates = 'category')

class Sphere(Base):
    __tablename__ = 'spheres'  # Match actual DB table name (lowercase)
    id = Column(Integer, primary_key = True)
    name = Column(String(255), nullable = False)
    product_spheres = relationship('ProductSphere', back_populates= 'sphere')

class Product(Base):
    __tablename__ = 'products'  # Match actual DB table name (lowercase)
    id = Column(Integer, primary_key = True)
    category_id = Column(Integer, ForeignKey('categories.id'), nullable = False)  # Match actual table name
    name = Column(String(255), nullable= False)
    short_desc = Column(Text)
    created_at = Column(TIMESTAMP)
    updated_at = Column(TIMESTAMP)
    category = relationship('Category', back_populates = 'products')
    is_deleted = Column(Boolean, nullable = False, default = False) 
    # connection Product - ProductFile, cascade - files will be deleted automaticly in case of deleting the product, 
    files = relationship('ProductFile', back_populates= 'product', cascade= 'all, delete-orphan')
    product_spheres = relationship('ProductSphere', back_populates='product', cascade= 'all, delete-orphan')

class ProductSphere(Base):
    __tablename__ = 'product_spheres'  # Match actual DB table name (lowercase)
    id = Column(Integer, primary_key = True)
    product_id = Column(Integer, ForeignKey('products.id'), nullable = False)  # Match actual table name
    product_name = Column(String(255))  # Add missing field from backup
    sphere_id = Column(Integer, ForeignKey ('spheres.id'), nullable = False)  # Match actual table name
    sphere_name = Column(String(100))
    description = Column(Text)
    advantages = Column(Text)
    notes = Column(Text)
    package = Column(String(500))
    
    # Add the missing relationships
    product = relationship('Product', back_populates='product_spheres')
    sphere = relationship('Sphere', back_populates='product_spheres')

class ProductFile(Base):
    __tablename__ = 'product_files'  # Match actual DB table name (lowercase)
    id = Column(Integer, primary_key= True)
    # CASCADE - if product is_deleted = True : all files will be deleted
    product_id = Column(Integer, ForeignKey('products.id', ondelete= "CASCADE"))  # Match actual table name
    file_id = Column(String(512), nullable = False)
    kind = Column(Enum("image", "video", "doc", name = "filekind"),nullable= False) # NOTE: list of file types right here
    ordering = Column(Integer, nullable = False, default = 0)
    uploaded_by = Column(Integer)  # Исправлено - правильное поле из базы
    uploaded_at = Column(TIMESTAMP)  # Исправлено - правильное поле из базы
    is_deleted = Column(Boolean, nullable = False, default = 0)
    product = relationship("Product", back_populates = "files")







