import gensim.downloader as api
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

import re

#from nltk.corpus import stopwords
#nltk.download('stopwords')

# Загрузка предварительно обученной модели Google News
model = api.load('word2vec-google-news-300')

def clean_naming(text: str):
    text = text.lower()
    text = re.sub(r"[«»\"\'\-,.]", " ", text)
    text = re.sub(r'\s+', ' ', text).strip()

    return text
# Пример данных
queries = [
    "ЗВС", "ЗВСКА", "звс", "звска",
    "ПКВ", "пкв",
    "Лента", "ЛЕНТА", "ЖИДКАЯ ЛЕНТА", "Flex", "FLEX", "флекс",
    "Битолит", "Добавка",
    "Торма Мост", "Торма",
    "Т", "Мастика Т"
]
products = [
    "Герметик «БРИТ» ГОСТ БП-Г25, БП-Г35, БП-Г50",
    "Мастики герметизирующие ДШ-85, ДШ-90"
]

# Проверяем все продукты и запросы
for product_name in products:
    print(f"Сравнение запросов с продуктом: '{product_name}'")

    product_embedding = np.mean([model[word] for word in product_name.lower().split() if word in model], axis=0)

    results = []

    for query in queries:
        # Получаем эмбеддинг запроса
        if query in model:
            query_embedding = model[query]
            cos_sim = cosine_similarity([product_embedding], [query_embedding])
            euc_dist = euclidean(product_embedding, query_embedding)

            
            # Если сходство больше порога (например, 0.50), добавляем результат
            if cos_sim[0][0] > 0.50:
                results.append((query, cos_sim[0][0]))

    # Сортируем результаты по убыванию сходства
    results.sort(key=lambda x: x[1], reverse=True)

    # Печатаем отсортированные результаты
    for query, sim in results:
        print(f"    Запрос: '{query}', Значение сходства: {sim:.2f}")
    print("\n" + "-"*50 + "\n")
