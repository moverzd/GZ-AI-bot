import os
import re
import logging
import pdfplumber
from typing import Optional

logger = logging.getLogger(__name__)

async def extract_text_from_pdf(pdf_path: str, max_pages: Optional[int] = None, max_length: Optional[int] = None) -> str:
    """
    Извлекает текст из PDF файла с расширенными возможностями и обработкой ошибок.
    
    Args:
        pdf_path: Путь к PDF файлу
        max_pages: Максимальное количество страниц для извлечения (None для всех)
        max_length: Максимальная длина извлекаемого текста (None для всего текста)
        
    Returns:
        Извлеченный текст
    """
    logger.info(f"Извлечение текста из файла: {pdf_path}")
    
    if not os.path.exists(pdf_path):
        logger.error(f"Файл не существует: {pdf_path}")
        return "Файл не найден"
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            documents = []
            pages_to_process = pdf.pages[:max_pages] if max_pages else pdf.pages
            logger.info(f"PDF содержит {len(pdf.pages)} страниц, обрабатываем {len(pages_to_process)} страниц")
            
            total_text_length = 0
            for i, page in enumerate(pages_to_process):
                try:
                    # Пробуем сначала извлечь текст стандартным методом
                    page_text = page.extract_text()
                    
                    # Если текст не удалось извлечь или он слишком короткий, 
                    # попробуем альтернативный подход с извлечением таблиц
                    if not page_text or len(page_text) < 100:
                        try:
                            # Пробуем извлечь таблицы
                            tables = page.extract_tables()
                            if tables:
                                table_texts = []
                                for table in tables:
                                    # Преобразуем таблицу в текст
                                    table_text = "\n".join([" | ".join([str(cell) if cell else "" for cell in row]) for row in table])
                                    table_texts.append(table_text)
                                
                                # Объединяем текст таблиц
                                tables_text = "\n\n".join(table_texts)
                                if tables_text:
                                    if page_text:  # Если был текст, добавляем таблицы
                                        page_text += "\n\n" + tables_text
                                    else:  # Если текста не было, используем только таблицы
                                        page_text = tables_text
                        except Exception as e:
                            logger.warning(f"Не удалось извлечь таблицы со страницы {i+1}: {e}")
                    
                    if page_text:
                        # Выполняем дополнительную очистку текста от артефактов
                        # Удаляем множественные пробелы и переводы строк
                        page_text = re.sub(r'\s+', ' ', page_text).strip()
                        # Удаляем повторяющиеся знаки пунктуации
                        page_text = re.sub(r'([.,:;!?])\1+', r'\1', page_text)
                        
                        documents.append(page_text)
                        total_text_length += len(page_text)
                        
                        # Если превысили максимальную длину, останавливаемся (только если лимит установлен)
                        if max_length and total_text_length > max_length:
                            logger.info(f"Достигнут максимальный размер текста ({max_length} символов) на странице {i+1}")
                            break
                except Exception as e:
                    logger.error(f"Ошибка при извлечении текста из страницы {i+1}: {e}")
    
        full_text = ' '.join(documents)
        
        # Обрезаем до максимальной длины на всякий случай (только если лимит установлен)
        if max_length and len(full_text) > max_length:
            full_text = full_text[:max_length]
            
        # Очищаем от повторяющихся пробелов и переносов строк для более компактного представления
        full_text = re.sub(r'\s+', ' ', full_text).strip()
        
        # Если текст слишком короткий, логируем предупреждение
        if len(full_text) < 500 and len(pages_to_process) > 0:
            logger.warning(f"Извлеченный текст слишком короткий ({len(full_text)} символов), возможно документ содержит изображения или защищен")
            
        logger.info(f"Извлечено {len(full_text)} символов текста из PDF")
        
        return full_text
    except Exception as e:
        logger.error(f"Ошибка при обработке PDF файла: {e}")
        return f"Ошибка извлечения текста из PDF: {str(e)}"
