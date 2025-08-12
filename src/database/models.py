from sqlalchemy import Column, Integer, String, Text, ForeignKey, TIMESTAMP, Enum, Boolean, event, DECIMAL, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
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
    packages = relationship(
        'ProductPackage', 
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


class ProductPackage(Base):
    """Упаковка продукта."""
    
    __tablename__ = 'product_package'
    
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey('products.id', ondelete="CASCADE"), nullable=False)
    product_name = Column(String(255), nullable=False)
    package_type = Column(String(100), nullable=False)
    package_weight = Column(DECIMAL(8, 2), nullable=False)
    packages_per_pallet = Column(Integer, nullable=False)
    net_weight = Column(DECIMAL(8, 2), nullable=False)
    created_at = Column(TIMESTAMP)
    updated_at = Column(TIMESTAMP)
    is_active = Column(Boolean, nullable=False, default=True)
    
    # Отношения
    product = relationship("Product", back_populates="packages")


class UserQuery(Base):
    """Пользовательские запросы к боту."""
    
    __tablename__ = 'user_queries'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False, index=True)  # Telegram user ID
    username = Column(String(255))  # Telegram username
    query_text = Column(Text, nullable=False)  # Текст запроса пользователя
    query_type = Column(
        Enum('search', 'ai_question', 'product_view', name='query_type'),
        nullable=False,
        default='ai_question'
    )  # Тип запроса
    created_at = Column(DateTime, nullable=False, default=func.now())
    
    # Отношения
    responses = relationship(
        'BotResponse', 
        back_populates='query', 
        cascade='all, delete-orphan'
    )


class BotResponse(Base):
    """Ответы бота на запросы пользователей."""
    
    __tablename__ = 'bot_responses'
    
    id = Column(Integer, primary_key=True)
    query_id = Column(Integer, ForeignKey('user_queries.id', ondelete="CASCADE"), nullable=False)
    response_text = Column(Text, nullable=False)  # Текст ответа бота
    response_type = Column(
        Enum('ai_generated', 'search_results', 'product_info', 'error', name='response_type'),
        nullable=False,
        default='ai_generated'
    )  # Тип ответа
    execution_time = Column(DECIMAL(8, 2))  # Время выполнения запроса в секундах
    sources_count = Column(Integer, default=0)  # Количество источников, использованных для ответа
    message_id = Column(Integer)  # ID сообщения в Telegram для связи с feedback
    created_at = Column(DateTime, nullable=False, default=func.now())
    
    # Отношения
    query = relationship('UserQuery', back_populates='responses')
    feedbacks = relationship(
        'UserFeedback', 
        back_populates='response', 
        cascade='all, delete-orphan'
    )


class UserFeedback(Base):
    """Обратная связь пользователей по ответам бота."""
    
    __tablename__ = 'user_feedback'
    
    id = Column(Integer, primary_key=True)
    response_id = Column(Integer, ForeignKey('bot_responses.id', ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, nullable=False, index=True)  # Telegram user ID
    feedback_type = Column(
        Enum('like', 'dislike', name='feedback_type'),
        nullable=False
    )  # Тип реакции
    comment = Column(Text)  # Комментарий пользователя (необязательный)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Отношения
    response = relationship('BotResponse', back_populates='feedbacks')


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