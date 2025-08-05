from sqlalchemy import Column, Integer, String, Text, ForeignKey, TIMESTAMP, Enum, Boolean, event
from sqlalchemy.orm import relationship
from src.database.connection import Base

"""
Модели базы данных для работы с продуктами и связанными сущностями.
"""


class Category(Base):
    """Категория продуктов."""
    
    __tablename__ = 'categories'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    
    # Отношения
    products = relationship('Product', back_populates='category')


class Sphere(Base):
    """Сфера применения продуктов."""
    
    __tablename__ = 'spheres'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    
    # Отношения
    product_spheres = relationship('ProductSphere', back_populates='sphere')


class Product(Base):
    """Продукт."""
    
    __tablename__ = 'products'
    
    id = Column(Integer, primary_key=True)
    category_id = Column(Integer, ForeignKey('categories.id'), nullable=False)
    name = Column(String(255), nullable=False)
    created_at = Column(TIMESTAMP)
    updated_at = Column(TIMESTAMP)
    is_deleted = Column(Boolean, nullable=False, default=False)
    
    # Отношения
    category = relationship('Category', back_populates='products')
    files = relationship(
        'ProductFile', 
        back_populates='product', 
        cascade='all, delete-orphan'
    )
    product_spheres = relationship(
        'ProductSphere', 
        back_populates='product', 
        cascade='all, delete-orphan'
    )


class ProductSphere(Base):
    """Связь продукта со сферой применения и дополнительная информация."""
    
    __tablename__ = 'product_spheres'
    
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    product_name = Column(String(255))
    sphere_id = Column(Integer, ForeignKey('spheres.id'), nullable=False)
    sphere_name = Column(String(100))
    description = Column(Text)
    advantages = Column(Text)
    notes = Column(Text)
    package = Column(String(500))
    
    # Отношения
    product = relationship('Product', back_populates='product_spheres')
    sphere = relationship('Sphere', back_populates='product_spheres')


class ProductFile(Base):
    """Файл, прикрепленный к продукту."""
    
    __tablename__ = 'product_files'
    
    id = Column(Integer, primary_key=True)
    product_id = Column(
        Integer, 
        ForeignKey('products.id', ondelete="CASCADE")
    )
    file_id = Column(String(512), nullable=False)
    kind = Column(
        Enum(
            'image', 'video', 'document', 'presentation', 
            'pdf', 'word', 'excel', 'archive', 'other',
            name="filekind"
        ),
        nullable=False
    )
    ordering = Column(Integer, nullable=False, default=0)
    uploaded_by = Column(Integer)
    uploaded_at = Column(TIMESTAMP)
    is_deleted = Column(Boolean, nullable=False, default=False)
    is_main_image = Column(Boolean, nullable=False, default=False)
    title = Column(String(255))
    file_size = Column(Integer)
    mime_type = Column(String(100))
    original_filename = Column(String(255))
    local_path = Column(String(512))
    
    # Отношения
    product = relationship("Product", back_populates="files")


# Регистрация обработчиков событий SQLAlchemy
@event.listens_for(Product, 'after_insert')
def _on_product_insert(mapper, connection, target):
    """Событие после создания продукта."""
    from src.services.embeddings.sync_service import on_product_insert
    on_product_insert(mapper, connection, target)


@event.listens_for(Product, 'after_update')
def _on_product_update(mapper, connection, target):
    """Событие после обновления продукта."""
    from src.services.embeddings.sync_service import on_product_update
    on_product_update(mapper, connection, target)


@event.listens_for(Product, 'after_delete')
def _on_product_delete(mapper, connection, target):
    """Событие после удаления продукта."""
    from src.services.embeddings.sync_service import on_product_delete
    on_product_delete(mapper, connection, target)