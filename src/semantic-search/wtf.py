from sentence_transformers import SentenceTransformer
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import pandas as pd
import re

# Загрузка модели
model = SentenceTransformer('deepvk/USER-bge-m3')  # 359 млн параметров

# Список продуктов
products_list = [
    "Лента стыковочная «БРИТ» АЭРО 50х8",
    "Лента стыковочная «БРИТ» А, ТРОПИК, NORD",
    "Мастика герметизирующая «БРИТ» ТОРМА МОСТ",
    "Мастики герметизирующие ДШ-85, ДШ-90",
    "Добавка стабилизирующая «Битолит» для ЩМАС",
    "Грунтовка полимерная «БРИТ»",
    "Состав «БРИТ» ЗВС-Р 65, ЗВС-Р 75, ЗВС-Р 85",
    "Состав цветной защитный «БРИТ» ЦЗС-Р",
    "Пропитка гидрофобизирующая «БРИТ» ПК-В",
    "Пропитка проникающая гидрофобизирующая «БРИТ» ПП",
    "Мастика «БРИТ» МБП-Г/ШМ-75",
    "Эмульсия напыляемая «БРИТ» Жидкая резина Мост",
    "Мастики изоляционные «БРИТ» МБР-65, МБР-75, МБР-90, МБР-100",
    "Мастика битумная «БРИТ» МБ-50",
    "Шнур уплотнительный термостойкий «БРИТ»",
    "Шнур уплотнительный термостойкий «БРИТ»",
    "Герметик «БРИТ» ГОСТ БП-Г25, БП-Г35, БП-Г50",
    "Герметик «БРИТ» ГОСТ БП-Г25, БП-Г35, БП-Г50",
    "Мастики герметизирующие «БРИТ» Т-65, Т-75, Т-85, Т-90",
]

# Функция очистки текста
def preprocess_text(text):
    # Приводим текст к нижнему регистру
    text = text.lower()
    
    # Убираем спецсимволы, кавычки и дефисы
    text = re.sub(r"[«»\"\'\-,.]", " ", text)
    
    # Убираем лишние пробелы
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

# Применяем preprocess_text ко всем продуктам в списке
cleaned_products_list = [preprocess_text(product) for product in products_list]

# Список запросов
queries = [
    "ЗВС", "ЗВСКА", "звс", "звска",
    "ПКВ", "пкв",
    "Лента", "ЛЕНТА", "ЖИДКАЯ ЛЕНТА", "Flex", "FLEX", "флекс",
    "Битолит", "Добавка",
    "Торма Мост", "Торма",
    "Т", "Мастика Т"
]

# Функция поиска
def search(query, threshold=0.3):
    # Преобразуем запрос в эмбеддинг
    query_embedding = model.encode(query)
    
    # Преобразуем все продукты в эмбеддинги
    product_embeddings = model.encode(cleaned_products_list)
    
    # Вычисляем косинусное сходство между запросом и продуктами
    cos_sim = cosine_similarity([query_embedding], product_embeddings)

    # Сортируем продукты по сходству
    top_10_idx = np.argsort(cos_sim[0])[::-1][:10]  # Топ-10
    top_10_products = [(products_list[idx], cos_sim[0][idx]) for idx in top_10_idx]
    
    # Печатаем результаты, исключая те, где сходство меньше порога
    print("\nТоп 10 продуктов для запроса:", query)
    count = 0
    for i, (product, score) in enumerate(top_10_products):
        if score >= threshold:
            count += 1
            print(f"{i+1}. Продукт: {product}, Сходство: {score:.2f}")
    
    if count == 0:
        print("Нет результатов с достаточным сходством.")

# Бесконечный цикл для ввода запросов
while True:
    query = preprocess_text(input("\nВведите запрос (или 'exit' для выхода): "))
    if query.lower() == 'exit':
        break
    search(query)
