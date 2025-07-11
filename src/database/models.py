from sqlalchemy import Column, Integer, String, Text, ForeignKey, TIMESTAMP, Enum, Boolean
from sqlalchemy.orm import relationship
from src.database.connection import Base

"""
Описание таблиц, отношенией для бд с использованием SQLAlchemy
"""

class Category(Base):
    __tablename__ = 'categories'  
    id = Column(Integer, primary_key = True)
    name = Column(String(255), nullable = False)
    products = relationship('Product', back_populates = 'category')

class Sphere(Base):
    __tablename__ = 'spheres' 
    id = Column(Integer, primary_key = True)
    name = Column(String(255), nullable = False)
    product_spheres = relationship('ProductSphere', back_populates= 'sphere')

class Product(Base):
    __tablename__ = 'products' 
    id = Column(Integer, primary_key = True)
    category_id = Column(Integer, ForeignKey('categories.id'), nullable = False) 
    name = Column(String(255), nullable= False)
    short_desc = Column(Text)  # добавляем поле для соответствия с БД, но не юзаем его
    created_at = Column(TIMESTAMP)
    updated_at = Column(TIMESTAMP)
    category = relationship('Category', back_populates = 'products')
    is_deleted = Column(Boolean, nullable = False, default = False) 
    # connection Product - ProductFile, cascade - files will be deleted automaticly in case of deleting the product, 
    files = relationship('ProductFile', back_populates= 'product', cascade= 'all, delete-orphan')
    product_spheres = relationship('ProductSphere', back_populates='product', cascade= 'all, delete-orphan')

class ProductSphere(Base):
    __tablename__ = 'product_spheres' 
    id = Column(Integer, primary_key = True)
    product_id = Column(Integer, ForeignKey('products.id'), nullable = False) 
    product_name = Column(String(255))  
    sphere_id = Column(Integer, ForeignKey ('spheres.id'), nullable = False)  
    sphere_name = Column(String(100))
    description = Column(Text)
    advantages = Column(Text)
    notes = Column(Text)
    package = Column(String(500))
    product = relationship('Product', back_populates='product_spheres')
    sphere = relationship('Sphere', back_populates='product_spheres')

class ProductFile(Base):
    __tablename__ = 'product_files'  
    id = Column(Integer, primary_key= True)
    # CASCADE - if product is_deleted = True : all files will be deleted
    product_id = Column(Integer, ForeignKey('products.id', ondelete= "CASCADE")) 
    file_id = Column(String(512), nullable = False)
    kind = Column(Enum('image','video','document','presentation','pdf','word','excel','archive','other', name = "filekind"),nullable= False)
    ordering = Column(Integer, nullable = False, default = 0)
    uploaded_by = Column(Integer)  
    uploaded_at = Column(TIMESTAMP)  
    is_deleted = Column(Boolean, nullable = False, default = 0)
    title = Column(String(255))
    file_size = Column(Integer)
    mime_type = Column(String(100))
    original_filename = Column(String(255))
    product = relationship("Product", back_populates = "files")







