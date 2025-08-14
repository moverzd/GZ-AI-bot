from typing import List, Tuple, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.database.models import Sphere, Product, ProductSphere
from src.database.product_file_repositories import ProductFileRepository

class SphereService:
    """
    Сервис для работы со сферами применения
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.file_repo = ProductFileRepository(session)

    async def get_all_spheres(self) -> List[Sphere]:
        """
        Получить все сферы, исключая скрытые для пользователей
        """
        # Список названий сфер, которые нужно скрыть от пользователей
        hidden_spheres = ["ПГС (В процессе редактирования)"]
        
        result = await self.session.execute(
            select(Sphere).where(
                ~Sphere.name.in_(hidden_spheres)
            )
        )
        return list(result.scalars().all())

    async def get_products_by_sphere(self, sphere_id: int) -> List[Tuple[Product, Optional[str]]]:
        """
        Вернуть продукты с главными фотографиями
        """
        result = await self.session.execute(
            select(Product).join(ProductSphere).where(
                ProductSphere.sphere_id == sphere_id,
                Product.is_deleted == False
            )
        )
        products = result.scalars().all()

        output: List[Tuple[Product, Optional[str]]] = []
        for product in products:
            main_image = await self.file_repo.get_main_image(product.id)
            output.append((product, main_image))
        return output